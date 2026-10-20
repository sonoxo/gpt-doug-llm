# GPT-Doug Kraken local planning fleet

This is executable Python software: a foreground planner and optional reviewer,
with private mission metadata, one active subprocess, 32 waiting slots, at most
8 model-call attempts per mission, at most 1024 requested output tokens per call,
a 600-second execution deadline, and 1 MiB message limits. These are ceilings;
configuration may lower them. Queued waiting time is not execution time.

No external tools, HeyPCB calls, purchases, model downloads, self-replication,
physical devices or trained GPT-Doug weights are implemented. Node is not needed.
The reviewer does not approve tool actions. `approved` and `external_tools_enabled`
are always false. `completed` means that proposal computation finished, not that
its claims are correct. Both roles can use the same model; this is disclosed.
Different model IDs are not asserted to be statistically independent.

## Verify this checkout

From the checkout root, with Python 3.10+ on macOS or Linux:

```sh
python3 -m unittest discover -s biochip/tests -t . -v
python3 -m biochip.fleet --help
```

The automated suite uses disposable databases, real child Python processes and
local HTTP test fixtures. A fixture returning a string is not a live LLM test.
Real model/server and Mac acceptance must be recorded separately before release.
Python 3.10 syntax compatibility is checked; use a supported Python release.

## Select a local model

Start your separately installed local server and review its actual configuration
and model license. A localhost API can proxy a paid/cloud service: neither
model names nor discovery prove locality, cost, quality or license compliance.
Do not approve a remote backend merely because it listens on loopback.

An explicit inventory may be obtained without inference:

```sh
python3 -c 'from biochip.models import ModelRouter; print(ModelRouter().discover())'
```

Write a regular operator-owned configuration JSON file, not writable by other
users. Replace all example values with actual reviewed values. The deliberately
false confirmation below prevents accidental use without that review.

```json
{
  "operator": "local-operator",
  "project": "gpt-doug",
  "state_directory": "/Users/YOUR_USERNAME/.gpt-doug/kraken-state",
  "planner": {
    "provider": "ollama",
    "name": "REPLACE_WITH_INSTALLED_MODEL_ID",
    "endpoint": "http://127.0.0.1:11434",
    "approved_by": "local-operator",
    "approved_at": "2026-10-16T00:00:00+00:00",
    "locality_evidence": "REPLACE_WITH_YOUR_LOCAL_BACKEND_REVIEW_REFERENCE",
    "license_evidence": "REPLACE_WITH_REVIEWED_MODEL_CARD_REFERENCE",
    "operator_confirmed_local": false
  },
  "reviewer": null
}
```

Set `operator_confirmed_local` to true only after reviewing the selected backend.
Use the real approval time. The operator identity must match `approved_by`.
To enable a reviewer, replace null with another fully reviewed ModelApproval
object. Other compatible providers use `/v1/models` and `/v1/chat/completions`.
The state directory must be an explicit absolute path, owned by your user with
mode 0700 (created privately when absent). Database and lock files use 0600.
Existing insecure files/directories are refused, not silently changed.

## Foreground commands

```sh
python3 -m biochip.fleet doctor --config ./kraken.json
python3 -m biochip.fleet inventory --config ./kraken.json
python3 -m biochip.fleet plan --config ./kraken.json
printf '%s\n' 'Review this nonsensitive software design.' | python3 -m biochip.fleet run --config ./kraken.json
python3 -m biochip.fleet status --config ./kraken.json --mission ACTUAL_MISSION_ID
python3 -m biochip.fleet stop
```

Doctor/inventory/plan perform discovery only and do not create a mission ledger.
Status opens an existing ledger read-only. Run reads a bounded prompt from stdin
and executes one mission. The library also supports a context-managed
`FleetSupervisor(config, ledger)` with `submit` and `run_pending` for a bounded
queue. Close an idle supervisor after use; no startup service is installed.

Exit codes: 0 requested operation completed; 2 configuration/policy validation
failed; 3 cooperative stop; 4 unavailable, provider failure or uncertain outcome.
The stop command returns 0 when it successfully latches STOP. No automatic resume
exists. The repository's existing operator-controlled stop gate remains authority.
Preserve GPT_DOUG_AI_STOP_DIR, GPT_DOUG_AI_BLOCK_ALL and
GPT_DOUG_AI_REQUIRE_STOP_DIRECTORY. The fleet will never clear them automatically.

## Evidence and boundaries

A committed dispatch intent precedes each worker start. Failed attempts consume
budget. The deadline covers discovery and inference in the owned child. STDIN,
STDOUT and STDERR are bounded and supervised; stderr is discarded, not copied to
logs. Cancellation terminates only that child, not an unrelated model server.
This is not an OS sandbox; trusted source files run with your user's permissions.
Backend generation already accepted by a separate server may continue after the
client is stopped. Timed-out outcomes are uncertain, never silently replayed.

A single POSIX file lock owns the state directory. Interrupted queued/running
records become uncertain after acquiring that lock on restart. Prompts exist
only in memory and are not recovered or automatically rerun. Keep the lock inode;
do not delete it to bypass an active supervisor.

The ledger stores operator/project/model IDs, source-content SHA-256, policy
revision, prompt/proposal hashes, events and actual counters. Raw prompts,
model replies and credentials are not stored by default. JSON replies are printed
to stdout, so redirecting stdout is an explicit decision to save them. These hashes
and local operator identifiers are not signatures or multi-user authentication.
Unknown token usage remains null; requested token caps are not proof that a
separately configured backend complied. Future safe tools and HeyPCB require
separate reviewed adapters and enforceable no-charge contracts.
