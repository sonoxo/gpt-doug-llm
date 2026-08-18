# The Resilience Matrix

A terminal-based defensive risk-simulation RPG for governance, cybersecurity resilience, quantum readiness, safety, and compliance decisions.

The simulation is intentionally abstract and non-operational. It does **not** include exploit code, real-system targeting, weapons design, hazardous procedures, safeguard evasion, or instructions for attacking systems.

## Run

From the repository root:

```bash
python -m resilience_matrix
```

Run a deterministic one-decision sample:

```bash
python -m resilience_matrix --seed 17 --demo
```

If installed from the project package, the `resilience-matrix` console entry point is also available.

## Gameplay

You lead the fictional Meridian Civic Cooperative through eight turns. Each turn presents an abstract event such as supplier failure, cryptographic obsolescence, an audit finding, communications outage, insider-policy violation, integrity anomaly, governance ambiguity, or a recovery-assurance gap.

Decisions update qualitative, ordinal tracks for:

- readiness
- budget capacity
- stakeholder trust
- compliance posture
- evidence quality
- risk likelihood, impact, and confidence
- control effectiveness and maturity

Risk ratings deliberately avoid numeric probability or loss estimates. Every displayed likelihood, impact, confidence, and overall priority band includes a plain-language explanation.

## Commands

- `map` — render an ASCII dependency graph
- `inspect <id>` — inspect any ontology entity
- `risks [risk-id]` — show risk ratings and explanations
- `controls [control-id]` — show control state and evidence links
- `stakeholders [id]` — show authority and responsibilities
- `evidence [evidence-id]` — show provenance and confidence
- `decide <number|choice-id>` — apply a defensive choice
- `save <path>` — save simulation state as JSON
- `load <path>` — restore simulation state
- `help` — show command help
- `quit` — exit

## Editable ontology and scenarios

The model is data-driven:

- `resilience_matrix/data/ontology.json`
- `resilience_matrix/data/scenarios.json`

The ontology contains assets, threats, dependencies, controls, stakeholders, risks, evidence, and explicit relationships. References are validated at startup. Scenario choices may change qualitative tracks, a referenced risk, and a referenced control.

### Allowed risk ordinals

- likelihood: `Rare`, `Unlikely`, `Possible`, `Likely`, `Almost Certain`
- impact: `Minor`, `Moderate`, `Major`, `Severe`, `Critical`
- confidence: `Low`, `Medium`, `High`
- control effectiveness: `Ineffective`, `Limited`, `Moderate`, `Strong`

The engine also uses qualitative control maturity and overall-priority bands. These are ordinal labels only; they are not presented as quantitative measurements.

## Tests

The tests use only Python's standard library:

```bash
python -m unittest tests.test_resilience_matrix -v
```

Coverage includes ontology reference validation, risk updates, save/load behavior, and deterministic seeded scenario ordering.

## Extending safely

Keep scenario content defensive and abstract. Good additions describe governance choices, monitoring, redundancy, access policy, cryptographic migration, training, supplier review, assurance testing, escalation, audit, and evidence management. Avoid procedural attack steps, exploit details, targeting instructions, safeguard bypasses, or hazardous operational guidance.
