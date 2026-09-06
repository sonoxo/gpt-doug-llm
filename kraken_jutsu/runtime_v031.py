from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .agents_v031 import AIPDecisionLayer, AppointmentEngine, FriendGate
from .models_v031 import TrustState
from .sources_v031 import CISAKEVSource
from .store_v031 import OntologyStore

VA3LM_LANES = (
    "Inventory",
    "Identity",
    "Segmentation",
    "Detection",
    "Containment",
    "Recovery",
    "Verification",
)


class LiveRuntime:
    def __init__(self, state_root: str | Path) -> None:
        self.state = Path(state_root)
        self.state.mkdir(parents=True, exist_ok=True)
        self.store = OntologyStore(self.state / "ontology.db")
        self.friends = FriendGate(self.state)
        self.audit = self.state / "audit.jsonl"

    def audit_event(self, event: str, payload: dict[str, Any]) -> None:
        with self.audit.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {"ts": int(time.time()), "event": event, "payload": payload},
                    sort_keys=True,
                )
                + "\n"
            )

    def ingest_kev(self, source: CISAKEVSource | None = None) -> int:
        payload = (source or CISAKEVSource()).fetch()
        rows = payload.get("vulnerabilities", [])
        if not isinstance(rows, list):
            raise ValueError("CISA KEV vulnerabilities must be a list")
        self.store.upsert_object(
            "source:cisa-kev",
            "DataSource",
            {
                "name": "CISA KEV",
                "count": len(rows),
                "dateReleased": payload.get("dateReleased"),
                "source_url": payload.get("_kraken_source_url"),
            },
        )
        for row in rows:
            if not isinstance(row, dict):
                continue
            cve = row.get("cveID")
            if cve:
                self.store.upsert_object(cve, "Vulnerability", row)
                self.store.link("source:cisa-kev", "ASSERTS", cve)
        self.audit_event(
            "source.ingest",
            {
                "source": "CISA-KEV",
                "count": len(rows),
                "source_url": payload.get("_kraken_source_url"),
            },
        )
        return len(rows)

    def discover_appoint_promote(self) -> list[dict[str, Any]]:
        engine = AppointmentEngine()
        aip = AIPDecisionLayer()
        output: list[dict[str, Any]] = []

        for candidate in self.friends.discover():
            self.store.upsert_object(candidate.agent_id, "AgentCandidate", candidate.to_dict())
            appointment = engine.appoint(candidate)
            self.store.add_appointment(appointment)
            proposal = aip.propose_appointment(candidate, appointment)
            self.store.upsert_object(proposal.action_id, "ActionProposal", proposal.to_dict())
            self.store.link(candidate.agent_id, "HAS_APPOINTMENT", appointment.appointment_id)
            self.store.link(candidate.agent_id, "HAS_ACTION_PROPOSAL", proposal.action_id)

            promotion: dict[str, Any] = {"promoted": False, "reason": "candidate not verified"}
            if candidate.trust_state == TrustState.VERIFIED.value:
                candidate.trust_state = TrustState.APPOINTED.value
                self.store.upsert_object(candidate.agent_id, "AgentCandidate", candidate.to_dict())
                try:
                    destination = self.friends.promote(candidate, appointment)
                except (PermissionError, FileNotFoundError) as exc:
                    promotion = {"promoted": False, "reason": str(exc)}
                else:
                    candidate.trust_state = TrustState.BLACKHOUSE.value
                    candidate.source_path = str(destination)
                    self.store.upsert_object(candidate.agent_id, "AgentCandidate", candidate.to_dict())
                    self.store.link(candidate.agent_id, "PROMOTED_TO", "BLACKHOUSE")
                    promotion = {"promoted": True, "destination": str(destination)}

            event = {
                "va3lm": {
                    "pattern": ["plan", "approval", "act", "verify", "evidence", "ontology"],
                    "lanes": list(VA3LM_LANES),
                },
                "agent": candidate.to_dict(),
                "appointment": appointment.to_dict(),
                "proposal": proposal.to_dict(),
                "promotion": promotion,
            }
            self.audit_event("agent.lifecycle", event)
            output.append(event)
        return output

    def readiness(self) -> dict[str, Any]:
        agents = self.store.list_objects("AgentCandidate")
        blackhouse_agents = [
            x for x in agents if x["data"].get("trust_state") == TrustState.BLACKHOUSE.value
        ]
        sources = self.store.list_objects("DataSource")
        gate_a = bool(blackhouse_agents)
        gate_b = any(x["object_id"] == "source:cisa-kev" for x in sources)
        return {
            "va3lm": {
                "lanes": list(VA3LM_LANES),
                "control_loop": ["plan", "approval", "act", "verify", "evidence", "ontology"],
            },
            "gate_a_usb_blackhouse": gate_a,
            "gate_b_live_ontology": gate_b,
            "kraken_ready": gate_a and gate_b,
            "blackhouse_agents": len(blackhouse_agents),
            "live_sources": len(sources),
        }
