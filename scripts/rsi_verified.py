#!/usr/bin/env python3
"""Auditable, repeat-measured entry point to GPT-DOUG's existing bounded RSI.

No automatic merge, deployment or external actions. Evaluation source is
operator-owned and must reside outside the agent-editable repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from rsi_supervisor import ExternalBenchmark, Metrics, RecursiveImprovement, require_clean_git_repo
from zyra_agent import MissionBudget, ZyraAgent

SCHEMA = 'gpt-doug.rsi-verified.v1'
MAX_REPEATS = 7


def _timestamp():
    return datetime.now(timezone.utc).isoformat()


def validate_repeats(n, tolerance):
    if type(n) is not int or not 2 <= n <= MAX_REPEATS:
        raise ValueError('benchmark repeats must be between 2 and 7')
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)) or not math.isfinite(tolerance) or not 0 <= tolerance <= 0.05:
        raise ValueError('max quality spread must be finite and between 0 and 0.05')


class VerifiedBenchmark:
    """Repeated, stable, independent evidence with conservative aggregation."""

    def __init__(self, source, *, repeats=3, max_quality_spread=0.0):
        validate_repeats(repeats, max_quality_spread)
        self.source = source
        self.repeats = repeats
        self.max_quality_spread = max_quality_spread
        self.observations = []

    def __call__(self):
        samples = [self.source() for _ in range(self.repeats)]
        if not all(isinstance(s, Metrics) for s in samples):
            raise ValueError('all benchmark runs must return validated Metrics')
        quality_spread = max(s.quality for s in samples) - min(s.quality for s in samples)
        result = {'at': _timestamp(), 'samples': [s.to_dict() for s in samples],
                  'quality_spread': round(quality_spread, 12), 'stable': quality_spread <= self.max_quality_spread + 1e-12}
        self.observations.append(result)
        if not result['stable']:
            raise ValueError('unstable benchmark: quality spread exceeds allowed tolerance')
        # Never average away regressions, security failures, or worst-case quality.
        return Metrics(quality=min(s.quality for s in samples),
                       regressions=max(s.regressions for s in samples),
                       security_ok=all(s.security_ok for s in samples))


def audit_chain(report):
    """Hash chained event log; tamper-evident if head digest is retained separately."""
    records = []
    previous = '0' * 64
    for i, event in enumerate(report.get('cycles', []), 1):
        payload = {'sequence': i, 'previous_sha256': previous, 'event': event}
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        records.append({'sequence': i, 'previous_sha256': previous,
                        'event_sha256': digest})
        previous = digest
    return {'algorithm': 'sha256', 'events': records, 'head_sha256': previous,
            'warning': 'Hash chain is not a digital signature; independently preserve the head digest.'}


def save_report(path, repo, report):
    destination = Path(path).expanduser().resolve()
    if destination == repo or repo in destination.parents:
        raise ValueError('report must be outside the editable repository')
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.rsi-', suffix='.json', dir=destination.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(report, out, indent=2, sort_keys=True)
            out.write('\n')
        os.chmod(tmp, 0o600)
        os.replace(tmp, destination)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return destination


def require_local_model_url(value):
    try:
        u = urlsplit(value)
        valid_hosts = {'127.0.0.1', 'localhost', '::1'}
        if (u.scheme != 'http' or u.hostname not in valid_hosts or
                u.username is not None or u.password is not None or
                u.port not in (None, 11434) or u.path not in ('', '/') or
                u.query or u.fragment):
            raise ValueError('Model endpoint must be a local Ollama HTTP endpoint')
    except (ValueError, AttributeError) as exc:
        raise ValueError('Model endpoint must be an authorized loopback address') from exc
    return value


def run_verified(*, repo, benchmark_path, goal=None, cycles=1, repeats=3,
                 min_gain=0.01, model='qwen2.5-coder:7b',
                 base_url='http://127.0.0.1:11434', max_quality_spread=0.0,
                 probe_only=False, agent=None):
    validate_repeats(repeats, max_quality_spread)
    require_local_model_url(base_url)
    repo = require_clean_git_repo(str(repo))
    evaluator = ExternalBenchmark(Path(benchmark_path), repo)
    verified = VerifiedBenchmark(evaluator, repeats=repeats, max_quality_spread=max_quality_spread)
    result = {'schema': SCHEMA, 'created_at': _timestamp(),
              'mode': 'probe-only' if probe_only else 'bounded-local-agent-evolution',
              'benchmark_sha256': evaluator.digest,
              'benchmark_path': str(evaluator.script),
              'repeats': repeats, 'quality_spread_tolerance': max_quality_spread,
              'promotion': 'human-review-only',
              'uses_paid_api': False}
    if probe_only:
        baseline = verified()
        result.update({'status': 'BENCHMARK_MEASURED', 'baseline': baseline.to_dict(), 'cycles': []})
    else:
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError('goal is required unless --probe is set')
        # Existing supervisor enforces 1-3 cycles, tracked checkpoints, rollback,
        # kill switch, unchanged benchmark and safety/unit/lint checks.
        runner = RecursiveImprovement(agent or ZyraAgent(repo, model=model,
                                                         base_url=base_url,
                                                         budget=MissionBudget()),
                                      cycles=cycles, benchmark=verified, min_gain=min_gain)
        result.update(runner.run(goal))
        result['model'] = model
        result['min_gain'] = min_gain
    result['measurements'] = verified.observations
    result['audit'] = audit_chain(result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--benchmark', required=True, help='trusted Python evaluator installed outside repo')
    parser.add_argument('--goal')
    parser.add_argument('--probe', action='store_true', help='offline evaluator preflight, no agent calls or changes')
    parser.add_argument('--cycles', type=int, default=2)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--max-quality-spread', type=float, default=0.0)
    parser.add_argument('--min-gain', type=float, default=0.01)
    parser.add_argument('--model', default='qwen2.5-coder:7b')
    parser.add_argument('--base-url', default='http://127.0.0.1:11434')
    parser.add_argument('--report', default=str(Path.home() / '.gpt-doug' / 'rsi' / 'verified-report.json'))
    args = parser.parse_args(argv)
    try:
        root = Path(args.repo).expanduser().resolve()
        output = Path(args.report).expanduser().resolve()
        if output == root or root in output.parents:
            raise ValueError('report must be outside the repository')
        report = run_verified(repo=root, benchmark_path=args.benchmark, goal=args.goal,
                              cycles=args.cycles, repeats=args.repeats, min_gain=args.min_gain,
                              model=args.model, base_url=args.base_url,
                              max_quality_spread=args.max_quality_spread, probe_only=args.probe)
        destination = save_report(output, root, report)
        print(json.dumps({'status': report['status'], 'report': str(destination),
                          'cycles': len(report['cycles']), 'benchmark_repeats': args.repeats,
                          'audit_head_sha256': report['audit']['head_sha256']}, indent=2))
        return 0 if report['status'] in ('BENCHMARK_MEASURED', 'REVIEW_REQUIRED', 'MEASURED_GAIN_REVIEW_REQUIRED') else 1
    except (ValueError, OSError, TimeoutError) as exc:
        # Do not print raw traceback, model outputs, or HTTP credentials.
        parser.exit(1, 'RSI BLOCKED: ' + type(exc).__name__ + '\n')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
