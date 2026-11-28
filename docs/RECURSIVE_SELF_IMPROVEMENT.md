# Bounded recursive self-improvement (RSI)

The repository's existing `ZyraAgent.run(goal, evolve=True)` supports restricted code changes and checkpoints. `rsi_supervisor.py` adds independent regression/quality gates and a finite, review-only feedback loop. This is software improvement, **not** self-modification of ChatGPT or an assertion of AGI.

## Running

Start from a **clean local Git checkout** with Python, pytest, Ruff, a working local Ollama server, and an installed model:

```bash
python3 rsi_supervisor.py --repo . --goal "Improve ZYRA planning reliability and add regression tests"
```

Without a benchmark, only one iteration executes, and a passing candidate is **REVIEW_REQUIRED**, never described as a measured gain.

For two or three bounded improvement generations, supply a **trusted, operator-written** held-out Python benchmark located **outside** the editable repository:

```bash
python3 rsi_supervisor.py --repo . --goal "Improve error recovery" --cycles 2 \
  --benchmark "$HOME/rsi-evaluation/heldout.py" --min-gain 0.01
```

The supervisor invokes the evaluator as `python3 heldout.py /absolute/repo/path`. It must emit *only*:

```json
{"quality": 0.74, "regressions": 0, "security_ok": true}
```

Quality must be finite and between 0 and 1. Candidate quality must exceed the previous measured baseline by at least `--min-gain`; known regressions must be zero; security must pass. Failed candidates revert that generation's checkpoint. A SHA-256 digest detects benchmark edits during a run. The evaluator and its source data are operator-controlled, never agent-editable.

Each generation invokes ZYRA's allowed `evolve` path and requires syntax, unit, Ruff, and Git whitespace gates. All work remains **local and uncommitted**, with no automatic push, merge, deployment, model-weight training, or production promotion. Evidence is recorded by default at `~/.gpt-doug/rsi/report.json`; custom report paths must be outside the repo.

## Verification and limitations

```bash
python3 -m unittest tests.test_rsi_supervisor -v
python3 -m compileall -q rsi_supervisor.py tests/test_rsi_supervisor.py
ruff check rsi_supervisor.py tests/test_rsi_supervisor.py
```

Unit tests exercise mocked agent missions and regression decisions; they cannot prove improvements with a live LLM. Actual quality claims require an independent held-out benchmark, suitable datasets, CI completion, and human review. Only run tests and benchmarks against trusted code in an isolated development environment. The existing agent remains responsible for path limits, emergency stop, and checkpoint rollback.

## GPT-DOUG-LLM-CL1: simulator-only RSI with held-out evaluation

**This is software improvement over synthetic rate-bin data, not live CL1 hardware, biological learning, mitochondrial telemetry, or artificial general intelligence.**

- The only changeable CL1 RSI target is `agents/cl1_rsi_policy.py`. Evaluation scripts, test suites, workflow policies and other modules are protected by a rollback-on-violation scope gate.
- The held-out evaluator `scripts/cl1_rsi_heldout.py` tests **36 deterministic generated noisy traces** (six seeds × six scenarios), balanced accuracy, reproducibility, input validation and per-scenario regression thresholds. No CL SDK is needed for these tests.
- The evaluator installer creates a **private, random per-installation challenge** (six extra synthetic seeds), embeds it into a checksum-identified evaluator **outside** the editable repository, and records a protected local provenance manifest. A prior installation remains immutable unless explicitly replaced. Python's `-I` mode and filtered `PYTHONPATH` limit accidental code contamination; this is **not** an OS security sandbox for untrusted code.
- Three independent benchmark measurements establish the CL1 baseline and measure each candidate. Unstable measurements, known regressions or security failures block the mission. The loop is capped at three generations, and accepted changes remain local and require human review.

### One-command free evaluator setup on Mac

```bash
python3 scripts/prepare_cl1_rsi_evaluator.py
python3 -I "$HOME/.gpt-doug/rsi/evaluators/cl1-heldout.py" "$PWD"
```

The second command emits `{"quality": <measured value>, "regressions": 0, "security_ok": true}` when the baseline passes; the quality value must be **measured**, not assumed. The installer will not overwrite a different trusted evaluator without `--replace`.

### Run an actual local, bounded CL1 improvement cycle

```bash
python3 rsi_supervisor.py --repo . --profile cl1-sim --goal "Improve synthetic spike activity decoder reliability" --cycles 2 --min-gain 0.01
```

This requires an available **local Ollama code model** for edit proposals. A benchmark alone is free and offline. The agent may modify only the synthetic decoder; candidate tests and quality evaluations must pass before the next generation. A success does not automatically push, merge, train weights, access physical CL1, or deploy.

Local evidence is recorded at `~/.gpt-doug/rsi/report.json`, including evaluator SHA-256, baseline measurements and individual generation decisions.

### Independent verification

```bash
python3 -m unittest tests.test_rsi_supervisor tests.test_cl1_rsi -v
python3 -m py_compile rsi_supervisor.py agents/cl1_rsi_policy.py scripts/cl1_rsi_heldout.py scripts/prepare_cl1_rsi_evaluator.py
```

**Limitations:** This benchmark demonstrates reproducible improvement only on its own synthetic software challenge. The static AST restriction and isolated Python mode do not make malicious candidate code safe to run. Evaluate reviewed code in an isolated environment. No actual CL1 biological data is collected.
