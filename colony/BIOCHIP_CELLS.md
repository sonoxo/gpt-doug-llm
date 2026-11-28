# GPT-BioChip Digital Cells

A deterministic, abstract cell-state simulation integrated into the Biochip/MLM Colony branch. It is a software model, not a validated biological mechanism and not a predictor of real cell behavior.

## Run

```sh
python3 -m colony.biochip_cells --db colony.sqlite3 seed --count 10
python3 -m colony.biochip_cells --db colony.sqlite3 tick --steps 20 --nutrition 0.7 --stimulus 0.2
python3 -m colony.biochip_cells --db colony.sqlite3 status
python3 -m unittest discover -s colony -p 'test_*.py' -v
```

## State model

Each digital cell stores membrane integrity, energy, stress, signaling, age, generation, and active/inactive lifecycle state. SQLite persists state across CLI invocations. State variables are clamped to [0, 1].

## Resource and safety bounds

- Hard population ceiling: 50,000 digital cells per database.
- Seed operation: at most 10,000 cells per invocation and never beyond the configured population ceiling.
- Tick operation: at most 10,000 steps per CLI invocation.
- Reproduction is capacity-aware: offspring are not materialized or inserted after the population ceiling is reached.
- Seed/tick writes are transactional; a failed transaction is rolled back.
- Summary queries use SQL aggregates rather than loading the entire population.

The Python API accepts a lower max_cells value for tests and constrained deployments; it cannot raise the hard ceiling above 50,000.

This model creates zero physical cells. No biological tissue, laboratory equipment, medical workflow, robotics, or external hardware is connected. The simulation is not evidence of biological efficacy.
