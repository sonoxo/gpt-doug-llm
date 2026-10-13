"""Deterministic Guardian robotics simulation; no hardware/network/targeting APIs.

The bio-computer metaphor here is software-only: battery = metabolism,
heartbeat = safety cycle, audit log = memory, unit isolation = immune response.
All motion occurs in a fictitious integer grid and does not command real robots.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

OWNER = "Douglas Montel Brown Jr."
MODE = "GUARDIAN_SYNTHETIC_TRAINING"
WIDTH, HEIGHT = 26, 16
MAX_UNITS, MAX_INCIDENTS, MAX_TICKS = 24, 40, 500
ROLES = {"survey", "rescue", "relay", "inspection", "logistics"}
AUTO_TASKS = {"survey", "inspection"}
BLOCKED_FIELDS = {
    "weapon", "weapons", "payload", "ammunition", "munition", "fire_control",
    "attack", "attack_plan", "engagement", "engage", "strike", "target", "target_id",
    "person_id", "person_name", "biometric", "face_id", "gps", "lat", "lon",
    "lng", "latitude", "longitude", "coordinates", "aimpoint", "guidance",
    "actuator", "actuation_command", "hardware_port", "radio_address", "ip_address",
    "external_command", "external_action", "cot_endpoint", "endpoint", "url",
}
UNIT_KEYS = {"id", "role", "x", "y", "battery", "quality"}
INCIDENT_KEYS = {"id", "kind", "x", "y", "severity", "description"}
SCENARIO_KEYS = {"scenarioId", "syntheticOnly", "units", "obstacles", "incidents"}


class GuardianError(ValueError):
    """Invalid request or a denied unsafe state transition."""


def _scan(value: Any, path: str = "scenario") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).lower().strip() in BLOCKED_FIELDS:
                raise GuardianError(f"restricted field: {path}.{key}")
            _scan(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _scan(child, f"{path}[{index}]")


def _number(value: Any, name: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise GuardianError(f"{name} must be an integer in {low}..{high}")
    return value


def _coord(x: Any, y: Any) -> tuple[int, int]:
    return _number(x, "x", 0, WIDTH - 1), _number(y, "y", 0, HEIGHT - 1)


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 50 or not all(
        c.isalnum() or c in "-_" for c in value
    ):
        raise GuardianError(f"invalid {name}")
    return value


def _ensure_fields(value: Any, fields: set[str], name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GuardianError(f"{name} must be an object")
    _scan(value, name)
    if set(value) - fields:
        raise GuardianError(f"unsupported fields for {name}: {sorted(set(value) - fields)}")
    return value


def default_scenario() -> dict[str, Any]:
    units = [
        ("GDR-01", "survey", 2, 2, 95),
        ("GDR-02", "survey", 2, 5, 87),
        ("GDR-03", "inspection", 3, 8, 91),
        ("GDR-04", "inspection", 2, 11, 84),
        ("GDR-05", "rescue", 5, 3, 98),
        ("GDR-06", "rescue", 5, 5, 94),
        ("GDR-07", "relay", 5, 9, 88),
        ("GDR-08", "relay", 4, 12, 92),
        ("GDR-09", "logistics", 6, 13, 90),
        ("GDR-10", "logistics", 7, 12, 96),
    ]
    return {
        "scenarioId": "GUARDIAN-TRAINING-01", "syntheticOnly": True,
        "units": [dict(id=i, role=r, x=x, y=y, battery=b, quality=95) for i, r, x, y, b in units],
        "obstacles": [[11, y] for y in range(2, 10) if y != 6] + [[17, y] for y in range(7, 14) if y != 10],
        "incidents": [
            {"id": "EV-001", "kind": "inspection", "x": 12, "y": 3, "severity": 2, "description": "Synthetic infrastructure integrity check"},
            {"id": "EV-002", "kind": "relay", "x": 21, "y": 11, "severity": 3, "description": "Simulated communications relay outage"},
            {"id": "EV-003", "kind": "survey", "x": 16, "y": 4, "severity": 1, "description": "Synthetic environmental survey"},
        ],
    }


def _shortest_path(start: tuple[int, int], goal: tuple[int, int], obstacles: set[tuple[int, int]]) -> list[tuple[int, int]] | None:
    if start == goal:
        return []
    todo: deque[tuple[int, int]] = deque([start])
    parents: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    while todo:
        x, y = todo.popleft()
        for node in ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1)):
            if node in parents or node in obstacles or not (0 <= node[0] < WIDTH and 0 <= node[1] < HEIGHT):
                continue
            parents[node] = (x, y)
            if node == goal:
                path: list[tuple[int, int]] = []
                at = goal
                while at != start:
                    path.append(at)
                    at = parents[at]  # type: ignore[assignment]
                return list(reversed(path))
            todo.append(node)
    return None


class GuardianSim:
    """Inspectable state-machine; never interacts with any external device."""

    def __init__(self, scenario: Mapping[str, Any] | None = None):
        raw = _ensure_fields(deepcopy(scenario if scenario is not None else default_scenario()), SCENARIO_KEYS, "scenario")
        if raw.get("syntheticOnly") is not True:
            raise GuardianError("syntheticOnly must be true")
        self.scenario_id = _identifier(raw.get("scenarioId"), "scenarioId")
        objects = raw.get("units")
        if not isinstance(objects, list) or not 1 <= len(objects) <= MAX_UNITS:
            raise GuardianError("unit count exceeds bounded capacity")
        obstacles = raw.get("obstacles", [])
        if not isinstance(obstacles, list) or len(obstacles) > 150:
            raise GuardianError("invalid obstacle list")
        self.obstacles: set[tuple[int, int]] = set()
        for point in obstacles:
            if not isinstance(point, list) or len(point) != 2:
                raise GuardianError("obstacles must be [x,y] pairs")
            self.obstacles.add(_coord(*point))
        self.units: list[dict[str, Any]] = []
        for obj in objects:
            u = _ensure_fields(obj, UNIT_KEYS, "unit")
            ident = _identifier(u.get("id"), "unit id")
            role = u.get("role")
            if role not in ROLES:
                raise GuardianError("unsupported unit role")
            x, y = _coord(u.get("x"), u.get("y"))
            if (x, y) in self.obstacles:
                raise GuardianError("unit occupies obstacle")
            self.units.append({
                "id": ident, "role": role, "x": x, "y": y,
                "homeX": x, "homeY": y,
                "battery": _number(u.get("battery", 100), "battery", 0, 100),
                "quality": _number(u.get("quality", 100), "quality", 0, 100),
                "status": "STANDBY", "task": None, "completed": 0,
            })
        if len({u["id"] for u in self.units}) != len(self.units):
            raise GuardianError("duplicate unit ids")
        self.incidents: list[dict[str, Any]] = []
        incoming = raw.get("incidents", [])
        if not isinstance(incoming, list) or len(incoming) > MAX_INCIDENTS:
            raise GuardianError("incident count exceeds bounded capacity")
        for incident in incoming:
            self._add_incident(incident)
        self.tick = 0
        self.estop = False
        self.audit: list[dict[str, Any]] = []
        self._digest = "0" * 64
        self._event("INITIALIZED", "Synthetic Guardian fleet initialized")

    def _add_incident(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        i = _ensure_fields(raw, INCIDENT_KEYS, "incident")
        ident = _identifier(i.get("id"), "incident id")
        if any(item["id"] == ident for item in self.incidents):
            raise GuardianError("duplicate incident id")
        kind = i.get("kind")
        if kind not in ROLES:
            raise GuardianError("invalid incident kind")
        x, y = _coord(i.get("x"), i.get("y"))
        if (x, y) in self.obstacles:
            raise GuardianError("incident intersects obstacle")
        description = i.get("description", "Synthetic scenario")
        if not isinstance(description, str) or not 1 <= len(description) <= 120:
            raise GuardianError("invalid incident description")
        event = {
            "id": ident, "kind": kind, "x": x, "y": y,
            "severity": _number(i.get("severity", 1), "severity", 1, 5),
            "description": description,
            "approvalRequired": kind not in AUTO_TASKS,
            "approvals": [], "status": "PENDING", "assigned": None,
        }
        self.incidents.append(event)
        return event

    def inject(self, *, incident_id: str, kind: str, x: int, y: int, severity: int, description: str = "Synthetic training scenario") -> dict[str, Any]:
        self._check_running()
        if len(self.incidents) >= MAX_INCIDENTS:
            raise GuardianError("incident capacity reached")
        new = self._add_incident({"id": incident_id, "kind": kind, "x": x, "y": y, "severity": severity, "description": description})
        self._event("INJECTED", new["id"])
        return deepcopy(new)

    def _event(self, action: str, detail: str) -> None:
        seq = len(self.audit) + 1
        data = {"seq": seq, "tick": self.tick, "action": action, "detail": detail[:160], "prev": self._digest}
        digest = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        data["sha256"] = digest
        self.audit.append(data)
        self._digest = digest
        if len(self.audit) > 5000:
            raise GuardianError("audit capacity reached; archive and reset simulation")

    def _global_stop(self) -> bool:
        value = os.getenv("GPT_DOUG_AI_BLOCK_ALL", "").lower().strip()
        if value not in {"", "0", "off", "false", "no"}:
            return True
        folder = Path(os.getenv("GPT_DOUG_AI_STOP_DIR", "~/.gpt-doug/ai-killswitch")).expanduser()
        # Treat malformed/unreadable stop path as a stopped system, matching GPT-Doug fail-closed semantics.
        try:
            if folder.is_symlink() or (folder.exists() and not folder.is_dir()):
                return True
            latch = folder / "STOP"
            return latch.is_symlink() or latch.exists()
        except OSError:
            return True

    def _check_running(self) -> None:
        if self.estop or self._global_stop():
            raise PermissionError("Guardian is in emergency safe-hold")

    def emergency_stop(self, operator: str) -> None:
        actor = _identifier(operator, "operator")
        if not self.estop:
            self.estop = True
            for unit in self.units:
                unit["status"] = "SAFE_HOLD"
                unit["task"] = None
            for incident in self.incidents:
                if incident["status"] == "ASSIGNED":
                    incident["status"] = "PENDING"
                    incident["assigned"] = None
            self._event("E_STOP", actor)

    def resume(self, primary_operator: str, secondary_operator: str) -> None:
        a = _identifier(primary_operator, "primary operator")
        b = _identifier(secondary_operator, "secondary operator")
        if a == b:
            raise PermissionError("two distinct operators required")
        if self._global_stop():
            raise PermissionError("host stop remains latched")
        if self.estop:
            self.estop = False
            for unit in self.units:
                if unit["status"] == "SAFE_HOLD":
                    unit["status"] = "STANDBY"
            self._event("RESUMED", f"{a}+{b}")

    def approve(self, incident_id: str, operator: str) -> dict[str, Any]:
        self._check_running()
        actor = _identifier(operator, "operator")
        incident = next((i for i in self.incidents if i["id"] == incident_id), None)
        if incident is None:
            raise GuardianError("unknown incident")
        if incident["status"] == "COMPLETE":
            raise GuardianError("incident already resolved")
        if not incident["approvalRequired"]:
            return deepcopy(incident)
        if actor in incident["approvals"]:
            raise PermissionError("operator has already approved")
        incident["approvals"].append(actor)
        self._event("APPROVED", f"{incident_id}:{actor}")
        return deepcopy(incident)

    def _can_assign(self, i: dict[str, Any]) -> bool:
        if i["status"] != "PENDING":
            return False
        required = 2 if i["severity"] >= 4 else 1
        return not i["approvalRequired"] or len(i["approvals"]) >= required

    def _assign(self) -> None:
        pending = sorted((i for i in self.incidents if self._can_assign(i)), key=lambda i: (-i["severity"], i["id"]))
        for incident in pending:
            best = None
            for unit in self.units:
                if unit["role"] != incident["kind"] or unit["task"] is not None or unit["status"] in {"QUARANTINED", "SAFE_HOLD", "CHARGING"}:
                    continue
                if unit["quality"] < 35 or unit["battery"] < 20:
                    continue
                path = _shortest_path((unit["x"], unit["y"]), (incident["x"], incident["y"]), self.obstacles)
                ret = _shortest_path((incident["x"], incident["y"]), (unit["homeX"], unit["homeY"]), self.obstacles)
                if path is None or ret is None:
                    continue
                if unit["battery"] < 2 * (len(path) + len(ret)) + 12:
                    continue
                candidate = (len(path), unit["id"], unit)
                if best is None or candidate[:2] < best[:2]:
                    best = candidate
            if best:
                selected = best[2]
                selected["task"] = incident["id"]
                selected["status"] = "ENROUTE"
                incident["status"] = "ASSIGNED"
                incident["assigned"] = selected["id"]
                self._event("DISPATCH", f"{selected['id']}:{incident['id']}")

    def step(self) -> dict[str, Any]:
        self._check_running()
        if self.tick >= MAX_TICKS:
            raise GuardianError("tick budget reached; archive/reset")
        self.tick += 1
        for unit in self.units:
            if unit["quality"] < 35:
                if unit["task"]:
                    inc = next(i for i in self.incidents if i["id"] == unit["task"])
                    inc["status"] = "PENDING"
                    inc["assigned"] = None
                unit["task"] = None
                if unit["status"] != "QUARANTINED":
                    unit["status"] = "QUARANTINED"
                    self._event("QUARANTINE", unit["id"])
        self._assign()
        for unit in self.units:
            if unit["status"] in {"QUARANTINED", "SAFE_HOLD"}:
                continue
            if unit["task"] is not None:
                inc = next(i for i in self.incidents if i["id"] == unit["task"])
                path = _shortest_path((unit["x"], unit["y"]), (inc["x"], inc["y"]), self.obstacles)
                if path is None or unit["battery"] < 2:
                    inc["status"] = "PENDING"
                    inc["assigned"] = None
                    unit["task"] = None
                    unit["status"] = "SAFE_HOLD"
                    self._event("PATH_ABORT", unit["id"])
                    continue
                if path:
                    unit["x"], unit["y"] = path[0]
                    unit["battery"] -= 2
                if (unit["x"], unit["y"]) == (inc["x"], inc["y"]):
                    inc["status"] = "COMPLETE"
                    inc["assigned"] = unit["id"]
                    unit["task"] = None
                    unit["completed"] += 1
                    unit["status"] = "RETURNING"
                    self._event("COMPLETED", f"{unit['id']}:{inc['id']}")
            elif (unit["x"], unit["y"]) == (unit["homeX"], unit["homeY"]):
                unit["status"] = "CHARGING" if unit["battery"] < 85 else "STANDBY"
                if unit["status"] == "CHARGING":
                    unit["battery"] = min(100, unit["battery"] + 4)
            else:
                route = _shortest_path((unit["x"], unit["y"]), (unit["homeX"], unit["homeY"]), self.obstacles)
                if not route or unit["battery"] < 2:
                    unit["status"] = "SAFE_HOLD"
                    self._event("RETURN_ABORT", unit["id"])
                else:
                    unit["x"], unit["y"] = route[0]
                    unit["battery"] -= 2
                    unit["status"] = "RETURNING"
        self._event("HEARTBEAT", f"tick:{self.tick}")
        return self.snapshot(include_audit=False)

    def run(self, ticks: int = 20) -> dict[str, Any]:
        n = _number(ticks, "ticks", 1, MAX_TICKS)
        for _ in range(n):
            self.step()
        return self.snapshot()

    def verify_audit(self) -> bool:
        prev = "0" * 64
        for sequence, event in enumerate(self.audit, 1):
            data = {k: v for k, v in event.items() if k != "sha256"}
            if event["seq"] != sequence or event["prev"] != prev:
                return False
            current = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if event["sha256"] != current:
                return False
            prev = current
        return prev == self._digest

    def snapshot(self, include_audit: bool = True) -> dict[str, Any]:
        state = {
            "schema": "gpt-doug.guardian.sim.v1", "scenarioId": self.scenario_id,
            "ownerAttribution": OWNER, "mode": MODE, "syntheticOnly": True,
            "grid": {"width": WIDTH, "height": HEIGHT, "units": "arbitrary_cells"},
            "tick": self.tick, "estop": self.estop or self._global_stop(),
            "units": deepcopy(self.units), "obstacles": [list(x) for x in sorted(self.obstacles)],
            "incidents": deepcopy(self.incidents),
            "policy": {"weaponCapabilities": False, "targeting": False, "physicalActuation": False,
                       "networkConnections": False, "unboundedReplication": False,
                       "humanApprovalForEscalations": True},
            "headDigest": self._digest, "auditValid": self.verify_audit(),
        }
        if include_audit:
            state["audit"] = deepcopy(self.audit)
        return state
