#!/usr/bin/env python3
"""Telemetry-only global nuclear-energy aggregation for XUNIA / ZYRA.

This module intentionally accepts only aggregated public/synthetic health signals.
It does not implement plant control, setpoints, shutdown/startup logic, targeting,
or credentialed access to protected nuclear infrastructure.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

FORBIDDEN_KEYS = {
    "actuate",
    "command",
    "control",
    "credential",
    "credentials",
    "password",
    "secret",
    "token",
    "setpoint",
    "shutdown",
    "startup",
    "scram",
    "trip",
    "valve",
    "pump",
    "rod_position",
    "control_rod",
    "target",
    "targeting",
    "weapon",
    "override",
    "bypass",
}

ALLOWED_PROVENANCE = {"public", "synthetic"}


class PipelineError(ValueError):
    pass


def _walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, nested in value.items():
            yield str(key).lower()
            yield from _walk_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_keys(nested)


def reject_operational_fields(payload: dict[str, Any]) -> None:
    bad = sorted({key for key in _walk_keys(payload) if key in FORBIDDEN_KEYS})
    if bad:
        raise PipelineError(
            "Operational/control fields are not accepted by this telemetry-only pipeline: "
            + ", ".join(bad)
        )


def _bounded_number(value: Any, name: str, lo: float = 0.0, hi: float = 100.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PipelineError(f"{name} must be numeric")
    value = float(value)
    if not math.isfinite(value) or value < lo or value > hi:
        raise PipelineError(f"{name} must be between {lo} and {hi}")
    return value


@dataclass(frozen=True)
class NuclearSignal:
    region: str
    provenance: str
    availability_pct: float
    reporting_coverage_pct: float
    generation_pct_of_reference: float
    data_freshness_minutes: float

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "NuclearSignal":
        reject_operational_fields(raw)
        provenance = str(raw.get("provenance", "")).lower()
        if provenance not in ALLOWED_PROVENANCE:
            raise PipelineError("provenance must be public or synthetic")
        region = str(raw.get("region", "")).strip()
        if not region:
            raise PipelineError("region is required")
        freshness = _bounded_number(raw.get("data_freshness_minutes"), "data_freshness_minutes", 0, 1440)
        return cls(
            region=region,
            provenance=provenance,
            availability_pct=_bounded_number(raw.get("availability_pct"), "availability_pct"),
            reporting_coverage_pct=_bounded_number(raw.get("reporting_coverage_pct"), "reporting_coverage_pct"),
            generation_pct_of_reference=_bounded_number(
                raw.get("generation_pct_of_reference"), "generation_pct_of_reference"
            ),
            data_freshness_minutes=freshness,
        )

    def score(self) -> float:
        freshness_score = max(0.0, 100.0 - (self.data_freshness_minutes / 1440.0 * 100.0))
        score = (
            self.availability_pct * 0.40
            + self.reporting_coverage_pct * 0.25
            + self.generation_pct_of_reference * 0.25
            + freshness_score * 0.10
        )
        return round(score, 2)


def state_for(score: float) -> str:
    if score < 25:
        return "LOW"
    if score < 50:
        return "NOMINAL"
    if score < 75:
        return "HIGH"
    return "SURGE"


def aggregate(signals: list[NuclearSignal]) -> dict[str, Any]:
    if not signals:
        raise PipelineError("at least one signal is required")

    component_scores = [signal.score() for signal in signals]
    confidences = [0.80 if signal.provenance == "public" else 0.35 for signal in signals]
    charge = round(sum(component_scores) / len(component_scores), 2)
    confidence = round(sum(confidences) / len(confidences), 3)

    return {
        "schema": "xunia.zyra.nuclr-global-charge.v1",
        "mode": "TELEMETRY_ONLY",
        "source": "NUCLR",
        "charge_component": charge,
        "state": state_for(charge),
        "confidence": confidence,
        "coverage": round(len(signals) / max(1, len(signals)), 3),
        "advisory_only": True,
        "external_actuation": False,
        "regions": [
            {**asdict(signal), "score": signal.score()} for signal in signals
        ],
    }


def run(payload: dict[str, Any]) -> dict[str, Any]:
    reject_operational_fields(payload)
    if payload.get("schema") != "xunia.zyra.nuclr-input.v1":
        raise PipelineError("unsupported input schema")
    raw_signals = payload.get("signals")
    if not isinstance(raw_signals, list) or not raw_signals:
        raise PipelineError("signals must be a non-empty list")
    return aggregate([NuclearSignal.from_dict(item) for item in raw_signals])


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run telemetry-only NUCLR global pipeline")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = run(payload)
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
