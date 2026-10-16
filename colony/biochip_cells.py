"""Deterministic digital cell colony simulation (not a living cell model).

Discrete abstract values represent membrane integrity, energy, signaling and
stress. No wet-lab experiments, medical inference or physical device control.
"""
from dataclasses import dataclass, asdict
import argparse
import json
import sqlite3
import uuid

def clamp(x):
    return max(0.0, min(1.0, round(float(x), 4)))

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
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS digital_cells (
            id TEXT PRIMARY KEY, generation INTEGER, age INTEGER,
            membrane REAL, energy REAL, signaling REAL, stress REAL, state TEXT
        )""")
        self.db.commit()

    def _store(self, cell):
        self.db.execute("""INSERT OR REPLACE INTO digital_cells
          (id,generation,age,membrane,energy,signaling,stress,state)
          VALUES (:id,:generation,:age,:membrane,:energy,:signaling,:stress,:state)""",
          asdict(cell))

    def cells(self):
        return [Cell(*row) for row in self.db.execute(
            "SELECT id,generation,age,membrane,energy,signaling,stress,state FROM digital_cells ORDER BY id"
        )]

    def seed(self, count):
        if count < 0 or count > 10000:
            raise ValueError("Seed count must be 0..10000")
        with self.db:
            for _ in range(count):
                self._store(Cell(uuid.uuid4().hex[:16]))
        return self.summary()

    def tick(self, nutrition=0.5, stimulus=0.0):
        if not 0 <= nutrition <= 1 or not 0 <= stimulus <= 1:
            raise ValueError("Nutrition and stimulus must be between 0 and 1")
        new_cells = []
        with self.db:
            for c in self.cells():
                if c.state != "active":
                    continue
                c.age += 1
                c.signaling = clamp(0.6*c.signaling + 0.4*stimulus)
                c.energy = clamp(c.energy + .2*nutrition - .09 - .03*c.signaling)
                c.stress = clamp(c.stress + .12*(1-nutrition) + .05*c.signaling - .08*nutrition)
                c.membrane = clamp(c.membrane - .04*c.stress + .03*nutrition)
                if c.energy < .12 or c.membrane < .25 or c.stress > .9:
                    c.state = "inactive"
                elif c.energy > .85 and c.stress < .25 and c.age >= 3:
                    c.energy = clamp(c.energy * .6)
                    c.age = 0
                    new_cells.append(Cell(uuid.uuid4().hex[:16], generation=c.generation+1,
                                          energy=c.energy))
                self._store(c)
            for cell in new_cells:
                self._store(cell)
        return self.summary()

    def summary(self):
        cells = self.cells()
        active = [c for c in cells if c.state == "active"]
        return {"model":"gpt-biochip-digital-cells", "type":"abstract_simulation",
                "total":len(cells), "active":len(active),
                "inactive":len(cells)-len(active),
                "generations":max((c.generation for c in cells),default=0),
                "mean_energy":round(sum(c.energy for c in active)/len(active),4) if active else 0,
                "physical_cells_created":0}

    def close(self):
        self.db.close()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db",default="colony.sqlite3")
    sub = p.add_subparsers(dest="command",required=True)
    sub.add_parser("status")
    seed = sub.add_parser("seed"); seed.add_argument("--count",type=int,default=10)
    tick = sub.add_parser("tick")
    tick.add_argument("--steps",type=int,default=1)
    tick.add_argument("--nutrition",type=float,default=.5)
    tick.add_argument("--stimulus",type=float,default=0)
    args = p.parse_args()
    col = CellColony(args.db)
    try:
        if args.command == "seed":
            out = col.seed(args.count)
        elif args.command == "tick":
            if not 0 <= args.steps <= 10000:
                raise ValueError("steps must be 0..10000")
            out = col.summary()
            for _ in range(args.steps):
                out = col.tick(args.nutrition,args.stimulus)
        else:
            out = col.summary()
        print(json.dumps(out,indent=2))
    finally:
        col.close()

if __name__ == "__main__":
    main()
