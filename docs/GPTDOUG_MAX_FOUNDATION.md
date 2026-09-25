# GPT-Doug MAX Foundation

This document is the canonical map for the local visual/agent foundation.

## Foundation

```text
ONTOLOGY
   ↓
GENOME / HASH
   ↓
PHENOTYPE
   ↓
EMBODIMENT
   ↓
HUD + MATRIX
   ↓
KNOWLEDGE + SKILLS + RESEARCH
   ↓
MAX CONTROL
   ↓
USER-AUTHORIZED ADMIN
```

## Stable commands

```text
gptmax             master launcher
doughud            HUD / visual embodiment
dougcore           Matrix core
dougmax            MAX control broker
dougsec            authorized defensive security mode
dougctl            knowledge / research / skill controller
```

## Permanent boot menu

The intended interactive Zsh boot path is:

```bash
export PATH="$HOME/.local/bin:$PATH"; clear; "$HOME/.local/bin/gptdougmax"
```

Use a recursion guard when adding this to `~/.zshrc`.

## Separation of concerns

| Component | Owns |
| --- | --- |
| Ontology | identity, states, policy-relevant traits |
| Phenotype | derived visual/behavior parameters |
| Runtime | state machine and embodiment |
| HUD | presentation and shortcuts |
| Knowledge | retrieved/crawled evidence |
| Skill registry | reusable workflows |
| MAX broker | command planning, risk classification, execution |
| Admin | explicit OS authorization only |

A visual shell must never silently become execution authority.

## Global skill lattice

See [GLOBAL_SKILL_LATTICE.md](GLOBAL_SKILL_LATTICE.md). The lattice exposes 100,000,000 deterministic workflow addresses without claiming 100,000,000 pretrained capabilities.

## Visual GPT-Doug

See [VISUAL_GPTDOUG.md](VISUAL_GPTDOUG.md) for the terminal embodiment, source-art conventions, launcher, controls, and separation rules.
