"""Governed GPT-Doug sensor swarm: bounded, read-only, offline observation ingestion.

No remote discovery, credentials, camera capture, actuation, or covert tracking.
"""
from __future__ import annotations

import concurrent.futures
import csv
import hashlib
import io
import json
import math
import os
import re
import shutil
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

SCHEMA = "gpt-doug.sensor-swarm.v1"
EVENT_SCHEMA = "gpt-doug.sensor-observation.v1"
KINDS = {"synthetic", "biopineal", "host-health", "json", "jsonl", "csv"}
FILE_KINDS = {"json", "jsonl", "csv"}
MAX_SENSORS = 16
MAX_BYTES = 262144
MAX_ROWS = 128
MAX_RETAINED_EVENTS = 50000
DEFAULT_DB = Path.home() / ".config" / "gpt-doug" / "sensor-swarm.sqlite3"
POLICY_PATH = Path(__file__).resolve().parents[1] / "docs" / "sensor-policy.json"
IDENT = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,63}$")
SAFE_UNIT = re.compile(r"^[A-Za-z0-9/%_. -]{0,24}$")
ALLOWED_ENUMS = {"OK", "WARN", "ERROR", "ONLINE", "OFFLINE", "UP", "DOWN", "PASS", "FAIL", "UNKNOWN", "UNVERIFIED", "VERIFIED", "PENDING", "LOW", "MEDIUM", "HIGH", "HEALTHY", "DEGRADED", "ACTIVE", "INACTIVE"}
SENSITIVE = re.compile(r"password|secret|bearer|api.?key|access.?token|private.?key|credential|@|gh[pousr]_|sk-[A-Za-z0-9_-]{16,}|xox[baprs]-", re.I)

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def load_policy(path=POLICY_PATH):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("sensor governance policy unavailable or malformed") from exc
    if data.get("mode") != "AUTHORIZED_SENSORS_ONLY" or not data.get("controls", {}).get("explicit_authorization_required"):
        raise ValueError("fail-closed sensor policy required")
    forbidden_controls = ("facial_recognition", "biometric_identification",
                          "license_plate_owner_lookup", "covert_person_tracking",
                          "private_residence_monitoring", "weapon_targeting",
                          "fire_control", "autonomous_external_action")
    if any(data["controls"].get(name) is not False for name in forbidden_controls):
        raise ValueError("unsafe sensor capabilities not explicitly denied")
    required_forbidden_types = {"person", "face", "biometric_identity",
                                "license_plate_owner", "private_vehicle", "private_residence",
                                "weapon_target", "live_military_unit"}
    prohibited = set(data.get("prohibited_object_types", []))
    if not required_forbidden_types <= prohibited:
        raise ValueError("mandatory prohibited object types missing from sensor policy")
    required_controls = ("provenance_required", "human_review_for_material_actions")
    if not all(data["controls"].get(name) is True for name in required_controls):
        raise ValueError("mandatory sensor controls are missing")
    if not isinstance(data.get("allowed_object_types"), list) or not isinstance(data.get("prohibited_object_types"), list):
        raise ValueError("object-type policy missing")
    return data

def validate_specs(specs, policy):
    if type(specs) is not list or not 1 <= len(specs) <= MAX_SENSORS:
        raise ValueError("expected 1 to 16 registered sensors")
    allowed = set(policy["allowed_object_types"]) - set(policy["prohibited_object_types"])
    seen = set()
    for spec in specs:
        if type(spec) is not dict or not {"id", "kind", "source_id", "object_type", "authorization_scope", "purpose", "classification"} <= spec.keys():
            raise ValueError("sensor registration fields missing")
        if set(spec) - {"id", "kind", "source_id", "object_type", "authorization_scope", "purpose", "classification", "path"}:
            raise ValueError("unknown sensor registration field")
        for field in ("id", "source_id", "authorization_scope", "purpose"):
            if not isinstance(spec[field], str) or not IDENT.fullmatch(spec[field]) or SENSITIVE.search(spec[field]):
                raise ValueError("invalid sensor metadata")
        if spec["id"] in seen:
            raise ValueError("duplicate sensor ID")
        seen.add(spec["id"])
        if spec["kind"] not in KINDS or spec["object_type"] not in allowed:
            raise ValueError("sensor adapter or object type denied by policy")
        if spec["classification"] not in {"public", "synthetic", "authorized_local"}:
            raise ValueError("invalid data classification")
        if spec["kind"] in FILE_KINDS:
            if not isinstance(spec.get("path"), str) or not spec["path"]:
                raise ValueError("approved relative file path required")
            if spec["classification"] == "synthetic":
                raise ValueError("file classification must reflect its authorization")
        elif "path" in spec:
            raise ValueError("only file sensors may contain paths")
        if spec["kind"] == "biopineal" and spec["object_type"] != "research_evidence":
            raise ValueError("BioPineal is evidence, not physical telemetry")
        if spec["kind"] == "host-health" and spec["object_type"] != "infrastructure_asset":
            raise ValueError("host-health is infrastructure telemetry")
        if spec["kind"] == "synthetic" and spec["classification"] != "synthetic":
            raise ValueError("synthetic events must be labeled synthetic")
    return specs

def load_manifest(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("manifest unavailable or malformed") from exc
    if type(data) is not dict or set(data) != {"schema", "sensors"} or data["schema"] != SCHEMA:
        raise ValueError("unsupported or invalid manifest schema")
    validate_specs(data["sensors"], load_policy())
    return data["sensors"]

def safe_path(root, name, kind):
    if root is None:
        raise PermissionError("file sensors require an explicitly approved --root")
    if "\\" in name or "\x00" in name:
        raise ValueError("invalid file path")
    rel = PurePosixPath(name)
    if rel.is_absolute() or any(part in {"", ".", ".."} or part.startswith(".") for part in rel.parts):
        raise ValueError("unsafe relative path")
    if rel.suffix != "." + kind:
        raise ValueError("file extension must match registered sensor adapter")
    base = Path(root).expanduser().resolve(strict=True)
    if not base.is_dir():
        raise ValueError("approved root must be a directory")
    current = base
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("symlinked sensor paths are not allowed")
    target = current.resolve(strict=True)
    if not target.is_relative_to(base) or not target.is_file():
        raise ValueError("file path escaped approved root")
    if target.stat().st_size > MAX_BYTES:
        raise ValueError("sensor file exceeds byte limit")
    return target

def timestamp(value):
    if value is None:
        return utc_now()
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO 8601 string")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid ISO 8601 timestamp") from exc
    if dt.tzinfo is None or dt.year < 1970 or dt > datetime.now(timezone.utc) + timedelta(days=1):
        raise ValueError("timestamp requires timezone and supported range")
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")

def observation(spec, row, *, locator, sha):
    if type(row) is not dict or set(row) - {"metric", "value", "unit", "observed_at"}:
        raise ValueError("only metric, value, unit and observed_at are allowed in rows")
    metric, value, unit = row.get("metric"), row.get("value"), row.get("unit", "")
    if not isinstance(metric, str) or not IDENT.fullmatch(metric) or SENSITIVE.search(metric):
        raise ValueError("metric label denied")
    if type(value) in (int, float):
        if abs(value) > 1e15 or not math.isfinite(value):
            raise ValueError("numeric value out of bounds")
    elif type(value) is bool:
        pass
    elif type(value) is str:
        if value not in ALLOWED_ENUMS or SENSITIVE.search(value):
            raise ValueError("text value denied; no PII, credentials, or free-form text")
    else:
        raise ValueError("only bounded scalar sensor values are supported")
    if not isinstance(unit, str) or not SAFE_UNIT.fullmatch(unit):
        raise ValueError("invalid unit")
    observed = timestamp(row.get("observed_at"))
    identity = {"sensor_id": spec["id"], "source_id": spec["source_id"],
                "metric": metric, "value": value, "unit": unit,
                "object_type": spec["object_type"],
                "classification": spec["classification"],
                "authorization_scope": spec["authorization_scope"], "purpose": spec["purpose"],
                "observed_at": observed, "source_sha256": sha, "locator": locator}
    return {"schema": EVENT_SCHEMA, "id": digest(identity),
            "sensor_id": spec["id"], "source_id": spec["source_id"],
            "object_type": spec["object_type"], "authorization_scope": spec["authorization_scope"],
            "purpose": spec["purpose"], "classification": spec["classification"],
            "observed_at": observed, "ingested_at": utc_now(),
            "metric": metric, "value": value, "unit": unit,
            "provenance": {"adapter": spec["kind"], "locator": locator,
                           "source_sha256": sha, "authenticity_verified": False},
            "read_only": True}

def collect_one(spec, root=None):
    kind = spec["kind"]
    if kind in FILE_KINDS:
        target = safe_path(root, spec["path"], kind)
        raw = target.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        text = raw.decode("utf-8-sig")
        if kind == "json":
            data = json.loads(text)
            rows = data if isinstance(data, list) else data.get("observations") if isinstance(data, dict) else None
        elif kind == "jsonl":
            rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        else:
            rows = list(csv.DictReader(io.StringIO(text)))
        if type(rows) is not list or len(rows) > MAX_ROWS:
            raise ValueError("unbounded or invalid sensor rows")
        events = []
        fallback_time = datetime.fromtimestamp(target.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")
        for i, row in enumerate(rows, 1):
            if kind == "csv":
                if not isinstance(row, dict) or "value" not in row:
                    raise ValueError("CSV requires a value column")
                val = row["value"]
                try:
                    row["value"] = json.loads(val)
                except (TypeError, ValueError):
                    row["value"] = val
                row = {k: v for k, v in row.items() if v not in (None, "")}
            if not isinstance(row, dict):
                raise ValueError("row must be a JSON object")
            row.setdefault("observed_at", fallback_time)
            events.append(observation(spec, row, locator=f"row:{i}", sha=sha))
        return events
    if kind == "host-health":
        now = utc_now()
        return [
            observation(spec, {"metric": "logical_cpu_count", "value": os.cpu_count() or 1,
                               "unit": "cores", "observed_at": now},
                        locator="stdlib:os.cpu_count", sha=digest("python-os")),
            observation(spec, {"metric": "local_free_space_bytes", "value": shutil.disk_usage(Path.home()).free,
                               "unit": "bytes", "observed_at": now},
                        locator="stdlib:shutil.disk_usage", sha=digest("python-shutil")),
        ]
    if kind == "biopineal":
        from research_lab.biopineal_patent import report as patent_report
        from research_lab.biopineal_phase2 import graph as research_graph
        prior, kg = patent_report(), research_graph()
        stamp = prior["patent"]["publication_date"] + "T00:00:00Z"
        evidence = [
            ("atom_balance_confirmed", prior["equation_balanced"]),
            ("official_patent_record_verified", kg["official_record_verified"]),
            ("patent_rights_verified", kg["technology_use_rights_verified"]),
            ("evidence_graph_node_count", len(kg["nodes"])),
        ]
        return [observation(spec, {"metric": key, "value": val, "observed_at": stamp},
                            locator="repo:biopineal-evidence", sha=prior["sha256"])
                for key, val in evidence]
    if kind == "synthetic":
        return [observation(spec, {"metric": "synthetic_heartbeat", "value": True,
                                    "observed_at": "2026-10-13T00:00:00Z"},
                            locator="synthetic:fixture", sha=digest("synthetic-v1"))]
    raise ValueError("unknown sensor adapter")

def snapshot(specs, *, root=None, authorized_local=False, policy_path=POLICY_PATH):
    policy = load_policy(policy_path)
    validate_specs(specs, policy)
    if not authorized_local and any(s["kind"] in FILE_KINDS | {"host-health"} for s in specs):
        raise PermissionError("real local sensors require --authorize-local")
    if any(s["kind"] in FILE_KINDS for s in specs) and root is None:
        raise PermissionError("local file sensors require explicit --root")
    events, statuses, seen = [], [], set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(specs))) as executor:
        futures = {s["id"]: executor.submit(collect_one, s, root) for s in specs}
        for spec in specs:
            state = {"id": spec["id"], "adapter": spec["kind"], "status": "healthy",
                     "accepted": 0, "duplicates": 0}
            try:
                gathered = futures[spec["id"]].result(timeout=8)
                if len(gathered) > MAX_ROWS:
                    raise ValueError("sensor emitted too many events")
                for event in gathered:
                    if event["id"] in seen:
                        state["duplicates"] += 1
                    else:
                        seen.add(event["id"])
                        events.append(event)
                        state["accepted"] += 1
            except Exception as exc:  # Isolate a failed adapter from unrelated sensors.
                state["status"] = "rejected"
                state["error_type"] = type(exc).__name__
                state["accepted"] = 0
            statuses.append(state)
    return {"schema": SCHEMA, "generated_at": utc_now(), "events": events,
            "sensors": statuses, "accepted": len(events),
            "rejected_sensors": sum(x["status"] == "rejected" for x in statuses),
            "read_only": True, "network_scanning": False,
            "autonomous_external_action": False}

def demo_specs():
    common = {"authorization_scope": "offline-research", "purpose": "research-observability"}
    return [{"id": "biopineal-evidence", "kind": "biopineal", "source_id": "repo-biopineal",
             "object_type": "research_evidence", "classification": "public", **common},
            {"id": "synthetic-pulse", "kind": "synthetic", "source_id": "local-fixture",
             "object_type": "environmental_sensor", "classification": "synthetic", **common}]

class Store:
    """Owner-local SQLite journal; not connected to any public endpoint."""
    def __init__(self, path=DEFAULT_DB):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.path.is_symlink():
            raise ValueError("database must not be a symlink")
        self.connection = sqlite3.connect(str(self.path), timeout=5)
        if os.name == "posix":
            self.path.chmod(0o600)
        self.connection.execute("CREATE TABLE IF NOT EXISTS events "
                                "(id TEXT PRIMARY KEY, inserted REAL NOT NULL, payload TEXT NOT NULL)")
        self.connection.execute("CREATE TABLE IF NOT EXISTS health "
                                "(id TEXT PRIMARY KEY, updated REAL NOT NULL, payload TEXT NOT NULL)")
        self.connection.commit()
    def write(self, result, retention_days=7):
        if type(retention_days) is not int or not 1 <= retention_days <= 30:
            raise ValueError("retention must be a whole number of days between 1 and 30")
        with self.connection:
            self.connection.execute("DELETE FROM events WHERE inserted < ?",
                                    (time.time() - retention_days * 86400,))
            for e in result["events"]:
                self.connection.execute("INSERT OR IGNORE INTO events VALUES(?,?,?)",
                                        (e["id"], time.time(), canonical(e)))
            self.connection.execute(
                "DELETE FROM events WHERE id IN "
                "(SELECT id FROM events ORDER BY inserted DESC, id DESC LIMIT -1 OFFSET ?)",
                (MAX_RETAINED_EVENTS,))
            for h in result["sensors"]:
                self.connection.execute("INSERT OR REPLACE INTO health VALUES(?,?,?)",
                                        (h["id"], time.time(), canonical(h)))
    def status(self, limit=40):
        rows = self.connection.execute("SELECT payload FROM events ORDER BY inserted DESC, id DESC LIMIT ?", (limit,))
        events = [json.loads(row[0]) for row in rows]
        statuses = [json.loads(row[0]) for row in self.connection.execute(
            "SELECT payload FROM health ORDER BY id")]
        count = self.connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        return {"schema": SCHEMA, "events": events, "sensors": statuses,
                "stored_count": count, "read_only": True,
                "network_scanning": False, "autonomous_external_action": False}
    def close(self):
        self.connection.close()
