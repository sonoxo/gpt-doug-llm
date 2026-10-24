"""No-network, no-weights test suite for the 99,999,999 logical REA swarm."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

from integrations.openai_model_mirror import swarm
from integrations.openai_model_mirror.mirror import MirrorError


class SwarmContract(unittest.TestCase):
    def test_99999999_logical_agents_have_exact_partition_sum(self):
        plan = swarm.create_plan(count=99_999_999, slots=8, sample=12)
        self.assertEqual(plan["indexed_virtual_agents"], 99_999_999)
        self.assertEqual(sum(s["agent_count"] for s in plan["partitions"]), 99_999_999)
        self.assertEqual(len(plan["partitions"]), 8)
        self.assertEqual(len(plan["sample"]), 12)
        self.assertEqual(plan["sample"][-1]["zero_based_index"], 99_999_998)
        self.assertEqual(plan["sample"][0]["zero_based_index"], 0)

    def test_honest_no_real_replication(self):
        plan = swarm.create_plan()
        for key in ("active_processes_started", "weights_copied", "agents_executing_inference"):
            self.assertEqual(plan[key], 0)
        for key in ("satellite_uplink", "external_network_access", "self_propagation", "remote_deployment"):
            self.assertFalse(plan[key])
        self.assertIn("not-run", plan["rea_inspection_status"])

    def test_deterministic_agent_identity_and_pool(self):
        a = swarm.create_plan(model="openai/gpt-oss-20b", count=101, slots=7)
        b = swarm.create_plan(model="openai/gpt-oss-20b", count=101, slots=7)
        self.assertEqual(a, b)
        self.assertNotEqual(a["pool_id"], swarm.create_plan(count=102, slots=7)["pool_id"])
        self.assertEqual(len(set(x["agent_id"] for x in a["sample"])), 12)

    def test_small_count_more_slots_and_no_zero_id(self):
        plan = swarm.create_plan(count=2, slots=8, sample=8)
        self.assertEqual([p["agent_count"] for p in plan["partitions"]], [1, 1, 0, 0, 0, 0, 0, 0])
        self.assertEqual([p["first_zero_based_id"] for p in plan["partitions"]], [0, 1, -1, -1, -1, -1, -1, -1])
        self.assertEqual(len(plan["sample"]), 2)

    def test_reject_invalid_counts_slots_samples(self):
        for kwargs in (
            {"count": 0}, {"count": 100_000_000}, {"count": True},
            {"slots": 0}, {"slots": 65}, {"slots": 1.2},
            {"sample": -1}, {"sample": 65},
        ):
            with self.assertRaises(MirrorError):
                swarm.create_plan(**kwargs)

    def test_reject_untrusted_model_owner(self):
        for name in ("outside/repo", "openai/../bad", "OpenAI/gpt-oss-20b"):
            with self.assertRaises(MirrorError):
                swarm.create_plan(model=name)

    def test_rea_evidence_gates_and_digest(self):
        evidence = {"model": "openai/gpt-oss-20b", "status": "rea-static-inspection", "results": [{"path": "model.safetensors"}]}
        plan = swarm.create_plan(rea_analysis=evidence)
        self.assertEqual(plan["rea_inspection_status"], "inspected-local-model")
        self.assertEqual(len(plan["rea_evidence_sha256"]), 64)
        with self.assertRaises(MirrorError):
            swarm.create_plan(rea_analysis={"model": "openai/other", "status": "rea-static-inspection"})

    def test_no_rea_call_unless_explicit(self):
        output = io.StringIO()
        with patch.object(swarm, "inspect_with_rea", side_effect=AssertionError("unapproved REA execution")):
            with redirect_stdout(output):
                self.assertEqual(swarm.main(["--count", "99999999"]), 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["indexed_virtual_agents"], 99_999_999)

    def test_explicit_rea_inspection_wires_existing_mirror(self):
        evidence = {"model": "openai/gpt-oss-20b", "status": "rea-static-inspection", "results": []}
        output = io.StringIO()
        with patch.object(swarm, "inspect_with_rea", return_value=evidence) as inspect:
            with redirect_stdout(output):
                self.assertEqual(swarm.main(["--inspect-rea", "--count", "100"]), 0)
        self.assertEqual(inspect.call_count, 1)
        self.assertEqual(inspect.call_args.kwargs["max_files"], 16)
        self.assertEqual(json.loads(output.getvalue())["rea_inspection_status"], "inspected-local-model")

    def test_invalid_cli_fails_closed(self):
        output = io.StringIO()
        with redirect_stderr(output):
            self.assertEqual(swarm.main(["--count", "100000000"]), 2)
        self.assertIn("blocked", output.getvalue())

    def test_output_is_local_and_exclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "99m.json"
            with redirect_stdout(io.StringIO()):
                self.assertEqual(swarm.main(["--count", "99999999", "--output", str(path)]), 0)
            saved = json.loads(path.read_text())
            self.assertEqual(saved["indexed_virtual_agents"], 99_999_999)
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(swarm.main(["--output", str(path)]), 2)

    def test_empty_sample(self):
        self.assertEqual(swarm.create_plan(sample=0)["sample"], [])


if __name__ == "__main__":
    unittest.main()
