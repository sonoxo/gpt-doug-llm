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


    def test_live_phase_events_match_real_reasoning_stages(self):
        observed = []
        engine = SkullEngine(
            chat_fn=self.fake_chat, memory=self.memory, ontology=self.ontology,
            config=SkullConfig(depth=2),
            on_progress=lambda phase, message: observed.append(phase),
        )
        result = engine.run("Explain the XUNIA ontology")
        self.assertEqual(result.calls, 3)
        self.assertEqual(observed, ["retrieve", "draft", "critique", "revise", "complete"])
        self.assertTrue(result.answer)

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


class TerminalAsciiTests(unittest.TestCase):
    def test_banner_and_network_use_fixed_width_printable_ascii(self):
        from skull_llm.terminal import render_banner, render_network

        for render in (render_banner, render_network):
            output = render(columns=80)
            self.assertTrue(all(len(line) == 80 for line in output.splitlines()))
            self.assertTrue(all(ch == "\n" or 32 <= ord(ch) <= 126 for ch in output))
        self.assertIn("SKULL-LLM", render_banner(columns=80))
        self.assertIn("ORCHESTRATOR", render_network(columns=80))
        self.assertIn("REFERENCE TOPOLOGY", render_network(columns=80))

    def test_dashboard_shows_actual_status_and_never_invents_metrics(self):
        from skull_llm.terminal import render_dashboard

        snapshot = {
            "ollama": {
                "configured": False, "model_available": False,
                "model": "qwen2.5-coder:7b", "message": "Ollama is not running",
            },
            "stopped": True, "pytorch_installed": False,
            "ready_for_inference": False,
        }
        output = render_dashboard(snapshot, columns=80)
        self.assertIn("OLLAMA        : OFFLINE", output)
        self.assertIn("EMERGENCY STOP: ENGAGED", output)
        self.assertIn("MODEL         : qwen2.5-coder:7b", output)
        self.assertIn("TRAINED WEIGHTS: NOT PROVIDED", output)
        self.assertTrue(all(len(line) == 80 for line in output.splitlines()))

    def test_terminal_strips_unsafe_control_characters_from_model_status(self):
        from skull_llm.terminal import render_dashboard

        output = render_dashboard({
            "ollama": {
                "configured": True, "model_available": True,
                "model": "evil\x1b[31m\x00\nmodel",
                "message": "test\x1b[2J\nlog",
            },
            "ready_for_inference": True,
        })
        self.assertNotIn("\x1b", output)
        self.assertNotIn("\x00", output)
        self.assertIn("CORE          : READY", output)

    def test_cli_ascii_modes_are_accessible_without_models(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest.mock import patch

        from skull_llm.cli import main

        for command in ("banner", "portrait", "network"):
            out = StringIO()
            with redirect_stdout(out):
                self.assertEqual(main([command, "--width", "70"]), 0)
            self.assertIn("SKULL-LLM", out.getvalue())
        out = StringIO()
        stub = {
            "ollama": {"configured": False, "model_available": False},
            "stopped": False, "ready_for_inference": False,
        }
        with patch("skull_llm.cli.doctor", return_value=stub), redirect_stdout(out):
            self.assertEqual(main(["dashboard", "--width", "70"]), 0)
        self.assertIn("NOT READY", out.getvalue())


class AnatomicalAsciiTests(unittest.TestCase):
    def test_skull_is_shaded_anatomical_shape(self):
        from skull_llm.anatomy import render_anatomical_skull

        art = render_anatomical_skull(72, 36)
        rows = art.splitlines()
        self.assertEqual(len(rows), 36)
        self.assertTrue(all(len(row) <= 72 for row in rows))
        self.assertTrue(all(32 <= ord(char) <= 126 for char in art if char != "\n"))
        self.assertGreater(len(set("".join(rows)) - {" "}), 5, "shading must have depth")
        self.assertIn(" ", rows[16], "orbital sockets must be recessed")
        self.assertTrue(rows[-1].strip(), "lower jaw should be visible")
        self.assertNotIn("\x1b", art)

    def test_procedural_portrait_and_banner_fit_narrow_terminals(self):
        from skull_llm.terminal import render_banner, render_dashboard, render_portrait

        for width in (42, 72, 100):
            for output in (
                render_banner(columns=width),
                render_portrait(columns=width),
                render_dashboard({"ollama": {}, "stopped": False}, columns=width),
            ):
                self.assertTrue(all(len(line) == width for line in output.splitlines()))
                self.assertNotIn("\x1b", output)
        self.assertIn("PROCEDURAL ANATOMY", render_portrait(columns=80))

    def test_bad_dimensions_are_rejected(self):
        from skull_llm.anatomy import render_anatomical_skull, render_photo_ascii

        with self.assertRaises(ValueError):
            render_anatomical_skull(width=17)
        with self.assertRaises(ValueError):
            render_anatomical_skull(width=70, height=65)
        with self.assertRaises(ValueError):
            render_photo_ascii("not-a-real-file.png", width=300)

    def test_photo_ascii_optional_pillow(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("optional Pillow not installed")
        from skull_llm.anatomy import render_photo_ascii

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bone.png"
            image = Image.new("L", (80, 80), color=180)
            image.putpixel((40, 40), 0)
            image.save(path)
            art = render_photo_ascii(str(path), width=50)
            self.assertEqual(len(art.splitlines()), 26)
            self.assertTrue(all(len(line) <= 50 for line in art.splitlines()))
            self.assertNotIn("\x1b", art)


if __name__ == "__main__":
    unittest.main()
