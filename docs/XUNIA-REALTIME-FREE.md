# XUNIA Realtime Free Runtime

XUNIA can run its core security automation locally without a paid API, paid model, or hosted control plane.

## What runs locally

- governed ASSESS / PENTEST / SIMULATE engagement manifests
- SQLite-backed persistent job queue
- concurrent security workers
- registered OSS tool execution through the bounded XUNIA executor
- SSE event stream
- interval schedules
- Git/filesystem change triggers
- evidence hashing
- normalized findings
- deterministic remediation queue
- high/critical local alerts
- retest and VERIFIED workflow

The runtime binds to `127.0.0.1:8765` by default. Destructive actions remain disabled.

## Start everything

```bash
python xunia_realtime_all.py --watch-config examples/xunia-watch.json
```

Without a watcher:

```bash
python xunia_realtime_runtime.py
```

Check which optional security engines are installed:

```bash
python xunia_tool_doctor.py
```

## Local API

- `GET /health`
- `GET /v1/jobs`
- `POST /v1/jobs`
- `GET /v1/jobs/{id}`
- `POST /v1/jobs/{id}/cancel`
- `POST /v1/jobs/{id}/retest`
- `GET /v1/findings`
- `POST /v1/findings/{id}/resolve`
- `POST /v1/findings/{id}/retest`
- `GET /v1/remediations`
- `GET /v1/notifications`
- `POST /v1/schedules`
- `GET /v1/events` (Server-Sent Events)

## Persistence

Default database:

```text
.xunia/realtime.db
```

SQLite WAL mode is used so the dashboard can read while worker threads write.

## Concurrency

The runtime defaults to eight global worker slots. Each engagement also carries its own `maxConcurrency` value, and the effective worker count is the smaller of the two.

This means source-code checks such as Trivy, Syft, Grype, Gitleaks, Semgrep, OSV-Scanner and Checkov can run concurrently when authorized and installed, while web/network jobs remain bounded by engagement policy.

## Local security boundary

By default the service only accepts loopback connections. To bind remotely, both of these must be intentionally configured:

```bash
export XUNIA_RUNTIME_ALLOW_REMOTE=1
export XUNIA_LOCAL_TOKEN='use-a-long-random-token'
```

Zyra also refuses to proxy to a non-loopback runtime unless `XUNIA_RUNTIME_ALLOW_REMOTE_PROXY=1` is explicitly set.

## Git/file automation

`xunia_realtime_watch.py` uses Python's standard library to monitor local Git state or a filesystem path. When it detects a change it refreshes the engagement window and queues a new authorized job.

Example:

```bash
python xunia_realtime_watch.py examples/xunia-watch.json
```

The watcher ignores common generated directories such as `.git`, `node_modules`, virtual environments, `dist`, and `build` when hashing a directory tree.

## Findings and remediation

Supported JSON/JSONL normalization currently covers:

- Nuclei
- Trivy
- Grype
- Gitleaks
- Semgrep
- Checkov
- Prowler

The remediation queue intentionally provides defensive fix guidance rather than exploit instructions. Gitleaks normalization does not copy the detected secret value into the finding record.

A normal lifecycle is:

```text
QUEUED -> RUNNING -> COMPLETED
                     |
                     v
                  FINDING
                     |
                     v
              REMEDIATION QUEUED
                     |
                     v
          RESOLVED_PENDING_RETEST
                     |
                     v
                  RETESTING
                 /        \
              OPEN      VERIFIED
```

## Cost model

The runtime itself has no required paid service dependency. Costs only appear if the operator chooses paid infrastructure or paid third-party services later. Running on hardware you already own keeps the core orchestration, database, dashboard connection, schedules and event stream local.
