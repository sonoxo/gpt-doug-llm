from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    service_name: str
    environment: str
    database_url: str
    audit_key: str
    director_token: str
    analyst_token: str
    auditor_token: str
    client_token: str
    allow_demo_auth: bool
    repo_root: Path
    default_workspace_name: str

    @property
    def production(self) -> bool:
        return self.environment.lower() in {"prod", "production"}


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    repo_root = Path(__file__).resolve().parents[1]
    data_dir = repo_root / "agency_cloud" / ".data"
    data_dir.mkdir(parents=True, exist_ok=True)

    settings = Settings(
        service_name=os.getenv("AGENCY_SERVICE_NAME", "ZYRA Intelligence Cloud"),
        environment=os.getenv("AGENCY_ENVIRONMENT", "development"),
        database_url=os.getenv(
            "AGENCY_DATABASE_URL",
            f"sqlite+pysqlite:///{(data_dir / 'agency.db').as_posix()}",
        ),
        audit_key=os.getenv("AGENCY_AUDIT_KEY", ""),
        director_token=os.getenv("AGENCY_DIRECTOR_TOKEN", ""),
        analyst_token=os.getenv("AGENCY_ANALYST_TOKEN", ""),
        auditor_token=os.getenv("AGENCY_AUDITOR_TOKEN", ""),
        client_token=os.getenv("AGENCY_CLIENT_TOKEN", ""),
        allow_demo_auth=_truthy(os.getenv("AGENCY_ALLOW_DEMO_AUTH")),
        repo_root=repo_root,
        default_workspace_name=os.getenv("AGENCY_DEFAULT_WORKSPACE", "ZYRA Command"),
    )

    if settings.production:
        missing = [
            name
            for name, value in {
                "AGENCY_AUDIT_KEY": settings.audit_key,
                "AGENCY_DIRECTOR_TOKEN": settings.director_token,
                "AGENCY_ANALYST_TOKEN": settings.analyst_token,
                "AGENCY_AUDITOR_TOKEN": settings.auditor_token,
                "AGENCY_CLIENT_TOKEN": settings.client_token,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(
                "production intelligence cloud requires secrets: " + ", ".join(missing)
            )
        if settings.allow_demo_auth:
            raise RuntimeError("AGENCY_ALLOW_DEMO_AUTH must be disabled in production")

    return settings
