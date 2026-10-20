"""Frozen operator configuration. Attestation is not technical proof of a backend."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import os
from pathlib import Path
import stat

from ..transport import normalize_loopback_url
from ..validation import MAX_BYTES, bounded_int, bounded_text, decode_json, finite_number


@dataclass(frozen=True)
class FleetLimits:
    max_inflight: int = 1
    queue_capacity: int = 32
    max_model_calls: int = 8
    max_tool_calls: int = 10
    max_output_tokens: int = 1024
    deadline_seconds: float = 600.0
    max_message_bytes: int = MAX_BYTES

    def __post_init__(self):
        for name, ceiling in (('max_inflight', 1), ('queue_capacity', 32), ('max_model_calls', 8),
                              ('max_tool_calls', 10), ('max_output_tokens', 1024), ('max_message_bytes', MAX_BYTES)):
            bounded_int(getattr(self, name), name=name, minimum=1, maximum=ceiling)
        finite_number(self.deadline_seconds, name='deadline_seconds', minimum=0,
                      exclusive_minimum=True, maximum=600)


@dataclass(frozen=True)
class ModelApproval:
    provider: str
    name: str
    endpoint: str
    approved_by: str
    approved_at: str
    locality_evidence: str
    license_evidence: str
    operator_confirmed_local: bool

    def __post_init__(self):
        for name in ('provider', 'name', 'approved_by', 'approved_at'):
            bounded_text(getattr(self, name), name=name, max_bytes=256)
        for name in ('locality_evidence', 'license_evidence'):
            bounded_text(getattr(self, name), name=name, max_bytes=4096)
        if self.operator_confirmed_local is not True:
            raise ValueError('explicit operator confirmation of local inference is required')
        try:
            stamp = datetime.fromisoformat(self.approved_at.replace('Z', '+00:00'))
            if stamp.tzinfo is None or stamp.utcoffset() is None:
                raise ValueError('approval timestamp must have a timezone')
        except (ValueError, OverflowError) as exc:
            raise ValueError('approval timestamp must be timezone-aware ISO 8601') from exc
        object.__setattr__(self, 'endpoint', normalize_loopback_url(self.endpoint))


@dataclass(frozen=True)
class FleetConfig:
    operator: str
    project: str
    state_directory: Path
    planner: ModelApproval
    reviewer: ModelApproval | None = None
    limits: FleetLimits = field(default_factory=FleetLimits)

    def __post_init__(self):
        bounded_text(self.operator, name='operator', max_bytes=256)
        bounded_text(self.project, name='project', max_bytes=256)
        if not isinstance(self.state_directory, Path) or not self.state_directory.is_absolute() or '\0' in str(self.state_directory):
            raise ValueError('state_directory must be an explicit absolute Path')
        if not isinstance(self.limits, FleetLimits):
            raise ValueError('invalid fleet limits')
        if not isinstance(self.planner, ModelApproval):
            raise ValueError('planner approval is required')
        for selected in (self.planner, self.reviewer):
            if selected is not None and (not isinstance(selected, ModelApproval) or selected.approved_by != self.operator):
                raise ValueError('each selected model must be approved by the configured operator')


def load_config(path: Path) -> FleetConfig:
    path = Path(path).expanduser()
    fd = os.open(str(path), os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or (os.name == 'posix' and (info.st_uid != os.geteuid() or info.st_mode & 0o022)):
            raise PermissionError('config must be an operator-owned regular file, not writable by others')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = decode_json(stream.read(MAX_BYTES + 1))
    finally:
        os.close(fd)
    if not isinstance(data, dict):
        raise ValueError('fleet config must be an object')
    required = {'operator', 'project', 'state_directory', 'planner'}
    if not required <= data.keys() or data.keys() - (required | {'reviewer', 'limits'}):
        raise ValueError('missing or unknown fleet configuration fields')
    try:
        if not isinstance(data['state_directory'], str):
            raise ValueError('state directory must be a string')
        planner = ModelApproval(**data['planner'])
        reviewer = ModelApproval(**data['reviewer']) if data.get('reviewer') is not None else None
        limits = FleetLimits(**data.get('limits', {}))
        return FleetConfig(data['operator'], data['project'], Path(data['state_directory']), planner, reviewer, limits)
    except TypeError as exc:
        raise ValueError('invalid or unknown fields in fleet configuration') from exc
