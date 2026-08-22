#!/usr/bin/env python3
"""ZYRA defensive-control simulator.

This module intentionally has NO hardware, targeting, launch, firing, network,
serial, GPIO, CAN, radio, actuator, or external-control interfaces. It exists
only to exercise operator-control, authorization, emergency-stop, audit, and
fail-closed state-machine behavior in software tests and demos.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any

SAFE = "SAFE"
ARMED_SIM = "ARMED_SIM"
E_STOP = "E_STOP"


@dataclass
class AuditEvent:
    ts: float
    action: str
    state_before: str
    state_after: str
    operator: str
    note: str = ""


@dataclass
class DefensiveControlSimulator:
    state: str = SAFE
    audit: list[AuditEvent] = field(default_factory=list)

    def _record(self, action: str, before: str, operator: str, note: str = "") -> None:
        self.audit.append(AuditEvent(time(), action, before, self.state, operator, note))

    def arm_simulation(self, *, operator: str, primary_ok: bool, secondary_ok: bool) -> dict[str, Any]:
        before = self.state
        if self.state == E_STOP:
            raise PermissionError("simulator is in emergency-stop state")
        if not (primary_ok and secondary_ok):
            self.state = SAFE
            self._record("arm_denied", before, operator, "dual authorization required")
            return {"ok": False, "state": self.state, "reason": "dual authorization required"}
        self.state = ARMED_SIM
        self._record("arm_simulation", before, operator)
        return {"ok": True, "state": self.state}

    def disarm(self, *, operator: str) -> dict[str, Any]:
        before = self.state
        self.state = SAFE
        self._record("disarm", before, operator)
        return {"ok": True, "state": self.state}

    def emergency_stop(self, *, operator: str, note: str = "") -> dict[str, Any]:
        before = self.state
        self.state = E_STOP
        self._record("emergency_stop", before, operator, note)
        return {"ok": True, "state": self.state}

    def reset_estop(self, *, operator: str, primary_ok: bool, secondary_ok: bool) -> dict[str, Any]:
        before = self.state
        if not (primary_ok and secondary_ok):
            self._record("estop_reset_denied", before, operator, "dual authorization required")
            return {"ok": False, "state": self.state, "reason": "dual authorization required"}
        self.state = SAFE
        self._record("estop_reset", before, operator)
        return {"ok": True, "state": self.state}

    def simulated_action(self, *, operator: str, label: str) -> dict[str, Any]:
        """Record an inert simulated action; never performs real-world actuation."""
        before = self.state
        if self.state != ARMED_SIM:
            self._record("simulation_denied", before, operator, "simulator not armed")
            return {"ok": False, "state": self.state, "reason": "simulator not armed"}
        self._record("simulated_action", before, operator, label[:120])
        return {
            "ok": True,
            "state": self.state,
            "simulated": True,
            "external_effect": False,
            "label": label[:120],
        }

    def status(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "simulator_only": True,
            "external_effect": False,
            "hardware_interfaces": [],
            "network_interfaces": [],
            "audit_events": len(self.audit),
        }
