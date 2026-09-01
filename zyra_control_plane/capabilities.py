"""Machine-readable capability manifests and per-mission grants."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class CapabilityManifest:
    name: str
    kind: str
    capabilities: tuple[str, ...]
    network: bool = False
    writes: bool = False
    external_effects: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MissionGrant:
    profile: str
    allowed: tuple[str, ...]
    network_allowed: bool = False
    writes_allowed: bool = False
    external_effects_allowed: bool = False

    def permits(self, capability: str) -> bool:
        return capability in self.allowed


FDE_LOCAL_CAPABILITIES = (
    "discover-source",
    "record-provenance",
    "inventory-constraints",
    "profile-schema",
    "map-keys",
    "map-lineage",
    "measure-quality",
    "interpret-code",
    "extract-business-logic",
    "map-dependencies",
    "map-ontology",
    "map-standard",
    "record-assumption",
    "propose-contract",
    "generate-transform",
    "write-branch-artifact",
    "version-mapping",
    "reconcile",
    "run-evaluation",
    "check-lineage",
    "diagnose-failure",
    "root-cause",
    "propose-repair",
    "request-decision",
    "record-decision",
    "record-acceptance",
    "check-rollback",
    "check-impact",
    "check-approval",
    "record-tool-use",
    "record-evidence",
    "record-risk",
    "attest-completion",
)


DEFAULT_MANIFESTS = (
    CapabilityManifest("gpt-doug-core", "orchestrator", ("plan", "route", "review", "journal", "checkpoint")),
    CapabilityManifest("zyra", "compiler", ("compile", "requirement-lock", "manifest", "typescript-spec"), writes=True),
    CapabilityManifest("mythos", "model-provider", ("reason", "architect", "review"), network=True),
    CapabilityManifest("ollama", "local-model-provider", ("reason", "code", "review")),
    CapabilityManifest("xunia", "consensus-router", ("route", "consensus", "review"), network=True),
    CapabilityManifest("sandbox", "execution", ("copy-workspace", "run-check", "smoke-test", "artifact-manifest"), writes=True),
    CapabilityManifest("github", "delivery", ("pull-request", "status-check", "merge"), network=True, writes=True, external_effects=True),
    CapabilityManifest("security", "verification", ("lint", "dependency-audit", "sbom", "policy-check", "attest")),
    CapabilityManifest("fde-source-scout", "migration-role", ("discover-source", "record-provenance", "inventory-constraints")),
    CapabilityManifest("fde-schema-cartographer", "migration-role", ("profile-schema", "map-keys", "map-lineage", "measure-quality")),
    CapabilityManifest("fde-code-interpreter", "migration-role", ("interpret-code", "extract-business-logic", "map-dependencies")),
    CapabilityManifest("fde-mapping-engineer", "migration-role", ("map-ontology", "map-standard", "record-assumption", "propose-contract")),
    CapabilityManifest("fde-transform-builder", "migration-role", ("generate-transform", "write-branch-artifact", "version-mapping"), writes=True),
    CapabilityManifest("fde-verifier", "migration-role", ("reconcile", "run-evaluation", "check-lineage", "policy-check")),
    CapabilityManifest("fde-diagnostician", "migration-role", ("diagnose-failure", "root-cause", "propose-repair")),
    CapabilityManifest("fde-sme-gateway", "migration-role", ("request-decision", "record-decision", "record-acceptance"), writes=True),
    CapabilityManifest("fde-release-controller", "migration-role", ("check-rollback", "check-impact", "check-approval", "promote-release"), network=True, writes=True, external_effects=True),
    CapabilityManifest("fde-auditor", "migration-role", ("record-tool-use", "record-evidence", "record-risk", "attest-completion"), writes=True),
)

READ_ONLY = MissionGrant(
    "read-only",
    (
        "plan", "route", "review", "journal", "reason", "architect", "consensus",
        "discover-source", "record-provenance", "inventory-constraints", "profile-schema",
        "map-keys", "map-lineage", "measure-quality", "interpret-code",
        "extract-business-logic", "map-dependencies", "map-ontology", "map-standard",
        "record-assumption", "propose-contract", "reconcile", "run-evaluation",
        "check-lineage", "policy-check", "diagnose-failure", "root-cause", "propose-repair",
        "request-decision", "check-rollback", "check-impact", "check-approval",
    ),
)

WRITE_LOCAL = MissionGrant(
    "write-local",
    (
        "plan", "route", "review", "journal", "checkpoint", "compile", "requirement-lock", "manifest",
        "typescript-spec", "copy-workspace", "run-check", "smoke-test", "artifact-manifest", "lint",
        "dependency-audit", "sbom", "policy-check", "attest",
        *FDE_LOCAL_CAPABILITIES,
    ),
    writes_allowed=True,
)

NETWORK_APPROVED = MissionGrant(
    "network-approved",
    tuple(sorted({cap for item in DEFAULT_MANIFESTS for cap in item.capabilities})),
    network_allowed=True,
    writes_allowed=True,
    external_effects_allowed=True,
)


class CapabilityRegistry:
    def __init__(self, manifests: Iterable[CapabilityManifest] = DEFAULT_MANIFESTS) -> None:
        self._items = {item.name: item for item in manifests}

    def register(self, manifest: CapabilityManifest) -> None:
        self._items[manifest.name] = manifest

    def get(self, name: str) -> CapabilityManifest:
        return self._items[name]

    def all(self) -> list[dict[str, object]]:
        return [self._items[key].to_dict() for key in sorted(self._items)]

    def authorize(self, agent: str, grant: MissionGrant, required: Iterable[str]) -> tuple[bool, tuple[str, ...]]:
        manifest = self.get(agent)
        missing = tuple(
            capability for capability in required
            if capability not in manifest.capabilities or not grant.permits(capability)
        )
        if manifest.network and not grant.network_allowed:
            missing += ("network-boundary",)
        if manifest.writes and not grant.writes_allowed:
            missing += ("write-boundary",)
        if manifest.external_effects and not grant.external_effects_allowed:
            missing += ("external-effect-boundary",)
        return (not missing, missing)

    def snapshot(self, grant: MissionGrant) -> dict[str, object]:
        return {
            "grant": {
                "profile": grant.profile,
                "allowed": list(grant.allowed),
                "network_allowed": grant.network_allowed,
                "writes_allowed": grant.writes_allowed,
                "external_effects_allowed": grant.external_effects_allowed,
            },
            "manifests": self.all(),
        }
