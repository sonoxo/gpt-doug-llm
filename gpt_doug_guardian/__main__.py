"""CLI: python -m gpt_doug_guardian [--steps N] [--out FILE]."""
import argparse
import json
from pathlib import Path

from .sim import GuardianSim


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline synthetic Guardian fleet training")
    parser.add_argument("--steps", type=int, default=24, help="simulation ticks (1..500)")
    parser.add_argument("--out", help="optional path for JSON state report")
    args = parser.parse_args()
    sim = GuardianSim()
    sim.run(args.steps)
    payload = json.dumps(sim.snapshot(), indent=2)
    if args.out:
        path = Path(args.out).expanduser()
        path.write_text(payload + "\n", encoding="utf-8")
        print(f"Saved {path} (tick {sim.tick}, audit verified: {sim.verify_audit()})")
    else:
        print(payload)


if __name__ == "__main__":
    main()
