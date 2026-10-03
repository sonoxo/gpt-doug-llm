# Engineering invention-review worksheet

Status for every candidate: prototype implemented; novelty unassessed; no patent
application prepared or filed. GPT-Doug is a development aid, not a named inventor.
Human inventors/contributions must be recorded from actual evidence, not inferred
from repository ownership. Publishing this source is a public disclosure; review
filing implications with a patent professional.

## 1. Evidence-bound admission

Problem: a previously approved action may run after code, data or policy changes.
Prototype: bind approval to one canonical snapshot, persist a hashed bearer receipt,
and conditionally consume it once if versions, issuer and expiry still match.
Known building blocks: content addressing, capability tokens, optimistic concurrency,
single-use transaction records. None is claimed as new.
Experiment: mutate each binding independently; compare rejection and replay rates
with an approval that binds only the action. Measure contention and crash behavior
before making throughput/reliability claims. Production gap: identity and atomic
action execution. Possible claim distinction: not established.

## 2. Dependency-aware repair planning

Problem: selecting too few tests misses downstream regressions; selecting all tests
can increase feedback time. Prototype: reverse graph closure with coverage gaps and
rollback revision boundaries. Known building blocks: build graphs, regression test
selection, dependency analysis. Possible claim distinction: not established.
Experiment: seed faults across an independently verified graph, compare selected
tests with the full suite, and record missed failures, time and stale-edge errors.
Do not disable full-suite gates on the basis of the synthetic demo.

## 3. Offline ontology reconciliation

Problem: disconnected replicas may conflict or lose provenance when synchronized.
Prototype: deterministic three-way object merge with conflict records, parent
hashes and deletion provenance. Known building blocks: three-way merge, version
control, replicated data structures. Possible claim distinction: not established.
Experiment: generate edit/edit, edit/delete and disjoint changes in different input
orders; verify stable results and zero silent conflict resolution. Next assess
schema and policy-aware merge rules against established approaches.

## 4. Verifiable research lineage

Problem: a source revision can leave downstream conclusions carrying stale citations.
Prototype: exact source anchors and transitive invalidation through claim dependencies.
Known building blocks: citation indexing, content hashing, data lineage and incremental
invalidation. Possible claim distinction: not established.
Experiment: change sources, offsets and quotes; compare detected invalidations with
a hand-labeled corpus. Semantic support requires a separate labeled evaluation;
an unchanged quote alone never establishes truth or legal applicability.

## Evidence required before filing review

- Named human contributors and dated conception records.
- Closest prior art, claim-by-claim distinctions and supporting searches.
- A specific technical improvement beyond combining known components.
- Reproducible experiments with baselines, failure cases and limitations.
- First public disclosure dates and a qualified patent review.

Repository patent watchlist: ../intel/briefings/2026-09-12-uspto-palantir-patent-landscape.md
(relative to repository root: intel/briefings/2026-09-12-uspto-palantir-patent-landscape.md).
That watchlist is not a complete prior-art search or freedom-to-operate opinion.
