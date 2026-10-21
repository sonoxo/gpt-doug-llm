# GPT-Doug BioChip (software memory core)

A zero-dependency Python/SQLite implementation of durable memory with provenance, confidence, owner isolation, optional shared visibility, SHA-256 corruption checks, TTL expiration, heartbeat health status, and per-actor audit trails.

This is **not a physical biochip, an organoid, a biological system, a consciousness model, or a live hardware interface**. It makes no claims of continuous activity when the process is stopped.

## Quick start

From repository root:

```bash
python3 -m unittest discover -s biochip/tests -v
python3 - <<'PY'
from biochip.core import BioChip
chip = BioChip("biochip.sqlite3")
chip.remember("ontology:project", {"name": "GPT-Doug-LLM"}, actor="doug", provenance="local operator", confidence=1.0)
print(chip.recall("ontology:project", actor="doug"))
print(chip.heartbeat())
PY
```

## Security boundary

`actor` is a caller-supplied identifier, **not authentication**. Only deploy behind a trusted service that authenticates the principal and passes the verified identity. SQLite data is not encrypted; protect the database at rest and restrict filesystem access. SHA-256 detects accidental modification but is **not** tamper-proof against a malicious database writer. Audit is local and not immutable. Shared records are readable to any authenticated caller using this instance. Avoid secrets in values until external encryption and key management are integrated.

## Next integration

Add a service adapter to the existing governed agent/ontology interface with authenticated identities, authorization decisions, namespace support, resource quotas, atomic backups, and scheduled heartbeat execution. Do not bind this component to external tools or execution privileges without approval gates.
