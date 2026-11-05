"""Offline SKULL-LLM regression tests: no API keys, paid services or model weights."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from gpt_brain.memory import BrainMemory
from gpt_brain.ontology import OntologyIndex
from skull_llm.runtime import SkullConfig, SkullEngine

try:
    import torch
except ImportError:
    torch = None


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.memory = BrainMemory(root / "memory.jsonl")
        ontology = root / "ontology.json"
        ontology.write_text(json.dumps({"domain": {"system": "XUNIA ontology"}}))
        self.ontology = OntologyIndex(ontology)
        self.calls = []

    def fake_chat(self, messages, model, options):
        self.calls.append((messages, model, options))
        prompt = messages[0]["content"]
        if "Audit the draft" in prompt:
            content = "Check uncertain claims; do not report tests as executed."
        elif "Rewrite the answer" in prompt:
            content = "Revised, appropriately qualified answer."
        elif "execution plan" in prompt:
            content = "Make a plan and verify assumptions."
        else:
            content = "Initial answer."
        return {"message": {"role": "assistant", "content": content}, "done": True}

    def engine(self, **config):
        return SkullEngine(
            chat_fn=self.fake_chat, memory=self.memory,
            ontology=self.ontology, config=SkullConfig(**config),
        )

    def test_depth_two_uses_three_bounded_model_calls(self):
        self.memory.add("semantic", "XUNIA memory", provenance="test:document")
        result = self.engine(depth=2).run("Explain XUNIA system")
        self.assertEqual(result.calls, 3)
        self.assertEqual(len(self.calls), 3)
        self.assertIn("Revised", result.answer)
        self.assertTrue(result.provenance)
        self.assertGreaterEqual(result.ontology_hits, 1)
        self.assertEqual(len(self.memory.records()), 1, "No implicit memory writes")

    def test_depth_three_planning(self):
        result = self.engine(depth=3).run("Explain XUNIA system")
        self.assertEqual(result.calls, 4)
        self.assertIn("VERIFICATION PLAN", self.calls[1][0][1]["content"])

    def test_depth_one_one_call(self):
        result = self.engine(depth=1).run("Simple question")
        self.assertEqual(result.calls, 1)
        self.assertIsNone(result.critique)

    def test_opt_in_memory(self):
        self.engine(depth=1, remember=True).run("Make a plan")
        self.assertEqual(self.memory.records()[0]["provenance"], "skull-llm:local-session")

    def test_bad_depth_and_empty_task(self):
        with self.assertRaises(ValueError):
            SkullConfig(depth=99)
        with self.assertRaises(ValueError):
            self.engine().run(" ")

    def test_backend_error_fails_visibly(self):
        engine = SkullEngine(
            chat_fn=lambda *_: {"error": "model_unavailable"},
            memory=self.memory, ontology=self.ontology,
        )
        with self.assertRaisesRegex(RuntimeError, "model_unavailable"):
            engine.run("test")


@unittest.skipUnless(torch is not None, "optional PyTorch not installed")
class NeuralTests(unittest.TestCase):
    def test_causal_logits_and_backpropagation(self):
        from skull_llm.neural import NeuralConfig, SkullTransformer

        torch.manual_seed(5)
        model = SkullTransformer(NeuralConfig(dim=32, layers=1, heads=4, max_seq_len=16))
        model.eval()
        a = torch.tensor([[10, 20, 30, 40]])
        b = torch.tensor([[10, 20, 30, 41]])
        with torch.no_grad():
            logits_a, _ = model(a)
            logits_b, _ = model(b)
        self.assertTrue(torch.allclose(logits_a[:, :-1], logits_b[:, :-1], atol=1e-5))
        logits, loss = model(a, a)
        self.assertEqual(tuple(logits.shape), (1, 4, 256))
        self.assertIsNotNone(loss)
        loss.backward()
        self.assertTrue(torch.isfinite(loss))
        self.assertGreater(model.parameter_count(), 0)

    def test_training_checkpoint_and_sampling(self):
        from skull_llm.train import sample_file, train_file

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "text.txt").write_text("SKULL XUNIA GPT DOUG. " * 10)
            result = train_file(
                str(root / "text.txt"), str(root / "model.pt"),
                steps=2, batch_size=2, context=8, dim=32,
                layers=1, heads=4, device="cpu",
            )
            self.assertTrue((root / "model.pt").is_file())
            self.assertEqual(result["training_steps"], 2)
            self.assertFalse(result["pretrained"])
            sample = sample_file(str(root / "model.pt"), "SKULL", new_tokens=4)
            self.assertTrue(sample.startswith("SKULL"))


if __name__ == "__main__":
    unittest.main()
