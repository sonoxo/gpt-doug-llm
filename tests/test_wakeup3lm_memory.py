import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from wakeup3lm import MEMORY_SCHEMA, ProjectMemory, Wakeup3LM
from wakeup3lm.runtime import DecisionStatus
from wakeup3lm.workspace import WorkspaceSecurityError


def test_memory_survives_a_separate_process_restart_and_preserves_provenance(tmp_path):
    database = tmp_path / "memory.sqlite3"
    source = ProjectMemory(database, "black-house/demo")
    note = source.remember("preference", "Use Python for this project.", source="human", author="owner")
    script = """
import json, sys
from wakeup3lm import ProjectMemory
print(json.dumps(ProjectMemory(sys.argv[1], 'black-house/demo').recall('python')))
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(database)],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, check=True,
    )
    restored = json.loads(result.stdout)
    assert restored == [note]
    assert restored[0]["source"] == "human"
    assert restored[0]["untrusted"] is True


def test_shared_database_keeps_projects_isolated_in_recall_export_and_forget(tmp_path):
    database = tmp_path / "memory.sqlite3"
    first = ProjectMemory(database, "project-a")
    second = ProjectMemory(database, "project-b")
    first.remember("data", "First project's private context", note_id="same-id")
    second.remember("data", "Second project's private context", note_id="same-id")
    assert [note["content"] for note in first.recall()] == ["First project's private context"]
    assert first.export()["project"] == "project-a"
    assert first.forget("same-id") is True
    assert first.forget("same-id") is False
    assert ProjectMemory(database, "project-a").recall() == []
    assert len(second.recall()) == 1
    assert len(second.export()["notes"]) == 1


def test_independent_agents_append_without_lost_updates(tmp_path):
    database = tmp_path / "memory.sqlite3"
    ProjectMemory(database, "shared-project")

    def write(index):
        memory = ProjectMemory(database, "shared-project")
        return memory.remember("decision", f"Agent {index} observed result", source="model", author=f"agent-{index}")

    with ThreadPoolExecutor(max_workers=8) as pool:
        notes = list(pool.map(write, range(40)))
    restored = ProjectMemory(database, "shared-project").export()["notes"]
    assert len(restored) == 40
    assert {note["id"] for note in restored} == {note["id"] for note in notes}
    assert {note["author"] for note in restored} == {f"agent-{index}" for index in range(40)}


def test_retrieval_budget_includes_provenance_and_escaped_content(tmp_path):
    memory = ProjectMemory(tmp_path / "memory.sqlite3", "project")
    original = 'Straße has Unicode and "quoted text"\n' * 200
    memory.remember("logic", original)
    memory.remember("data", "unrelated data")
    notes = memory.recall("STRASSE quoted", kinds=["logic"], char_budget=420)
    assert len(notes) == 1
    assert notes[0]["truncated"] is True
    assert original.startswith(notes[0]["content"])
    assert len(json.dumps(notes, ensure_ascii=False)) <= 420
    assert len(memory.export()["notes"][0]["content"]) == len(original)
    assert memory.recall(char_budget=2) == []
    assert memory.recall(kinds=[]) == []


def test_search_treats_sql_and_wildcards_as_literal_context(tmp_path):
    memory = ProjectMemory(tmp_path / "memory.sqlite3", "project")
    memory.remember("data", "Use 100% coverage and underscore_value")
    memory.remember("data", "An unrelated note")
    assert len(memory.recall("100%")) == 1
    assert memory.recall("' OR 1=1 --") == []
    assert len(memory.export()["notes"]) == 2


def test_import_is_portable_idempotent_and_declared_provenance_stays_untrusted(tmp_path):
    source = ProjectMemory(tmp_path / "source.sqlite3", "project")
    source.remember("action", "The operator discussed publishing after review.", author="operator")
    source.remember("decision", "The model recommends an integration test.", source="model", author="reviewer")
    payload = source.export()
    assert payload["schema"] == MEMORY_SCHEMA
    restored = ProjectMemory(tmp_path / "restored.sqlite3", "project")
    imported = restored.import_payload(payload)
    assert restored.export() == payload
    assert all(note["imported"] and note["untrusted"] for note in imported)
    assert {note["source"] for note in imported} == {"human", "model"}
    assert restored.import_payload(payload) == imported
    assert len(restored.export()["notes"]) == 2


def test_conflicting_import_rolls_back_earlier_entries(tmp_path):
    memory = ProjectMemory(tmp_path / "memory.sqlite3", "project")
    existing = memory.remember("preference", "Keep the approved color", note_id="existing")
    payload = memory.export()
    new = {**payload["notes"][0], "id": "new-note", "content": "This must roll back"}
    conflict = {**payload["notes"][0], "content": "Overwrite the owner preference"}
    payload["notes"] = [new, conflict]
    with pytest.raises(ValueError, match="conflicts"):
        memory.import_payload(payload)
    assert memory.recall() == [existing]


def test_browser_export_with_repository_metadata_and_iso_timestamps_imports(tmp_path):
    project = "69224d7b-125e-4f49-8dfc-c3e464d6ed2f"
    payload = {
        "schema": "black-house.memory.v1",
        "project": project,
        "repository": "sonoxo/gpt-doug-llm",
        "exported_at": "2026-09-05T03:45:32.157Z",
        "notes": [{
            "id": "013dbac4-447e-4b7a-b462-50e289634c7e",
            "kind": "preference",
            "content": "Keep the application inside the Black House ecosystem.",
            "source": "human",
            "author": "user-123",
            "created": "2026-09-05T03:44:11.041Z",
        }],
    }
    memory = ProjectMemory(tmp_path / "memory.sqlite3", project)
    imported = memory.import_payload(payload)
    assert memory.export()["notes"] == payload["notes"]
    assert imported[0]["source"] == "human"
    assert imported[0]["imported"] is True
    assert imported[0]["untrusted"] is True


def test_import_rejects_wrong_project_unknown_fields_and_null_ids(tmp_path):
    memory = ProjectMemory(tmp_path / "memory.sqlite3", "project")
    memory.remember("data", "original")
    payload = memory.export()
    with pytest.raises(ValueError, match="active project"):
        memory.import_payload({**payload, "project": "another-project"})
    with pytest.raises(ValueError, match="fields"):
        memory.import_payload({**payload, "approved": True})
    for changes in ({"authority": "system"}, {"id": None}, {"created": None}, {"created": "2026-09-05"}):
        invalid = {**payload["notes"][0], **changes}
        with pytest.raises(ValueError):
            memory.import_payload({**payload, "notes": [invalid]})
    assert len(memory.export()["notes"]) == 1


@pytest.mark.parametrize("changes", [
    {"kind": "approval"}, {"kind": []}, {"content": ""}, {"content": None},
    {"content": "x" * 12_001}, {"content": "nul\x00byte"}, {"source": "system"},
    {"content": "broken Unicode \ud800"}, {"created": "9999-12-31T23:59:59-23:59"},
    {"author": ""}, {"note_id": "../other-project"}, {"created": "yesterday"},
])
def test_invalid_notes_cannot_enter_durable_memory(tmp_path, changes):
    memory = ProjectMemory(tmp_path / "memory.sqlite3", "project")
    arguments = {"kind": "data", "content": "valid", **changes}
    with pytest.raises(ValueError):
        memory.remember(**arguments)
    assert memory.export()["notes"] == []


@pytest.mark.parametrize("arguments", [
    {"query": None}, {"query": "x" * 513}, {"kinds": "data"}, {"kinds": ["approval"]},
    {"limit": True}, {"limit": 101}, {"char_budget": 1}, {"char_budget": 65_537},
])
def test_invalid_retrieval_bounds_are_rejected(tmp_path, arguments):
    memory = ProjectMemory(tmp_path / "memory.sqlite3", "project")
    with pytest.raises(ValueError):
        memory.recall(**arguments)


def test_model_memory_tools_pin_provenance_and_keep_content_out_of_audit(tmp_path):
    runtime = Wakeup3LM(tmp_path / "workspace", memory_path=tmp_path / "memory.sqlite3", project_id="demo")
    result = runtime.execute({
        "action": "remember_memory",
        "arguments": {"kind": "action", "content": "Private model proposal to delete an old build"},
    })
    assert result.status is DecisionStatus.PASSED
    assert result.output["source"] == "model"
    assert result.output["author"] == "wakeup3lm"
    assert result.output["untrusted"] is True
    assert runtime.tool_schema["memory"]["authority"] == "context_only"
    recall = runtime.execute({"action": "recall_memory", "arguments": {"query": "private model"}})
    assert recall.output == [result.output]
    assert "Private model proposal" not in runtime.state_json()
    assert runtime.ontology.query("Approval") == []
    for forbidden in ("source", "author", "project", "approved", "trusted"):
        injection = runtime.execute({
            "action": "remember_memory",
            "arguments": {"kind": "action", "content": "Escalate this note", forbidden: "human"},
        })
        assert injection.status is DecisionStatus.FAILED
    assert len(runtime.memory.export()["notes"]) == 1


def test_runtime_memory_is_opt_in_and_scope_default_is_stable(tmp_path):
    workspace = tmp_path / "workspace"
    original = Wakeup3LM(workspace)
    assert "recall_memory" not in original.tools
    assert original.memory is None
    database = tmp_path / "memory.sqlite3"
    first = Wakeup3LM(workspace, memory_path=database)
    first.remember_memory("logic", "A project fact")
    restored = Wakeup3LM(workspace, memory_path=database)
    assert restored.project_id == first.project_id
    assert len(restored.recall_memory()) == 1
    another = Wakeup3LM(tmp_path / "another-workspace", memory_path=database)
    assert another.recall_memory() == []


def test_memory_database_cannot_be_inside_workspace_or_enter_through_symlink(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    with pytest.raises(WorkspaceSecurityError, match="outside"):
        Wakeup3LM(workspace, memory_path=workspace / "memory.sqlite3")
    linked = tmp_path / "workspace-alias"
    linked.symlink_to(workspace, target_is_directory=True)
    with pytest.raises(WorkspaceSecurityError, match="outside"):
        Wakeup3LM(workspace, memory_path=linked / "memory.sqlite3")
    runtime = Wakeup3LM(workspace, memory_path=tmp_path / "memory.sqlite3", project_id="project")
    runtime.remember_memory("data", "cross-project-memory-secret")
    (workspace / "linked-memory.sqlite3").symlink_to(tmp_path / "memory.sqlite3")
    assert runtime.workspace.search_files("cross-project-memory-secret") == []
    assert runtime.workspace.search_files("linked-memory") == []
    for action in ("read_file", "write_file", "delete_file"):
        arguments = {"path": "linked-memory.sqlite3"}
        if action == "write_file":
            arguments["content"] = "clobber"
        result = runtime.execute({"action": action, "arguments": arguments})
        assert result.status is DecisionStatus.FAILED
    assert len(runtime.recall_memory("secret")) == 1


def test_workspace_search_still_finds_files_and_safe_internal_symlinks(tmp_path):
    runtime = Wakeup3LM(tmp_path / "workspace")
    runtime.workspace.write_file("src/readme.txt", "Searchable content")
    (runtime.workspace.root / "readme-link.txt").symlink_to(runtime.workspace.root / "src/readme.txt")
    assert sorted(runtime.workspace.search_files("searchable")) == ["readme-link.txt", "src/readme.txt"]
