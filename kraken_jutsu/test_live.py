from pathlib import Path

from kraken_jutsu.live import (
    AgentCandidate,
    AIPDecisionLayer,
    AppointmentEngine,
    OntologyStore,
)


def candidate(name, caps, test=0.95, provenance=0.90, integrity=0.98):
    return AgentCandidate(
        agent_id=name,
        name=name,
        version="1",
        fingerprint="abc",
        capabilities=caps,
        test_score=test,
        provenance_score=provenance,
        integrity_score=integrity,
    )


def test_cpr_appointment():
    appt = AppointmentEngine().appoint(
        candidate("repair", ["diagnose", "recover", "repair", "verify"])
    )
    assert appt.role == "CPR"


def test_llm_appointment():
    appt = AppointmentEngine().appoint(
        candidate("brain", ["reason", "code", "analyze", "summarize", "classify"])
    )
    assert appt.role == "LLM"


def test_max_needs_breadth_and_assurance():
    appt = AppointmentEngine().appoint(
        candidate(
            "beast",
            [
                "orchestrate", "coordinate", "diagnose", "recover",
                "configure", "deploy", "reason", "code", "verify", "plan",
            ],
            test=0.99,
            provenance=0.98,
            integrity=0.99,
        )
    )
    assert appt.role == "MAX"


def test_high_authority_appointment_requires_approval():
    c = candidate("admin", ["configure", "deploy", "maintain", "backup"])
    appt = AppointmentEngine().appoint(c)
    proposal = AIPDecisionLayer().propose_appointment(c, appt)
    assert proposal.requires_approval is True


def test_store_round_trip(tmp_path: Path):
    store = OntologyStore(tmp_path / "ontology.db")
    store.upsert_object("agent:1", "AgentCandidate", {"name": "friend"})
    assert store.get_object("agent:1")["data"]["name"] == "friend"
