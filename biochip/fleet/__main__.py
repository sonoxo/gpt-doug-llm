"""Foreground local planning CLI. No background service or external tools."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import platform
from pathlib import Path
import sqlite3
import sys

from ai_killswitch import AIKillSwitchEngaged, emergency_stop, status as stop_status
from .config import FleetConfig, load_config
from .ledger import MissionLedger
from .supervisor import FleetSupervisor
from ..models import Model, ModelRouter, require_allowed
from ..validation import MAX_BYTES, bounded_text, encode_json


def inspect_inventory(config: FleetConfig) -> dict:
    selected, cache, errors = [], {}, {}
    for role, approval in (('planner', config.planner), ('reviewer', config.reviewer)):
        if approval is None:
            continue
        key = (approval.provider, approval.endpoint)
        if key not in cache:
            cache[key] = ModelRouter({approval.provider: approval.endpoint}, timeout=5).discover()
        models, diagnostic = cache[key]
        errors.update({role + ':' + name: error for name, error in diagnostic.items()})
        selected.append(dict(role=role, provider=approval.provider, model=approval.name,
                             endpoint=approval.endpoint, available=Model(approval.provider, approval.name) in models,
                             installed_models=[m.name for m in models]))
    return dict(selected=selected, errors=errors,
                discovery_verified=not errors and all(row['available'] for row in selected),
                inference_verified=None, review_verified=None, external_tools_enabled=False,
                observed_os=platform.system(), python_version=platform.python_version(),
                macos_acceptance_verified=None, stop=stop_status())


def _emit(value) -> None:
    # Escaped JSON on the terminal, no raw model-controlled ANSI sequences.
    raw = encode_json(value)
    sys.stdout.write(raw.decode('utf-8') + '\n')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='GPT-Doug Kraken: bounded local proposals, never tool execution')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('doctor', 'inventory', 'plan', 'run', 'status'):
        command = commands.add_parser(name)
        command.add_argument('--config', required=True, type=Path)
        if name == 'status':
            command.add_argument('--mission', required=True)
    commands.add_parser('stop')
    args = parser.parse_args(argv)
    try:
        if args.command == 'stop':
            _emit(emergency_stop('operator_kraken_stop'))
            return 0
        config = load_config(args.config)
        if args.command == 'status':
            ledger = MissionLedger(config.state_directory / 'missions.sqlite3', read_only=True)
            result = ledger.read(args.mission, operator=config.operator, project=config.project)
            result['external_tools_enabled'] = False
            _emit(result)
            return 0
        if args.command in ('doctor', 'inventory', 'plan'):
            result = inspect_inventory(config)
            if args.command == 'plan':
                result['limits'] = asdict(config.limits)
                result['mode'] = 'proposal_only'
                result['ready_to_run'] = result['discovery_verified'] and not result['stop']['stopped']
            _emit(result)
            if args.command == 'plan' and result['stop']['stopped']:
                return 3
            return 0 if result['discovery_verified'] else 4
        require_allowed('Kraken foreground run')
        raw = sys.stdin.buffer.read(config.limits.max_message_bytes + 1)
        if len(raw) > config.limits.max_message_bytes:
            raise ValueError('prompt exceeds byte limit')
        prompt = raw.decode('utf-8')
        bounded_text(prompt, name='prompt', max_bytes=config.limits.max_message_bytes)
        ledger = MissionLedger(config.state_directory / 'missions.sqlite3')
        with FleetSupervisor(config, ledger) as supervisor:
            supervisor.submit(prompt)
            result = supervisor.run_pending()[0]
        result.update(observed_os=platform.system(), macos_acceptance_verified=None, mode='proposal_only')
        _emit(result)
        return 0 if result['state'] == 'completed' else 3 if result['state'] == 'stopped' else 4
    except AIKillSwitchEngaged:
        _emit(dict(state='stopped', reason='operator_stop', external_tools_enabled=False))
        return 3
    except (ValueError, TypeError, PermissionError) as exc:
        _emit(dict(error=type(exc).__name__, reason='configuration_or_policy_error', external_tools_enabled=False))
        return 2
    except (OSError, RuntimeError, sqlite3.Error, KeyError) as exc:
        _emit(dict(error=type(exc).__name__, reason='unavailable_or_uncertain', external_tools_enabled=False))
        return 4
    except KeyboardInterrupt:
        _emit(dict(state='uncertain', reason='interrupted', external_tools_enabled=False))
        return 4


if __name__ == '__main__':
    raise SystemExit(main())
