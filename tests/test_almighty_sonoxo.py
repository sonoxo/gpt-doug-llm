"""Offline tests for the actual GPT-Almighty Sonoxo trainable masked LM."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import torch
except ImportError as exc:
    # The MLM model is an opt-in dependency, covered by its dedicated CI workflow.
    raise unittest.SkipTest("optional torch dependency not installed: pip install -e .[mlm]") from exc

from gpt_doug_mlm.almighty_sonoxo import (
    AlmightySonoxoMLM, MASK, MODEL_ID, ModelConfig, WordTokenizer,
    fill_mask, load_model, mask_batch, register_as_provider, tokenize, train_model,
)
from gpt_doug_mlm.providers import ProviderRegistry


CORPUS = [
    "the ontology stores evidence with provenance and context .",
    "the ontology links evidence to source identifiers .",
    "the model learns representations from local text .",
    "the model predicts masked tokens using neural weights .",
    "the council reviews proposed model improvements .",
    "the council verifies results before approval .",
    "the operator controls all consequential changes .",
    "the operator can stop model inference immediately .",
    "the language model stores its weights in safetensors .",
    "the neural model predicts missing words from context .",
    "the repository records model versions with provenance .",
    "the evaluation tracks training and validation losses .",
] * 3


def training_data(folder: Path) -> Path:
    source = folder / "corpus.txt"
    source.write_text("\n".join(CORPUS) + "\n", encoding="utf-8")
    return source


class AlmightySonoxoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.tmp.name)
        source = training_data(cls.folder)
        cls.manifest = train_model(
            source, cls.folder / "trained", epochs=3, batch_size=12,
            max_vocab=128, max_len=32, d_model=32, num_heads=4,
            num_layers=1, ff_dim=64, seed=2026,
        )
        cls.model, cls.tokenizer, _ = load_model(cls.folder / "trained")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_mask_token_kept_and_normalized(self):
        self.assertEqual(tokenize("The [mask] IS here."), ["the", MASK, "is", "here", "."])

    def test_vocabulary_has_expected_special_order(self):
        self.assertEqual(self.tokenizer.vocab[:5], ["[PAD]", "[UNK]", MASK, "[CLS]", "[SEP]"])

    def test_network_has_trainable_parameters(self):
        self.assertGreater(self.manifest["training"]["parameters"], 1000)
        self.assertGreater(len(self.model.state_dict()), 5)

    def test_neural_network_output_shape(self):
        x = torch.tensor([[3, 5, 6, 4]], dtype=torch.long)
        out = self.model(x)
        self.assertEqual(list(out.shape), [1, 4, len(self.tokenizer.vocab)])

    def test_training_losses_recorded(self):
        self.assertEqual(len(self.manifest["training"]["train_loss"]), 3)
        self.assertTrue(all(float(x) >= 0 for x in self.manifest["training"]["validation_loss"]))

    def test_weights_saved_and_checksum_validated(self):
        self.assertEqual(self.manifest["model_id"], MODEL_ID)
        self.assertEqual(len(self.manifest["weights_sha256"]), 64)
        self.assertTrue((self.folder / "trained" / "model.safetensors").exists())

    def test_masked_inference_produces_probabilities(self):
        answer = fill_mask(self.model, self.tokenizer, "the [MASK] stores evidence .", 3)
        self.assertEqual(len(answer["candidates"]), 3)
        self.assertTrue(0 <= answer["candidates"][0]["probability"] <= 1)
        self.assertNotIn(answer["candidates"][0]["token"], self.tokenizer.vocab[:5])

    def test_mask_must_be_present_once(self):
        for phrase in ("the model learns", "[MASK] [MASK]"):
            with self.assertRaises(ValueError):
                fill_mask(self.model, self.tokenizer, phrase)

    def test_tokenizer_rejects_bad_vocabulary(self):
        with self.assertRaises(ValueError):
            WordTokenizer(["oops", "x", "y", "z", "w", "t"])

    def test_bad_model_config_rejected(self):
        with self.assertRaises(ValueError):
            AlmightySonoxoMLM(ModelConfig(vocab_size=12, d_model=31, num_heads=4))

    def test_mask_batch_ignores_special_tokens(self):
        batch = torch.tensor([[3, 5, 6, 4, 0]], dtype=torch.long)
        import random
        _, target = mask_batch(batch, vocab_size=12, rng=random.Random(3), probability=0.5)
        self.assertEqual(int(target[0, 0]), -100)
        self.assertEqual(int(target[0, 3]), -100)
        self.assertGreater(int(target.ne(-100).sum()), 0)

    def test_opt_in_provider_bridge(self):
        registry = ProviderRegistry()
        register_as_provider(registry, self.model, self.tokenizer)
        self.assertIn(MODEL_ID, registry.names())
        outcome = json.loads(registry.get(MODEL_ID).propose("the [MASK] learns from data"))
        self.assertEqual(outcome["task"], "masked-token prediction")

    def test_refuse_tampered_checkpoint(self):
        manifest_path = self.folder / "trained" / "manifest.json"
        data = json.loads(manifest_path.read_text())
        data["weights_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as t:
            folder = Path(t)
            (folder / "manifest.json").write_text(json.dumps(data))
            (folder / "model.safetensors").write_bytes((self.folder / "trained" / "model.safetensors").read_bytes())
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                load_model(folder)

    def test_operator_stop_blocks_inference(self):
        with patch.dict(os.environ, {"GPT_DOUG_AI_BLOCK_ALL": "1"}):
            with self.assertRaises(PermissionError):
                fill_mask(self.model, self.tokenizer, "the [MASK] learns from data")

    def test_operator_stop_blocks_training(self):
        with patch.dict(os.environ, {"GPT_DOUG_AI_BLOCK_ALL": "1"}):
            with self.assertRaises(PermissionError):
                train_model(self.folder / "corpus.txt", self.folder / "blocked", epochs=1)


if __name__ == "__main__":
    unittest.main()
