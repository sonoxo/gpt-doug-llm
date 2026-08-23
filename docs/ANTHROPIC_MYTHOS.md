# GPT-Doug + Anthropic Mythos

GPT-Doug can route requests through Anthropic Claude Mythos 5 without copying or modifying Anthropic model weights.

## What this integration does

- Targets `claude-mythos-5` through the existing Anthropic Messages API provider.
- Requires a valid `ANTHROPIC_API_KEY` and Anthropic authorization for Mythos.
- Does not bypass Anthropic access controls.
- Falls back to `claude-fable-5` on model/access HTTP 400, 403, or 404 responses unless fallback is disabled.
- Returns metadata showing whether Mythos or the fallback model produced the result.

## Health check

```bash
export ANTHROPIC_API_KEY="..."
python3 mythos_doug.py --health
```

## Run a prompt

```bash
export ANTHROPIC_API_KEY="..."
python3 mythos_doug.py "Review this repository and propose the smallest safe fix."
```

## Configuration

- `ANTHROPIC_MYTHOS_MODEL` defaults to `claude-mythos-5`.
- `ANTHROPIC_MYTHOS_FALLBACK_MODEL` defaults to `claude-fable-5`.
- `ANTHROPIC_MYTHOS_FALLBACK=0` disables fallback.
- Existing Anthropic provider timeout behavior is preserved.

This is provider routing, not a literal merge of proprietary model weights. GPT-Doug remains the orchestration/runtime layer; Anthropic supplies inference when the Mythos profile is selected.
