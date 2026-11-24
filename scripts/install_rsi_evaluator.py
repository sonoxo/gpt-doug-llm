#!/usr/bin/env python3
"""Copy the reference evaluator outside the agent-editable source tree."""
import argparse
import os
from pathlib import Path


def install(src, dest, repo):
    src = Path(src).resolve(strict=True)
    repo = Path(repo).resolve(strict=True)
    dest = Path(dest).expanduser().resolve()
    if src != repo / 'benchmarks' / 'zyra_action_quality.py':
        raise ValueError('Source must be the repository reference evaluator')
    if dest == repo or repo in dest.parents:
        raise ValueError('Evaluator must be outside the editable repository')
    if not dest.parent.exists():
        dest.parent.mkdir(mode=0o700, parents=True)
    if dest.exists():
        raise ValueError('Destination exists; refusing silent replacement')
    fd = os.open(dest, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(src.read_bytes())
    except BaseException:
        dest.unlink(missing_ok=True)
        raise
    return dest


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', default='.')
    p.add_argument('--dest', default=str(Path.home() / '.gpt-doug' / 'rsi' / 'evaluator' / 'zyra_action_quality.py'))
    a = p.parse_args(argv)
    try:
        repo = Path(a.repo).expanduser().resolve(strict=True)
        print('Installed ' + str(install(repo / 'benchmarks' / 'zyra_action_quality.py', a.dest, repo)))
        return 0
    except (OSError, ValueError) as exc:
        p.exit(1, 'RSI evaluator install blocked: ' + type(exc).__name__ + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
