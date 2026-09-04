from wakeup3lm.ontology import OntologyGraph
from wakeup3lm.runtime import DecisionStatus, Wakeup3LM
from wakeup3lm.workspace import WorkspaceFS


def test_ontology_batch_coalesces_snapshot_writes(tmp_path, monkeypatch):
    state_path = tmp_path / "ontology.json"
    graph = OntologyGraph(state_path)
    writes = 0
    original = graph._persist_now

    def counted_persist():
        nonlocal writes
        writes += 1
        original()

    monkeypatch.setattr(graph, "_persist_now", counted_persist)

    with graph.batch():
        graph.upsert("Workspace", "default", root=str(tmp_path))
        graph.upsert("Model", "wakeup3lm", role="IDE LLM")
        graph.link("Model", "wakeup3lm", "OPERATES_IN", "Workspace", "default")

    assert writes == 1
    assert state_path.exists()

    restored = OntologyGraph(state_path)
    assert restored.get("Workspace", "default") is not None
    assert restored.get("Model", "wakeup3lm") is not None
    assert len(restored.links) == 1


def test_runtime_uses_two_durable_phases_per_successful_tool_call(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "hello.txt").write_text("hello\n", encoding="utf-8")
    runtime = Wakeup3LM(workspace, tmp_path / "runtime-state.json")

    writes = 0
    original = runtime.ontology._persist_now

    def counted_persist():
        nonlocal writes
        writes += 1
        original()

    monkeypatch.setattr(runtime.ontology, "_persist_now", counted_persist)

    result = runtime.execute(
        {
            "action": "read_file",
            "arguments": {"path": "hello.txt"},
            "rationale": "optimization regression test",
        }
    )

    assert result.status == DecisionStatus.PASSED
    assert result.output == "hello\n"
    assert writes == 2


def test_workspace_search_prunes_generated_dependency_trees(tmp_path):
    workspace = WorkspaceFS(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "keep.txt").write_text("needle\n", encoding="utf-8")
    (tmp_path / "node_modules" / "pkg").mkdir(parents=True)
    (tmp_path / "node_modules" / "pkg" / "noise.txt").write_text("needle\n", encoding="utf-8")

    matches = workspace.search_files("needle")

    assert "src/keep.txt" in matches
    assert all(not path.startswith("node_modules/") for path in matches)
