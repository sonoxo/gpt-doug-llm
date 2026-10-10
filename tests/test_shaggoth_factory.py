"""Integration checks for the bounded local GPT-Doug-Shaggoth factory."""
from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / 'gpt_zyra_shaggoth' / 'factory.py'
spec = importlib.util.spec_from_file_location('shaggoth_factory_under_test', FILE)
assert spec and spec.loader
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


class FactoryFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'project'
        self.root.mkdir()
        self.state = Path(self.tmp.name) / 'private-state'
        self.policy_path = self.root / f.POLICY_REL
        self.policy_path.parent.mkdir(parents=True)
        self.authorized_policy()
        self.factory = f.Factory(self.root, self.state)

    def authorized_policy(self):
        self.policy_path.write_text(json.dumps({
            'mode': 'DEFENSIVE_AUTHORIZED_ENVIRONMENTS_ONLY', 'status': 'ACTIVE',
            'truth_boundary': {'external_legal_status': 'NOT_PROMOTED_TO_STATUTE_OR_REGULATION'},
            'guardrails': f.EXPECTED_RULES.copy(),
        }), encoding='utf-8')

    def enqueue(self, kind='python-scaffold', goal='Create a normalized CSV data helper', **kwargs):
        return self.factory.submit(kind, goal, **kwargs)


class PolicyAndIntakeTests(FactoryFixture):
    def test_canonical_rules_all_checked(self):
        report = self.factory.policy()
        self.assertEqual(report['state'], 'VERIFIED')
        self.assertEqual(report['rules_total'], len(f.EXPECTED_RULES))
        self.assertEqual(report['rules_matching'], len(f.EXPECTED_RULES))

    def test_rule_drift_blocks_intake(self):
        p = json.loads(self.policy_path.read_text())
        p['guardrails']['credentialAcquisition'] = True
        self.policy_path.write_text(json.dumps(p))
        self.assertEqual(self.factory.policy()['state'], 'REVIEW_REQUIRED')
        with self.assertRaises(PermissionError):
            self.enqueue()

    def test_policy_legal_boundary_blocks(self):
        p = json.loads(self.policy_path.read_text())
        p['truth_boundary']['external_legal_status'] = 'LAW'
        self.policy_path.write_text(json.dumps(p))
        self.assertFalse(self.factory.policy()['local_drafts_allowed'])

    def test_symlink_denied(self):
        self.policy_path.unlink()
        out = Path(self.tmp.name) / 'fake-policy'
        out.write_text('{}')
        self.policy_path.symlink_to(out)
        self.assertEqual(self.factory.policy()['state'], 'UNVERIFIED')

    def test_bogus_policy_types_fail_closed(self):
        self.policy_path.write_text(json.dumps({'mode': 'X', 'guardrails': []}))
        self.assertEqual(self.factory.policy()['state'], 'UNVERIFIED')

    def test_no_policy_demo_only(self):
        self.policy_path.unlink()
        self.assertEqual(self.factory.policy()['state'], 'UNVERIFIED')
        sandbox = f.Factory(self.root, self.state / 'standalone', demo_policy=True)
        self.assertEqual(sandbox.policy()['state'], 'DEMO_ONLY')
        self.assertFalse(sandbox.policy()['ollama_allowed'])
        self.assertEqual(sandbox.submit('test-plan', 'Test a data processing task')['stage'], 'QUEUED')

    def test_private_disk_permissions(self):
        if os.name == 'posix':
            self.assertEqual(self.state.stat().st_mode & 0o777, 0o700)
            self.assertEqual(self.factory.db.stat().st_mode & 0o777, 0o600)

    def test_no_credentials_in_goal(self):
        for goal in ('Scan all files and brute force API keys',
                     'Harvest service credentials from other machines',
                     'Store -----BEGIN PRIVATE KEY----- data in project',
                     'My password=foo must appear here'):
            with self.subTest(goal=goal), self.assertRaises(ValueError):
                self.enqueue(goal=goal)
        self.assertEqual(self.factory.status()['jobs_total'], 0)

    def test_invalid_goal_and_kind(self):
        for goal in ('x', 'z'*481, 'hello\x00world'):
            with self.subTest(goal=goal[:10]), self.assertRaises(ValueError):
                self.enqueue(goal=goal)
        with self.assertRaises(ValueError):
            self.enqueue(kind='shell-execution')

    def test_ollama_requires_explicit_optin(self):
        with self.assertRaises(PermissionError):
            self.enqueue(backend='ollama')

    def test_idempotency_replay_and_conflict(self):
        a = self.enqueue(idempotency='request-1')
        b = self.enqueue(idempotency='request-1')
        self.assertEqual(a['id'], b['id'])
        self.assertEqual(self.factory.status()['jobs_total'], 1)
        with self.assertRaises(ValueError):
            self.enqueue(goal='A different research question', idempotency='request-1')

    def test_unsupported_id_and_traversal(self):
        with self.assertRaises(ValueError):
            self.factory.job('../etc/passwd')
        with self.assertRaises(KeyError):
            self.factory.job('0'*32)

    def test_worker_cannot_cross_policy_revocation(self):
        job = self.enqueue()
        p = json.loads(self.policy_path.read_text())
        p['guardrails']['uncontrolledAgentReplication'] = True
        self.policy_path.write_text(json.dumps(p))
        result = self.factory.process_one()
        self.assertEqual(result['stage'], 'BLOCKED')
        self.assertFalse((self.state / 'artifacts' / job['id']).exists())

    def test_ollama_stays_disabled_in_demo_even_when_flagged(self):
        self.policy_path.unlink()
        sandbox = f.Factory(self.root, self.state / 'demo2', demo_policy=True, allow_ollama=True)
        with self.assertRaises(PermissionError):
            sandbox.submit('python-scaffold', 'Create a simple offline helper', 'ollama')


class ProductionTests(FactoryFixture):
    def test_scaffold_build_has_manifest_and_no_execution(self):
        submitted = self.enqueue()
        result = self.factory.process_one()
        self.assertEqual(submitted['id'], result['id'])
        self.assertEqual(result['stage'], 'AWAITING_REVIEW')
        self.assertEqual(result['progress'], 100)
        with zipfile.ZipFile(io.BytesIO(self.factory.archive(submitted['id']))) as z:
            names = set(z.namelist())
            self.assertTrue({'component.py', 'test_example.py', 'manifest.json', 'review.json', 'verification.json'}.issubset(names))
            verified = json.loads(z.read('verification.json'))
            self.assertEqual(verified['actual_tests_executed'], 0)
            self.assertFalse(verified['safe_to_execute'])
            self.assertIn('from component import describe', z.read('test_example.py').decode())

    def test_research_and_test_plan_files(self):
        a = self.enqueue('research-brief', 'Map an evidence based AI workflow')
        b = self.enqueue('test-plan', 'Check the approval workflow')
        self.assertEqual(self.factory.process_one()['stage'], 'AWAITING_REVIEW')
        self.assertEqual(self.factory.process_one()['stage'], 'AWAITING_REVIEW')
        with zipfile.ZipFile(io.BytesIO(self.factory.archive(a['id']))) as z:
            self.assertIn('RESEARCH.md', z.namelist())
            self.assertIn('No research was retrieved', z.read('RESEARCH.md').decode())
        with zipfile.ZipFile(io.BytesIO(self.factory.archive(b['id']))) as z:
            self.assertEqual(json.loads(z.read('test_matrix.json'))['status'], 'UNEXECUTED_TEMPLATE')

    def test_review_does_not_deploy(self):
        j = self.enqueue()
        self.factory.process_one()
        result = self.factory.approve(j['id'], 'approve')
        self.assertEqual(result['stage'], 'APPROVED_LOCAL')
        self.assertIn('no deployment authorized', result['review_note'])
        with self.assertRaises(ValueError):
            self.factory.approve(j['id'], 'approve')
        self.assertEqual(self.factory.status()['counts']['APPROVED_LOCAL'], 1)

    def test_reject_is_explicit(self):
        j = self.enqueue()
        self.factory.process_one()
        self.assertEqual(self.factory.approve(j['id'], 'reject')['stage'], 'REJECTED')

    def test_pause_blocks_worker_until_resume(self):
        job = self.enqueue()
        self.factory.pause(True)
        self.assertIsNone(self.factory.process_one())
        self.assertEqual(self.factory.job(job['id'])['stage'], 'QUEUED')
        self.factory.pause(False)
        self.assertEqual(self.factory.process_one()['stage'], 'AWAITING_REVIEW')

    def test_bundle_checksum_tamper_rejected(self):
        job = self.enqueue()
        self.factory.process_one()
        path = self.state / 'artifacts' / job['id'] / 'component.py'
        path.write_text('tampered!', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.factory.archive(job['id'])

    def test_manifests_are_all_exact(self):
        job = self.enqueue()
        self.factory.process_one()
        with zipfile.ZipFile(io.BytesIO(self.factory.archive(job['id']))) as z:
            manifest = json.loads(z.read('manifest.json'))
            self.assertEqual(job['id'], manifest['job_id'])
            for name, digest in manifest['files'].items():
                self.assertEqual(f.sha256(z.read(name)), digest)

    def test_python_static_verifier_rejects_unsafe_functions(self):
        cases = ('import subprocess\nsubprocess.run(["ls"])',
                 'eval("2+2")',
                 'def broken(: pass')
        for code in cases:
            with self.subTest(code=code[:15]), self.assertRaises((ValueError, SyntaxError)):
                f.verify_files({'component.py': code, 'test_example.py': 'def test_a(): pass'}, 'python-scaffold')

    def test_no_model_call_in_offline_factory(self):
        job = self.enqueue()
        with patch.object(f.urllib.request, 'build_opener', side_effect=AssertionError('network used')):
            self.factory.process_one()
        self.assertEqual(self.factory.job(job['id'])['stage'], 'AWAITING_REVIEW')

    def test_policy_drift_prevents_human_approval(self):
        job = self.enqueue()
        self.factory.process_one()
        policy = json.loads(self.policy_path.read_text())
        policy['guardrails']['uncontrolledAgentReplication'] = True
        self.policy_path.write_text(json.dumps(policy))
        with self.assertRaises(PermissionError):
            self.factory.approve(job['id'], 'approve')
        self.assertEqual(self.factory.job(job['id'])['stage'], 'AWAITING_REVIEW')

    def test_opt_in_ollama_draft_enters_review_without_executing(self):
        factory = f.Factory(self.root, self.state / 'ollama-enabled', allow_ollama=True)
        job = factory.submit('python-scaffold', 'Write an offline object parser', 'ollama')
        with patch.object(f, 'ollama_draft', return_value={
            'component.py': 'def parse(value):\n    return str(value)\n',
            'test_example.py': 'def test_parse():\n    assert True\n',
            'README.md': 'Local model proposal; no tests executed.\n',
        }) as model:
            output = factory.process_one()
        self.assertEqual(output['stage'], 'AWAITING_REVIEW')
        model.assert_called_once()
        with zipfile.ZipFile(io.BytesIO(factory.archive(job['id']))) as z:
            checks = json.loads(z.read('verification.json'))
            self.assertEqual(checks['actual_tests_executed'], 0)

    def test_model_generated_unsafe_draft_is_blocked(self):
        factory = f.Factory(self.root, self.state / 'ollama-unsafe', allow_ollama=True)
        job = factory.submit('python-scaffold', 'Generate a local test helper', 'ollama')
        with patch.object(f, 'ollama_draft', return_value={
            'component.py': 'import subprocess\nsubprocess.run(["ls"])\n',
            'test_example.py': 'def test_a(): assert True\n',
            'README.md': 'Untrusted output\n',
        }):
            self.assertEqual(factory.process_one()['stage'], 'BLOCKED')
        self.assertFalse((factory.state / 'artifacts' / job['id']).exists())

    def test_explicit_demo_request_creates_new_bounded_batch(self):
        first = self.factory.seed_demo()
        second = self.factory.seed_demo(repeat=True)
        self.assertEqual(len(second), 3)
        self.assertFalse(set(x['id'] for x in first) & set(x['id'] for x in second))
        self.assertEqual(self.factory.status()['jobs_total'], 6)

    def test_sqlite_persists_after_restart(self):
        job = self.enqueue('test-plan', 'Verify offline production status')
        self.factory.process_one()
        restarted = f.Factory(self.root, self.state)
        self.assertEqual(restarted.job(job['id'])['stage'], 'AWAITING_REVIEW')
        self.assertGreater(len(restarted.events()), 4)

    def test_seed_demo_idempotent(self):
        a = self.factory.seed_demo()
        b = self.factory.seed_demo()
        self.assertEqual([x['id'] for x in a], [x['id'] for x in b])
        self.assertEqual(self.factory.status()['jobs_total'], 3)

    def test_no_empty_claim_of_ai_generation(self):
        job = self.enqueue()
        self.factory.process_one()
        self.assertEqual(self.factory.status()['backend'], 'offline')
        self.assertNotIn('autonomous self-improvement', self.factory.archive(job['id']).decode('latin1'))


class HTTPTests(FactoryFixture):
    def setUp(self):
        super().setUp()
        self.server = f.FactoryServer(self.factory, 0, workers=False)
        self.serverthread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.serverthread.start()
        self.addCleanup(self.stop_server)
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.serverthread.join(timeout=2)

    def fetch(self, path, method='GET', payload=None, headers=None):
        data = f.canonical(payload) if payload is not None else None
        request = urllib.request.Request(self.url+path, data=data, method=method,
              headers=headers or {})
        return urllib.request.urlopen(request, timeout=3)

    def test_root_dashboard_real_html_and_status(self):
        with self.fetch('/') as response:
            html=response.read().decode()
            self.assertIn('SHAGGOTH', html)
            self.assertIn('factory-csrf', html)
            self.assertNotIn('@@CSRF_TOKEN@@', html)
        with self.fetch('/api/status') as response:
            snap=json.load(response)
            self.assertEqual(snap['policy']['state'], 'VERIFIED')
            self.assertFalse(snap['limits']['exec_generated_code'])
        with self.fetch('/factory.js') as response:
            self.assertIn('EventSource', response.read().decode())

    def test_unauthorized_submission_denied(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.fetch('/api/jobs', method='POST', payload={'kind':'test-plan','goal':'A valid safe task'},
                       headers={'Content-Type':'application/json'})
        self.assertEqual(ctx.exception.code, 403)

    def test_authorized_enqueue_and_download(self):
        with self.fetch('/api/jobs', method='POST', payload={'kind':'python-scaffold','goal':'Create local helper'},
                        headers={'X-Factory-CSRF':self.server.token,'Content-Type':'application/json'}) as response:
            job=json.load(response)['job']
        self.factory.process_one()
        with self.fetch(f'/api/jobs/{job["id"]}/download') as response:
            self.assertEqual(response.status, 200)
            z=zipfile.ZipFile(io.BytesIO(response.read()))
            self.assertIn('manifest.json', z.namelist())

    def test_mutation_rejects_cross_origin(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.fetch('/api/demo', method='POST', payload={},headers={
                'Content-Type':'application/json', 'X-Factory-CSRF':self.server.token,
                'Origin':'https://attacker.example'})
        self.assertEqual(ctx.exception.code,403)

    def test_delete_and_put_denied(self):
        for method in ('DELETE','PUT','PATCH'):
            with self.subTest(method=method), self.assertRaises(urllib.error.HTTPError) as ctx:
                self.fetch('/api/jobs', method=method)
            self.assertEqual(ctx.exception.code, 405)

    def test_sse_has_real_policy_and_jobs(self):
        with self.fetch('/events') as response:
            first = response.readline().decode('utf-8')
            self.assertTrue(first.startswith('data: '))
            obj=json.loads(first[6:])
            self.assertEqual(obj['policy']['state'], 'VERIFIED')
            response.close()

    def test_excess_stream_clients_rejected(self):
        handles=[]
        try:
            for _ in range(f.MAX_SSE_CLIENTS):
                handles.append(self.fetch('/events'))
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                self.fetch('/events')
            self.assertEqual(ctx.exception.code,429)
        finally:
            for handle in handles:
                handle.close()


class LauncherTests(unittest.TestCase):
    def test_start_from_unrelated_directory_with_demo(self):
        with tempfile.TemporaryDirectory() as state, tempfile.TemporaryDirectory() as cwd:
            # Startup must show an actual local URL and have a live HTTP server.
            process = subprocess.Popen(['bash', str(ROOT/'run-GPT-Doug-Shaggoth-Factory.command'),
                 '--port','0','--no-browser'], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                 text=True, env={**os.environ,'HOME':state})
            try:
                import select
                ready, _, _ = select.select([process.stdout], [], [], 8)
                self.assertTrue(ready, 'launcher did not start')
                first=process.stdout.readline()
                self.assertIn('FACTORY', first)
                second=process.stdout.readline().strip()
                self.assertRegex(second, r'^http://127\.0\.0\.1:\d+/$')
                with urllib.request.urlopen(second+'api/health',timeout=2) as response:
                    self.assertEqual(json.load(response)['status'], 'UP')
            finally:
                process.terminate()
                process.wait(timeout=5)

    def test_cli_demo_and_offline_results(self):
        with tempfile.TemporaryDirectory() as state:
            out = subprocess.run([sys.executable,str(FILE),'--state-dir',state,'--demo-policy','demo'],
                                 cwd='/',capture_output=True,text=True,timeout=20)
            self.assertEqual(out.returncode,0,out.stderr)
            data=json.loads(out.stdout)
            self.assertEqual(data['processed'],3)
            self.assertTrue(all(j['stage']=='AWAITING_REVIEW' for j in data['jobs']))


if __name__ == '__main__':
    unittest.main()
