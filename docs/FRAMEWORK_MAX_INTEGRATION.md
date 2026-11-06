# GPT-DOUG MAX — Integrated SKULL & Framework (2026-11-06)

**Status:** SKULL-LLM PR #503 and framework reliability PR #505 were
merged into the main repository. This increment adds an integrated command
router, offline 3D verification, and an **actual measured local latency**
benchmark. The branch is reviewable until the new integration CI passes.

## All-in-one terminal on macOS

Use an independent checkout so the working older SKULL environment is not
overwritten:

```bash
git clone --depth 1 https://github.com/sonoxo/gpt-doug-llm.git ~/gpt-doug-max
cd ~/gpt-doug-max
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/gpt-doug health --strict --verify-skull
.venv/bin/gpt-doug skull live
```

**Until this integration branch is merged**, check out
`feat/max-integrated-runtime-20261106` for the newly documented aliases.

The existing standalone commands remain intact:
`skull-llm`, `biochip-cl1-skull-gpt-skull`, and `gpt-doug-health`.
The emergency stop is **not** renamed: `gpt-doug-llm stop the kraken`
remains under operator control.

### Local inference benchmark

```bash
ollama serve
ollama pull qwen2.5-coder:7b
OLLAMA_MODEL=qwen2.5-coder:7b .venv/bin/gpt-doug skull bench --iterations 3
```

This invokes the actual local model (one **depth-1** inference per sample).
It reports wall-clock minimum, median, 95th percentile, maximum and response
character lengths. **Character counts are not token counts**; it does
not estimate tokens/second or claim to measure a model's intelligence.
Maximum 5 benchmark repetitions. No prompt or generated answer is included
in the report. The operator emergency stop is checked before/after every
sample; memory saving is disabled.

### Offline hardware-independent graphics test

```bash
.venv/bin/gpt-doug health --json --strict --verify-skull
```

This checks **two separately rotated, perspective-projected 3D frames**,
with **zero model calls and zero network calls**. The CL1 visualization
is simulated; no physical neuronal telemetry is present. For a live Ollama
connectivity check separately opt into `--ollama`.

### Native Mac app

Build the real SwiftUI / WebKit desktop app with the existing local venv:

```bash
bash macos/build-app.sh --open
```

The app remains coupled to its checkout's Python environment and Ollama.
It is **not** a new operating system. Codesign is ad-hoc, not App Store
notarization. The current 3D skull remains procedural rather than a real
medical scan.

## Gate requirements

- Offline core CLI integration tests must pass without Ollama, paid APIs,
  background tasks or hardware.
- Benchmarks must be explicitly requested, bounded, kill-switch-aware,
  and must not leak prompts/answers.
- The existing emergency-stop, SKULL runtime, npm security and unified
  framework workflows must remain green before integration.
- Other Sonoxo repositories, external tenants, and Mac installations are
  not modified by GitHub CI.
