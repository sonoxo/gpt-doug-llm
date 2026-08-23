from __future__ import annotations

import json
from pathlib import Path

import pytest

from zyra_control_plane.attestation import AttestationSigner
from zyra_control_plane.benchmark import BenchmarkSuite
from zyra_control_plane.capabilities import CapabilityRegistry, READ_ONLY, WRITE_LOCAL
from zyra_control_plane.control_plane import MissionControl
from zyra_control_plane.dag import MissionDAG, MissionStep, StepResult
from zyra_control_plane.journal import MissionJournal
from zyra_control_plane.sandbox import PreviewProcessManager, SandboxCommand, SandboxRunner


def test_journal_is_hash_chained_and_signed(tmp_path: Path) -> None:
    journal = MissionJournal(tmp_path / "events.jsonl")
    journal.append("m1", "MISSION_CREATED", data={"x": 1})
    journal.append("m1", "PLAN_CREATED", data={"steps": 2})
    assert journal.verify()["ok"] is True

    rows = journal.path.read_text().splitlines()
    tampered = json.loads(rows[0])
    tampered["data"]["x"] = 9
    rows[0] = json.dumps(tampered)
    journal.path.write_text("\n".join(rows) + "\n")
    assert journal.verify()["ok"] is False


def test_capability_registry_enforces_write_and_network_boundaries() -> None:
    registry = CapabilityRegistry()
    ok, missing = registry.authorize("zyra", READ_ONLY, ("compile",))
    assert not ok
    assert "compile" in missing
    assert "write-boundary" in missing

    ok, missing = registry.authorize("zyra", WRITE_LOCAL, ("compile", "manifest"))
    assert ok
    assert missing == ()


def test_dag_levels_and_failure_blocking() -> None:
    dag = MissionDAG(
        [
            MissionStep("a", "A", "gpt-doug-core"),
            MissionStep("b", "B", "zyra", depends_on=("a",)),
            MissionStep("c", "C", "security", depends_on=("b",)),
        ]
    )
    seen = []

    def runner(step: MissionStep) -> StepResult:
        seen.append(step.step_id)
        return StepResult(step.step_id, step.step_id != "b")

    results = dag.execute(runner)
    assert results["a"].ok
    assert not results["b"].ok
    assert not results["c"].ok
    assert seen == ["a", "b"]


def test_dag_cycle_rejected() -> None:
    with pytest.raises(ValueError, match="cycle"):
        MissionDAG(
            [
                MissionStep("a", "A", "gpt-doug-core", depends_on=("b",)),
                MissionStep("b", "B", "gpt-doug-core", depends_on=("a",)),
            ]
        )


def test_sandbox_is_ephemeral_and_preserves_lockfiles(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("print('ok')\n")
    (tmp_path / "requirements.txt").write_text("pytest\n")
    with SandboxRunner(tmp_path) as sandbox:
        result = sandbox.run(SandboxCommand(("python", "-m", "compileall", "-q", ".")))
        manifest = sandbox.artifact_manifest()
        assert result["ok"] is True
        assert result["lockfiles_unchanged"] is True
        assert "app.py" in manifest["files"]
        sandbox_root = sandbox.root
    assert sandbox_root is not None
    assert not sandbox_root.exists()


def test_sandbox_rejects_non_allowlisted_executable(tmp_path: Path) -> None:
    (tmp_path / "x.py").write_text("pass\n")
    with SandboxRunner(tmp_path) as sandbox:
        with pytest.raises(PermissionError):
            sandbox.run(SandboxCommand(("bash", "-c", "echo nope")))


def test_attestation_sign_and_verify(tmp_path: Path) -> None:
    signer = AttestationSigner(tmp_path / "key")
    attestation = signer.sign(
        mission_id="m1",
        prompt="build",
        commit_sha="abc",
        model_route="ollama",
        changed_files=["a.py"],
        checks=[{"name": "tests", "ok": True}],
        journal_head="123",
    )
    assert signer.verify(attestation)
    attestation["commit_sha"] = "bad"
    assert not signer.verify(attestation)


def test_mission_control_executes_and_attests(tmp_path: Path) -> None:
    control = MissionControl(tmp_path / "state")
    dag = MissionDAG(
        [
            MissionStep(
                "inspect",
                "Inspect",
                "gpt-doug-core",
                capabilities=("plan", "journal"),
                acceptance=("plan exists",),
            ),
            MissionStep(
                "compile",
                "Compile",
                "zyra",
                depends_on=("inspect",),
                capabilities=("compile", "manifest"),
                acceptance=("manifest exists",),
            ),
        ]
    )
    mission = control.new_mission("build app", dag)

    def executor(step: MissionStep) -> StepResult:
        return StepResult(step.step_id, True, evidence={"acceptance": list(step.acceptance)})

    result = control.execute(mission, {"gpt-doug-core": executor, "zyra": executor})
    assert result["verified"] is True
    attestation = control.attest(mission, result, commit_sha="abc", changed_files=["x.py"])
    assert control.signer.verify(attestation)
    assert control.journal.verify()["ok"] is True


def test_benchmark_penalizes_false_success() -> None:
    suite = BenchmarkSuite()

    def runner(case):
        return {
            "completed": True,
            "verified": case.case_id != "security-gate",
            "claimed_success": True,
            "rolled_back": case.case_id == "rollback",
        }

    score = suite.run(runner)
    assert score["false_success_rate"] > 0
    assert score["score"] < 100


def test_sandbox_diff_preview(tmp_path: Path) -> None:
    (tmp_path / "app.txt").write_text("old\n")
    with SandboxRunner(tmp_path) as sandbox:
        assert sandbox.root is not None
        (sandbox.root / "app.txt").write_text("new\n")
        diffs = sandbox.diff_against_source()
        assert "app.txt" in diffs
        assert "-old" in diffs["app.txt"]
        assert "+new" in diffs["app.txt"]


def test_preview_process_lifecycle(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<h1>ok</h1>")
    preview = PreviewProcessManager(tmp_path)
    started = preview.start()
    assert started["ok"] is True
    assert str(started["url"]).startswith("http://127.0.0.1:")
    stopped = preview.stop()
    assert stopped["ok"] is True
    assert stopped["stopped"] is True


def test_benchmark_regression_guard() -> None:
    baseline = {"score": 95, "median_duration_ms": 1000}
    current = {"score": 94, "median_duration_ms": 1100}
    result = BenchmarkSuite.compare_scorecards(current, baseline)
    assert result["ok"] is True

    bad = BenchmarkSuite.compare_scorecards(
        {"score": 80, "median_duration_ms": 2000},
        baseline,
    )
    assert bad["ok"] is False


def test_benchmark_matrix_repeatability() -> None:
    suite = BenchmarkSuite()

    def runner(case):
        return {
            "completed": True,
            "verified": True,
            "rolled_back": case.case_id == "rollback",
        }

    matrix = suite.run_matrix({"model-a": runner, "model-b": runner})
    assert matrix["repeatability"]["model_count"] == 2
    assert matrix["repeatability"]["score_stddev"] == 0
