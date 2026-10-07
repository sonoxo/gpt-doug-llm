from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

import agency_cloud.godseye_ui as ui


HTML = Path(__file__).resolve().parents[1] / "static" / "godseye.html"


def _client():
    app = FastAPI()
    app.include_router(ui.router)
    return TestClient(app)


def test_godseye_dashboard_route_and_structure():
    response = _client().get("/godseye")
    assert response.status_code == 200
    text = response.text
    for dom_id in [
        "coreState",
        "systemHealth",
        "brainState",
        "warhawkState",
        "zyraState",
        "intelState",
        "complianceState",
        "bioState",
        "planetaryState",
        "policyState",
        "provenanceList",
        "eventLog",
        "queryInput",
        "querySubmit",
        "queryOutput",
    ]:
        assert f'id="{dom_id}"' in text
    assert 'href="/global-intel"' in text
    assert 'href="/global-compliance"' in text
    assert 'href="/bioinformatics-fusion"' in text


def test_dashboard_shell_declares_read_only_boundary():
    text = HTML.read_text(encoding="utf-8")
    assert "READ-ONLY" in text
    assert "NO WEAPON CONTROL" in text
    assert "NO IMPLANT CONTROL" in text


def test_dashboard_live_endpoints_and_safe_rendering():
    text = HTML.read_text(encoding="utf-8")
    assert "/api/v1/godseye/status" in text
    assert "/api/v1/godseye/sources" in text
    assert "/api/v1/planetary/status" in text
    assert "/api/v1/godseye/query" in text
    assert "/ws/v1/events" in text
    assert "new WebSocket" in text
    assert "textContent" in text
    assert "replaceChildren" in text
    assert "document.createElement" in text
    assert "eval(" not in text
    assert "new Function" not in text
    assert "innerHTML" not in text
    assert "shell" not in text.lower()
    assert "terminal" not in text.lower()


def test_dashboard_provenance_uses_text_only_path():
    text = HTML.read_text(encoding="utf-8")
    assert "function renderProvenance" in text
    assert "row.textContent=String(item)" in text.replace(" ", "")
    assert "<img src=x onerror=1>" not in text
