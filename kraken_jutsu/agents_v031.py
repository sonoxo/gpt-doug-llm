from __future__ import annotations

import hashlib
import json
import shutil
import time
import uuid
from pathlib import Path

from .models_v031 import ActionProposal, AgentCandidate, Appointment, Role, TrustState


CAPS = {
    Role.OFFICER: {
        "orchestrate": 2.0, "coordinate": 2.0, "policy": 1.5,
        "plan": 1.5, "reason": 1.0, "delegate": 1.0, "verify": 0.5,
    },
    Role.CPR: {
        "diagnose": 2.0, "recover": 2.0, "repair": 2.0,
        "verify": 1.5, "rollback": 1.0, "healthcheck": 1.0,
    },
    Role.ADMIN: {
        "configure": 2.0, "deploy": 1.5, "maintain": 1.5,
        "backup": 1.0, "observe": 0.5, "verify": 0.5,
    },
    Role.LLM: {
        "reason": 2.0, "code": 1.5, "analyze": 1.5,
        "summarize": 1.0, "classify": 1.0, "plan": 1.0,
    },
}

PERMISSIONS = {
    Role.OFFICER: ["ontology:read", "mission:plan", "agent:recommend", "action:propose"],
    Role.CPR: ["telemetry:read", "diagnostic:run", "recovery:propose", "verify:run"],
    Role.ADMIN: ["inventory:read", "config:propose", "deployment:propose", "backup:verify"],
    Role.LLM: ["ontology:read", "evidence:read", "analysis:write", "action:propose"],
    Role.MAX: [
        "ontology:read", "evidence:read", "mission:plan", "agent:recommend",
        "diagnostic:run", "analysis:write", "action:propose", "verify:run",
    ],
}


class AppointmentEngine:
    def appoint(self, candidate: AgentCandidate) -> Appointment:
        assurance = (
            candidate.test_score * 0.40
            + candidate.provenance_score * 0.25
            + candidate.integrity_score * 0.35
        )
        caps = set(candidate.capabilities)
        scored: list[tuple[float, Role, list[str]]] = []
        for role, weights in CAPS.items():
            matched = sorted(c for c in caps if c in weights)
            capability_score = sum(weights[c] for c in matched) / sum(weights.values())
            total = capability_score * 0.65 + assurance * 0.35
            scored.append((
                total,
                role,
                [
                    f"capability-fit={capability_score:.2f}",
                    f"assurance={assurance:.2f}",
                    f"matched={','.join(matched) or 'none'}",
                ],
            ))

        scored.sort(key=lambda x: x[0], reverse=True)
        score, role, reasons = scored[0]
        breadth = sum(
            1 for weights in CAPS.values()
            if sum(1 for c in caps if c in weights) >= 2
        )
        if (
            assurance >= 0.92
            and candidate.test_score >= 0.95
            and candidate.integrity_score >= 0.95
            and breadth >= 3
            and score >= 0.70
        ):
            role = Role.MAX
            score = min(1.0, score * 0.70 + assurance * 0.30)
            reasons += [f"multi-domain-breadth={breadth}/4", "MAX threshold satisfied"]

        confidence = min(
            0.99,
            0.35
            + 0.25 * assurance
            + 0.25 * min(1.0, score)
            + 0.15 * min(1.0, len(caps) / 8),
        )
        return Appointment(
            appointment_id=str(uuid.uuid4()),
            agent_id=candidate.agent_id,
            role=role.value,
            confidence=round(confidence, 3),
            score=round(score, 3),
            reasons=reasons,
            recommended_permissions=PERMISSIONS[role],
        )


class AIPDecisionLayer:
    def propose_appointment(
        self, candidate: AgentCandidate, appointment: Appointment
    ) -> ActionProposal:
        high_authority = appointment.role in {
            Role.OFFICER.value, Role.ADMIN.value, Role.MAX.value
        }
        return ActionProposal(
            action_id=str(uuid.uuid4()),
            action_type="appoint-agent",
            subject=candidate.agent_id,
            risk="high" if high_authority else "medium",
            rationale=[
                f"ontology-role={appointment.role}",
                f"confidence={appointment.confidence}",
                f"score={appointment.score}",
                "role classification is separate from runtime privilege",
            ],
            requires_approval=high_authority,
        )


class FriendGate:
    def __init__(self, state_root: str | Path) -> None:
        self.state = Path(state_root)
        self.inbox = self.state / "agent-inbox"
        self.quarantine = self.state / "quarantine"
        self.friends = self.state / "BLACKHOUSE" / "friends"
        for path in (self.inbox, self.quarantine, self.friends):
            path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def fingerprint(path: Path) -> str:
        h = hashlib.sha256()
        for child in sorted(p for p in path.rglob("*") if p.is_file()):
            h.update(str(child.relative_to(path)).encode("utf-8"))
            h.update(child.read_bytes())
        return h.hexdigest()

    def discover(self) -> list[AgentCandidate]:
        result: list[AgentCandidate] = []
        for package in sorted(self.inbox.iterdir()):
            if not package.is_dir() or package.name.startswith("."):
                continue
            manifest_path = package / "agent.json"
            if not manifest_path.exists():
                continue
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            agent_id = str(uuid.uuid4())
            qpath = self.quarantine / f"{agent_id}-{package.name}"
            shutil.move(str(package), qpath)
            capabilities = manifest.get("capabilities", [])
            if not isinstance(capabilities, list):
                capabilities = []
            candidate = AgentCandidate(
                agent_id=agent_id,
                name=str(manifest.get("name", package.name)),
                version=str(manifest.get("version", "0")),
                fingerprint=self.fingerprint(qpath),
                capabilities=sorted({str(x) for x in capabilities}),
                test_score=float(manifest.get("test_score", 0.0)),
                provenance_score=float(manifest.get("provenance_score", 0.0)),
                integrity_score=float(manifest.get("integrity_score", 0.0)),
                source_path=str(qpath),
            )
            if (
                candidate.test_score >= 0.80
                and candidate.provenance_score >= 0.70
                and candidate.integrity_score >= 0.90
            ):
                candidate.trust_state = TrustState.VERIFIED.value
            result.append(candidate)
        return result

    def promote(self, candidate: AgentCandidate, appointment: Appointment) -> Path:
        if candidate.trust_state not in {
            TrustState.VERIFIED.value, TrustState.APPOINTED.value
        }:
            raise PermissionError("candidate has not passed verification")
        if appointment.confidence < 0.70:
            raise PermissionError("appointment confidence below Black House threshold")
        src = Path(candidate.source_path)
        if not src.exists():
            raise FileNotFoundError(src)
        dest = self.friends / f"{candidate.name}-{candidate.agent_id}"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.move(str(src), dest)
        member = {
            **candidate.to_dict(),
            "trust_state": TrustState.BLACKHOUSE.value,
            "appointment": appointment.to_dict(),
            "blackhouse_path": str(dest),
            "promoted_at": int(time.time()),
        }
        (dest / "blackhouse-member.json").write_text(
            json.dumps(member, indent=2, sort_keys=True), encoding="utf-8"
        )
        return dest
