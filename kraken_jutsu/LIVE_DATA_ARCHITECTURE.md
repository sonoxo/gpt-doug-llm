# Kraken Jutsu — Live Data + AIP Decision Architecture

Kraken Jutsu follows an AIP-style separation of **data, logic, actions, and security**.

## Data plane

Live/attributed evidence flows through adapters into normalized ontology objects.

```text
CISA KEV ─┐
NIST NVD ─┼─> adapter -> provenance -> object/link -> ontology.db
OSINT Ind ┤
USB Agents┘
```

Core portable storage is SQLite in WAL mode plus an append-only `audit.jsonl` stream.

### Object types

- `AgentCandidate`
- `Appointment`
- `ActionProposal`
- `DataSource`
- `Vulnerability`
- `Observation`
- `BlackHouseMember`

### Link types

- `ASSERTS`
- `ENRICHED_BY`
- `SUPPORTS`
- `CONTRADICTS`
- `HAS_APPOINTMENT`
- `HAS_ACTION_PROPOSAL`
- `PROMOTED_TO`

## Logic plane

The appointment engine scores each discovered GPT-agent against capability fit and assurance evidence.

Roles:

- `OFFICER`: orchestration, coordination, policy, delegation
- `CPR`: diagnosis, repair, recovery, rollback, verification
- `ADMIN`: infrastructure/configuration/deployment operations
- `LLM`: reasoning, coding, classification, analysis, summarization
- `MAX`: high-assurance multi-domain agent with broad benchmark evidence

`MAX` requires high integrity/test/provenance scores and multi-domain breadth; it cannot be earned from a name alone.

## Action plane

A role decision creates an `ActionProposal`. Appointment classification does **not** grant runtime privilege.

High-authority roles (`OFFICER`, `ADMIN`, `MAX`) generate proposals with `requires_approval=true`. This keeps fresh data and AI reasoning from silently becoming privileged execution.

## Security plane

Agent lifecycle:

```text
DISCOVERED -> QUARANTINED -> FINGERPRINTED -> VERIFIED
     -> ONTOLOGY JUDGMENT -> APPOINTED -> BLACK HOUSE
```

Controls:

- SHA-256 package fingerprints
- quarantine before execution
- benchmark/provenance/integrity thresholds
- append-only audit trail
- role separate from permissions
- third-party OSINT treated as evidence, not truth
- offensive validation restricted to owned/authorized lab contexts

## USB layout

```text
/Volumes/<USB>/
├── KRAKENXYZ/
│   ├── app/
│   └── kraken-jutsu
└── .krakenxyz/
    ├── ontology.db
    ├── audit.jsonl
    ├── agent-inbox/
    ├── quarantine/
    └── BLACKHOUSE/
        └── friends/
```

## Live feeds

Kraken reuses `kraken_jutsu.intel.GovernmentSourceRegistry` for government and standards sources, including CISA KEV. `NVDSource` adds NIST NVD CVE API 2.0 enrichment. The existing OSINT Industries adapter remains terms/authorization gated and should feed provenance-bearing evidence rather than unrestricted identity truth.
