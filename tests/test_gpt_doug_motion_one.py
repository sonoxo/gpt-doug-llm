"""GPT-DOUG Motion-1: real, offline train/generate smoke tests.

Requires torch and Pillow, no network or model downloads.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import torch
from PIL import Image

from open_video_model.data import CAPTIONS, FolderClipSet, make_training_batch, synthetic_clip
from open_video_model.model import MotionConfig, MotionDiffusion, prompt_tokens, trained_parameter_count
from open_video_model.train import load_checkpoint, train
from open_video_model.generate import render, video_frames


class MotionOneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(2)
        cls.cfg = MotionConfig(frames=4, size=16, width=8, timesteps=4, cond_dim=16, vocab=256)

    def test_stable_tokenizer(self):
        a=prompt_tokens("Red circle moving RIGHT",vocab=256,length=8)
        b=prompt_tokens("red circle moving right",vocab=256,length=8)
        self.assertEqual(a,b)
        self.assertEqual(len(a),8)
        self.assertTrue(all(0 <= n < 256 for n in a))
        with self.assertRaises(ValueError): prompt_tokens("x"*401)

    def test_video_shapes(self):
        cfg=self.cfg
        model=MotionDiffusion(cfg)
        clips,prompts=make_training_batch(cfg,2,0)
        self.assertEqual(clips.shape,(2,3,4,16,16))
        tokens=torch.tensor([prompt_tokens(x,cfg.vocab) for x in prompts],dtype=torch.long)
        loss=model.loss(clips,tokens)
        self.assertTrue(bool(torch.isfinite(loss)))
        loss.backward()
        self.assertTrue(any(p.grad is not None for p in model.parameters()))
        self.assertGreater(trained_parameter_count(model),1000)

    def test_synthetic_motion_is_real(self):
        c=synthetic_clip("red circle moving right",4,16,seed=1)
        self.assertEqual(c.shape,(3,4,16,16))
        self.assertFalse(torch.equal(c[:,0],c[:,-1]))

    def test_denoising_sampling(self):
        model=MotionDiffusion(self.cfg)
        model.eval()
        tokens=torch.tensor([prompt_tokens("red circle moving right",self.cfg.vocab)])
        output=model.sample(tokens,seed=7)
        self.assertEqual(output.shape,(3,4,16,16))
        self.assertTrue(bool(torch.isfinite(output).all()))
        self.assertEqual(len(video_frames(output)),4)

    def test_end_to_end_train_checkpoint_generate_gif(self):
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint=Path(tmp)/"original-model.pt"
            result=train(self.cfg,steps=2,batch_size=1,checkpoint=checkpoint,
                         device_name="cpu",log_every=1)
            self.assertTrue(checkpoint.exists())
            self.assertEqual(result["trained_steps"],2)
            model,payload=load_checkpoint(checkpoint)
            self.assertEqual(payload["config"]["timesteps"],4)
            self.assertEqual(payload["format"],"gpt-doug-motion-1-checkpoint-v1")
            self.assertGreater(trained_parameter_count(model),1000)
            video_path=Path(tmp)/"generated.gif"
            metadata=render(prompt="red circle moving right",output=video_path,
                            checkpoint=checkpoint,device_name="cpu",seed=10)
            self.assertFalse(metadata["preview_not_ml"])
            self.assertEqual(metadata["frames"],4)
            self.assertTrue(video_path.is_file() and video_path.stat().st_size>50)
            with Image.open(video_path) as video:
                self.assertEqual(video.format,"GIF")
                self.assertGreaterEqual(getattr(video,"n_frames",1),1)
            self.assertTrue(video_path.with_suffix(".json").exists())

    def test_synthetic_preview_explicit_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"preview.gif"
            receipt=render(prompt="blue square moving left",output=out,preview=True)
            self.assertTrue(out.exists())
            self.assertTrue(receipt["preview_not_ml"])
            self.assertEqual(receipt["trained_steps"],0)

    def test_generation_requires_training(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                render(prompt="a circle",output=Path(tmp)/"x.gif",
                       checkpoint=Path(tmp)/"missing.pt",device_name="cpu")

    def test_folder_training_clips(self):
        with tempfile.TemporaryDirectory() as tmp:
            scene=Path(tmp)/"take-001"
            (scene/"frames").mkdir(parents=True)
            (scene/"caption.txt").write_text("red circle moving right",encoding="utf-8")
            for i in range(4):
                Image.new("RGB",(16,16),(20+i*20,40,80)).save(scene/"frames"/f"{i:03d}.png")
            source=FolderClipSet(Path(tmp),self.cfg)
            self.assertEqual(len(source),1)
            label,video=source.sample(0)
            self.assertEqual(label,"red circle moving right")
            self.assertEqual(video.shape,(3,4,16,16))

    def test_invalid_size_and_configuration(self):
        with self.assertRaises(ValueError):
            MotionConfig(frames=3).validate()
        with self.assertRaises(ValueError):
            MotionConfig(size=128).validate()
        with self.assertRaises(ValueError):
            MotionConfig(width=9).validate()

    def test_only_original_code_no_network(self):
        repo=Path(__file__).resolve().parents[1]
        for name in ("model.py","data.py","train.py","generate.py","__main__.py"):
            source=(repo/"open_video_model"/name).read_text(encoding="utf-8")
            for forbidden in ("requests.get(","urllib.request.urlopen(","hf_hub_download(","HfApi(","api_key=","subprocess.Popen(", "eval("):
                self.assertNotIn(forbidden,source)


if __name__=="__main__":
    unittest.main()
