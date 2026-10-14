"""BioPINEAL no-unnecessary-guardrails is limited to offline research."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from research_lab.warfighter import research_freedom
from research_lab.warfighter.cli import main


class ResearchFreedomTests(unittest.TestCase):
    def test_safe_offline_actions_do_not_require_extra_approval(self):
        for action in (
            'source_search', 'read_heartbeat', 'operator_show',
            'simulate_classical_quantum', 'validate_synthetic_scenario',
            'validate_research_ontology',
        ):
            with self.subTest(action=action):
                result = research_freedom.evaluate(action)
                self.assertEqual(result['decision'], 'NO_EXTRA_REVIEW_REQUIRED')
                self.assertEqual(result['authority'], 'RESEARCH_ONLY')
                self.assertTrue(result['input_validation_still_required'])
                self.assertTrue(result['existing_security_controls_unchanged'])
                self.assertFalse(result['grants_external_permission'])

    def test_external_publication_privileges_and_unknown_actions_not_covered(self):
        for action in ('publish', 'pineal_project', 'operator_register',
                       'grant_military_authority', 'hardware_connect',
                       'exploit_external_system', 'weapons_control',
                       'run_unbounded_agents', 'unknown_action'):
            with self.subTest(action=action):
                result = research_freedom.evaluate(action)
                self.assertEqual(result['decision'], 'NORMAL_CONTROLS_REQUIRED')
                self.assertFalse(result['grants_external_permission'])
                self.assertTrue(result['existing_security_controls_unchanged'])

    def test_policy_does_not_allow_credential_or_patent_rights_bypass(self):
        policy = research_freedom.load_policy()
        self.assertEqual(policy['id'], 'BIOPINEAL_NO_UNNECESSARY_GUARDRAILS_V1')
        self.assertEqual(policy['scope'], 'LOCAL_SYNTHETIC_RESEARCH_ONLY')
        self.assertFalse(policy['disables_existing_security_controls'])
        self.assertFalse(policy['grants_government_authority'])
        self.assertFalse(policy['grants_patent_or_third_party_rights'])
        self.assertFalse(policy['automatic_publication'])
        self.assertEqual(set(policy['no_extra_review_actions']), {
            'source_search', 'read_heartbeat', 'operator_show',
            'simulate_classical_quantum', 'validate_synthetic_scenario',
            'validate_research_ontology',
        })

    def test_forged_policy_escalation_rejected(self):
        policy = research_freedom.load_policy()
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / 'policy.json'
            for mutation in (
                lambda v: v.update(disables_existing_security_controls=True),
                lambda v: v.update(grants_government_authority=True),
                lambda v: v['no_extra_review_actions'].append('publish'),
                lambda v: v['no_extra_review_actions'].append('hardware_connect'),
                lambda v: v.update(automatic_publication=True),
                lambda v: v.update(authority='OPERATIONAL'),
            ):
                payload = json.loads(json.dumps(policy))
                mutation(payload)
                dest.write_text(json.dumps(payload), encoding='utf-8')
                with self.subTest(mutation=mutation):
                    with self.assertRaises(ValueError):
                        research_freedom.load_policy(dest)

    def test_invalid_nested_policy_action_does_not_crash_with_typeerror(self):
        payload = research_freedom.load_policy()
        payload['no_extra_review_actions'][-1] = {'action': 'publish'}
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / 'policy.json'
            target.write_text(json.dumps(payload), encoding='utf-8')
            with self.assertRaises(ValueError):
                research_freedom.load_policy(target)

    def test_cli_reports_rule_without_executing_requested_action(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = main(['biopineal', 'freedom', '--action', 'simulate_classical_quantum'])
        self.assertEqual(result, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload['decision'], 'NO_EXTRA_REVIEW_REQUIRED')
        self.assertEqual(payload['external_calls'], 0)
        self.assertFalse(payload['action_executed'])
        self.assertEqual(payload['authority'], 'RESEARCH_ONLY')

    def test_unlisted_actions_are_not_promoted_through_cli(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = main(['biopineal', 'freedom', '--action', 'publish'])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(out.getvalue())['decision'], 'NORMAL_CONTROLS_REQUIRED')


if __name__ == '__main__':
    unittest.main()
