#!/usr/bin/env python3
"""Independent held-out benchmark for the GPT-DOUG-LLM CL1 synthetic RSI profile.

The operator installs a COPY of this evaluator OUTSIDE the agent-editable repo.
It imports only a specific local, simulator-only policy module under evaluation.
It does not operate physical CL1 hardware or run real neural experiments.
Use only with reviewed code in an isolated development environment: -I and AST
restrictions improve separation but are NOT an operating-system security sandbox.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import math
from pathlib import Path
import random
import sys

SEEDS = (113, 227, 347, 521, 691, 823)
CASES_PER_SEED = 6
SAMPLES_PER_CASE = 256
MAX_CODE_BYTES = 32_768
ALLOWED_IMPORTS = {"math", "__future__"}
FORBIDDEN_NAMES = {
    "eval", "exec", "compile", "open", "__import__", "input",
    "globals", "locals", "vars", "getattr", "setattr", "delattr",
    "breakpoint", "exit", "quit",
}
# Guard accidental or simplistic evaluator tampering. This is not a sandbox.
FORBIDDEN_AST = (ast.ImportFrom, ast.With, ast.AsyncWith, ast.Global, ast.Nonlocal)


def load_candidate(repo: Path):
    candidate = (repo / "agents" / "cl1_rsi_policy.py").resolve(strict=True)
    if candidate != repo / "agents" / "cl1_rsi_policy.py" or not candidate.is_file():
        raise ValueError("CL1 candidate must be the expected regular Python file")
    if candidate.is_symlink() or candidate.stat().st_size > MAX_CODE_BYTES:
        raise ValueError("CL1 candidate path or size not allowed")
    source = candidate.read_text(encoding="utf-8")
    tree = ast.parse(source, filename="agents/cl1_rsi_policy.py")
    for node in ast.walk(tree):
        if isinstance(node, (ast.ImportFrom,)):
            if node.module != "__future__":
                raise ValueError("CL1 candidate has an unapproved relative or third-party import")
        elif isinstance(node, ast.Import):
            if any(alias.name not in ALLOWED_IMPORTS for alias in node.names):
                raise ValueError("CL1 candidate imports outside its synthetic model")
        elif isinstance(node, (ast.With, ast.AsyncWith, ast.Global, ast.Nonlocal)):
            raise ValueError("CL1 candidate has unsupported side-effect constructs")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_NAMES:
                raise ValueError("CL1 candidate attempts a forbidden dynamic operation")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError("CL1 candidate accesses hidden runtime attributes")
    spec = importlib.util.spec_from_file_location("_cl1_heldout_candidate", candidate)
    if spec is None or spec.loader is None:
        raise ValueError("Cannot import CL1 candidate")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    decoder = getattr(module, "decode_activity", None)
    if not callable(decoder):
        raise ValueError("Expected decode_activity(rates,baseline)")
    return decoder


def make_case(seed: int, case: int) -> tuple[list[float], list[int], float]:
    rng = random.Random((seed << 8) + case)
    baseline = rng.uniform(4.0, 22.0)
    rates: list[float] = []
    targets: list[int] = []
    state = rng.randint(0, 1)
    remaining = 0
    for _ in range(SAMPLES_PER_CASE):
        if remaining == 0:
            state = 1 - state
            remaining = rng.randint(8, 25)
        remaining -= 1
        # A non-biological two-state activity signal with Gaussian readout noise.
        intensity = (1.54 if state else 0.87) * baseline
        value = intensity + rng.gauss(0, 0.38 * baseline)
        rates.append(max(0.0, round(value, 6)))
        targets.append(state)
    return rates, targets, baseline


def verify_prediction(values: object, expected_count: int) -> list[int]:
    if not isinstance(values, list) or len(values) != expected_count:
        raise ValueError("Decoder must return an output list with exactly one item per bin")
    if any(type(value) is not int or value not in (0, 1) for value in values):
        raise ValueError("Decoder outputs must be binary integer classes")
    return values


def balanced_accuracy(prediction: list[int], targets: list[int]) -> float:
    positive = sum(targets)
    negative = len(targets) - positive
    if positive == 0 or negative == 0:
        raise ValueError("Held-out case does not include both states")
    true_pos = sum(pred == 1 and truth == 1 for pred, truth in zip(prediction, targets))
    true_neg = sum(pred == 0 and truth == 0 for pred, truth in zip(prediction, targets))
    return (true_pos / positive + true_neg / negative) / 2


def benchmark(repo: Path) -> dict:
    decoder = load_candidate(repo)
    # These contracts prevent a high score that sacrifices bounds/validation.
    for bad_rates, bad_baseline in (
        ([1.0], 0.0), ([float("nan")], 5.0),
        ([-1.0], 5.0), ([1.0] * 1025, 5.0),
    ):
        try:
            decoder(bad_rates, bad_baseline)
        except ValueError:
            pass
        else:
            raise ValueError("CL1 decoder bypasses a strict input boundary")
    if verify_prediction(decoder([], 5.0), 0) != []:
        raise ValueError("Unexpected decoder result on an empty sequence")
    scores: list[float] = []
    regressions = 0
    for seed in SEEDS:
        for case in range(CASES_PER_SEED):
            rates, targets, baseline = make_case(seed, case)
            output = verify_prediction(decoder(rates[:], baseline), len(rates))
            if (seed, case) == (SEEDS[0], 0):
                if output != verify_prediction(decoder(rates[:], baseline), len(rates)):
                    raise ValueError("CL1 decoder is not reproducible")
            score = balanced_accuracy(output, targets)
            scores.append(score)
            if not math.isfinite(score) or score < 0.65:
                regressions += 1
    quality = round(sum(scores) / len(scores), 6)
    return {"quality": quality, "regressions": regressions, "security_ok": regressions == 0}


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -I <trusted-heldout.py> /absolute/repository-root")
    repo = Path(sys.argv[1]).expanduser().resolve(strict=True)
    if not repo.is_dir() or not (repo / "agents").is_dir():
        raise SystemExit("Invalid CL1 source repository")
    # Return the exact strict Metrics schema; failures are never dressed up as gain.
    print(json.dumps(benchmark(repo), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
