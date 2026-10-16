# BioChip memory

A file-backed SQLite memory store, not biological hardware. Public operations:
`remember`, `recall`, `forget`, `heartbeat`, `audit_trail`.

Actor/key limits: 256 UTF-8 bytes. Provenance: 4096 bytes. Serialized value:
1048576 bytes. Keys are preserved exactly. Confidence must be finite in [0,1];
TTL must be finite and strictly positive, or None. Booleans are not numbers.
Invalid inputs raise ValueError before a write. Actors are caller-supplied
identifiers, not authenticated identities. Use only in a trusted local process.

Run `python3 -m unittest discover -s biochip/tests -t . -v` from the checkout.

Ownership checks and writes serialize with BEGIN IMMEDIATE, including across
instances. Known denials commit only their audit event, then raise PermissionError;
unexpected failures roll back. Audit/commit failures are surfaced, never treated
as a successful write. An unavailable disk cannot guarantee a durable denial log.

## Storage and upgrades
New database and backup files use mode 0600. Existing insecure, symlink or
nonregular files are refused, not silently chmodded. Use a private directory;
`BioChip(':memory:')` is unsupported. Existing version-0 schemas are checked,
backed up to a unique `.legacy-v0-*.sqlite3` snapshot, then marked version 1.
Future/incompatible schemas and corrupt legacy rows stop adoption without
rewriting them. `chip.backup('new-path.sqlite3')` uses SQLite consistent backup
and refuses overwrite. Keep backups confidential and manage retention yourself.
A legacy NULL expiry cannot reveal whether an earlier caller supplied NaN.
Same-UID hostile processes and encrypted storage are outside this boundary.
