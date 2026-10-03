from __future__ import annotations

import asyncio
import dataclasses
import importlib
import os
import time
from collections.abc import AsyncIterable
from typing import Any, Protocol


@dataclasses.dataclass(frozen=True)
class Vec3:
    x: float
    y: float
    z: float


@dataclasses.dataclass(frozen=True)
class ThreatEvent:
    event_id: str
    threat_kind: str
    source_asset: str
    target_asset: str
    source_position: Vec3
    target_position: Vec3
    cvss: float
    anomaly_confidence: float
    bytes_per_second: int
    observed_at_unix_ms: int
    gotham_target_rid: str = ""
    ontology_entity_rid: str = ""
    geotime_track_rid: str = ""
    source_indicator: str = ""
    session_id: str = ""


@dataclasses.dataclass(frozen=True)
class HapticProjection:
    event_id: str
    focal_point: Vec3
    pattern: str
    modulation_hz: float
    normalized_amplitude: float
    duty_cycle: float
    severity: float
    confidence: float


@dataclasses.dataclass(frozen=True)
class LinkHealth:
    connected: bool
    jitter_ms: float
    token_valid: bool = True


@dataclasses.dataclass(frozen=True)
class OperatorContext:
    operator_id: str
    mtls_verified: bool
    hardware_token_verified: bool
    pq_channel_verified: bool
    rbac_allowed: bool
    deliberate_confirmation: bool


@dataclasses.dataclass(frozen=True)
class OperatorGesture:
    gesture_id: str
    gesture: str
    threat_event_id: str
    target_asset: str


@dataclasses.dataclass(frozen=True)
class ActionReceipt:
    accepted: bool
    action: str
    reason: str
    external_audit_id: str = ""


class HapticSink(Protocol):
    def apply(self, projection: HapticProjection) -> bool: ...
    def disarm(self) -> None: ...


class DefenseOntologyPort(Protocol):
    def upsert_threat(self, event: ThreatEvent, projection: HapticProjection) -> str: ...
    def record_operator_action(
        self,
        *,
        gesture: OperatorGesture,
        operator: OperatorContext,
        action: str,
        accepted: bool,
        reason: str,
    ) -> str: ...
    def apply_mitigation(self, action: str, parameters: dict[str, Any]) -> str: ...


class GothamPort(Protocol):
    def validate_target_binding(self, target_rid: str) -> bool: ...
    def add_ontology_object_to_gaia(self, object_rid: str, *, label: str) -> str: ...


class AuditPort(Protocol):
    def append(self, event: dict[str, Any]) -> str: ...


@dataclasses.dataclass(frozen=True)
class SafetyProfile:
    max_modulation_hz: float = 250.0
    max_normalized_amplitude: float = 0.65
    max_duty_cycle: float = 0.40
    max_jitter_ms: float = 15.0
    edge_deadline_ms: float = 5.0


class EdgeMapper:
    """Deterministic threat-to-haptic mapping for the edge hot path."""

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, value))

    @staticmethod
    def _pattern(kind: str) -> str:
        return {
            "ddos_volumetric": "expanding_ring",
            "privilege_escalation": "rising_column",
            "port_sweep": "directional_sweep",
            "malware_execution": "sharp_pulse",
        }.get(kind, "neutral_pulse")

    def map(self, event: ThreatEvent, safety: SafetyProfile) -> HapticProjection:
        cvss = self._clamp01(event.cvss / 10.0)
        confidence = self._clamp01(event.anomaly_confidence)
        traffic = 0.0
        if event.threat_kind == "ddos_volumetric":
            traffic = self._clamp01(event.bytes_per_second / float(1024**3))
        severity = self._clamp01(0.50 * cvss + 0.40 * confidence + 0.10 * traffic)

        return HapticProjection(
            event_id=event.event_id,
            focal_point=event.target_position,
            pattern=self._pattern(event.threat_kind),
            modulation_hz=min(safety.max_modulation_hz, 8.0 + 112.0 * severity),
            normalized_amplitude=min(safety.max_normalized_amplitude, 0.10 + 0.80 * severity),
            duty_cycle=min(safety.max_duty_cycle, 0.10 + 0.35 * severity),
            severity=severity,
            confidence=confidence,
        )


class CyberTactileEdge:
    """Edge runtime. Palantir network calls are never placed on the <5 ms actuation path."""

    def __init__(self, sink: HapticSink, safety: SafetyProfile = SafetyProfile()):
        self._sink = sink
        self._safety = safety
        self._mapper = EdgeMapper()
        self._latched_disarmed = False

    @property
    def disarmed(self) -> bool:
        return self._latched_disarmed

    def reset(self) -> None:
        self._latched_disarmed = False

    def process(self, event: ThreatEvent, health: LinkHealth) -> HapticProjection | None:
        start_ns = time.perf_counter_ns()
        if (
            self._latched_disarmed
            or not health.connected
            or not health.token_valid
            or health.jitter_ms > self._safety.max_jitter_ms
        ):
            self._latched_disarmed = True
            self._sink.disarm()
            return None

        projection = self._mapper.map(event, self._safety)
        applied = self._sink.apply(projection)
        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
        if not applied or elapsed_ms > self._safety.edge_deadline_ms:
            self._latched_disarmed = True
            self._sink.disarm()
            return None
        return projection


class DefenseActionPolicy:
    """Allowlisted defensive cyber mitigations only."""

    @staticmethod
    def action_for(gesture: str, event: ThreatEvent, projection: HapticProjection) -> str:
        if gesture == "pinch":
            return "RevokeSession" if event.threat_kind == "privilege_escalation" else "OpenIncident"
        if gesture == "squeeze":
            return "IsolateHost" if projection.severity >= 0.80 else "OpenIncident"
        if gesture == "press":
            if event.threat_kind in {"ddos_volumetric", "port_sweep"}:
                return "BlockIPRange"
            if event.threat_kind == "malware_execution":
                return "TerminateProcess"
        return "OpenIncident"

    @staticmethod
    def parameters_for(action: str, event: ThreatEvent, operator: OperatorContext) -> dict[str, Any]:
        base = {
            "threatEventId": event.event_id,
            "targetAsset": event.target_asset,
            "operatorId": operator.operator_id,
            "gothamTargetRid": event.gotham_target_rid or None,
            "ontologyEntityRid": event.ontology_entity_rid or None,
        }
        if action == "RevokeSession":
            base["sessionId"] = event.session_id
        elif action == "BlockIPRange":
            base["indicator"] = event.source_indicator
        return {key: value for key, value in base.items() if value not in (None, "")}


class DefenseController:
    def __init__(self, ontology: DefenseOntologyPort, audit: AuditPort):
        self._ontology = ontology
        self._audit = audit

    @staticmethod
    def _authorized(operator: OperatorContext) -> bool:
        return (
            operator.deliberate_confirmation
            and operator.mtls_verified
            and operator.hardware_token_verified
            and operator.pq_channel_verified
            and operator.rbac_allowed
            and bool(operator.operator_id)
        )

    def handle(
        self,
        *,
        gesture: OperatorGesture,
        operator: OperatorContext,
        event: ThreatEvent,
        projection: HapticProjection,
    ) -> ActionReceipt:
        if gesture.threat_event_id != event.event_id or gesture.target_asset != event.target_asset:
            reason = "gesture not bound to active threat"
            self._ontology.record_operator_action(
                gesture=gesture, operator=operator, action="None", accepted=False, reason=reason
            )
            return ActionReceipt(False, "None", reason)
        if not self._authorized(operator):
            reason = "zero-trust authorization failed"
            self._ontology.record_operator_action(
                gesture=gesture, operator=operator, action="None", accepted=False, reason=reason
            )
            return ActionReceipt(False, "None", reason)

        action = DefenseActionPolicy.action_for(gesture.gesture, event, projection)
        params = DefenseActionPolicy.parameters_for(action, event, operator)
        if action == "RevokeSession" and not event.session_id:
            reason = "session id required for RevokeSession"
            self._ontology.record_operator_action(
                gesture=gesture, operator=operator, action=action, accepted=False, reason=reason
            )
            return ActionReceipt(False, action, reason)
        if action == "BlockIPRange" and not event.source_indicator:
            reason = "source indicator required for BlockIPRange"
            self._ontology.record_operator_action(
                gesture=gesture, operator=operator, action=action, accepted=False, reason=reason
            )
            return ActionReceipt(False, action, reason)

        external_id = self._ontology.apply_mitigation(action, params)
        audit_id = self._audit.append(
            {
                "event": "haptic_defense_action",
                "action": action,
                "operator_id": operator.operator_id,
                "threat_event_id": event.event_id,
                "target_asset": event.target_asset,
                "external_action_id": external_id,
            }
        )
        self._ontology.record_operator_action(
            gesture=gesture, operator=operator, action=action, accepted=True, reason="accepted"
        )
        return ActionReceipt(True, action, "accepted", external_audit_id=audit_id or external_id)


class PalantirMirror:
    """Asynchronous control-plane mirroring that cannot block the edge HAL path."""

    def __init__(self, ontology: DefenseOntologyPort, gotham: GothamPort | None = None):
        self._ontology = ontology
        self._gotham = gotham

    async def mirror(self, event: ThreatEvent, projection: HapticProjection) -> str:
        if self._gotham and event.gotham_target_rid:
            valid = await asyncio.to_thread(self._gotham.validate_target_binding, event.gotham_target_rid)
            if not valid:
                raise RuntimeError("Gotham target binding failed validation")

        object_rid = await asyncio.to_thread(self._ontology.upsert_threat, event, projection)
        if self._gotham and object_rid:
            await asyncio.to_thread(
                self._gotham.add_ontology_object_to_gaia,
                object_rid,
                label="Cyber Threat Tactile Projection",
            )
        return object_rid


class EdgeStreamService:
    def __init__(self, edge: CyberTactileEdge, mirror: PalantirMirror):
        self._edge = edge
        self._mirror = mirror

    async def run(self, events: AsyncIterable[tuple[ThreatEvent, LinkHealth]]) -> None:
        pending: set[asyncio.Task[Any]] = set()
        async for event, health in events:
            projection = self._edge.process(event, health)
            if projection is None:
                continue
            task = asyncio.create_task(self._mirror.mirror(event, projection))
            pending.add(task)
            task.add_done_callback(pending.discard)
        if pending:
            await asyncio.gather(*pending)


@dataclasses.dataclass(frozen=True)
class PalantirConfig:
    foundry_url: str
    client_id: str
    client_secret: str
    defense_osdk_package: str
    gaia_map_rid: str = ""
    gotham_preview: bool = False
    gotham_scopes: tuple[str, ...] = ()

    @classmethod
    def from_env(cls) -> "PalantirConfig":
        scopes = tuple(filter(None, os.getenv("GOTHAM_OAUTH_SCOPES", "").split()))
        return cls(
            foundry_url=os.environ["FOUNDRY_URL"],
            client_id=os.environ["CLIENT_ID"],
            client_secret=os.environ["CLIENT_SECRET"],
            defense_osdk_package=os.environ["DEFENSE_OSDK_PACKAGE"],
            gaia_map_rid=os.getenv("GOTHAM_GAIA_MAP_RID", ""),
            gotham_preview=os.getenv("GOTHAM_PREVIEW", "false").lower() == "true",
            gotham_scopes=scopes,
        )


class GeneratedDefenseOsdkAdapter:
    """Adapter for the enrollment-generated Defense OSDK Python package."""

    ACTION_FUNCTIONS = {
        "UpsertCyberThreatVector": "upsert_cyber_threat_vector",
        "RecordDefenseOperatorAction": "record_defense_operator_action",
        "IsolateHost": "isolate_host",
        "RevokeSession": "revoke_session",
        "BlockIPRange": "block_ip_range",
        "TerminateProcess": "terminate_process",
        "OpenIncident": "open_incident",
    }

    def __init__(self, config: PalantirConfig, *, client: Any | None = None):
        self._config = config
        if client is not None:
            self._client = client
            self._action_config = None
            return

        sdk = importlib.import_module(config.defense_osdk_package)
        auth = sdk.ConfidentialClientAuth(
            client_id=config.client_id,
            client_secret=config.client_secret,
            hostname=config.foundry_url,
            should_refresh=True,
            scopes=["api:ontologies-read", "api:ontologies-write"],
        )
        self._client = sdk.FoundryClient(auth=auth, hostname=config.foundry_url)
        try:
            runtime_types = importlib.import_module("foundry_sdk_runtime.types")
            self._action_config = runtime_types.ActionConfig(
                mode=runtime_types.ActionMode.VALIDATE_AND_EXECUTE,
                return_edits=runtime_types.ReturnEditsMode.ALL,
            )
        except (ImportError, AttributeError):
            self._action_config = None

    def _invoke(self, canonical_action: str, **parameters: Any) -> Any:
        function_name = self.ACTION_FUNCTIONS[canonical_action]
        fn = getattr(self._client.ontology.actions, function_name)
        kwargs = dict(parameters)
        if self._action_config is not None:
            kwargs["action_config"] = self._action_config
        response = fn(**kwargs)
        validation = getattr(response, "validation", None)
        result = getattr(validation, "result", "VALID") if validation is not None else "VALID"
        if str(result).upper() != "VALID":
            raise RuntimeError(f"Defense OSDK action {canonical_action} rejected: {result}")
        return response

    @staticmethod
    def _response_id(response: Any, fallback: str) -> str:
        edits = getattr(response, "edits", None)
        for attr in ("object_rid", "rid", "primary_key"):
            value = getattr(edits, attr, None) if edits is not None else None
            if value:
                return str(value)
        return fallback

    def upsert_threat(self, event: ThreatEvent, projection: HapticProjection) -> str:
        response = self._invoke(
            "UpsertCyberThreatVector",
            event_id=event.event_id,
            threat_kind=event.threat_kind,
            source_asset=event.source_asset,
            target_asset=event.target_asset,
            x=projection.focal_point.x,
            y=projection.focal_point.y,
            z=projection.focal_point.z,
            severity=projection.severity,
            anomaly_confidence=projection.confidence,
            cvss=event.cvss,
            bytes_per_second=event.bytes_per_second,
            modulation_hz=projection.modulation_hz,
            normalized_amplitude=projection.normalized_amplitude,
            duty_cycle=projection.duty_cycle,
            observed_at_unix_ms=event.observed_at_unix_ms,
            gotham_target_rid=event.gotham_target_rid or None,
            geotime_track_rid=event.geotime_track_rid or None,
        )
        return self._response_id(response, event.ontology_entity_rid or event.event_id)

    def record_operator_action(
        self,
        *,
        gesture: OperatorGesture,
        operator: OperatorContext,
        action: str,
        accepted: bool,
        reason: str,
    ) -> str:
        response = self._invoke(
            "RecordDefenseOperatorAction",
            gesture_id=gesture.gesture_id,
            gesture=gesture.gesture,
            threat_event_id=gesture.threat_event_id,
            target_asset=gesture.target_asset,
            operator_id=operator.operator_id,
            requested_action=action,
            accepted=accepted,
            decision_reason=reason,
        )
        return self._response_id(response, gesture.gesture_id)

    def apply_mitigation(self, action: str, parameters: dict[str, Any]) -> str:
        response = self._invoke(action, **parameters)
        return self._response_id(response, f"{action}:{parameters.get('threatEventId', '')}")


class GothamPlatformAdapter:
    """Official gotham-platform-python adapter for Target Workbench and Gaia."""

    def __init__(self, config: PalantirConfig, *, client: Any | None = None):
        self._config = config
        if client is not None:
            self._client = client
            return
        gotham = importlib.import_module("gotham")
        auth = gotham.ConfidentialClientAuth(
            client_id=config.client_id,
            client_secret=config.client_secret,
            scopes=list(config.gotham_scopes),
        )
        self._client = gotham.GothamClient(auth=auth, hostname=config.foundry_url)

    def validate_target_binding(self, target_rid: str) -> bool:
        if not target_rid:
            return True
        target = self._client.target_workbench.Targets.get(
            target_rid,
            preview=self._config.gotham_preview or None,
        )
        return target is not None

    def add_ontology_object_to_gaia(self, object_rid: str, *, label: str) -> str:
        if not self._config.gaia_map_rid or not object_rid:
            return ""
        response = self._client.gaia.Map.add_objects(
            self._config.gaia_map_rid,
            label=label,
            object_rids=[object_rid],
            preview=self._config.gotham_preview or None,
        )
        layer_ids = getattr(response, "data_layer_ids", None) or getattr(response, "dataLayerIds", None) or []
        return str(layer_ids[0]) if layer_ids else ""
