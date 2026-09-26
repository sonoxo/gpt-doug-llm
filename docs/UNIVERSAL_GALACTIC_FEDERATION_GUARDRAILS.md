# GPT-DOUG / DOUG-MAX — Universal Galactic Federation Guardrails

This is the next-generation defensive guardrail layer for GPT-DOUG / GPT-DOUG-MAX.

**Important truth boundary:** `Universal Galactic Federation Law` is a project governance label in this repository. It is not represented as an enacted statute, regulation, government order, accreditation, or external legal authority.

## What is now wired

```text
PUBLIC / INTERNAL EVIDENCE
        ↓
PROVENANCE + HASH / SOURCE STATUS
        ↓
CORRELATION + CLASSIFICATION
        ↓
GPT-DOUG PROPOSAL
        ↓
GUARDRAIL / POLICY VALIDATION
        ↓
HUMAN AUTHORIZATION WHEN REQUIRED
        ↓
BOUNDED EXECUTOR
        ↓
GPT-CHAOS / INDEPENDENT CRITIC
        ↓
AUDIT + MEMORY PROMOTION
```

The canonical ontology is:

`safety-shield/ontology/universal-galactic-federation-guardrails-v1.json`

## Patent intelligence

The initial cyber seed registry is:

`intel/sources/2026-09-22-cyber-patent-guardrail-seeds.json`

The records are derived from a user-supplied USPTO Patent Public Search result set dated September 22, 2026. Only **US-12744799-B1** had full text visible in the supplied capture; the remaining records are explicitly marked metadata-only until their official document text is retrieved and reviewed.

Each seed stores an official Patent Public Search external-search permalink using the format documented by USPTO.

### Targeted corpus work

The existing reader remains the bounded targeted-query path:

```bash
doug-max patent-corpus crawl --query cyber --workers 6
```

It downloads discovered USPTO PDFs, hashes them, extracts text, and builds SQLite FTS5 search state.

### Corpus-scale / “all patents” work

Do **not** attempt to scrape the entire Patent Public Search UI with millions of browser requests.

For corpus-scale research, use the USPTO Open Data Portal / PatentsView bulk datasets and ingest those bulk artifacts offline with resumable manifests and hashes. Patent Public Search remains the targeted verification/search layer.

The system must keep:

```text
full_uspto_corpus_ingested = false
```

until a completion manifest proves that every intended bulk artifact was acquired, verified, indexed, and reconciled.

## YouTube evidence gate

Registered source:

`https://www.youtube.com/watch?v=6pV7-wxLnrA`

Registry:

`intel/glassonion/media/6pV7-wxLnrA.json`

The current state is intentionally:

```text
BLOCKED_UNTIL_EVIDENCE
```

The URL alone is not enough to infer the video's content. When an actual transcript is available:

```bash
doug-max guardrails media-ingest path/to/transcript.txt
```

The transcript is normalized, chunked, SHA-256 locked, and stored as source evidence. Speaker claims remain attributed source claims until independently corroborated.

## Local persistent guardrail memory

Install the ontology, source registry, and patent permalinks into local GPT-DOUG state:

```bash
doug-max guardrails install-memory
```

Default state:

```text
~/.config/gpt-doug/galactic-guardrails/
  guardrail-ontology.json
  media-source.json
  patent-permalinks.jsonl
  manifest.json
  media/
```

This is **persistent indexed/configuration memory**, not model-weight training.

## Validation

Every `doug-max` invocation runs a fail-closed guardrail preflight when the ontology is present.

Manual checks:

```bash
doug-max guardrails validate
doug-max guardrails status
doug-max guardrails status --benchmark
doug-max guardrails permalinks
```

## CPU / GPU / RAM / universal memory / quantum

Physical hardware is not magically upgraded by changing software.

GPT-DOUG's compute fabric instead:

- detects CPU count and physical RAM;
- detects CUDA, Apple MPS, MLX, and keeps CPU fallback;
- uses bounded concurrency rather than assuming unlimited compute;
- uses tiered memory: request context → bounded cache → local indexed persistence → governed evidence/ontology → external source references;
- may detect optional quantum SDK adapters, but never interprets SDK installation as proof of QPU access;
- treats AGI and SAGI as project capability labels unless a defined evaluation demonstrates the claimed capability.

Run:

```bash
doug-max compute-profile
```

## Defensive cyber boundary

This layer is for defensive, authorized environments.

It does not enable:

- credential theft;
- unauthorized exploitation;
- destructive intrusion;
- offensive replication;
- uncontrolled agent replication;
- automatic third-party action;
- unattended containment;
- autonomous transfer of funds;
- weapon targeting or release.

The operating rule remains:

```text
EVIDENCE BEFORE AUTHORITY
PROVENANCE BEFORE MEMORY
AUTHORIZATION BEFORE ACTION
VERIFICATION BEFORE CLAIM
```
