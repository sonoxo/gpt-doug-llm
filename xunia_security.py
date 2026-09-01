"""XUNIA authorized security assessment and penetration-test planner.

Planning and authorization are separated from execution. Commands are represented as
argv arrays, never shell strings. Destructive actions are not supported.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from typing import List, Optional, Sequence, Tuple
from urllib.parse import urlparse

SCHEMA_VERSION = "xunia.security.engagement/v1"
TARGET_TYPES = {"url", "host", "cidr", "path", "image", "cloud"}


class SecurityMode(str, Enum):
    ASSESS = "ASSESS"
    PENTEST = "PENTEST"
    SIMULATE = "SIMULATE"


class ToolRisk(str, Enum):
    PASSIVE = "PASSIVE"
    DISCOVERY = "DISCOVERY"
    SAFE_ACTIVE = "SAFE_ACTIVE"
    LAB_ACTIVE = "LAB_ACTIVE"


@dataclass(frozen=True)
class Target:
    type: str
    value: str

    def normalized(self) -> str:
        raw = self.value.strip()
        if not raw:
            raise ValueError("EMPTY_TARGET")
        if self.type not in TARGET_TYPES:
            raise ValueError("INVALID_TARGET_TYPE")
        if self.type == "url":
            parsed = urlparse(raw)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("INVALID_URL_TARGET")
            path = parsed.path.rstrip("/")
            return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"
        if self.type in {"host", "cidr", "cloud"}:
            return raw.lower()
        return raw


@dataclass(frozen=True)
class Engagement:
    engagement_id: str
    owner: str
    mode: SecurityMode
    starts_at: datetime
    ends_at: datetime
    targets: Tuple[Target, ...]
    allowed_checks: Tuple[str, ...]
    authorization_reference: str
    exclusions: Tuple[Target, ...] = ()
    max_requests_per_second: int = 10
    max_concurrency: int = 4
    destructive_allowed: bool = False
    schema_version: str = SCHEMA_VERSION

    def validate(self, now: Optional[datetime] = None) -> None:
        now = now or datetime.now(timezone.utc)
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("UNSUPPORTED_ENGAGEMENT_SCHEMA")
        if not self.engagement_id.strip() or not self.owner.strip():
            raise ValueError("ENGAGEMENT_IDENTITY_REQUIRED")
        if not self.authorization_reference.strip():
            raise ValueError("AUTHORIZATION_REFERENCE_REQUIRED")
        if not self.targets or not self.allowed_checks:
            raise ValueError("ENGAGEMENT_SCOPE_REQUIRED")
        if self.destructive_allowed:
            raise ValueError("DESTRUCTIVE_ACTIONS_NOT_SUPPORTED")
        if self.max_requests_per_second < 1 or self.max_concurrency < 1:
            raise ValueError("ENGAGEMENT_LIMITS_INVALID")
        if self.starts_at >= self.ends_at:
            raise ValueError("ENGAGEMENT_WINDOW_INVALID")
        if now < self.starts_at or now > self.ends_at:
            raise PermissionError("ENGAGEMENT_OUTSIDE_AUTHORIZED_WINDOW")
        for target in (*self.targets, *self.exclusions):
            target.normalized()


@dataclass(frozen=True)
class ToolAdapter:
    id: str
    check: str
    risk: ToolRisk
    target_types: Tuple[str, ...]
    phases: Tuple[str, ...]

    def supports(self, target: Target) -> bool:
        return target.type in self.target_types

    def command(self, target: Target) -> List[str]:
        if not self.supports(target):
            raise ValueError("TOOL_TARGET_TYPE_NOT_SUPPORTED")
        value = target.normalized()
        if self.id == "nmap":
            host = urlparse(value).hostname if target.type == "url" else value
            if not host:
                raise ValueError("NMAP_TARGET_REQUIRED")
            return ["nmap", "-sV", "--version-light", "--reason", host]
        if self.id == "nuclei":
            return ["nuclei", "-u", value, "-severity", "low,medium,high,critical", "-jsonl"]
        if self.id == "zap-baseline":
            return ["zap-baseline.py", "-t", value, "-J", "zap-report.json"]
        if self.id == "trivy":
            subcommand = "image" if target.type == "image" else "fs"
            return ["trivy", subcommand, "--scanners", "vuln,secret,misconfig", value]
        if self.id == "syft":
            return ["syft", value, "-o", "cyclonedx-json"]
        if self.id == "grype":
            return ["grype", value, "-o", "json"]
        if self.id == "gitleaks":
            return ["gitleaks", "detect", "--source", value, "--report-format", "json"]
        if self.id == "semgrep":
            return ["semgrep", "scan", "--config", "auto", "--json", value]
        if self.id == "osv-scanner":
            return ["osv-scanner", "scan", "source", "-r", value]
        if self.id == "checkov":
            return ["checkov", "-d", value, "-o", "json"]
        if self.id == "prowler":
            return ["prowler", "--output-formats", "json"]
        raise ValueError("UNKNOWN_TOOL_ADAPTER")


TOOL_CATALOG: Tuple[ToolAdapter, ...] = (
    ToolAdapter("nmap", "service.discovery", ToolRisk.DISCOVERY, ("url", "host", "cidr"), ("recon", "assessment")),
    ToolAdapter("nuclei", "web.templates", ToolRisk.SAFE_ACTIVE, ("url",), ("assessment", "validation")),
    ToolAdapter("zap-baseline", "web.baseline", ToolRisk.PASSIVE, ("url",), ("assessment",)),
    ToolAdapter("trivy", "supply-chain.vulnerability", ToolRisk.PASSIVE, ("path", "image"), ("supply-chain",)),
    ToolAdapter("syft", "supply-chain.sbom", ToolRisk.PASSIVE, ("path", "image"), ("supply-chain",)),
    ToolAdapter("grype", "supply-chain.cve", ToolRisk.PASSIVE, ("path", "image"), ("supply-chain",)),
    ToolAdapter("gitleaks", "source.secrets", ToolRisk.PASSIVE, ("path",), ("supply-chain",)),
    ToolAdapter("semgrep", "source.sast", ToolRisk.PASSIVE, ("path",), ("supply-chain",)),
    ToolAdapter("osv-scanner", "dependency.osv", ToolRisk.PASSIVE, ("path",), ("supply-chain",)),
    ToolAdapter("checkov", "iac.misconfiguration", ToolRisk.PASSIVE, ("path",), ("cloud", "supply-chain")),
    ToolAdapter("prowler", "cloud.posture", ToolRisk.PASSIVE, ("cloud",), ("cloud", "assessment")),
)


def _matches(scope: Target, requested: Target) -> bool:
    if scope.type != requested.type:
        return False
    allowed = scope.normalized()
    value = requested.normalized()
    if allowed == value:
        return True
    if scope.type == "url":
        return value.startswith(allowed + "/")
    if scope.type == "host" and allowed.startswith("*."):
        suffix = allowed[1:]
        return value.endswith(suffix) and value != suffix[1:]
    return False


def target_authorized(engagement: Engagement, requested: Target) -> bool:
    if any(_matches(item, requested) for item in engagement.exclusions):
        return False
    return any(_matches(item, requested) for item in engagement.targets)


def _risk_allowed(mode: SecurityMode, risk: ToolRisk) -> bool:
    if mode == SecurityMode.ASSESS:
        return risk in {ToolRisk.PASSIVE, ToolRisk.DISCOVERY}
    if mode == SecurityMode.PENTEST:
        return risk != ToolRisk.LAB_ACTIVE
    return True


@dataclass(frozen=True)
class PlannedStep:
    order: int
    tool: ToolAdapter
    target: Target
    argv: Tuple[str, ...]

    @property
    def evidence_id(self) -> str:
        material = "\0".join((self.tool.id, self.target.normalized(), *self.argv)).encode("utf-8")
        return sha256(material).hexdigest()


@dataclass
class SecurityPlan:
    engagement_id: str
    mode: SecurityMode
    authorization_reference: str
    steps: List[PlannedStep] = field(default_factory=list)
    destructive_actions: str = "DENIED"


class XuniaSecurityPlatform:
    """Plans only explicitly authorized, non-destructive security checks."""

    def __init__(self, catalog: Sequence[ToolAdapter] = TOOL_CATALOG):
        self.catalog = tuple(catalog)

    def plan(self, engagement: Engagement, now: Optional[datetime] = None) -> SecurityPlan:
        engagement.validate(now)
        plan = SecurityPlan(
            engagement_id=engagement.engagement_id,
            mode=engagement.mode,
            authorization_reference=engagement.authorization_reference,
        )
        order = 1
        for target in engagement.targets:
            if not target_authorized(engagement, target):
                continue
            for tool in self.catalog:
                if not tool.supports(target):
                    continue
                if tool.check not in engagement.allowed_checks:
                    continue
                if not _risk_allowed(engagement.mode, tool.risk):
                    continue
                argv = tuple(tool.command(target))
                plan.steps.append(PlannedStep(order, tool, target, argv))
                order += 1
        return plan

    def authorize_step(self, engagement: Engagement, step: PlannedStep, now: Optional[datetime] = None) -> None:
        engagement.validate(now)
        if not target_authorized(engagement, step.target):
            raise PermissionError("TARGET_OUT_OF_SCOPE")
        if not step.tool.supports(step.target):
            raise PermissionError("TOOL_TARGET_TYPE_NOT_AUTHORIZED")
        if step.tool.check not in engagement.allowed_checks:
            raise PermissionError("CHECK_NOT_AUTHORIZED")
        if not _risk_allowed(engagement.mode, step.tool.risk):
            raise PermissionError("RISK_NOT_AUTHORIZED")
        if step.tool.command(step.target) != list(step.argv):
            raise PermissionError("COMMAND_INTEGRITY_CHECK_FAILED")
