# GPT-Doug Cognitive Evidence Fusion — Offline Research Core

This release extends the existing ontology-first GPT-Doug Brain, BioPineal Phase II and governed Sensor Swarm. It does not claim artificial general intelligence, superintelligence, physical biochips, patented technology ownership, or access to all global networks.

## Architecture

Authorized observations (Sensor Swarm) -> validated read-only ontology export -> independent offline workers -> evidence brief -> human review. All workers are deterministic, not additional independently trained models.

- **Evidence curator**: query-aware ranking of bounded scalar observations; never invents missing data.
- **Consistency critic**: flags conflicting values from the same source at the same timestamp and cross-source disagreements. Temporal change alone is not a contradiction.
- **Freshness reviewer**: checks whether recorded observations exceed a declared age window.
- **Governance auditor**: reports source authentication, synthetic data presence, local-data redaction, and review gates.

Workers run concurrently using Python's standard library; no paid tokens, network access, database server, GPUs, model downloads or API keys. This increases **auditability and engineering capability**, not the inherent intelligence of the underlying language model.

## One-command offline demo

~~~sh
bash scripts/doug-max super-ai demo
bash scripts/doug-max super-ai status
bash scripts/doug-max super-ai live-demo
~~~

The live-demo command starts a localhost-only interactive research console at http://127.0.0.1:8777/. Users can change the question and inspect source-linked reported readings, disagreement counts, freshness and policy warnings. It uses only demo evidence and no personal or physical sensor data. Stop with Ctrl+C.

The demo creates a temporary local database solely to assemble the existing BioPineal patent-evidence + synthetic heartbeat graph. Nothing is transmitted, polled on the network, or deployed. The temporary database is removed when the command exits. The run is blocked if GPT-Doug's cooperative AI kill switch is engaged; read-only status remains inspectable.

## Analyze an existing authorized sensor-swarm export

First prepare a local sensor journal using an explicitly authorized manifest, as documented in [SENSOR_SWARM.md](SENSOR_SWARM.md). Then:

~~~sh
bash scripts/doug-max swarm-sensors ontology > /tmp/gpt-doug-sensor-ontology.json
bash scripts/doug-max super-ai brief --graph /tmp/gpt-doug-sensor-ontology.json --question "Is the BioPineal patent record verified?"
~~~

For local data, analysis **redacts** authorized_local observations by default. Only the operator can request local observations explicitly:

~~~sh
bash scripts/doug-max super-ai brief --graph /tmp/gpt-doug-sensor-ontology.json --question "ambient reading" --include-local
~~~

Write a brief and check its deterministic replay digest (which is **not** source authentication):

~~~sh
bash scripts/doug-max super-ai demo > /tmp/gpt-doug-brief.json
bash scripts/doug-max super-ai verify /tmp/gpt-doug-brief.json
~~~

## Bounded security contract

1. Exactly one explicit, local JSON graph, maximum 1 MiB. Symlink input files are rejected.
2. Graph checksum/schema and typed source/observation links are checked; SHA-256 self-digests are never elevated to trustworthy signatures.
3. Supports up to 512 nodes, 512 edges and 128 observations; output contains at most 48 individual observations.
4. Only policy-allowed object types and bounded numerical, Boolean, or predefined status-enum readings are accepted. Text instructions, raw documents, people, faces, residences, live military units, weapon targets and credential-like data cannot be evidence inputs.
5. An unverified source or an unverified patent excerpt remains **UNVERIFIED** regardless of number of confirmations, lexical relevance score or local checksum.
6. Privately authorized local observations do not appear in a default brief without --include-local.
7. Research runs are advisory: no ontology promotion, no device actuation, no remote data access, no external action, and no automatic publication.
8. AI kill-switch is checked before and after the cognitive review. A software kill switch controls cooperating GPT-Doug processes only, not unrelated third-party AI infrastructure.

**Note on apparent confidence:** relevance rank and event counts are not probabilities of truth. Source authenticity and technology-use rights are independent, human-reviewable requirements.

## Automated validation

~~~sh
python3 -m unittest discover -s tests -p 'test_cognitive_fusion.py' -v
python3 -m unittest discover -s tests -p 'test_sensor_swarm.py' -v
python3 -m unittest discover -s tests -p 'test_biopineal_phase2.py' -v
bash -n scripts/doug-max
~~~

Run CI on Python 3.11 and 3.12. Broader repository security and regression failures remain separate release gates. Physical manufacturing, patent rights verification and runtime global feeds are not part of this release.

## Future milestones (not yet built)

- Signed, authenticated evidence and device identity verification.
- Human-reviewed promotion of independently verified information into durable ontology memory.
- Evaluations for hallucination, data poisoning, schema drift, privacy leakage, and contradiction recall.
- Optional explicitly configured local language-model adapter that consumes *sanitized evidence briefs* and respects model-stop and egress controls.
- Operator-visible inspection history and independently auditable approval logs.
