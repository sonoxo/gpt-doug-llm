# Maven Live Sync

Maven Live Sync is the governed bridge from approved Palantir Maven / Foundry ontology exports into the public XUNIA Maven Ontology and Planet xZoon.

## Flow

```text
Palantir Maven / Foundry
        |
        | approved ontology export
        v
maven-sync/approved/*.json
        |
        | GitHub Actions: Maven Live Sync
        v
tools/maven_live_sync.py
        |
        +--> validate approval + provenance + graph integrity
        +--> deterministic ID/link reconciliation
        +--> governed Action checks
        v
docs/maven-ontology/ontology.json
        |
        +--> docs/maven-ontology/sync-log.json
        v
XUNIA Pages / Planet xZoon
```

## Required export envelope

Every export must be JSON and use this shape:

```json
{
  "schemaVersion": "maven-export/1.0",
  "source": {
    "system": "Palantir Maven",
    "exportId": "unique-export-id",
    "uri": "palantir://your-project/ontology/export-id",
    "generatedAt": "2026-09-10T15:00:00Z"
  },
  "approval": {
    "status": "approved",
    "scope": "ontology-sync",
    "approvedBy": "operator-or-governance-id",
    "approvedAt": "2026-09-10T15:01:00Z"
  },
  "nodes": [],
  "links": []
}
```

`approval.status` must be `approved` and `approval.scope` must be `ontology-sync`. Pending, rejected, malformed, or out-of-scope exports are rejected without modifying the production graph.

## Nodes

Minimum node fields:

```json
{
  "id": "maven:mission:demo",
  "label": "Demo Mission",
  "objectType": "Mission"
}
```

Optional fields include `type`, `status`, `confidence`, `lat`, `lon`, `desc`, and upstream `provenance`. Missing globe coordinates are generated deterministically from the canonical ID.

Status must be `candidate` or `verified`. Confidence must be between `0` and `1`.

### Governed Actions

Action mode is restricted to:

```text
recommend | simulate | approved
```

An Action in `approved` mode must carry an `approvalId`, and that identifier must resolve to an `Approval` object in the merged ontology.

## Links

Either form is accepted:

```json
["maven:mission:demo", "maven:capability:search", "REQUIRES"]
```

or:

```json
{
  "source": "maven:mission:demo",
  "target": "maven:capability:search",
  "relation": "REQUIRES"
}
```

Every endpoint must resolve to an ontology node after reconciliation.

## Provenance

The bridge attaches the export source system, source URI, export ID, generation timestamp, approver, approval timestamp, and sync method to each imported node. Upstream provenance supplied by Maven/Foundry is retained under `provenance.upstream`.

## Idempotency

Canonical node IDs replace older versions of the same object. Links are deduplicated. Reprocessing an identical approved export produces no new production commit.

## Free mode

The bridge uses Python standard library code, GitHub Actions, GitHub Pages, and the existing browser-side Planet xZoon visualizer. It does not require a paid database or paid inference API.

## Triggering sync

The production workflow runs automatically when an approved JSON export is committed under:

```text
maven-sync/approved/*.json
```

It can also be launched manually with the `Maven Live Sync` workflow and an approved repository path.

A Palantir-side exporter can complete the final connection by writing its approved export to this folder through an authorized Git workflow. Do not put Palantir tokens, passwords, private keys, or bearer credentials inside export files or this repository.
