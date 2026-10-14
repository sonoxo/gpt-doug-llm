# GPT-Doug Universal Council — Stark + Ironman + Orca + Chaos + MLM

**Scope:** A *working, bounded research-software council*, not artificial superintelligence or a biological neuron chip. This project has no self-propagation, automatic upgrades, external agent recruitment, hidden collection, or hardware actuation. All agents remain within operator permissions.

## Composition

| Component | Concrete integration | Default state |
| --- | --- | --- |
| GPT-Doug-LLM | Existing ontology-grounded GPT-Doug architecture and kill switch | Common control plane |
| GPT-Stark-LLM | `StarkPlanner.plan`: 1–6 typed, SHA-256-bound steps | Offline planning |
| GPT-Ironman-LLM | `IronmanRuntime.execute`: operator-registered tools only | No actions; dry-run |
| GPT-Orca-LLM | `OrcaCouncil.run`: planner / researcher / critic / synthesizer | Model calls disabled |
| GPT-Chaos | Declared worker fabric and static adversarial checks | Static checks only; no worker spawning |
| GPT-Doug-MLM | Opt-in `ProviderRegistry` adapter reviews | No provider automatically contacted |
| Universal synthetic biochip | Reuses `research_lab.orca_neurocloud.NeuroGraph` | Deterministic local simulation |
| Bounded RSI | Compares externally measured metrics and passes candidates to review | Proposal evaluation only |

The report maintains the distinction between **source-supplied claims**, **model suggestions**, **measured test results supplied by an evaluator**, and **reviewed human decisions**. It cannot independently establish truth from arbitrary caller inputs. JSON source IDs and SHA-256 digests make records traceable but do not prove the source is authentic.

## Run without internet or paid APIs

```bash
python3 -m agents.universal_council 'Design an ontology-backed medical evidence index' --neurons 16 --cycles 3
python3 -m unittest agents.tests.test_universal_council agents.tests.test_stark_ironman agents.tests.test_gpt_orca_llm tests.test_orca_neurocloud -v
```

The standard run **does not invoke a language model**. It produces a transparent offline Stark plan, Ironman dry-run, Chaos checks, synthetic neural states and empty RSI candidate evaluation. The result is JSON with the root `schema: gpt-doug.universal-council.v1` and integrity digest.

To invoke the four-role Orca model council with an explicitly configured provider:

```bash
GPT_DOUG_PROVIDER=ollama OLLAMA_MODEL=llama3 python3 -m agents.universal_council 'Review public scientific claims' --live-orca
```

Ollama must already be running with the selected model installed; this command **does not** download models or spin up a hosted service. Paid provider use is subject to explicit provider configuration. Model output is unverified, and failed provider calls are reported rather than silently replaced with made-up inference.

Source input can be a small local JSON array passed via `--evidence-json`:

```json
[{"source_id":"s1","statement":"Research claim requiring validation","provenance":"https://example.org/source"}]
```

This is user-supplied evidence, not independently authenticated evidence. Do not feed restricted government, patient-identifiable, personal or classified data to public models or public GitHub.

## Bounded iterative improvement (RSI)

```python
from agents.universal_council import (
    UniversalCouncil, Metrics, ImprovementCandidate,
)
from agents.stark_ironman import Evidence

baseline = Metrics(quality=0.6, safety=0.9, efficiency=0.5)
candidate = ImprovementCandidate(
    candidate_id="index-v2",
    description="Indexing change evaluated by an operator's own benchmark",
    measured=Metrics(quality=0.7, safety=0.9, efficiency=0.6),
    tests_passed=True,
    source_ids=("bench-001",),
    evaluation_ref="bench-001",
)
report = UniversalCouncil().run(
    "Assess a proposed local search index improvement",
    evidence=[Evidence("bench-001", "Benchmark report metadata", "authorized-local-evaluation")],
    baseline=baseline,
    improvement_rounds=[[candidate]],
)
print(report["bounded_rsi"])
```

**Scores are caller-provided measurement assertions**, not calculated from an unseen benchmark. Eligible candidates are only sent to **human review**; no patch is applied, no model trained, no baseline auto-promoted and no repository merged. The evaluator caps the number of candidates (8 per round) and rounds (3). Unverified provenance, absent evaluation evidence, failing tests, reduced safety, scope/permission expansion or non-positive utility gain all block candidates.

For real upgrades, maintain a separate owner-operated CI/evaluation system that produces signed or verifiable artifacts, independently assesses performance/regressions, and requires human approval and secure deployment. Do not let model output become an executable tool specification by itself.

## Safety and capacity ceilings

- Up to **6** Stark steps, **16** provenance-tagged sources, **4** registered MLM reviewers.
- Up to **64** simulated neurons and **8** deterministic simulation ticks.
- Up to **3** RSI evaluation rounds, **8** candidates per round; unchanged baseline.
- Operator-maintained `ai_killswitch.require_ai_allowed` checks at each component boundary.
- No automatic network probing, cross-repository injection, permission escalation, botnets, self-replication, remote execution, or access to unauthorized systems.
- The neural model is a numerical toy graph and cannot grow organoids, interface with neurons, operate a robot, or establish consciousness.

## Dependencies and integration

This research branch builds on the **GPT-Stark / Ironman draft branch** (PR #421) and vendors the bounded **GPT-Orca council** and **synthetic NeuroCloud** modules from the Orca development branch (PR #417, including its merged PR #418). After upstream PRs are merged, resolve overlap and rebase the integration branch before merging to `main`. Avoid merging duplicates or overwriting upstream changes.

The first-party graph is the offline `NeuroGraph` in `research_lab/orca_neurocloud.py`. `GPTChaos.WORKER_FABRIC` metadata may be read, but **Chaos swarm workers are not launched** by the council. MLM reviewers only run when a caller passes an explicit adapter registry and selected provider names. A real Ironman tool must be registered by the operator separately; the council does not expose automatic tool dispatch.

## Independent validation

- Focused unit tests use deterministic model and neuron fakes; they do **not** prove actual model capability, network security or hardware performance.
- The sibling Orca and NeuroCloud suites exercise their respective components.
- Run all focused tests and repository CI prior to promotion. Cross-project CI can fail independently; do not declare production readiness solely on these tests.