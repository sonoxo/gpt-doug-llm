import json

from knowledge.store import KnowledgeStore


def test_knowledge_index(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    (repo / "app.py").write_text(
        "def build_graph():\n"
        "    return 'ontology engine'\n",
        encoding="utf-8",
    )

    document = (
        repo
        / ".doug"
        / "ontology"
        / "documents"
        / "doc_test"
    )

    document.mkdir(
        parents=True
    )

    (
        document
        / "pages.jsonl"
    ).write_text(
        json.dumps(
            {
                "page": 7,
                "source_file": "report.pdf",
                "text": (
                    "SilverTech supplied "
                    "CNC machine tools."
                ),
            }
        )
        + "\n",
        encoding="utf-8",
    )

    (repo / ".env").write_text(
        "SECRET_VALUE=do_not_index",
        encoding="utf-8",
    )

    store = KnowledgeStore(
        repo
        / ".doug"
        / "knowledge"
    )

    result = store.rebuild(repo)

    assert result["chunks"] >= 2

    hits = store.search(
        "SilverTech"
    )

    assert hits
    assert any(
        "SilverTech" in hit["text"]
        for hit in hits
    )

    secret_hits = store.search(
        "do_not_index"
    )

    assert secret_hits == []
