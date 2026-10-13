# GPT-Doug Warfighter Research Core (local prototype)

**Scope:** Educational, synthetic research only. No classified or controlled information, operational readiness authority, troop tracking, targeting, weapon interfaces, or remote defense systems. This code does **not** prove quantum computing, real biological chips, or physical extra dimensions.

The public design specification is tracked in `docs/WARFIGHTER_RESEARCH_ONTOLOGY.md`. This file documents the runnable local prototype. The research-only schema has 21 object types and 16 directed relationship definitions. Synthetic scenarios never become authoritative operational data. Local review labels are not authenticated persons or external authorizations.

## Install

Apply the accompanying `gpt-doug-warfighter-core.patch` to the root of an existing `sonoxo/gpt-doug-llm` checkout, or unzip the source overlay there. Check conflicts before applying:

```sh
git apply --check /path/to/gpt-doug-warfighter-core.patch
git apply /path/to/gpt-doug-warfighter-core.patch
```

The overlay does not overwrite `ZYRA_MSS_V1`, existing PINEAL code, or `scripts/doug-max`. It deliberately leaves existing executable dispatch paths unchanged. For this prototype, run the new module directly:

```sh
python3 -m research_lab.warfighter.cli doctor
python3 -m unittest discover -s research_lab/warfighter/tests -p 'test_*.py' -v
python3 -m research_lab.warfighter.cli ontology --validate
```

## Synthetic exercise

From the repository root:

```sh
python3 -m research_lab.warfighter.cli simulate research_lab/warfighter/examples/synthetic_training_defense.json --input-root research_lab/warfighter/examples --workspace "$HOME/Downloads/memory/warfighter-research"
```

Copy `run_id` and `run_sha256` from the JSON output. The simulator records its run in a local SQLite quarantine. It never approves or publishes it.

### Verification

```sh
python3 -m research_lab.warfighter.cli verify 'wr:run:YOUR_RUN_ID' --workspace "$HOME/Downloads/memory/warfighter-research"
```

The verifier replays the currently installed mathematical model and compares input, output, implementation digest, model version, and exact envelope structure. Passing means a specified synthetic computation reproduces. It does **not** mean real-world readiness, statistical accuracy, scientific discovery, or operational authorization.

### Explicit local review and research publication

```sh
python3 -m research_lab.warfighter.cli review 'wr:run:YOUR_RUN_ID' --decision approve --reviewer 'local-operator-label' --rationale 'Verified synthetic exercise for research publication' --workspace "$HOME/Downloads/memory/warfighter-research"
```

The terminal will ask you to type the exact 64-character run SHA-256 digest. The review command requires an interactive TTY. `--reviewer` is a locally provided label; it does not authenticate an identity. **Approval authorizes research-only publication, nothing more.**

```sh
python3 -m research_lab.warfighter.cli publish 'wr:run:YOUR_RUN_ID' --workspace "$HOME/Downloads/memory/warfighter-research"
python3 -m research_lab.warfighter.cli findings --workspace "$HOME/Downloads/memory/warfighter-research"
```

A published research finding may be revoked explicitly:

```sh
python3 -m research_lab.warfighter.cli revoke 'wr:publication:YOUR_PUBLICATION_ID' --reason 'Superseded exercise' --workspace "$HOME/Downloads/memory/warfighter-research"
```

Revocation hides it from current research retrieval, retains the local audit trail, and marks any existing PINEAL projection STALE. Reconciliation is a separate human-commanded step, not background synchronization.

## PINEAL (optional)

On a system with the existing `integrations/gpt-doug-pineal` package installed/importable:

```sh
python3 -m research_lab.warfighter.cli pineal-project 'wr:publication:YOUR_PUBLICATION_ID' --pineal-db "$HOME/Downloads/memory/bio/pineal.sqlite3" --workspace "$HOME/Downloads/memory/warfighter-research"
```

PINEAL is **never touched during ordinary status, analysis, verification, query, or simulation**. Projection uses the dedicated `warfighter_research` namespace; the existing `warfighter-defense-si` metrics remain synthetic-only. The code never requests network access, secrets, or real defense-system telemetry.

## Exact research math

When installed alongside the original repository's math modules, `--engine bio-hilbert` and `--engine exact-linear` delegate to the already established exact-rational research modules. Use their **original JSON mathematical input formats**, saved inside your declared input root. These models are mathematical abstractions, not physical quantum hardware, field forecasts, or a complete validation of the Warfighter domain.

The historical Bio-Hilbert sample is `research_lab/examples/bio_hilbert_6_to_infinity.json`. The exact-linear sample is `research_lab/examples/multidimensional_nonnormal.json`.

## Local evidence and limitations

- Automated suite on a standalone local development workspace: see `WARFIGHTER_CORE_TEST_REPORT.md`. One full-repository math integration test is skipped when those original modules are absent locally.
- No independent reviewer/subagent was available in this environment. Do not interpret local self-review as a formal security assessment, ATO, or public operational deployment.
- Python 3.9+ targeted, Python 3.13 exercised in the isolated workspace.
- SQLite audit chaining is tamper-evident relative to a trusted external checksum; privileged rewrite of a local DB and its entire hash chain cannot be prevented by local software alone.
- Review identity labels are not externally authenticated. A production system would need identities/roles, external attestations, secured key storage, rollback protection and an independent security review.
- No browser or Blender 6D view is provided in this research core; those are separate planned components.
