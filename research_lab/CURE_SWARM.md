# Bio-Gpt Cure Swarm — oncology evidence research

This is a **free-first, operator-controlled, five-role oncology research metadata pipeline**, not an unlimited AI swarm and **not a cure, treatment plan, clinical decision support device, or experimental drug generator**. The software cannot discover or validate a cure by itself. The "infinite" objective means research cycles can be repeated, bounded and independently evaluated over time. No background service or unlimited compute is activated by default.

The implementation extends Bio-Gpt with a *separate evidence pipeline*. It does not change the stability proofs for the mathematical Bio-Hilbert toy model; evidence metadata is not converted into a biological efficacy equation.

## Quick start (Python 3.9+; standard library only)

From a checked-out branch/repository root:

```bash
bash scripts/doug-max cure-swarm demo
bash run-Cure-Swarm.command         # interactive local research dashboard
bash run-Cure-Swarm.command --once  # one-shot safe diagnostics
bash scripts/doug-max bio-gpt open # select 5 for offline Cure Swarm
```

The three-record demo is entirely **synthetic**. IDs start with `SIM-`; none identify real trials or discoveries. Both terminal menus refuse automatic external fetching; online retrieval must be explicitly invoked from the separate CLI.

To search fresh **public metadata** from ClinicalTrials.gov and Europe PMC (explicit opt-in, HTTPS GET, max 10 records from each source per run):

```bash
bash scripts/doug-max cure-swarm online --query 'glioblastoma' --per-source 5 --save-snapshot oncology-snapshot.json > oncology-review.json
bash scripts/doug-max cure-swarm analyze oncology-snapshot.json > oncology-replay.json
bash scripts/doug-max cure-swarm verify oncology-replay.json
```

If the GPT-Doug preflight rejects the network command, investigate that policy rather than disabling it. You can also run `python3 -m research_lab.cure_swarm online --query 'glioblastoma'` as an explicit operator-initiated standalone program if you are authorized to use the public APIs. No API keys, paid tokens, patient records or cloud accounts are required for these two public interfaces. Public providers may throttle requests or change APIs; connectivity is not guaranteed.

To compare two recorded research cycles (never assume missing a capped page means a study was withdrawn):

```bash
python3 -m research_lab.cure_swarm compare old-snapshot.json new-snapshot.json > review-diff.json
```

## What the five roles actually execute

| Component | Bounded and observable software action |
|---|---|
| GPT-Doug | Validates oncology topic and enforces source record limits |
| GPT-Pineal | Indexes evidence records with canonical identifiers and SHA-256 content hashes |
| GPT-Doug-Chaos | Flags missing posted results, early phases, withdrawals, preprints and retraction signals |
| GPT-Doug-Shaggoth | Sets hard human medical review gate and forbids patient-specific treatment recommendations |
| GPT-Doug-Redpanda | Produces a consistent report and review queue with no autonomous subagents or external effects |

The roles are deterministic Python stages, not five active LLM instances. Their outputs are **research questions, not conclusions that treatments work**. Exact replay verifies JSON consistency, not whether a published result is accurate, peer-reviewed, or clinically relevant.

## Public sources and provenance

- [ClinicalTrials.gov API](https://clinicaltrials.gov/data-api/about-api) — registration metadata and available reported result status; registering a study is **not** evidence that a treatment works.
- [Europe PMC REST API](https://europepmc.org/RestfulWebService) — bibliographic publication metadata and preprint identifiers. A publication can be wrong, outdated, retracted or not generalizable.
- [National Cancer Institute: How clinical trials work](https://www.cancer.gov/research/participate/clinical-trials/how-trials-work) — trials must assess safety and effectiveness and require safeguards before routine medical use.

All network destinations are hardcoded and HTTPS-only. The program rejects redirects, caps downloaded bytes and batch sizes, validates identifiers, and never transmits user health data. Date stamps are UTC. Content hashes help detect local changes **but are not digital signatures or independent provider attestations**. Always open the source URLs and have qualified researchers review complete primary studies, endpoints, adverse events, designs and competing evidence before forming scientific conclusions.

## Future regulated, authorized extensions

Add registry outcome-level extraction, preregistered statistical evaluation, explicit retraction checks, qualified oncologist/pharmacologist review, institutional review and reproducible analysis of consenting, deidentified datasets. Any wet-lab or human-facing study requires actual institutional oversight, safety review, ethics approval and appropriate regulatory compliance; this code does not provide or automate those.

The optional GitHub Actions workflow is **manual-trigger only**, capped at one query and five records per source by default; it consumes whatever GitHub Actions quota applies. There is no perpetual background job or claim that cloud resources are free indefinitely.
