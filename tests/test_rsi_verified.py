"""Offline tests for trusted repeated RSI measurements and audit boundaries."""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
# In the full repository, the real rsi_supervisor and zyra_agent modules are imported.
import rsi_verified as rv  # noqa: E402
from rsi_supervisor import Metrics  # noqa: E402


class VerifiedRSITests(unittest.TestCase):
    def test_repeatable_measurements(self):
        calls = []
        def good():
            calls.append(1)
            return Metrics(0.7, 0, True)
        b = rv.VerifiedBenchmark(good, repeats=3)
        self.assertEqual(b(), Metrics(0.7, 0, True))
        self.assertEqual(len(calls), 3)
        self.assertTrue(b.observations[0]['stable'])

    def test_unstable_score_fails_closed(self):
        seq = iter([Metrics(0.6, 0, True), Metrics(0.7, 0, True)])
        with self.assertRaisesRegex(ValueError, 'unstable'):
            rv.VerifiedBenchmark(lambda: next(seq), repeats=2)()

    def test_worst_case_failure_not_averaged(self):
        seq = iter([Metrics(0.9, 0, True), Metrics(0.89, 2, False)])
        b = rv.VerifiedBenchmark(lambda: next(seq), repeats=2, max_quality_spread=0.02)
        result = b()
        self.assertFalse(result.security_ok)
        self.assertEqual(result.regressions, 2)
        self.assertEqual(result.quality, 0.89)

    def test_repeat_limits(self):
        for num in [0, 1, 8, True]:
            with self.subTest(num=num), self.assertRaises(ValueError):
                rv.validate_repeats(num, 0)
        for spread in [-0.1, 0.1, float('nan'), True]:
            with self.subTest(spread=spread), self.assertRaises(ValueError):
                rv.validate_repeats(3, spread)

    def test_model_endpoint_is_local_only(self):
        self.assertEqual(rv.require_local_model_url('http://127.0.0.1:11434'),
                         'http://127.0.0.1:11434')
        for url in ['https://example.org', 'http://192.168.1.2:11434',
                    'http://u:p@localhost:11434', 'http://localhost:8080',
                    'http://localhost:11434/other']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                rv.require_local_model_url(url)

    def test_audit_chain_and_change_detection(self):
        report = {'cycles': [{'generation': 1, 'decision': 'PASS'},
                             {'generation': 2, 'decision': 'REJECT'}]}
        audit = rv.audit_chain(report)
        self.assertEqual(len(audit['events']), 2)
        self.assertEqual(audit['events'][0]['event_sha256'],
                         audit['events'][1]['previous_sha256'])
        report['cycles'][0]['decision'] = 'FAIL'
        self.assertNotEqual(rv.audit_chain(report)['head_sha256'], audit['head_sha256'])

    def test_report_location_and_private_permissions(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / 'repo'
            repo.mkdir()
            with self.assertRaisesRegex(ValueError, 'outside'):
                rv.save_report(repo / 'evidence.json', repo, {})
            out = rv.save_report(Path(td) / 'secure' / 'evidence.json', repo, {'status': 'REVIEW_REQUIRED'})
            self.assertEqual(json.loads(out.read_text())['status'], 'REVIEW_REQUIRED')
            self.assertEqual(out.stat().st_mode & 0o777, 0o600)

    def test_reference_quality_score(self):
        benchmark = ROOT / 'benchmarks' / 'zyra_action_quality.py'
        spec = importlib.util.spec_from_file_location('reference_quality', benchmark)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        def baseline(raw):
            raw = raw.strip()
            candidates = [raw]
            if '{' in raw and '}' in raw:
                candidates.append(raw[raw.find('{'):raw.rfind('}') + 1])
            for item in candidates:
                try:
                    value = json.loads(item)
                    if isinstance(value, dict):
                        return value
                except json.JSONDecodeError:
                    continue
            raise ValueError('no JSON action')
        result = module.score(baseline, ValueError)
        self.assertGreater(result['quality'], 0)
        self.assertLess(result['quality'], 1)
        self.assertEqual(result['regressions'], 1)  # Current parser accepts JSON array wrappers.
        self.assertFalse(result['security_ok'])

    def test_evaluator_installer_keeps_source_outside_repo(self):
        spec = importlib.util.spec_from_file_location('install_rsi_evaluator',
                                                       ROOT / 'scripts' / 'install_rsi_evaluator.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / 'source'
            (repo / 'benchmarks').mkdir(parents=True)
            source = repo / 'benchmarks' / 'zyra_action_quality.py'
            source.write_text('print(1)\n')
            destination = Path(td) / 'private' / 'evaluator.py'
            module.install(source, destination, repo)
            self.assertEqual(destination.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(ValueError):
                module.install(source, destination, repo)
            with self.assertRaises(ValueError):
                module.install(source, repo / 'other.py', repo)

    def test_invalid_initial_benchmark_prevents_agent_creation(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / 'repo'
            repo.mkdir()
            script = Path(td) / 'evaluator.py'
            script.write_text('print("{}")\n')
            with patch.object(rv, 'require_clean_git_repo', return_value=repo):
                # A failed/invalid benchmark must block before invoking the LLM.
                with self.assertRaises(ValueError):
                    rv.run_verified(repo=repo, benchmark_path=script, probe_only=True, repeats=2)


if __name__ == '__main__':
    unittest.main()
