# AEGIS War Room Decision Support

AEGIS War Room is a bounded decision-support layer for defensive mission assurance. It is intended to help operators compare non-lethal options using explicit evidence, uncertainty, human approval, and auditable rationale.

## Supported decision domains

- Mission continuity
- Logistics
- Maintenance
- Evacuation
- Humanitarian support
- Communications resilience
- Cyber defense
- Infrastructure recovery
- Personnel safety
- Resource allocation

## Deliberately unsupported

AEGIS War Room does **not** provide:

- Target selection
- Weapon release decisions
- Fire control
- Strike planning
- Lethal engagement recommendations
- Offensive cyber operations

Those categories are represented in the type system only so the decision engine can fail closed and reject them.

## Decision contract

A request supplies an objective, operator-provided options, evidence, constraints, and mission/principal identifiers. The engine ranks the options using safety, continuity, resilience, reversibility, policy fit, logistics feasibility, cost efficiency, and recovery speed.

Evidence quality affects confidence rather than silently increasing the substantive option score. Missing linked evidence forces confidence to zero for that option.

Every result is marked `DECISION_SUPPORT_ONLY` and requires human approval. The engine does not execute commands or grant authority.

## Visualization

`build_dashboard_payload()` provides a UI-ready payload containing ranked options, confidence, risk, evidence references, rationale, limitations, provenance, and an explicit safety boundary. Unknown data must remain unknown rather than being displayed as healthy/green.

## Tests

Run with the Python standard library:

```bash
python -m unittest tests.test_aegis_war_room -v
```

The test suite checks:

- Non-lethal option ranking
- Mandatory human approval
- Rejection of target selection
- Rejection of weapon release
- Rejection of offensive cyber requests
- Unknown confidence when evidence is absent
- Visualization safety-boundary preservation

## Next integration phase

Wire this decision layer into Golden Shield / Mission DNA / MITO so that any future defensive action is separately authorized and proven. The decision engine itself must remain a planner, not an executor.
