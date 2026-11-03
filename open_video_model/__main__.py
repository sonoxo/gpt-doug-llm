"""Standalone, free GPT-DOUG Motion-1 local video model CLI."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from .model import MotionConfig, MotionDiffusion, trained_parameter_count
from .train import DEFAULT_CHECKPOINT, select_device, train
from .generate import render


def parse(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="gpt-doug-motion-1", description="Original trainable text-conditioned video diffusion")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Check local PyTorch and MPS, without downloading any model weights")
    studio = sub.add_parser("studio", help="Start free local browser studio, localhost only")
    studio.add_argument("--port", type=int, default=8792)
    builder = sub.add_parser("train", help="Train on local synthetic or authorized video frames")
    builder.add_argument("--steps", type=int, default=500)
    builder.add_argument("--batch", type=int, default=2)
    builder.add_argument("--lr", type=float, default=0.0006)
    builder.add_argument("--frames", type=int, default=8)
    builder.add_argument("--size", type=int, default=32)
    builder.add_argument("--width", type=int, default=24)
    builder.add_argument("--timesteps", type=int, default=48)
    builder.add_argument("--seed", type=int, default=42)
    builder.add_argument("--device", choices=["auto", "cpu", "mps", "cuda"], default="auto")
    builder.add_argument("--data-dir", type=Path, help="Optional authorized local scene folders")
    builder.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    for name in ("generate", "preview"):
        item = sub.add_parser(name, help="Generate from trained weights" if name=="generate" else "Render labeled procedural preview without AI")
        item.add_argument("--prompt", required=True)
        item.add_argument("--out", type=Path, required=True)
        item.add_argument("--seed", type=int, default=42)
        item.add_argument("--fps", type=int, default=8)
        item.add_argument("--device", choices=["auto", "cpu", "mps", "cuda"], default="auto")
        if name=="generate":
            item.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse(argv)
        if args.command == "doctor":
            import platform
            import torch
            model = MotionDiffusion(MotionConfig())
            result = {"name": "GPT-DOUG Motion-1", "license": "MIT implementation",
                      "python": sys.version.split()[0], "torch": torch.__version__,
                      "platform": platform.platform(), "mps_available": bool(torch.backends.mps.is_available()),
                      "cuda_available": bool(torch.cuda.is_available()),
                      "selected_device": str(select_device("auto")),
                      "parameters": trained_parameter_count(model),
                      "default_checkpoint": str(DEFAULT_CHECKPOINT),
                      "checkpoint_exists": DEFAULT_CHECKPOINT.exists(),
                      "cinematic_pretrained_weights_bundled": False, "paid_apis": 0}
        elif args.command == "studio":
            from .studio import serve
            serve(port=args.port)
            return 0
        elif args.command == "train":
            config=MotionConfig(frames=args.frames,size=args.size,width=args.width,timesteps=args.timesteps)
            result=train(config,steps=args.steps,batch_size=args.batch,lr=args.lr,seed=args.seed,
                         checkpoint=args.checkpoint,dataset=args.data_dir,device_name=args.device)
        else:
            result=render(prompt=args.prompt,output=args.out,seed=args.seed,fps=args.fps,
                          device_name=args.device,preview=args.command=="preview",
                          checkpoint=getattr(args,"checkpoint",None))
        print(json.dumps(result,indent=2))
        return 0
    except (RuntimeError,ValueError,FileNotFoundError,OSError,ImportError) as exc:
        print("GPT-DOUG MOTION-1 ERROR: "+str(exc),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
