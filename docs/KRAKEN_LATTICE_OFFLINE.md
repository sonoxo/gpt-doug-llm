# Kraken + Lattice: Offline Synthetic Preview

This module adds a **local JSON preview**, not a live Anduril Lattice integration. It inherits the bounded Kraken simulation for search-and-rescue, inspections, medical supplies, and warehouse tasks.

## Run

```sh
python3 -m research_lab.kraken_lattice_preview --agents 16 --ticks 20
python3 -m unittest discover -s tests -p 'test_kraken_lattice_preview.py' -v
```

There is **no networking, SDK authentication, live entity publishing, robotics task execution, weapons, targeting, or external track ingestion**. Coordinates are a made-up 64×64 grid; they are not latitude/longitude. The emitted JSON is illustrative, not a valid Lattice Entity payload.

## Path to authorized integration

1. Request developer program or Lattice Sandbox access through https://developer.anduril.com/ .
2. Read https://developer.anduril.com/guides/concepts/overview and https://developer.anduril.com/guides/getting-started/set-up .
3. Use an approved sandbox, synthetic data only, and a separate opt-in exporter validated against the current official Entity schema before enabling any API traffic.
4. Keep actual robotics and tasking out of scope pending separate authorization and safety review.

Public SDK: https://github.com/anduril/lattice-sdk-python . Production system access may not be free or open and should not be assumed. Do not embed tokens in git history.
