"""Governed Defense OSDK capability contract for the XUNIA / GPT-DOUG ecosystem.

Palantir Defense OSDK clients are generated and permissioned inside an authorized
Palantir enrollment. This module deliberately does not invent undocumented API
endpoints or provide ambient operational authority. It exposes the supported
application-domain contract to the local runtime and keeps kinetic targeting /
fires execution outside autonomous local authority.
"""

from os import getenv


SAFE_DOMAINS = (
    "intelligence",
    "mission-planning",
    "order-of-battle",
    "sustainment",
)

RESTRICTED_DOMAINS = (
    "targeting-and-fires",
)


class DefenseOSDKDomain:
    """Immutable-style value object describing one Defense OSDK domain."""

    __slots__ = ("name", "enabled", "execution", "notes")

    def __init__(self, name: str, enabled: bool, execution: str, notes: str) -> None:
        self.name = name
        self.enabled = enabled
        self.execution = execution
        self.notes = notes


class PalantirDefenseOSDK:
    """Local capability registry for an enrollment-generated Defense OSDK client."""

    def __init__(self, foundry: object | None) -> None:
        self.foundry = foundry

    @property
    def configured(self) -> bool:
        raw = getenv("PALANTIR_DEFENSE_OSDK_ENABLED", "").strip().lower()
        return self.foundry is not None and raw in {"1", "true", "yes", "on"}

    def domains(self) -> list[DefenseOSDKDomain]:
        safe_enabled = self.configured
        domains = [
            DefenseOSDKDomain(
                name=name,
                enabled=safe_enabled,
                execution="tenant-generated-client-only",
                notes=(
                    "Available only through an authorized, enrollment-generated OSDK client "
                    "and the invoking identity's Palantir permissions."
                ),
            )
            for name in SAFE_DOMAINS
        ]
        domains.extend(
            DefenseOSDKDomain(
                name=name,
                enabled=False,
                execution="blocked-from-autonomous-local-execution",
                notes=(
                    "Representable for read-only ontology/simulation context, but local autonomous "
                    "weapon-targeting or fires execution is not exposed by this integration."
                ),
            )
            for name in RESTRICTED_DOMAINS
        )
        return domains

    def require_domain(self, name: str) -> DefenseOSDKDomain:
        normalized = name.strip().lower().replace("_", "-")
        for domain in self.domains():
            if domain.name == normalized:
                if not domain.enabled:
                    raise PermissionError(
                        f"Defense OSDK domain '{normalized}' is not enabled for local execution"
                    )
                return domain
        raise ValueError(f"Unknown Defense OSDK domain: {name}")

    def status(self) -> dict[str, object]:
        domains = self.domains()
        return {
            "configured": self.configured,
            "adapter": "authorized tenant-generated Defense OSDK client contract",
            "safe_domains": [domain.name for domain in domains if domain.enabled],
            "restricted_domains": [domain.name for domain in domains if not domain.enabled],
            "authority": (
                "Foundry/Gotham identity, Ontology permissions, OSDK application scopes, "
                "markings, local policy and human approval"
            ),
            "truth_boundary": (
                "Configuration does not imply Palantir licensing, Defense OSDK entitlement, "
                "government affiliation, mission authority or weapons-release authority."
            ),
        }
