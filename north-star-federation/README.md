# THE NORTH STAR FEDERATION

> **GPT-DOUG-LLM-MAX collective intelligence federation**
>
> **People + Agents + Evidence + Dissent + Simulation + Consensus + Policy + Outcomes**

[![North Star](https://img.shields.io/badge/NORTH%20STAR-FEDERATION-d4af37?style=for-the-badge)](#the-north-star-federation)
[![GPT-Doug-Max](https://img.shields.io/badge/GPT--DOUG--LLM--MAX-COLLECTIVE%20SUPERVISOR-0ea5e9?style=for-the-badge)](https://github.com/sonoxo/gpt-doug-llm)
[![ZYRA](https://img.shields.io/badge/ZYRA-GOVERNED%20EXECUTION-16a34a?style=for-the-badge)](https://github.com/sonoxo/zyra)

## Mission

**THE NORTH STAR FEDERATION** is the coordination layer for the GPT-Doug ecosystem. It does not try to collapse every project into one monolith. It gives independent components a common registry, evidence contract, deliberation model, policy boundary, and outcome loop.

```text
HUMANS + HETEROGENEOUS AGENTS
            |
            v
    FEDERATION REGISTRY
            |
            v
      EVIDENCE GRAPH
            |
            v
 INDEPENDENT PROPOSALS FIRST
            |
            v
   CHALLENGE + DISSENT
            |
            v
 SIMULATION / VERIFICATION
            |
            v
 CONSENSUS + UNCERTAINTY
            |
            v
       ZYRA GUARD
            |
            v
     HUMAN AUTHORITY
            |
            v
   AUTHORIZED ACTIONS
            |
            v
     OUTCOME EVIDENCE
            |
            +-------> learn / reassess
```

## North Star

GPT-Doug-Max is not one giant model. The target is a governed collective-intelligence runtime where specialized systems can disagree, cite evidence, challenge assumptions, simulate alternatives, preserve dissent, and converge only when the evidence supports convergence.

**North-star equation:**

```text
GPT-DOUG-LLM-MAX =
  Ontology
  + Heterogeneous Agent Swarm
  + Humans
  + Evidence
  + Dissent
  + Simulation
  + Consensus
  + Policy
  + Authorized Actions
  + Outcome Learning
```

## Federation members

| Member | Role | Canonical home |
| --- | --- | --- |
| **GPT-DOUG-LLM-MAX** | Collective supervisor and orchestration layer | https://github.com/sonoxo/gpt-doug-llm |
| **ZYRA** | Bounded execution and policy-gated actions | https://github.com/sonoxo/zyra |
| **Wakeup3lm** | IDE-native LLM execution kernel | `gpt-doug-llm/wakeup3lm` |
| **THE BLACK HOUSE** | Governance, ontology, mission root | `gpt-doug-llm/the-black-house` |
| **KRAKEN JUTSU** | Provenance-first judgment and defensive orchestration | `gpt-doug-llm/kraken_jutsu` |
| **A.E.O. / RVIA-INTEL** | Provenance-first intelligence accountability | `gpt-doug-llm/rvia-intel/aeo` |
| **SHADOW GLASS / GLASS ONION** | Policy, provenance, and defensive control plane | `gpt-doug-llm/safety-shield` |

The machine-readable source of truth is [`federation/registry.json`](federation/registry.json).

## Federation contract

Every member must preserve these invariants:

1. **Evidence before authority.** Model output is a proposal, not authorization.
2. **Independent reasoning first.** Agents should produce initial views before seeing the group answer when practical.
3. **Dissent is data.** Strong counterarguments remain attached to the decision record.
4. **Ontology is shared context.** Objects, links, provenance, confidence, and outcomes are explicit.
5. **Policy sits between reasoning and mutation.** Material actions remain bounded by deterministic controls and human authority where required.
6. **Simulation precedes consequential changes.** When a safe simulation or dry-run is available, use it.
7. **Outcomes feed the graph.** The federation learns from measured results, not self-reported success.
8. **External authorization is external.** This repository does not manufacture Palantir access, government authority, clearances, credentials, contracts, or third-party permissions.

## Quick start

```bash
python -m north_star_federation status
python -m north_star_federation validate
python -m north_star_federation member gpt-doug-max
```

Run tests:

```bash
python -m pytest -q
```

## Repository layout

```text
north-star-federation/
├── README.md
├── CHARTER.md
├── SECURITY.md
├── pyproject.toml
├── federation/
│   ├── registry.json
│   └── policies.json
├── src/north_star_federation/
│   ├── __init__.py
│   ├── __main__.py
│   └── registry.py
└── tests/
    └── test_registry.py
```

## Status language

- **implemented** - code exists and is part of the current GPT-Doug ecosystem.
- **source-linked** - the federation tracks a canonical source but does not claim deployment.
- **integration-ready** - connector/runtime exists but requires external authorization/configuration.
- **planned** - architecture/roadmap item only.

## Independence statement

THE NORTH STAR FEDERATION, GPT-DOUG-LLM-MAX, ZYRA, THE BLACK HOUSE, KRAKEN JUTSU, A.E.O., SHADOW GLASS, GLASS ONION, and related Sonoxo project names are independent software/project artifacts. References to public agencies, companies, products, standards, patents, or research are interoperability, research, provenance, or design context and do not imply endorsement, agency status, clearance, contract award, certification, or affiliation.
