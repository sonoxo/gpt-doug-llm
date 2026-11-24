# GPT-DOUG-LLM MAX — verified recursive software improvement

**Status: implementation + local offline tests; real multi-generation LLM optimization is not yet demonstrated.** This enhancement wraps the existing `rsi_supervisor.py` (which already creates checkpointed ZYRA coding missions with test, lint, independent benchmarking and rollback). It does not bypass those gates, change ChatGPT model weights, or grant new network or deployment powers.

## What it adds

- Repeated, independent benchmarks **2–7 times per baseline and candidate** (default 3). If result quality varies beyond the configured spread (default 0.0), the cycle is blocked and the existing supervisor rolls back the candidate.
- **Conservative evidence:** candidate quality is the worst sampled quality; regressions are the maximum observed; any security failure fails the gate.
- Baseline-only **probe** (no LLM, no source mutations) so the evaluator is verified before enabling RSI.
- Trusted evaluator SHA-256, timestamped observations, per-cycle hash chain, and an atomic owner-only (`0600`) JSON report stored **outside** the source checkout. A bare hash chain is not a digital signature.
- Localhost-only Ollama endpoint; no paid APIs, automatic merge, push or deployment.

## macOS install / probe (no paid API or LLM required)

In a clean checkout of `sonoxo/gpt-doug-llm` containing this feature:

```bash
python3 scripts/install_rsi_evaluator.py --repo .
python3 scripts/rsi_verified.py --repo . \
  --benchmark "$HOME/.gpt-doug/rsi/evaluator/zyra_action_quality.py" --probe
```

**Note:** the reference evaluator is publicly included and is **not** a secret held-out test. For stronger claims, maintain additional operator-controlled test cases and separate cross-validation. The reference evaluator measures action JSON parsing in `zyra_agent.py`, not overall intelligence, model-token quality, or AGI. On the inspected baseline parser, the reference security checks detect that a JSON array containing an embedded object may be accepted by the extractor; the baseline should therefore be marked as failing this security case until repaired.

## Optional live local RSI

Requires free local Ollama, an installed `qwen2.5-coder:7b` (or compatible model), and repo test dependencies such as pytest/Ruff. Begin with a clean disposable clone; obtain operator consent for code changes and inspect the diff and JSON report before accepting any modifications:

```bash
python3 scripts/rsi_verified.py --repo . \
  --goal "Improve ZYRA JSON action parsing and add defensive regression tests" \
  --benchmark "$HOME/.gpt-doug/rsi/evaluator/zyra_action_quality.py" \
  --cycles 2 --repeats 3 --min-gain 0.01
```

RSI remains finite (the parent supervisor enforces at most three generations). The agent changes allowed `zyra*.py`, `agents/`, `doug_core/`, `tests/` paths only. On failed measured or independent checks the current candidate is rolled back. Kept candidates are uncommitted and require a human review before any push or deployment. If the benchmark is already perfect, the quality-gain gate correctly prevents further accepted generations.

## Required verification

```bash
python3 -m unittest discover -s tests -p 'test_rsi_verified.py' -v
python3 -m unittest discover -s tests -p 'test_rsi_supervisor.py' -v
python3 -m compileall -q scripts/rsi_verified.py scripts/install_rsi_evaluator.py benchmarks/zyra_action_quality.py
```

These tests only validate orchestration, evaluator behavior and failure gates. **They do not claim that an LLM rewrote code or improved general reasoning.** No production RSI run, observed BIGO integration or site crawler feedback loop is implied by this change.
