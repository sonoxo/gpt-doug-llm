import json

import pytest

from cloud_nxyz import CloudNXYZEngine
from universal_hive.apm_law import APMLaw


def _manifest(tmp_path):
    tf = tmp_path / "infra" / "terraform"
    tf.mkdir(parents=True)
    (tf / "main.tf").write_text('terraform {}\n', encoding="utf-8")
    k8s = tmp_path / "infra" / "app.yaml"
    k8s.write_text(
        "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: nxyz\n",
        encoding="utf-8",
    )
    return {
        "project": "nxyz-demo",
        "monitoring": "api",
        "components": [
            {
                "id": "foundation",
                "provider": "aws",
                "iac_tool": "terraform",
                "config_path": "infra/terraform",
            },
            {
                "id": "app",
                "provider": "generic",
                "iac_tool": "kubernetes",
                "config_path": "infra/app.yaml",
                "depends_on": ["foundation"],
            },
        ],
    }


def test_apm_law_accepts_verified_reversible_procedure():
    law = APMLaw()
    verdict = law.validate_procedure(
        {
            "procedure_verified": True,
            "provenance": {"source": "test"},
            "context_validation": "validate",
            "authorization_boundary": "explicit",
            "rollback": "restore",
        },
        requires_mutation=True,
    )
    assert verdict["valid"] is True


def test_apm_law_rejects_permissionless_memory_reuse():
    law = APMLaw()
    verdict = law.validate_procedure(
        {
            "verified": True,
            "provenance": {"source": "test"},
            "context_validation": "validate",
            "rollback": "restore",
        },
        requires_mutation=True,
    )
    assert verdict["valid"] is False
    assert "APM-AUTHORITY" in verdict["failed"]


def test_cloud_nxyz_builds_provider_neutral_component_dag(tmp_path):
    engine = CloudNXYZEngine(root=tmp_path, state_dir=tmp_path / ".state")
    plan = engine.plan("deploy nxyz", _manifest(tmp_path))

    assert plan["apm_validation"]["valid"] is True
    assert [row["component_id"] for row in plan["components"]] == ["foundation", "app"]
    assert plan["components"][0]["iac_tool"] == "terraform"
    assert plan["components"][1]["iac_tool"] == "kubernetes"
    assert plan["monitoring"]["feedback_to_apm"] is True


def test_cloud_nxyz_default_execution_is_preview_only(tmp_path):
    engine = CloudNXYZEngine(root=tmp_path, state_dir=tmp_path / ".state")
    plan = engine.plan("deploy nxyz", _manifest(tmp_path))
    receipt = engine.execute(plan)

    assert receipt["status"] == "PLANNED"
    assert receipt["executed"] is False
    assert engine.accelerator.status()["event_count"] == 0


def test_cloud_nxyz_external_execution_requires_gate(tmp_path, monkeypatch):
    monkeypatch.delenv("GPT_DOUG_CLOUD_NXYZ_EXECUTE", raising=False)
    engine = CloudNXYZEngine(root=tmp_path, state_dir=tmp_path / ".state")
    plan = engine.plan("deploy nxyz", _manifest(tmp_path))

    with pytest.raises(PermissionError):
        engine.execute(plan, execute=True)


def test_cloud_nxyz_verified_outcome_feeds_apm(tmp_path):
    engine = CloudNXYZEngine(root=tmp_path, state_dir=tmp_path / ".state")
    plan = engine.plan("deploy nxyz", _manifest(tmp_path))
    receipt = {
        "status": "PASSED",
        "executed": True,
        "monitoring_attachment_status": "READY_FOR_MONITORING_BIND",
        "components": [{"component_id": "foundation", "steps": [{"phase": "apply", "status": "PASSED", "exit_code": 0}]}],
    }
    event = engine.record_outcome(plan, receipt)

    assert event["automation_type"] == "cloud-nxyz"
    assert engine.accelerator.status()["event_count"] == 1
    assert engine.learned_template()["automation_type"] == "cloud-nxyz"


def test_cloud_nxyz_rejects_config_escape(tmp_path):
    engine = CloudNXYZEngine(root=tmp_path, state_dir=tmp_path / ".state")
    manifest = {
        "components": [{
            "id": "escape",
            "provider": "generic",
            "iac_tool": "kubernetes",
            "config_path": "../outside.yaml",
        }]
    }
    with pytest.raises(ValueError):
        engine.plan("deploy", manifest)


def test_cloud_nxyz_refuses_to_learn_unexecuted_success(tmp_path):
    engine = CloudNXYZEngine(root=tmp_path, state_dir=tmp_path / ".state")
    plan = engine.plan("deploy nxyz", _manifest(tmp_path))
    with pytest.raises(ValueError):
        engine.record_outcome(
            plan,
            {
                "status": "PASSED",
                "executed": False,
                "components": [{"component_id": "foundation"}],
            },
        )
