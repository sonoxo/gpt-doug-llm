"""Offline Mac launcher regression: local studio starts before model training completes.

Mocks Python locally; does not install packages, train a model, or make network calls.
"""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "open_video_model/run_mac.sh"


class MacLauncherTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.home = Path(self.work.name)
        self.repo = self.home / "motion-source"
        (self.repo / "open_video_model/.venv/bin").mkdir(parents=True)
        shutil.copyfile(LAUNCHER, self.repo / "open_video_model/run_mac.sh")
        bin_dir = self.home / "fakebin"
        bin_dir.mkdir()
        py312 = bin_dir / "python3.12"
        py312.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        py312.chmod(0o755)
        stub = self.repo / "open_video_model/.venv/bin/python"
        stub.write_text(
            """#!/bin/sh
case "$1" in
  -c) exit 0 ;;
  -m)
    case "$3" in
      train)
        touch "$HOME/train.started"
        sleep 3
        touch "$HOME/train.finished"
        exit 0
        ;;
      studio)
        touch "$HOME/studio.started"
        if [ -f "$HOME/train.finished" ]; then
          touch "$HOME/studio.started.after.training"
        fi
        exit 0
        ;;
    esac
    ;;
esac
exit 13
""", encoding="utf-8"
        )
        stub.chmod(0o755)
        self.env = dict(os.environ)
        self.env.update(HOME=str(self.home), PATH=str(bin_dir) + os.pathsep + self.env.get("PATH", ""),
                        MOTION_TRAIN_STEPS="2")

    def launch(self, overrides=None):
        env={**self.env,**(overrides or {})}
        return subprocess.run(["bash",str(self.repo / "open_video_model/run_mac.sh")],
                              cwd=self.repo,env=env,capture_output=True,text=True,timeout=12)

    def test_local_studio_starts_before_background_training_finishes(self):
        result=self.launch()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue((self.home/"studio.started").exists())
        self.assertTrue((self.home/"train.started").exists())
        self.assertFalse((self.home/"studio.started.after.training").exists())
        self.assertFalse((self.home/"train.finished").exists())
        self.assertIn("Launching free local studio",result.stdout)

    def test_autotrain_opt_out_still_launches_server(self):
        result=self.launch({"MOTION_AUTOTRAIN":"0"})
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue((self.home/"studio.started").exists())
        self.assertFalse((self.home/"train.started").exists())

    def test_invalid_training_budget_fails_closed(self):
        result=self.launch({"MOTION_TRAIN_STEPS":"-1"})
        self.assertEqual(result.returncode,2)
        self.assertFalse((self.home/"studio.started").exists())

    def test_recovery_documentation_does_not_overwrite_non_git_folder(self):
        docs=(ROOT/"open_video_model/README.md").read_text(encoding="utf-8")
        page=(ROOT/"docs/motion-1/index.html").read_text(encoding="utf-8")
        self.assertIn('if [ -d "$HOME/gpt-doug-llm/.git" ]',docs)
        self.assertIn('git clone https://github.com/sonoxo/gpt-doug-llm.git "$HOME/GPT-DOUG-Motion1"',docs)
        self.assertIn('if [ -d "$HOME/gpt-doug-llm/.git" ]',page)
        self.assertIn("checkAgain()", (ROOT/"docs/motion-1/app.js").read_text(encoding="utf-8"))


if __name__=="__main__":
    unittest.main()
