"""BioPineal CL1 simulator-only recording bridge.

Runs ONLY with an explicit simulator flag. Does not stimulate neurons, spawn
autonomous agents or connect to network services. Use on a developer machine
with Cortical Labs cl-sdk, NEVER directly on physical CL1 equipment.
"""
from __future__ import annotations
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import sys


def ensure_simulator() -> str:
    try:
        version = importlib.metadata.version("cl-sdk")
    except importlib.metadata.PackageNotFoundError as exc:
        raise RuntimeError("Install the CL SDK simulator in a Python 3.12+ virtual environment: pip install cl-sdk") from exc
    # CL1 ships a distinct hardware API. If present, refuse to open a device.
    if Path("/opt/cl-api-whl").exists():
        raise RuntimeError("Physical CL1 environment detected; simulator bridge refuses hardware access")
    return version


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulator", action="store_true", help="Required acknowledgement: this is a local SDK simulation")
    parser.add_argument("--output", type=Path, default=Path("cl1-sim-recording.h5"))
    parser.add_argument("--seconds", type=float, default=3.0)
    args = parser.parse_args()
    if not args.simulator:
        parser.error("--simulator is required; physical CL1 connections are not supported")
    if not (0.1 <= args.seconds <= 10):
        parser.error("--seconds must be between 0.1 and 10")
    sdk_version = ensure_simulator()
    import time
    import cl
    # Official API: cl.open() and Neurons.record(). No stimulation calls.
    with cl.open() as neurons:
        recording = neurons.record(file_location=str(args.output.resolve()))
        try:
            time.sleep(args.seconds)
        finally:
            recording.stop()
    print(json.dumps({
        "status": "simulator-recording-finished",
        "sdk_version": sdk_version,
        "output_requested": str(args.output.resolve()),
        "data_type": "simulated_non_learning",
        "neural_learning_claim": False,
        "physical_hardware": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
