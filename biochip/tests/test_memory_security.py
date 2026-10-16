"""Regression tests for real memory boundaries; local disposable databases only."""
import json
from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from biochip import BioChip


class MemorySecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'memory.sqlite3'
        self.chip = BioChip(str(self.path))

    def remember(self, value=1, **kwargs):
        return self.chip.remember('x', value, actor='owner', provenance='test', **kwargs)

    def count(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            return db.execute('SELECT COUNT(*) FROM memories').fetchone()[0]

    def test_database_path_rejects_non_path_values(self):
        from biochip.storage import file_path
        for value in (None, True, 123, object()):
            with self.subTest(kind=type(value).__name__):
                with self.assertRaises(ValueError):
                    file_path(value)

    def test_rejects_nonfinite_ttl_and_expiry_overflow(self):
        for ttl in (float('nan'), float('inf'), -float('inf'), True, 0, -1, '5', 10**400):
            with self.subTest(ttl=repr(ttl)):
                with self.assertRaises(ValueError):
                    self.remember(ttl_seconds=ttl)
        with patch('biochip.core.time.time', return_value=1e308):
            with self.assertRaises(ValueError):
                self.remember(ttl_seconds=1e308)
        self.assertEqual(self.count(), 0)

    def test_rejects_bool_confidence_and_ttl(self):
        for value in (True, False, float('nan'), float('inf'), '1', None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.remember(confidence=value)
        self.assertEqual(self.count(), 0)

    def test_utf8_value_byte_limit(self):
        with self.assertRaises(ValueError):
            self.remember('\u00e9' * 1048576)
        self.assertEqual(self.count(), 0)
        self.remember('\u00e9' * 100)
        self.assertEqual(self.chip.recall('x', actor='owner')['value'], '\u00e9' * 100)

    def test_validation_does_not_write_memory(self):
        for field, value in (('actor', 'a' * 257), ('key', 'k' * 257),
                             ('provenance', 'p' * 4097), ('key', '\ud800'),
                             ('actor', None), ('provenance', ' ')):
            args = dict(key='x', value=1, actor='owner', provenance='test')
            args[field] = value
            with self.subTest(field=field, kind=type(value).__name__):
                with self.assertRaises(ValueError):
                    self.chip.remember(**args)
        self.assertEqual(self.count(), 0)

    def test_serialization_errors_are_value_errors(self):
        recursive = []; recursive.append(recursive)
        deep = []
        for _ in range(1500):
            deep = [deep]
        for value in (object(), recursive, deep, '\ud800', float('nan')):
            with self.assertRaises(ValueError):
                self.remember(value)
        self.assertEqual(self.count(), 0)

    def test_key_preserved_and_numeric_limits_strict(self):
        self.chip.remember(' x ', 1, actor='owner', provenance='test')
        self.assertIsNone(self.chip.recall('x', actor='owner'))
        self.assertEqual(self.chip.recall(' x ', actor='owner')['value'], 1)
        for bad in (True, 1.0, '3', 0, 1001):
            with self.assertRaises(ValueError):
                self.chip.audit_trail(actor='owner', limit=bad)

    def test_denied_actions_persist_in_audit(self):
        self.remember('original')
        for operation in (lambda: self.chip.recall('x', actor='other'),
                          lambda: self.chip.remember('x', 'replacement', actor='other', provenance='bad'),
                          lambda: self.chip.forget('x', actor='other')):
            with self.assertRaises(PermissionError):
                operation()
        events = self.chip.audit_trail(actor='other')
        self.assertEqual([e['outcome'] for e in events], ['denied'] * 3)
        self.assertNotIn('original', json.dumps(events))
        self.assertEqual(self.chip.recall('x', actor='owner')['value'], 'original')

    def test_integrity_failure_is_audited(self):
        self.remember('original')
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE memories SET value='123' WHERE key='x'")
        with self.assertRaises(ValueError):
            self.chip.recall('x', actor='owner')
        self.assertEqual(self.chip.audit_trail(actor='owner')[0]['outcome'], 'integrity_error')

    def test_audit_failure_rolls_back_mutation(self):
        self.remember('original')
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TRIGGER reject_audit BEFORE INSERT ON audit BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        with self.assertRaises(sqlite3.Error):
            self.remember('modified')
        with closing(sqlite3.connect(self.path)) as db, db:
            self.assertEqual(json.loads(db.execute('SELECT value FROM memories').fetchone()[0]), 'original')
            db.execute('DROP TRIGGER reject_audit')
        self.remember('retry')
        self.assertEqual(self.chip.recall('x', actor='owner')['value'], 'retry')

    def test_commit_failure_rolls_back_mutation(self):
        self.remember('original')
        real_connect = sqlite3.connect
        class CommitFails(sqlite3.Connection):
            def commit(self):
                raise sqlite3.OperationalError('commit failure fixture')
        with patch('biochip.core.sqlite3.connect', side_effect=lambda *a, **kw: real_connect(*a, **kw, factory=CommitFails)):
            with self.assertRaises(sqlite3.Error):
                self.remember('modified')
        self.assertEqual(self.chip.recall('x', actor='owner')['value'], 'original')

    def test_owner_read_is_inside_transaction(self):
        real_connect = sqlite3.connect
        class CheckTransaction(sqlite3.Connection):
            def execute(db, sql, *args, **kwargs):
                if 'SELECT owner FROM memories' in sql and not db.in_transaction:
                    raise AssertionError('owner read before acquiring transaction')
                return super().execute(sql, *args, **kwargs)
        with patch('biochip.core.sqlite3.connect', side_effect=lambda *a, **kw: real_connect(*a, **kw, factory=CheckTransaction)):
            self.remember()

    def test_two_instances_one_owner(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        other = BioChip(str(self.path))
        barrier = Barrier(2)
        def create(chip, actor):
            barrier.wait(timeout=5)
            try:
                chip.remember('race', actor, actor=actor, provenance='race test')
                return 'ok', actor
            except PermissionError:
                return 'denied', actor
        with ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(create, self.chip, 'one')
            f2 = pool.submit(create, other, 'two')
            outcomes = [f1.result(timeout=12), f2.result(timeout=12)]
        self.assertEqual(sorted(o[0] for o in outcomes), ['denied', 'ok'])
        owner = next(actor for state, actor in outcomes if state == 'ok')
        self.assertEqual(self.chip.recall('race', actor=owner)['value'], owner)

    def test_new_database_is_private(self):
        import os
        import stat
        self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode), 0o600)

    def test_nonregular_symlink_and_insecure_files_refused(self):
        import os
        link = self.path.parent / 'linked.sqlite3'
        link.symlink_to(self.path)
        for target in (link, self.path.parent):
            with self.assertRaises((ValueError, OSError)):
                BioChip(str(target))
        os.chmod(self.path, 0o644)
        with self.assertRaises(PermissionError):
            BioChip(str(self.path))
        os.chmod(self.path, 0o600)

    def test_memory_database_explicitly_unsupported(self):
        with self.assertRaisesRegex(ValueError, 'file'):
            BioChip(':memory:')

    def test_backup_private_consistent_and_never_overwrites(self):
        import os
        self.remember({'original': 1})
        dest = self.path.parent / 'backup.sqlite3'
        self.chip.backup(str(dest))
        self.assertEqual(os.stat(dest).st_mode & 0o777, 0o600)
        restored = BioChip(str(dest))
        self.assertEqual(restored.recall('x', actor='owner')['value'], {'original': 1})
        with self.assertRaises(FileExistsError):
            self.chip.backup(str(dest))

    def test_legacy_adoption_creates_backup(self):
        self.remember('legacy')
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('PRAGMA user_version=0')
        restored = BioChip(str(self.path))
        self.assertEqual(restored.recall('x', actor='owner')['value'], 'legacy')
        backups = list(self.path.parent.glob('*.legacy-v0-*.sqlite3'))
        self.assertEqual(len(backups), 1)
        with closing(sqlite3.connect(backups[0])) as db, db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 0)
            self.assertEqual(json.loads(db.execute('SELECT value FROM memories').fetchone()[0]), 'legacy')
        with closing(sqlite3.connect(self.path)) as db, db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 1)

    def test_failed_backup_prevents_legacy_adoption(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('PRAGMA user_version=0')
        with patch.object(BioChip, 'backup', side_effect=OSError('disk fixture'), create=True):
            with self.assertRaises(OSError):
                BioChip(str(self.path))
        with closing(sqlite3.connect(self.path)) as db, db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 0)

    def test_future_schema_untouched(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('PRAGMA user_version=99')
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            BioChip(str(self.path))
        self.assertEqual(self.path.read_bytes(), before)

    def test_incompatible_legacy_schema_and_bad_rows_refused(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('ALTER TABLE memories ADD COLUMN surprise TEXT')
            db.execute('PRAGMA user_version=0')
        with self.assertRaises(ValueError):
            BioChip(str(self.path))

    def test_legacy_nonfinite_row_refused_without_deletion(self):
        self.remember('legacy')
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('UPDATE memories SET expires_at=?', (float('inf'),))
            db.execute('PRAGMA user_version=0')
        with self.assertRaisesRegex(ValueError, 'x'):
            BioChip(str(self.path))
        self.assertEqual(self.count(), 1)

    def test_backup_failure_removes_only_reserved_destination(self):
        self.remember()
        dest = self.path.parent / 'backup.sqlite3'
        real_connect = sqlite3.connect
        class BackupFails(sqlite3.Connection):
            def backup(self, *a, **kw):
                raise sqlite3.OperationalError('backup failure fixture')
        with patch('biochip.core.sqlite3.connect', side_effect=lambda *a, **kw: real_connect(*a, **kw, factory=BackupFails)):
            with self.assertRaises(sqlite3.Error):
                self.chip.backup(str(dest))
        self.assertFalse(dest.exists())
        self.assertEqual(self.chip.recall('x', actor='owner')['value'], 1)

    def test_legacy_schema_requires_primary_key(self):
        from biochip.core import SCHEMA
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('DROP TABLE memories')
            db.execute(SCHEMA[0].replace('key TEXT PRIMARY KEY', 'key TEXT'))
            db.execute('PRAGMA user_version=0')
        with self.assertRaises(ValueError):
            BioChip(str(self.path))
