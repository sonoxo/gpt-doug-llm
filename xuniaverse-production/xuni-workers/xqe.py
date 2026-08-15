"""
Copyright (c) 2026 Douglas Brown Jr / Xuniaverse. Licensed under the
xuniaverse-production LICENSE (All Rights Reserved) — first authored
2026-08-14.

XQE — Xuni Quantum Engine, first real slice.

This is NOT quantum computing. Per the original ecosystem diagram, XQE
names a reasoning/execution pipeline: Superposition -> Simulate -> Score
-> Collapse -> Verify. This module implements that *pattern* honestly:

  Superposition — generate a small set of candidate task framings
                  (deterministic prompt rewrites, not multiple LLM calls
                  in this first slice).
  Simulate      — run each candidate through zyra_guard.review() to see
                  what would happen before anything is dispatched.
  Score         — a real, documented deterministic formula from the
                  simulate step's output (allowed/blocked, classification
                  level, prompt length) — no fabricated "quantum" scoring.
  Collapse      — pick the highest-scoring candidate.
  Verify        — actually dispatch the collapsed candidate through the
                  real ontology.submit_task_action -> daemon -> Doug
                  pipeline and report the real result.

Every step here is inspectable and real. Nothing about this claims
quantum superposition/entanglement in the physics sense.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zyra_guard  # noqa: E402
import ontology  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "xuni-workers" / "results"

CLASSIFICATION_PENALTY = {
    "UNCLASSIFIED": 0,
    "CONFIDENTIAL": 10,
    "SECRET": 1000,      # effectively disqualifying — Zyra would block it anyway
    "TOP SECRET": 1000,
}


def superposition(prompt: str) -> list:
    """Generate a small set of real candidate framings of the same task.
    Deterministic rewrites, not multiple LLM calls, in this first slice —
    documented honestly rather than implied to be model-generated."""
    return [
        {"variant": "as-given", "prompt": prompt},
        {"variant": "direct", "prompt": f"Do this directly and concisely, no extra commentary: {prompt}"},
        {"variant": "stepwise", "prompt": f"Break this into the smallest necessary steps, then do it: {prompt}"},
    ]


def simulate(candidates: list) -> list:
    """Run each candidate through the real Zyra guard — the actual check
    that would run at dispatch time — without dispatching anything yet."""
    simulated = []
    for c in candidates:
        allowed, reason = zyra_guard.review({"id": f"xqe-sim-{c['variant']}", "prompt": c["prompt"]})
        rice_hits = zyra_guard._rice_scan(c["prompt"])
        level = zyra_guard.classify(c["prompt"], allowed, None if allowed else reason, rice_hits)
        simulated.append({**c, "allowed": allowed, "reason": reason, "level": level})
    return simulated


def score(simulated: list) -> list:
    """
    Deterministic score per candidate, documented in full:
      base = 100
      - CLASSIFICATION_PENALTY[level]   (SECRET/TOP SECRET effectively zero it out)
      - 1 point per 20 chars of prompt length (mild preference for concision)
      - 0 score, unscored, if Zyra would block it outright (allowed=False)
    """
    scored = []
    for s in simulated:
        if not s["allowed"]:
            scored.append({**s, "score": 0})
            continue
        length_penalty = len(s["prompt"]) // 20
        pts = 100 - CLASSIFICATION_PENALTY.get(s["level"], 0) - length_penalty
        scored.append({**s, "score": max(pts, 0)})
    return scored


def collapse(scored: list) -> dict:
    """Pick the highest-scoring candidate; ties break toward the earliest
    (as-given) variant, since that's the least-transformed option."""
    return max(scored, key=lambda s: s["score"])


def verify(chosen: dict, task_id: str, timeout_s: int = 60) -> dict:
    """Actually dispatch the collapsed candidate through the real pipeline
    (ontology.submit_task_action -> daemon -> Doug) and wait for and
    return the real result — no simulated/fabricated outcome."""
    if not chosen["allowed"]:
        return {"task_id": task_id, "dispatched": False, "reason": chosen["reason"]}

    ontology.submit_task_action(task_id, chosen["prompt"])
    result_path = RESULTS_DIR / f"{task_id}.json"
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if result_path.exists():
            import json
            return {"task_id": task_id, "dispatched": True, "result": json.loads(result_path.read_text())}
        time.sleep(1)
    return {"task_id": task_id, "dispatched": True, "result": None, "reason": "timed out waiting for daemon"}


def run(prompt: str, task_id: str) -> dict:
    """Full pipeline: superposition -> simulate -> score -> collapse -> verify."""
    candidates = superposition(prompt)
    simulated = simulate(candidates)
    scored = score(simulated)
    chosen = collapse(scored)
    result = verify(chosen, task_id)
    return {"candidates": scored, "chosen": chosen, "verification": result}


if __name__ == "__main__":
    import json
    out = run(sys.argv[1] if len(sys.argv) > 1 else "add a health check endpoint", "xqe-cli-test")
    print(json.dumps(out, indent=2))
