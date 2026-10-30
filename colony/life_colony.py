"""GPT-Doug Biochip / MLM Colony: bounded life-science knowledge agents.

Digital research model only. No wet-lab protocol execution, organisms, hardware
control, clinical decisions or unsupported claims of biological consciousness.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import sqlite3
import uuid

DOMAINS = {
    "molecular": ("DNA", "RNA", "protein", "metabolism"),
    "cellular": ("membrane", "signaling", "cell_cycle", "homeostasis"),
    "tissue": ("differentiation", "extracellular_matrix", "repair"),
    "organ": ("physiology", "interactions", "regulation"),
    "organism": ("behavior", "development", "environment"),
    "ecosystem": ("ecology", "biodiversity", "adaptation"),
    "biochip": ("sensing", "signal_processing", "interfaces"),
    "robotics": ("embodiment_simulation", "perception", "actuation_models"),
}
AGENTS = {
    "gpt-doug-llm": ("orchestrator", tuple(DOMAINS)),
    "gpt-doug-mlm": ("evidence_synthesis", tuple(DOMAINS)),
    "gpt-biochip": ("digital_biochip", ("biochip", "cellular", "molecular")),
    "gpt-humanoid": ("robotics_simulation", ("robotics", "organism")),
    "gpt-organoid": ("organoid_literature", ("cellular", "tissue", "organ")),
}

@dataclass(frozen=True)
class Evidence:
    domain: str
    topic: str
    statement: str
    source: str
    source_type: str = "user_supplied"
    confidence: float = 0.0

class Colony:
    def __init__(self, path: str):
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS evidence (
          id TEXT PRIMARY KEY, domain TEXT NOT NULL, topic TEXT NOT NULL,
          statement TEXT NOT NULL, source TEXT NOT NULL, source_type TEXT NOT NULL,
          confidence REAL NOT NULL, observed_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS proposals (
          id TEXT PRIMARY KEY, agent TEXT NOT NULL, domain TEXT NOT NULL,
          question TEXT NOT NULL, evidence_ids TEXT NOT NULL,
          status TEXT NOT NULL CHECK(status IN ('needs_evidence','human_reviewed')),
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL,
          payload TEXT NOT NULL, timestamp TEXT NOT NULL, digest TEXT NOT NULL
        );
        """)
        self.db.commit()

    def _event(self, event, payload):
        when = datetime.now(timezone.utc).isoformat()
        serialized = json.dumps(payload, sort_keys=True)
        digest = hashlib.sha256((event + serialized + when).encode()).hexdigest()
        self.db.execute("INSERT INTO events(event,payload,timestamp,digest) VALUES(?,?,?,?)",
                        (event, serialized, when, digest))

    def ingest(self, item: Evidence):
        if item.domain not in DOMAINS:
            raise ValueError("Unrecognized life-science domain")
        if not 0 <= item.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        if not all([item.topic.strip(), item.statement.strip(), item.source.strip()]):
            raise ValueError("Evidence needs a topic, statement and source")
        eid = hashlib.sha256(json.dumps(asdict(item), sort_keys=True).encode()).hexdigest()[:24]
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO evidence VALUES(?,?,?,?,?,?,?,?)",
                (eid, item.domain, item.topic, item.statement, item.source, item.source_type,
                 item.confidence, datetime.now(timezone.utc).isoformat()))
            self._event("evidence_ingested", {"id": eid, "domain": item.domain})
        return eid

    def propose(self, agent, domain, question):
        if agent not in AGENTS:
            raise ValueError("Unknown agent")
        if domain not in AGENTS[agent][1]:
            raise ValueError("Agent is not authorized for this domain")
        if not question.strip():
            raise ValueError("Question required")
        rows = self.db.execute("SELECT id FROM evidence WHERE domain=? ORDER BY confidence DESC LIMIT 10", (domain,)).fetchall()
        ids = [r[0] for r in rows]
        pid = uuid.uuid4().hex
        status = "needs_evidence"
        with self.db:
            self.db.execute("INSERT INTO proposals VALUES(?,?,?,?,?,?,?)",
                (pid, agent, domain, question, json.dumps(ids), status, datetime.now(timezone.utc).isoformat()))
            self._event("proposal_created", {"id": pid, "evidence_count": len(ids), "status": status})
        return {"proposal_id": pid, "agent": agent, "domain": domain, "question": question,
                "evidence_ids": ids, "status": status,
                "note": "Proposal only. No autonomous experiment, scientific conclusion or action."}

    def status(self):
        count = self.db.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
        proposed = self.db.execute("SELECT COUNT(*) FROM proposals").fetchone()[0]
        events = self.db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        return {"colony": "gpt-doug-biochip-mlm", "mode": "digital_research_only",
                "agents": AGENTS, "life_domains": DOMAINS,
                "evidence_records": count, "proposals": proposed, "events": events,
                "external_tools_enabled": False, "wetlab_enabled": False}

    def close(self):
        self.db.close()

def main():
    p = argparse.ArgumentParser(description="GPT-Doug Biochip-MLM life-science colony")
    p.add_argument("--db", default="colony.sqlite3")
    sp = p.add_subparsers(dest="command", required=True)
    sp.add_parser("status")
    a = sp.add_parser("ingest")
    for x in ("domain", "topic", "statement", "source"):
        a.add_argument("--" + x, required=True)
    a.add_argument("--confidence", type=float, default=0.0)
    q = sp.add_parser("propose")
    q.add_argument("--agent", required=True, choices=AGENTS.keys())
    q.add_argument("--domain", required=True, choices=DOMAINS.keys())
    q.add_argument("--question", required=True)
    args = p.parse_args()
    db = Colony(args.db)
    try:
        if args.command == "status":
            result = db.status()
        elif args.command == "ingest":
            result = {"evidence_id": db.ingest(Evidence(args.domain, args.topic, args.statement, args.source, confidence=args.confidence))}
        else:
            result = db.propose(args.agent, args.domain, args.question)
        print(json.dumps(result, indent=2))
    finally:
        db.close()

if __name__ == "__main__":
    main()
