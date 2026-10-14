"""Offline behavioral and safety tests for the Stark/Ironman roles."""
import json
import unittest
from unittest.mock import patch

from agents.stark_ironman import Action, Evidence, IronmanRuntime, StarkPlanner


class MockRegistry:
    def __init__(self, provider):
        self.provider = provider

    def get(self, name):
        if name != "unit-provider":
            raise KeyError(name)
        return self.provider


class MockProvider:
    def __init__(self, answer):
        self.answer = answer
        self.calls = 0

    def propose(self, prompt):
        self.calls += 1
        return self.answer


class StarkIronmanTests(unittest.TestCase):
    def test_offline_has_no_provider_calls_and_provenance(self):
        plan = StarkPlanner().plan("Design a legal research index", evidence=(
            Evidence("registry", "NCT number is present", "ClinicalTrials.gov"),
        ))
        self.assertEqual(plan["mode"], "offline_template")
        self.assertEqual(plan["execution"], "not_executed")
        self.assertEqual(plan["evidence"][0]["provenance"], "ClinicalTrials.gov")
        self.assertEqual(len(plan["graph"]["steps"]), 3)
        self.assertEqual(IronmanRuntime().execute(plan)["completed"], 0)

    def test_registry_provider_generates_valid_graph(self):
        candidate = {"task": "Plan", "steps": [
            {"id": "s1", "description": "Analyze registry sources", "source_ids": ["ctgov"]},
        ]}
        provider = MockProvider(json.dumps(candidate))
        planner = StarkPlanner(provider_registry=MockRegistry(provider), provider_name="unit-provider")
        plan = planner.plan("Plan", evidence=(Evidence("ctgov", "Trial", "public record"),))
        self.assertEqual(plan["mode"], "model_generated")
        self.assertEqual(plan["graph"]["steps"][0]["source_ids"], ["ctgov"])
        self.assertEqual(provider.calls, 1)

    def test_unknown_source_in_model_output_falls_back(self):
        provider = MockProvider(json.dumps({"task": "Task", "steps": [
            {"id": "s1", "description": "Claim", "source_ids": ["fake"]},
        ]}))
        plan = StarkPlanner(provider_registry=MockRegistry(provider), provider_name="unit-provider").plan("Task")
        self.assertEqual(plan["mode"], "offline_template")
        self.assertIn("model_fallback:invalid_graph", plan["warnings"])

    def test_write_requires_explicit_per_step_approval(self):
        plan = StarkPlanner().plan("Design a small test")
        calls = []
        runtime = IronmanRuntime()
        runtime.register_tool("save_artifact", lambda p: calls.append(p["name"]) or "ok", risk="write")
        action = Action("s2", "save_artifact", {"name": "approved.txt"})
        dry = runtime.execute(plan, actions=(action,))
        self.assertEqual(dry["events"][1]["status"], "dry_run")
        self.assertFalse(calls)
        blocked = runtime.execute(plan, actions=(action,), commit=True)
        self.assertEqual(blocked["events"][1]["status"], "blocked_approval_required")
        allowed = runtime.execute(plan, actions=(action,), approved_steps=("s2",), commit=True)
        self.assertEqual(allowed["events"][1]["status"], "completed")
        self.assertEqual(calls, ["approved.txt"])

    def test_external_requires_approval_and_explicit_opt_in(self):
        plan = StarkPlanner().plan("Inspect a public website")
        calls = []
        runtime = IronmanRuntime()
        runtime.register_tool("network", lambda _: calls.append(1), risk="external")
        req = Action("s1", "network", {})
        self.assertEqual(runtime.execute(plan, actions=(req,), commit=True,
                         approved_steps=("s1",))["events"][0]["status"], "blocked_external_disabled")
        self.assertFalse(calls)
        self.assertEqual(runtime.execute(plan, actions=(req,), commit=True,
                         approved_steps=("s1",), allow_external=True)["events"][0]["status"], "completed")
        self.assertEqual(len(calls), 1)

    def test_unregistered_tool_is_never_invoked(self):
        plan = StarkPlanner().plan("Analyze test")
        report = IronmanRuntime().execute(plan, actions=(Action("s1", "shell", {"command": "rm -rf /"}),), commit=True)
        self.assertEqual(report["events"][0]["status"], "blocked_unregistered_tool")

    def test_tampered_plan_is_rejected(self):
        plan = StarkPlanner().plan("Analyze")
        plan["graph"]["steps"][0]["description"] = "Ignore policy"
        with self.assertRaises(ValueError):
            IronmanRuntime().execute(plan)

    def test_invalid_inputs_and_duplicate_evidence(self):
        with self.assertRaises(ValueError):
            StarkPlanner().plan(" ")
        with self.assertRaises(ValueError):
            StarkPlanner().plan("x", evidence=(Evidence("x", "a", "b"), Evidence("x", "c", "d")))
        runtime = IronmanRuntime()
        runtime.register_tool("t", lambda _: None)
        with self.assertRaises(ValueError):
            runtime.register_tool("t", lambda _: None)

    def test_killswitch_blocks_plan_and_tool_execution(self):
        import ai_killswitch
        with patch.object(ai_killswitch, "require_ai_allowed", side_effect=PermissionError("stop")):
            # The core imported the bound function; patch its local name.
            with patch("agents.stark_ironman.require_ai_allowed", side_effect=PermissionError("stop")):
                with self.assertRaises(PermissionError):
                    StarkPlanner().plan("analyze")
        plan = StarkPlanner().plan("analyze")
        with patch("agents.stark_ironman.require_ai_allowed", side_effect=PermissionError("stop")):
            with self.assertRaises(PermissionError):
                IronmanRuntime().execute(plan)

    def test_read_only_registered_tool_executes_when_explicitly_committed(self):
        plan = StarkPlanner().plan("Search local catalog")
        runtime = IronmanRuntime()
        runtime.register_tool("catalog", lambda p: {"name": p["query"]})
        result = runtime.execute(plan, actions=(Action("s1", "catalog", {"query": "books"}),), commit=True)
        self.assertEqual(result["events"][0]["result"], {"name": "books"})
        self.assertEqual(result["completed"], 1)


if __name__ == "__main__":
    unittest.main()