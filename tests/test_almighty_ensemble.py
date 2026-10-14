"""Registered multi-model council tests. No network or tokens are used."""
from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from gpt_doug_mlm.almighty_ensemble import SonoxoModelCouncil, Source, register_local_ollama
from gpt_doug_mlm.providers import CallableProvider, ProviderRegistry


class CouncilTests(unittest.TestCase):
    def setUp(self):
        self.registry = ProviderRegistry()
        self.registry.register(CallableProvider("model-a", lambda text: "proposal a", lambda text: "review a"))
        self.registry.register(CallableProvider("model-b", lambda text: "proposal b", lambda text: "review b"))
        self.council = SonoxoModelCouncil(self.registry)
        self.sources = [Source("trial-1", "Trial protocol amendment was posted", "registry:2026-10-14")]

    def test_multi_model_proposal_and_review(self):
        x = self.council.evaluate("Review trial amendment", proposer_models=["model-a", "model-b"], reviewer_models=["model-b"], evidence=self.sources)
        self.assertTrue(x["all_proposers_returned"])
        self.assertEqual(set(x["proposals"]), {"model-a", "model-b"})
        self.assertEqual(x["reviews"]["model-b"]["output"], "review b")
        self.assertEqual(x["source_ids"], ["trial-1"])
        self.assertFalse(x["external_actions_performed"])

    def test_repeatable_evidence_digest(self):
        kw = dict(proposer_models=["model-a"], evidence=self.sources)
        a = self.council.evaluate("Test", **kw)
        b = self.council.evaluate("Test", **kw)
        self.assertEqual(a["evidence_packet_sha256"], b["evidence_packet_sha256"])

    def test_unregistered_model_denied(self):
        with self.assertRaisesRegex(ValueError, "registered"):
            self.council.evaluate("Task", proposer_models=["unknown"])

    def test_duplicate_models_denied(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            self.council.evaluate("Task", proposer_models=["model-a", "model-a"])

    def test_evidence_requires_provenance(self):
        with self.assertRaises(ValueError):
            self.council.evaluate("Task", proposer_models=["model-a"], evidence=[Source("id", "some data", "")])

    def test_external_actions_not_exposed(self):
        x = self.council.evaluate("Task", proposer_models=["model-a"])
        self.assertFalse(x["self_modification_performed"])
        self.assertIn("unverified", x["fact_verification"])

    def test_operator_stop_blocks_council(self):
        with patch.dict(os.environ, {"GPT_DOUG_AI_BLOCK_ALL": "1"}):
            with self.assertRaises(PermissionError):
                self.council.evaluate("Task", proposer_models=["model-a"])

    def test_local_ollama_requires_opt_in(self):
        with patch.dict(os.environ, {"GPT_DOUG_PROVIDER": "none"}):
            with self.assertRaises(RuntimeError):
                register_local_ollama(self.registry, ["fake-model"])

    def test_failing_provider_is_recorded(self):
        def fails(prompt):
            raise OSError("no provider")
        self.registry.register(CallableProvider("broken", fails, fails))
        result = self.council.evaluate("Task", proposer_models=["broken"])
        self.assertEqual(result["proposals"]["broken"]["status"], "failed:OSError")
        self.assertFalse(result["all_proposers_returned"])


if __name__ == "__main__":
    unittest.main()
