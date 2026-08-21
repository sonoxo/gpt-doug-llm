from pathlib import Path

import pytest

import xunia_godis as xg


def test_resolve_profile_alias_and_model_name():
    assert xg.resolve_profile("godis").model == "gpt-xunia-godis"
    assert xg.resolve_profile("gpt-xunia-rag").key == "rag"
    with pytest.raises(ValueError):
        xg.resolve_profile("missing")


def test_render_modelfile_replaces_only_base_model(tmp_path: Path):
    source = tmp_path / "Modelfile"
    source.write_text("FROM old:model\n\nPARAMETER temperature 0.2\n", encoding="utf-8")
    rendered = xg._render_modelfile(source, "new:model")
    assert rendered.startswith("FROM new:model\n")
    assert "PARAMETER temperature 0.2" in rendered


def test_retrieve_finds_relevant_local_context_and_skips_node_modules(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "architecture.md").write_text(
        "XUNIA uses Ollama for local model inference. RAG retrieves local documents.",
        encoding="utf-8",
    )
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "noise.md").write_text(
        "Ollama Ollama Ollama unrelated vendored text",
        encoding="utf-8",
    )
    hits = xg.retrieve(tmp_path, "How does XUNIA use Ollama for local inference?", top_k=3)
    assert hits
    assert hits[0].path == "docs/architecture.md"
    assert all("node_modules" not in hit.path for hit in hits)


def test_format_context_contains_source_labels():
    chunks = [xg.Chunk("README.md", 2, "hello", 1.0)]
    assert xg.format_context(chunks) == "[source:README.md#2]\nhello"


def test_parser_accepts_http_mcp_list():
    args = xg.build_parser().parse_args(["mcp-list", "--url", "http://127.0.0.1:9000/mcp"])
    assert args.command == "mcp-list"
    assert args.url.endswith("/mcp")
    assert args.stdio is None


def test_parser_accepts_stdio_mcp_list():
    args = xg.build_parser().parse_args(["mcp-list", "--stdio", "python3", "server.py"])
    assert args.stdio == ["python3", "server.py"]
