from __future__ import annotations

import hmac
from dataclasses import dataclass

from agency_cloud.config import Settings


@dataclass(frozen=True)
class Principal:
    subject: str
    role: str


class AuthenticationError(RuntimeError):
    pass


class AuthorizationError(RuntimeError):
    pass


def _token_entries(settings: Settings) -> list[tuple[str, Principal]]:
    entries: list[tuple[str, Principal]] = []
    configured = [
        (settings.director_token, Principal("director", "director")),
        (settings.analyst_token, Principal("analyst", "analyst")),
        (settings.auditor_token, Principal("auditor", "auditor")),
        (settings.client_token, Principal("client", "client")),
    ]
    entries.extend((token, principal) for token, principal in configured if token)
    if settings.allow_demo_auth and not settings.production:
        entries.extend(
            [
                ("director-demo", Principal("director-demo", "director")),
                ("analyst-demo", Principal("analyst-demo", "analyst")),
                ("auditor-demo", Principal("auditor-demo", "auditor")),
                ("client-demo", Principal("client-demo", "client")),
            ]
        )
    return entries


def authenticate(settings: Settings, token: str) -> Principal:
    candidate = str(token or "").strip()
    if not candidate:
        raise AuthenticationError("missing bearer token")
    for expected, principal in _token_entries(settings):
        if hmac.compare_digest(candidate, expected):
            return principal
    raise AuthenticationError("invalid bearer token")


def require_role(principal: Principal, *roles: str) -> None:
    if principal.role not in set(roles):
        raise AuthorizationError(
            f"role {principal.role!r} is not cleared for this intelligence action"
        )
