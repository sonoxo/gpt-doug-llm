"""Deterministic GPT-Orca-LLM tests; no model/network required."""
import unittest

from agents.adaptive_intelligence import Evidence
from agents.gpt_orca_llm import OrcaCouncil, ROLES


class OrcaCouncilTests(unittest.TestCase):
    def test_role_order_and_provenance(self):
        roles = []

        def fake_backend(messages, model=None):
            role = messages[0]["content"].split("'s ")[1].split(".")[0]
            roles.append(role)
            return {"message": {"content": role + " result"}}

        result = OrcaCouncil(backend=fake_backend).run(
            "Summarize a source", [Evidence(source_id="doc-1", text="Source material")]
        )
        self.assertTrue(result.completed)
        self.assertEqual(roles, list(ROLES))
        self.assertEqual(result.evidence_ids, ["doc-1"])
        self.assertEqual(result.answer, "synthesizer result")

    def test_no_backend_stops_safely(self):
        result = OrcaCouncil(backend=lambda messages, model=None: {
            "message": {"content": ""}, "error": "provider_not_configured"
        }).run("Analyze a claim")
        self.assertFalse(result.completed)
        self.assertEqual(len(result.turns), 1)
        self.assertEqual(result.turns[0].error, "provider_not_configured")

    def test_task_limit(self):
        with self.assertRaises(ValueError):
            OrcaCouncil(max_task_chars=3).run("lengthy task")


if __name__ == "__main__":
    unittest.main()
