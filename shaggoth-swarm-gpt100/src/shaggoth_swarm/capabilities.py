from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Risk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class CapabilitySpec:
    name: str
    description: str
    risk: Risk
    requires_scope: bool = False
    audit_required: bool = True


CAPABILITY_CATALOG: tuple[CapabilitySpec, ...] = (
    CapabilitySpec("reason", "Reason over supplied context.", Risk.LOW, audit_required=False),
    CapabilitySpec("summarize", "Summarize supplied or retrieved content.", Risk.LOW, audit_required=False),
    CapabilitySpec("classify", "Classify supplied or retrieved content.", Risk.LOW, audit_required=False),
    CapabilitySpec("plan", "Create bounded execution plans.", Risk.LOW, audit_required=False),
    CapabilitySpec("model.invoke", "Invoke an explicitly configured model endpoint.", Risk.MEDIUM, True),
    CapabilitySpec("fs.read", "Read files inside an approved workspace.", Risk.MEDIUM, True),
    CapabilitySpec("fs.write", "Create or update files inside an approved workspace.", Risk.MEDIUM, True),
    CapabilitySpec("process.run", "Run commands from an explicit executable/argument allowlist.", Risk.HIGH, True),
    CapabilitySpec("http.get", "GET from explicitly allowlisted endpoints.", Risk.MEDIUM, True),
    CapabilitySpec("http.write", "POST/PUT/PATCH/DELETE only to explicitly allowlisted authorized endpoints.", Risk.HIGH, True),
    CapabilitySpec("git.read", "Inspect commits, branches, diffs, and repository metadata.", Risk.MEDIUM, True),
    CapabilitySpec("git.write", "Create branches, commits, tags, or pull requests in approved repositories.", Risk.HIGH, True),
    CapabilitySpec("github.read", "Read approved GitHub repositories, issues, pull requests, and workflows.", Risk.MEDIUM, True),
    CapabilitySpec("github.write", "Modify approved GitHub repositories through authenticated APIs.", Risk.HIGH, True),
    CapabilitySpec("database.read", "Query approved databases with scoped credentials.", Risk.MEDIUM, True),
    CapabilitySpec("database.write", "Write to approved databases with scoped credentials.", Risk.HIGH, True),
    CapabilitySpec("object_store.read", "Read approved object/blob storage.", Risk.MEDIUM, True),
    CapabilitySpec("object_store.write", "Write approved object/blob storage.", Risk.HIGH, True),
    CapabilitySpec("queue.consume", "Consume from approved queues/topics.", Risk.MEDIUM, True),
    CapabilitySpec("queue.publish", "Publish to approved queues/topics.", Risk.HIGH, True),
    CapabilitySpec("secrets.use", "Use named secret handles without revealing their plaintext values.", Risk.HIGH, True),
    CapabilitySpec("schedule.manage", "Create or modify bounded scheduled tasks in an approved scheduler.", Risk.HIGH, True),
    CapabilitySpec("email.read", "Read approved mailbox content.", Risk.MEDIUM, True),
    CapabilitySpec("email.send", "Send mail from an approved account.", Risk.HIGH, True),
    CapabilitySpec("calendar.read", "Read approved calendar content.", Risk.MEDIUM, True),
    CapabilitySpec("calendar.write", "Create or modify approved calendar events.", Risk.HIGH, True),
    CapabilitySpec("telemetry.read", "Read approved logs, metrics, and traces.", Risk.MEDIUM, True),
    CapabilitySpec("telemetry.write", "Emit logs, metrics, traces, and audit events.", Risk.MEDIUM, True),
    CapabilitySpec("artifact.create", "Create documents, archives, reports, and build artifacts in approved storage.", Risk.MEDIUM, True),
    CapabilitySpec("artifact.publish", "Publish artifacts to approved destinations.", Risk.HIGH, True),
    CapabilitySpec("web.search", "Search public web sources through an approved provider.", Risk.MEDIUM, True),
)

CAPABILITIES_BY_NAME = {spec.name: spec for spec in CAPABILITY_CATALOG}
ALL_SUPPORTED_CAPABILITIES = frozenset(CAPABILITIES_BY_NAME)

PROFILE_REASONING = frozenset({"reason", "summarize", "classify", "plan"})
PROFILE_LOCAL_DEV = PROFILE_REASONING | frozenset({
    "model.invoke",
    "fs.read",
    "fs.write",
    "process.run",
    "git.read",
    "git.write",
    "artifact.create",
    "telemetry.write",
})
PROFILE_INTEGRATIONS = PROFILE_REASONING | frozenset({
    "model.invoke",
    "http.get",
    "http.write",
    "github.read",
    "github.write",
    "database.read",
    "database.write",
    "object_store.read",
    "object_store.write",
    "queue.consume",
    "queue.publish",
    "secrets.use",
    "schedule.manage",
    "email.read",
    "email.send",
    "calendar.read",
    "calendar.write",
    "telemetry.read",
    "telemetry.write",
    "artifact.create",
    "artifact.publish",
    "web.search",
})
PROFILE_FULL_AUTHORIZED = ALL_SUPPORTED_CAPABILITIES

PROFILES: dict[str, frozenset[str]] = {
    "reasoning": PROFILE_REASONING,
    "local-dev": PROFILE_LOCAL_DEV,
    "integrations": PROFILE_INTEGRATIONS,
    "full-authorized": PROFILE_FULL_AUTHORIZED,
}
