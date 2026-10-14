# GPT-Doug-MLM Biochip Research Core

This module introduces a **research-only** multimodel orchestration and biological-signal observation layer. It does not connect to the Pentagon, defense systems, hardware, CL1 devices, remote networks, or live data sources. No such access is inferred from naming.

## Components

- `ResearchRouter`: runs only caller-injected local/authorized model adapters. It returns candidate outputs with confidence **0.0**, rather than presenting uncalibrated model text as scientific certainty.
- `Observation`: requires a source, timestamp with timezone, unit, and permission/consent reference. Neural signal and biochip telemetry are labels, not proof of hardware integration.
- `EvidenceJournal`: local JSONL hash-chained evidence, with tamper checks. It is not cryptographically signed, concurrency safe, encrypted, or production-grade storage.
- `ProposalGate`: records human-reviewed research proposals; has no execution or deployment method.
- `heartbeat`: verifies evidence-chain integrity and reports local health.

## Local example

```python
from datetime import datetime, timezone
from gpt_doug_mlm.biochip_research import Observation, EvidenceJournal, ResearchRouter, heartbeat

models = ResearchRouter({"local": lambda question: "Research candidate: " + question})
print(models.deliberate("Summarize synthetic signal observations"))

journal = EvidenceJournal("research-data/observations.jsonl")
journal.append(Observation(
    "authorized-lab", "synthetic", 0.25, "mV",
    datetime.now(timezone.utc).isoformat(), "local-test-permission"
))
print(heartbeat(journal))
```

## Guardrails and integration next steps

1. Add real model adapters **only** after explicit account authorization, limits, and privacy review.
2. For research hardware, implement a documented vendor SDK adapter with separate operator consent and read-only default.
3. Treat biosignals as sensitive personal information; enforce consent, minimization, retention limits, encryption and access controls before processing actual data.
4. Keep all code proposals behind tests, security review, reproducibility checks, and human approval. Never allow recursive autonomous deployment or unreviewed infrastructure changes.
5. Evaluate against synthetic, permitted datasets first. No operational or scientific efficacy claims are implied.

Test: `python -m pytest tests/test_biochip_research.py -q`
