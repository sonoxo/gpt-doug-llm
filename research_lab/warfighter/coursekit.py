"""Warfighter CourseKit: deterministic, offline-only synthetic training assessment.

No external data is fetched. Source references and operational telemetry are never
inferred from private cloud folder URLs. Scores describe a toy quiz, not readiness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

VERSION = '1.0.0'
MAX_BYTES = 65536
COURSE_KEYS = frozenset({'schema_version', 'course_id', 'authority', 'source_kind',
                         'classification', 'synthetic', 'title', 'items'})
ITEM_KEYS = frozenset({'id', 'domain', 'prompt', 'choices', 'correct_choice', 'rationale'})
DOMAINS = frozenset({'opsec', 'defensive-cyber', 'communications', 'logistics',
                     'continuity', 'readiness'})
ID_RE = re.compile(r'wr:course:[a-z0-9._-]{1,80}\Z')
QUESTION_RE = re.compile(r'q[0-9]{3,4}\Z')


def _pairs_unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _nonfinite(_: str) -> None:
    raise ValueError('nonfinite JSON literal prohibited')


def load_local_json(path: Path, *, allowed_root: Path) -> dict[str, Any]:
    """Read a small UTF-8 JSON object inside one explicitly allowed local root."""
    path = Path(path)
    if path.is_symlink():
        raise ValueError('symlink inputs prohibited')
    try:
        root = Path(allowed_root).resolve(strict=True)
        full = path.resolve(strict=True)
        if not full.is_relative_to(root) or not full.is_file():
            raise ValueError('input outside allowed root or not a file')
        if full.stat().st_size > MAX_BYTES:
            raise ValueError('input exceeds 64 KiB')
        value = json.loads(full.read_bytes().decode('utf-8'),
                           object_pairs_hook=_pairs_unique, parse_constant=_nonfinite)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('invalid UTF-8 JSON') from exc
    except OSError as exc:
        raise ValueError('input unavailable') from exc
    if not isinstance(value, dict):
        raise ValueError('top-level JSON must be object')
    return value


def _text(value: Any, label: str, limit: int = 400) -> None:
    if (not isinstance(value, str) or not 1 <= len(value) <= limit or
            any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise ValueError('invalid ' + label)


def validate_pack(value: Any) -> dict[str, Any]:
    """Fail closed on non-synthetic, malformed, or unbounded course packs."""
    if not isinstance(value, dict) or set(value) != COURSE_KEYS:
        raise ValueError('course pack requires exact fields')
    if (value['schema_version'] != VERSION or
            value['authority'] != 'RESEARCH_ONLY' or
            value['source_kind'] != 'SYNTHETIC' or
            value['classification'] != 'SYNTHETIC' or
            value['synthetic'] is not True):
        raise ValueError('only synthetic, research-only courses allowed')
    if not isinstance(value['course_id'], str) or not ID_RE.fullmatch(value['course_id']):
        raise ValueError('invalid course ID')
    _text(value['title'], 'course title', 120)
    items = value['items']
    if not isinstance(items, list) or not 5 <= len(items) <= 50:
        raise ValueError('course must contain 5 to 50 questions')
    used: set[str] = set()
    for item in items:
        if not isinstance(item, dict) or set(item) != ITEM_KEYS:
            raise ValueError('course question requires exact fields')
        qid = item['id']
        if not isinstance(qid, str) or not QUESTION_RE.fullmatch(qid) or qid in used:
            raise ValueError('invalid or duplicate question ID')
        used.add(qid)
        if item['domain'] not in DOMAINS:
            raise ValueError('unapproved exercise domain')
        _text(item['prompt'], 'question', 400)
        _text(item['rationale'], 'rationale', 600)
        choices = item['choices']
        if (not isinstance(choices, list) or not 2 <= len(choices) <= 5):
            raise ValueError('question requires 2 to 5 choices')
        for option in choices:
            _text(option, 'answer option', 200)
        if len(set(option.casefold() for option in choices)) != len(choices):
            raise ValueError('duplicate options')
        if type(item['correct_choice']) is not int or not 0 <= item['correct_choice'] < len(choices):
            raise ValueError('correct choice index invalid')
    encoded = json.dumps(value, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=True, allow_nan=False).encode('ascii')
    if len(encoded) > MAX_BYTES:
        raise ValueError('course pack too large')
    return json.loads(encoded.decode('ascii'))


def fingerprint(value: dict[str, Any]) -> str:
    """Stable content checksum; not a publisher signature or source attestation."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=True, allow_nan=False).encode('ascii')).hexdigest()


def validate_responses(value: Any, pack: dict[str, Any]) -> dict[str, int]:
    if not isinstance(value, dict) or set(value) != {'schema_version', 'course_id', 'responses'}:
        raise ValueError('response file requires exact fields')
    if value['schema_version'] != VERSION or value['course_id'] != pack['course_id']:
        raise ValueError('responses must match course ID and schema')
    responses = value['responses']
    if not isinstance(responses, dict):
        raise ValueError('responses must be object')
    indexed = {item['id']: len(item['choices']) for item in pack['items']}
    for qid, choice in responses.items():
        if qid not in indexed or type(choice) is not int or not 0 <= choice < indexed[qid]:
            raise ValueError('unknown question or invalid response')
    return dict(responses)


def grade(pack: dict[str, Any], response_doc: dict[str, Any]) -> dict[str, Any]:
    pack = validate_pack(pack)
    responses = validate_responses(response_doc, pack)
    per_domain: dict[str, dict[str, int]] = {}
    feedback: list[dict[str, str]] = []
    total_correct = 0
    for item in pack['items']:
        qid = item['id']
        domain = item['domain']
        counts = per_domain.setdefault(domain, {'correct': 0, 'total': 0})
        counts['total'] += 1
        choice = responses.get(qid)
        correct = choice == item['correct_choice'] if choice is not None else False
        if correct:
            counts['correct'] += 1
            total_correct += 1
        feedback.append({'question_id': qid, 'domain': domain,
                         'result': 'CORRECT' if correct else 'UNANSWERED' if choice is None else 'REVIEW',
                         'rationale': item['rationale']})
    for counts in per_domain.values():
        counts['score_pct'] = 100 * counts['correct'] // counts['total']
    return {'status': 'SYNTHETIC_ASSESSMENT', 'authority': 'RESEARCH_ONLY',
            'classification': 'SYNTHETIC', 'operational_ready': False,
            'human_reviewed': False, 'external_calls': 0,
            'course_id': pack['course_id'], 'pack_sha256': fingerprint(pack),
            'question_count': len(pack['items']), 'answered': len(responses),
            'correct': total_correct,
            'score_pct': 100 * total_correct // len(pack['items']),
            'per_domain': dict(sorted(per_domain.items())), 'feedback': feedback}


def sources() -> dict[str, Any]:
    """Source placeholders, not assertions about contents of user-provided URLs."""
    return {'status': 'AWAITING_AUTHORIZED_COURSE_EXPORTS',
            'authority': 'RESEARCH_ONLY', 'external_calls': 0,
            'remote_folders_imported': 0, 'source_slots': 2,
            'auto_drive_access': False, 'auto_publish': False,
            'instructions': ('Connect authorized course sources privately; review rights and '
                             'classification before manually creating a SYNTHETIC course pack. '
                             'Never commit private Drive links or raw controlled material.')}


def command(action: str, *, pack: Path | None = None,
            input_root: Path | None = None,
            responses: Path | None = None) -> dict[str, Any]:
    if action == 'sources':
        return sources()
    if action not in {'validate', 'grade'} or pack is None or input_root is None:
        raise ValueError('course validate/grade requires --pack and --input-root')
    course = validate_pack(load_local_json(pack, allowed_root=input_root))
    if action == 'validate':
        return {'status': 'VALID_SYNTHETIC_COURSE', 'authority': 'RESEARCH_ONLY',
                'classification': 'SYNTHETIC', 'external_calls': 0,
                'course_id': course['course_id'], 'question_count': len(course['items']),
                'pack_sha256': fingerprint(course)}
    if responses is None:
        raise ValueError('course grade requires --responses')
    return grade(course, load_local_json(responses, allowed_root=input_root))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('sources', 'validate', 'grade'))
    parser.add_argument('--pack', type=Path)
    parser.add_argument('--input-root', type=Path)
    parser.add_argument('--responses', type=Path)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(command(args.action, pack=args.pack, input_root=args.input_root,
                                 responses=args.responses), sort_keys=True, indent=2))
        return 0
    except (ValueError, TypeError, OSError, OverflowError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)[:200]}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
