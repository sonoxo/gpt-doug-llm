"""No *additional* reviews for bounded offline research; never a security bypass.

This is a descriptive policy query, not a runtime authorization primitive.
Existing validation, human-review, patent/data-rights and security controls remain.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_POLICY_FILE = (Path(__file__).resolve().parents[2] / 'safety-shield' / 'ontology' /
                'biopineal-research-freedom-v1.json')
_NO_REVIEW = frozenset({
    'source_search', 'read_heartbeat', 'operator_show',
    'simulate_classical_quantum', 'validate_synthetic_scenario',
    'validate_research_ontology',
})
_EXPECTED = {
    'schema_version': '1.0.0',
    'id': 'BIOPINEAL_NO_UNNECESSARY_GUARDRAILS_V1',
    'authority': 'RESEARCH_ONLY',
    'scope': 'LOCAL_SYNTHETIC_RESEARCH_ONLY',
    'disables_existing_security_controls': False,
    'grants_government_authority': False,
    'grants_patent_or_third_party_rights': False,
    'automatic_publication': False,
    'requires_input_validation': True,
    'requires_bounded_resources': True,
    'third_party_system_access': False,
    'human_review_for_publication': True,
}
_FIELDS = frozenset((*_EXPECTED, 'no_extra_review_actions'))
_ACTION = re.compile(r'[a-z][a-z0-9_]{0,63}\Z')


def load_policy(path: Path | None = None) -> dict[str, Any]:
    """Load one fixed policy schema; rejected edits cannot increase privileges."""
    target = _POLICY_FILE if path is None else Path(path)
    if target.is_symlink() or not target.is_file() or target.stat().st_size > 16384:
        raise ValueError('research freedom policy must be a regular <=16 KiB file')
    try:
        policy = json.loads(target.read_text(encoding='utf-8'),
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError('invalid nonfinite policy')))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('invalid research freedom policy JSON') from exc
    if not isinstance(policy, dict) or set(policy) != _FIELDS:
        raise ValueError('invalid research freedom policy keys')
    for field, expected in _EXPECTED.items():
        if type(policy[field]) is not type(expected) or policy[field] != expected:
            raise ValueError('research freedom policy may not change authority or controls: ' + field)
    actions = policy['no_extra_review_actions']
    if (not isinstance(actions, list) or len(actions) != len(_NO_REVIEW)
            or not all(isinstance(a, str) and _ACTION.fullmatch(a) for a in actions)
            or set(actions) != _NO_REVIEW):
        raise ValueError('research freedom allowlist may not expand')
    return policy


def evaluate(action: str) -> dict[str, Any]:
    """Assess if extra *research review* is needed; never execute an action."""
    if not isinstance(action, str) or not _ACTION.fullmatch(action):
        raise ValueError('action must be an ASCII local research action identifier')
    policy = load_policy()
    free = action in policy['no_extra_review_actions']
    return {
        'policy_id': policy['id'],
        'scope': policy['scope'],
        'authority': 'RESEARCH_ONLY',
        'action': action,
        'decision': 'NO_EXTRA_REVIEW_REQUIRED' if free else 'NORMAL_CONTROLS_REQUIRED',
        'meaning': ('No additional operator-review step for an otherwise valid local synthetic exercise.'
                    if free else 'This rule cannot waive existing reviews, security or data-rights checks.'),
        'input_validation_still_required': True,
        'existing_security_controls_unchanged': True,
        'grants_external_permission': False,
        'military_authority': False,
        'patent_rights_granted': False,
        'action_executed': False,
        'external_calls': 0,
    }
