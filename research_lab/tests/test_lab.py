import copy
import json
import tempfile
import unittest
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from research_lab.approval import ApprovalGate, digest
from research_lab.repair import plan, affected_nodes
from research_lab.reconcile import reconcile
from research_lab.lineage import anchor, audit, verify
from research_lab.demo import run


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.gate = ApprovalGate(":memory:", ["operator"])
        self.addCleanup(self.gate.close)
        self.state = {"mission": "m1", "action": "a1", "code": {"c": digest("c")},
                      "data": {"d": digest("d")}, "policy": {"p": digest("p")}}

    def test_success_then_replay(self):
        token = self.gate.issue(self.state, "operator", 100)
        self.assertTrue(self.gate.consume(token, self.state, 101))
        self.assertFalse(self.gate.consume(token, self.state, 102))

    def test_each_binding_dimension(self):
        token = self.gate.issue(self.state, "operator", 100)
        for key in self.state:
            changed = copy.deepcopy(self.state)
            changed[key] = "changed" if key in ("mission", "action") else {"new": digest("new")}
            self.assertFalse(self.gate.consume(token, changed, 101))

    def test_expiry_and_future_issue(self):
        token = self.gate.issue(self.state, "operator", 100, ttl=5)
        self.assertFalse(self.gate.consume(token, self.state, 99))
        self.assertFalse(self.gate.consume(token, self.state, 105))

    def test_unauthorized_issuer(self):
        with self.assertRaises(PermissionError):
            self.gate.issue(self.state, "intruder", 100)

    def test_unknown_token(self):
        self.assertFalse(self.gate.consume("forged", self.state, 101))

    def test_revoked_approver(self):
        token = self.gate.issue(self.state, "operator", 100)
        self.gate.approvers = frozenset()
        self.assertFalse(self.gate.consume(token, self.state, 101))

    def test_missing_evidence(self):
        state = {**self.state, "data": {}}
        with self.assertRaises(ValueError):
            self.gate.issue(state, "operator", 100)

    def test_nonfinite_expiry(self):
        with self.assertRaises(ValueError):
            self.gate.issue(self.state, "operator", 100, float("inf"))

    def test_restart_and_concurrent_consumption(self):
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / "gate.sqlite")
            gate = ApprovalGate(db, ["operator"])
            token = gate.issue(self.state, "operator", 100)
            gate.close()
            def consume(_):
                other = ApprovalGate(db, ["operator"])
                try:
                    return other.consume(token, self.state, 101)
                finally:
                    other.close()
            with ThreadPoolExecutor(max_workers=4) as pool:
                self.assertEqual(sum(pool.map(consume, range(4))), 1)


class RepairTests(unittest.TestCase):
    def test_transitive_cycle_and_disconnected_node(self):
        graph = {"a": ["c"], "b": ["a"], "c": ["b"], "other": []}
        self.assertEqual(affected_nodes(graph, ["a"]), ["a", "b", "c"])

    def test_unknown_dependency(self):
        with self.assertRaises(ValueError):
            affected_nodes({"a": ["absent"]}, ["a"])

    def test_unknown_change(self):
        with self.assertRaises(ValueError):
            affected_nodes({"a": []}, ["absent"])

    def test_missing_coverage_requires_review(self):
        result = plan({"a": []}, ["a"], {}, {})
        self.assertEqual(result["status"], "REVIEW")
        self.assertEqual(result["missing_rollback_revisions"], ["a"])

    def test_test_deduplication(self):
        result = plan({"a": [], "b": ["a"]}, ["a"], {"a": ["shared"], "b": ["shared"]}, {"a": "v1", "b": "v1"})
        self.assertEqual(result["tests"], ["shared"])
        self.assertEqual(result["status"], "PLAN_READY")


class ReconciliationTests(unittest.TestCase):
    def test_json_boolean_and_integer_are_distinct(self):
        result = reconcile({"a": 0}, {"a": True}, {"a": 1})
        self.assertEqual(result["status"], "CONFLICT")

    def test_disjoint_and_no_input_mutation(self):
        base, local, remote = {"a": 1, "b": 1}, {"a": 2, "b": 1}, {"a": 1, "b": 2}
        before = copy.deepcopy((base, local, remote))
        result = reconcile(base, local, remote)
        self.assertEqual(result["candidate"], {"a": 2, "b": 2})
        self.assertEqual((base, local, remote), before)

    def test_edit_delete_conflict(self):
        result = reconcile({"a": 1}, {}, {"a": 2})
        self.assertFalse(result["apply_allowed"])
        self.assertFalse(result["conflicts"][0]["local"]["present"])

    def test_null_is_not_deletion(self):
        result = reconcile({"a": 1}, {"a": None}, {"a": 1})
        self.assertIn("a", result["candidate"])
        self.assertIsNone(result["candidate"]["a"])

    def test_identical_changes(self):
        self.assertEqual(reconcile({}, {"a": 1}, {"a": 1})["candidate"], {"a": 1})

    def test_deletion(self):
        result = reconcile({"a": 1}, {}, {"a": 1})
        self.assertEqual(result["candidate"], {})
        self.assertTrue(result["provenance"]["a"]["deleted"])

    def test_order_independent(self):
        a = reconcile({}, {"b": 2, "a": 1}, {})
        b = reconcile({}, {"a": 1, "b": 2}, {})
        self.assertEqual(json.dumps(a), json.dumps(b))


class LineageTests(unittest.TestCase):
    def test_unicode_offsets(self):
        text = "🧠 evidence"
        self.assertTrue(verify(anchor("doc", text, 2, 10), {"doc": text}))

    def test_missing_source(self):
        self.assertFalse(verify(anchor("doc", "text", 0, 4), {}))

    def test_quote_tampering(self):
        a = anchor("doc", "text", 0, 4)
        a["quote"] = "fake"
        self.assertFalse(verify(a, {"doc": "text"}))

    def test_transitive_invalidation_with_valid_child_anchor(self):
        a = anchor("a", "old", 0, 3)
        b = anchor("b", "valid", 0, 5)
        claims = {"parent": {"citations": [a]}, "child": {"citations": [b], "depends_on": ["parent"]}}
        result = audit(claims, {"a": "new", "b": "valid"})
        self.assertEqual(result["direct_invalid"], ["parent"])
        self.assertEqual(result["invalidated"], ["child", "parent"])

    def test_empty_citations_require_review(self):
        self.assertEqual(audit({"a": {}}, {})["claims"]["a"], "REVIEW")

    def test_invalid_offsets(self):
        with self.assertRaises(ValueError):
            anchor("a", "text", -1, 3)

    def test_demo(self):
        self.assertTrue(run()["passed"])


class CLITests(unittest.TestCase):
    def invoke(self, command, data):
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.json"
            source.write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run([sys.executable, str(root / "scripts/invention_lab.py"), command, str(source)], capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    def test_repair_cli_review(self):
        code, output = self.invoke("repair", {"dependencies": {"a": []}, "changed": ["a"], "tests": {}, "revisions": {}})
        self.assertEqual(code, 1)
        self.assertEqual(output["status"], "REVIEW")

    def test_reconcile_cli_conflict(self):
        code, output = self.invoke("reconcile", {"base": {"a": 1}, "local": {"a": 2}, "remote": {"a": 3}})
        self.assertEqual(code, 1)
        self.assertEqual(output["status"], "CONFLICT")

    def test_lineage_cli(self):
        data = {"documents": {"doc": "text"}, "claims": {"claim": {"citations": [anchor("doc", "text", 0, 4)]}}}
        code, output = self.invoke("lineage", data)
        self.assertEqual(code, 0)
        self.assertEqual(output["semantic_support"], "not_evaluated")

    def test_bad_input_cli(self):
        code, output = self.invoke("repair", {})
        self.assertEqual(code, 2)
        self.assertEqual(output["status"], "ERROR")


if __name__ == "__main__":
    unittest.main()
