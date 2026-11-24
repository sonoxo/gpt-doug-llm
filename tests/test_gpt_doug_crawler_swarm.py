"""Offline authorization, parallelism, provenance and error isolation tests."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import gpt_doug_crawler_swarm as swarm  # noqa: E402


def target(i='site', host='example.org'):
    return {'id': i, 'base_url': f'https://{host}/', 'allow_host': host,
            'authorized': True, 'max_pages': 2, 'max_depth': 1}


class SwarmTests(unittest.TestCase):
    def test_single_exact_authorized_target(self):
        result = swarm.validate_manifest({'schema': swarm.SCHEMA, 'targets': [target()]})
        self.assertEqual(result[0]['allow_host'], 'example.org')
        self.assertNotIn('authorized', result[0])

    def test_reject_missing_authorization(self):
        t = target()
        del t['authorized']
        with self.assertRaisesRegex(ValueError, 'authorized'):
            swarm.validate_manifest({'schema': swarm.SCHEMA, 'targets': [t]})

    def test_private_and_credentials_blocked(self):
        for bad in ['https://localhost/', 'http://example.org/',
                    'https://u:pass@example.org/', 'https://example.org/admin',
                    'https://example.org/?token=secret', 'https://example.org/a#ref',
                    'https://example.org:8443/']:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                swarm.validate_manifest({'schema': swarm.SCHEMA,
                                         'targets': [{**target(), 'base_url': bad}]})

    def test_duplicate_hosts_blocked(self):
        with self.assertRaisesRegex(ValueError, 'unique'):
            swarm.validate_manifest({'schema': swarm.SCHEMA,
                                     'targets': [target(), target('again')]})

    def test_page_budget_and_workers(self):
        rows = [target(f'site{i}', f'site{i}.example.org') for i in range(9)]
        for row in rows:
            row['max_pages'] = 12
        with self.assertRaisesRegex(ValueError, 'budget'):
            swarm.validate_manifest({'schema': swarm.SCHEMA, 'targets': rows})
        with self.assertRaisesRegex(ValueError, 'workers'):
            swarm.run_swarm([target()], 30)

    def test_parallel_result_order_and_failure_isolation(self):
        items = swarm.validate_manifest({'schema': swarm.SCHEMA, 'targets': [
            target('a', 'a.example.org'), target('b', 'b.example.org')]})
        def fake(t):
            if t['id'] == 'a':
                return {'id': 'a', 'status': 'completed', 'evidence': [{'id': 'x'}]}
            raise RuntimeError('test failure')
        report = swarm.run_swarm(items, 2, crawl_fn=fake)
        self.assertEqual([r['id'] for r in report['targets']], ['a', 'b'])
        self.assertEqual(report['summary'], {'targets': 2, 'completed': 1,
                                             'failed': 1, 'evidence_records': 1})
        self.assertEqual(report['targets'][1]['error_type'], 'RuntimeError')

    def test_crawl_metadata_never_exports_body(self):
        t = swarm.validate_manifest({'schema': swarm.SCHEMA, 'targets': [target()]})[0]
        fake_snapshot = {'coverage': {'pagesStored': 1}, 'edges': [], 'outboundDomains': [],
                         'pages': [{'url': 'https://example.org/', 'title': 'Public page',
                                    'sha256': 'a' * 64, 'bytes': 42, 'depth': 0,
                                    'observedAt': '2026-11-04T00:00:00Z',
                                    'text': 'SECRET SHOULD NOT LEAVE MIRROR'}]}
        result = swarm.crawl_target(t, mirror_fn=lambda *args: fake_snapshot)
        serialized = json.dumps(result)
        self.assertNotIn('SECRET', serialized)
        self.assertIn('neural_features', serialized)
        self.assertEqual(result['evidence'][0]['classification'], 'public_unverified')

    def test_demo_and_atomic_output(self):
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder) / 'out.json'
            rc = swarm.main(['--demo', '--out', str(dest)])
            self.assertEqual(rc, 0)
            self.assertTrue(json.loads(dest.read_text())['synthetic'])

    def test_cli_rejects_unapproved_live_crawl(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'manifest.json'
            path.write_text(json.dumps({'schema': swarm.SCHEMA, 'targets': [target()]}))
            with self.assertRaises(SystemExit) as ctx:
                swarm.main(['--manifest', str(path)])
            self.assertEqual(ctx.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
