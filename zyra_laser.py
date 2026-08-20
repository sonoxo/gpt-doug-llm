#!/usr/bin/env python3
"""ZYRA LASER: bounded local defensive circuit breaker.

LASER never retaliates, scans external systems, or executes attack payloads.
It only isolates ZYRA's own model-processing path after repeated blocked
policy events, and provides a deterministic native self-test.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any


@dataclass(frozen=True)
class LaserDecision:
    action: str
    engaged: bool
    strikes: int
    lock_remaining: int
    reason: str
    fingerprint: str | None = None


class ZyraLaser:
    VERSION = "LASER/1.1"

    def __init__(self, state_path: str | Path | None = None, *, threshold: int = 3, window_seconds: int = 90, lock_seconds: int = 45):
        self.state_path = Path(state_path or Path.home() / ".gpt-doug" / "zyra-laser.json")
        self.threshold = max(1, int(threshold))
        self.window_seconds = max(10, int(window_seconds))
        self.lock_seconds = max(5, int(lock_seconds))
        self.state = self._load()
        self._prune(time.time())

    def _default_state(self) -> dict[str, Any]:
        return {"version": self.VERSION, "strikes": [], "lock_until": 0.0, "incidents": 0, "last_reason": "", "last_fingerprint": ""}

    def _load(self) -> dict[str, Any]:
        try:
            if self.state_path.exists():
                data = json.loads(self.state_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    base = self._default_state(); base.update(data); return base
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
        return self._default_state()

    def _save(self) -> None:
        self.state_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self.state, sort_keys=True), encoding="utf-8")
        self.state_path.chmod(0o600)

    def _prune(self, now: float) -> None:
        floor = now - self.window_seconds
        self.state["strikes"] = [float(ts) for ts in self.state.get("strikes", []) if float(ts) >= floor]
        if float(self.state.get("lock_until", 0.0)) <= now:
            self.state["lock_until"] = 0.0

    def _fingerprint(self, verdict: Any, direction: str) -> str:
        material = json.dumps({"direction": direction, "risk": getattr(verdict, "risk", ""), "reasons": list(getattr(verdict, "reasons", []) or []), "controls": list(getattr(verdict, "control_ids", []) or [])}, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(material).hexdigest()[:16]

    def is_locked(self) -> bool:
        self._prune(time.time())
        return float(self.state.get("lock_until", 0.0)) > time.time()

    def status(self) -> dict[str, Any]:
        now = time.time(); self._prune(now)
        remaining = max(0, int(round(float(self.state.get("lock_until", 0.0)) - now)))
        return {"version": self.VERSION, "armed": True, "locked": remaining > 0, "lock_remaining": remaining, "strikes": len(self.state.get("strikes", [])), "threshold": self.threshold, "window_seconds": self.window_seconds, "incidents": int(self.state.get("incidents", 0)), "last_reason": self.state.get("last_reason", ""), "last_fingerprint": self.state.get("last_fingerprint", "")}

    def observe(self, verdict: Any, direction: str) -> LaserDecision:
        now = time.time(); self._prune(now)
        if getattr(verdict, "allowed", True):
            self._save(); s = self.status()
            return LaserDecision("ALLOW", s["locked"], s["strikes"], s["lock_remaining"], "no critical policy violation")
        fp = self._fingerprint(verdict, direction)
        reason = "; ".join(list(getattr(verdict, "reasons", []) or [])) or "policy block"
        weight = self.threshold if direction == "output" else 1
        self.state["strikes"].extend([now] * weight)
        self.state["incidents"] = int(self.state.get("incidents", 0)) + 1
        self.state["last_reason"] = reason; self.state["last_fingerprint"] = fp
        engaged = len(self.state["strikes"]) >= self.threshold
        if engaged:
            self.state["lock_until"] = max(float(self.state.get("lock_until", 0.0)), now + self.lock_seconds)
        self._save(); s = self.status()
        return LaserDecision("ISOLATE" if engaged else "INTERCEPT", s["locked"], s["strikes"], s["lock_remaining"], reason, fp)

    def reset(self) -> dict[str, Any]:
        self.state["strikes"] = []; self.state["lock_until"] = 0.0; self.state["last_reason"] = ""; self.state["last_fingerprint"] = ""
        self._save(); return self.status()


def run_native_laser_test() -> dict[str, Any]:
    """Deterministic local self-test. No model call, network call, or payload execution."""
    blocked = SimpleNamespace(allowed=False, risk="critical", reasons=["native laser self-test"], control_ids=["ZYRA-TEST-001"])
    with tempfile.TemporaryDirectory(prefix="zyra-laser-test-") as tmp:
        laser = ZyraLaser(Path(tmp) / "laser.json", threshold=3, window_seconds=90, lock_seconds=5)
        d1 = laser.observe(blocked, "input")
        d2 = laser.observe(blocked, "input")
        d3 = laser.observe(blocked, "input")
        locked = laser.status()
        reset = laser.reset()
    checks = {
        "first_intercept": d1.action == "INTERCEPT" and not d1.engaged,
        "second_intercept": d2.action == "INTERCEPT" and not d2.engaged,
        "third_isolates": d3.action == "ISOLATE" and d3.engaged,
        "lock_engaged": bool(locked["locked"]),
        "reset_unlocks": not bool(reset["locked"]) and reset["strikes"] == 0,
    }
    return {"passed": all(checks.values()), "checks": checks, "payload_execution": False, "external_targeting": False}


if __name__ == "__main__":
    report = run_native_laser_test()
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if report["passed"] else 1)
