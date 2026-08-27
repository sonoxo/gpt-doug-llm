from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from agency_cloud.audit import verify_chain
from agency_cloud.config import Settings
from agency_cloud.db import build_engine, build_session_factory, create_schema
from agency_cloud.models import AuditEvent
from agency_cloud.service import IntelligenceService


def settings_for(tmp_path: Path) -> Settings:
    return Settings(
        service_name="ZYRA Intelligence Cloud Test",
        environment="test",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'agency.db').as_posix()}",
        audit_key="unit-test-audit-key",
        director_token="director-test",
        analyst_token="analyst-test",
        auditor_token="auditor-test",
        client_token="client-test",
        allow_demo_auth=False,
        repo_root=tmp_path,
        default_workspace_name="Test Command",
    )


def test_full_intelligence_business_flow(tmp_path: Path):
    settings = settings_for(tmp_path)
    engine = build_engine(settings)
    create_schema(engine)
    factory = build_session_factory(engine)

    with factory() as session:
        service = IntelligenceService(session, settings)
        workspace = service.bootstrap()
        case = service.create_case(
            workspace_id=workspace.id,
            actor="analyst-test",
            title="Supply-chain risk watch",
            summary="Track corroborated business and cyber-defense indicators.",
            priority="HIGH",
            tags=["supply-chain"],
        )
        intel = service.create_intel(
            workspace_id=workspace.id,
            actor="analyst-test",
            title="Vendor advisory published",
            summary="Vendor published an advisory affecting a monitored dependency.",
            intelligence_class="CYBER_DEFENSE_INTELLIGENCE",
            source_id="vendor-advisory-001",
            source_location="https://example.invalid/advisory/001",
            provenance_locator="section:summary",
            confidence="HIGH",
            tags=["vendor", "dependency"],
        )
        service.attach_intel(
            workspace_id=workspace.id,
            actor="analyst-test",
            case_id=case.id,
            intel_id=intel.id,
        )
        service.create_report(
            workspace_id=workspace.id,
            actor="analyst-test",
            title="Client risk brief",
            executive_summary="Monitored dependency requires review.",
            body="Source-grounded business intelligence brief.",
            case_id=case.id,
            status="FINAL",
        )
        service.create_alert(
            workspace_id=workspace.id,
            actor="analyst-test",
            title="Dependency review required",
            summary="Review exposure and remediation guidance.",
            severity="HIGH",
            source_ref=intel.id,
        )

        status = service.status(workspace.id)
        assert status["counts"] == {"cases": 1, "intel": 1, "reports": 1, "alerts": 1}
        assert status["auditChain"]["valid"] is True
        assert len(intel.source_digest) == 64
        assert service.list_reports(workspace.id, client_visible_only=True)[0].status == "FINAL"


def test_audit_chain_detects_tampering(tmp_path: Path):
    settings = settings_for(tmp_path)
    engine = build_engine(settings)
    create_schema(engine)
    factory = build_session_factory(engine)

    with factory() as session:
        service = IntelligenceService(session, settings)
        workspace = service.bootstrap()
        service.create_case(
            workspace_id=workspace.id,
            actor="director-test",
            title="Integrity test",
            priority="MEDIUM",
        )
        valid, _ = verify_chain(session, audit_key=settings.audit_key)
        assert valid is True

        event = session.scalar(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(1))
        assert event is not None
        event.payload = {"tampered": True}
        session.commit()
        valid, message = verify_chain(session, audit_key=settings.audit_key)
        assert valid is False
        assert "mismatch" in message
