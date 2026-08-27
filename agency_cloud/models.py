from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class Base(DeclarativeBase):
    pass


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(96), nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (UniqueConstraint("workspace_id", "case_number", name="uq_case_number"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    case_number: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="MEDIUM")
    owner: Mapped[str] = mapped_column(String(160), nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    intel_links: Mapped[list["CaseIntel"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class IntelRecord(Base):
    __tablename__ = "intel_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(280), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    intelligence_class: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False, default="MEDIUM")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="INGESTED")
    source_id: Mapped[str] = mapped_column(String(280), nullable=False)
    source_location: Mapped[str] = mapped_column(Text, nullable=False)
    provenance_locator: Mapped[str] = mapped_column(String(280), nullable=False)
    source_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(64), nullable=False, default="BUSINESS_CONTEXT")
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_by: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case_links: Mapped[list["CaseIntel"]] = relationship(back_populates="intel", cascade="all, delete-orphan")


class CaseIntel(Base):
    __tablename__ = "case_intel"
    __table_args__ = (UniqueConstraint("case_id", "intel_id", name="uq_case_intel"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    intel_id: Mapped[str] = mapped_column(ForeignKey("intel_records.id", ondelete="CASCADE"), index=True)
    attached_by: Mapped[str] = mapped_column(String(160), nullable=False)
    attached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case: Mapped[Case] = relationship(back_populates="intel_links")
    intel: Mapped[IntelRecord] = relationship(back_populates="case_links")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(280), nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT")
    classification: Mapped[str] = mapped_column(String(48), nullable=False, default="BUSINESS_CONFIDENTIAL")
    authored_by: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(280), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="MEDIUM")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="OPEN")
    source_ref: Mapped[str] = mapped_column(String(280), nullable=False, default="")
    created_by: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    actor: Mapped[str] = mapped_column(String(160), nullable=False)
    action: Mapped[str] = mapped_column(String(96), nullable=False)
    object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    object_id: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
