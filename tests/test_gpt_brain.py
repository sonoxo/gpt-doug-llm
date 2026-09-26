from __future__ import annotations

import json
from pathlib import Path

import pytest

from gpt_brain.kernel import BrainConfig, BrainKernel
from gpt_brain.memory import BrainMemory
from gpt_brain.ontology import OntologyIndex
from gpt_brain.router import BrainRouter


def fake_chat(messages, model, options):
    system = messages[0]["content"]
    user = messages[1]["content"]
    if "final GPT-Doug critic" in system:
        text = "No material contradiction found; preserve uncertainty."
    elif "GPT-Doug Brain" in system:
        text = "Integrated answer grounded in supplied ontology and memory."
    else:
        text = f"artifact:{system.split('.')[0]}:{'ONTOLOGY CONTEXT' in user}"
    return {"message": {"role": "assistant", "content": text}, "done": True}


def test_router_selects_builder_research_and_critic():
    names = [a.name for a in BrainRouter().route("build medical research ontology app")]
    assert "builder" in names
    assert "research" in names
    assert "ontology" in names
    assert "critic" in names


def test_router_rejects_nonpositive_agent_limit():
    with pytest.raises(ValueError):
        BrainRouter().route("build", max_agents=0)


def test_memory_roundtrip_and_recall(tmp_path: Path):
    memory = BrainMemory(tmp_path / "memory.jsonl")
    memory.add("semantic", "NF2 is linked to meningioma research", provenance="unit-test")
    hit = memory.recall("NF2 meningioma")
    assert hit and hit[0]["provenance"] == "unit-test"


def test_memory_rejects_secret_like_content(tmp_path: Path):
    memory = BrainMemory(tmp_path / "memory.jsonl")
    with pytest.raises(ValueError):
        memory.add("semantic", "api_key=abcdefghijklmnop123456", provenance="unit-test")


def test_ontology_search_returns_exact_paths(tmp_path: Path):
    path = tmp_path / "ontology.json"
    path.write_text(
        json.dumps({"domains": {"medical": {"diseases": ["meningioma", "glioma"]}}})
    )
    hits = OntologyIndex(path).search("medical meningioma")
    assert hits
    assert any(
        "medical" in item["path"] or item["value"] == "meningioma"
        for item in hits
    )


def test_missing_ontology_is_empty(tmp_path: Path):
    ontology = OntologyIndex(tmp_path / "missing.json")
    assert ontology.load() == {}
    assert ontology.search("anything") == []


def test_kernel_runs_specialists_and_archives_episode(tmp_path: Path):
    memory = BrainMemory(tmp_path / "memory.jsonl")
    ontology_path = tmp_path / "ontology.json"
    ontology_path.write_text(
        json.dumps({"domains": {"medical": {"focus": "cancer research"}}})
    )
    kernel = BrainKernel(
        chat_fn=fake_chat,
        memory=memory,
        ontology=OntologyIndex(ontology_path),
        config=BrainConfig(max_agents=4),
    )
    result = kernel.run("build a medical cancer research ontology")
    assert result.answer.startswith("Integrated answer")
    assert "critic" in result.agents
    assert memory.records()[-1]["provenance"].startswith("brain-run:")


def test_kernel_survives_one_specialist_failure(tmp_path: Path):
    def flaky_chat(messages, model, options):
        if "evidence specialist" in messages[0]["content"]:
            raise RuntimeError("simulated specialist outage")
        return fake_chat(messages, model, options)

    ontology_path = tmp_path / "ontology.json"
    ontology_path.write_text(json.dumps({"domains": {"medical": {"focus": "cancer"}}}))
    result = BrainKernel(
        chat_fn=flaky_chat,
        memory=BrainMemory(tmp_path / "memory.jsonl"),
        ontology=OntologyIndex(ontology_path),
    ).run("build medical cancer research ontology")

    assert result.answer.startswith("Integrated answer")
    assert any(item.startswith("specialist:research:failed:") for item in result.uncertainty)


def test_memory_archive_failure_does_not_destroy_answer(tmp_path: Path):
    class BrokenArchiveMemory(BrainMemory):
        def add(self, *args, **kwargs):
            raise OSError("simulated read-only memory")

    ontology_path = tmp_path / "ontology.json"
    ontology_path.write_text(json.dumps({"domains": {"medical": {"focus": "cancer"}}}))
    result = BrainKernel(
        chat_fn=fake_chat,
        memory=BrokenArchiveMemory(tmp_path / "memory.jsonl"),
        ontology=OntologyIndex(ontology_path),
    ).run("build medical cancer research ontology")

    assert result.answer.startswith("Integrated answer")
    assert "memory_archive:failed:OSError" in result.uncertainty


def test_empty_task_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError):
        BrainKernel(
            chat_fn=fake_chat,
            memory=BrainMemory(tmp_path / "memory.jsonl"),
            ontology=OntologyIndex(tmp_path / "missing.json"),
        ).run("   ")


def test_transcript_ingestion(tmp_path: Path):
    memory = BrainMemory(tmp_path / "memory.jsonl")
    count = memory.ingest_transcript(
        "User: Build it\nAssistant: Built artifact",
        provenance="chat-export",
    )
    assert count == 2
    assert len(memory.records()) == 2
