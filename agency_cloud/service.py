from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from agency_cloud.audit import append_event, verify_chain
from agency_cloud.config import Settings
from agency_cloud.models import Alert, AuditEvent, Case, CaseIntel, IntelRecord, Report, Workspace, new_id


INTELLIGENCE_CLASSES = {
    "ADJUDICATED_LEGAL_FACT",
    "LEGAL_ACTION_FACT",
    "AGENCY_REPORTED_INTELLIGENCE",
    "LEGAL_RECORD_ALLEGATION",
    "LEGAL_RECORD_SUMMARY",
    "CORROBORATED_INTELLIGENCE",
    "MEDIA_INTELLIGENCE_CLAIM",
    "ANALYTIC_JUDGMENT",
    "UNVERIFIED_INTELLIGENCE",
    "BUSINESS_INTELLIGENCE",
    "CYBER_DEFENSE_INTELLIGENCE",
}
CONFIDENCE_LEVELS = {"LOW", "MEDIUM", "HIGH"}
CASE_STATUSES = {"OPEN", "MONITORING", "CLOSED"}
PRIORITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
REPORT_STATUSES = {"DRAFT", "FINAL"}
ALERT_STATUSES = {"OPEN", "ACKNOWLEDGED", "CLOSED"}


class IntelligenceServiceError(RuntimeError):
    pass


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "workspace"


def _source_digest(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class IntelligenceService:
    def __init__(self, session: Session, settings: Settings):
        self.session = session
        self.settings = settings

    def bootstrap(self) -> Workspace:
        workspace = self.session.scalar(select(Workspace).order_by(Workspace.created_at.asc()).limit(1))
        if workspace:
            return workspace
        workspace = Workspace(
            id=new_id("ws"),
            name=self.settings.default_workspace_name,
            slug=_slug(self.settings.default_workspace_name),
            active=True,
        )
        self.session.add(workspace)
        append_event(
            self.session,
            audit_key=self.settings.audit_key,
            workspace_id=workspace.id,
            actor="system-bootstrap",
            action="WORKSPACE_CREATED",
            object_type="workspace",
            object_id=workspace.id,
            payload={"name": workspace.name, "slug": workspace.slug},
        )
        self.session.commit()
        return workspace

    def get_workspace(self, workspace_id: str) -> Workspace:
        workspace = self.session.get(Workspace, workspace_id)
        if not workspace or not workspace.active:
            raise IntelligenceServiceError("workspace does not exist or is inactive")
        return workspace

    def list_workspaces(self) -> list[Workspace]:
        return list(self.session.scalars(select(Workspace).order_by(Workspace.name.asc())))

    def create_workspace(self, *, actor: str, name: str, slug: str | None = None) -> Workspace:
        workspace = Workspace(
            id=new_id("ws"),
            name=name.strip(),
            slug=_slug(slug or name),
            active=True,
        )
        if not workspace.name:
            raise IntelligenceServiceError("workspace name is required")
        self.session.add(workspace)
        append_event(
            self.session,
            audit_key=self.settings.audit_key,
            workspace_id=workspace.id,
            actor=actor,
            action="WORKSPACE_CREATED",
            object_type="workspace",
            object_id=workspace.id,
            payload={"name": workspace.name, "slug": workspace.slug},
        )
        self.session.commit()
        return workspace

    def status(self, workspace_id: str) -> dict:
        self.get_workspace(workspace_id)
        counts = {}
        for name, model in {
            "cases": Case,
            "intel": IntelRecord,
            "reports": Report,
            "alerts": Alert,
        }.items():
            counts[name] = self.session.scalar(
                select(func.count()).select_from(model).where(model.workspace_id == workspace_id)
            ) or 0
        audit_ok, audit_message = verify_chain(self.session, audit_key=self.settings.audit_key)
        return {
            "service": self.settings.service_name,
            "environment": self.settings.environment,
            "legalStatus": "PRIVATE INTELLIGENCE COMPANY — NOT A GOVERNMENT AGENCY",
            "workspaceId": workspace_id,
            "counts": counts,
            "auditChain": {"valid": audit_ok, "message": audit_message},
        }

    def create_case(
        self,
        *,
        workspace_id: str,
        actor: str,
        title: str,
        summary: str = "",
        priority: str = "MEDIUM",
        tags: list[str] | None = None,
    ) -> Case:
        self.get_workspace(workspace_id)
        priority = priority.upper()
        if priority not in PRIORITIES:
            raise IntelligenceServiceError("invalid case priority")
        sequence = self.session.scalar(
            select(func.count()).select_from(Case).where(Case.workspace_id == workspace_id)
        ) or 0
        case = Case(
            id=new_id("case"),
            workspace_id=workspace_id,
            case_number=f"ZIC-{datetime.now(timezone.utc):%Y%m%d}-{sequence + 1:04d}",
            title=title.strip(),
            summary=summary.strip(),
            status="OPEN",
            priority=priority,
            owner=actor,
            tags=tags or [],
        )
        if not case.title:
            raise IntelligenceServiceError("case title is required")
        self.session.add(case)
        append_event(
            self.session,
            audit_key=self.settings.audit_key,
            workspace_id=workspace_id,
            actor=actor,
            action="CASE_CREATED",
            object_type="case",
            object_id=case.id,
            payload={"caseNumber": case.case_number, "priority": case.priority},
        )
        self.session.commit()
        return case

    def list_cases(self, workspace_id: str) -> list[Case]:
        self.get_workspace(workspace_id)
        return list(
            self.session.scalars(
                select(Case).where(Case.workspace_id == workspace_id).order_by(Case.created_at.desc())
            )
        )

    def create_intel(
        self,
        *,
        workspace_id: str,
        actor: str,
        title: str,
        summary: str,
        intelligence_class: str,
        source_id: str,
        source_location: str,
        provenance_locator: str,
        confidence: str = "MEDIUM",
        jurisdiction: str = "BUSINESS_CONTEXT",
        tags: list[str] | None = None,
    ) -> IntelRecord:
        self.get_workspace(workspace_id)
        intelligence_class = intelligence_class.upper()
        confidence = confidence.upper()
        if intelligence_class not in INTELLIGENCE_CLASSES:
            raise IntelligenceServiceError("unsupported intelligence class")
        if confidence not in CONFIDENCE_LEVELS:
            raise IntelligenceServiceError("invalid confidence level")
        required = [title, summary, source_id, source_location, provenance_locator]
        if any(not str(value).strip() for value in required):
            raise IntelligenceServiceError("intel requires title, summary and complete provenance")
        digest = _source_digest(
            {
                "sourceId": source_id,
                "sourceLocation": source_location,
                "provenanceLocator": provenance_locator,
                "title": title,
                "summary": summary,
            }
        )
        record = IntelRecord(
            id=new_id("intel"),
            workspace_id=workspace_id,
            title=title.strip(),
            summary=summary.strip(),
            intelligence_class=intelligence_class,
            confidence=confidence,
            status="INGESTED",
            source_id=source_id.strip(),
            source_location=source_location.strip(),
            provenance_locator=provenance_locator.strip(),
            source_digest=digest,
            jurisdiction=jurisdiction.strip().upper() or "BUSINESS_CONTEXT",
            tags=tags or [],
            created_by=actor,
        )
        self.session.add(record)
        append_event(
            self.session,
            audit_key=self.settings.audit_key,
            workspace_id=workspace_id,
            actor=actor,
            action="INTEL_INGESTED",
            object_type="intel",
            object_id=record.id,
            payload={
                "intelligenceClass": record.intelligence_class,
                "confidence": record.confidence,
                "sourceDigest": digest,
            },
        )
        self.session.commit()
        return record

    def list_intel(self, workspace_id: str) -> list[IntelRecord]:
        self.get_workspace(workspace_id)
        return list(
            self.session.scalars(
                select(IntelRecord)
                .where(IntelRecord.workspace_id == workspace_id)
                .order_by(IntelRecord.created_at.desc())
            )
        )

    def attach_intel(self, *, workspace_id: str, actor: str, case_id: str, intel_id: str) -> CaseIntel:
        case = self.session.get(Case, case_id)
        intel = self.session.get(IntelRecord, intel_id)
        if not case or case.workspace_id != workspace_id:
            raise IntelligenceServiceError("case not found in workspace")
        if not intel or intel.workspace_id != workspace_id:
            raise IntelligenceServiceError("intel record not found in workspace")
        existing = self.session.scalar(
            select(CaseIntel).where(CaseIntel.case_id == case_id, CaseIntel.intel_id == intel_id)
        )
        if existing:
            return existing
        link = CaseIntel(case_id=case_id, intel_id=intel_id, attached_by=actor)
        self.session.add(link)
        append_event(
            self.session,
            audit_key=self.settings.audit_key,
            workspace_id=workspace_id,
            actor=actor,
            action="INTEL_ATTACHED_TO_CASE",
            object_type="case",
            object_id=case_id,
            payload={"intelId": intel_id},
        )
        self.session.commit()
        return link

    def create_report(
        self,
        *,
        workspace_id: str,
        actor: str,
        title: str,
        executive_summary: str,
        body: str,
        case_id: str | None = None,
        status: str = "DRAFT",
        classification: str = "BUSINESS_CONFIDENTIAL",
    ) -> Report:
        self.get_workspace(workspace_id)
        status = status.upper()
        if status not in REPORT_STATUSES:
            raise IntelligenceServiceError("invalid report status")
        if case_id:
            case = self.session.get(Case, case_id)
            if not case or case.workspace_id != workspace_id:
                raise IntelligenceServiceError("report case is outside workspace")
        report = Report(
            id=new_id("report"),
            workspace_id=workspace_id,
            case_id=case_id,
            title=title.strip(),
            executive_summary=executive_summary.strip(),
            body=body.strip(),
            status=status,
            classification=classification.strip().upper(),
            authored_by=actor,
            published_at=datetime.now(timezone.utc) if status == "FINAL" else None,
        )
        if not report.title or not report.body:
            raise IntelligenceServiceError("report title and body are required")
        self.session.add(report)
        append_event(
            self.session,
            audit_key=self.settings.audit_key,
            workspace_id=workspace_id,
            actor=actor,
            action="REPORT_CREATED",
            object_type="report",
            object_id=report.id,
            payload={"status": status, "caseId": case_id},
        )
        self.session.commit()
        return report

    def list_reports(self, workspace_id: str, *, client_visible_only: bool = False) -> list[Report]:
        self.get_workspace(workspace_id)
        statement = select(Report).where(Report.workspace_id == workspace_id)
        if client_visible_only:
            statement = statement.where(Report.status == "FINAL")
        return list(self.session.scalars(statement.order_by(Report.created_at.desc())))

    def create_alert(
        self,
        *,
        workspace_id: str,
        actor: str,
        title: str,
        summary: str,
        severity: str = "MEDIUM",
        source_ref: str = "",
    ) -> Alert:
        self.get_workspace(workspace_id)
        severity = severity.upper()
        if severity not in PRIORITIES:
            raise IntelligenceServiceError("invalid alert severity")
        alert = Alert(
            id=new_id("alert"),
            workspace_id=workspace_id,
            title=title.strip(),
            summary=summary.strip(),
            severity=severity,
            status="OPEN",
            source_ref=source_ref.strip(),
            created_by=actor,
        )
        if not alert.title or not alert.summary:
            raise IntelligenceServiceError("alert title and summary are required")
        self.session.add(alert)
        append_event(
            self.session,
            audit_key=self.settings.audit_key,
            workspace_id=workspace_id,
            actor=actor,
            action="ALERT_CREATED",
            object_type="alert",
            object_id=alert.id,
            payload={"severity": severity, "sourceRef": source_ref},
        )
        self.session.commit()
        return alert

    def list_alerts(self, workspace_id: str) -> list[Alert]:
        self.get_workspace(workspace_id)
        return list(
            self.session.scalars(
                select(Alert).where(Alert.workspace_id == workspace_id).order_by(Alert.created_at.desc())
            )
        )

    def audit_events(self, workspace_id: str | None = None, limit: int = 100) -> list[AuditEvent]:
        statement = select(AuditEvent)
        if workspace_id:
            statement = statement.where(AuditEvent.workspace_id == workspace_id)
        statement = statement.order_by(AuditEvent.created_at.desc()).limit(max(1, min(limit, 500)))
        return list(self.session.scalars(statement))
