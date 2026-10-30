# REA Recursive Healing & Recovery — CL1

REA means **Recursive Evaluation and Assurance** in this implementation. The
engine provides a closed-loop reliability pattern:

1. Observe a component health signal.
2. Classify it as healthy, degraded, failed, or unknown.
3. Require evidence and a verified checkpoint before retry recommendations.
4. Apply bounded exponential backoff and a finite retry budget.
5. Open a circuit breaker after repeated failures.
6. Record an audit event and require human diagnosis when the system cannot
   safely recover.

## Safety boundary

The engine emits recovery recommendations only. It does not run shell commands,
mutate files, restart services, restore snapshots, access credentials, or deploy.
A future adapter must be explicitly configured, least-privileged, tested in
THEGREENHOUSE, and gated by approval. A checkpoint must be independently
verified by its registering caller; the engine does not claim to verify storage
integrity itself.

## Run tests

```bash
python3 -m unittest discover -s tests -p 'test_rea_recovery.py'
```

## Status

Reference implementation and unit tests are staged. Live telemetry, probes,
checkpoint storage, recovery executors, and post-recovery service verification
are not connected.
