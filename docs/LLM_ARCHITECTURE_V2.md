# GPT-DOUG-LLM-MAX / CL1 — Architecture v2

**Build scope:** A locally operated, no-billing Python/Ollama runtime in the existing GPT-DOUG repository. This is a staged PR, not a live deployment or an assumption of control over all other Sonoxo repos. The architecture JSON next to this document is a machine-readable design manifest.

## Model request path

```text
  OPERATOR / MAC BROWSER                         GLASS ONION
          |                                      music / bank
  XUNIA localhost UI :8787                       adapters only
          |
  KRAKEN SHIELD / emergency stop -> local hash-linked audit
          |
  ZYRA / GOLDEN SHIELD inbound checks
          |
  GPT-DOUG CL1 ROUTER   (Ollama only, no cloud fallback)
          |
  installed model inventory + explicit model admission
          |
  bounded inference options (num_ctx <= 8192; num_predict <= 2048)
          |
  URL guard -> no proxies -> no HTTP redirects
          |
  OLLAMA 127.0.0.1:11434 / preinstalled open-weight models
          |
  XUNIA stream / SFNN checkpoint / current output policy
          |
  BROWSER
```

## Real architectural changes

1. `agents/cl1_runtime_v2.py`: pure model-inventory selection and bounded options for local inference. No implicit `pull` or silent selection of another quantization. Tagless names resolve only to installed `:latest`.
2. `agents/llm_backend.py`: direct Ollama chat uses the same admission checks, refuses unexpected inference options, disables proxy environment interception and HTTP redirects. It exposes only CL1-supported local provider choices to the UI.
3. `agents/xunia_stream.py`: streaming requests use the identical model and resource policy, returning explicit errors for missing models or invalid limits without making an inference request.
4. `scripts/cl1-free-swarm.sh`: the Mac `doctor` now checks model inventory through the same redirect/proxy-free local transport and will not accept `:cloud` models.
5. `Kraken Shield`, `ZYRA`, emergency stop, and Glass Onion remain connected at their existing integration points; this PR does not extend their enforcement into unrelated applications.

## Runtime constraints

- Inference: local **Ollama only**; other provider selections do not become paid fallbacks.
- Explicit override: a model must already appear in the local `/api/tags` inventory. Missing models are refused rather than pulled.
- Local transport: requires an approved loopback URL, no environment proxies and no HTTP redirects.
- Resource bounds: context 256–8192 tokens, output 1–2048 tokens. Default request 4096 context and 1024 output. Safe limits for temperature, top-p, top-k, repetition penalty, seed and stop sequences.
- Unknown inference option fields are discarded; malformed known fields are refused.
- No autonomous repository writes, finance API actions, media publishing, remote compute provisioning, Stripe checkout, or paid model API calls are introduced.
- Local CPU, memory, disk, bandwidth and power may still have real costs.

## Operate from Mac Terminal

Use an **isolated clone** so existing untracked `kraken_shield/` source files cannot block `git switch` and are not overwritten:

```bash
cd "$HOME"
git clone --depth 1 --single-branch \
  -b feat/cl1-llm-architecture-v2-20261114 \
  https://github.com/sonoxo/gpt-doug-llm.git \
  "$HOME/gpt-doug-llm-v2"
cd "$HOME/gpt-doug-llm-v2"
bash scripts/cl1-free-swarm.sh setup
bash scripts/cl1-free-swarm.sh doctor
bash scripts/cl1-free-swarm.sh run
```

The intended UI is `http://127.0.0.1:8787/`. Keep the terminal running. Ollama must already be running on port 11434 with a downloaded local model (the launcher defaults to `qwen2.5-coder:3b`). `setup` installs free/open-source Python dependencies locally into `.venv`; it is not a paid hosting service.

## Validation

```bash
python3 -m unittest discover -s tests -p 'test_cl1_llm_arch_v2.py' -v
python3 -m unittest discover -s tests -p 'test_cl1_free_only.py' -v
bash -n scripts/cl1-free-swarm.sh
```

`CL1 LLM Architecture v2` runs this on Python 3.11 and 3.12, plus selected emergency-stop and Kraken tests. A green CI gate is not proof of Mac local startup: confirm the browser, model readiness, streaming response, and stop control on the operator's machine.

## Remaining hardening requirements

- **Outbound streaming DLP:** the existing XUNIA code may transmit tokens before its final output audit. Do not describe it as a pre-delivery outbound block; a separate buffering design and its latency/cost tradeoff must be reviewed.
- **Other processes:** Glass Onion/Jukebox/finance modules outside this Python model boundary need separate enforcement.
- **System-level sandbox:** the Python transport policy prevents configured proxy and 30x redirect mechanisms for these model requests; it is not a replacement for a host firewall, OS sandbox or a verified no-egress test.
- **Upstream dependencies:** the independent MAX completion suite can still fail on Zyra's npm security audit. Preserve that failing gate until Zyra's dependency remediation is independently validated.
- **Upgrade ordering:** #519 (CL1) -> #520 (Kraken) -> #521 (Glass Onion) -> #522 (Jukebox MAX) -> this PR.

This branch **does not** change the operator's current Mac checkout, install any service remotely, merge prior PRs or cancel any existing provider subscription.
