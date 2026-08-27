from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from agency_cloud import __version__
from agency_cloud.audit import verify_chain
from agency_cloud.config import Settings, load_settings
from agency_cloud.db import build_engine, build_session_factory, create_schema
from agency_cloud.integrations import (
    IntelligenceIntegrationError,
    glassonion_query,
    glassonion_status,
    live_changes,
    lock_summary,
    ontology_query,
    ontology_status,
)
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
        raise HTTPException(status_code=401, detail=str(exc), headers={"WWW-Authenticate": "Bearer"}) from exc


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


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "service": settings.service_name,
        "version": __version__,
        "legalStatus": "PRIVATE INTELLIGENCE COMPANY — NOT A GOVERNMENT AGENCY",
    }


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
        return _row(_service(session).create_workspace(actor=principal.subject, name=payload.name, slug=payload.slug))
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
        return {"caseId": link.case_id, "intelId": link.intel_id, "attachedBy": link.attached_by}
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
            workspace_id, client_visible_only=principal.role == "client"
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
