from __future__ import annotations

from datetime import datetime
from typing import Final

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from agency_cloud.audit import append_event
from agency_cloud.config import Settings
from agency_cloud.models import Base, new_id, utcnow

OPERATING_MODE: Final = "ADVISORY_ONLY"
DECISIONS: Final = {"ACCEPTED_FOR_HUMAN_IMPLEMENTATION", "REJECTED", "DEFERRED"}
RISK_LEVELS: Final = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


class AdvisoryRecord(Base):
    __tablename__ = "advisory_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    objective: Mapped[str] = mapped_column(String(280), nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False, default="MEDIUM")
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(48), nullable=False, default="PROPOSED")
    created_by: Mapped[str] = mapped_column(String(160), nullable=False)
    decided_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    decision_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AdvisoryError(RuntimeError):
    pass


def create_advisory(
    session: Session,
    settings: Settings,
    *,
    workspace_id: str,
    actor: str,
    objective: str,
    recommendation: str,
    rationale: str = "",
    risk_level: str = "MEDIUM",
    evidence_refs: list[str] | None = None,
) -> AdvisoryRecord:
    risk_level = str(risk_level or "MEDIUM").upper()
    if risk_level not in RISK_LEVELS:
        raise AdvisoryError("invalid advisory risk level")
    if not str(objective).strip() or not str(recommendation).strip():
        raise AdvisoryError("objective and recommendation are required")

    item = AdvisoryRecord(
        id=new_id("adv"),
        workspace_id=workspace_id,
        objective=str(objective).strip(),
        recommendation=str(recommendation).strip(),
        rationale=str(rationale or "").strip(),
        risk_level=risk_level,
        evidence_refs=[str(v)[:280] for v in (evidence_refs or [])][:64],
        status="PROPOSED",
        created_by=actor,
    )
    session.add(item)
    append_event(
        session,
        audit_key=settings.audit_key,
        workspace_id=workspace_id,
        actor=actor,
        action="ADVISORY_PROPOSED",
        object_type="advisory",
        object_id=item.id,
        payload={"riskLevel": risk_level, "mode": OPERATING_MODE},
    )
    session.commit()
    return item


def list_advisories(session: Session, workspace_id: str, *, limit: int = 100) -> list[AdvisoryRecord]:
    return list(
        session.scalars(
            select(AdvisoryRecord)
            .where(AdvisoryRecord.workspace_id == workspace_id)
            .order_by(AdvisoryRecord.created_at.desc())
            .limit(max(1, min(limit, 500)))
        )
    )


def decide_advisory(
    session: Session,
    settings: Settings,
    *,
    workspace_id: str,
    actor: str,
    advisory_id: str,
    decision: str,
    note: str = "",
) -> AdvisoryRecord:
    decision = str(decision or "").upper()
    if decision not in DECISIONS:
        raise AdvisoryError("invalid advisory decision")
    item = session.get(AdvisoryRecord, advisory_id)
    if not item or item.workspace_id != workspace_id:
        raise AdvisoryError("advisory not found in workspace")

    item.status = decision
    item.decided_by = actor
    item.decision_note = str(note or "").strip()
    item.decided_at = utcnow()
    append_event(
        session,
        audit_key=settings.audit_key,
        workspace_id=workspace_id,
        actor=actor,
        action="ADVISORY_DECISION_RECORDED",
        object_type="advisory",
        object_id=item.id,
        payload={"decision": decision, "mode": OPERATING_MODE, "execution": False},
    )
    session.commit()
    return item


def advisory_policy() -> dict:
    return {
        "mode": OPERATING_MODE,
        "humanAuthority": True,
        "autonomousExecution": False,
        "implementationBoundary": "Recommendation and decision records only. Execution is outside this AI service.",
        "allowed": ["analyze", "compare", "recommend", "prioritize", "explain", "record human decision"],
        "notProvided": ["direct execution", "credential use", "privileged mutation", "unattended consequential action"],
    }
