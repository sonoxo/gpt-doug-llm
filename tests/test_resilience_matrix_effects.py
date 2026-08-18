import io
import unittest
from unittest.mock import patch

from resilience_matrix.effects import TerminalFX


class FakeTTY(io.StringIO):
    def isatty(self):
        return True


class TerminalFXTests(unittest.TestCase):
    def test_non_tty_disables_animation(self):
        stream = io.StringIO()
        fx = TerminalFX(enabled=True, stream=stream, sleep=lambda _: None)
        self.assertFalse(fx.enabled)
        fx.boot()
        self.assertEqual(stream.getvalue(), "")

    def test_explicit_disable_wins_on_tty(self):
        stream = FakeTTY()
        fx = TerminalFX(enabled=False, stream=stream, sleep=lambda _: None)
        self.assertFalse(fx.enabled)
        fx.decision()
        self.assertEqual(stream.getvalue(), "")

    def test_tty_phase_emits_stable_completion_line(self):
        stream = FakeTTY()
        fx = TerminalFX(enabled=True, stream=stream, sleep=lambda _: None)
        fx.phase("Checking matrix", frames=2, width=4, final="OK")
        output = stream.getvalue()
        self.assertIn("Checking matrix", output)
        self.assertIn("[OK]", output)
        self.assertIn(TerminalFX.SHOW_CURSOR, output)

    def test_environment_can_disable_animation(self):
        stream = FakeTTY()
        with patch.dict("os.environ", {"RESILIENCE_NO_ANIMATIONS": "1"}, clear=False):
            fx = TerminalFX(enabled=True, stream=stream, sleep=lambda _: None)
        self.assertFalse(fx.enabled)

    def test_3d_scene_uses_alternate_screen_and_restores_terminal(self):
        stream = FakeTTY()
        fx = TerminalFX(
            enabled=True,
            stream=stream,
            sleep=lambda _: None,
            scene_seconds=0.2,
            fps=6,
        )
        fx.scene3d("TEST SCENE")
        output = stream.getvalue()
        self.assertIn(TerminalFX.ALT_SCREEN_ON, output)
        self.assertIn(TerminalFX.ALT_SCREEN_OFF, output)
        self.assertIn(TerminalFX.SHOW_CURSOR, output)
        self.assertIn("TEST SCENE", output)

    def test_live_scene_duration_and_fps_controls(self):
        stream = FakeTTY()
        fx = TerminalFX(enabled=True, stream=stream, sleep=lambda _: None)
        self.assertEqual(fx.set_scene_seconds(7.5), 7.5)
        self.assertEqual(fx.set_fps(30), 30)
        settings = fx.settings()
        self.assertEqual(settings["scene_seconds"], 7.5)
        self.assertEqual(settings["fps"], 30)

    def test_invalid_live_effect_settings_are_rejected(self):
        fx = TerminalFX(enabled=False, stream=FakeTTY(), sleep=lambda _: None)
        with self.assertRaises(ValueError):
            fx.set_scene_seconds(0)
        with self.assertRaises(ValueError):
            fx.set_fps(5)
        with self.assertRaises(ValueError):
            fx.set_fps(61)

    def test_effects_can_be_toggled_on_supported_terminal(self):
        fx = TerminalFX(enabled=True, stream=FakeTTY(), sleep=lambda _: None)
        self.assertTrue(fx.enabled)
        self.assertFalse(fx.set_enabled(False))
        self.assertTrue(fx.set_enabled(True))

    def test_showcase_renders_manual_scene(self):
        stream = FakeTTY()
        fx = TerminalFX(
            enabled=True,
            stream=stream,
            sleep=lambda _: None,
            scene_seconds=0.2,
            fps=6,
        )
        fx.showcase(seconds=0.2)
        output = stream.getvalue()
        self.assertIn("MANUAL EFFECTS SHOWCASE", output)
        self.assertIn("Terminal effects channel", output)


if __name__ == "__main__":
    unittest.main()
