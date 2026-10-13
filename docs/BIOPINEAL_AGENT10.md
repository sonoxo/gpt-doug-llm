# GPT-Doug BioPINEAL: local Agent10 alias, heartbeat and quantum-inspired mathematics

**Status:** Local, opt-in research prototype. All outputs are `RESEARCH_ONLY`.

The project has **no evidence of a physical biochip, biological mitochondria connected to a computer, measured ATP consumption, quantum processing hardware, access to extra physical dimensions, or military credential verification**. These terms refer to software analogies and bounded classical numerical models.

## Local Agent10 operator label

The operator-profile command records only a locally supplied callsign as a private file in an explicitly chosen workspace, with `SELF_DECLARED` provenance, no granted privileges, and unverified identity/military affiliation. It **does not** register a government credential, confer permissions or make a claim in the canonical ZYRA ontology. It does not change the independent human review requirement for research publication. No profile is uploaded to GitHub or automatically synchronized to PINEAL.

```bash
# From an existing checkout of the feature branch; run on your own machine
bash scripts/doug-max warfighter operator register --callsign Agent10 --workspace "$HOME/Downloads/memory/warfighter-research"
bash scripts/doug-max warfighter operator show --workspace "$HOME/Downloads/memory/warfighter-research"
```

Profile storage: `~/Downloads/memory/warfighter-research/operator-profile.json` (private directory and file permissions on POSIX). Registering the same label twice is idempotent. Changing the label requires a separately reviewed process to preserve attribution; this version rejects silent replacement. A callsign is not a validated person, certificate, role or authorization.

## Read-only BioPINEAL heartbeat

The status command reads, but does not modify, the user's existing `~/Downloads/memory/working/heartbeat.json`. It displays `LIVE` only for a very recent explicitly beating heartbeat; otherwise it says `STALE`, `MISSING`, `INVALID`, `FUTURE_TIMESTAMP`, or `UNCONFIRMED`. For example, a 250-second-old heartbeat is correctly `STALE` even when an earlier dashboard displayed `ONLINE`.

```bash
bash scripts/doug-max warfighter biopineal status --memory-root "$HOME/Downloads/memory" --workspace "$HOME/Downloads/memory/warfighter-research"
```

`ram_gb` and `cpu_load_1m` are displayed only if the heartbeat file reports them. A CPU load average is **not** CPU utilization. GPU activity remains `UNMEASURED` without a suitable telemetry source.

## Mitochondrial metaphor + classical quantum-state demonstrator

This module spends **abstract computation units** on a small, local, classical statevector simulation. The units count toy amplitude-operations and optional sample iterations. They are **not** joules, electrical power, tokens, or measured biological ATP. The initial model has at most six simulated qubits, 128 allowed gates and 1024 pseudorandom measurement samples, with a strict operator-specified budget. Gate set: H, X, Z, CNOT. There is no quantum processor or model inference.

```bash
bash scripts/doug-max warfighter biopineal simulate \
  research_lab/warfighter/examples/biopineal_bell.json \
  --input-root research_lab/warfighter/examples \
  --budget-units 200
```

The Bell-state example starts at `|00>`, applies Hadamard on qubit 0 and a controlled NOT (0→1), then returns `P(00)=0.5`, `P(11)=0.5` and zero for the other basis states, plus simulated cost. This is **classical calculation of a toy quantum state**, not evidence of real-world entanglement or extra dimensions. It performs no networking, no PINEAL writes, no ZYRA authorization changes, no review or publication.

## Verify locally

```bash
python3 -m unittest research_lab.warfighter.tests.test_agent10_biopineal -v
python3 -m unittest discover -s research_lab/warfighter/tests -p 'test_*.py' -v
```

For full-repository integration, consult the Warfighter CI workflow. All sensitive defense datasets remain excluded from these examples; use only authorized synthetic data.
