# GPT-Orca NeuroCloud: simulated neuron chip and humanoid twin

An offline, synthetic neural-network graph with deterministic activations,
a humanoid joint-state digital twin, a SQLite provenance store and an optional
loopback-only HTTP status endpoint. This is a **software simulation**, not
a physical biochip, organoid, conscious system, or real robot controller.

This is designed to complement GPT-Doug's memory/ontology layer and the
GPT-Orca-LLM council in PR #417. The simulator does not yet run model
inference or share its database with the council. The next reviewed step is
a read-only adapter that converts synthetic observations to evidence packets.

## Run

```bash
python3 -m research_lab.orca_neurocloud --neurons 12 --cycles 3 --db /tmp/orca-neurocloud.sqlite3
python3 -m unittest tests.test_orca_neurocloud -v
python3 -m research_lab.orca_neurocloud --cycles 1 --serve
curl http://127.0.0.1:8765/health
```

Pure Python standard library. To package for authorized cloud hosting, use
a container or VM behind authenticated access and TLS. **Do not expose**
the default HTTP service publicly; it is intentionally bound to localhost,
and has no authentication. Device actuation and remote writes are absent.

Future work: consented sensor adapter, model-mediated observation analysis,
RBAC, telemetry, container CI and validation with the existing ontology.
