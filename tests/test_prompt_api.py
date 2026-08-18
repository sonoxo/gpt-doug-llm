import json
from pathlib import Path

import pytest

import prompt_api


def test_safe_relpath_rejects_traversal():
    with pytest.raises(ValueError):
        prompt_api._safe_relpath("../escape.txt")


def test_materialize_writes_project(tmp_path, monkeypatch):
    monkeypatch.setattr(prompt_api, "WORKSPACE", tmp_path.resolve())
    spec = {
        "name": "demo",
        "summary": "demo app",
        "stack": ["html"],
        "run": "python3 -m http.server 8000",
        "files": [
            {"path": "index.html", "content": "<h1>Hello</h1>"},
            {"path": "README.md", "content": "# Demo"},
        ],
    }
    meta = prompt_api.materialize(spec)
    assert meta["name"] == "demo"
    assert (tmp_path / "demo" / "index.html").read_text() == "<h1>Hello</h1>"
    saved = json.loads((tmp_path / "demo" / ".prompt-app.json").read_text())
    assert saved["files"] == ["index.html", "README.md"]
