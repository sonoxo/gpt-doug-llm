"""Motion-1 v2 revamp tests: stdlib-first startup, telemetry and browser controls.

Everything here runs without network access or model downloads.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


class MotionRevampTests(unittest.TestCase):
    def test_studio_is_importable_without_third_party_site_packages(self):
        code = """
import sys
from open_video_model import studio
from open_video_model.__main__ import parse
assert 'torch' not in sys.modules
assert 'PIL' not in sys.modules
assert parse(['studio']).command == 'studio'
assert studio.MotionHandler is not None
"""
        result = subprocess.run(
            [sys.executable, "-S", "-c", code],
            cwd=ROOT, capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_local_http_starts_in_clean_stdlib_environment(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        code = (
            "import webbrowser; webbrowser.open=lambda *a, **k: False;"
            "from open_video_model.__main__ import main;"
            f"main(['studio','--port','{port}'])"
        )
        proc = subprocess.Popen(
            [sys.executable, "-S", "-c", code],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        try:
            response = None
            for _ in range(60):
                if proc.poll() is not None:
                    break
                try:
                    with urlopen(f"http://127.0.0.1:{port}/api/health", timeout=.35) as request:
                        response = json.load(request)
                    break
                except OSError:
                    time.sleep(.1)
            if response is None:
                stdout, stderr = proc.communicate(timeout=2)
                self.fail(f"Studio failed to start with stdlib Python. {stdout} {stderr}")
            self.assertTrue(response["local"])
            self.assertIn(response["pipeline"]["stage"],
                          {"not-started", "installing", "training", "ready", "failed"})
            with urlopen(f"http://127.0.0.1:{port}/", timeout=2) as request:
                body = request.read().decode("utf-8")
            self.assertIn('id="demoCanvas"', body)
        finally:
            if proc.poll() is None:
                proc.terminate()
            try:
                proc.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate(timeout=2)

    def test_status_parses_training_counters_without_exposing_logs(self):
        from open_video_model import studio
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            state = base / "setup-status"
            log = base / "training.log"
            checkpoint = base / "not-ready.pt"
            state.write_text("training\n", encoding="utf-8")
            log.write_text(
                "some private log data\n"
                "GPT-DOUG Motion-1 | 25/500 | loss=0.99100 | device=cpu\n"
                "GPT-DOUG Motion-1 | 50/500 | loss=0.85420 | device=cpu\n",
                encoding="utf-8"
            )
            with patch.object(studio, "STATUS_FILE", state), \
                 patch.object(studio, "TRAIN_LOG", log), \
                 patch.object(studio, "DEFAULT_CHECKPOINT", checkpoint):
                info = studio.pipeline_status()
            self.assertEqual(info, {"stage": "training",
                                    "completed_steps": 50, "total_steps": 500})
            self.assertNotIn("private log data", json.dumps(info))

    def test_bootstrap_is_non_destructive_and_scripts_parse(self):
        paths = ["bootstrap_mac.sh", "run_mac.sh", "setup_mac.sh"]
        for name in paths:
            path = ROOT / "open_video_model" / name
            self.assertTrue(path.exists())
            result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        bootstrap = (ROOT / "open_video_model/bootstrap_mac.sh").read_text(encoding="utf-8")
        self.assertIn('if [[ -e "$candidate" || -L "$candidate" ]]', bootstrap)
        self.assertIn('git clone --depth 1', bootstrap)
        self.assertNotIn("rm -rf", bootstrap)
        self.assertNotIn("sudo", bootstrap)
        self.assertIn("open_video_model/run_mac.sh", bootstrap)

    def test_browser_demo_is_honestly_labeled_and_download_is_wired(self):
        html = (ROOT / "docs/motion-1/index.html").read_text(encoding="utf-8")
        js = (ROOT / "docs/motion-1/app.js").read_text(encoding="utf-8")
        css = (ROOT / "docs/motion-1/style.css").read_text(encoding="utf-8")
        for selector in ('id="demo"', 'id="demoCanvas"', 'id="download"',
                         'id="trainProgress"', 'id="stageText"'):
            self.assertIn(selector, html)
        self.assertIn("LIVE PROCEDURAL CANVAS / NOT AI VIDEO", js)
        self.assertIn('link.download=', js)
        self.assertIn('pipeline.stage', js)
        self.assertIn(".livebar", css)
        self.assertIn("bootstrap_mac.sh", html)


if __name__ == "__main__":
    unittest.main()
