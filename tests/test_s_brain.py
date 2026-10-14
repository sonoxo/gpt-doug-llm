"""Offline regression suite for the Sonoxo S-Brain memory and model bridges."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gpt_brain.s_brain import Evidence, SBrain


class FakeOntology:
    def __init__(self, hits=None):
        self.hits = hits or []
        self.queries = []

    def search(self, query, limit=8):
        self.queries.append(query)
        return self.hits[:limit]


class SBrainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "memory.sqlite3"
        self.ontology = FakeOntology()
        self.brain = SBrain(self.db, ontology=self.ontology)
        self.addCleanup(self.brain.close)

    @staticmethod
    def fact(**change):
        values = dict(subject="NCT001", predicate="recruitment", value="recruiting",
                      source_id="ctgov-2026", source_uri="https://clinicaltrials.gov/study/NCT001",
                      observed_at="2026-10-14T12:00:00Z", confidence=0.85)
        values.update(change)
        return Evidence(**values)

    def test_01_durable_and_provenance(self):
        self.brain.remember(self.fact())
        result = self.brain.query("NCT001 recruitment")
        self.assertEqual(result["evidence"][0]["source_id"], "ctgov-2026")
        self.assertIn("source_id=ctgov-2026", result["answer"])
        self.assertFalse(result["independent_fact_verification"])

    def test_02_restart_preserves_hash(self):
        record = self.brain.remember(self.fact())
        with SBrain(self.db, ontology=FakeOntology()) as second:
            rows = second.query("NCT001")["evidence"]
            self.assertEqual(rows[0]["evidence_id"], record["id"])

    def test_03_exact_deduplication(self):
        first = self.brain.remember(self.fact())
        second = self.brain.remember(self.fact())
        self.assertTrue(first["inserted"])
        self.assertFalse(second["inserted"])
        self.assertEqual(self.brain.heartbeat()["records"], 1)

    def test_04_preserves_different_observation_time(self):
        self.brain.remember(self.fact())
        self.brain.remember(self.fact(observed_at="2026-10-15T12:00:00Z"))
        self.assertEqual(self.brain.heartbeat()["records"], 2)

    def test_05_same_time_conflict_requires_review(self):
        self.brain.remember(self.fact())
        self.brain.remember(self.fact(value="suspended", source_id="sponsor", source_uri="sponsor-report"))
        conflicts = self.brain.query("NCT001 recruitment")["disagreements"]
        self.assertEqual(conflicts[0]["type"], "same-time-conflict")
        self.assertFalse(conflicts[0]["independently_resolved"])

    def test_06_status_change_is_not_mislabelled_simultaneous_conflict(self):
        self.brain.remember(self.fact())
        self.brain.remember(self.fact(value="completed", observed_at="2026-10-15T12:00:00Z"))
        self.assertEqual(self.brain.query("NCT001")["disagreements"][0]["type"],
                         "possible-status-or-value-transition")

    def test_07_rejects_secrets_without_writing(self):
        with self.assertRaises(ValueError):
            self.brain.remember(self.fact(value="password=123456789abcd"))
        self.assertEqual(self.brain.heartbeat()["records"], 0)

    def test_08_rejects_secrets_in_metadata(self):
        with self.assertRaises(ValueError):
            self.brain.remember(self.fact(metadata={"credential": "api_key=0123456789abcdef"}))

    def test_09_rejects_invalid_confidence(self):
        for confidence in [-0.1, 1.1, float("nan"), float("inf")]:
            with self.subTest(confidence=confidence), self.assertRaises(ValueError):
                self.brain.remember(self.fact(confidence=confidence))

    def test_10_rejects_naive_timestamps(self):
        with self.assertRaises(ValueError):
            self.brain.remember(self.fact(observed_at="2026-10-14T12:00:00"))

    def test_11_rejects_empty_required_fields(self):
        with self.assertRaises(ValueError):
            self.brain.remember(self.fact(source_id=""))

    def test_12_rejects_oversized_content(self):
        with self.assertRaises(ValueError):
            self.brain.remember(self.fact(value="x" * 2401))

    def test_13_ontology_first_even_when_memory_empty(self):
        self.ontology.hits = [{"path": "$.medical.cancer", "value": "oncology", "score": 1.0}]
        result = self.brain.query("oncology")
        self.assertTrue(result["ontology_first"])
        self.assertEqual(self.ontology.queries, ["oncology"])
        self.assertEqual(result["ontology_hits"][0]["path"], "$.medical.cancer")

    def test_14_missing_source_does_not_invent_answer(self):
        result = self.brain.query("unknown molecular biomarker")
        self.assertIn("Insufficient", result["answer"])
        self.assertEqual(result["evidence"], [])

    def test_15_result_bounds_and_ranking(self):
        for n in range(7):
            self.brain.remember(self.fact(value=f"recruiting cohort {n}"))
        self.assertEqual(len(self.brain.query("recruitment", limit=3)["evidence"]), 3)
        with self.assertRaises(ValueError):
            self.brain.query("status", limit=100)

    def test_16_status_is_local_read_only(self):
        self.brain.remember(self.fact())
        before = self.brain.heartbeat()
        after = self.brain.heartbeat()
        self.assertTrue(before["healthy"])
        self.assertEqual(after["records"], 1)
        self.assertFalse(after["self_modification_performed"])

    def test_17_caller_confidence_is_not_verified_probability(self):
        self.brain.remember(self.fact(confidence=0.99))
        row = self.brain.query("NCT001")["evidence"][0]
        self.assertEqual(row["confidence_basis"], "caller-assessed-not-independent-fact-check")

    def test_18_live_requires_evidence(self):
        with self.assertRaises(ValueError):
            self.brain.ask_live("invisible cancer trial", model_call=lambda *a: {})

    def test_19_live_fake_provider_preserves_sources_and_no_writes(self):
        self.brain.remember(self.fact())
        received = []
        def fake_model(messages, model, options):
            received.append(json.loads(messages[1]["content"]))
            return {"message": {"content": "Reported recruiting [ctgov-2026]; not verified."}}
        result = self.brain.ask_live("NCT001 status", model="fake", model_call=fake_model)
        self.assertEqual(result["model_output_status"], "unverified-model-synthesis")
        self.assertEqual(self.brain.heartbeat()["records"], 1)
        self.assertEqual(received[0]["source_observations"][0]["source_id"], "ctgov-2026")

    def test_20_live_rejects_bad_provider_responses(self):
        self.brain.remember(self.fact())
        for response in [{"error": "offline"}, {}, {"message": {"content": ""}}]:
            with self.subTest(response=response), self.assertRaises(RuntimeError):
                self.brain.ask_live("NCT001", model_call=lambda *a, data=response: data)

    def test_21_council_requires_registry(self):
        self.brain.remember(self.fact())
        with self.assertRaises(ValueError):
            self.brain.council("NCT001", proposers=["test"])

    def test_22_real_provider_registry_opt_in(self):
        from gpt_doug_mlm.providers import ProviderRegistry, CallableProvider
        self.brain.remember(self.fact())
        r = ProviderRegistry()
        r.register(CallableProvider(name="fake-model", propose_fn=lambda _: "proposal only",
                                    review_fn=lambda _: "review only"))
        v = self.brain.council("NCT001", proposers=["fake-model"],
                               reviewers=["fake-model"], registry=r)
        self.assertEqual(v["source_ids"], ["ctgov-2026"])
        self.assertFalse(v["self_modification_performed"])
        self.assertEqual(v["fact_verification"],
                         "not-performed; provider outputs are unverified model text")

    def test_23_unknown_council_model_fails_closed(self):
        from gpt_doug_mlm.providers import ProviderRegistry
        self.brain.remember(self.fact())
        with self.assertRaises(ValueError):
            self.brain.council("NCT001", proposers=["unregistered"],
                               registry=ProviderRegistry())

    def test_24_kill_switch_prevents_write_query_and_live(self):
        self.brain.remember(self.fact())
        with patch.dict(os.environ, {"GPT_DOUG_AI_BLOCK_ALL": "1"}):
            with self.assertRaises(PermissionError):
                self.brain.remember(self.fact(value="new value"))
            with self.assertRaises(PermissionError):
                self.brain.query("NCT001")
            with self.assertRaises(PermissionError):
                self.brain.ask_live("NCT001", model_call=lambda *args: {})

    def test_25_rejects_symlinked_database(self):
        actual = Path(self.tmp.name) / "real.sqlite3"
        actual.write_text("not a database")
        link = Path(self.tmp.name) / "link.sqlite3"
        link.symlink_to(actual)
        with self.assertRaises(ValueError):
            SBrain(link, ontology=FakeOntology())

    def test_26_cli_round_trip(self):
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]),
                   GPT_DOUG_AI_BLOCK_ALL="0")
        root = Path(__file__).resolve().parents[1]
        cmd = [sys.executable, "-m", "gpt_brain.s_brain_cli", "--db", str(self.db)]
        add = subprocess.run(cmd+["remember", "--subject", "NCT005", "--predicate", "phase",
                                  "--value", "phase 3", "--source-id", "registry",
                                  "--source-uri", "https://clinicaltrials.gov/study/NCT005"],
                             cwd=root, env=env, capture_output=True, text=True, check=False)
        self.assertEqual(add.returncode, 0, add.stderr)
        ask = subprocess.run(cmd+["ask", "NCT005"], cwd=root, env=env,
                             capture_output=True, text=True, check=False)
        self.assertEqual(ask.returncode, 0, ask.stderr)
        self.assertEqual(json.loads(ask.stdout)["evidence"][0]["source_id"], "registry")


class SBrainNeuralTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from gpt_doug_mlm.almighty_sonoxo import train_model
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = Path(cls.tmp.name) / "knowledge.sqlite3"
        cls.model = Path(cls.tmp.name) / "checkpoint"
        corpus = Path(cls.tmp.name) / "corpus.txt"
        corpus.write_text("\n".join([
            "the ontology stores evidence with provenance",
            "the neural model predicts masked words",
            "local models learn from licensed sources",
            "observations require trustworthy source attribution",
            "the council reviews uncertain model suggestions",
            "cryptography records have documented evidence",
            "medical study results demand independent verification",
            "software must obey the operator stop signal",
            "the memory index stores immutable source records",
            "a small transformer predicts only missing tokens",
        ]), encoding="utf-8")
        cls.manifest = train_model(corpus, cls.model, epochs=1, batch_size=4,
                                   max_vocab=80, d_model=16, num_heads=4,
                                   num_layers=1, ff_dim=32, max_len=32)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_27_real_trained_mlm_weights(self):
        from gpt_doug_mlm.almighty_sonoxo import MODEL_ID
        with SBrain(self.db, ontology=FakeOntology()) as b:
            result = b.fill_mask(self.model, "the ontology stores [MASK] with provenance")
        self.assertEqual(result["model_id"], MODEL_ID)
        self.assertEqual(result["weights_sha256"], self.manifest["weights_sha256"])
        self.assertEqual(len(result["candidates"]), 5)
        self.assertTrue(result["neural_prediction_only"])

    def test_28_multiple_masks_not_chat(self):
        with SBrain(self.db, ontology=FakeOntology()) as b:
            with self.assertRaises(ValueError):
                b.fill_mask(self.model, "[MASK] and [MASK]", top_k=3)

    def test_29_checkpoint_hash_validation(self):
        from gpt_doug_mlm.almighty_sonoxo import load_model
        manifest = json.loads((self.model / "manifest.json").read_text())
        manifest["weights_sha256"] = "0" * 64
        fake = Path(self.tmp.name) / "tampered"
        fake.mkdir(exist_ok=True)
        (fake / "manifest.json").write_text(json.dumps(manifest))
        (fake / "model.safetensors").write_bytes((self.model / "model.safetensors").read_bytes())
        with self.assertRaises(ValueError):
            load_model(fake)


if __name__ == "__main__":
    unittest.main()
