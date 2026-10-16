"""Operator-owned, immutable fleet configuration."""
from dataclasses import FrozenInstanceError, replace
import json
import tempfile
from pathlib import Path
import unittest

from biochip.fleet.config import FleetLimits, ModelApproval, FleetConfig, load_config


def approval(**changes):
    data = dict(provider='ollama', name='fixture-model', endpoint='http://127.0.0.1:11434',
                approved_by='owner', approved_at='2026-10-16T00:00:00+00:00',
                locality_evidence='operator reviewed local server configuration',
                license_evidence='operator reviewed model card', operator_confirmed_local=True)
    data.update(changes)
    return ModelApproval(**data)


def config(directory, **changes):
    data = dict(operator='owner', project='p', state_directory=Path(directory) / 'state',
                planner=approval(), reviewer=None, limits=FleetLimits())
    data.update(changes)
    return FleetConfig(**data)


class FleetConfigTests(unittest.TestCase):
    def test_default_limits(self):
        limits = FleetLimits()
        self.assertEqual((limits.max_inflight, limits.queue_capacity, limits.max_model_calls), (1, 32, 8))
        self.assertEqual((limits.max_output_tokens, limits.deadline_seconds, limits.max_message_bytes), (1024, 600.0, 1048576))
        self.assertEqual(limits.max_tool_calls, 10)

    def test_rejects_invalid_limits(self):
        for field, value in (('max_inflight', 2), ('queue_capacity', 33), ('max_model_calls', 9),
                             ('max_output_tokens', 1025), ('deadline_seconds', 601), ('deadline_seconds', float('nan')),
                             ('max_message_bytes', 1048577), ('max_tool_calls', 11)):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                FleetLimits(**{field: value})
        for field in FleetLimits.__dataclass_fields__:
            for value in (True, 0, '1', float('inf')):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    FleetLimits(**{field: value})

    def test_rejects_unapproved_models(self):
        for field, value in (('approved_by', ''), ('locality_evidence', ''), ('license_evidence', ''),
                             ('operator_confirmed_local', False), ('operator_confirmed_local', 'yes'),
                             ('approved_at', '2026-10-16'), ('approved_at', 'nonsense'),
                             ('endpoint', 'https://example.invalid'), ('name', '')):
            with self.subTest(field=field), self.assertRaises(ValueError):
                approval(**{field: value})

    def test_state_directory_is_explicit(self):
        with self.assertRaises(ValueError):
            config('/tmp', state_directory=Path('relative'))
        with self.assertRaises(ValueError):
            config('/tmp', planner=approval(approved_by='different-operator'))

    def test_frozen_config(self):
        a = approval()
        with self.assertRaises(FrozenInstanceError):
            a.name = 'other'
        with self.assertRaises(FrozenInstanceError):
            FleetLimits().max_inflight = 100

    def test_load_strict_and_copies_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            from dataclasses import asdict
            raw = asdict(config(tmp)); raw['state_directory'] = str(raw['state_directory'])
            path = Path(tmp) / 'config.json'; path.write_text(json.dumps(raw))
            loaded = load_config(path)
            raw['planner']['name'] = 'changed'
            self.assertEqual(loaded.planner.name, 'fixture-model')
            self.assertFalse(loaded.state_directory.exists())
            raw['api_key'] = 'not-allowed'; path.write_text(json.dumps(raw))
            with self.assertRaises(ValueError):
                load_config(path)

    def test_config_rejects_duplicate_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config.json'
            path.write_text('{"operator":"one","operator":"two"}')
            with self.assertRaises(ValueError):
                load_config(path)
