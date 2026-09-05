import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import engine


def _config(tmp_path: Path) -> engine.StudioConfig:
    return engine.StudioConfig(
        backend="mlx",
        wan_repo=tmp_path,
        wan_model=tmp_path,
        mlx_model="test",
        mlxgen_bin="mlxgen",
        mmaudio_repo=tmp_path,
        python_bin="python",
        ffmpeg_bin="ffmpeg",
    )


class BrowserExportTests(unittest.TestCase):
    def test_browser_export_rejects_missing_source(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(RuntimeError, "did not create a usable file"):
                engine.make_browser_playable(_config(root), root / "missing.mp4", root / "final.mp4")

    def test_browser_export_uses_compatible_mp4_settings(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "model-output.mp4"
            output = root / "final.mp4"
            source.write_bytes(b"generated video")
            calls = []

            def fake_run(command, cwd=None):
                calls.append(command)
                Path(command[-1]).write_bytes(b"browser video")
                return "ok"

            with patch.object(engine, "_run", side_effect=fake_run):
                engine.make_browser_playable(_config(root), source, output)

            command = calls[0]
            self.assertEqual(command[command.index("-c:v") + 1], "libx264")
            self.assertEqual(command[command.index("-pix_fmt") + 1], "yuv420p")
            self.assertEqual(command[command.index("-movflags") + 1], "+faststart")
            self.assertEqual(command[command.index("-c:a") + 1], "aac")
            self.assertEqual(output.read_bytes(), b"browser video")

    def test_single_shot_is_transcoded_instead_of_blindly_copied(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "shot.mp4"
            output = root / "final.mp4"
            source.write_bytes(b"unsupported codec")
            called = []

            def fake_make_browser_playable(cfg, src, dst):
                called.append((src, dst))
                dst.write_bytes(b"compatible codec")

            with patch.object(engine, "make_browser_playable", side_effect=fake_make_browser_playable):
                engine.concat_videos(_config(root), [source], output)

            self.assertEqual(called, [(source, output)])
            self.assertEqual(output.read_bytes(), b"compatible codec")


if __name__ == "__main__":
    unittest.main()
