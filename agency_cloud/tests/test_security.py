from pathlib import Path

import pytest

from agency_cloud.config import Settings
from agency_cloud.security import AuthorizationError, authenticate, require_role


def settings() -> Settings:
    return Settings(
        service_name="ZYRA Intelligence Cloud Test",
        environment="test",
        database_url="sqlite+pysqlite:///:memory:",
        audit_key="audit",
        director_token="director-token",
        analyst_token="analyst-token",
        auditor_token="auditor-token",
        client_token="client-token",
        allow_demo_auth=False,
        repo_root=Path("."),
        default_workspace_name="Test",
    )


def test_roles_are_explicit_and_bounded():
    cfg = settings()
    analyst = authenticate(cfg, "analyst-token")
    client = authenticate(cfg, "client-token")

    require_role(analyst, "director", "analyst")
    with pytest.raises(AuthorizationError):
        require_role(client, "director", "analyst")
