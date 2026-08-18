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


if __name__ == "__main__":
    unittest.main()
