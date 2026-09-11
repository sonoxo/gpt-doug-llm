"""Governed Flipper Zero ontology runtime for GPT-DOUG-LLM / XUNIA / ZYRA.

This module models a Flipper Zero as an authorized edge-security sensor and
lab interface. It intentionally does not implement radio/NFC/RFID transmission,
credential emulation, bypasses, or control of third-party systems. Consequential
physical actions are represented only as staged ontology requests.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from typing import Any, Dict, List, Optional
from uuid import uuid4


class AuthorizationState(str, Enum):
    NOT_AUTHORIZED = "NOT_AUTHORIZED"
    OWNER_AUTHORIZED = "OWNER_AUTHORIZED"
    LAB_AUTHORIZED = "LAB_AUTHORIZED"
    EXPLICIT_SCOPE_AUTHORIZED = "EXPLICIT_SCOPE_AUTHORIZED"


class AssetAuthorization(str, Enum):
    OWNED = "OWNED"
    AUTHORIZED = "AUTHORIZED"
    LAB_ONLY = "LAB_ONLY"
    READ_ONLY = "READ_ONLY"
    DENIED = "DENIED"
    UNKNOWN = "UNKNOWN"


class SessionStatus(str, Enum):
    PLANNED = "PLANNED"
    AUTHORIZED = "AUTHORIZED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
    BLOCKED = "BLOCKED"


class ActionType(str, Enum):
    OBSERVE_SIGNAL = "OBSERVE_SIGNAL"
    PARSE_SIGNAL = "PARSE_SIGNAL"
    CREATE_DIGITAL_TWIN = "CREATE_DIGITAL_TWIN"
    RUN_SIMULATION = "RUN_SIMULATION"
    EXECUTE_AUTHORIZED_TEST = "EXECUTE_AUTHORIZED_TEST"
    ABORT_SESSION = "ABORT_SESSION"


PROTECTED_ASSET_CLASSES = {
    "EMERGENCY_COMMUNICATIONS",
    "PUBLIC_INFRASTRUCTURE",
    "TRAFFIC_CONTROL",
    "UTILITY_INFRASTRUCTURE",
    "MEDICAL_SYSTEM",
    "THIRD_PARTY_ACCESS_SYSTEM",
}

ACTIVE_PHYSICAL_ACTIONS = {ActionType.EXECUTE_AUTHORIZED_TEST}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


@dataclass
class FlipperDevice:
    device_id: str
    name: str = "Flipper Zero"
    model: str = "FlipperZero"
    firmware: str = "unknown"
    owner_id: str = ""
    environment: str = "LAB"
    connection_state: str = "DISCONNECTED"
    battery_percent: Optional[int] = None
    trust_level: str = "UNVERIFIED"
    authorization_state: AuthorizationState = AuthorizationState.NOT_AUTHORIZED
    last_seen: Optional[str] = None


@dataclass
class Asset:
    asset_id: str
    name: str
    owner_id: str
    asset_type: str = "LAB_DEVICE"
    authorization_status: AssetAuthorization = AssetAuthorization.UNKNOWN
    sensitivity: str = "NORMAL"
    protected_class: Optional[str] = None


@dataclass
class Authorization:
    authorization_id: str
    actor_id: str
    device_id: str
    asset_id: str
    scope: List[str]
    granted_at: str
    expires_at: Optional[str] = None
    granted_by: str = "owner"
    environment: str = "LAB"
    evidence_reference: str = ""


@dataclass
class TestSession:
    session_id: str
    device_id: str
    operator_id: str
    asset_id: str
    environment: str
    purpose: str
    authorization_id: str
    status: SessionStatus = SessionStatus.AUTHORIZED
    started_at: Optional[str] = None
    ended_at: Optional[str] = None


@dataclass
class Observation:
    observation_id: str
    session_id: str
    timestamp: str
    module: str
    protocol: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    signal_hash: str = ""
    confidence: float = 1.0


@dataclass
class DigitalTwin:
    twin_id: str
    asset_id: str
    protocol: str
    simulated_state: Dict[str, Any]
    created_at: str
    source_observations: List[str]
    confidence: float = 1.0


class FlipperOntology:
    """In-memory ontology facade with deny-by-default governance.

    The class is transport-neutral: hardware I/O belongs in a separately reviewed
    adapter. This layer validates scope and records ontology/audit state only.
    """

    def __init__(self) -> None:
        self.devices: Dict[str, FlipperDevice] = {}
        self.assets: Dict[str, Asset] = {}
        self.authorizations: Dict[str, Authorization] = {}
        self.sessions: Dict[str, TestSession] = {}
        self.observations: Dict[str, Observation] = {}
        self.digital_twins: Dict[str, DigitalTwin] = {}
        self.audit_events: List[Dict[str, Any]] = []

    def _event(self, event_type: str, **payload: Any) -> Dict[str, Any]:
        event = {
            "event_id": _id("evt"),
            "event": event_type,
            "timestamp": _now(),
            **payload,
        }
        self.audit_events.append(event)
        return event

    def register_device(
        self,
        device_id: str,
        owner_id: str,
        *,
        firmware: str = "unknown",
        environment: str = "LAB",
        authorization_state: AuthorizationState = AuthorizationState.OWNER_AUTHORIZED,
    ) -> Dict[str, Any]:
        device = FlipperDevice(
            device_id=device_id,
            owner_id=owner_id,
            firmware=firmware,
            environment=environment,
            authorization_state=authorization_state,
            trust_level="TRUSTED" if authorization_state != AuthorizationState.NOT_AUTHORIZED else "UNVERIFIED",
            last_seen=_now(),
        )
        self.devices[device_id] = device
        self._event("FLIPPER_REGISTERED", device_id=device_id, owner_id=owner_id)
        return asdict(device)

    def register_asset(
        self,
        asset_id: str,
        name: str,
        owner_id: str,
        *,
        asset_type: str = "LAB_DEVICE",
        authorization_status: AssetAuthorization = AssetAuthorization.UNKNOWN,
        protected_class: Optional[str] = None,
    ) -> Dict[str, Any]:
        asset = Asset(
            asset_id=asset_id,
            name=name,
            owner_id=owner_id,
            asset_type=asset_type,
            authorization_status=authorization_status,
            protected_class=protected_class,
        )
        self.assets[asset_id] = asset
        self._event("ASSET_REGISTERED", asset_id=asset_id, authorization_status=authorization_status.value)
        return asdict(asset)

    def grant_authorization(
        self,
        actor_id: str,
        device_id: str,
        asset_id: str,
        scope: List[str],
        *,
        granted_by: str = "owner",
        environment: str = "LAB",
        evidence_reference: str = "",
        expires_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        if device_id not in self.devices:
            raise ValueError("unknown Flipper device")
        if asset_id not in self.assets:
            raise ValueError("unknown asset")
        authorization = Authorization(
            authorization_id=_id("auth"),
            actor_id=actor_id,
            device_id=device_id,
            asset_id=asset_id,
            scope=list(scope),
            granted_at=_now(),
            expires_at=expires_at,
            granted_by=granted_by,
            environment=environment,
            evidence_reference=evidence_reference,
        )
        self.authorizations[authorization.authorization_id] = authorization
        self._event(
            "AUTHORIZATION_GRANTED",
            authorization_id=authorization.authorization_id,
            actor_id=actor_id,
            device_id=device_id,
            asset_id=asset_id,
        )
        return asdict(authorization)

    def _authorization_is_valid(self, authorization: Authorization, requested_scope: str) -> bool:
        if requested_scope not in authorization.scope:
            return False
        if authorization.expires_at:
            try:
                expiry = datetime.fromisoformat(authorization.expires_at.replace("Z", "+00:00"))
            except ValueError:
                return False
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry <= datetime.now(timezone.utc):
                return False
        return True

    def start_session(
        self,
        operator_id: str,
        device_id: str,
        asset_id: str,
        authorization_id: str,
        purpose: str,
    ) -> Dict[str, Any]:
        device = self.devices.get(device_id)
        asset = self.assets.get(asset_id)
        authorization = self.authorizations.get(authorization_id)
        if not device or not asset or not authorization:
            raise PermissionError("device, asset, and authorization must all exist")
        if authorization.actor_id != operator_id or authorization.device_id != device_id or authorization.asset_id != asset_id:
            raise PermissionError("authorization does not match requested session")
        if asset.authorization_status in {AssetAuthorization.UNKNOWN, AssetAuthorization.DENIED}:
            raise PermissionError("asset is not authorized")
        if asset.protected_class in PROTECTED_ASSET_CLASSES:
            raise PermissionError("protected real-world asset class is blocked")
        if device.authorization_state == AuthorizationState.NOT_AUTHORIZED:
            raise PermissionError("Flipper device is not authorized")
        if not self._authorization_is_valid(authorization, "SESSION"):
            raise PermissionError("authorization does not permit a session")

        session = TestSession(
            session_id=_id("session"),
            device_id=device_id,
            operator_id=operator_id,
            asset_id=asset_id,
            environment=authorization.environment,
            purpose=purpose,
            authorization_id=authorization_id,
            status=SessionStatus.ACTIVE,
            started_at=_now(),
        )
        self.sessions[session.session_id] = session
        self._event("SESSION_STARTED", session_id=session.session_id, asset_id=asset_id)
        return asdict(session)

    def observe_signal(
        self,
        session_id: str,
        module: str,
        protocol: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        session = self.sessions.get(session_id)
        if not session or session.status != SessionStatus.ACTIVE:
            raise PermissionError("an active authorized session is required")
        authorization = self.authorizations[session.authorization_id]
        if not self._authorization_is_valid(authorization, ActionType.OBSERVE_SIGNAL.value):
            raise PermissionError("authorization does not permit observation")
        payload = metadata or {}
        digest = sha256(repr(sorted(payload.items())).encode("utf-8")).hexdigest()
        observation = Observation(
            observation_id=_id("obs"),
            session_id=session_id,
            timestamp=_now(),
            module=module.upper(),
            protocol=protocol,
            metadata=payload,
            signal_hash=digest,
        )
        self.observations[observation.observation_id] = observation
        self._event(
            "SIGNAL_OBSERVED",
            session_id=session_id,
            observation_id=observation.observation_id,
            module=observation.module,
            protocol=protocol,
        )
        return asdict(observation)

    def create_digital_twin(
        self,
        session_id: str,
        protocol: str,
        simulated_state: Dict[str, Any],
        source_observations: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        session = self.sessions.get(session_id)
        if not session or session.status != SessionStatus.ACTIVE:
            raise PermissionError("an active authorized session is required")
        authorization = self.authorizations[session.authorization_id]
        if not self._authorization_is_valid(authorization, ActionType.CREATE_DIGITAL_TWIN.value):
            raise PermissionError("authorization does not permit digital-twin creation")
        sources = list(source_observations or [])
        missing = [item for item in sources if item not in self.observations]
        if missing:
            raise ValueError(f"unknown source observations: {missing}")
        twin = DigitalTwin(
            twin_id=_id("twin"),
            asset_id=session.asset_id,
            protocol=protocol,
            simulated_state=dict(simulated_state),
            created_at=_now(),
            source_observations=sources,
        )
        self.digital_twins[twin.twin_id] = twin
        self._event("DIGITAL_TWIN_CREATED", session_id=session_id, twin_id=twin.twin_id)
        return asdict(twin)

    def request_action(
        self,
        session_id: str,
        action: ActionType | str,
        *,
        twin_id: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        action = ActionType(action)
        session = self.sessions.get(session_id)
        if not session or session.status != SessionStatus.ACTIVE:
            raise PermissionError("an active authorized session is required")
        authorization = self.authorizations[session.authorization_id]
        if not self._authorization_is_valid(authorization, action.value):
            raise PermissionError(f"authorization does not permit {action.value}")

        if action == ActionType.RUN_SIMULATION:
            if not twin_id or twin_id not in self.digital_twins:
                raise ValueError("RUN_SIMULATION requires a known digital twin")
            result = {
                "decision": "ALLOWED",
                "execution": "SIMULATION_ONLY",
                "action": action.value,
                "session_id": session_id,
                "twin_id": twin_id,
                "parameters": parameters or {},
            }
        elif action in ACTIVE_PHYSICAL_ACTIONS:
            # The ontology may represent a test request, but this runtime never
            # directly performs physical/RF actuation. A separately reviewed
            # adapter and human approval would be required downstream.
            result = {
                "decision": "STAGED",
                "execution": "NO_PHYSICAL_ACTUATION",
                "human_review_required": True,
                "action": action.value,
                "session_id": session_id,
                "parameters": parameters or {},
            }
        else:
            result = {
                "decision": "ALLOWED",
                "execution": "ONTOLOGY_ONLY",
                "action": action.value,
                "session_id": session_id,
                "parameters": parameters or {},
            }

        self._event("ACTION_REQUESTED", **result)
        return result

    def abort_session(self, session_id: str) -> Dict[str, Any]:
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError("unknown session")
        session.status = SessionStatus.ABORTED
        session.ended_at = _now()
        self._event("SESSION_ABORTED", session_id=session_id)
        return asdict(session)

    def summary(self) -> Dict[str, Any]:
        return {
            "object_counts": {
                "FlipperDevice": len(self.devices),
                "Asset": len(self.assets),
                "Authorization": len(self.authorizations),
                "TestSession": len(self.sessions),
                "Observation": len(self.observations),
                "DigitalTwin": len(self.digital_twins),
                "AuditEvent": len(self.audit_events),
            },
            "policy": {
                "default": "DENY",
                "physical_actuation": "STAGED_ONLY",
                "protected_asset_classes": sorted(PROTECTED_ASSET_CLASSES),
            },
        }


_RUNTIME = FlipperOntology()


def runtime() -> FlipperOntology:
    """Return the process-local GPT-DOUG Flipper ontology runtime."""
    return _RUNTIME
