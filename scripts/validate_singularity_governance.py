#!/usr/bin/env python3
"""Validate GPT-DOUG-LLM's declared Law of AI Singularity governance contract.

This enforces repository-side engineering boundaries only. It does not confer
authority to external systems, and does not claim AGI, Palantir connectivity,
or continuous autonomous execution.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config" / "gpt-doug-singularity-governance.json"
REGISTRY = ROOT / "ecosystem" / "registry.v4.json"
LAYERS = ROOT / "config" / "ai-layer-manifest.json"
XZSWEEP = ROOT / ".github" / "workflows" / "xzsweep.yml"
PORTFOLIO = ROOT / ".github" / "workflows" / "sonoxo-portfolio-audit.yml"

REQUIRED_PLANES = {
    "black-house", "xunia-hq", "xunia-domain-root", "zyra",
    "red-house", "green-house", "orange-house", "glass-onion-spatial",
}
REQUIRED_LAYERS = {
    "classical_ai", "machine_learning", "neural_networks",
    "deep_learning", "generative_ai", "agentic_ai",
}
REQUIRED_CYCLE = [
    "observe", "propose", "test", "review",
    "authorize", "deploy", "verify", "learn",
]
EXTERNAL_AUTHORIZED = {
    "merge_reviewed_pull_request",
    "change_production_configuration",
    "deploy_external_system",
    "run_active_external_assessment",
    "spend_money",
    "operate_physical_device",
}
PROHIBITED = {
    "remote_server_disruption",
    "unauthorized_network_assessment",
    "secret_exfiltration",
    "unbounded_self_replication",
    "unreviewed_dependency_upgrades",
    "suppression_of_failing_checks",
    "fabricated_telemetry",
}


def _identifiers(items: object, label: str, errors: list[str]) -> set[str]:
    if not isinstance(items, list) or not all(isinstance(x, str) for x in items):
        errors.append(f"{label} is not a list of identifiers")
        return set()
    if len(items) != len(set(items)):
        errors.append(f"{label} has duplicate identifiers")
    return set(items)


def validate(
    policy: dict, registry: dict, ai: dict, xzsweep: str, portfolio: str
) -> list[str]:
    """Return explicit drift findings; callers can test modified copies offline."""
    errors: list[str] = []
    if policy.get("schema") != "gpt-doug-llm/singularity-governance/v1":
        errors.append("singularity schema mismatch")
    if policy.get("kind") != "PROJECT_DEFINED_ENGINEERING_GOVERNANCE":
        errors.append("scientific status is not misrepresented")
    if policy.get("name") != "GPT-DOUG-LLM // Law of AI Singularity":
        errors.append("control name drifted")
    if policy.get("canonical_control_agent") != "GPT-DOUG-LLM":
        errors.append("GPT-DOUG-LLM control agent missing")
    for item in (policy, registry):
        if item.get("canonical_control_root") != "sonoxo/gpt-doug-llm":
            errors.append("canonical root must remain sonoxo/gpt-doug-llm")
    if policy.get("source_of_truth") != [
        "ecosystem/registry.v4.json", "config/ai-layer-manifest.json"
    ]:
        errors.append("ontology evidence source drifted")
    if _identifiers(policy.get("ontology_planes"), "policy planes", errors) != REQUIRED_PLANES:
        errors.append("policy planes are incomplete or unexpected")
    planes = registry.get("core_planes")
    if not isinstance(planes, list) or {p.get("id") for p in planes if isinstance(p, dict)} != REQUIRED_PLANES:
        errors.append("canonical ecosystem planes drifted")
    if _identifiers(policy.get("ai_layers"), "policy AI layers", errors) != REQUIRED_LAYERS:
        errors.append("AI architecture layers drifted")
    layers = ai.get("required_layer_ids")
    if _identifiers(layers, "architecture AI layers", errors) != REQUIRED_LAYERS:
        errors.append("existing architecture contract drifted")
    if policy.get("governance_cycle") != REQUIRED_CYCLE:
        errors.append("observe/test/review/authorize loop drifted")
    registry_binding = registry.get("gpt_doug_llm_governance")
    if not isinstance(registry_binding, dict) or registry_binding.get("policy") != "config/gpt-doug-singularity-governance.json" or registry_binding.get("title") != "GPT-DOUG-LLM // Law of AI Singularity" or registry_binding.get("cycle") != REQUIRED_CYCLE:
        errors.append("canonical GPT-DOUG-LLM singularity governance linkage missing")

    if not isinstance(policy.get("interpretation"), str) or "not an established scientific law" not in policy["interpretation"]:
        errors.append("project-defined status disclosure missing")
    if policy.get("effective_scope") != "REPOSITORY_CI_AND_DECLARED_GOVERNANCE_CONTRACT":
        errors.append("contract cannot claim to control unattached runtimes")
    state = policy.get("scope_state", {})
    if not isinstance(state, dict) or state.get("palantir_foundry_connection") != "NOT_VERIFIED" or state.get("military_infrastructure_control") != "NONE" or state.get("external_system_access") != "EXPLICIT_AUTHORIZATION_ONLY":
        errors.append("external connectivity/authority boundary violated")
    bounds = policy.get("bounds", {})
    required_bools = {
        "auto_merge": False,
        "force_push": False,
        "silent_direct_main_commits": False,
        "unrestricted_external_actions": False,
        "paid_api_requirement": False,
        "local_or_free_only": True,
    }
    if not isinstance(bounds, dict) or any(bounds.get(k) is not v for k, v in required_bools.items()):
        errors.append("automatic execution/payment policy widened")
    if not isinstance(bounds, dict) or bounds.get("automatic_repair_file_mutations") != 0:
        errors.append("scheduled automatic file mutation not allowed")
    for k, ceiling in (
        ("max_parallel_review_workers", 8),
        ("max_automated_remediation_attempts", 2),
    ):
        value = bounds.get(k) if isinstance(bounds, dict) else None
        if type(value) is not int or not 0 <= value <= ceiling:
            errors.append(f"{k} exceeds bounded-execution policy")
    automation = _identifiers(policy.get("automated_actions"), "automatic actions", errors)
    if not {"read_repository_state", "run_offline_tests", "publish_evidence_artifacts"} <= automation:
        errors.append("required harmless automatic actions missing")
    if automation & EXTERNAL_AUTHORIZED:
        errors.append("external side effect is listed as automatic")
    if not _identifiers(policy.get("authorized_actions"), "approved actions", errors) >= EXTERNAL_AUTHORIZED:
        errors.append("high-impact human-approved action boundary is incomplete")
    if not _identifiers(policy.get("prohibitions"), "prohibited actions", errors) >= PROHIBITED:
        errors.append("non-interference boundary is incomplete")
    recovery = policy.get("recovery", {})
    if not isinstance(recovery, dict) or recovery.get("human_approval_required") is not True or recovery.get("push_permission_failure") != "DO_NOT_ESCALATE_TOKENS_SWITCH_TO_READ_ONLY_REPORT":
        errors.append("recovery flow may escalate privileges")
    control = policy.get("controls", {})
    if not isinstance(control, dict) or control.get("xzsweep_workflow") != ".github/workflows/xzsweep.yml" or control.get("portfolio_workflow") != ".github/workflows/sonoxo-portfolio-audit.yml":
        errors.append("infrastructure recovery controls drifted")
    if any(token in xzsweep for token in ("--apply", "git push", "git add -A", "git commit", "contents: write", "force-push")):
        errors.append("XZSWEEP attempts unsafe automated writes")
    if "permissions:\n  contents: read" not in xzsweep or "persist-credentials: false" not in xzsweep:
        errors.append("XZSWEEP is not least-privilege")
    if "scripts/xzsweep.py --hours 24 --report .xzsweep/freshness.json" not in xzsweep:
        errors.append("XZSWEEP audit does not run in read-only mode")
    if "actions/upload-artifact@v4" not in xzsweep or "git diff --exit-code" not in xzsweep:
        errors.append("XZSWEEP lacks audit evidence/immutability check")
    if "offline-portfolio:\n    # Ubuntu 26.04 images do not provide Python 3.9 via setup-python; pin stable runner.\n    runs-on: ubuntu-24.04" not in portfolio:
        errors.append("portfolio Python 3.9 job lacks compatible pinned runner")
    if "python-version: ['3.9', '3.12']" not in portfolio:
        errors.append("portfolio compatible Python matrix drifted")
    return errors


def run(root: Path = ROOT) -> int:
    try:
        policy = json.loads((root / "config/gpt-doug-singularity-governance.json").read_text())
        registry = json.loads((root / "ecosystem/registry.v4.json").read_text())
        ai = json.loads((root / "config/ai-layer-manifest.json").read_text())
        sweep = (root / ".github/workflows/xzsweep.yml").read_text()
        portfolio = (root / ".github/workflows/sonoxo-portfolio-audit.yml").read_text()
    except (OSError, ValueError) as exc:
        print("GPT-DOUG-LLM SINGULARITY: FAIL - missing/invalid governance evidence:", exc)
        return 1
    failures = validate(policy, registry, ai, sweep, portfolio)
    if failures:
        print("GPT-DOUG-LLM SINGULARITY: FAIL")
        for finding in failures:
            print(" -", finding)
        return 1
    print("GPT-DOUG-LLM SINGULARITY: PASS (repository governance contract only)")
    print(f"Control: {policy['canonical_control_root']}")
    print(f"Ontology planes: {len(policy['ontology_planes'])}; AI layers: {len(policy['ai_layers'])}")
    print("XZSWEEP: report-only; portfolio: compatible runner; external actions: require authorization")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
