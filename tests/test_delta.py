"""Actual CPU tests for GPT-Delta: frozen base, low-rank training, safety gates."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch

from gpt_doug_mlm.almighty_sonoxo import load_model, train_model
from gpt_doug_mlm.delta import (
    DeltaAdapter, DeltaConfig, fill_delta, load_delta, promote_delta,
    rollback_delta, train_delta,
)
from gpt_doug_mlm.delta_evidence import observe_change
from gpt_doug_mlm.delta_cli import main as delta_main


BASE = [
    "the ontology stores evidence with provenance .",
    "the model learns from local text with provenance .",
    "the model predicts missing words with context .",
    "the council verifies evidence before approval .",
    "the operator reviews model evidence and results .",
    "the operator controls model changes and safety .",
    "the source records evidence with provenance .",
    "the ontology links research with source identifiers .",
    "the model trains on source data with provenance .",
    "the neural model stores learned weights with provenance .",
    "the evaluation reviews training and validation losses .",
    "the council stores its research results with provenance .",
] * 3

NEW = [
    "the ontology stores evidence with provenance .",
    "the ontology stores research evidence with provenance .",
    "the ontology stores model results with provenance .",
    "the ontology stores safety evidence with provenance .",
    "the ontology stores source identifiers with provenance .",
    "the ontology stores context and evidence with provenance .",
    "the ontology stores training data with provenance .",
    "the ontology stores evaluation results with provenance .",
] * 3


class DeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        cls.root = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.root.name)
        cls.base_corpus = cls.folder / "base_corpus.txt"
        cls.new_corpus = cls.folder / "new_corpus.txt"
        cls.base_corpus.write_text("\n".join(BASE) + "\n", encoding="utf-8")
        cls.new_corpus.write_text("\n".join(NEW) + "\n", encoding="utf-8")
        cls.base = cls.folder / "base"
        train_model(cls.base_corpus, cls.base, epochs=2, d_model=32,
                    num_layers=1, num_heads=4, ff_dim=64, max_vocab=128,
                    max_len=32, batch_size=12, seed=123)
        cls.candidate = cls.folder / "candidate"
        cls.manifest = train_delta(cls.base, cls.new_corpus, cls.candidate,
                                   replay=cls.base_corpus, epochs=2,
                                   learning_rate=0.002, rank=4, seed=123)

    @classmethod
    def tearDownClass(cls):
        cls.root.cleanup()

    def test_real_frozen_parent_and_small_adaptation(self):
        model, _, _ = load_delta(self.base, self.candidate)
        self.assertTrue(all(not p.requires_grad for p in model.parent.parameters()))
        self.assertTrue(all(p.requires_grad for p in model.adapter_parameters()))
        self.assertGreater(self.manifest["training"]["adapter_parameters"], 0)
        self.assertLess(self.manifest["training"]["adapter_parameters"], 10000)

    def test_initial_residual_is_identically_zero(self):
        parent, tok, _ = load_model(self.base)
        adapter = DeltaAdapter(parent, DeltaConfig(rank=4))
        x = torch.tensor([tok.encode("the ontology stores evidence .", 32)], dtype=torch.long)
        with torch.no_grad():
            self.assertTrue(torch.allclose(parent(x), adapter(x), atol=1e-5))

    def test_training_is_real_and_updates_parameters(self):
        model, tok, _ = load_delta(self.base, self.candidate)
        self.assertGreater(float(model.up.weight.detach().abs().sum()), 0)
        x = torch.tensor([tok.encode("the ontology stores [MASK] with provenance", 32)], dtype=torch.long)
        self.assertEqual(list(model(x).shape), [1, x.size(1), len(tok.vocab)])

    def test_training_does_not_mutate_parent_weights(self):
        original = json.loads((self.base / "manifest.json").read_text())
        self.assertEqual(self.manifest["parent_weights_sha256"], original["weights_sha256"])
        self.assertEqual((self.base / "model.safetensors").is_file(), True)

    def test_candidate_remains_unpromoted(self):
        self.assertEqual(self.manifest["status"], "candidate-not-promoted")
        self.assertFalse((self.candidate / "active.json").exists())
        self.assertEqual(len(self.manifest["training"]["loss_history"]), 2)
        self.assertIn("independent_replay", self.manifest["evaluation"]["gates"])

    def test_mask_prediction_on_real_adapter(self):
        result = fill_delta(self.base, self.candidate, "the ontology stores [MASK] with provenance", 3)
        self.assertEqual(result["model_id"], "gpt-delta-mlm-sagiqi")
        self.assertEqual(len(result["candidates"]), 3)
        self.assertLessEqual(sum(v["probability"] for v in result["candidates"]), 1.001)

    def test_inference_requires_exactly_one_mask(self):
        with self.assertRaises(ValueError):
            fill_delta(self.base, self.candidate, "there is no masked token")
        with self.assertRaises(ValueError):
            fill_delta(self.base, self.candidate, "[MASK] and [MASK]")

    def test_tampered_adapter_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            clone = Path(folder)
            shutil.copyfile(self.candidate / "manifest.json", clone / "manifest.json")
            payload = (self.candidate / "adapter.safetensors").read_bytes()
            (clone / "adapter.safetensors").write_bytes(payload + b"tampering")
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                load_delta(self.base, clone)

    def test_parent_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            clone = Path(folder)
            shutil.copyfile(self.candidate / "adapter.safetensors", clone / "adapter.safetensors")
            manifest = json.loads((self.candidate / "manifest.json").read_text())
            manifest["parent_weights_sha256"] = "0" * 64
            (clone / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "parent checkpoint mismatch"):
                load_delta(self.base, clone)

    def test_invalid_rank_rejected(self):
        parent, _, _ = load_model(self.base)
        with self.assertRaises(ValueError):
            DeltaAdapter(parent, DeltaConfig(rank=0))
        with self.assertRaises(ValueError):
            DeltaAdapter(parent, DeltaConfig(rank=50))

    def test_no_replay_always_blocks_review_eligibility(self):
        with tempfile.TemporaryDirectory() as folder:
            result = train_delta(self.base, self.new_corpus, folder, epochs=1, rank=2)
        self.assertFalse(result["evaluation"]["gates"]["replay_provided"])
        self.assertFalse(result["evaluation"]["eligible_for_review"])

    def test_explicit_operator_approval_needed(self):
        with self.assertRaises(PermissionError):
            promote_delta(self.base, self.candidate, self.folder / "no.json")
        self.assertFalse((self.folder / "no.json").exists())

    def test_promotion_must_have_original_evaluation_data(self):
        with self.assertRaisesRegex(ValueError, "independent replay"):
            promote_delta(self.base, self.candidate, self.folder / "no.json", approve=True)
        fake = self.folder / "wrong.txt"
        fake.write_text("unrelated corpus from other sources\n" * 12)
        with self.assertRaisesRegex(ValueError, "do not match"):
            promote_delta(self.base, self.candidate, self.folder / "no.json",
                          corpus=self.new_corpus, replay=fake, approve=True)

    def test_rollback_restores_local_pointer_without_deployment(self):
        filename = self.folder / "pointer.json"
        filename.write_text(json.dumps({
            "schema": "sonoxo.delta-pointer.v1",
            "active_candidate": str(self.candidate), "history": [],
            "operator_approved": True,
        }))
        with self.assertRaises(PermissionError):
            rollback_delta(filename)
        result = rollback_delta(filename, approve=True)
        self.assertIsNone(result["active_candidate"])
        self.assertFalse(result["deployment_performed"])

    def test_s_brain_new_duplicate_and_changed(self):
        with tempfile.TemporaryDirectory() as folder:
            db = str(Path(folder) / "events.sqlite3")
            event = dict(database=db, subject="Study NCT00000000", predicate="recruitment",
                         source_id="registry", source_uri="https://clinicaltrials.gov")
            fresh = observe_change(**event, value="recruiting")
            duplicate = observe_change(**event, value="recruiting")
            change = observe_change(**event, value="suspended")
            self.assertEqual((fresh["event"], duplicate["event"], change["event"]),
                             ("new", "duplicate", "changed"))
            self.assertTrue(change["material"])
            self.assertTrue(change["contradictory_values"])
            self.assertFalse(change["independently_verified"])

    def test_standalone_sqlite_fallback_when_s_brain_not_installed(self):
        import sys
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(sys.modules, {"gpt_brain.s_brain": None}):
                db = Path(folder) / "fallback.sqlite3"
                kwargs = dict(database=db, subject="NCT-TEST", predicate="recruitment",
                              source_id="registry", source_uri="local:snapshot")
                self.assertEqual(observe_change(**kwargs, value="recruiting")["event"], "new")
                self.assertEqual(observe_change(**kwargs, value="recruiting")["event"], "duplicate")
                change = observe_change(**kwargs, value="suspended")
                self.assertEqual(change["event"], "changed")
                self.assertEqual(change["backend"], "standalone-sqlite")
                self.assertFalse(change["independently_verified"])

    def test_secrets_rejected_by_s_brain(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "secret-like"):
                observe_change(database=Path(folder) / "s.sqlite", subject="secret",
                               predicate="token", value="api_key=abcdefghijklmnop123456789",
                               source_id="source", source_uri="local:test")

    def test_emergency_stop_blocks_training_inference_and_evidence(self):
        with patch.dict(os.environ, {"GPT_DOUG_AI_BLOCK_ALL": "1"}):
            with self.assertRaises(PermissionError):
                fill_delta(self.base, self.candidate, "the [MASK] source")
            with self.assertRaises(PermissionError):
                train_delta(self.base, self.new_corpus, self.folder / "blocked")
            with self.assertRaises(PermissionError):
                observe_change(database=self.folder / "blocked.sqlite", subject="study",
                               predicate="status", value="active", source_id="registry",
                               source_uri="local:registry")

    def test_cli_help_does_not_download_models(self):
        with self.assertRaises(SystemExit) as ctx:
            delta_main(["--help"])
        self.assertEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
