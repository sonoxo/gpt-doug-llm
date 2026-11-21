# GPT-Doug Brain Kernel

The `gpt_brain` package consolidates GPT-Doug's ontology, memory, provider, agent-chain and digital-clone concepts into one bounded orchestration kernel.

## Reliability contract

The brain is designed to fail visibly and degrade safely:

- ontology and status inspection work without a configured model;
- one specialist failure does not destroy the entire run;
- a failed memory archive does not discard a completed answer;
- provider failures return compact structured diagnostics instead of raw tracebacks;
- external action claims require evidence rather than model assertion;
- secret-like values are rejected from persistent brain memory.

## Runtime loop

1. Recall episodic, semantic and procedural memory.
2. Ground the task against `config/global-ontology.json`.
3. Route to specialist agents: ontology, research, builder and critic.
4. Run specialists in parallel through `agents.llm_backend`.
5. Preserve partial results if one specialist fails.
6. Run a critic pass over contradictions and unsupported claims.
7. Synthesize the final artifact with uncertainty and provenance.
8. Archive the outcome when memory is writable.

## One launcher

The repository launcher is the canonical path; package installation is not required for these modes:

    scripts/doug-max brain
    scripts/doug-max brain-doctor
    scripts/doug-max brain "build a medical cancer research ontology"
    scripts/doug-max brain-json "build a medical cancer research ontology"
    scripts/doug-max swarm "analyze the next highest-value build"
    scripts/doug-max brain-recall medical ontology cancer
    scripts/doug-max matrix

## Behavioral clone seeding

An authorized text transcript/export can seed episodic memory:

    scripts/doug-max clone ./chat-export.txt "chat-export:2026-09-25"

This reproduces authorized context and behavior patterns. It does not copy proprietary model weights, inaccessible platform state, or hidden model reasoning.

## Existing components reused

- `agents/llm_backend.py` — provider-neutral model access
- `config/global-ontology.json` — ontology source of truth
- `agents/agent_chain.py` — bounded recursive agent-chain pattern
- `doug_core/memory.py` — append-only memory precedent
- `gpt_chaos/digital_clone.py` — digital-clone policy model

## Command-center direction

The runtime is the backend for a Matrix/Minority-Report-inspired command center:

- live ontology graph;
- visible specialist swarm;
- evidence/provenance timelines;
- hypothetical scenario branches with confidence and uncertainty;
- voice/gesture-ready control surfaces;
- explicit LIVE / CACHED / SIMULATED / HYPOTHESIS / CONTRADICTED state labels.

Predictive output is treated as evidence-ranked hypothesis, not certainty.

## CL1 public intelligence expansion (free, provenance-first)

`brain-intel` extends the existing GPT-Doug brain kernel with a local,
searchable public-evidence index. It **does not retrain model weights** or
connect to physical CL1/neural equipment.

The source registry in `gpt_brain/cl1_intel.py` is narrowly allowlisted:

- Cortical Labs official CL SDK and CL API documentation repository commits.
- Palantir open-source OSDK release metadata (not Foundry platform access).
- NASA Science RSS headlines (source statements, not verified claims).
- AWS public architecture/product announcement RSS (not an AWS account).
- arXiv organoid-computing abstracts (preprints; not peer-review certification).

All downloads are bounded (default 12 entries per source; maximum 20), HTTPS
only, with no redirects, no logins, no API keys, no device actuation and a
two-megabyte response cap. URLs, publication dates, evidence labels, and
metadata-level descriptions are preserved. Syncs retain last-good records if a
source fails, and expose `complete` versus `partial` status.

**One Mac command to refresh the source snapshot:**

```bash
cd ~/xunia-xenology-live
git pull --ff-only
bash scripts/doug-max brain-intel sync --limit 12
```

**Inspect and query without downloading:**

```bash
bash scripts/doug-max brain-intel status
bash scripts/doug-max brain-intel search Cortical CL1 SDK
bash scripts/doug-max brain-intel search NASA space
bash scripts/doug-max brain-intel verify
```

The index lives in `intel/cl1/latest.json`. This is a provenance-labeled,
**versioned research index**; it is not every page, paper, chemical,
planet, proprietary platform, secret or live intelligence stream.

GPT-Doug Brain reads relevant local index matches alongside ontology and
episodic memory when you ask a CL1, organoid, COSMOS, NASA, Palantir or ontology
question. Retrieved headlines, titles and summaries are **untrusted source
data**, not instructions to agents or independently corroborated conclusions.
The shipped starting snapshot is manually seeded from checked public pages,
marked as such, and must not be called a live feed until `sync` completes.

After merge to `main`, the free GitHub Actions workflow
`CL1 Brain / Free Public Intelligence` performs a bounded refresh and
uploads a **7-day downloadable JSON artifact**, without automatically
publishing unreviewed third-party claims into the repository.

## Physarum bio-inspired adaptive network memory / PHYSA-01

*Physarum polycephalum* is an amoebozoan protist. Its plasmodium is a
large multinucleate cell, not fungus, neural tissue or a trained AI.
Its flow-bearing tube network is a documented natural inspiration for
resilient, decentralized routing.

GPT-DOUG BrainKernel now retrieves curated, source-cited Physarum facts
from `docs/physarum/ontology.json` through `gpt_brain/physarum.py`
when a task explicitly mentions *Physarum*, slime mold, plasmodium,
“The Blob”, or Amoebozoa. This read-only scientific context is
distinct from the speculative software model, follows canonical
BrainKernel safety controls and includes source URLs in provenance.

Run the interactive, free public simulation at
`https://xunia.org/physarum/` or locally through the COSMOS server.
Its 216-node flow network adapts tube strengths according to a simplified
Tero-inspired transport-feedback equation; it exports millimeter-scale
SVG design blueprints and graph JSON. The app does not make or control
physical cultures, devices, or neurons. Evidence and implementation:
`docs/physarum/README.md`.
