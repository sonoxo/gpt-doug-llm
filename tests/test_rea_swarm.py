"""REA swarm security and mock-boundary acceptance tests."""
import hashlib
import json
import os
from pathlib import Path

import pytest

from gpt_chaos.rea_swarm import execute, make_plan


@pytest.fixture
def paths(tmp_path):
    a, b, output = tmp_path / "a", tmp_path / "b", tmp_path / "output"
    for p in (a, b, output):
        p.mkdir()
    return a, b, output


def fake_rea(tmp_path, monkeypatch, code):
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    tool = bindir / "rea"
    tool.write_text("#!/usr/bin/env python3\n" + code + "\n")
    tool.chmod(0o755)
    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.getenv("PATH", ""))


def test_dry_run_has_no_side_effects(paths):
    a, b, output = paths
    plan = make_plan([str(a), str(b)], "javascript", str(output))
    assert plan["state"] == "PLAN_ONLY"
    assert len(plan["jobs"]) == 2
    assert not list(output.iterdir())


@pytest.mark.parametrize("targets,mode", [([], "javascript"), (["relative"], "desktop"),
    (["/tmp/missing-rea-test-9753"], "javascript")])
def test_reject_invalid_paths(paths, targets, mode):
    with pytest.raises(ValueError):
        make_plan(targets, mode, str(paths[2]))


def test_overlap_and_duplicate_rejected(paths):
    a, b, output = paths
    sub = a / "proof"
    sub.mkdir()
    with pytest.raises(ValueError):
        make_plan([str(a)], "desktop", str(sub))
    with pytest.raises(ValueError):
        make_plan([str(a), str(a)], "javascript", str(output))


def test_authorization_required(paths):
    a, b, output = paths
    plan = make_plan([str(a)], "javascript", str(output))
    with pytest.raises(PermissionError):
        execute(plan, authorized=False)


def test_parallel_mock_and_hash(paths, tmp_path, monkeypatch):
    a, b, output = paths
    fake_rea(tmp_path, monkeypatch,
             "import json,sys\nprint(json.dumps({'target':sys.argv[2]}))")
    result = execute(make_plan([str(a), str(b)], "javascript", str(output)),
                     authorized=True)
    assert result["state"] == "PASS"
    assert len(result["results"]) == 2
    folder = Path(result["output_directory"])
    assert folder.stat().st_mode & 0o777 == 0o700
    for row in result["results"]:
        data = (folder / row["evidence"]).read_bytes()
        assert row["sha256"] == hashlib.sha256(data).hexdigest()
        assert json.loads(data)["target"] == row["target"]
    assert (folder / "manifest.json").exists()
    assert not list(a.iterdir()) and not list(b.iterdir())


def test_invalid_json_blocks(paths, tmp_path, monkeypatch):
    a, b, output = paths
    fake_rea(tmp_path, monkeypatch, "print('{not-json')")
    result = execute(make_plan([str(a)], "javascript", str(output)),
                     authorized=True)
    assert result["state"] == "BLOCKED"
    assert [p.name for p in Path(result["output_directory"]).iterdir()] == ["manifest.json"]


def test_nonzero_exit_blocks(paths, tmp_path, monkeypatch):
    a, b, output = paths
    fake_rea(tmp_path, monkeypatch, "import sys\nsys.exit(9)")
    result = execute(make_plan([str(a)], "javascript", str(output)),
                     authorized=True)
    assert result["state"] == "BLOCKED"


def test_stop_fails_closed(paths, tmp_path, monkeypatch):
    a, b, output = paths
    fake_rea(tmp_path, monkeypatch, "print('{}')")
    monkeypatch.setenv("GPT_DOUG_AI_BLOCK_ALL", "1")
    with pytest.raises(PermissionError):
        execute(make_plan([str(a)], "javascript", str(output)), authorized=True)


def test_timeout_fails_closed(paths, tmp_path, monkeypatch):
    a, b, output = paths
    fake_rea(tmp_path, monkeypatch, "import time\ntime.sleep(3)")
    result = execute(make_plan([str(a)], "javascript", str(output)),
                     authorized=True, timeout=1)
    assert result["state"] == "BLOCKED"
