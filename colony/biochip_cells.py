"""Bounded digital-cell colony simulation; not a biological cell model.

The model is an abstract, deterministic state machine. It performs no wet-lab
work, medical inference, physical-device control, or external network actions.
"""
from dataclasses import dataclass, asdict
import argparse
import json
import sqlite3
import uuid

MAX_CELLS = 50_000
MAX_SEED_COUNT = 10_000
MAX_STEPS = 10_000


def clamp(value):
    return max(0.0, min(1.0, round(float(value), 4)))


@dataclass
class Cell:
    id: str
    generation: int = 0
    age: int = 0
    membrane: float = 1.0
    energy: float = 0.7
    signaling: float = 0.0
    stress: float = 0.0
    state: str = "active"


class CellColony:
    def __init__(self, path, max_cells=MAX_CELLS):
        if not isinstance(max_cells, int) or isinstance(max_cells, bool):
            raise ValueError("max_cells must be an integer")
        if not 1 <= max_cells <= MAX_CELLS:
            raise ValueError(f"max_cells must be between 1 and {MAX_CELLS}")
        self.max_cells = max_cells
        self.db = sqlite3.connect(path, timeout=10)
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.execute("PRAGMA busy_timeout = 10000")
        self.db.execute("""CREATE TABLE IF NOT EXISTS digital_cells (
            id TEXT PRIMARY KEY, generation INTEGER NOT NULL, age INTEGER NOT NULL,
            membrane REAL NOT NULL, energy REAL NOT NULL, signaling REAL NOT NULL,
            stress REAL NOT NULL, state TEXT NOT NULL
        )""")
        self.db.commit()

    def _store(self, cell):
        self.db.execute("""INSERT INTO digital_cells
          (id,generation,age,membrane,energy,signaling,stress,state)
          VALUES (:id,:generation,:age,:membrane,:energy,:signaling,:stress,:state)""",
          asdict(cell))

    def cells(self):
        rows = self.db.execute(
            "SELECT id,generation,age,membrane,energy,signaling,stress,state "
            "FROM digital_cells ORDER BY id"
        )
        return [Cell(*row) for row in rows]

    def _population(self):
        return self.db.execute("SELECT COUNT(*) FROM digital_cells").fetchone()[0]

    def seed(self, count):
        if not isinstance(count, int) or isinstance(count, bool):
            raise ValueError("Seed count must be an integer")
        if count < 0 or count > MAX_SEED_COUNT:
            raise ValueError(f"Seed count must be 0..{MAX_SEED_COUNT}")
        with self.db:
            current = self._population()
            if current > self.max_cells:
                raise RuntimeError("Existing population exceeds configured colony limit")
            if current + count > self.max_cells:
                raise ValueError(
                    f"Seeding would exceed colony limit ({self.max_cells})"
                )
            for _ in range(count):
                self._store(Cell(uuid.uuid4().hex))
        return self.summary()

    def tick(self, nutrition=0.5, stimulus=0.0):
        if not 0 <= nutrition <= 1 or not 0 <= stimulus <= 1:
            raise ValueError("Nutrition and stimulus must be between 0 and 1")

        new_cells = []
        with self.db:
            population = self._population()
            if population > self.max_cells:
                raise RuntimeError("Existing population exceeds configured colony limit")
            remaining_capacity = self.max_cells - population

            for cell in self.cells():
                if cell.state != "active":
                    continue
                cell.age += 1
                cell.signaling = clamp(0.6 * cell.signaling + 0.4 * stimulus)
                cell.energy = clamp(
                    cell.energy + 0.2 * nutrition - 0.09 - 0.03 * cell.signaling
                )
                cell.stress = clamp(
                    cell.stress + 0.12 * (1 - nutrition)
                    + 0.05 * cell.signaling - 0.08 * nutrition
                )
                cell.membrane = clamp(
                    cell.membrane - 0.04 * cell.stress + 0.03 * nutrition
                )

                if (cell.energy < 0.12 or cell.membrane < 0.25
                        or cell.stress > 0.9):
                    cell.state = "inactive"
                elif (remaining_capacity > len(new_cells)
                      and cell.energy > 0.85 and cell.stress < 0.25
                      and cell.age >= 3):
                    cell.energy = clamp(cell.energy * 0.6)
                    cell.age = 0
                    new_cells.append(Cell(
                        uuid.uuid4().hex,
                        generation=cell.generation + 1,
                        energy=cell.energy,
                    ))
                self._store(cell)

            for offspring in new_cells:
                self._store(offspring)

        return self.summary()

    def summary(self):
        total, active, inactive, generations, mean_energy = self.db.execute(
            """SELECT COUNT(*),
                      COALESCE(SUM(CASE WHEN state='active' THEN 1 ELSE 0 END), 0),
                      COALESCE(SUM(CASE WHEN state!='active' THEN 1 ELSE 0 END), 0),
                      COALESCE(MAX(generation), 0),
                      COALESCE(AVG(CASE WHEN state='active' THEN energy END), 0)
               FROM digital_cells"""
        ).fetchone()
        return {
            "model": "gpt-biochip-digital-cells",
            "type": "abstract_simulation",
            "total": total,
            "active": active,
            "inactive": inactive,
            "generations": generations,
            "mean_energy": round(mean_energy, 4),
            "max_population": self.max_cells,
            "population_limit_reached": total >= self.max_cells,
            "physical_cells_created": 0,
        }

    def close(self):
        self.db.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="colony.sqlite3")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    seed = sub.add_parser("seed")
    seed.add_argument("--count", type=int, default=10)
    tick = sub.add_parser("tick")
    tick.add_argument("--steps", type=int, default=1)
    tick.add_argument("--nutrition", type=float, default=0.5)
    tick.add_argument("--stimulus", type=float, default=0.0)
    args = parser.parse_args()

    colony = CellColony(args.db)
    try:
        if args.command == "seed":
            output = colony.seed(args.count)
        elif args.command == "tick":
            if not 0 <= args.steps <= MAX_STEPS:
                raise ValueError(f"steps must be 0..{MAX_STEPS}")
            output = colony.summary()
            for _ in range(args.steps):
                output = colony.tick(args.nutrition, args.stimulus)
        else:
            output = colony.summary()
        print(json.dumps(output, indent=2))
    finally:
        colony.close()


if __name__ == "__main__":
    main()
