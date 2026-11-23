"""Offline regression tests for the GPT-DOUG-LLM Law of AI Singularity CI contract."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts import validate_singularity_governance as gate

ROOT = Path(__file__).resolve().parents[1]


class SingularityGovernanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads((ROOT / "config/gpt-doug-singularity-governance.json").read_text())
        cls.registry = json.loads((ROOT / "ecosystem/registry.v4.json").read_text())
        cls.ai = json.loads((ROOT / "config/ai-layer-manifest.json").read_text())
        cls.sweep = (ROOT / ".github/workflows/xzsweep.yml").read_text()
        cls.portfolio = (ROOT / ".github/workflows/sonoxo-portfolio-audit.yml").read_text()

    def validate(self, policy=None, registry=None, ai=None, sweep=None, portfolio=None):
        return gate.validate(
            self.policy if policy is None else policy,
            self.registry if registry is None else registry,
            self.ai if ai is None else ai,
            self.sweep if sweep is None else sweep,
            self.portfolio if portfolio is None else portfolio,
        )

    def test_current_repository_governance_contract_passes(self):
        self.assertEqual(self.validate(), [])
        self.assertEqual(gate.run(), 0)

    def test_gpt_doug_llm_must_be_explicit_canonical_control(self):
        policy = copy.deepcopy(self.policy)
        policy["canonical_control_agent"] = "unknown"
        self.assertTrue(any("GPT-DOUG-LLM" in issue for issue in self.validate(policy=policy)))
        policy = copy.deepcopy(self.policy)
        policy["canonical_control_root"] = "other-org/project"
        self.assertTrue(any("canonical root" in issue for issue in self.validate(policy=policy)))

    def test_project_rule_cannot_be_misrepresented_as_scientific_law(self):
        policy = copy.deepcopy(self.policy)
        policy["kind"] = "PROVEN_SINGULARITY"
        self.assertTrue(self.validate(policy=policy))
        policy = copy.deepcopy(self.policy)
        policy["interpretation"] = "Superintelligence achieved automatically"
        self.assertTrue(self.validate(policy=policy))

    def test_six_ai_layers_and_eight_ontology_planes_are_pinned(self):
        policy = copy.deepcopy(self.policy)
        policy["ai_layers"].remove("agentic_ai")
        self.assertTrue(any("layers" in issue.lower() for issue in self.validate(policy=policy)))
        policy = copy.deepcopy(self.policy)
        policy["ontology_planes"].append("black-house")
        self.assertTrue(any("duplicate" in issue for issue in self.validate(policy=policy)))
        registry = copy.deepcopy(self.registry)
        registry["core_planes"].pop()
        self.assertTrue(any("ecosystem" in issue for issue in self.validate(registry=registry)))

    def test_canonical_ontology_links_to_gpt_doug_llm_singularity_policy(self):
        registry = copy.deepcopy(self.registry)
        registry.pop("gpt_doug_llm_governance")
        findings = self.validate(registry=registry)
        self.assertTrue(any("governance linkage" in issue for issue in findings))

    def test_self_modification_and_external_actions_remain_permission_scoped(self):
        policy = copy.deepcopy(self.policy)
        policy["bounds"]["auto_merge"] = True
        self.assertTrue(any("automatic execution" in issue for issue in self.validate(policy=policy)))
        policy = copy.deepcopy(self.policy)
        policy["automated_actions"].append("operate_physical_device")
        self.assertTrue(any("side effect" in issue for issue in self.validate(policy=policy)))
        policy = copy.deepcopy(self.policy)
        policy["bounds"]["automatic_repair_file_mutations"] = 10
        self.assertTrue(any("file mutation" in issue for issue in self.validate(policy=policy)))

    def test_no_hallucinated_third_party_authority(self):
        policy = copy.deepcopy(self.policy)
        policy["scope_state"]["palantir_foundry_connection"] = "LIVE_AND_CONNECTED"
        self.assertTrue(any("connectivity" in issue for issue in self.validate(policy=policy)))
        policy = copy.deepcopy(self.policy)
        policy["prohibitions"].remove("remote_server_disruption")
        self.assertTrue(any("non-interference" in issue for issue in self.validate(policy=policy)))

    def test_xzsweep_cannot_regain_auto_push_or_write_permissions(self):
        self.assertTrue(any("unsafe automated writes" in issue for issue in self.validate(sweep=self.sweep + "\ngit push origin HEAD:main")))
        self.assertTrue(any("least-privilege" in issue for issue in self.validate(sweep=self.sweep.replace("contents: read","contents: write"))))
        self.assertTrue(any("unsafe automated writes" in issue for issue in self.validate(sweep=self.sweep.replace("scripts/xzsweep.py --hours 24 --report", "scripts/xzsweep.py --hours 24 --apply --report"))))

    def test_portfolio_matrix_runner_incompatibility_is_detected(self):
        changed = self.portfolio.replace("runs-on: ubuntu-24.04", "runs-on: ubuntu-latest", 1)
        self.assertTrue(any("runner" in issue for issue in self.validate(portfolio=changed)))

    def test_cycle_requires_explicit_approval_before_deployment(self):
        policy = copy.deepcopy(self.policy)
        policy["governance_cycle"].remove("authorize")
        self.assertTrue(any("loop" in issue for issue in self.validate(policy=policy)))


if __name__ == "__main__":
    unittest.main()
