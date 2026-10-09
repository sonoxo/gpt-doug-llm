"""Offline ZYRA federation templates and fail-closed observation policy.

The registry never performs an API request, discovers a token, or implies
permission to read named companies, markets, neural devices, or defense systems.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

from .store import validate_text


@dataclass(frozen=True)
class Node:
    id: str
    name: str
    sector: str
    scope: str
    status: str = "not-connected"


_NODES = (
    Node("zyra", "ZYRA Federation", "defensive-governance", "local policy and audit", "local-only"),
    Node("meta", "Meta", "social-business", "licensed aggregate metadata"),
    Node("tesla", "Tesla", "mobility-energy", "authorized public industry metrics"),
    Node("x", "X", "social-business", "licensed aggregate metadata"),
    Node("snapchat", "Snapchat", "social-business", "licensed aggregate metadata"),
    Node("linkedin", "LinkedIn", "professional-networks", "licensed aggregate metadata"),
    Node("global-trade", "Global Trade", "trade", "public or licensed aggregate statistics"),
    Node("global-markets", "Global Markets", "markets", "public or licensed delayed statistics"),
    Node("biotech", "Biotech Research", "open-science", "non-personal research aggregates"),
    Node("warfighter-defense-si", "Warfighter Defense SI", "defensive-training",
         "synthetic defensive readiness and systems integration"),
)
_NODE_BY_ID = {node.id: node for node in _NODES}
_TOKEN = re.compile(r"[a-z][a-z0-9_]{0,47}\Z")
_UNIT = re.compile(r"[A-Za-z%/$._0-9-]{1,20}\Z")
_NEURO_RESEARCH_METRICS = frozenset({
    "publications", "study_count", "open_dataset_count", "model_accuracy_pct",
    "simulated_eeg_bandpower", "simulation_latency_ms",
})
_DEFENSE_SIM_METRICS = frozenset({
    "patch_compliance_pct", "training_readiness_pct", "sensor_health_pct",
    "simulation_alerts", "zero_trust_coverage_pct",
})
_DENIED_WORDS = (
    "weapon", "payload", "target", "fire_control", "kill", "kinetic", "strike",
    "classified", "secret", "cui", "person", "patient", "medical_record",
    "neural_stimulation", "thought", "brain_decoding", "raw_biometric", "eeg_raw",
    "identity", "gps_location", "private_key", "api_key",
)


def list_nodes() -> list[dict]:
    """Return a fresh registry snapshot; none of these integrations are connected."""
    return [{"id": n.id, "name": n.name, "sector": n.sector,
             "scope": n.scope, "connected": False, "status": n.status,
             "data_access": "local-only" if n.id == "zyra" else "none"}
            for n in _NODES]


def validate_observation(node: str, metric: str, value: float, unit: str,
                         source: str, *, synthetic: bool = False,
                         classification: str = "PUBLIC") -> dict:
    """Accept only user supplied public aggregates or explicit simulations.

    The caller, not this package, must have rights to any manually imported data.
    No raw medical/neural signals or real defense information is accepted.
    """
    if node not in _NODE_BY_ID:
        raise ValueError("unrecognized federation node")
    if not isinstance(metric, str) or not _TOKEN.fullmatch(metric):
        raise ValueError("metric must be an ASCII snake_case identifier")
    if type(value) not in (float, int) or not math.isfinite(value) or abs(value) > 1e12:
        raise ValueError("observation value must be a finite numeric aggregate")
    if not isinstance(unit, str) or not _UNIT.fullmatch(unit):
        raise ValueError("unit contains invalid characters")
    if type(synthetic) is not bool:
        raise ValueError("synthetic must be a boolean")
    if classification not in ("PUBLIC", "SYNTHETIC"):
        raise ValueError("restricted or personal data classifications are not accepted")
    if classification == "SYNTHETIC" and not synthetic:
        raise ValueError("synthetic classification requires synthetic=True")
    source = validate_text("source", source, 160)
    if any(ord(c) < 32 or ord(c) == 127 for c in source):
        raise ValueError("control characters forbidden in provenance")
    if any(word in metric for word in _DENIED_WORDS):
        raise ValueError("sensitive or operational metrics are forbidden")
    if node == "warfighter-defense-si":
        if not synthetic:
            raise ValueError("warfighter defensive SI accepts synthetic training data only")
        if metric not in _DEFENSE_SIM_METRICS:
            raise ValueError("metric outside defensive synthetic allowlist")
    if node == "biotech":
        if metric not in _NEURO_RESEARCH_METRICS:
            raise ValueError("biotech accepts approved non-personal research aggregates only")
        if metric in {"simulated_eeg_bandpower", "simulation_latency_ms"} and not synthetic:
            raise ValueError("neural simulation metrics require synthetic=True")
    if metric.endswith("_pct") and not (0 <= value <= 100):
        raise ValueError("percent metric outside 0..100")
    return {"node": node, "metric": metric, "value": float(value),
            "unit": unit, "source": source,
            "kind": "synthetic" if synthetic else "local-manual",
            "classification": "SYNTHETIC" if synthetic else "PUBLIC"}
