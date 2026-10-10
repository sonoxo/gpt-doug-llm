"""Integration tests for the local-only live Chaos access cube."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODFILE = ROOT / 'gpt_chaos' / 'live_cube.py'
spec = importlib.util.spec_from_file_location('testable_live_cube', MODFILE)
assert spec is not None and spec.loader is not None
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class SourceFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / m.POLICY_REL
        self.path.parent.mkdir(parents=True)
        self.policy = {
            'mode': 'DEFENSIVE_AUTHORIZED_ENVIRONMENTS_ONLY',
            'status': 'ACTIVE',
            'truth_boundary': {'external_legal_status': 'NOT_PROMOTED_TO_STATUTE_OR_REGULATION'},
            'guardrails': m.GUARDRAIL_EXPECTED.copy(),
        }
        self.persist()
        for _, _, relative in m.MODULES:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('# harmless source stub\n', encoding='utf8')

    def persist(self):
        self.path.write_text(json.dumps(self.policy), encoding='utf8')


class MonitorTests(SourceFixture):
    def test_policy_valid_and_fingerprint(self):
        p = m.read_policy(self.root)
        self.assertEqual(p['state'], 'MATCHED')
        self.assertEqual(p['controls_checked'], p['controls_total'])
        self.assertEqual(len(p['fingerprint']), 12)

    def test_policy_drift_fails_closed(self):
        self.policy['guardrails']['credentialAcquisition'] = True
        self.persist()
        self.assertEqual(m.read_policy(self.root)['state'], 'REVIEW_REQUIRED')
        self.assertLess(m.read_policy(self.root)['controls_checked'], len(m.GUARDRAIL_EXPECTED))

    def test_legal_truth_boundary_cannot_be_promoted(self):
        self.policy['truth_boundary']['external_legal_status'] = 'CLAIMED_AS_UNIVERSAL_LAW'
        self.persist()
        self.assertEqual(m.read_policy(self.root)['state'], 'REVIEW_REQUIRED')

    def test_policy_missing_or_symlink_unverified(self):
        self.path.unlink()
        self.assertEqual(m.read_policy(self.root)['state'], 'UNVERIFIED')
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside) / 'policy.json'
            external.write_text(json.dumps(self.policy), encoding='utf8')
            self.path.symlink_to(external)
            self.assertEqual(m.read_policy(self.root)['state'], 'UNVERIFIED')

    def test_policy_oversize_and_invalid_json(self):
        self.path.write_text(' ' * (m.MAX_POLICY_BYTES + 1))
        self.assertEqual(m.read_policy(self.root)['state'], 'UNVERIFIED')
        self.path.write_text('{bad json')
        self.assertEqual(m.read_policy(self.root)['state'], 'UNVERIFIED')

    def test_all_source_checks_distinguish_presence_from_running(self):
        monitor = m.LiveMonitor(self.root)
        a = monitor.snapshot()
        self.assertEqual(a['counts']['source_present'], 7)
        self.assertEqual(a['counts']['running_agents_verified'], 0)
        self.assertTrue(all(s['runtime_state'] == 'NOT_VERIFIED' for s in a['modules']))
        self.assertEqual(a['policy']['state'], 'MATCHED')
        self.assertEqual(a['counts']['rules_enforced'], 3)
        self.assertFalse(a['security_boundary']['authorization_by_cube_rotation'])

    def test_missing_one_source_does_not_claim_active(self):
        path = self.root / m.MODULES[0][2]
        path.unlink()
        a = m.LiveMonitor(self.root).snapshot()
        self.assertEqual(a['counts']['source_present'], 6)
        self.assertEqual(a['modules'][0]['source_state'], 'NOT_FOUND')
        self.assertEqual(a['counts']['running_agents_verified'], 0)

    def test_symlinked_module_not_accepted(self):
        path = self.root / m.MODULES[0][2]
        path.unlink()
        with tempfile.TemporaryDirectory() as other:
            out = Path(other) / 'fake.py'
            out.write_text('hello')
            path.symlink_to(out)
            self.assertEqual(m.LiveMonitor(self.root).snapshot()['modules'][0]['source_state'], 'NOT_FOUND')

    def test_snapshot_sequence_updates(self):
        monitor = m.LiveMonitor(self.root)
        a, b = monitor.snapshot(), monitor.snapshot()
        self.assertEqual(b['sequence'], a['sequence'] + 1)
        self.assertEqual(b['http_requests'], 0)
        monitor.request()
        self.assertEqual(monitor.snapshot()['http_requests'], 1)

    def test_concurrent_clients_bounded(self):
        monitor = m.LiveMonitor(self.root)
        for _ in range(m.MAX_SSE_CLIENTS):
            self.assertTrue(monitor.admit_client())
        self.assertFalse(monitor.admit_client())
        self.assertEqual(monitor.snapshot()['connected_viewers'], m.MAX_SSE_CLIENTS)
        for _ in range(m.MAX_SSE_CLIENTS):
            monitor.leave_client()
        self.assertEqual(monitor.snapshot()['connected_viewers'], 0)


class HTTPTests(SourceFixture):
    def setUp(self):
        super().setUp()
        self.monitor = m.LiveMonitor(self.root)
        self.server = m.LoopbackServer(0, self.monitor)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        self.addCleanup(self.stop_server)
        self.origin = f'http://127.0.0.1:{self.server.server_port}'

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=2)

    def get(self, path, **headers):
        req = urllib.request.Request(self.origin + path, headers=headers)
        return urllib.request.urlopen(req, timeout=3)

    def test_api_status_actual_local_measurements(self):
        with self.get('/api/status') as r:
            self.assertEqual(r.status, 200)
            self.assertNotIn('Access-Control-Allow-Origin', r.headers)
            payload = json.load(r)
        self.assertEqual(payload['mode'], 'LIVE_LOCAL_READ_ONLY')
        self.assertEqual(payload['policy']['state'], 'MATCHED')
        self.assertEqual(payload['counts']['source_present'], 7)
        self.assertGreaterEqual(payload['http_requests'], 1)
        self.assertFalse(payload['security_boundary']['credential_access'])

    def test_real_html_css_js_and_health(self):
        with self.get('/') as r:
            body = r.read().decode()
            self.assertIn('Access <span>Rubik Cube</span>', body)
            self.assertIn('Content-Security-Policy', r.headers)
        with self.get('/app.js') as r:
            self.assertIn(b'EventSource', r.read())
        with self.get('/styles.css') as r:
            self.assertIn(b'transform-style:preserve-3d', r.read())
        with self.get('/api/health') as r:
            self.assertEqual(json.load(r)['status'], 'LOCAL_SERVER_RUNNING')

    def test_reject_cross_origin(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.get('/api/status', Origin='https://attacker.example')
        self.assertEqual(caught.exception.code, 403)

    def test_reject_host_header(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.get('/api/status', Host='attacker.example')
        self.assertEqual(caught.exception.code, 403)

    def test_no_mutations(self):
        for method in ('POST', 'PUT', 'DELETE'):
            with self.subTest(method=method):
                req = urllib.request.Request(self.origin+'/api/status', data=b'',method=method)
                with self.assertRaises(urllib.error.HTTPError) as err:
                    urllib.request.urlopen(req, timeout=3)
                self.assertEqual(err.exception.code, 405)

    def test_unknown_paths_and_query_denied(self):
        for path in ('/garbage', '/../../etc/passwd', '/api/status?token=bad'):
            with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError) as err:
                self.get(path)
            self.assertEqual(err.exception.code, 404)

    def test_head_has_length_but_no_body(self):
        req = urllib.request.Request(self.origin+'/',method='HEAD')
        with urllib.request.urlopen(req,timeout=3) as r:
            self.assertEqual(r.status, 200)
            self.assertGreater(int(r.headers['Content-Length']),1000)
            self.assertEqual(r.read(),b'')

    def test_sse_pushes_actual_snapshot(self):
        with patch.object(m, 'SSE_MAX_SECONDS', 1.1), patch.object(m, 'SSE_INTERVAL_SECONDS', .05):
            with self.get('/events') as r:
                self.assertEqual(r.headers.get_content_type(), 'text/event-stream')
                self.assertEqual(r.readline(), b'event: snapshot\n')
                line = r.readline().decode()
                self.assertTrue(line.startswith('data: '))
                payload = json.loads(line[6:])
                self.assertEqual(payload['counts']['source_total'], 7)
                self.assertEqual(payload['connected_viewers'], 1)


class CLITests(SourceFixture):
    def test_snapshot_cli_is_offline(self):
        run = subprocess.run([sys.executable, str(MODFILE), 'snapshot'],
                             text=True,capture_output=True,timeout=8)
        self.assertEqual(run.returncode,0,run.stderr)
        state = json.loads(run.stdout)
        self.assertEqual(state['counts']['running_agents_verified'],0)

    def test_run_from_unrelated_cwd(self):
        script = ROOT/'run-GPT-Doug-Chaos.command'
        run = subprocess.run(['bash',str(script),'--no-browser','--port','-1'],
                             cwd=self.root,text=True,capture_output=True,timeout=8)
        self.assertEqual(run.returncode,2)
        self.assertIn('startup failed',run.stdout)

    def test_positive_launcher_from_another_directory(self):
        # Actually start and reach the UI; catches earlier launcher path bugs.
        with tempfile.TemporaryDirectory() as other:
            launch = ROOT / 'run-GPT-Doug-Chaos.command'
            proc = subprocess.Popen(['bash', str(launch), '--no-browser', '--port', '0'],
                                    cwd=other, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True)
            try:
                first = proc.stdout.readline().strip()
                second = proc.stdout.readline().strip()
                self.assertIn('GPT-DOUG-CHAOS', first)
                self.assertTrue(second.startswith('Dashboard: http://127.0.0.1:'), second)
                url = second.split('Dashboard: ', 1)[1]
                with urllib.request.urlopen(url + 'api/health', timeout=3) as res:
                    self.assertEqual(json.load(res)['status'], 'LOCAL_SERVER_RUNNING')
            finally:
                proc.terminate()
                proc.wait(timeout=4)
                proc.stdout.close()
                proc.stderr.close()

    def test_no_host_public_option(self):
        run = subprocess.run([sys.executable,str(MODFILE),'serve','--host','0.0.0.0'],
                             text=True,capture_output=True,timeout=8)
        self.assertNotEqual(run.returncode,0)
        self.assertIn('unrecognized arguments',run.stderr)


if __name__ == '__main__':
    unittest.main()
