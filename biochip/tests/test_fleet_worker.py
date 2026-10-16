"""Real subprocess and local HTTP worker tests; no model account required."""
from dataclasses import replace
import json
import os
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from ai_killswitch import AIKillSwitchEngaged
from biochip.fleet.config import FleetLimits
from biochip.fleet.supervisor import run_inference, _exchange, _decode_result, _child_environment
from biochip.models import ProviderProtocolError
from biochip.tests.helpers import HTTPFixture, stop_environment
from biochip.tests.test_fleet_config import approval


class FleetWorkerTests(unittest.TestCase):
    def setUp(self):
        self.context = stop_environment(); self.stop_dir = self.context.__enter__()
        self.addCleanup(self.context.__exit__, None, None, None)

    def child(self, code):
        proc = subprocess.Popen([sys.executable, '-I', '-c', code], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        def cleanup():
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=3)
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                stream.close()
        self.addCleanup(cleanup)
        return proc

    def test_valid_worker_response(self):
        def respond(h, body):
            value = {'models': [{'name': 'fixture-model'}]} if body is None else {'message': {'content': 'proposal'}, 'eval_count': 2}
            HTTPFixture.reply(h, value)
        with HTTPFixture(respond) as server:
            result = run_inference(approval(endpoint=server.url), 'nonsensitive fixture',
                                   system='planner', limits=FleetLimits(), deadline=time.monotonic()+5)
        self.assertEqual((result.text, result.reported_output_tokens), ('proposal', 2))
        self.assertEqual([r[0] for r in server.requests], ['GET', 'POST'])

    def test_malformed_worker_output(self):
        for raw in (b'not-json', b'{}', b'{"text":null}'):
            with self.assertRaises(ProviderProtocolError):
                _decode_result(raw, 0, approval(), FleetLimits())

    def test_child_byte_limit(self):
        proc = self.child('import sys; sys.stdout.buffer.write(b"x" * 100000); sys.stdout.flush()')
        with self.assertRaises(ValueError):
            _exchange(proc, b'{}', deadline=time.monotonic()+3, max_bytes=4096)
        self.assertIsNotNone(proc.poll())

    def test_stalled_stdin_deadline(self):
        proc = self.child('import time; time.sleep(60)')
        before = time.monotonic()
        with self.assertRaises(TimeoutError):
            _exchange(proc, b'x' * 1048576, deadline=before+0.3, max_bytes=1048576)
        self.assertLess(time.monotonic()-before, 3)
        self.assertIsNotNone(proc.poll())

    def test_stderr_flood_deadline(self):
        proc = self.child('import sys; sys.stderr.buffer.write(b"x" * 2000000); sys.stderr.flush()')
        before = time.monotonic()
        with self.assertRaises(ValueError):
            _exchange(proc, b'{}', deadline=before+3, max_bytes=8192)
        self.assertLess(time.monotonic()-before, 3)
        self.assertIsNotNone(proc.poll())

    def test_stop_only_terminates_owned_child(self):
        sentinel = self.child('import time; time.sleep(60)')
        entered, release = Event(), Event()
        def respond(h, body):
            if body is None:
                HTTPFixture.reply(h, {'models': [{'name': 'fixture-model'}]})
            else:
                entered.set(); release.wait(5)
                HTTPFixture.reply(h, {'message': {'content': 'late'}})
        with HTTPFixture(respond) as server, ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(run_inference, approval(endpoint=server.url), 'fixture',
                                 system='', limits=FleetLimits(), deadline=time.monotonic()+8)
            try:
                self.assertTrue(entered.wait(4))
                (self.stop_dir / 'STOP').write_text('stop')
                with self.assertRaises(AIKillSwitchEngaged):
                    future.result(timeout=3)
                self.assertIsNone(sentinel.poll())
            finally:
                release.set()

    def test_stop_environment_preserved(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'not-for-child', 'HEYPCB_API_KEY': 'not-for-child',
                                     'PYTHONPATH': '/untrusted', 'GPT_DOUG_AI_BLOCK_ALL': 'invalid'}):
            env = _child_environment()
        self.assertEqual(env['GPT_DOUG_AI_BLOCK_ALL'], 'invalid')
        self.assertEqual(env['GPT_DOUG_AI_STOP_DIR'], str(self.stop_dir))
        self.assertEqual(env['GPT_DOUG_AI_REQUIRE_STOP_DIRECTORY'], '1')
        self.assertEqual(env['HOME'], os.environ['HOME'])
        self.assertFalse({'OPENAI_API_KEY', 'HEYPCB_API_KEY', 'PYTHONPATH'} & env.keys())

    def test_worker_requires_current_model_discovery(self):
        with HTTPFixture() as server:
            with self.assertRaises(RuntimeError):
                run_inference(approval(endpoint=server.url), 'fixture', system='',
                              limits=FleetLimits(), deadline=time.monotonic()+5)
            self.assertEqual([r[0] for r in server.requests], ['GET'])
