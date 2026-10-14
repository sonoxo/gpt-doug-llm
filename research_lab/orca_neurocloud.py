"""GPT-Doug/Orca NeuroCloud: synthetic neuron graph and humanoid state simulator.

No biological cells, physical chip connections or actuator commands.
Standard-library-only; HTTP listener binds to loopback by default.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
import time
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

JOINTS = ("head", "left_shoulder", "right_shoulder", "left_elbow",
          "right_elbow", "left_hip", "right_hip", "left_knee", "right_knee")
LIMIT = 64


@dataclass(frozen=True)
class Synapse:
    source: int
    target: int
    weight: float


class NeuroGraph:
    def __init__(self, neurons: int = 12):
        if not 2 <= neurons <= LIMIT:
            raise ValueError("neuron count must be between 2 and 64")
        self.neurons = neurons
        self.state = [0.0] * neurons
        self.synapses = [Synapse(i, (i + 1) % neurons, 0.4) for i in range(neurons)]
        self.synapses += [Synapse(i, (i + 3) % neurons, -0.15) for i in range(neurons)]
        self.tick_count = 0

    def tick(self, stimuli: list[float] | None = None) -> list[float]:
        inputs = stimuli if stimuli is not None else [0.0] * self.neurons
        if len(inputs) != self.neurons or any(not math.isfinite(float(x)) or abs(float(x)) > 1 for x in inputs):
            raise ValueError("stimuli must be finite values in [-1,1] for every neuron")
        currents = [float(x) for x in inputs]
        for edge in self.synapses:
            currents[edge.target] += self.state[edge.source] * edge.weight
        self.state = [round(math.tanh(v), 6) for v in currents]
        self.tick_count += 1
        return list(self.state)


class HumanoidTwin:
    """Read-only simulated pose; never issues motor commands."""

    def __init__(self, graph: NeuroGraph):
        self.graph = graph

    def snapshot(self) -> dict:
        values = self.graph.state
        return {
            "type": "synthetic_humanoid_digital_twin",
            "simulation": True,
            "tick": self.graph.tick_count,
            "joint_angles_degrees": {
                name: round(values[i % len(values)] * 45, 3)
                for i, name in enumerate(JOINTS)
            },
        }


class BrainMemory:
    def __init__(self, filename: str = ":memory:"):
        self.db = sqlite3.connect(filename)
        self.db.execute("""CREATE TABLE IF NOT EXISTS observations
                         (digest TEXT PRIMARY KEY, created REAL, category TEXT,
                          payload TEXT, provenance TEXT)""")
        self.db.commit()

    def add(self, category: str, data: dict, provenance: str = "simulator") -> str:
        if not category or len(category) > 64:
            raise ValueError("invalid category")
        serialized = json.dumps(data, sort_keys=True, allow_nan=False)
        if len(serialized) > 20000:
            raise ValueError("observation too large")
        digest = hashlib.sha256((category + serialized).encode()).hexdigest()
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO observations VALUES (?,?,?,?,?)",
                            (digest, time.time(), category, serialized, provenance))
        return digest

    def recent(self, limit: int = 10) -> list[dict]:
        limit = max(1, min(limit, 100))
        rows = self.db.execute(
            "SELECT digest, category, payload, provenance FROM observations ORDER BY created DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [{"id": r[0], "category": r[1], "data": json.loads(r[2]),
                 "provenance": r[3]} for r in rows]


class NeuroCloud:
    def __init__(self, neurons: int = 12, database: str = ":memory:"):
        self.graph = NeuroGraph(neurons)
        self.twin = HumanoidTwin(self.graph)
        self.memory = BrainMemory(database)

    def cycle(self) -> dict:
        # Intentionally deterministic and bounded: a synthetic impulse only.
        stimulus = [1.0 if self.graph.tick_count % self.graph.neurons == i else 0.0
                    for i in range(self.graph.neurons)]
        activations = self.graph.tick(stimulus)
        snapshot = self.twin.snapshot()
        self.memory.add("humanoid_pose", snapshot)
        return {"neural": {"neurons": self.graph.neurons,
                           "synapses": len(self.graph.synapses),
                           "activations": activations},
                "humanoid": snapshot, "memory_items": len(self.memory.recent(100))}


def handler_factory(cloud: NeuroCloud):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/health":
                body = {"ok": True, "service": "gpt-orca-neurocloud",
                        "simulation": True, "tick": cloud.graph.tick_count}
            elif self.path == "/snapshot":
                body = {"neural_state": cloud.graph.state, "humanoid": cloud.twin.snapshot()}
            else:
                self.send_error(404)
                return
            payload = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="GPT-Orca NeuroCloud simulated chip")
    parser.add_argument("--neurons", type=int, default=12)
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--db", default=":memory:")
    parser.add_argument("--serve", action="store_true", help="Read-only local health endpoint")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not 0 <= args.cycles <= 100:
        parser.error("--cycles must be 0..100")
    cloud = NeuroCloud(args.neurons, args.db)
    for _ in range(args.cycles):
        print(json.dumps(cloud.cycle()))
    if args.serve:
        print("Listening on 127.0.0.1:%d (read only)" % args.port)
        ThreadingHTTPServer(("127.0.0.1", args.port), handler_factory(cloud)).serve_forever()


if __name__ == "__main__":
    main()
