from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import stat
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .intel import GovernmentSourceRegistry


class Role(str, Enum):
    OFFICER = "OFFICER"
    CPR = "CPR"
    ADMIN = "ADMIN"
    LLM = "LLM"
    MAX = "MAX"


class TrustState(str, Enum):
    DISCOVERED = "DISCOVERED"
    QUARANTINED = "QUARANTINED"
    VERIFIED = "VERIFIED"
    APPOINTED = "APPOINTED"
    BLACKHOUSE = "BLACKHOUSE"
    REJECTED = "REJECTED"


@dataclass(slots=True)
class AgentCandidate:
    agent_id: str
    name: str
    version: str
    fingerprint: str
    capabilities: list[str]
    test_score: float
    provenance_score: float
    integrity_score: float
    trust_state: str = TrustState.QUARANTINED.value
    source_path: str = ""
    observed_at: int = field(default_factory=lambda: int(time.time()))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Appointment:
    appointment_id: str
    agent_id: str
    role: str
    confidence: float
    score: float
    reasons: list[str]
    recommended_permissions: list[str]
    created_at: int = field(default_factory=lambda: int(time.time()))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ActionProposal:
    action_id: str
    action_type: str
    subject: str
    risk: str
    rationale: list[str]
    requires_approval: bool
    created_at: int = field(default_factory=lambda: int(time.time()))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS objects(
  object_id TEXT PRIMARY KEY,
  object_type TEXT NOT NULL,
  data_json TEXT NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS links(
  src_id TEXT NOT NULL,
  link_type TEXT NOT NULL,
  dst_id TEXT NOT NULL,
  data_json TEXT NOT NULL DEFAULT '{}',
  created_at INTEGER NOT NULL,
  PRIMARY KEY(src_id, link_type, dst_id)
);
CREATE TABLE IF NOT EXISTS appointments(
  appointment_id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL,
  role TEXT NOT NULL,
  confidence REAL NOT NULL,
  score REAL NOT NULL,
  reasons_json TEXT NOT NULL,
  permissions_json TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
"""


class OntologyStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def upsert_object(self, object_id: str, object_type: str, data: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO objects(object_id,object_type,data_json,updated_at)
               VALUES(?,?,?,?)
               ON CONFLICT(object_id) DO UPDATE SET
                 object_type=excluded.object_type,
                 data_json=excluded.data_json,
                 updated_at=excluded.updated_at""",
            (object_id, object_type, json.dumps(data, sort_keys=True), int(time.time())),
        )
        self.conn.commit()

    def get_object(self, object_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM objects WHERE object_id=?", (object_id,)).fetchone()
        if not row:
            return None
        return {"object_id": row["object_id"], "object_type": row["object_type"], "data": json.loads(row["data_json"]), "updated_at": row["updated_at"]}

    def list_objects(self, object_type: str | None = None) -> list[dict[str, Any]]:
        if object_type:
            rows = self.conn.execute("SELECT * FROM objects WHERE object_type=? ORDER BY updated_at DESC", (object_type,)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM objects ORDER BY updated_at DESC").fetchall()
        return [{"object_id": r["object_id"], "object_type": r["object_type"], "data": json.loads(r["data_json"]), "updated_at": r["updated_at"]} for r in rows]

    def link(self, src_id: str, link_type: str, dst_id: str, data: dict[str, Any] | None = None) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO links(src_id,link_type,dst_id,data_json,created_at) VALUES(?,?,?,?,?)",
            (src_id, link_type, dst_id, json.dumps(data or {}, sort_keys=True), int(time.time())),
        )
        self.conn.commit()

    def add_appointment(self, appointment: Appointment) -> None:
        a = appointment.to_dict()
        self.conn.execute(
            "INSERT OR REPLACE INTO appointments VALUES(?,?,?,?,?,?,?,?)",
            (a["appointment_id"], a["agent_id"], a["role"], a["confidence"], a["score"], json.dumps(a["reasons"]), json.dumps(a["recommended_permissions"]), a["created_at"]),
        )
        self.conn.commit()

    def latest_appointment(self, agent_id: str) -> dict[str, Any] | None:
        r = self.conn.execute("SELECT * FROM appointments WHERE agent_id=? ORDER BY created_at DESC LIMIT 1", (agent_id,)).fetchone()
        if not r:
            return None
        return {"appointment_id": r["appointment_id"], "agent_id": r["agent_id"], "role": r["role"], "confidence": r["confidence"], "score": r["score"], "reasons": json.loads(r["reasons_json"]), "recommended_permissions": json.loads(r["permissions_json"]), "created_at": r["created_at"]}


CAPS = {
    Role.OFFICER: {"orchestrate": 2.0, "coordinate": 2.0, "policy": 1.5, "plan": 1.5, "reason": 1.0, "delegate": 1.0, "verify": 0.5},
    Role.CPR: {"diagnose": 2.0, "recover": 2.0, "repair": 2.0, "verify": 1.5, "rollback": 1.0, "healthcheck": 1.0},
    Role.ADMIN: {"configure": 2.0, "deploy": 1.5, "maintain": 1.5, "backup": 1.0, "observe": 0.5, "verify": 0.5},
    Role.LLM: {"reason": 2.0, "code": 1.5, "analyze": 1.5, "summarize": 1.0, "classify": 1.0, "plan": 1.0},
}

PERMISSIONS = {
    Role.OFFICER: ["ontology:read", "mission:plan", "agent:recommend", "action:propose"],
    Role.CPR: ["telemetry:read", "diagnostic:run", "recovery:propose", "verify:run"],
    Role.ADMIN: ["inventory:read", "config:propose", "deployment:propose", "backup:verify"],
    Role.LLM: ["ontology:read", "evidence:read", "analysis:write", "action:propose"],
    Role.MAX: ["ontology:read", "evidence:read", "mission:plan", "agent:recommend", "diagnostic:run", "analysis:write", "action:propose", "verify:run"],
}


class AppointmentEngine:
    def appoint(self, candidate: AgentCandidate) -> Appointment:
        assurance = candidate.test_score * 0.40 + candidate.provenance_score * 0.25 + candidate.integrity_score * 0.35
        caps = set(candidate.capabilities)
        scored: list[tuple[float, Role, list[str]]] = []
        for role, weights in CAPS.items():
            matched = sorted(c for c in caps if c in weights)
            capability_score = sum(weights[c] for c in matched) / sum(weights.values())
            total = capability_score * 0.65 + assurance * 0.35
            scored.append((total, role, [f"capability-fit={capability_score:.2f}", f"assurance={assurance:.2f}", f"matched={','.join(matched) or 'none'}"]))
        scored.sort(key=lambda x: x[0], reverse=True)
        score, role, reasons = scored[0]
        breadth = sum(1 for weights in CAPS.values() if sum(1 for c in caps if c in weights) >= 2)
        if assurance >= 0.92 and candidate.test_score >= 0.95 and candidate.integrity_score >= 0.95 and breadth >= 3 and score >= 0.70:
            role = Role.MAX
            score = min(1.0, score * 0.70 + assurance * 0.30)
            reasons += [f"multi-domain-breadth={breadth}/4", "MAX threshold satisfied"]
        confidence = min(0.99, 0.35 + 0.25 * assurance + 0.25 * min(1.0, score) + 0.15 * min(1.0, len(caps) / 8))
        return Appointment(str(uuid.uuid4()), candidate.agent_id, role.value, round(confidence, 3), round(score, 3), reasons, PERMISSIONS[role])


class AIPDecisionLayer:
    def propose_appointment(self, candidate: AgentCandidate, appointment: Appointment) -> ActionProposal:
        high_authority = appointment.role in {Role.OFFICER.value, Role.ADMIN.value, Role.MAX.value}
        return ActionProposal(
            action_id=str(uuid.uuid4()),
            action_type="appoint-agent",
            subject=candidate.agent_id,
            risk="high" if high_authority else "medium",
            rationale=[f"ontology-role={appointment.role}", f"confidence={appointment.confidence}", f"score={appointment.score}", "role classification is separate from runtime privilege"],
            requires_approval=high_authority,
        )


class FriendGate:
    def __init__(self, state_root: str | Path) -> None:
        self.state = Path(state_root)
        self.inbox = self.state / "agent-inbox"
        self.quarantine = self.state / "quarantine"
        self.friends = self.state / "BLACKHOUSE" / "friends"
        for p in (self.inbox, self.quarantine, self.friends):
            p.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def fingerprint(path: Path) -> str:
        h = hashlib.sha256()
        for child in sorted(p for p in path.rglob("*") if p.is_file()):
            h.update(str(child.relative_to(path)).encode("utf-8"))
            h.update(child.read_bytes())
        return h.hexdigest()

    def discover(self) -> list[AgentCandidate]:
        result: list[AgentCandidate] = []
        for package in sorted(self.inbox.iterdir()):
            if not package.is_dir() or package.name.startswith("."):
                continue
            manifest_path = package / "agent.json"
            if not manifest_path.exists():
                continue
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            agent_id = str(uuid.uuid4())
            qpath = self.quarantine / f"{agent_id}-{package.name}"
            shutil.move(str(package), qpath)
            c = AgentCandidate(
                agent_id=agent_id,
                name=str(manifest.get("name", package.name)),
                version=str(manifest.get("version", "0")),
                fingerprint=self.fingerprint(qpath),
                capabilities=sorted({str(x) for x in manifest.get("capabilities", [])}),
                test_score=float(manifest.get("test_score", 0.0)),
                provenance_score=float(manifest.get("provenance_score", 0.0)),
                integrity_score=float(manifest.get("integrity_score", 0.0)),
                source_path=str(qpath),
            )
            if c.test_score >= 0.80 and c.provenance_score >= 0.70 and c.integrity_score >= 0.90:
                c.trust_state = TrustState.VERIFIED.value
            result.append(c)
        return result

    def promote(self, candidate: AgentCandidate, appointment: Appointment) -> Path:
        if candidate.trust_state not in {TrustState.VERIFIED.value, TrustState.APPOINTED.value}:
            raise PermissionError("candidate has not passed verification")
        if appointment.confidence < 0.70:
            raise PermissionError("appointment confidence below Black House threshold")
        src = Path(candidate.source_path)
        if not src.exists():
            raise FileNotFoundError(src)
        dest = self.friends / f"{candidate.name}-{candidate.agent_id}"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.move(str(src), dest)
        member = {**candidate.to_dict(), "trust_state": TrustState.BLACKHOUSE.value, "appointment": appointment.to_dict(), "blackhouse_path": str(dest), "promoted_at": int(time.time())}
        (dest / "blackhouse-member.json").write_text(json.dumps(member, indent=2, sort_keys=True), encoding="utf-8")
        return dest


class NVDSource:
    base_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"

    def fetch_cve(self, cve_id: str, timeout: int = 30) -> dict[str, Any]:
        url = self.base_url + "?" + urlencode({"cveId": cve_id})
        headers = {"User-Agent": "krakenXYZ-Kraken-Jutsu/0.3", "Accept": "application/json"}
        if os.getenv("NVD_API_KEY"):
            headers["apiKey"] = os.environ["NVD_API_KEY"]
        req = Request(url, headers=headers)
        with urlopen(req, timeout=timeout) as response:  # nosec B310 -- fixed HTTPS host.
            return json.load(response)


@dataclass(slots=True)
class USBLayout:
    mount: Path
    runtime: Path
    state: Path


def install_usb(source_root: str | Path, mount: str | Path) -> USBLayout:
    mount = Path(mount).expanduser().resolve()
    if not mount.exists() or not os.access(mount, os.W_OK):
        raise PermissionError(f"USB mount unavailable or not writable: {mount}")
    runtime = mount / "KRAKENXYZ"
    state = mount / ".krakenxyz"
    app = runtime / "app"
    runtime.mkdir(parents=True, exist_ok=True)
    state.mkdir(parents=True, exist_ok=True)
    if app.exists():
        shutil.rmtree(app)
    shutil.copytree(Path(source_root).resolve(), app, ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", ".pytest_cache"))
    for rel in ("agent-inbox", "quarantine", "BLACKHOUSE/friends"):
        (state / rel).mkdir(parents=True, exist_ok=True)
    launcher = runtime / "kraken-jutsu"
    launcher.write_text("#!/bin/sh\nset -eu\n" + f'export KRAKENXYZ_STATE="{state}"\n' + f'export PYTHONPATH="{app.parent}${{PYTHONPATH:+:$PYTHONPATH}}"\n' + 'exec python3 -m kraken_jutsu.live "$@"\n', encoding="utf-8")
    launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return USBLayout(mount, runtime, state)


class LiveRuntime:
    def __init__(self, state_root: str | Path) -> None:
        self.state = Path(state_root)
        self.state.mkdir(parents=True, exist_ok=True)
        self.store = OntologyStore(self.state / "ontology.db")
        self.friends = FriendGate(self.state)
        self.audit = self.state / "audit.jsonl"

    def audit_event(self, event: str, payload: dict[str, Any]) -> None:
        with self.audit.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": int(time.time()), "event": event, "payload": payload}, sort_keys=True) + "\n")

    def ingest_kev(self) -> int:
        payload = GovernmentSourceRegistry().fetch_json("cisa-kev")
        rows = payload.get("vulnerabilities", [])
        self.store.upsert_object("source:cisa-kev", "DataSource", {"name": "CISA KEV", "count": len(rows), "dateReleased": payload.get("dateReleased")})
        for row in rows:
            cve = row.get("cveID")
            if cve:
                self.store.upsert_object(cve, "Vulnerability", row)
                self.store.link("source:cisa-kev", "ASSERTS", cve)
        self.audit_event("source.ingest", {"source": "CISA-KEV", "count": len(rows)})
        return len(rows)

    def discover_and_appoint(self) -> list[dict[str, Any]]:
        engine = AppointmentEngine()
        aip = AIPDecisionLayer()
        output = []
        for c in self.friends.discover():
            self.store.upsert_object(c.agent_id, "AgentCandidate", c.to_dict())
            appt = engine.appoint(c)
            self.store.add_appointment(appt)
            proposal = aip.propose_appointment(c, appt)
            self.store.upsert_object(proposal.action_id, "ActionProposal", proposal.to_dict())
            self.store.link(c.agent_id, "HAS_APPOINTMENT", appt.appointment_id)
            self.store.link(c.agent_id, "HAS_ACTION_PROPOSAL", proposal.action_id)
            self.audit_event("agent.appointed", {"agent": c.to_dict(), "appointment": appt.to_dict(), "proposal": proposal.to_dict()})
            output.append({"agent": c.to_dict(), "appointment": appt.to_dict(), "proposal": proposal.to_dict()})
        return output


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(prog="kraken-jutsu-live")
    p.add_argument("--state", default=os.getenv("KRAKENXYZ_STATE", ".krakenxyz"))
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ingest-kev")
    sub.add_parser("discover-appoint")
    sub.add_parser("status")
    u = sub.add_parser("init-usb")
    u.add_argument("--mount", required=True)
    args = p.parse_args()
    if args.cmd == "init-usb":
        layout = install_usb(Path(__file__).resolve().parents[1], args.mount)
        print(json.dumps({"mount": str(layout.mount), "runtime": str(layout.runtime), "state": str(layout.state)}, indent=2))
    else:
        rt = LiveRuntime(args.state)
        if args.cmd == "ingest-kev":
            print(json.dumps({"count": rt.ingest_kev()}, indent=2))
        elif args.cmd == "discover-appoint":
            print(json.dumps(rt.discover_and_appoint(), indent=2))
        else:
            print(json.dumps({"agents": rt.store.list_objects("AgentCandidate"), "sources": rt.store.list_objects("DataSource"), "actions": rt.store.list_objects("ActionProposal")}, indent=2))
