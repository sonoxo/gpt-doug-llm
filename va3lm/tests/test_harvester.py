from __future__ import annotations

from pathlib import Path

from va3lm.harvester import OntologiHarvester
from va3lm.ontologi import OntologiEngine


def test_harvester_processes_changed_repo_files_and_skips_secrets(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text(
        "Virginia learns candidate knowledge through governed ontology seeds.\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / ".env").write_text("TOKEN=never-ingest\n", encoding="utf-8")
    checkpoint = tmp_path / ".state" / "harvest.json"
    harvester = OntologiHarvester(OntologiEngine.load_default())

    first = harvester.harvest(tmp_path, roots=("docs",), checkpoint_path=checkpoint)
    second = harvester.harvest(tmp_path, roots=("docs",), checkpoint_path=checkpoint)

    assert first["processedFiles"] == 1
    assert first["createdSeeds"] == 1
    assert first["blockedFiles"] == 1
    assert first["automaticPromotion"] is False
    assert second["processedFiles"] == 0
    assert second["unchangedFiles"] == 1


def test_harvester_reprocesses_modified_artifact(tmp_path: Path):
    (tmp_path / "intel").mkdir()
    source = tmp_path / "intel" / "brief.md"
    source.write_text("Evidence must preserve provenance before a claim is promoted.\n", encoding="utf-8")
    checkpoint = tmp_path / "checkpoint.json"
    harvester = OntologiHarvester(OntologiEngine.load_default())
    harvester.harvest(tmp_path, roots=("intel",), checkpoint_path=checkpoint)

    source.write_text("Evidence must preserve provenance before a claim is promoted.\nContradictory claims should be surfaced for review.\n", encoding="utf-8")
    result = harvester.harvest(tmp_path, roots=("intel",), checkpoint_path=checkpoint)

    assert result["processedFiles"] == 1
    assert result["createdSeeds"] == 1


def test_harvester_reads_python_docstrings(tmp_path: Path):
    (tmp_path / "va3lm").mkdir()
    (tmp_path / "va3lm" / "agent.py").write_text(
        '"""Virginia routes structured knowledge through ONTologi Cortex."""\n',
        encoding="utf-8",
    )
    harvester = OntologiHarvester(OntologiEngine.load_default())
    result = harvester.harvest(tmp_path, roots=("va3lm",))
    assert result["processedFiles"] == 1
    assert result["createdSeeds"] == 1


def test_harvester_rejects_root_escape(tmp_path: Path):
    harvester = OntologiHarvester(OntologiEngine.load_default())
    try:
        harvester.harvest(tmp_path, roots=("../outside",))
    except ValueError as exc:
        assert "escaped repository boundary" in str(exc)
    else:
        raise AssertionError("expected repository boundary rejection")
