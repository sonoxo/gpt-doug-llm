from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .models import GoDsEyeSnapshot, SubsystemState
from .planetary import planetary_status
from .zyra import zyra_status


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _first_int(*values: Any) -> Optional[int]:
    for value in values:
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
    return None


def _generated_at(payload: Dict[str, Any]) -> Optional[str]:
    for key in ("generatedAt", "generated_at", "reviewedAt", "reviewed_at"):
        value = payload.get(key)
        if value is not None:
            return str(value)
    return None


def _source_count(name: str, payload: Dict[str, Any]) -> Optional[int]:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    benchmark = payload.get("benchmark") if isinstance(payload.get("benchmark"), dict) else {}
    coverage = payload.get("coverage") if isinstance(payload.get("coverage"), dict) else {}
    sources = payload.get("sources") if isinstance(payload.get("sources"), list) else None
    return _first_int(
        payload.get("sourceCount"),
        summary.get("sourceCount"),
        benchmark.get("sourceCount"),
        coverage.get("regimeCount"),
        len(sources) if sources is not None else None,
    )


def _online_status(name: str, payload: Dict[str, Any]) -> str:
    explicit = str(payload.get("status") or "").upper()
    if explicit in {"ONLINE", "DEGRADED", "OFFLINE"}:
        return explicit

    if name == "brain":
        readiness = payload.get("readiness") if isinstance(payload.get("readiness"), dict) else {}
        return "ONLINE" if readiness.get("core_ready") is True else "DEGRADED"

    if name == "global_intel":
        summary = payload.get("benchmark") if isinstance(payload.get("benchmark"), dict) else {}
    elif name == "biofusion":
        summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    else:
        return "ONLINE"

    total = _first_int(summary.get("sourceCount"))
    online = _first_int(summary.get("onlineSources"))
    if total is None or online is None:
        return "DEGRADED"
    if total > 0 and online == 0:
        return "OFFLINE"
    if online < total:
        return "DEGRADED"
    return "ONLINE"


def _errors(payload: Dict[str, Any]) -> List[str]:
    value = payload.get("errors")
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    if value:
        return [str(value)]
    if payload.get("error"):
        return [str(payload["error"])]
    return []


def _provenance(payload: Dict[str, Any]) -> List[str]:
    items: List[str] = []
    direct = payload.get("provenance")
    if isinstance(direct, list):
        for item in direct:
            if item is not None and str(item) not in items:
                items.append(str(item))
    elif direct:
        items.append(str(direct))
    for source in payload.get("sources", []) or []:
        if isinstance(source, dict):
            source_id = source.get("id") or source.get("sourceId") or source.get("name")
            locator = source.get("url") or source.get("provenance") or source.get("authority")
            if source_id and locator:
                items.append(f"{source_id}:{locator}")
            elif source_id:
                items.append(str(source_id))
        elif source:
            items.append(str(source))
    return items


def _state_from_payload(name: str, payload: Dict[str, Any]) -> SubsystemState:
    status = _online_status(name, payload)
    errors = _errors(payload)
    partial = bool(payload.get("partial")) or status != "ONLINE" or bool(errors)
    return SubsystemState(
        name=name,
        status=status,
        generated_at=_generated_at(payload),
        source_count=_source_count(name, payload),
        stale=bool(payload.get("stale", False)),
        partial=partial,
        provenance=_provenance(payload),
        errors=errors,
        payload=payload,
    )


def _safe_collect(name: str, callback: Callable[[], Any]) -> SubsystemState:
    try:
        payload = callback()
        if not isinstance(payload, dict):
            raise ValueError(f"{name} adapter returned non-dict payload")
        return _state_from_payload(name, payload)
    except (TimeoutError, OSError, RuntimeError, ValueError, TypeError) as exc:
        return SubsystemState(
            name=name,
            status="DEGRADED",
            partial=True,
            errors=[f"{type(exc).__name__}: {exc}"],
            payload={},
        )


def _load_defaults():
    from agency_cloud.bioinformatics import bioinformatics_fusion
    from agency_cloud.config import load_settings
    from agency_cloud.global_compliance import global_posture
    from agency_cloud.global_intel import global_intel_benchmark
    from gpt_brain.status import build_status
    from warhawk import WarHawkSwarm

    return {
        "settings": load_settings(),
        "brain_status_fn": build_status,
        "warhawk_factory": WarHawkSwarm,
        "intel_fn": global_intel_benchmark,
        "compliance_fn": global_posture,
        "bio_fn": bioinformatics_fusion,
    }


def collect_snapshot(
    *,
    settings=None,
    brain_status_fn=None,
    warhawk_factory=None,
    intel_fn=None,
    compliance_fn=None,
    bio_fn=None,
    planetary_fn=planetary_status,
    zyra_fn=zyra_status,
) -> GoDsEyeSnapshot:
    if any(item is None for item in (brain_status_fn, warhawk_factory, intel_fn, compliance_fn, bio_fn)):
        defaults = _load_defaults()
        if settings is None:
            settings = defaults["settings"]
        brain_status_fn = brain_status_fn or defaults["brain_status_fn"]
        warhawk_factory = warhawk_factory or defaults["warhawk_factory"]
        intel_fn = intel_fn or defaults["intel_fn"]
        compliance_fn = compliance_fn or defaults["compliance_fn"]
        bio_fn = bio_fn or defaults["bio_fn"]

    states = {
        "brain": _safe_collect("brain", lambda: brain_status_fn()),
        "warhawk": _safe_collect("warhawk", lambda: warhawk_factory().status()),
        "global_intel": _safe_collect("global_intel", lambda: intel_fn(force=False)),
        "global_compliance": _safe_collect("global_compliance", lambda: compliance_fn(settings)),
        "biofusion": _safe_collect("biofusion", lambda: bio_fn(force=False)),
        "zyra": _safe_collect("zyra", lambda: zyra_fn()),
        "planetary": _safe_collect("planetary", lambda: planetary_fn()),
    }

    provenance: List[str] = []
    uncertainty: List[str] = []
    for name, state in states.items():
        for item in state.provenance:
            if item not in provenance:
                provenance.append(item)
        if state.status != "ONLINE" or state.partial:
            detail = state.errors[0] if state.errors else state.status
            uncertainty.append(f"{name}: {detail}")

    return GoDsEyeSnapshot(
        schema="gpt-doug.godseye-snapshot.v1",
        generated_at=_utc_now(),
        policy={
            "mode": "READ_ONLY_FUSION",
            "humanAuthorizationRequired": True,
            "automaticExternalAction": False,
            "realWorldControl": False,
        },
        subsystems=states,
        provenance=provenance,
        uncertainty=uncertainty,
    )


def snapshot_sources(snapshot: GoDsEyeSnapshot) -> List[Dict[str, Any]]:
    flattened: List[Dict[str, Any]] = []
    for subsystem, state in snapshot.subsystems.items():
        for source in state.payload.get("sources", []) or []:
            if isinstance(source, dict):
                flattened.append({"subsystem": subsystem, **source})
            else:
                flattened.append({"subsystem": subsystem, "id": str(source)})
    return flattened
