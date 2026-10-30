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
