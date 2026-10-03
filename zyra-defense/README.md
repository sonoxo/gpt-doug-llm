# ZYRA Defense Digital-Twin Ontology

Simulation-only reference implementation for a Palantir-style defense ontology.

## Included

- Platforms, subsystems, sensors, observations, tracks, missions and units
- Simulation-only target and abstract effect-system models
- Advisory recommendations
- Human authorization requests and approvals
- Safety governor that blocks real-world actuation semantics and interfaces
- Immutable-style audit events
- Palantir Ontology write-payload adapter
- JSON export

## Hard boundary

This project does **not** implement real-world targeting, weapon release, fire-control,
autonomous lethal engagement, coordinates for engagement, or actuation interfaces.

## Run

```bash
python demo.py
python -m unittest discover -s tests -v
```

## Palantir integration

`PalantirOntologyAdapter` converts domain objects to normalized write payloads. Connect
that adapter to your authorized Foundry/OSDK integration separately and map the
`objectType` values to your tenant's Ontology object API names.
