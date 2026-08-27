from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency_cloud.models import AuditEvent, new_id


GENESIS_HASH = "0" * 64


def _canonical_payload(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _event_hash(key: str, envelope: dict) -> str:
    secret = key.encode("utf-8") if key else b"zyra-development-audit-key"
    return hmac.new(secret, _canonical_payload(envelope), hashlib.sha256).hexdigest()


def append_event(
    session: Session,
    *,
    audit_key: str,
    workspace_id: str | None,
    actor: str,
    action: str,
    object_type: str,
    object_id: str,
    payload: dict | None = None,
) -> AuditEvent:
    previous = session.scalar(select(AuditEvent).order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(1))
    prev_hash = previous.event_hash if previous else GENESIS_HASH
    created_at = datetime.now(timezone.utc)
    event_id = new_id("audit")
    body = {
        "id": event_id,
        "workspaceId": workspace_id,
        "actor": actor,
        "action": action,
        "objectType": object_type,
        "objectId": object_id,
        "payload": payload or {},
        "prevHash": prev_hash,
        "createdAt": created_at.isoformat(),
    }
    event = AuditEvent(
        id=event_id,
        workspace_id=workspace_id,
        actor=actor,
        action=action,
        object_type=object_type,
        object_id=object_id,
        payload=payload or {},
        prev_hash=prev_hash,
        event_hash=_event_hash(audit_key, body),
        created_at=created_at,
    )
    session.add(event)
    session.flush()
    return event


def verify_chain(session: Session, *, audit_key: str) -> tuple[bool, str]:
    events = list(session.scalars(select(AuditEvent).order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())))
    expected_prev = GENESIS_HASH
    for event in events:
        if event.prev_hash != expected_prev:
            return False, f"audit chain break before {event.id}"
        body = {
            "id": event.id,
            "workspaceId": event.workspace_id,
            "actor": event.actor,
            "action": event.action,
            "objectType": event.object_type,
            "objectId": event.object_id,
            "payload": event.payload or {},
            "prevHash": event.prev_hash,
            "createdAt": event.created_at.isoformat(),
        }
        if not hmac.compare_digest(event.event_hash, _event_hash(audit_key, body)):
            return False, f"audit event hash mismatch: {event.id}"
        expected_prev = event.event_hash
    return True, f"verified {len(events)} audit events"
