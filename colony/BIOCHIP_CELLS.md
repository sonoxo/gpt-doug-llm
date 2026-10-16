# GPT-BioChip Digital Cells

This is a discrete abstract cell-state simulation integrated into the Biochip/MLM Colony branch. It does **not** predict actual cell biology.

```sh
python3 -m colony.biochip_cells --db colony.sqlite3 seed --count 10
python3 -m colony.biochip_cells --db colony.sqlite3 tick --steps 20 --nutrition 0.7 --stimulus 0.2
python3 -m colony.biochip_cells --db colony.sqlite3 status
python3 -m unittest discover -s colony -p 'test_*.py' -v
```

Each digital cell has membrane integrity, energy, stress, signaling, age, generation and active/inactive lifecycle status. SQLite persists states across CLI invocations. Updates are bounded, deterministic except for UUIDs and intentionally simplified; no real-cell predictions should be drawn. No live biological tissue or robotics are connected.
