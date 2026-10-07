from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

from agency_cloud import __version__
from agency_cloud.advisory import (
    AdvisoryError,
    advisory_policy,
    create_advisory,
    decide_advisory,
    list_advisories,
)
from agency_cloud.audit import verify_chain
from agency_cloud.bioinformatics import (
    bioinformatics_catalog,
    bioinformatics_fusion,
)
from agency_cloud.compliance import (
    catalog as compliance_catalog,
    posture as compliance_posture,
)
from agency_cloud.config import load_settings
from agency_cloud.db import build_engine, build_session_factory, create_schema
from agency_cloud.global_compliance import (
    global_catalog,
    global_posture,
    horizon_2027,
    jurisdiction_profile,
)
from agency_cloud.global_intel import (
    global_intel_benchmark,
    source_catalog as global_intel_source_catalog,
)
from agency_cloud.integrations import (
    IntelligenceIntegrationError,
    glassonion_query,
    glassonion_status,
    live_changes,
    lock_summary,
    ontology_query,
    ontology_status,
)
from agency_cloud.platform import (
    ONTOLOGY_SCHEMA,
    PLATFORM_MANIFEST,
    PUBLIC_EVENT_CLASSES,
    SOURCE_REGISTRY,
)
from agency_cloud.realtime import event_hub
from agency_cloud.security import (
    AuthenticationError,
    AuthorizationError,
    Principal,
    authenticate,
    require_role,
)
from agency_cloud.service import IntelligenceService, IntelligenceServiceError

settings = load_settings()
engine = build_engine(settings)
session_factory = build_session_factory(engine)
security = HTTPBearer(auto_error=False)
static_dir = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_schema(engine)
    with session_factory() as session:
        IntelligenceService(session, settings).bootstrap()
    yield


app = FastAPI(
    title="ZYRA Intelligence Cloud",
    version=__version__,
    description=(
        "Private business-intelligence and cyber-defense operations platform. "
        "Not a government agency and does not confer governmental authority."
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Zyra-Workspace"],
)
@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-Frame-Options"] = "DENY"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


app.mount("/assets", StaticFiles(directory=static_dir), name="assets")


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    slug: str | None = Field(default=None, max_length=96)


class CaseCreate(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    summary: str = Field(default="", max_length=10000)
    priority: str = "MEDIUM"
    tags: list[str] = Field(default_factory=list, max_length=32)


class IntelCreate(BaseModel):
    title: str = Field(min_length=2, max_length=280)
    summary: str = Field(min_length=2, max_length=40000)
    intelligence_class: str
    source_id: str = Field(min_length=1, max_length=280)
    source_location: str = Field(min_length=1, max_length=4000)
    provenance_locator: str = Field(min_length=1, max_length=280)
    confidence: str = "MEDIUM"
    jurisdiction: str = "BUSINESS_CONTEXT"
    tags: list[str] = Field(default_factory=list, max_length=64)


class ReportCreate(BaseModel):
    title: str = Field(min_length=2, max_length=280)
    executive_summary: str = Field(default="", max_length=20000)
    body: str = Field(min_length=2, max_length=100000)
    case_id: str | None = None
    status: str = "DRAFT"
    classification: str = "BUSINESS_CONFIDENTIAL"


class AlertCreate(BaseModel):
    title: str = Field(min_length=2, max_length=280)
    summary: str = Field(min_length=2, max_length=20000)
    severity: str = "MEDIUM"
    source_ref: str = Field(default="", max_length=280)


class QueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)


class PlatformEventCreate(BaseModel):
    event_type: str = Field(min_length=2, max_length=64)
    entity_kind: str = Field(default="event", min_length=1, max_length=64)
    object_id: str = Field(default="", max_length=128)
    title: str = Field(min_length=2, max_length=280)
    summary: str = Field(default="", max_length=20000)
    classification: str = Field(default="SIMULATION", min_length=2, max_length=48)
    source_id: str = Field(min_length=1, max_length=160)
    provenance_locator: str = Field(min_length=1, max_length=500)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    payload: dict = Field(default_factory=dict)


class AdvisoryCreate(BaseModel):
    objective: str = Field(min_length=2, max_length=280)
    recommendation: str = Field(min_length=2, max_length=40000)
    rationale: str = Field(default="", max_length=40000)
    risk_level: str = Field(default="MEDIUM", max_length=16)
    evidence_refs: list[str] = Field(default_factory=list, max_length=64)


class AdvisoryDecision(BaseModel):
    decision: str = Field(min_length=2, max_length=48)
    note: str = Field(default="", max_length=20000)


def get_session():
    with session_factory() as session:
        yield session


def get_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> Principal:
    try:
        token = credentials.credentials if credentials else ""
        return authenticate(settings, token)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_workspace_header(
    workspace_id: Annotated[str | None, Header(alias="X-Zyra-Workspace")] = None,
) -> str:
    if not workspace_id:
        raise HTTPException(status_code=400, detail="X-Zyra-Workspace header is required")
    return workspace_id


def _guard(principal: Principal, *roles: str) -> None:
    try:
        require_role(principal, *roles)
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _row(value) -> dict:
    result = {}
    for column in inspect(value).mapper.column_attrs:
        item = getattr(value, column.key)
        if isinstance(item, datetime):
            item = item.isoformat()
        result[column.key] = item
    return result


def _service(session: Session) -> IntelligenceService:
    return IntelligenceService(session, settings)


def _service_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@app.get("/")
def dashboard():
    return FileResponse(static_dir / "index.html")


@app.get("/global-compliance")
def global_compliance_dashboard():
    return FileResponse(static_dir / "global-compliance.html")


@app.get("/global-intel")
def global_intel_dashboard():
    return FileResponse(static_dir / "global-intel.html")


@app.get("/bioinformatics-fusion")
def bioinformatics_fusion_dashboard():
    return FileResponse(static_dir / "bioinformatics-fusion.html")


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "service": settings.service_name,
        "version": __version__,
        "legalStatus": "PRIVATE INTELLIGENCE COMPANY — NOT A GOVERNMENT AGENCY",
    }


@app.get("/readyz")
def readyz():
    try:
        with session_factory() as session:
            session.execute(text("SELECT 1"))
            audit_ok, audit_message = verify_chain(session, audit_key=settings.audit_key)
        if not audit_ok:
            raise HTTPException(status_code=503, detail={"database": "ok", "audit": audit_message})
        return {
            "status": "ready",
            "database": "ok",
            "audit": audit_message,
            "realtimeConnections": event_hub.connection_count,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"readiness failure: {exc}") from exc


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    with session_factory() as session:
        from agency_cloud.models import (
            Alert,
            AuditEvent,
            Case,
            IntelRecord,
            PlatformEvent,
            Report,
            Workspace,
        )
        counts = {
            "workspaces": session.scalar(select(func.count()).select_from(Workspace)) or 0,
            "cases": session.scalar(select(func.count()).select_from(Case)) or 0,
            "intel": session.scalar(select(func.count()).select_from(IntelRecord)) or 0,
            "reports": session.scalar(select(func.count()).select_from(Report)) or 0,
            "alerts": session.scalar(select(func.count()).select_from(Alert)) or 0,
            "events": session.scalar(select(func.count()).select_from(PlatformEvent)) or 0,
            "audit": session.scalar(select(func.count()).select_from(AuditEvent)) or 0,
        }
        audit_ok, _ = verify_chain(session, audit_key=settings.audit_key)

    lines = [
        "# HELP gpt_doug_core_info GPT-DOUG core platform identity.",
        "# TYPE gpt_doug_core_info gauge",
        'gpt_doug_core_info{service="' + settings.service_name.replace('"', "") + '"} 1',
        "# HELP gpt_doug_realtime_connections Current public realtime client count.",
        "# TYPE gpt_doug_realtime_connections gauge",
        f"gpt_doug_realtime_connections {event_hub.connection_count}",
        "# HELP gpt_doug_audit_chain_valid Whether the audit chain verifies.",
        "# TYPE gpt_doug_audit_chain_valid gauge",
        f"gpt_doug_audit_chain_valid {1 if audit_ok else 0}",
    ]
    for name, value in counts.items():
        lines.extend([
            f"# HELP gpt_doug_{name}_total Persisted GPT-DOUG {name} count.",
            f"# TYPE gpt_doug_{name}_total gauge",
            f"gpt_doug_{name}_total {value}",
        ])
    return "\n".join(lines) + "\n"


@app.get("/api/v1/meta")
def meta():
    return {
        "service": settings.service_name,
        "version": __version__,
        "environment": settings.environment,
        "legalStatus": "PRIVATE INTELLIGENCE COMPANY — NOT A GOVERNMENT AGENCY",
        "mission": "Business intelligence, strategic risk, cyber-defense intelligence, and client advisory.",
    }


@app.get("/api/v1/workspaces")
def workspaces(
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[Session, Depends(get_session)],
):
    _guard(principal, "director", "auditor")
    return [_row(item) for item in _service(session).list_workspaces()]


@app.post("/api/v1/workspaces", status_code=201)
def create_workspace(
    payload: WorkspaceCreate,
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[Session, Depends(get_session)],
):
    _guard(principal, "director")
    try:
        return _row(
            _service(session).create_workspace(
                actor=principal.subject,
                name=payload.name,
                slug=payload.slug,
            )
        )
    except IntelligenceServiceError as exc:
        raise _service_error(exc) from exc


@app.get("/api/v1/status")
def status(
    workspace_id: Annotated[str, Depends(get_workspace_header)],
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[Session, Depends(get_session)],
):
    _guard(principal, "director", "analyst", "auditor", "client")
    try:
        result = _service(session).status(workspace_id)
        result["locks"] = lock_summary(settings)
        return result
    except (IntelligenceServiceError, IntelligenceIntegrationError) as exc:
        raise _service_error(exc) from exc


@app.get("/api/v1/cases")
def cases(
    workspace_id: Annotated[str, Depends(get_workspace_header)],
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[Session, Depends(get_session)],
):
    _guard(principal, "director", "analyst", "auditor", "client")
    try:
        return [_row(item) for item in _service(session).list_cases(workspace_id)]
    except IntelligenceServiceError as exc:
        raise _service_error(exc) from exc


@app.post("/api/v1/cases", status_code=201)
def create_case(
    payload: CaseCreate,
    workspace_id: Annotated[str, Depends(get_workspace_header)],
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[Session, Depends(get_session)],
):
    _guard(principal, "director", "analyst")
    try:
        item = _service(session).create_case(
            workspace_id=workspace_id,
            actor=principal.subject,
            title=payload.title,
            summary=payload.summary,
            priority=payload.priority,
            tags=payload.tags,
        )
        return _row(item)
    except IntelligenceServiceError as exc:
        raise _service_error(exc) from exc


@app.get("/api/v1/intel")
def intel_records(
    workspace_id: Annotated[str, Depends(get_workspace_header)],
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[Session, Depends(get_session)],
):
    _guard(principal, "director", "analyst", "auditor")
    try:
        return [_row(item) for item in _service(session).list_intel(workspace_id)]
    except IntelligenceServiceError as exc:
        raise _service_error(exc) from exc


@app.post("/api/v1/intel", status_code=201)
def create_intel(
    payload: IntelCreate,
    workspace_id: Annotated[str, Depends(get_workspace_header)],
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[Session, Depends(get_session)],
):
    _guard(principal, "director", "analyst")
    try:
        item = _service(session).create_intel(
            workspace_id=workspace_id,
            actor=principal.subject,
            title=payload.title,
            summary=payload.summary,
            intelligence_class=payload.intelligence_class,
            source_id=payload.source_id,
            source_location=payload.source_location,
            provenance_locator=payload.provenance_locator,
            confidence=payload.confidence,
            jurisdiction=payload.jurisdiction,
            tags=payload.tags,
        )
        return _row(item)
    except IntelligenceServiceError as exc:
        raise _service_error(exc) from exc


@app.post("/api/v1/cases/{case_id}/intel/{intel_id}", status_code=201)
def attach_intel(
    case_id: str,
    intel_id: str,
    workspace_id: Annotated[str, Depends(get_workspace_header)],
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[Session, Depends(get_session)],
):
    _guard(principal, "director", "analyst")
    try:
        link = _service(session).attach_intel(
            workspace_id=workspace_id,
            actor=principal.subject,
            case_id=case_id,
            intel_id=intel_id,
        )
        return {
            "caseId": link.case_id,
            "intelId": link.intel_id,
            "attachedBy": link.attached_by,
        }
    except IntelligenceServiceError as exc:
        raise _service_error(exc) from exc


@app.get("/api/v1/reports")
def reports(
    workspace_id: Annotated[str, Depends(get_workspace_header)],
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[Session, Depends(get_session)],
):
    _guard(principal, "director", "analyst", "auditor", "client")
    try:
        items = _service(session).list_reports(
            workspace_id,
            client_visible_only=principal.role == "client",
        )
        return [_row(item) for item in items]
    except IntelligenceServiceError as exc:
        raise _service_error(exc) from exc


@app.post("/api/v1/reports", status_code=201)
def create_report(
    payload: ReportCreate,
    workspace_id: Annotated[str, Depends(get_workspace_header)],
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[Session, Depends(get_session)],
):
    _guard(principal, "director", "analyst")
    try:
        item = _service(session).create_report(
            workspace_id=workspace_id,
            actor=principal.subject,
            title=payload.title,
            executive_summary=payload.executive_summary,
            body=payload.body,
            case_id=payload.case_id,
            status=payload.status,
            classification=payload.classification,
        )
        return _row(item)
    except IntelligenceServiceError as exc:
        raise _service_error(exc) from exc


@app.get("/api/v1/alerts")
def alerts(
    workspace_id: Annotated[str, Depends(get_workspace_header)],
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[Session, Depends(get_session)],
):
    _guard(principal, "director", "analyst", "auditor", "client")
    try:
        return [_row(item) for item in _service(session).list_alerts(workspace_id)]
    except IntelligenceServiceError as exc:
        raise _service_error(exc) from exc


@app.post("/api/v1/alerts", status_code=201)
def create_alert(
    payload: AlertCreate,
    workspace_id: Annotated[str, Depends(get_workspace_header)],
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[Session, Depends(get_session)],
):
    _guard(principal, "director", "analyst")
    try:
        item = _service(session).create_alert(
            workspace_id=workspace_id,
            actor=principal.subject,
            title=payload.title,
            summary=payload.summary,
            severity=payload.severity,
            source_ref=payload.source_ref,
        )
        return _row(item)
    except IntelligenceServiceError as exc:
        raise _service_error(exc) from exc


@app.get("/api/v1/audit")
def audit_events(
    workspace_id: Annotated[str, Depends(get_workspace_header)],
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[Session, Depends(get_session)],
    limit: int = 100,
):
    _guard(principal, "director", "auditor")
    return [_row(item) for item in _service(session).audit_events(workspace_id, limit=limit)]


@app.get("/api/v1/audit/verify")
def audit_verify(
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[Session, Depends(get_session)],
):
    _guard(principal, "director", "auditor")
    valid, message = verify_chain(session, audit_key=settings.audit_key)
    return {"valid": valid, "message": message}


@app.get("/api/v1/live/changes")
def api_live_changes(principal: Annotated[Principal, Depends(get_principal)]):
    _guard(principal, "director", "analyst", "auditor")
    try:
        return live_changes(settings)
    except IntelligenceIntegrationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/v1/ontology/status")
def api_ontology_status(principal: Annotated[Principal, Depends(get_principal)]):
    _guard(principal, "director", "analyst", "auditor")
    try:
        return {"result": ontology_status(settings)}
    except IntelligenceIntegrationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/v1/ontology/query")
def api_ontology_query(
    payload: QueryRequest,
    principal: Annotated[Principal, Depends(get_principal)],
):
    _guard(principal, "director", "analyst", "auditor")
    try:
        return {"result": ontology_query(settings, payload.question)}
    except IntelligenceIntegrationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/v1/glassonion/status")
def api_glassonion_status(principal: Annotated[Principal, Depends(get_principal)]):
    _guard(principal, "director", "analyst", "auditor")
    try:
        return {"result": glassonion_status(settings)}
    except IntelligenceIntegrationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/v1/glassonion/query")
def api_glassonion_query(
    payload: QueryRequest,
    principal: Annotated[Principal, Depends(get_principal)],
):
    _guard(principal, "director", "analyst", "auditor")
    try:
        return {"result": glassonion_query(settings, payload.question)}
    except IntelligenceIntegrationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/v1/platform/manifest")
def platform_manifest():
    return {
        **PLATFORM_MANIFEST,
        "operatingPolicy": advisory_policy(),
        "realtimeConnections": event_hub.connection_count,
        "service": settings.service_name,
        "environment": settings.environment,
    }


@app.get("/api/v1/ontology/schema")
def ontology_schema():
    return ONTOLOGY_SCHEMA


@app.get("/api/v1/sources")
def source_registry():
    return {"sources": SOURCE_REGISTRY}


@app.get("/api/v1/public/events")
def public_events(
    session: Annotated[Session, Depends(get_session)],
    limit: int = 50,
):
    events = _service(session).list_public_platform_events(limit=limit)
    return {
        "classes": sorted(PUBLIC_EVENT_CLASSES),
        "events": [_row(item) for item in events],
    }


@app.get("/api/v1/events")
def platform_events(
    workspace_id: Annotated[str, Depends(get_workspace_header)],
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[Session, Depends(get_session)],
    limit: int = 100,
):
    _guard(principal, "director", "analyst", "auditor")
    try:
        return [_row(item) for item in _service(session).list_platform_events(workspace_id, limit=limit)]
    except IntelligenceServiceError as exc:
        raise _service_error(exc) from exc


@app.post("/api/v1/events", status_code=201)
async def create_platform_event(
    payload: PlatformEventCreate,
    workspace_id: Annotated[str, Depends(get_workspace_header)],
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[Session, Depends(get_session)],
):
    _guard(principal, "director", "analyst")
    try:
        item = _service(session).create_platform_event(
            workspace_id=workspace_id,
            actor=principal.subject,
            event_type=payload.event_type,
            entity_kind=payload.entity_kind,
            object_id=payload.object_id,
            title=payload.title,
            summary=payload.summary,
            classification=payload.classification,
            source_id=payload.source_id,
            provenance_locator=payload.provenance_locator,
            confidence=payload.confidence,
            payload=payload.payload,
        )
    except IntelligenceServiceError as exc:
        raise _service_error(exc) from exc

    event = _row(item)
    if item.classification in PUBLIC_EVENT_CLASSES:
        await event_hub.broadcast({"type": "platform_event", "event": event})
    return event


@app.websocket("/ws/v1/events")
async def public_event_stream(websocket: WebSocket):
    await event_hub.connect(websocket)
    try:
        with session_factory() as session:
            history = [
                _row(item)
                for item in _service(session).list_public_platform_events(limit=25)
            ]
        await websocket.send_json(
            {
                "type": "platform_snapshot",
                "ontologyVersion": ONTOLOGY_SCHEMA["version"],
                "events": history,
                "publicClasses": sorted(PUBLIC_EVENT_CLASSES),
            }
        )
        while True:
            await asyncio.sleep(10)
            await websocket.send_json(
                {
                    "type": "heartbeat",
                    "service": settings.service_name,
                    "ontologyVersion": ONTOLOGY_SCHEMA["version"],
                    "connections": event_hub.connection_count,
                }
            )
    except Exception:
        pass
    finally:
        await event_hub.disconnect(websocket)


@app.get("/api/v1/bioinformatics/catalog")
def api_bioinformatics_catalog():
    return bioinformatics_catalog()


@app.get("/api/v1/bioinformatics/fusion")
def api_bioinformatics_fusion():
    return bioinformatics_fusion()


@app.get("/api/v1/intel/global/sources")
def api_global_intel_sources():
    return global_intel_source_catalog()


@app.get("/api/v1/intel/global/benchmark")
def api_global_intel_benchmark():
    return global_intel_benchmark()


@app.get("/api/v1/compliance/catalog")
def api_compliance_catalog():
    return compliance_catalog()


@app.get("/api/v1/compliance/global")
def api_global_compliance_catalog():
    return global_catalog()


@app.get("/api/v1/compliance/horizon/2027")
def api_compliance_horizon_2027():
    return horizon_2027()


@app.get("/api/v1/compliance/jurisdictions")
def api_compliance_jurisdictions(regions: str = "GLOBAL,US,EU,UK"):
    requested = [item.strip() for item in regions.split(",") if item.strip()]
    return jurisdiction_profile(requested)


@app.get("/api/v1/compliance/posture")
def api_compliance_posture(
    principal: Annotated[Principal, Depends(get_principal)],
):
    _guard(principal, "director", "auditor")
    return compliance_posture(settings)


@app.get("/api/v1/compliance/global/posture")
def api_global_compliance_posture(
    principal: Annotated[Principal, Depends(get_principal)],
):
    _guard(principal, "director", "auditor")
    return global_posture(settings)


@app.get("/api/v1/advisory/policy")
def api_advisory_policy():
    return advisory_policy()


@app.get("/api/v1/advisories")
def api_advisories(
    workspace_id: Annotated[str, Depends(get_workspace_header)],
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[Session, Depends(get_session)],
    limit: int = 100,
):
    _guard(principal, "director", "analyst", "auditor")
    _service(session).get_workspace(workspace_id)
    return [_row(item) for item in list_advisories(session, workspace_id, limit=limit)]


@app.post("/api/v1/advisories", status_code=201)
def api_create_advisory(
    payload: AdvisoryCreate,
    workspace_id: Annotated[str, Depends(get_workspace_header)],
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[Session, Depends(get_session)],
):
    _guard(principal, "director", "analyst")
    _service(session).get_workspace(workspace_id)
    try:
        item = create_advisory(
            session,
            settings,
            workspace_id=workspace_id,
            actor=principal.subject,
            objective=payload.objective,
            recommendation=payload.recommendation,
            rationale=payload.rationale,
            risk_level=payload.risk_level,
            evidence_refs=payload.evidence_refs,
        )
        result = _row(item)
        result["executionAllowed"] = False
        result["requiresHumanDecision"] = True
        return result
    except AdvisoryError as exc:
        raise _service_error(exc) from exc


@app.post("/api/v1/advisories/{advisory_id}/decision")
def api_decide_advisory(
    advisory_id: str,
    payload: AdvisoryDecision,
    workspace_id: Annotated[str, Depends(get_workspace_header)],
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[Session, Depends(get_session)],
):
    _guard(principal, "director")
    _service(session).get_workspace(workspace_id)
    try:
        item = decide_advisory(
            session,
            settings,
            workspace_id=workspace_id,
            actor=principal.subject,
            advisory_id=advisory_id,
            decision=payload.decision,
            note=payload.note,
        )
        result = _row(item)
        result["executionPerformed"] = False
        return result
    except AdvisoryError as exc:
        raise _service_error(exc) from exc
