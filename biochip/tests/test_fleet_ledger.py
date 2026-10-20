"""Real SQLite ledger tests; no prompts, replies or credentials in stored events."""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from biochip.fleet.ledger import MissionLedger
from biochip.tests.test_fleet_config import config


class FleetLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.config = config(self.temp.name)
        self.path = self.config.state_directory / 'missions.sqlite3'
        self.ledger = MissionLedger(self.path)
        self.mid = self.ledger.create(self.config, 'a' * 64)

    def test_state_directory_symlink_refused_before_creation(self):
        target = Path(self.temp.name) / 'target'
        target.mkdir(mode=0o700)
        link = Path(self.temp.name) / 'linked-state'
        link.symlink_to(target, target_is_directory=True)
        with self.assertRaises(PermissionError):
            MissionLedger(link / 'missions.sqlite3')
        self.assertFalse((target / 'missions.sqlite3').exists())

    def test_state_transitions(self):
        self.assertTrue(self.ledger.transition(self.mid, expected='queued', new='running', detail={}))
        self.assertFalse(self.ledger.transition(self.mid, expected='queued', new='running', detail={}))
        self.assertTrue(self.ledger.transition(self.mid, expected='running', new='completed', detail={'model_calls': 1}))
        self.assertFalse(self.ledger.transition(self.mid, expected='completed', new='running', detail={}))
        self.assertEqual(self.ledger.read(self.mid, operator='owner', project='p')['state'], 'completed')

    def test_cross_project_denial(self):
        for operator, project in (('other', 'p'), ('owner', 'other')):
            with self.assertRaises(PermissionError):
                self.ledger.read(self.mid, operator=operator, project=project)

    def test_reconcile_without_replay(self):
        self.ledger.transition(self.mid, expected='queued', new='running', detail={})
        self.assertEqual(self.ledger.reconcile_interrupted(), 1)
        self.assertEqual(self.ledger.reconcile_interrupted(), 0)
        self.assertEqual(self.ledger.read(self.mid, operator='owner', project='p')['state'], 'uncertain')

    def test_rejects_sensitive_event_fields(self):
        for event in ({'prompt': 'private'}, {'reply': 'private'}, {'api_key': 'secret'},
                      {'reason': 'secret arbitrary text'}, {'tool_calls': 1}, {'model_calls': True}):
            with self.assertRaises(ValueError):
                self.ledger.record(self.mid, event)
        stored = self.ledger.read(self.mid, operator='owner', project='p')
        self.assertIsNone(stored['metadata']['reported_output_tokens'])
        self.assertNotIn('private', json.dumps(stored))

    def test_disk_failure_blocks_dispatch(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TRIGGER reject_event BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT, 'fixture'); END")
        with self.assertRaises(sqlite3.Error):
            self.ledger.transition(self.mid, expected='queued', new='running', detail={})
        self.assertEqual(self.ledger.read(self.mid, operator='owner', project='p')['state'], 'queued')

    def test_private_and_persistent(self):
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o600)
        self.assertEqual(os.stat(self.path.parent).st_mode & 0o777, 0o700)
        other = MissionLedger(self.path)
        self.assertEqual(other.read(self.mid, operator='owner', project='p')['id'], self.mid)
        with self.assertRaises(AttributeError):
            self.ledger.database = Path('/tmp/unapproved')

    def test_readonly_never_creates_or_writes(self):
        before = self.path.read_bytes()
        readonly = MissionLedger(self.path, read_only=True)
        readonly.read(self.mid, operator='owner', project='p')
        with self.assertRaises(PermissionError):
            readonly.create(self.config, 'b' * 64)
        self.assertEqual(self.path.read_bytes(), before)
        missing = self.path.parent / 'missing.sqlite3'
        with self.assertRaises(FileNotFoundError):
            MissionLedger(missing, read_only=True)
        self.assertFalse(missing.exists())

    def test_future_schema_and_symlinks_refused(self):
        link = self.path.parent / 'alias.sqlite3'; link.symlink_to(self.path)
        with self.assertRaises(PermissionError):
            MissionLedger(link)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('PRAGMA user_version=99')
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            MissionLedger(self.path)
        self.assertEqual(self.path.read_bytes(), before)
