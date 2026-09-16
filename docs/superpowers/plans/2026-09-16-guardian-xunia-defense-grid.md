# GUARDIAN / XUNIA Defense Grid Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, defensive GUARDIAN/XUNIA pipeline that turns authorized observations into hazard assessments, simulation-gated protective proposals, auditable authorization decisions, privacy-preserving XUNIA exports, and append-only defense receipts.

**Architecture:** Implement a small Python package under `guardian/defense_grid` using standard-library dataclasses/enums, explicit JSON policy files, a deny-by-default policy evaluator, an allow-listed action registry, a synthetic/inert simulation layer, and a privacy-preserving XUNIA exporter. The implementation extends the existing Safety Shield GREEN/AMBER/RED/BLACK model and infrastructure-resilience contract; it does not add weapon-control logic, external counter-intrusion, or live mutating connectors.

**Tech Stack:** Python 3.9+, dataclasses, enum, json, hashlib, pathlib, pytest, GitHub Actions, RDF/Turtle ontology text, GeoJSON-compatible dictionaries.

**Spec:** `docs/superpowers/specs/2026-09-16-guardian-xunia-defense-grid-design.md`

## Global Constraints

- Python floor remains `>=3.9`.
- Unknown identity, provenance, scope, authorization, or integrity fails closed.
- External dispatch remains disabled by default.
- A model score alone cannot authorize action.
- Consequential mutation requires a successful simulation receipt.
- Material actions require a valid, unexpired human authorization grant.
- Mutating actions require rollback metadata unless explicitly classified non-mutating.
- Public XUNIA export suppresses precise human location and personal/biometric telemetry by default.
- Unsupported attribution remains hypothesis, not fact.
- The executable action registry must not contain weapon target selection, strike/engagement recommendation, fire-control, guidance/interceptor command generation, initiation/detonation control, explosive/fragmentation design, external exploitation, counter-hacking, or destructive third-party actions.
- This plan intentionally stops at dry-run/synthetic execution. Any future live defensive adapter for owned infrastructure requires a separate environment-specific authorization/specification pass after this plan is green.

## Scope Check

GUARDIAN SHIELD, XUNIA Defense Grid, and GUARDIAN Range share the same domain models, policy evaluator, registry, and evidence receipts. They are therefore implemented in one sequential plan rather than three disconnected plans. Each task below ends in an independently testable deliverable.

## File Structure

Create:

```text
guardian/
  __init__.py
  defense_grid/
    __init__.py
    models.py
    policy.py
    registry.py
    receipts.py
    simulation.py
    xunia_export.py
    schemas/
      sensor-observation.schema.json
      hazard-assessment.schema.json
      response-proposal.schema.json
      simulation-receipt.schema.json
      authorization-grant.schema.json
      defense-receipt.schema.json
      xunia-defense-layer.schema.json
    policies/
      authorized-boundary.json
      protective-actions.json
      physical-hazard-policy.json
    fixtures/
      synthetic-observations.json
      synthetic-hazards.json

safety-shield/ontology/guardian-defense-grid.ttl
scripts/validate_guardian_defense.py
tests/guardian/test_models.py
tests/guardian/test_policy.py
tests/guardian/test_registry.py
tests/guardian/test_receipts.py
tests/guardian/test_simulation.py
tests/guardian/test_xunia_export.py
tests/guardian/test_validator.py
.github/workflows/guardian-defense-gate.yml
docs/GUARDIAN_XUNIA_DEFENSE_GRID.md
```

Modify:

```text
pyproject.toml
README.md
```

---

### Task 1: Package and Domain Models

**Files:**
- Create: `guardian/__init__.py`
- Create: `guardian/defense_grid/__init__.py`
- Create: `guardian/defense_grid/models.py`
- Modify: `pyproject.toml`
- Test: `tests/guardian/test_models.py`

**Interfaces:**
- Consumes: no new internal interfaces.
- Produces: `SensorObservation`, `HazardAssessment`, `ResponseProposal`, `SimulationReceipt`, `AuthorizationGrant`, `DefenseReceipt`, and enums used by every later task.

- [ ] **Step 1: Write the failing model tests**

```python
# tests/guardian/test_models.py
from datetime import datetime, timezone

import pytest

from guardian.defense_grid.models import (
    AttributionStatus,
    FactOrInference,
    GuardianState,
    Impact,
    ProvenanceStatus,
    SensorObservation,
)


def test_sensor_observation_accepts_verified_fact():
    observed = SensorObservation(
        observation_id="obs-1",
        source_id="sensor-a",
        source_type="synthetic",
        observed_at="2026-09-16T06:00:00Z",
        received_at="2026-09-16T06:00:01Z",
        payload_hash="a" * 64,
        provenance_status=ProvenanceStatus.VERIFIED,
        confidence=0.92,
        scope_id="lab",
        fact_or_inference=FactOrInference.FACT,
        geometry={"type": "Point", "coordinates": [-77.43, 37.54]},
        location_precision_class="COARSE_ASSET",
    )
    assert observed.confidence == 0.92
    assert observed.provenance_status is ProvenanceStatus.VERIFIED


def test_sensor_observation_rejects_invalid_confidence():
    with pytest.raises(ValueError, match="confidence"):
        SensorObservation(
            observation_id="obs-2",
            source_id="sensor-a",
            source_type="synthetic",
            observed_at="2026-09-16T06:00:00Z",
            received_at="2026-09-16T06:00:01Z",
            payload_hash="b" * 64,
            provenance_status=ProvenanceStatus.VERIFIED,
            confidence=1.2,
            scope_id="lab",
            fact_or_inference=FactOrInference.FACT,
        )


def test_sensor_observation_rejects_non_sha256_hash():
    with pytest.raises(ValueError, match="payload_hash"):
        SensorObservation(
            observation_id="obs-3",
            source_id="sensor-a",
            source_type="synthetic",
            observed_at="2026-09-16T06:00:00Z",
            received_at="2026-09-16T06:00:01Z",
            payload_hash="not-a-sha256",
            provenance_status=ProvenanceStatus.VERIFIED,
            confidence=0.5,
            scope_id="lab",
            fact_or_inference=FactOrInference.FACT,
        )
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run:

```bash
pytest tests/guardian/test_models.py -v
```

Expected: FAIL during import because `guardian.defense_grid.models` does not exist.

- [ ] **Step 3: Implement the minimal domain model module**

```python
# guardian/defense_grid/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class GuardianState(str, Enum):
    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"
    BLACK = "BLACK"


class ProvenanceStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIAL = "PARTIAL"
    UNVERIFIED = "UNVERIFIED"
    REJECTED = "REJECTED"


class FactOrInference(str, Enum):
    FACT = "FACT"
    INFERENCE = "INFERENCE"


class Impact(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AttributionStatus(str, Enum):
    NONE = "NONE"
    HYPOTHESIS = "HYPOTHESIS"
    VERIFIED_EXTERNAL_SOURCE = "VERIFIED_EXTERNAL_SOURCE"


class ExecutionStatus(str, Enum):
    ALLOWED = "ALLOWED"
    DENIED = "DENIED"
    FAILED = "FAILED"
    SUCCEEDED = "SUCCEEDED"
    ROLLED_BACK = "ROLLED_BACK"


class ValidationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_RUN = "NOT_RUN"


class LiveState(str, Enum):
    LIVE = "LIVE"
    DELAYED = "DELAYED"
    RECONSTRUCTED = "RECONSTRUCTED"
    MODELED = "MODELED"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"


def _validate_confidence(value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError("confidence must be between 0 and 1")


def _validate_sha256(value: str) -> None:
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value.lower()):
        raise ValueError("payload_hash must be a lowercase-compatible SHA-256 hex digest")


@dataclass(frozen=True)
class SensorObservation:
    observation_id: str
    source_id: str
    source_type: str
    observed_at: str
    received_at: str
    payload_hash: str
    provenance_status: ProvenanceStatus
    confidence: float
    scope_id: str
    fact_or_inference: FactOrInference
    geometry: Optional[Dict[str, Any]] = None
    location_precision_class: Optional[str] = None
    personal_telemetry: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        _validate_confidence(self.confidence)
        _validate_sha256(self.payload_hash)


@dataclass(frozen=True)
class HazardAssessment:
    assessment_id: str
    observation_ids: List[str]
    hazard_class: str
    impact: Impact
    likelihood: float
    state: GuardianState
    attribution_status: AttributionStatus
    rationale: str

    def __post_init__(self) -> None:
        _validate_confidence(self.likelihood)


@dataclass(frozen=True)
class ResponseProposal:
    proposal_id: str
    assessment_id: str
    action_class: str
    target_resource_id: str
    authorized_boundary_id: str
    material_action: bool
    simulation_required: bool
    simulation_receipt_id: Optional[str]
    rollback_plan_id: Optional[str]
    human_approval_required: bool
    expires_at: str


@dataclass(frozen=True)
class SimulationReceipt:
    receipt_id: str
    proposal_id: str
    succeeded: bool
    simulated_at: str
    evidence_refs: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class AuthorizationGrant:
    grant_id: str
    proposal_id: str
    approver_identity: str
    scope_id: str
    approved_action_class: str
    approved_target_resource_id: str
    issued_at: str
    expires_at: str


@dataclass(frozen=True)
class DefenseReceipt:
    receipt_id: str
    proposal_id: str
    grant_id: Optional[str]
    executed: bool
    execution_status: ExecutionStatus
    started_at: str
    completed_at: str
    evidence_refs: List[str]
    post_action_validation: ValidationStatus
    rollback_receipt_id: Optional[str] = None
```

Create empty package markers:

```python
# guardian/__init__.py
"""GUARDIAN defensive systems package."""
```

```python
# guardian/defense_grid/__init__.py
"""Human-governed GUARDIAN/XUNIA defensive control plane."""
```

Modify `pyproject.toml` package list without restructuring setuptools:

```toml
[tool.setuptools]
packages = ["agents", "web", "workers", "tests", "models", "guardian", "guardian.defense_grid"]
```

- [ ] **Step 4: Run the focused tests and verify pass**

Run:

```bash
pytest tests/guardian/test_models.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit the model layer**

```bash
git add guardian/__init__.py guardian/defense_grid/__init__.py guardian/defense_grid/models.py tests/guardian/test_models.py pyproject.toml
git commit -m "feat: add guardian defense domain models"
```

---

### Task 2: Authorized-Boundary Policy and Safe Action Registry

**Files:**
- Create: `guardian/defense_grid/policies/authorized-boundary.json`
- Create: `guardian/defense_grid/policies/protective-actions.json`
- Create: `guardian/defense_grid/policies/physical-hazard-policy.json`
- Create: `guardian/defense_grid/registry.py`
- Create: `guardian/defense_grid/policy.py`
- Test: `tests/guardian/test_registry.py`
- Test: `tests/guardian/test_policy.py`

**Interfaces:**
- Consumes: `ResponseProposal`, `SimulationReceipt`, `AuthorizationGrant`, `ProvenanceStatus` from Task 1.
- Produces: `ActionRegistry`, `PolicyDecision`, and `evaluate_proposal(...)` for receipts, simulation, and CI validation.

- [ ] **Step 1: Write registry tests that reject prohibited semantics**

```python
# tests/guardian/test_registry.py
import pytest

from guardian.defense_grid.registry import ActionRegistry, RegistryError


def test_default_registry_contains_only_protective_actions():
    registry = ActionRegistry.default()
    assert "isolate_managed_workload" in registry.action_names
    assert "revoke_owned_session" in registry.action_names
    assert "preserve_incident_evidence" in registry.action_names


def test_registry_rejects_weapon_control_semantics():
    registry = ActionRegistry.empty()
    with pytest.raises(RegistryError):
        registry.register("fire_control_solution", mutating=True, material=True)


def test_registry_rejects_external_counter_intrusion_semantics():
    registry = ActionRegistry.empty()
    with pytest.raises(RegistryError):
        registry.register("exploit_external_host", mutating=True, material=True)
```

- [ ] **Step 2: Write policy tests for fail-closed behavior**

```python
# tests/guardian/test_policy.py
from guardian.defense_grid.models import AuthorizationGrant, ResponseProposal, SimulationReceipt
from guardian.defense_grid.policy import evaluate_proposal
from guardian.defense_grid.registry import ActionRegistry


def proposal(**overrides):
    data = dict(
        proposal_id="proposal-1",
        assessment_id="assessment-1",
        action_class="isolate_managed_workload",
        target_resource_id="asset-1",
        authorized_boundary_id="lab",
        material_action=True,
        simulation_required=True,
        simulation_receipt_id="sim-1",
        rollback_plan_id="rollback-1",
        human_approval_required=True,
        expires_at="2099-01-01T00:00:00Z",
    )
    data.update(overrides)
    return ResponseProposal(**data)


def test_unknown_boundary_is_denied():
    decision = evaluate_proposal(
        proposal(),
        registry=ActionRegistry.default(),
        authorized_boundaries={"prod"},
        simulation_receipt=SimulationReceipt("sim-1", "proposal-1", True, "2026-09-16T06:00:00Z"),
        authorization_grant=None,
        now="2026-09-16T06:00:01Z",
    )
    assert decision.allowed is False
    assert decision.reason == "unknown authorized boundary"


def test_material_action_requires_human_grant():
    decision = evaluate_proposal(
        proposal(),
        registry=ActionRegistry.default(),
        authorized_boundaries={"lab"},
        simulation_receipt=SimulationReceipt("sim-1", "proposal-1", True, "2026-09-16T06:00:00Z"),
        authorization_grant=None,
        now="2026-09-16T06:00:01Z",
    )
    assert decision.allowed is False
    assert decision.reason == "human authorization required"


def test_material_action_allowed_with_matching_grant():
    grant = AuthorizationGrant(
        grant_id="grant-1",
        proposal_id="proposal-1",
        approver_identity="operator-1",
        scope_id="lab",
        approved_action_class="isolate_managed_workload",
        approved_target_resource_id="asset-1",
        issued_at="2026-09-16T05:59:00Z",
        expires_at="2099-01-01T00:00:00Z",
    )
    decision = evaluate_proposal(
        proposal(),
        registry=ActionRegistry.default(),
        authorized_boundaries={"lab"},
        simulation_receipt=SimulationReceipt("sim-1", "proposal-1", True, "2026-09-16T06:00:00Z"),
        authorization_grant=grant,
        now="2026-09-16T06:00:01Z",
    )
    assert decision.allowed is True
```

- [ ] **Step 3: Run policy/registry tests and verify failure**

Run:

```bash
pytest tests/guardian/test_registry.py tests/guardian/test_policy.py -v
```

Expected: FAIL because `registry.py` and `policy.py` do not exist.

- [ ] **Step 4: Create the explicit JSON policy files**

`guardian/defense_grid/policies/authorized-boundary.json`:

```json
{
  "schema": "guardian.authorized-boundary.v1",
  "default": "deny",
  "external_dispatch": "disabled",
  "require_known_scope": true,
  "require_human_approval_for_material_actions": true,
  "require_simulation_for_consequential_mutation": true,
  "require_rollback_for_mutation": true
}
```

`guardian/defense_grid/policies/protective-actions.json`:

```json
{
  "schema": "guardian.protective-actions.v1",
  "actions": [
    {"name": "isolate_managed_workload", "mutating": true, "material": true},
    {"name": "revoke_owned_session", "mutating": true, "material": true},
    {"name": "rotate_owned_secret", "mutating": true, "material": true},
    {"name": "apply_owned_firewall_deny", "mutating": true, "material": true},
    {"name": "rate_limit_owned_service", "mutating": true, "material": true},
    {"name": "disable_owned_service", "mutating": true, "material": true},
    {"name": "quarantine_managed_file", "mutating": true, "material": true},
    {"name": "sandbox_suspicious_input", "mutating": false, "material": false},
    {"name": "activate_internal_deception", "mutating": true, "material": true},
    {"name": "preserve_incident_evidence", "mutating": false, "material": false},
    {"name": "failover_owned_service", "mutating": true, "material": true},
    {"name": "restore_verified_checkpoint", "mutating": true, "material": true},
    {"name": "notify_operator", "mutating": false, "material": false},
    {"name": "trigger_safety_procedure", "mutating": false, "material": true}
  ]
}
```

`guardian/defense_grid/policies/physical-hazard-policy.json`:

```json
{
  "schema": "guardian.physical-hazard-policy.v1",
  "mode": "DEFENSIVE_HAZARD_AWARENESS",
  "allowed_outputs": [
    "observe",
    "correlate",
    "alert",
    "map_hazard",
    "preserve_evidence",
    "recommend_protective_action",
    "trigger_safety_procedure"
  ],
  "prohibited_outputs": [
    "weapon_target_selection",
    "strike_recommendation",
    "fire_control",
    "guidance_command",
    "initiation_control",
    "explosive_design",
    "fragmentation_design",
    "external_counter_intrusion"
  ]
}
```

- [ ] **Step 5: Implement registry and policy evaluator**

```python
# guardian/defense_grid/registry.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Set


class RegistryError(ValueError):
    pass


PROHIBITED_TOKENS = {
    "target_selection",
    "strike_recommendation",
    "fire_control",
    "guidance",
    "interceptor_command",
    "initiation",
    "detonation",
    "explosive_design",
    "fragmentation_design",
    "exploit_external",
    "counter_hack",
    "counter_intrusion",
}


@dataclass(frozen=True)
class ActionDefinition:
    name: str
    mutating: bool
    material: bool


class ActionRegistry:
    def __init__(self) -> None:
        self._actions: Dict[str, ActionDefinition] = {}

    @classmethod
    def empty(cls) -> "ActionRegistry":
        return cls()

    @classmethod
    def default(cls) -> "ActionRegistry":
        registry = cls()
        for name, mutating, material in (
            ("isolate_managed_workload", True, True),
            ("revoke_owned_session", True, True),
            ("rotate_owned_secret", True, True),
            ("apply_owned_firewall_deny", True, True),
            ("rate_limit_owned_service", True, True),
            ("disable_owned_service", True, True),
            ("quarantine_managed_file", True, True),
            ("sandbox_suspicious_input", False, False),
            ("activate_internal_deception", True, True),
            ("preserve_incident_evidence", False, False),
            ("failover_owned_service", True, True),
            ("restore_verified_checkpoint", True, True),
            ("notify_operator", False, False),
            ("trigger_safety_procedure", False, True),
        ):
            registry.register(name, mutating=mutating, material=material)
        return registry

    @property
    def action_names(self) -> Set[str]:
        return set(self._actions)

    def get(self, name: str) -> ActionDefinition:
        if name not in self._actions:
            raise RegistryError(f"unregistered action: {name}")
        return self._actions[name]

    def register(self, name: str, *, mutating: bool, material: bool) -> None:
        lowered = name.lower()
        if any(token in lowered for token in PROHIBITED_TOKENS):
            raise RegistryError(f"prohibited action semantics: {name}")
        self._actions[name] = ActionDefinition(name, mutating, material)
```

```python
# guardian/defense_grid/policy.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Set

from .models import AuthorizationGrant, ResponseProposal, SimulationReceipt
from .registry import ActionRegistry, RegistryError


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str


def _parse_rfc3339(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def evaluate_proposal(
    proposal: ResponseProposal,
    *,
    registry: ActionRegistry,
    authorized_boundaries: Set[str],
    simulation_receipt: Optional[SimulationReceipt],
    authorization_grant: Optional[AuthorizationGrant],
    now: str,
) -> PolicyDecision:
    try:
        action = registry.get(proposal.action_class)
    except RegistryError:
        return PolicyDecision(False, "unregistered action")

    if proposal.authorized_boundary_id not in authorized_boundaries:
        return PolicyDecision(False, "unknown authorized boundary")
    if _parse_rfc3339(proposal.expires_at) <= _parse_rfc3339(now):
        return PolicyDecision(False, "proposal expired")
    if action.mutating and not proposal.rollback_plan_id:
        return PolicyDecision(False, "rollback plan required")
    if proposal.simulation_required:
        if simulation_receipt is None or not simulation_receipt.succeeded:
            return PolicyDecision(False, "successful simulation required")
        if simulation_receipt.proposal_id != proposal.proposal_id:
            return PolicyDecision(False, "simulation receipt mismatch")
    if proposal.material_action or action.material or proposal.human_approval_required:
        if authorization_grant is None:
            return PolicyDecision(False, "human authorization required")
        if authorization_grant.proposal_id != proposal.proposal_id:
            return PolicyDecision(False, "authorization proposal mismatch")
        if authorization_grant.scope_id != proposal.authorized_boundary_id:
            return PolicyDecision(False, "authorization scope mismatch")
        if authorization_grant.approved_action_class != proposal.action_class:
            return PolicyDecision(False, "authorization action mismatch")
        if authorization_grant.approved_target_resource_id != proposal.target_resource_id:
            return PolicyDecision(False, "authorization target mismatch")
        if _parse_rfc3339(authorization_grant.expires_at) <= _parse_rfc3339(now):
            return PolicyDecision(False, "authorization expired")
    return PolicyDecision(True, "allowed")
```

- [ ] **Step 6: Run policy and registry tests**

Run:

```bash
pytest tests/guardian/test_registry.py tests/guardian/test_policy.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit policy/registry layer**

```bash
git add guardian/defense_grid/policies guardian/defense_grid/registry.py guardian/defense_grid/policy.py tests/guardian/test_registry.py tests/guardian/test_policy.py
git commit -m "feat: enforce guardian authorized-boundary policy"
```

---

### Task 3: Append-Only Evidence Receipts

**Files:**
- Create: `guardian/defense_grid/receipts.py`
- Test: `tests/guardian/test_receipts.py`

**Interfaces:**
- Consumes: `DefenseReceipt`, `ExecutionStatus`, `ValidationStatus` from Task 1 and `PolicyDecision` from Task 2.
- Produces: `AppendOnlyReceiptStore.append(...)`, `read_all()`, and `receipt_from_decision(...)`.

- [ ] **Step 1: Write receipt-store tests**

```python
# tests/guardian/test_receipts.py
import json

from guardian.defense_grid.models import ExecutionStatus, ValidationStatus
from guardian.defense_grid.receipts import AppendOnlyReceiptStore, receipt_from_decision
from guardian.defense_grid.policy import PolicyDecision


def test_denial_is_written_as_append_only_receipt(tmp_path):
    path = tmp_path / "receipts.jsonl"
    store = AppendOnlyReceiptStore(path)
    receipt = receipt_from_decision(
        receipt_id="r-1",
        proposal_id="p-1",
        decision=PolicyDecision(False, "unknown authorized boundary"),
        started_at="2026-09-16T06:00:00Z",
        completed_at="2026-09-16T06:00:01Z",
        evidence_refs=["obs-1"],
    )
    store.append(receipt)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert rows[0]["execution_status"] == "DENIED"
    assert rows[0]["executed"] is False


def test_append_never_rewrites_previous_receipts(tmp_path):
    path = tmp_path / "receipts.jsonl"
    store = AppendOnlyReceiptStore(path)
    first = receipt_from_decision("r-1", "p-1", PolicyDecision(False, "denied"), "a", "b", [])
    second = receipt_from_decision("r-2", "p-2", PolicyDecision(False, "denied"), "c", "d", [])
    store.append(first)
    before = path.read_text()
    store.append(second)
    assert path.read_text().startswith(before)
    assert len(store.read_all()) == 2
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/guardian/test_receipts.py -v
```

Expected: FAIL because `receipts.py` does not exist.

- [ ] **Step 3: Implement JSONL append-only storage and denial receipts**

```python
# guardian/defense_grid/receipts.py
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import List

from .models import DefenseReceipt, ExecutionStatus, ValidationStatus
from .policy import PolicyDecision


class AppendOnlyReceiptStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def append(self, receipt: DefenseReceipt) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(receipt)
        payload["execution_status"] = receipt.execution_status.value
        payload["post_action_validation"] = receipt.post_action_validation.value
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    def read_all(self) -> List[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line]


def receipt_from_decision(
    receipt_id: str,
    proposal_id: str,
    decision: PolicyDecision,
    started_at: str,
    completed_at: str,
    evidence_refs: List[str],
) -> DefenseReceipt:
    return DefenseReceipt(
        receipt_id=receipt_id,
        proposal_id=proposal_id,
        grant_id=None,
        executed=False,
        execution_status=ExecutionStatus.ALLOWED if decision.allowed else ExecutionStatus.DENIED,
        started_at=started_at,
        completed_at=completed_at,
        evidence_refs=evidence_refs,
        post_action_validation=ValidationStatus.NOT_RUN,
    )
```

- [ ] **Step 4: Run receipt tests**

Run:

```bash
pytest tests/guardian/test_receipts.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit append-only receipts**

```bash
git add guardian/defense_grid/receipts.py tests/guardian/test_receipts.py
git commit -m "feat: add append-only guardian defense receipts"
```

---

### Task 4: GUARDIAN Range Simulation

**Files:**
- Create: `guardian/defense_grid/simulation.py`
- Create: `guardian/defense_grid/fixtures/synthetic-observations.json`
- Create: `guardian/defense_grid/fixtures/synthetic-hazards.json`
- Test: `tests/guardian/test_simulation.py`

**Interfaces:**
- Consumes: `ResponseProposal`, `SimulationReceipt`, `ActionRegistry`.
- Produces: `simulate_proposal(...)` and `load_synthetic_scenarios(...)`.

- [ ] **Step 1: Write inert simulation tests**

```python
# tests/guardian/test_simulation.py
import json

from guardian.defense_grid.models import ResponseProposal
from guardian.defense_grid.registry import ActionRegistry
from guardian.defense_grid.simulation import simulate_proposal


def test_safe_registered_action_generates_successful_simulation_receipt():
    proposal = ResponseProposal(
        proposal_id="p-1",
        assessment_id="a-1",
        action_class="preserve_incident_evidence",
        target_resource_id="asset-1",
        authorized_boundary_id="lab",
        material_action=False,
        simulation_required=True,
        simulation_receipt_id=None,
        rollback_plan_id=None,
        human_approval_required=False,
        expires_at="2099-01-01T00:00:00Z",
    )
    receipt = simulate_proposal(proposal, registry=ActionRegistry.default(), simulated_at="2026-09-16T06:00:00Z")
    assert receipt.succeeded is True
    assert receipt.proposal_id == "p-1"


def test_unregistered_action_simulation_fails_closed():
    proposal = ResponseProposal(
        proposal_id="p-2",
        assessment_id="a-2",
        action_class="unknown_action",
        target_resource_id="asset-1",
        authorized_boundary_id="lab",
        material_action=False,
        simulation_required=True,
        simulation_receipt_id=None,
        rollback_plan_id=None,
        human_approval_required=False,
        expires_at="2099-01-01T00:00:00Z",
    )
    receipt = simulate_proposal(proposal, registry=ActionRegistry.default(), simulated_at="2026-09-16T06:00:00Z")
    assert receipt.succeeded is False
```

- [ ] **Step 2: Run simulation tests and verify failure**

Run:

```bash
pytest tests/guardian/test_simulation.py -v
```

Expected: FAIL because `simulation.py` does not exist.

- [ ] **Step 3: Implement deterministic dry-run simulation**

```python
# guardian/defense_grid/simulation.py
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

from .models import ResponseProposal, SimulationReceipt
from .registry import ActionRegistry, RegistryError


def simulate_proposal(
    proposal: ResponseProposal,
    *,
    registry: ActionRegistry,
    simulated_at: str,
) -> SimulationReceipt:
    token = f"{proposal.proposal_id}|{proposal.action_class}|{proposal.target_resource_id}|{simulated_at}"
    receipt_id = "sim-" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
    try:
        registry.get(proposal.action_class)
        succeeded = True
    except RegistryError:
        succeeded = False
    return SimulationReceipt(
        receipt_id=receipt_id,
        proposal_id=proposal.proposal_id,
        succeeded=succeeded,
        simulated_at=simulated_at,
        evidence_refs=[f"dry-run:{proposal.action_class}"],
    )


def load_synthetic_scenarios(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("synthetic scenario file must contain a JSON list")
    return payload
```

Create fixtures with only inert/synthetic scenarios:

```json
[
  {
    "id": "credential-compromise-lab",
    "kind": "credential_compromise",
    "boundary": "lab",
    "target": "synthetic-account",
    "recommended_action": "revoke_owned_session"
  },
  {
    "id": "service-abuse-lab",
    "kind": "service_abuse",
    "boundary": "lab",
    "target": "synthetic-service",
    "recommended_action": "rate_limit_owned_service"
  }
]
```

```json
[
  {
    "id": "physical-hazard-track-1",
    "kind": "modeled_physical_hazard",
    "live_state": "MODELED",
    "fact_or_inference": "INFERENCE",
    "recommended_action": "trigger_safety_procedure"
  }
]
```

- [ ] **Step 4: Run simulation tests**

Run:

```bash
pytest tests/guardian/test_simulation.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit GUARDIAN Range core**

```bash
git add guardian/defense_grid/simulation.py guardian/defense_grid/fixtures tests/guardian/test_simulation.py
git commit -m "feat: add inert guardian defense simulation range"
```

---

### Task 5: Privacy-Preserving XUNIA Defense Export

**Files:**
- Create: `guardian/defense_grid/xunia_export.py`
- Test: `tests/guardian/test_xunia_export.py`

**Interfaces:**
- Consumes: `SensorObservation`, `HazardAssessment`, `LiveState`.
- Produces: `to_xunia_feature(...)` and `to_feature_collection(...)` returning GeoJSON-compatible dictionaries.

- [ ] **Step 1: Write XUNIA privacy/provenance tests**

```python
# tests/guardian/test_xunia_export.py
from guardian.defense_grid.models import (
    AttributionStatus,
    FactOrInference,
    GuardianState,
    HazardAssessment,
    Impact,
    LiveState,
    ProvenanceStatus,
    SensorObservation,
)
from guardian.defense_grid.xunia_export import to_xunia_feature


def observation(precision="COARSE_ASSET", personal=None):
    return SensorObservation(
        observation_id="obs-1",
        source_id="sensor-a",
        source_type="synthetic",
        observed_at="2026-09-16T06:00:00Z",
        received_at="2026-09-16T06:00:01Z",
        payload_hash="c" * 64,
        provenance_status=ProvenanceStatus.VERIFIED,
        confidence=0.8,
        scope_id="lab",
        fact_or_inference=FactOrInference.FACT,
        geometry={"type": "Point", "coordinates": [-77.43, 37.54]},
        location_precision_class=precision,
        personal_telemetry=personal,
    )


def assessment():
    return HazardAssessment(
        assessment_id="a-1",
        observation_ids=["obs-1"],
        hazard_class="service_disruption",
        impact=Impact.MODERATE,
        likelihood=0.7,
        state=GuardianState.AMBER,
        attribution_status=AttributionStatus.HYPOTHESIS,
        rationale="synthetic test",
    )


def test_public_export_suppresses_precise_person_location():
    feature = to_xunia_feature(
        observation("PRECISE_PERSON"),
        assessment(),
        event_id="event-1",
        live_state=LiveState.LIVE,
        recommended_protective_action="notify_operator",
        public=True,
    )
    assert feature["geometry"] is None


def test_public_export_never_contains_personal_telemetry():
    feature = to_xunia_feature(
        observation(personal={"heart_rate": 88}),
        assessment(),
        event_id="event-1",
        live_state=LiveState.LIVE,
        recommended_protective_action="notify_operator",
        public=True,
    )
    assert "personal_telemetry" not in feature["properties"]


def test_export_preserves_provenance_and_fact_inference_labels():
    feature = to_xunia_feature(
        observation(),
        assessment(),
        event_id="event-1",
        live_state=LiveState.MODELED,
        recommended_protective_action="notify_operator",
        public=True,
    )
    assert feature["properties"]["provenance_status"] == "VERIFIED"
    assert feature["properties"]["fact_or_inference"] == "FACT"
    assert feature["properties"]["live_state"] == "MODELED"
```

- [ ] **Step 2: Run exporter tests and verify failure**

Run:

```bash
pytest tests/guardian/test_xunia_export.py -v
```

Expected: FAIL because `xunia_export.py` does not exist.

- [ ] **Step 3: Implement GeoJSON-compatible exporter**

```python
# guardian/defense_grid/xunia_export.py
from __future__ import annotations

from typing import Dict, Iterable, List

from .models import HazardAssessment, LiveState, SensorObservation


PRECISE_PERSON_CLASSES = {"PRECISE_PERSON", "BIOMETRIC_PERSON"}


def to_xunia_feature(
    observation: SensorObservation,
    assessment: HazardAssessment,
    *,
    event_id: str,
    live_state: LiveState,
    recommended_protective_action: str,
    public: bool = True,
) -> Dict[str, object]:
    geometry = observation.geometry
    if public and observation.location_precision_class in PRECISE_PERSON_CLASSES:
        geometry = None

    properties = {
        "event_id": event_id,
        "observation_id": observation.observation_id,
        "source_id": observation.source_id,
        "source_type": observation.source_type,
        "observed_at": observation.observed_at,
        "received_at": observation.received_at,
        "provenance_status": observation.provenance_status.value,
        "confidence": observation.confidence,
        "state": assessment.state.value,
        "location_precision_class": observation.location_precision_class,
        "evidence_refs": [observation.observation_id, assessment.assessment_id],
        "assessment_summary": assessment.rationale,
        "recommended_protective_action": recommended_protective_action,
        "fact_or_inference": observation.fact_or_inference.value,
        "live_state": live_state.value,
        "attribution_status": assessment.attribution_status.value,
    }
    return {"type": "Feature", "geometry": geometry, "properties": properties}


def to_feature_collection(features: Iterable[Dict[str, object]]) -> Dict[str, object]:
    return {"type": "FeatureCollection", "features": list(features)}
```

- [ ] **Step 4: Run XUNIA tests**

Run:

```bash
pytest tests/guardian/test_xunia_export.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit XUNIA export layer**

```bash
git add guardian/defense_grid/xunia_export.py tests/guardian/test_xunia_export.py
git commit -m "feat: add privacy-preserving xunia defense export"
```

---

### Task 6: Machine-Readable Schemas and Deterministic Validator

**Files:**
- Create: `guardian/defense_grid/schemas/sensor-observation.schema.json`
- Create: `guardian/defense_grid/schemas/hazard-assessment.schema.json`
- Create: `guardian/defense_grid/schemas/response-proposal.schema.json`
- Create: `guardian/defense_grid/schemas/simulation-receipt.schema.json`
- Create: `guardian/defense_grid/schemas/authorization-grant.schema.json`
- Create: `guardian/defense_grid/schemas/defense-receipt.schema.json`
- Create: `guardian/defense_grid/schemas/xunia-defense-layer.schema.json`
- Create: `scripts/validate_guardian_defense.py`
- Test: `tests/guardian/test_validator.py`

**Interfaces:**
- Consumes: JSON policies from Task 2 and prohibited token rules from `registry.py`.
- Produces: `scripts/validate_guardian_defense.py` command with exit 0 on valid defensive contract and exit 2 on violation.

- [ ] **Step 1: Write validator tests against temporary policy trees**

```python
# tests/guardian/test_validator.py
import json
from pathlib import Path

import pytest

from scripts.validate_guardian_defense import ValidationError, validate_contract


def test_contract_rejects_external_dispatch_enabled(tmp_path):
    policy = {
        "schema": "guardian.authorized-boundary.v1",
        "default": "deny",
        "external_dispatch": "enabled",
        "require_known_scope": True,
        "require_human_approval_for_material_actions": True,
        "require_simulation_for_consequential_mutation": True,
        "require_rollback_for_mutation": True,
    }
    path = tmp_path / "authorized-boundary.json"
    path.write_text(json.dumps(policy), encoding="utf-8")
    with pytest.raises(ValidationError, match="external dispatch"):
        validate_contract(boundary_policy_path=path)
```

- [ ] **Step 2: Run validator tests and verify failure**

Run:

```bash
pytest tests/guardian/test_validator.py -v
```

Expected: FAIL because `scripts.validate_guardian_defense` does not exist.

- [ ] **Step 3: Create JSON Schema documents**

Use Draft 2020-12 metadata and exact required fields from the spec. Example for `sensor-observation.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "guardian.sensor-observation.v1",
  "type": "object",
  "required": [
    "observation_id",
    "source_id",
    "source_type",
    "observed_at",
    "received_at",
    "payload_hash",
    "provenance_status",
    "confidence",
    "scope_id",
    "fact_or_inference"
  ],
  "properties": {
    "observation_id": {"type": "string", "minLength": 1},
    "source_id": {"type": "string", "minLength": 1},
    "source_type": {"type": "string", "minLength": 1},
    "observed_at": {"type": "string"},
    "received_at": {"type": "string"},
    "payload_hash": {"type": "string", "pattern": "^[0-9a-fA-F]{64}$"},
    "provenance_status": {"enum": ["VERIFIED", "PARTIAL", "UNVERIFIED", "REJECTED"]},
    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    "scope_id": {"type": "string", "minLength": 1},
    "fact_or_inference": {"enum": ["FACT", "INFERENCE"]},
    "geometry": {"type": ["object", "null"]},
    "location_precision_class": {"type": ["string", "null"]}
  },
  "additionalProperties": false
}
```

Create the remaining six schema files with the exact field names/enums defined by the approved spec plus `SimulationReceipt` from Task 1. No schema may define executable weapon-control or external-counter-intrusion fields.

- [ ] **Step 4: Implement the deterministic repository validator**

```python
# scripts/validate_guardian_defense.py
#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BOUNDARY = ROOT / "guardian" / "defense_grid" / "policies" / "authorized-boundary.json"
DEFAULT_ACTIONS = ROOT / "guardian" / "defense_grid" / "policies" / "protective-actions.json"
DEFAULT_HAZARD = ROOT / "guardian" / "defense_grid" / "policies" / "physical-hazard-policy.json"
DEFAULT_SCHEMAS = ROOT / "guardian" / "defense_grid" / "schemas"

PROHIBITED = {
    "weapon_target_selection",
    "strike_recommendation",
    "fire_control",
    "guidance_command",
    "initiation_control",
    "explosive_design",
    "fragmentation_design",
    "external_counter_intrusion",
}


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def validate_contract(
    *,
    boundary_policy_path: Path = DEFAULT_BOUNDARY,
    actions_path: Path = DEFAULT_ACTIONS,
    hazard_policy_path: Path = DEFAULT_HAZARD,
    schema_dir: Path = DEFAULT_SCHEMAS,
) -> None:
    boundary = json.loads(Path(boundary_policy_path).read_text(encoding="utf-8"))
    require(boundary.get("default") == "deny", "default policy must deny")
    require(boundary.get("external_dispatch") == "disabled", "external dispatch must stay disabled")
    require(boundary.get("require_known_scope") is True, "known scope requirement missing")
    require(boundary.get("require_human_approval_for_material_actions") is True, "human approval requirement missing")
    require(boundary.get("require_simulation_for_consequential_mutation") is True, "simulation requirement missing")
    require(boundary.get("require_rollback_for_mutation") is True, "rollback requirement missing")

    if Path(actions_path).exists():
        actions = json.loads(Path(actions_path).read_text(encoding="utf-8"))
        names = {str(item.get("name", "")).lower() for item in actions.get("actions", [])}
        for name in names:
            require(not any(token in name for token in PROHIBITED), f"prohibited executable action: {name}")

    if Path(hazard_policy_path).exists():
        hazard = json.loads(Path(hazard_policy_path).read_text(encoding="utf-8"))
        prohibited = set(hazard.get("prohibited_outputs", []))
        require(PROHIBITED.issubset(prohibited), "physical hazard prohibitions incomplete")

    if Path(schema_dir).exists():
        for path in sorted(Path(schema_dir).glob("*.schema.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            require(payload.get("type") == "object", f"{path.name}: schema root must be object")


def main() -> int:
    validate_contract()
    print("GUARDIAN DEFENSE GATE: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"GUARDIAN DEFENSE GATE: FAIL // {exc}")
        raise SystemExit(2)
```

- [ ] **Step 5: Run validator tests and command**

Run:

```bash
pytest tests/guardian/test_validator.py -v
python3 scripts/validate_guardian_defense.py
python3 -m py_compile scripts/validate_guardian_defense.py
```

Expected:

```text
GUARDIAN DEFENSE GATE: PASS
```

- [ ] **Step 6: Commit schemas and validator**

```bash
git add guardian/defense_grid/schemas scripts/validate_guardian_defense.py tests/guardian/test_validator.py
git commit -m "feat: add guardian defense schemas and validator"
```

---

### Task 7: Safety Shield Ontology Integration

**Files:**
- Create: `safety-shield/ontology/guardian-defense-grid.ttl`
- Test: extend `tests/guardian/test_validator.py`

**Interfaces:**
- Consumes: approved domain names and policy invariants from Tasks 1-6.
- Produces: RDF/Turtle vocabulary connecting GUARDIAN Defense Grid to Safety Shield, SHADOW GLASS, GLASS ONION, Human Oversight, and Audit Ledger concepts.

- [ ] **Step 1: Add an ontology contract test**

```python
# append to tests/guardian/test_validator.py
from pathlib import Path


def test_guardian_ontology_contains_required_control_relationships():
    text = Path("safety-shield/ontology/guardian-defense-grid.ttl").read_text(encoding="utf-8")
    for token in (
        "GuardianDefenseGrid",
        "ShadowGlass",
        "GlassOnion",
        "HumanOversightGate",
        "AuditLedger",
        "DenyByDefault",
    ):
        assert token in text
    for prohibited in ("FireControl", "TargetSelection", "DetonationControl"):
        assert prohibited not in text
```

- [ ] **Step 2: Run the ontology contract test and verify failure**

Run:

```bash
pytest tests/guardian/test_validator.py::test_guardian_ontology_contains_required_control_relationships -v
```

Expected: FAIL because the ontology file does not exist.

- [ ] **Step 3: Create the GUARDIAN ontology extension**

```turtle
@prefix vllm: <https://xunia.example/ontology#> .

vllm:GuardianDefenseGrid a vllm:DefensiveControlPlane ;
  vllm:protectedBy vllm:ShadowGlass ;
  vllm:evidenceRecordedBy vllm:GlassOnion ;
  vllm:requires vllm:HumanOversightGate, vllm:AuditLedger ;
  vllm:defaultPolicy vllm:DenyByDefault .

vllm:SensorObservation a vllm:EvidenceObject .
vllm:HazardAssessment a vllm:AdvisoryAssessment .
vllm:ResponseProposal a vllm:ProposedAction .
vllm:SimulationReceipt a vllm:EvidenceObject .
vllm:AuthorizationGrant a vllm:HumanAuthorization .
vllm:DefenseReceipt a vllm:AuditEvidence .

vllm:ProtectiveAction a vllm:AuthorizedAction ;
  vllm:requires vllm:KnownScope, vllm:SimulationEvidence, vllm:RollbackPlan .

vllm:MaterialProtectiveAction a vllm:ProtectiveAction ;
  vllm:requires vllm:HumanOversightGate .

vllm:ExternalDispatch a vllm:DeniedByDefaultAction .
vllm:UntrustedContext a vllm:NonAuthorizingContext .
```

- [ ] **Step 4: Run the ontology contract test**

Run:

```bash
pytest tests/guardian/test_validator.py::test_guardian_ontology_contains_required_control_relationships -v
```

Expected: PASS.

- [ ] **Step 5: Commit ontology integration**

```bash
git add safety-shield/ontology/guardian-defense-grid.ttl tests/guardian/test_validator.py
git commit -m "feat: connect guardian defense grid to safety shield ontology"
```

---

### Task 8: CI Gate and Public Documentation

**Files:**
- Create: `.github/workflows/guardian-defense-gate.yml`
- Create: `docs/GUARDIAN_XUNIA_DEFENSE_GRID.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: all implementation/testing artifacts from Tasks 1-7.
- Produces: CI enforcement and public defensive-scope documentation.

- [ ] **Step 1: Create the CI workflow**

```yaml
# .github/workflows/guardian-defense-gate.yml
name: GUARDIAN Defense Gate

on:
  push:
    paths:
      - 'guardian/defense_grid/**'
      - 'safety-shield/ontology/guardian-defense-grid.ttl'
      - 'scripts/validate_guardian_defense.py'
      - 'tests/guardian/**'
      - '.github/workflows/guardian-defense-gate.yml'
  pull_request:
    paths:
      - 'guardian/defense_grid/**'
      - 'safety-shield/ontology/guardian-defense-grid.ttl'
      - 'scripts/validate_guardian_defense.py'
      - 'tests/guardian/**'
      - '.github/workflows/guardian-defense-gate.yml'
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: guardian-defense-${{ github.ref }}
  cancel-in-progress: true

jobs:
  validate:
    runs-on: ubuntu-latest
    timeout-minutes: 8
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install test dependencies
        run: python -m pip install -e '.[test]'

      - name: Run GUARDIAN focused tests
        run: pytest tests/guardian -q

      - name: Run deterministic defense validator
        run: python3 scripts/validate_guardian_defense.py

      - name: Compile defensive modules
        run: python3 -m py_compile guardian/defense_grid/*.py scripts/validate_guardian_defense.py
```

- [ ] **Step 2: Write the public operator documentation**

Create `docs/GUARDIAN_XUNIA_DEFENSE_GRID.md` with these exact sections and concrete content:

```markdown
# GUARDIAN / XUNIA Defense Grid

## Purpose
GUARDIAN/XUNIA provides provenance-first defensive awareness, synthetic/inert simulation, human-approved protective response on owned or explicitly authorized resources, and append-only evidence.

## Decision Contract
OBSERVE -> VERIFY -> ASSESS -> PROPOSE -> SIMULATE -> CHECK BOUNDARY -> HUMAN APPROVAL WHEN REQUIRED -> PROTECT -> VERIFY -> RECEIPT

## States
- GREEN: observe/correlate/recommend.
- AMBER: increase telemetry, simulate, preserve evidence, require review for material actions.
- RED: approved defensive containment/recovery on owned resources.
- BLACK: freeze nonessential mutation, quarantine locally governed resources, require explicit recovery authorization.

## Executable Boundary
The repository executes only allow-listed protective action semantics. It does not implement weapon target selection, fire control, guidance, initiation, explosive/fragmentation design, autonomous engagement, external exploitation, or counter-intrusion.

## XUNIA Privacy
Public exports suppress precise person location and exclude personal/biometric telemetry. Observed facts and model inference are always labeled separately.

## Government / NGA Boundary
Public NGA/NGP standards and ngageoint open-source software may be used for interoperability research. No repository artifact represents NGA sponsorship, certification, partnership, classified connectivity, or operational tasking authority.

## Validation
Run:

```bash
pytest tests/guardian -q
python3 scripts/validate_guardian_defense.py
```
```

- [ ] **Step 3: Add a README entry**

Add a short section near the existing Safety Shield/security documentation links:

```markdown
### GUARDIAN / XUNIA Defense Grid

- [Design](docs/superpowers/specs/2026-09-16-guardian-xunia-defense-grid-design.md)
- [Implementation plan](docs/superpowers/plans/2026-09-16-guardian-xunia-defense-grid.md)
- [Operator guide](docs/GUARDIAN_XUNIA_DEFENSE_GRID.md)
- [Deterministic validator](scripts/validate_guardian_defense.py)

The grid is defensive and human-governed: external dispatch defaults off, material actions require approval, consequential mutation is simulation-gated, and public XUNIA exports preserve provenance while suppressing precise personal location.
```

- [ ] **Step 4: Run all focused verification**

Run:

```bash
pytest tests/guardian -q
python3 scripts/validate_guardian_defense.py
python3 -m py_compile guardian/defense_grid/*.py scripts/validate_guardian_defense.py
```

Expected: all tests PASS and validator prints `GUARDIAN DEFENSE GATE: PASS`.

- [ ] **Step 5: Run the repository test suite to detect integration regressions**

Run:

```bash
pytest -q
```

Expected: PASS, or any pre-existing unrelated failures must be recorded verbatim before merge and must not be attributed to GUARDIAN without evidence.

- [ ] **Step 6: Commit CI and documentation**

```bash
git add .github/workflows/guardian-defense-gate.yml docs/GUARDIAN_XUNIA_DEFENSE_GRID.md README.md
git commit -m "docs: publish guardian xunia defensive control plane"
```

---

## Final Verification Checklist

After Tasks 1-8:

```bash
pytest tests/guardian -q
python3 scripts/validate_guardian_defense.py
python3 -m py_compile guardian/defense_grid/*.py scripts/validate_guardian_defense.py
pytest -q
```

Verify manually:

- `guardian/defense_grid/registry.py` has only protective action names.
- `guardian/defense_grid/policies/authorized-boundary.json` keeps `external_dispatch` set to `disabled`.
- `guardian/defense_grid/policies/physical-hazard-policy.json` contains the complete prohibited-output set.
- `to_xunia_feature(..., public=True)` removes geometry for `PRECISE_PERSON` and never serializes `personal_telemetry`.
- every mutating action is blocked without rollback metadata.
- every material action is blocked without a matching, unexpired `AuthorizationGrant`.
- every proposal requiring simulation is blocked without a matching successful `SimulationReceipt`.
- denied decisions can be recorded as `DefenseReceipt` entries.
- the public docs do not claim NGA/government sponsorship or authorization.

## Explicit Follow-On Boundary

Live mutating defensive adapters are not part of this implementation plan. After this plan passes CI, each desired live adapter must be specified separately with its exact owned/authorized target type, authentication method, dry-run semantics, rollback procedure, human-approval mechanism, audit sink, and post-change validation. The existing action registry and policy gate become mandatory prerequisites for those later adapters.
