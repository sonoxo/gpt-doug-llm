# GPT-DOUG // Palantir Sovereignty Performance Layer

This document maps the operator-supplied Palantir sovereignty architecture visual into a concrete GPT-DOUG runtime model for **memory, compute, GPU selection, and speed**.

The visual is used as an architecture reference, not as evidence that this repository controls Palantir infrastructure or possesses any tenant capability beyond what the configured, authorized environment exposes.

## Seven-layer reference model

| Sovereignty layer | GPT-DOUG implementation meaning |
| --- | --- |
| Data Sovereignty | governed data, evidence, lineage, retention, source ownership |
| Compute & Logic Sovereignty | bounded CPU/GPU routing, deterministic functions, transform policy |
| Model Sovereignty | provider-neutral model routing, model/version provenance, eval evidence |
| Semantic Sovereignty | Ontology objects, links, properties, entity identity and shared meaning |
| Kinetic Sovereignty | permissioned Actions/effects with audit, review and rollback where possible |
| Application Sovereignty | operator-owned apps, browser tools, OSDK clients and governed interfaces |
| Knowledge Sovereignty | information → reasoning → action → consequences → feedback-to-knowledge |

## Memory architecture

GPT-DOUG uses a tiered memory contract:

```text
L0  Current request/context
 ↓
L1  bounded in-process TTL/LRU cache
 ↓
L2  optional local persisted indexes/checkpoints
 ↓
L3  governed Ontology / dataset / evidence source of truth
```

The cache is an acceleration layer, not an authority layer. Cached state is disposable, bounded, and must preserve provenance.

`sovereignty_performance.TTLRUCache` implements the L1 contract with TTL expiration, LRU eviction and hit-rate telemetry.

## Compute routing

`sovereignty_performance.py` detects the local runtime instead of assuming a GPU exists.

Supported local routing signals:

- `cuda` when Torch reports CUDA runtime availability;
- `mps` when Torch reports Apple Metal Performance Shaders availability;
- `mlx` on supported Apple-silicon environments when MLX is installed;
- `cpu` as the mandatory fallback.

Default priority:

```text
CUDA → MPS → MLX → CPU
```

This is local compute routing only. It does not select, allocate, or control Foundry compute resources.

## Speed policy

Speed improvements are ordered by reducing repeated work before adding hardware:

1. bounded TTL/LRU caching;
2. request deduplication;
3. batching where semantics permit;
4. bounded concurrency;
5. lazy loading;
6. workload-specific accelerator routing;
7. network/API latency telemetry;
8. repeatable benchmark snapshots.

Run the local profile:

```bash
python sovereignty_performance.py
```

Run the dependency-free local microbenchmark:

```bash
python sovereignty_performance.py --benchmark
```

The microbenchmark is a regression signal only. It is **not** a model tokens-per-second benchmark, GPU benchmark, or Foundry performance measurement.

## Environment controls

```bash
export GPT_DOUG_CACHE_ENTRIES=256
export GPT_DOUG_CACHE_TTL_SECONDS=300
export GPT_DOUG_MAX_CONCURRENCY=8
```

Concurrency is clamped to the local CPU count. Cache size and TTL are bounded to positive values.

## Palantir integration rule

The existing Foundry client remains responsible for tenant access, exact-host HTTPS restrictions, read/write gates, Ontology APIs and authorization boundaries. The sovereignty performance layer may accelerate local work around those calls, but it never bypasses Palantir authorization and never turns local cache state into governed truth.

## Knowledge-base registration

The canonical machine-readable architecture lives at:

`safety-shield/agents/knowledge/palantir-stack-v1.json`

Version `1.2.0` adds:

- the seven sovereignty layers;
- the information → reasoning → action → consequences knowledge cycle;
- tiered memory authority;
- runtime CPU/GPU capability detection;
- accelerator priority;
- cache/concurrency/speed policy;
- explicit performance truthfulness rules.
