import json
from datetime import datetime, timezone

import pytest

from gpt_doug_mlm.biochip_research import (
    EvidenceJournal, Observation, ProposalGate, ResearchRouter, heartbeat,
)


def sample():
    return Observation("authorized-lab-1", "synthetic", 0.4, "mV",
                       datetime.now(timezone.utc).isoformat(), "research-consent-123")


def test_local_models_only():
    router = ResearchRouter({"a": lambda q: "answer:" + q, "b": lambda q: q.upper()})
    assert [item.model for item in router.deliberate("test")] == ["a", "b"]
    assert router.deliberate("test")[0].confidence == 0.0
    with pytest.raises(ValueError):
        router.deliberate("test", selected=["unregistered"])


def test_journal_chain_and_tamper_detection(tmp_path):
    journal = EvidenceJournal(str(tmp_path / "observations.jsonl"))
    first = journal.append(sample())
    second = journal.append(sample())
    assert first != second
    assert journal.verify() == second
    lines = journal.path.read_text().splitlines()
    altered = json.loads(lines[0])
    altered["observation"]["value"] = 999
    lines[0] = json.dumps(altered)
    journal.path.write_text("\n".join(lines) + "\n")
    assert heartbeat(journal)["healthy"] is False


def test_consent_required(tmp_path):
    journal = EvidenceJournal(str(tmp_path / "data.jsonl"))
    invalid = Observation("lab", "neural_signal", 1, "mV",
                          datetime.now(timezone.utc).isoformat(), "")
    with pytest.raises(ValueError):
        journal.append(invalid)


def test_proposal_is_review_only():
    gate = ProposalGate()
    pid = gate.propose("evaluate offline model benchmark", "a" * 64)
    gate.approve(pid, "research-reviewer")
    assert gate.proposals[pid]["status"] == "approved_for_review_only"
    with pytest.raises(ValueError):
        gate.approve(pid, "another")
