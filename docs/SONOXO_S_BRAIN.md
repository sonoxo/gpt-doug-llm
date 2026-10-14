# Sonoxo S-Brain — executable cognition and trained-model bridge

S-Brain is a local-first **software brain** for `sonoxo/gpt-doug-llm`, not a claim
of general or superhuman intelligence, biological neurons or self-awareness.
It adds a persistent source-attributed evidence index, ontology-first search,
contradiction/transition flags and optional inference bridges to **actual**
GPT-Almighty Sonoxo SAGIQI Transformer weights and registered model councils.

## Architecture

```
                         GPT-Doug / S-Brain CLI
                                  |
        +-------------------------+--------------------------+
        |                         |                          |
   OntologyIndex            Evidence memory             Inference adapters
 (versioned read-only)       SQLite, source IDs          (all opt-in)
        |                  timestamps, SHA-256                 |
        +-------------- retrieval / audit -------------------+
                                  |
                          Source-grounded result
              (no independent source authentication assumed)

SAGIQI trained MLM: validated safetensors -> learned Transformer -> masked-token probabilities
SAGIQI council: explicit providers -> proposer output -> optional reviewer -> unverified hypotheses
```

Default mode is offline, works with Python standard library, and **does not
require tokens, keys, GPUs, cloud services, or new model downloads**. Neural
weights require the separate, explicitly installed `.[mlm]` dependency extra.

## Run without an LLM

```sh
python3 -m pip install -e .
gpt-sonoxo-s-brain status

gpt-sonoxo-s-brain remember \
  --subject NCT05023980 --predicate status --value 'active-not-recruiting' \
  --source-id clinicaltrials-2026-10-14 \
  --source-uri https://clinicaltrials.gov/study/NCT05023980 \
  --confidence 0.8 --observed-at 2026-10-14T13:00:00Z

gpt-sonoxo-s-brain ask 'NCT05023980 status'
gpt-sonoxo-s-brain heartbeat
```

This sample is a usage demonstration, **not an independently checked registry
finding**. Only submit findings you have the right to store. The stored
`confidence` field is explicitly **caller-assessed**, not a verified probability.

`--db /path/evidence.sqlite3` selects a separate local SQLite file; otherwise,
the store defaults to `~/.gpt-doug/s-brain/evidence.sqlite3`. `--ontology
/path/global-ontology.json` overrides the default version-controlled ontology.

## Actual trained neural prediction

```sh
python3 -m pip install -e '.[mlm]'
gpt-sonoxo-s-brain fill-mask \
  --checkpoint ~/.gpt-doug/models/almighty-sonoxo-sagiqi \
  --text 'the ontology stores [MASK] with provenance' --top-k 5
```

`fill-mask` loads the actual PyTorch/Safetensors model from draft PR #424,
validates SHA-256 and predicts tokens. It is **not** chat/instruction following.
Train new model weights separately using `gpt-almighty-sonoxo-mlm train`.
Do not use these predictions as medical, security or factual evidence.

## Optional real model synthesis

```sh
GPT_DOUG_PROVIDER=ollama gpt-sonoxo-s-brain ask \
  'NCT05023980 status' --live

GPT_DOUG_PROVIDER=ollama gpt-sonoxo-s-brain council \
  'Summarize evidence uncertainty' --models llama3 \
  --reviewers qwen2.5:7b
```

Ollama and the exact model IDs must already exist on an operator-owned host.
No models are pulled automatically. The council is limited by the existing
`SonoxoModelCouncil` registry and returns **unverified** model text.
Generated answers are never silently inserted into the evidence database.

## Evidence and safety controls

- Persistent SQLite memory; SHA-256 evidence identities, time-stamped attribution.
- Ontology lookup before memory recall, with explicit source IDs in results.
- Conflicting claims at the same observation time are flagged for review;
  differences over time are flagged as possible legitimate transitions.
- Secret-looking inputs are rejected before persistence; this is **not** a
  replacement for managed sensitive-data handling.
- No unrestricted network crawling, unauthorized collection or external control.
- No autonomous code writes, model retraining, permission expansion, swarm
  propagation, physical device commands, or production deployments.
- `ai_killswitch.require_ai_allowed` is applied to inference and evidence writes;
  database integrity checks remain available read-only.
- Historical source reports remain distinguishable from independent verification.
- Operator can delete/reset only the explicitly owned local database; no
  automatic memory deletion or government/system authorization is asserted.

## Check

```sh
python -m unittest tests.test_s_brain -v
```

Focused local harness results: **29 of 29 tests passed**, including real
SAGIQI training/weight loading, SHA-256 mismatch rejection, provenance,
SQLite restart, source contradictions, model registration, and stop behavior.
GitHub Actions also runs the same test suite on Python 3.11 and 3.12; read
its status before merge. The local test harness uses a compatibility shim for
the repo kill switch; GitHub CI runs against the actual repository implementation.

## Branch dependencies

S-Brain is stacked on **PR #424**, which contains the trainable SAGIQI model and
provider registry. Merge #424 or reconcile its changes before rebasing this PR
onto `main`. Do not label this a new trained superintelligent foundation model.
