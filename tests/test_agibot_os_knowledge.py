"""Source-grounded AGIBOT OS reference and read-only query regression suite."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

from scripts.agibot_os_knowledge import ONTOLOGY, ROOT, matches, validate


def load() -> dict:
    return json.loads(ONTOLOGY.read_text(encoding="utf-8"))


def call(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "agibot_os_knowledge.py"), *args],
        cwd=ROOT, capture_output=True, text=True, check=False
    )


def test_reference_schema_and_document_review_are_valid() -> None:
    data = load()
    assert validate(data) == []
    assert data["schema"] == "xunia.embodied-os.public-reference.v1"
    assert data["sourceCoverage"]["independentlyBenchmarked"] is False
    assert data["gptDougIntegrationProposal"]["status"] == "DESIGN_ONLY_NOT_IMPLEMENTED"


def test_three_upstream_repositories_are_pinned_not_silently_updated() -> None:
    data = load()
    repos = {r["repository"]: r["headCommit"] for r in data["upstreamRepositories"]}
    assert repos["Link-U-OS/Link-U-OS"] == "64ac7b08dd609dfb463310945856419be470315a"
    assert repos["AgibotTech/agibot_x1_infer"] == "9e0b818804d644fb9c9663e932dd33b03b24dfa4"
    assert repos["AgibotTech/agibot_x1_train"] == "e6651b9ab843fd1b1be70c087bfb7e8b28e44ccd"
    for src in data["sources"]:
        if src["kind"] == "pinned_upstream_file":
            assert f'/blob/{src["commit"]}/' in src["url"]


def test_linku_os_alpha_and_x1_are_distinct_robot_platforms() -> None:
    data = load()
    nodes = {n["id"]: n for n in data["nodes"]}
    assert nodes["linku-os"]["family"] == "link_u_os"
    assert nodes["a2-platform"]["family"] == "link_u_os"
    assert nodes["x1-platform"]["family"] == "agibot_x1"
    assert nodes["aimrt"]["family"] == "shared"
    assert not any(
        e["from"] == "linku-os" and e["to"] == "x1-platform" for e in data["edges"]
    )


def test_search_and_show_return_only_source_backed_claims() -> None:
    data = load()
    hits = matches(data, "AimRT ROS2 Protobuf RPC")
    assert any(hit["id"] == "aimrt" for hit in hits)
    assert all(hit["source_urls"] for hit in hits)
    run = call("show", "x1-training")
    assert run.returncode == 0, run.stderr
    shown = json.loads(run.stdout)
    assert shown["node"]["family"] == "agibot_x1"
    assert shown["sources"][0]["repository"] == "AgibotTech/agibot_x1_train"


def test_cli_diagnostics_and_machine_output() -> None:
    check = call("doctor")
    assert check.returncode == 0, check.stdout + check.stderr
    assert "AGIBOT KNOWLEDGE DOCTOR: GREEN" in check.stdout
    status = call("status", "--json")
    assert status.returncode == 0
    payload = json.loads(status.stdout)
    assert payload["hardware_connected"] is False
    assert payload["simulator_connected"] is False
    graph = call("graph", "--json")
    assert graph.returncode == 0
    assert len(json.loads(graph.stdout)["edges"]) >= 10


def test_broken_source_pinning_fails_closed() -> None:
    data = load()
    data["sources"][2]["commit"] = "0" * 40
    assert any("pinned" in issue or "commit" in issue for issue in validate(data))


def test_dangling_graph_reference_fails_closed() -> None:
    data = load()
    data["edges"][0]["to"] = "imaginary-live-robot"
    assert any("dangling endpoint" in issue for issue in validate(data))


def test_governance_fails_closed_on_hardware_promotion() -> None:
    data = load()
    data["gptDougIntegrationProposal"]["robotCommandsEnabled"] = True
    data["guardrails"]["noHardwareControl"] = False
    issues = validate(data)
    assert any("robotCommandsEnabled" in issue for issue in issues)
    assert any("noHardwareControl" in issue for issue in issues)


def test_action_cannot_gain_network_or_mutation_authority() -> None:
    data = load()
    data["actions"][0]["networkEgress"] = True
    data["actions"][0]["externalMutation"] = True
    assert any("non-read-only action rejected" in issue for issue in validate(data))


def test_upstream_license_not_inherited_by_unreviewed_submodules() -> None:
    data = load()
    root = next(x for x in data["upstreamRepositories"] if x["repository"] == "Link-U-OS/Link-U-OS")
    training = next(x for x in data["upstreamRepositories"] if x["repository"] == "AgibotTech/agibot_x1_train")
    assert root["licenseAtRepositoryRoot"] == "MulanPSL-2.0"
    assert training["licenseAtRepositoryRoot"] == "NOT_REVIEWED"
    assert data["guardrails"]["separateSubmoduleLicenseReviewRequired"] is True


def test_no_claim_of_connected_teleoperation_or_deployment() -> None:
    data = load()
    proposal = data["gptDougIntegrationProposal"]
    assert proposal["simulatorConnected"] is False
    assert proposal["hardwareConnected"] is False
    assert proposal["robotCommandsEnabled"] is False
    assert data["guardrails"]["noTeleoperation"] is True
    assert data["guardrails"]["noRobotDeployment"] is True
    assert all(action["robotControl"] is False for action in data["actions"])
