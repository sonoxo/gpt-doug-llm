# 🚑 Cyber CPR

**Detect. Stabilize. Repair. Verify. Revive.**

Cyber CPR is a local-first defensive DevSecOps utility powered by the GPT-Doug-LLM/XUNIA engineering model. It watches GitHub repositories, identifies failing workflow states, records a heartbeat/streak, and can apply only explicitly enabled, bounded local remediation actions.

> Cyber CPR is defensive software. It does not change secrets, repository permissions, production credentials, firewall policy, or private infrastructure automatically.

## What it does

- checks GitHub Actions workflow health through the authenticated `gh` CLI;
- records `✅` / `❌` heartbeat state locally;
- announces `🚀 RECOVERY` after an unhealthy → healthy transition;
- announces `🔥 STREAK` after 5 consecutive healthy checks;
- keeps state in `~/.cyber-cpr/state.json`;
- supports one-shot checks or a continuous local pulse;
- exposes a bounded repair hook that is **off by default**;
- never stores GitHub tokens in the project.

## Requirements

- macOS or Linux
- Python 3.10+
- GitHub CLI (`gh`) already authenticated for repositories you are authorized to inspect

## Install

```bash
git clone https://github.com/sonoxo/gpt-doug-llm.git
cd gpt-doug-llm/cyber-cpr
./install.sh
```

Then run:

```bash
cyber-cpr check sonoxo/xuniahub
cyber-cpr check sonoxo/gpt-doug-llm
```

Continuous 3-minute local pulse:

```bash
cyber-cpr watch sonoxo/xuniahub --interval 180
```

Multiple repositories:

```bash
cyber-cpr watch sonoxo/xuniahub sonoxo/gpt-doug-llm --interval 180
```

## Status language

```text
✅ HEALTHY       latest relevant completed runs are successful
❌ ATTENTION     one or more relevant latest runs failed
⏳ PENDING       relevant run still queued/in progress
🚀 RECOVERY      previous pulse unhealthy, current pulse healthy
🔥 STREAK x5     five consecutive healthy pulses
```

## Safe automation boundary

Cyber CPR follows this control loop:

```text
DETECT → CLASSIFY → CONTAIN → BOUNDED REPAIR → VERIFY → REPORT
```

Automatic repair is deliberately constrained. A repair must be explicitly configured in `config.json`, run locally, match an exact known condition, and remain inside the selected repository working tree. Unknown failures are reported instead of guessed at.

Cyber CPR must **not** automatically mutate:

- secrets or credentials;
- GitHub/Vercel/cloud permissions;
- branch protection or organization settings;
- production databases or user data;
- firewall/authentication policy;
- unrelated application logic.

## GrimTheBuilder / XUNIA convention

For XUNIA ecosystem checks, GrimTheBuilder means the browser IDE/program hosted at:

`https://orbit-code-studio.almighty-son-8109.chatgpt.site/`

The `hello-world` project and GitHub `grimthebuilder` folders are workspace/export/integration artifacts only, never the GrimTheBuilder application itself.

## Uninstall

```bash
./uninstall.sh
```

State can be removed separately with:

```bash
rm -rf ~/.cyber-cpr
```

## License

MIT. Cyber CPR inherits the defensive and authorization boundaries documented by GPT-Doug-LLM.