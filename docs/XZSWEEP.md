# XZSWEEP Maintainer Policy

XZSWEEP is the repository's routine stale-file maintenance pass.

## Freshness rule

A tracked path is due for review when more than **24 hours** have elapsed since the newest of:

1. the path's last content-changing Git commit, or
2. its last XZSWEEP review for the exact same SHA-256 content hash.

This separates **maintenance freshness** from meaningless Git churn. XZSWEEP does not rewrite healthy source files merely to manufacture a newer commit timestamp.

## What a sweep does

For every due tracked path, XZSWEEP:

- reads the file and calculates a SHA-256 content hash;
- determines the path's last Git touch using full repository history;
- classifies UTF-8 text vs. binary content;
- validates JSON, JSONL, and Python syntax using the Python standard library;
- applies a deterministic missing-EOF-newline repair only to known-safe text formats;
- records the review, repair actions, validation findings, and freshness metadata in `.xzsweep/freshness.json`.

Binary files are reviewed and hashed but are not mutated merely for freshness.

## Automation

`.github/workflows/xzsweep.yml` runs the maintainer:

- after pushes to `main` (excluding the generated freshness ledger),
- once per day on schedule, and
- on manual workflow dispatch.

The workflow checks out full Git history, runs the 24-hour apply pass, rejects whitespace errors with `git diff --check`, and commits only when the sweep creates a meaningful maintenance delta or refreshes the audit ledger.

Generated XZSWEEP commits use `[skip ci]` and the workflow ignores ledger-only pushes to prevent self-trigger loops.

## Local use

```bash
python scripts/xzsweep.py --hours 24 --apply --report .xzsweep/freshness.json
```

A read-only review can omit `--apply`.

## Audit contract

`.xzsweep/freshness.json` is the machine-readable source of truth for the latest sweep. Each file record includes its current hash, Git touch time, XZSWEEP review time, whether it was due, actions applied, and validation findings.
