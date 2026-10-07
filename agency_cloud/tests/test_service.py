from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from agency_cloud.advisory import create_advisory, decide_advisory, list_advisories
from agency_cloud.audit import verify_chain
from agency_cloud.compliance import posture
from agency_cloud.config import Settings
from agency_cloud.db import build_engine, build_session_factory, create_schema
from agency_cloud.global_compliance import (
    global_catalog,
    global_posture,
    horizon_2027,
    jurisdiction_profile,
)
from agency_cloud.global_intel import build_benchmark, source_catalog
from agency_cloud.models import AuditEvent
from agency_cloud.service import IntelligenceService, IntelligenceServiceError


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
        cors_origins=("https://example.invalid",),
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
        assert status["counts"] == {"cases": 1, "intel": 1, "reports": 1, "alerts": 1, "events": 0}
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



def test_platform_event_fabric_persists_and_filters_public_classes(tmp_path: Path):
    settings = settings_for(tmp_path)
    engine = build_engine(settings)
    create_schema(engine)
    factory = build_session_factory(engine)

    with factory() as session:
        service = IntelligenceService(session, settings)
        workspace = service.bootstrap()

        public = service.create_platform_event(
            workspace_id=workspace.id,
            actor="analyst-test",
            event_type="SENSOR_HEALTH",
            entity_kind="sensor",
            object_id="sensor-01",
            title="Sensor healthy",
            summary="Synthetic sensor heartbeat.",
            classification="SIMULATION",
            source_id="platform-sim",
            provenance_locator="test:platform-sim",
            confidence=0.96,
            payload={"status": "healthy"},
        )
        service.create_platform_event(
            workspace_id=workspace.id,
            actor="analyst-test",
            event_type="BUSINESS_SIGNAL",
            entity_kind="event",
            object_id="signal-01",
            title="Private business signal",
            summary="Confidential test event.",
            classification="BUSINESS_CONFIDENTIAL",
            source_id="operator",
            provenance_locator="test:operator",
            confidence=0.9,
            payload={},
        )

        assert service.list_platform_events(workspace.id)[0].id != ""
        public_events = service.list_public_platform_events()
        assert [item.id for item in public_events] == [public.id]
        assert service.status(workspace.id)["counts"]["events"] == 2



def test_platform_event_policy_blocks_operational_weapon_actions(tmp_path: Path):
    settings = settings_for(tmp_path)
    engine = build_engine(settings)
    create_schema(engine)
    factory = build_session_factory(engine)

    with factory() as session:
        service = IntelligenceService(session, settings)
        workspace = service.bootstrap()
        with pytest.raises(IntelligenceServiceError):
            service.create_platform_event(
                workspace_id=workspace.id,
                actor="analyst-test",
                event_type="TARGET_SELECTION",
                entity_kind="event",
                object_id="blocked-01",
                title="Blocked operation",
                summary="Must never enter the operational event fabric.",
                classification="SIMULATION",
                source_id="platform-sim",
                provenance_locator="test:blocked",
                confidence=1.0,
                payload={},
            )



def test_advisory_records_never_execute(tmp_path: Path):
    settings = settings_for(tmp_path)
    engine = build_engine(settings)
    create_schema(engine)
    factory = build_session_factory(engine)

    with factory() as session:
        service = IntelligenceService(session, settings)
        workspace = service.bootstrap()
        item = create_advisory(
            session,
            settings,
            workspace_id=workspace.id,
            actor="analyst-test",
            objective="Improve production resilience",
            recommendation="Move durable state to managed Postgres and add restore testing.",
            rationale="Current local state is not a durable production boundary.",
            risk_level="HIGH",
            evidence_refs=["CP-DATA-01"],
        )
        assert item.status == "PROPOSED"
        decided = decide_advisory(
            session,
            settings,
            workspace_id=workspace.id,
            actor="director-test",
            advisory_id=item.id,
            decision="ACCEPTED_FOR_HUMAN_IMPLEMENTATION",
            note="Approved for an authorized operator to implement.",
        )
        assert decided.status == "ACCEPTED_FOR_HUMAN_IMPLEMENTATION"
        assert len(list_advisories(session, workspace.id)) == 1


def test_compliance_posture_is_evidence_not_certification(tmp_path: Path):
    settings = settings_for(tmp_path)
    result = posture(settings)
    assert result["schema"] == "gpt-doug.compliance-posture.v1"
    assert "no certification" in result["claim"].lower()
    assert result["counts"]["EXTERNAL"] >= 1



def test_global_compliance_catalog_and_2027_horizon(tmp_path: Path):
    settings = settings_for(tmp_path)
    catalog = global_catalog()
    horizon = horizon_2027()
    profile = jurisdiction_profile(["US", "EU", "UK"])
    posture_result = global_posture(settings)

    assert catalog["schema"] == "gpt-doug.global-compliance-catalog.v1"
    assert catalog["coverage"]["regimeCount"] >= 20
    assert "GLOBAL" in catalog["coverage"]["regions"]
    assert "EU" in catalog["coverage"]["regions"]
    assert "US" in catalog["coverage"]["regions"]
    assert any(item["date"] == "2027-12-11" for item in horizon["events"])
    assert any(item["date"] == "2027-12-02" for item in horizon["events"])
    assert "EU" in profile["regions"]
    assert "AI" in profile["requiredEngineeringDomains"]
    assert posture_result["schema"] == "gpt-doug.global-posture.v1"
    assert posture_result["counts"]["EXTERNAL"] >= 1



def test_global_intel_benchmark_uses_public_safe_sources():
    now = "2026-10-07T18:00:00+00:00"

    def fake_fetch(url: str):
        if "earthquake.usgs.gov" in url:
            return (
                {
                    "metadata": {"generated": 1791396000000},
                    "features": [
                        {
                            "properties": {"mag": 5.2, "place": "Synthetic Test Quake"},
                            "geometry": {"coordinates": [10.0, 20.0, 5.0]},
                        }
                    ],
                },
                100,
            )
        if "eonet.gsfc.nasa.gov" in url:
            return (
                {
                    "events": [
                        {
                            "title": "Synthetic Wildfire",
                            "categories": [{"title": "Wildfires"}],
                            "geometry": [{"date": now, "coordinates": [30.0, 40.0]}],
                        }
                    ]
                },
                120,
            )
        if "services.swpc.noaa.gov" in url:
            return ([["time_tag", "Kp"], [now, "4.0"]], 90)
        if "cisa.gov" in url:
            return (
                {
                    "vulnerabilities": [
                        {
                            "dateAdded": "2026-10-07",
                            "knownRansomwareCampaignUse": "Known",
                        }
                    ]
                },
                130,
            )
        if "api.worldbank.org" in url:
            return (
                [
                    {"page": 1},
                    [
                        {
                            "date": "2025",
                            "value": 68.5,
                            "indicator": {"value": "Individuals using the Internet (% of population)"},
                        }
                    ],
                ],
                110,
            )
        raise AssertionError(url)

    catalog = source_catalog()
    result = build_benchmark(fake_fetch)

    assert catalog["policy"]["mode"] == "PUBLIC_STRATEGIC_ONLY"
    assert "weapon targeting" in catalog["policy"]["blocked"]
    assert result["schema"] == "gpt-doug.global-intel-benchmark.v1"
    assert result["benchmark"]["sourceCount"] == 5
    assert result["benchmark"]["onlineSources"] == 5
    assert result["benchmark"]["overallScore"] >= 80
    assert result["signals"]["cisa-kev"]["catalogSize"] == 1
    assert any(point["category"] == "EARTHQUAKE" for point in result["mapPoints"])
