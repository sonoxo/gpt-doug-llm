import unittest

from recursive_fleet.planner import RecursivePlanner, build_rotation_plan


class RecursivePlannerTests(unittest.TestCase):
    def test_recurses_to_nested_subgoals(self):
        tree = {"root": ["alpha", "beta"], "alpha": ["alpha-1"], "alpha-1": [], "beta": []}
        plan = RecursivePlanner(lambda goal: tree.get(goal, []), max_depth=4, max_nodes=10).plan("root")
        self.assertEqual(plan.node_count, 4)
        self.assertEqual(plan.root.children[0].children[0].goal, "alpha-1")
        self.assertFalse(plan.budget_exhausted)

    def test_node_budget_is_hard_bound(self):
        plan = RecursivePlanner(lambda goal: [f"child-{i}" for i in range(20)] if goal == "root" else [], max_nodes=3).plan("root")
        self.assertEqual(plan.node_count, 3)
        self.assertTrue(plan.budget_exhausted)

    def test_cycles_and_duplicate_siblings_are_skipped(self):
        tree = {"root": ["child", "child"], "child": ["root"]}
        plan = RecursivePlanner(lambda goal: tree.get(goal, []), max_depth=5).plan("root")
        self.assertGreaterEqual(plan.skipped_cycles, 1)
        self.assertEqual(len(plan.root.children), 1)

    def test_bad_bounds_and_empty_goal_rejected(self):
        with self.assertRaises(ValueError):
            RecursivePlanner(max_nodes=0)
        with self.assertRaises(ValueError):
            RecursivePlanner().plan("  ")

    def test_rotation_plan_holds_unconfirmed_credentials(self):
        plan = build_rotation_plan([{
            "credential_id": "cred-1", "provider": "example", "alias": "worker",
            "environment": "staging", "rotation_requested": True, "owner_confirmed": False,
        }])
        self.assertEqual(plan["candidate_count"], 0)
        self.assertEqual(plan["held_count"], 1)
        self.assertFalse(plan["provider_mutations_performed"])

    def test_rotation_plan_requires_both_explicit_flags_and_redacts_secrets(self):
        records = [
            {"credential_id": f"cred-{i}", "provider": "example", "alias": f"worker-{i}",
             "environment": "staging", "rotation_requested": True, "owner_confirmed": True}
            for i in range(7)
        ]
        plan = build_rotation_plan(records, batch_size=3)
        self.assertEqual(plan["candidate_count"], 7)
        self.assertEqual([len(b["credential_ids"]) for b in plan["batches"]], [3, 3, 1])
        with self.assertRaises(ValueError):
            build_rotation_plan([{
                "credential_id": "cred-leak", "provider": "example", "alias": "x",
                "environment": "prod", "api_key": "never-accept-this"
            }])


if __name__ == "__main__":
    unittest.main()
