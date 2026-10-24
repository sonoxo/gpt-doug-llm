# GPT-DOUG Recursive Fleet Planner

A small, standard-library extension for the GPT-DOUG / Universal Hive ecosystem.
It adds bounded recursive task decomposition and metadata-only credential
rotation planning. It does **not** create model copies, launch cloud workers,
read raw secrets, or mutate provider credentials.

## Why "recursive"

A goal is expanded into subgoals, then expanded again by a caller-supplied
decomposer until the node budget, depth budget, or a leaf is reached. Hard ceilings
are 16 levels and 10,000 nodes per plan (defaults: 4 levels and 64 nodes). Stable
node IDs make a plan traceable. Cycles and repeated sibling tasks are skipped.
The default decomposer supplies inspectable starting workstreams for fleet
scaling, key rotation, and public communications. It makes no model calls.

## Ontology and Hivemind integration

`ontology.json` defines the Mission, PlanNode, WorkerPool, CredentialRecord, RotationBatch, Approval, and Evidence object types and their governed links. The CLI is integrated into the existing Hivemind module:

```bash
python3 -m hivemind.cli recursive-plan "Build a bounded worker fleet" --max-depth 4 --max-nodes 64
```

This command plans only; it does not summon or execute a swarm.

## Quick start

From the repository root:

```bash
python3 -m recursive_fleet.planner plan "Build a bounded GPT-DOUG worker fleet"
python3 -m recursive_fleet.planner plan "Plan owner-approved credential rotations" --max-depth 4 --max-nodes 64
python3 -m unittest tests.test_recursive_fleet_planner -v
```

## Credential rotation: plan, don't blindly rotate

Use only a JSON metadata inventory; do not place tokens, passwords, key
material, or credential values in that file. Required fields: `credential_id`,
`provider`, `alias`, and `environment`. A record enters a candidate batch
only when both `rotation_requested` and `owner_confirmed` are explicitly
`true`. Everything else is held with a reason.

```bash
python3 -m recursive_fleet.planner rotation-plan --input credential-metadata.json --batch-size 5
```

Output is `DRY_RUN_ONLY`. The program refuses secret-like field names and never
calls external providers. An authorized operator must issue the replacement at
the provider, validate it, migrate consumers gradually, verify health, and
revoke the old credential only after success and separate approval. Prefer
short-lived, workload-specific identities over shared "universal keys."

## Virtual fleet vs. real workers

A large logical namespace can represent possible work IDs or virtual worker
slots without instantiating processes. Real concurrency remains constrained by
CPU/RAM, provider rate limits, cost budgets, queue throughput, retries and
human approval. The requested target of `999999999999999999999` is therefore
a **virtual address-space aspiration**, not a claim that this software creates
that many agent copies. Scale by demand and measured capacity, not by spawning
unbounded processes.

## Build sequence

1. Inventory existing modules and their authority boundaries.
2. Define stable ontology IDs for `Mission`, `PlanNode`, `WorkerPool`,
   `CredentialRecord`, `RotationBatch`, `Evidence`, and `Approval`.
3. Add a scheduler with idempotent jobs, leases, cancellation, per-provider
   limits, bounded retries, backpressure, and dead-letter handling.
4. Run load tests and failure-injection tests using synthetic jobs first.
5. Connect secret-manager/provider APIs only through least-privilege identities
   with narrow scopes and explicit operator approval.
6. Publish reproducible benchmark results; do not claim capacity absent tests.

## Controls

- Hard maximum depth and node count on every plan.
- Deterministic IDs and duplicate/cycle detection.
- Metadata-only credential records; secret-like field names rejected.
- No remote writes, credential generation, provider calls, or deployment hooks.
- All provider-side rotations remain manual/authorized and auditable.
