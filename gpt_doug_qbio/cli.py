from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

from .core import MAX_FRAMES, SpikeFrame, analyze_sequence


def _demo_frames(frame_count: int, channel_count: int, seed: int) -> list[SpikeFrame]:
    rng = random.Random(seed)
    frames: list[SpikeFrame] = []
    for index in range(frame_count):
        wave = 0.5 + 0.5 * math.sin(index / 5.0)
        confluence = index / max(1, frame_count - 1)
        counts = []
        for channel in range(channel_count):
            spatial = 0.5 + 0.5 * math.sin((channel + index) / 7.0)
            probability = min(0.95, 0.03 + 0.20 * wave + 0.35 * confluence * spatial)
            value = 1 if rng.random() < probability else 0
            if confluence > 0.75 and rng.random() < 0.08:
                value += rng.randint(1, 3)
            counts.append(value)
        frames.append(SpikeFrame(t_ms=float(index * 20), counts=tuple(counts)))
    return frames


def _read_jsonl(path: Path) -> list[SpikeFrame]:
    frames = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            if len(frames) >= MAX_FRAMES:
                raise ValueError(f"input exceeds {MAX_FRAMES} frames")
            row = json.loads(line)
            try:
                raw_t = row["t_ms"]
                raw_counts = row["counts"]
                if isinstance(raw_t, bool) or not isinstance(raw_t, (int, float)):
                    raise TypeError("t_ms must be numeric")
                if not isinstance(raw_counts, list) or not raw_counts:
                    raise TypeError("counts must be a non-empty JSON array")
                if any(type(value) is not int or value < 0 for value in raw_counts):
                    raise TypeError("counts must contain non-negative JSON integers only")
                frame = SpikeFrame(t_ms=float(raw_t), counts=tuple(raw_counts))
            except Exception as exc:
                raise ValueError(f"invalid frame on line {line_number}") from exc
            frames.append(frame)
    return frames


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gpt-doug-qbio")
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="Run a deterministic synthetic spike-confluence sequence.")
    demo.add_argument("--frames", type=int, default=64)
    demo.add_argument("--channels", type=int, default=64)
    demo.add_argument("--seed", type=int, default=42)
    demo.add_argument("--window", type=int, default=8)

    analyze = sub.add_parser("analyze", help="Analyze authorized spike-count JSONL.")
    analyze.add_argument("path", type=Path)
    analyze.add_argument("--window", type=int, default=8)
    analyze.add_argument(
        "--source-class",
        default="OPERATOR_DECLARED",
        help="Provenance label only; it does not independently verify biological origin.",
    )

    args = parser.parse_args(argv)
    if args.command == "demo":
        if not 2 <= args.frames <= 10000:
            parser.error("--frames must be 2..10000")
        if not 1 <= args.channels <= 256:
            parser.error("--channels must be 1..256")
        frames = _demo_frames(args.frames, args.channels, args.seed)
        report = analyze_sequence(frames, window=args.window, source_class="SIMULATED")
    else:
        frames = _read_jsonl(args.path)
        report = analyze_sequence(frames, window=args.window, source_class=args.source_class)

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
