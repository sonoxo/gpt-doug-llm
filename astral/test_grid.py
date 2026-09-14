import unittest
from datetime import datetime, timedelta, timezone

from astral.grid import AstralGrid, ResourceNode, Task, build_grid


class AstralGridTests(unittest.TestCase):
    def make_grid(self) -> AstralGrid:
        return build_grid(
            [
                ResourceNode(
                    "alpha",
                    capacity={"compute": 8, "memory": 16, "context": 32},
                    labels={"general", "trusted"},
                    zone="xunia",
                ),
                ResourceNode(
                    "beta",
                    capacity={"compute": 10, "memory": 16, "context": 16},
                    labels={"general", "trusted"},
                    zone="xunia",
                ),
                ResourceNode(
                    "gamma",
                    capacity={"compute": 6, "memory": 8, "context": 8},
                    labels={"general"},
                    zone="lab",
                ),
            ]
        )

    def test_peer_assist_pools_only_shareable_resource(self) -> None:
        grid = self.make_grid()
        task = Task(
            "peer",
            requirements={"compute": 14, "memory": 8, "context": 8},
            required_labels={"trusted"},
            required_zone="xunia",
            shareable_resources={"compute"},
        )
        assignment = grid.assign(task)
        self.assertGreaterEqual(len(assignment.helper_nodes), 1)
        self.assertAlmostEqual(
            sum(bundle.get("compute", 0) for bundle in assignment.reservations.values()),
            14,
        )
        primary_bundle = assignment.reservations[assignment.primary_node]
        self.assertEqual(primary_bundle["memory"], 8)
        self.assertEqual(primary_bundle["context"], 8)
        for helper in assignment.helper_nodes:
            self.assertNotIn("memory", assignment.reservations[helper])
            self.assertNotIn("context", assignment.reservations[helper])

    def test_nonshareable_resource_must_fit_primary(self) -> None:
        grid = self.make_grid()
        task = Task(
            "context-heavy",
            requirements={"compute": 4, "context": 40},
            required_labels={"trusted"},
            required_zone="xunia",
            shareable_resources={"compute"},
        )
        with self.assertRaises(RuntimeError):
            grid.assign(task)

    def test_quarantine_and_authorization_fail_closed(self) -> None:
        grid = self.make_grid()
        grid.quarantine("alpha", reason="integrity_check")
        grid.update_node("beta", authorized=False)
        task = Task(
            "blocked",
            requirements={"compute": 2},
            required_labels={"trusted"},
            required_zone="xunia",
        )
        with self.assertRaises(RuntimeError):
            grid.assign(task)

    def test_release_restores_exact_reservations(self) -> None:
        grid = self.make_grid()
        task = Task(
            "release",
            requirements={"compute": 12, "memory": 4},
            required_labels={"trusted"},
            required_zone="xunia",
            shareable_resources={"compute"},
        )
        before = grid.snapshot()
        assignment = grid.assign(task)
        grid.release(assignment)
        after = grid.snapshot()
        before_nodes = {node["node_id"]: node["usage"] for node in before["nodes"]}
        after_nodes = {node["node_id"]: node["usage"] for node in after["nodes"]}
        self.assertEqual(before_nodes, after_nodes)

    def test_expired_lease_releases_resources(self) -> None:
        grid = self.make_grid()
        task = Task(
            "lease",
            requirements={"compute": 2},
            required_labels={"trusted"},
            required_zone="xunia",
            lease_seconds=1,
        )
        assignment = grid.assign(task)
        future = datetime.now(timezone.utc) + timedelta(seconds=5)
        expired = grid.expire_leases(now=future)
        self.assertIn("lease", expired)
        self.assertEqual(assignment.state, "released")

    def test_depletion_rebalance_avoids_old_primary(self) -> None:
        grid = self.make_grid()
        task = Task(
            "rebalance",
            requirements={"compute": 4, "memory": 4},
            required_labels={"trusted"},
            required_zone="xunia",
        )
        first = grid.assign(task)
        grid.update_node(first.primary_node, health=0.1)
        second = grid.rebalance(task)
        self.assertNotEqual(first.primary_node, second.primary_node)

    def test_audit_chain_verifies(self) -> None:
        grid = self.make_grid()
        task = Task(
            "audit",
            requirements={"compute": 2},
            required_labels={"trusted"},
            required_zone="xunia",
        )
        assignment = grid.assign(task)
        grid.release(assignment)
        self.assertTrue(grid.verify_audit_chain())
        grid.audit[-1]["event"] = "tampered"
        self.assertFalse(grid.verify_audit_chain())


if __name__ == "__main__":
    unittest.main()
