from doug_core.classifier import classify
from doug_core.evaluator import evaluate
from doug_core.reasoner import reason
from doug_core.router import route
from doug_core.runtime import DougRuntime
from doug_core.use_cases import list_use_cases
from doug_core.use_case_engine import run_use_case
from doug_core.verifier import verify_text
from doug_core.workspace import inspect_workspace


def test_coding_classifier():
    task = classify(
        "Fix this Python API"
    )

    assert task.task_type == "coding"
    assert task.needs_code


def test_security_classifier():
    task = classify(
        "Audit this repository security"
    )

    assert task.task_type == "security"


def test_offline_provider():
    task = classify(
        "Inspect local project"
    )

    providers = route(task)

    assert providers
    assert any(
        item.name == "offline"
        for item in providers
    )


def test_no_ollama_endpoint():
    result = verify_text(
        "hello",
        "Use localhost:11434",
    )

    assert result.score < 1.0


def test_reasoner():
    ctx = reason(
        "Build locally without Ollama"
    )

    assert ctx.plan
    assert ctx.risks


def test_workspace():
    report = inspect_workspace(".")

    assert report.files > 0


def test_use_cases():
    cases = list_use_cases()

    assert len(cases) >= 10


def test_operator():
    result = run_use_case(
        "operator",
        ".",
    )

    assert result.actions


def test_release():
    result = run_use_case(
        "release",
        ".",
    )

    assert (
        0
        <= result.data[
            "readiness_score"
        ]
        <= 100
    )


def test_runtime():
    runtime = DougRuntime()

    result = runtime.offline_response(
        "Inspect this project"
    )

    assert result.answer
    assert result.provider


def test_eval():
    result = evaluate()

    assert result["score"] >= 0.8
