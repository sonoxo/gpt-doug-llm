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
