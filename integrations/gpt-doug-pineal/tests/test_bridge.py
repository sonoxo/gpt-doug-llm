import json

from pineal.bridge import read_legacy_memory, read_ontology


def test_read_existing_brain_sources(tmp_path):
    ontology = tmp_path / "repo" / "config"
    ontology.mkdir(parents=True)
    (ontology / "global-ontology.json").write_text(json.dumps({"agents": {"gpt_doug": "pineal"}}))
    home = tmp_path / "home" / ".gpt-doug"
    home.mkdir(parents=True)
    (home / "brain-memory-v1.jsonl").write_text(json.dumps({"kind": "decision",
        "content": "pineal owns memory I/O", "provenance": "user"}) + "\n")
    assert read_ontology(tmp_path / "repo", "pineal")
    assert read_legacy_memory(tmp_path / "home", "pineal")
    assert read_legacy_memory(tmp_path / "home", "unrelated") == []
