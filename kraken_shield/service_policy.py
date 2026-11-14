"""Glass Onion service perimeter for music and bank *integrations*.

Pure, offline policy evaluation only: no account discovery, credentials,
OAuth, network access, bank API calls, transfers, or rights management.
URLs are checked before a *user-initiated* navigation, not fetched here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from urllib.parse import parse_qsl, urlsplit

# Catalog entries are declared destinations, not claims of connected accounts.
MUSIC_DESTINATIONS: dict[str, frozenset[str]] = {
    "audius": frozenset({"audius.co"}),
    "bandcamp": frozenset({"bandcamp.com", "www.bandcamp.com"}),
    "deezer": frozenset({"deezer.com", "www.deezer.com"}),
    "distrokid": frozenset({"distrokid.com", "www.distrokid.com"}),
    "internet-archive": frozenset({"archive.org", "www.archive.org"}),
    "jamendo": frozenset({"www.jamendo.com", "jamendo.com"}),
    "soundcloud": frozenset({"soundcloud.com", "www.soundcloud.com", "w.soundcloud.com"}),
    "spotify": frozenset({"open.spotify.com", "spotify.com"}),
    "suno": frozenset({"suno.com", "www.suno.com"}),
    "tidal": frozenset({"listen.tidal.com", "tidal.com"}),
    "youtube": frozenset({"www.youtube.com", "youtube.com", "youtu.be"}),
    "youtube-music": frozenset({"music.youtube.com"}),
    "apple-music": frozenset({"music.apple.com"}),
}
_SAFE_LOCAL = frozenset({"status", "inventory", "policy"})
_SAFE_PUBLIC_MUSIC = frozenset({"open_public_link", "read_public_catalog"})
_SENSITIVE_QUERY_KEYS = frozenset({
    "access_token", "id_token", "refresh_token", "token", "api_key",
    "apikey", "key", "password", "passwd", "secret", "client_secret",
    "authorization", "auth", "code", "session", "jwt", "otp", "pin",
    "account", "account_number", "routing", "iban", "ssn", "card",
})
_SECTORS = frozenset({"music", "bank"})


@dataclass(frozen=True)
class ServiceDecision:
    schema: str
    sector: str
    decision: str
    reason_code: str
    review_required: bool
    connected: bool
    executed: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def service_catalog() -> dict[str, object]:
    """Public policy metadata only; no connection/account state is inferred."""
    return {
        "schema": "glass-onion/service-catalog-v1",
        "music_destinations": sorted(MUSIC_DESTINATIONS),
        "banking": "NO_CONNECTED_BANK_ADAPTER",
        "bank_transactions_allowed": False,
        "music_publishing_allowed": False,
        "credentials_stored": False,
        "external_services_controlled": False,
        "scope": "cooperating CL1 service integrations only",
    }


def _decision(sector: str, allowed: bool, reason: str) -> ServiceDecision:
    return ServiceDecision(
        schema="glass-onion/service-decision-v1",
        sector=sector if sector in _SECTORS else "unknown",
        decision="ALLOW" if allowed else "BLOCK",
        reason_code=reason,
        review_required=not allowed,
        connected=False,
        executed=False,
    )


def _safe_public_destination(service: str, raw: str) -> tuple[bool, str]:
    if not isinstance(raw, str) or not raw or len(raw) > 2048:
        return False, "invalid_public_url"
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in raw):
        return False, "invalid_public_url"
    try:
        u = urlsplit(raw)
        if (
            u.scheme != "https" or not u.hostname or u.username is not None
            or u.password is not None or u.port not in (None, 443)
            or "\\" in raw or u.hostname.endswith(".")
        ):
            return False, "unsafe_public_url"
        host = u.hostname.lower()
        if host not in MUSIC_DESTINATIONS[service]:
            return False, "unapproved_music_host"
        for key, _ in parse_qsl(u.query, keep_blank_values=True):
            if key.strip().lower() in _SENSITIVE_QUERY_KEYS:
                return False, "sensitive_query_parameter"
    except (ValueError, KeyError):
        return False, "invalid_public_url"
    return True, "reviewed_public_destination"


def evaluate_service_access(
    sector: str, service: str, operation: str, *, url: str | None = None
) -> ServiceDecision:
    """Default-deny every unregistered service and financial action.

    A successful check permits at most offline policy reads or an operator's
    public music-link navigation. It never grants bank authorization.
    """
    if any(not isinstance(x, str) for x in (sector, service, operation)):
        return _decision("unknown", False, "invalid_input_type")
    sector = sector.strip().lower()
    service = service.strip().lower()
    operation = operation.strip().lower()
    if sector not in _SECTORS:
        return _decision(sector, False, "unknown_sector")
    if operation in _SAFE_LOCAL and url is None:
        return _decision(sector, True, "local_policy_only")
    if sector == "bank":
        return _decision(sector, False, "bank_connector_not_authorized")
    if service not in MUSIC_DESTINATIONS:
        return _decision(sector, False, "unregistered_music_service")
    if operation not in _SAFE_PUBLIC_MUSIC:
        return _decision(sector, False, "music_mutation_requires_operator_review")
    ok, reason = _safe_public_destination(service, url) if url is not None else (False, "public_url_required")
    return _decision(sector, ok, reason)
