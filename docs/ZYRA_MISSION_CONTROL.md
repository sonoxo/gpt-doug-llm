# ZYRA Mission Control 1.0

ZYRA Mission Control is the observability, scheduling, sandboxing, verification,
and proof layer for GPT-Doug.

## What ships

- tamper-evident, HMAC-signed JSONL mission journal
- step timing, model-call and token telemetry fields
- planning/tool/validation/review/runtime failure taxonomy
- dependency-aware mission DAGs with parallel independent levels
- explicit acceptance criteria locked before execution
- explicit resume checkpoints
- machine-readable capability manifests
- per-mission read-only, write-local, and network-approved grants
- explicit write/network boundaries
- signed policy snapshots
- disposable build sandboxes
- dependency-lock hash verification
- automatic localhost preview detection and preview process lifecycle
- golden-path smoke checks
- multi-file unified diff previews
- artifact/provenance SHA-256 manifests
- signed autonomous-change attestations
- local Mission Control web console
- live journal, mission history, telemetry, DAG plan, diff, capability,
  LASER/provider/self-heal status, and benchmark views
- operator checkpoint/rollback request controls
- reliability benchmark scorecards, cross-model repeatability, and regression thresholds

## Launch

```bash
python3 zyra_control.py status
python3 zyra_control.py capabilities
python3 zyra_control.py verify-journal
python3 zyra_control.py plan "build a verified application"
python3 zyra_control.py benchmark-self --output ~/.gpt-doug/mission-control/benchmark-scorecard.json
python3 zyra_control.py console
```

The console binds to `127.0.0.1:8790` by default. Remote binding fails closed
unless `ZYRA_ALLOW_REMOTE_CONSOLE=1` is explicitly set.

## Mission lifecycle

```text
MISSION_CREATED
  -> POLICY_SNAPSHOT
  -> ACCEPTANCE_LOCKED
  -> PLAN_CREATED
  -> STEP_STARTED / STEP_VERIFIED / STEP_FAILED
  -> PATCH_PREVIEW
  -> CHECKPOINT_SAVED
  -> MISSION_VERIFIED / MISSION_FAILED
  -> ATTESTATION_CREATED
```

Every journal record includes the previous record digest and a local HMAC
signature. Editing or reordering records makes journal verification fail.

## DAG execution

A mission is a set of steps with explicit dependencies. Independent steps at
the same dependency level may execute in parallel. A failed dependency blocks
downstream steps rather than allowing false progress.

## Capabilities

Agents and tools advertise machine-readable manifests. A mission grant is
evaluated against both the requested capability and the manifest's write or
network boundary. Network-capable providers therefore cannot silently gain
network authority under a local-only mission profile.

## Sandboxing

`SandboxRunner` copies a workspace to an ephemeral temporary directory,
excluding `.git`, virtual environments, caches, and dependency directories.
Commands use `subprocess` with `shell=False`, bounded timeouts, and an executable
allowlist. Lockfile hashes are checked before and after each command.

`PreviewProcessManager` serves generated static apps on localhost and provides
an explicit start/stop lifecycle. `start_static_preview()` detects common web
entrypoints and starts the preview automatically when requested.

## Proof

`AttestationSigner` creates a signed change record containing:

- mission ID
- prompt hash
- model route
- commit SHA when available
- changed files
- verification checks
- journal head
- artifact digest
- SBOM digest when available

This allows `VERIFIED` to be tied to evidence rather than a model claim.

## Benchmarking

The benchmark interface tracks verified completion, false-success rate,
rollback correctness, human-correction rate, model calls, and median runtime.
`run_matrix()` repeats the same benchmark across named providers/models and
reports score variance. `compare_scorecards()` blocks release regressions beyond
configured reliability and performance thresholds.

Real agent/model benchmark runners plug into the same `BenchmarkSuite` API;
the built-in `benchmark-self` command verifies the deterministic control-plane
contract without requiring a model or network connection.
