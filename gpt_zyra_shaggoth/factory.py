"""GPT-Doug-Shaggoth Autonomous Factory: local, bounded, review-gated drafts.

Autonomy here means: after explicit local job intake, one worker advances that job
through planning, draft generation, exact static verification and review queues.
It never executes generated code, provisions accounts, deploys, self-replicates,
searches for secrets or grants credentials. Local Ollama is optional/opt-in.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import ast
import hashlib
import io
import json
import os
import re
import secrets
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
import webbrowser
import zipfile
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
UI = Path(__file__).with_name('factory_ui')
DEFAULT_STATE = Path.home() / '.gpt-doug' / 'shaggoth-factory'
POLICY_REL = 'safety-shield/ontology/universal-galactic-federation-guardrails-v1.json'
MAX_GOAL = 480
MAX_ACTIVE = 48
MAX_TOTAL = 500
MAX_JOB_BYTES = 4096
MAX_DRAFT = 32768
MAX_EVENTS = 80
MAX_SSE_CLIENTS = 8
ALLOWED_KINDS = ('python-scaffold', 'research-brief', 'test-plan')
ALLOWED_BACKENDS = ('offline', 'ollama')
STAGES = ('PLANNING', 'BUILDING', 'VERIFYING', 'CRITIQUING', 'AWAITING_REVIEW')
EXPECTED_RULES = {
    'automaticBlocking': False, 'automaticContainment': False,
    'humanApprovalForContainment': True,
    'humanApprovalForConsequentialExternalAction': True,
    'externalThirdPartyAction': False, 'destructiveAction': False,
    'offensiveReplication': False, 'credentialAcquisition': False,
    'targetExploitation': False, 'uncontrolledAgentReplication': False,
    'autonomousFundsTransfer': False,
    'transcriptRequiredBeforeSemanticLearning': True,
    'authoritativeEvidenceRequiredForLegalPromotion': True,
    'patentClaimsCopiedIntoImplementationRequirements': False,
    'patentMaterialPriorArtReferenceOnly': True,
    'memoryRequiresProvenance': True,
    'modelWeightsModifiedBySourceIngestion': False,
    'masterLockRequiredForPublishedGuardrailState': True,
}
ROLES = (
    ('GPT-Doug', 'Planner', 'Defines an auditable local task'),
    ('GPT-Shaggoth', 'Fabricator', 'Builds a confined draft bundle'),
    ('GPT-Pineal', 'Verifier', 'Checks syntax, provenance and checksums'),
    ('GPT-Chaos', 'Critic', 'Flags uncertainty and untrusted output'),
    ('GPT-Redpanda', 'Reviewer gate', 'Awaits explicit human sign-off'),
)
SENSITIVE_RE = re.compile(
    r'(?:\bAKIA[A-Z0-9]{16}\b|\b(?:ghp|github_pat|sk-proj)[-_][A-Za-z0-9_-]{15,}'
    r'|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\bpassword\s*[:=]\s*\S+)',
    re.I,
)
DANGEROUS_RE = re.compile(
    r'\b(?:steal|harvest|exfiltrat(?:e|ion)|bypass|brute[ -]?force)\b.{0,80}'
    r'\b(?:credentials?|tokens?|passwords?|keys?|permissions?|rate[ -]?limits?)\b', re.I,
)
ID_RE = re.compile(r'^[0-9a-f]{32}$')


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def canonical(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def check_file(root: Path, rel: str) -> Path | None:
    current = root
    for part in Path(rel).parts:
        current = current / part
        if current.is_symlink():
            return None
    return current if current.is_file() else None


def policy_snapshot(root: Path, *, standalone_demo: bool = False) -> dict[str, Any]:
    path = check_file(root, POLICY_REL)
    if path is None:
        if standalone_demo:
            return {'state': 'DEMO_ONLY', 'reason': 'No repository policy; offline draft sandbox only',
                    'rules_matching': 0, 'rules_total': len(EXPECTED_RULES),
                    'fingerprint': None, 'local_drafts_allowed': True, 'ollama_allowed': False}
        return {'state': 'UNVERIFIED', 'reason': 'Canonical guardrail source missing or symlinked',
                'rules_matching': 0, 'rules_total': len(EXPECTED_RULES),
                'fingerprint': None, 'local_drafts_allowed': False, 'ollama_allowed': False}
    try:
        if path.stat().st_size > 128 * 1024:
            raise ValueError('policy file exceeds size cap')
        raw = path.read_bytes()
        data = json.loads(raw)
        rules = data['guardrails']
        if not isinstance(rules, dict):
            raise ValueError('guardrails must be a mapping')
        matching = sum(rules.get(name) is wanted for name, wanted in EXPECTED_RULES.items())
        good = (data['mode'] == 'DEFENSIVE_AUTHORIZED_ENVIRONMENTS_ONLY'
                and data['status'] == 'ACTIVE'
                and data['truth_boundary']['external_legal_status'] == 'NOT_PROMOTED_TO_STATUTE_OR_REGULATION'
                and matching == len(EXPECTED_RULES))
        return {'state': 'VERIFIED' if good else 'REVIEW_REQUIRED',
                'reason': 'Exact project controls checked' if good else 'Project policy drift or incomplete',
                'rules_matching': matching, 'rules_total': len(EXPECTED_RULES),
                'fingerprint': sha256(raw)[:16],
                'local_drafts_allowed': good, 'ollama_allowed': good}
    except (ValueError, OSError, TypeError, KeyError, UnicodeError):
        return {'state': 'UNVERIFIED', 'reason': 'Policy cannot be parsed or verified',
                'rules_matching': 0, 'rules_total': len(EXPECTED_RULES),
                'fingerprint': None, 'local_drafts_allowed': False, 'ollama_allowed': False}


def validate_goal(kind: Any, goal: Any, backend: Any) -> tuple[str, str, str]:
    if kind not in ALLOWED_KINDS or backend not in ALLOWED_BACKENDS:
        raise ValueError('unsupported blueprint or model backend')
    if not isinstance(goal, str) or not 4 <= len(goal.strip()) <= MAX_GOAL:
        raise ValueError('goal must contain 4 to 480 characters')
    goal = goal.strip()
    if any(ord(c) < 32 and c not in '\n\t' for c in goal):
        raise ValueError('unsupported control characters')
    if SENSITIVE_RE.search(goal) or DANGEROUS_RE.search(goal):
        raise ValueError('credential or access-control actions are outside this factory')
    return kind, goal, backend


def private_directory(path: Path) -> Path:
    if path.is_symlink():
        raise ValueError('state directory cannot be symlinked')
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == 'posix':
        path.chmod(0o700)
    return path


class Factory:
    def __init__(self, root: Path = ROOT, state: Path = DEFAULT_STATE, *, demo_policy: bool = False,
                 allow_ollama: bool = False, model: str = 'qwen2.5-coder:1.5b') -> None:
        self.root = Path(root).resolve()
        self.state = private_directory(Path(state).expanduser())
        private_directory(self.state / 'artifacts')
        self.db = self.state / 'factory.sqlite3'
        if self.db.is_symlink():
            raise ValueError('database cannot be symlinked')
        self.demo_policy = bool(demo_policy)
        self.allow_ollama = bool(allow_ollama)
        if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,80}', model):
            raise ValueError('unsupported local model name')
        self.model = model
        self.started_at = time.monotonic()
        self._pause = threading.Event()
        self._busy = threading.Lock()
        self._server_running = False
        self._setup()

    def policy(self) -> dict[str, Any]:
        return policy_snapshot(self.root, standalone_demo=self.demo_policy)

    @contextmanager
    def _connect(self):
        c = sqlite3.connect(self.db, timeout=8)
        try:
            c.row_factory = sqlite3.Row
            c.execute('PRAGMA busy_timeout=8000')
            with c:
                yield c
        finally:
            c.close()

    def _setup(self) -> None:
        with self._connect() as c:
            c.executescript('''
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, idempotency TEXT UNIQUE, kind TEXT NOT NULL,
                    goal TEXT NOT NULL, backend TEXT NOT NULL, stage TEXT NOT NULL,
                    progress INTEGER NOT NULL DEFAULT 0, created TEXT NOT NULL,
                    updated TEXT NOT NULL, artifact_sha256 TEXT, error TEXT,
                    review_note TEXT
                );
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT,
                    stage TEXT NOT NULL, detail TEXT NOT NULL, created TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS jobs_stage_time ON jobs(stage, created);
            ''')
        if os.name == 'posix':
            self.db.chmod(0o600)

    def _event(self, c: sqlite3.Connection, job_id: str | None, stage: str, detail: str) -> None:
        c.execute('INSERT INTO events(job_id,stage,detail,created) VALUES (?,?,?,?)',
                  (job_id, stage, detail[:240], utcnow()))

    def submit(self, kind: str, goal: str, backend: str = 'offline', *, idempotency: str | None = None) -> dict[str, Any]:
        kind, goal, backend = validate_goal(kind, goal, backend)
        policy = self.policy()
        if not policy['local_drafts_allowed']:
            raise PermissionError('canonical project policy must be verified before production')
        if backend == 'ollama' and (not self.allow_ollama or not policy['ollama_allowed']):
            raise PermissionError('local model backend not explicitly approved')
        if idempotency is not None and (not isinstance(idempotency, str)
                                       or not re.fullmatch(r'[a-zA-Z0-9_.:-]{1,64}', idempotency)):
            raise ValueError('bad idempotency value')
        with self._connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if idempotency is not None:
                existing = c.execute('SELECT * FROM jobs WHERE idempotency=?', (idempotency,)).fetchone()
                if existing:
                    if (existing['kind'], existing['goal'], existing['backend']) != (kind, goal, backend):
                        raise ValueError('idempotency key conflicts with different job')
                    return dict(existing)
            count = c.execute("SELECT COUNT(*) FROM jobs WHERE stage IN ('QUEUED','PLANNING','BUILDING','VERIFYING','CRITIQUING')").fetchone()[0]
            if count >= MAX_ACTIVE:
                raise ValueError('bounded queue capacity reached')
            if c.execute('SELECT COUNT(*) FROM jobs').fetchone()[0] >= MAX_TOTAL:
                raise ValueError('persistent job history is full; archive externally before adding more')
            job_id, now = uuid.uuid4().hex, utcnow()
            c.execute('INSERT INTO jobs(id,idempotency,kind,goal,backend,stage,progress,created,updated) '
                      'VALUES(?,?,?,?,?,?,?,?,?)', (job_id, idempotency, kind, goal, backend, 'QUEUED', 0, now, now))
            self._event(c, job_id, 'QUEUED', 'Accepted by local bounded factory')
        return self.job(job_id)

    def job(self, job_id: str) -> dict[str, Any]:
        if not isinstance(job_id, str) or not ID_RE.fullmatch(job_id):
            raise ValueError('invalid job identifier')
        with self._connect() as c:
            item = c.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
        if item is None:
            raise KeyError('job not found')
        return dict(item)

    def jobs(self, limit: int = 24) -> list[dict[str, Any]]:
        with self._connect() as c:
            rows = c.execute('SELECT * FROM jobs ORDER BY created DESC, rowid DESC LIMIT ?',
                             (min(48, max(1, limit)),)).fetchall()
        return [dict(x) for x in rows]

    def events(self, since: int = 0) -> list[dict[str, Any]]:
        with self._connect() as c:
            rows = c.execute('SELECT * FROM events WHERE seq>? ORDER BY seq DESC LIMIT ?',
                             (max(0, since), MAX_EVENTS)).fetchall()
        return [dict(x) for x in reversed(rows)]

    def stage(self, job_id: str, stage: str, detail: str, progress: int) -> None:
        with self._connect() as c:
            c.execute('UPDATE jobs SET stage=?,progress=?,updated=? WHERE id=?',
                      (stage, progress, utcnow(), job_id))
            self._event(c, job_id, stage, detail)

    def status(self) -> dict[str, Any]:
        with self._connect() as c:
            rows = c.execute('SELECT stage, COUNT(*) AS n FROM jobs GROUP BY stage').fetchall()
            count = c.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]
        totals = {x['stage']: x['n'] for x in rows}
        return {'name': 'GPT-Doug-Shaggoth Autonomous Factory', 'mode': 'LOCAL_BOUNDED_REVIEW_GATED',
                'backend': 'offline+opt-in-local-ollama' if self.allow_ollama else 'offline',
                'factory_running': self._server_running, 'worker_paused': self._pause.is_set(),
                'uptime_seconds': int(time.monotonic() - self.started_at),
                'policy': self.policy(), 'roles': [{'name': a, 'stage': b, 'description': c} for a, b, c in ROLES],
                'jobs_total': count, 'counts': totals,
                'jobs': self.jobs(), 'events': self.events(),
                'limits': {'active_queue': MAX_ACTIVE, 'workers': 1, 'network_external': False,
                           'exec_generated_code': False, 'automatic_deploy': False,
                           'total_history': MAX_TOTAL},
                'last_updated': utcnow()}

    def pause(self, paused: bool) -> None:
        if paused:
            self._pause.set()
        else:
            self._pause.clear()
        with self._connect() as c:
            self._event(c, None, 'PAUSED' if paused else 'RUNNING',
                        'Operator paused the local factory' if paused else 'Operator resumed the local factory')

    def approve(self, job_id: str, action: str) -> dict[str, Any]:
        if action not in ('approve', 'reject'):
            raise ValueError('review action must be approve or reject')
        if not self.policy()['local_drafts_allowed']:
            raise PermissionError('policy changed; review blocked')
        with self._connect() as c:
            c.execute('BEGIN IMMEDIATE')
            item = c.execute('SELECT stage FROM jobs WHERE id=?', (job_id,)).fetchone()
            if item is None:
                raise KeyError('job not found')
            if item['stage'] != 'AWAITING_REVIEW':
                raise ValueError('only review-ready drafts may be assessed')
            state = 'APPROVED_LOCAL' if action == 'approve' else 'REJECTED'
            c.execute('UPDATE jobs SET stage=?,progress=100,review_note=?,updated=? WHERE id=?',
                      (state, 'Human locally approved draft; no deployment authorized' if action == 'approve'
                       else 'Human rejected draft', utcnow(), job_id))
            self._event(c, job_id, state, 'Human reviewed local artifact only; no external effects')
        return self.job(job_id)

    def seed_demo(self, *, repeat: bool = False) -> list[dict[str, Any]]:
        rows = (
            ('python-scaffold', 'Create an offline data normalization utility for Shaggoth'),
            ('research-brief', 'Map verified software-agent governance research questions'),
            ('test-plan', 'Verify bounded autonomous factory tasks and safety gates'),
        )
        batch = uuid.uuid4().hex[:8] if repeat else 'fixed'
        return [self.submit(kind, goal, idempotency=f'factory-demo-v1-{batch}-{i}')
                for i, (kind, goal) in enumerate(rows)]

    def process_one(self, *, delay: float = 0.0) -> dict[str, Any] | None:
        if self._pause.is_set() or not self._busy.acquire(blocking=False):
            return None
        try:
            with self._connect() as c:
                c.execute('BEGIN IMMEDIATE')
                item = c.execute("SELECT id FROM jobs WHERE stage='QUEUED' ORDER BY created, rowid LIMIT 1").fetchone()
                if item is None:
                    return None
                job_id = item['id']
                c.execute("UPDATE jobs SET stage='PLANNING',progress=12,updated=? WHERE id=?",
                          (utcnow(), job_id))
                self._event(c, job_id, 'PLANNING', 'Planning worker accepted job')
            job = self.job(job_id)
            try:
                policy = self.policy()
                if not policy['local_drafts_allowed']:
                    raise PermissionError('policy changed while job was queued')
                if job['backend'] == 'ollama' and (not self.allow_ollama or not policy['ollama_allowed']):
                    raise PermissionError('local model is not approved')
                plan = make_plan(job)
                if delay:
                    time.sleep(delay)
                self.stage(job_id, 'BUILDING', 'Shaggoth fabricator assembling draft', 36)
                files = create_draft(job, plan, model=self.model)
                if delay:
                    time.sleep(delay)
                self.stage(job_id, 'VERIFYING', 'Pineal syntax and artifact manifest checks', 64)
                findings = verify_files(files, job['kind'])
                if delay:
                    time.sleep(delay)
                self.stage(job_id, 'CRITIQUING', 'Chaos critic checking evidence and limits', 83)
                critique = make_critique(job, findings)
                if delay:
                    time.sleep(delay)
                if not self.policy()['local_drafts_allowed']:
                    raise PermissionError('project policy drifted during production')
                digest = self._write_bundle(job_id, files, plan, findings, critique)
                with self._connect() as c:
                    c.execute('UPDATE jobs SET artifact_sha256=?,stage=?,progress=100,updated=? WHERE id=?',
                              (digest, 'AWAITING_REVIEW', utcnow(), job_id))
                    self._event(c, job_id, 'AWAITING_REVIEW', 'Draft bundle ready for explicit human review')
                return self.job(job_id)
            except Exception as exc:
                # No sensitive exception contents reach JSON/status; preserve class only.
                self.stage(job_id, 'BLOCKED', type(exc).__name__ + ': review inputs and local provider', 100)
                return self.job(job_id)
        finally:
            self._busy.release()

    def _write_bundle(self, job_id: str, files: dict[str, str], plan: dict[str, Any],
                      checks: dict[str, Any], critique: dict[str, Any]) -> str:
        destination = self.state / 'artifacts' / job_id
        if destination.exists():
            raise ValueError('artifact destination already exists')
        destination.mkdir(mode=0o700)
        all_files = {**files, 'plan.json': json.dumps(plan, indent=2, sort_keys=True) + '\n',
                     'verification.json': json.dumps(checks, indent=2, sort_keys=True) + '\n',
                     'review.json': json.dumps(critique, indent=2, sort_keys=True) + '\n'}
        digests = {}
        for name, body in all_files.items():
            if not re.fullmatch(r'[A-Za-z0-9_.-]{1,48}', name):
                raise ValueError('untrusted artifact filename')
            raw = body.encode('utf-8')
            if len(raw) > MAX_DRAFT:
                raise ValueError('artifact too large')
            target = destination / name
            with target.open('xb') as w:
                w.write(raw)
            if os.name == 'posix':
                target.chmod(0o600)
            digests[name] = sha256(raw)
        manifest = {'job_id': job_id, 'files': digests, 'generated': utcnow(),
                    'scope': 'local draft only; needs reviewer approval; no code executed'}
        manifest_raw = canonical(manifest)
        (destination / 'manifest.json').write_bytes(manifest_raw)
        return sha256(manifest_raw)

    def archive(self, job_id: str) -> bytes:
        job = self.job(job_id)
        if not job['artifact_sha256']:
            raise KeyError('artifact not yet ready')
        directory = self.state / 'artifacts' / job_id
        manifest_path = directory / 'manifest.json'
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise ValueError('artifact manifest invalid')
        raw = manifest_path.read_bytes()
        if sha256(raw) != job['artifact_sha256']:
            raise ValueError('manifest hash mismatch')
        manifest = json.loads(raw)
        if manifest['job_id'] != job_id:
            raise ValueError('artifact identity mismatch')
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('manifest.json', raw)
            for name, expected in manifest['files'].items():
                if not re.fullmatch(r'[A-Za-z0-9_.-]{1,48}', name):
                    raise ValueError('invalid artifact path')
                path = directory / name
                if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_DRAFT:
                    raise ValueError('artifact file inaccessible')
                filedata = path.read_bytes()
                if sha256(filedata) != expected:
                    raise ValueError('artifact hash mismatch')
                archive.writestr(name, filedata)
        return output.getvalue()


def make_plan(job: dict[str, Any]) -> dict[str, Any]:
    return {'goal': job['goal'], 'kind': job['kind'], 'backend': job['backend'],
            'workflow': list(STAGES),
            'acceptance': ['Draft is saved locally', 'Python output parses without execution',
                           'Artifacts have exact SHA-256 hashes', 'Human review required'],
            'external_effects': False, 'generated_code_execution': False,
            'source': 'user-supplied task; not a verified factual assertion'}


def safe_identifier(goal: str) -> str:
    words = re.findall(r'[a-z0-9]+', goal.lower())[:5]
    name = '_'.join(words)[:45] or 'new_component'
    if name[0].isdigit():
        name = 'component_' + name
    return name


def offline_draft(job: dict[str, Any]) -> dict[str, str]:
    goal, kind = job['goal'], job['kind']
    if kind == 'python-scaffold':
        identifier = safe_identifier(goal)
        module = ('"""Generated local starter; business logic must be reviewed and implemented."""\n'
                  f'GOAL = {goal!r}\n\n'
                  'def describe() -> dict[str, str]:\n'
                  '    """Return draft metadata; not a completed feature."""\n'
                  '    return {"status": "SCAFFOLD_ONLY", "goal": GOAL}\n')
        tests = ('"""Contract example; do not treat as full task acceptance tests."""\n'
                 'from component import describe\n\n'
                 'def test_scaffold_contract():\n'
                 '    assert describe()["status"] == "SCAFFOLD_ONLY"\n')
        return {'component.py': module, 'test_example.py': tests,
                'README.md': f'# {identifier}\n\n{goal}\n\nOffline starter only. No functional feature is claimed. '
                             'The example test was generated but **not executed**.\n'}
    if kind == 'research-brief':
        return {'RESEARCH.md': '# Research brief (review required)\n\n'
                f'**Research question:** {goal}\n\n'
                '## Evidence collection\n- Identify original authoritative sources\n'
                '- Record dates, provenance and limitations\n'
                '- Seek contradictory evidence and replication\n'
                '- Human review before reporting conclusions\n\n'
                'No research was retrieved; do not treat this template as evidence.\n'}
    return {'test_matrix.json': json.dumps({'objective': goal, 'status': 'UNEXECUTED_TEMPLATE',
            'checks': ['inputs and boundary cases', 'idempotency', 'failure handling',
                       'security policy and approval gate', 'replay and provenance',
                       'bounded resource usage']}, indent=2) + '\n'}


def ollama_draft(job: dict[str, Any], model: str) -> dict[str, str]:
    """Optional *local* model call. Outputs remain untrusted and unexecuted."""
    task = ('Produce a small Python module and one unittest file as JSON only. '
            'JSON keys exactly "module" and "tests"; values Python source strings. '
            'Avoid all filesystem, network, process, credential, shell or dynamic code APIs. '
            'No Markdown fences. State limited requirements in docstrings. Task: ' + job['goal'])
    raw = canonical({'model': model, 'prompt': task, 'stream': False,
                     'options': {'num_predict': 900, 'temperature': 0}})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    req = urllib.request.Request('http://127.0.0.1:11434/api/generate', data=raw,
                                 headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with opener.open(req, timeout=14) as response:
            data = response.read(MAX_DRAFT * 2 + 1)
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
        raise RuntimeError('local model service unavailable') from exc
    if len(data) > MAX_DRAFT * 2:
        raise ValueError('model reply exceeds local cap')
    try:
        top = json.loads(data)
        result = json.loads(top['response'])
        if set(result) != {'module', 'tests'} or not all(isinstance(result[x], str) for x in result):
            raise ValueError('model reply schema is invalid')
    except (ValueError, TypeError, KeyError) as exc:
        raise ValueError('model response must contain source JSON') from exc
    return {'component.py': result['module'], 'test_example.py': result['tests'],
            'README.md': '# Locally generated draft\n\nOnly syntax checked; never executed. Human review required.\n'}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('local model redirects are forbidden')


def create_draft(job: dict[str, Any], plan: dict[str, Any], *, model: str) -> dict[str, str]:
    if job['backend'] == 'ollama':
        if job['kind'] != 'python-scaffold':
            raise ValueError('local code model currently supports python-scaffold only')
        return ollama_draft(job, model)
    return offline_draft(job)


def verify_files(files: dict[str, str], kind: str) -> dict[str, Any]:
    if not 1 <= len(files) <= 4:
        raise ValueError('artifact count outside bound')
    hashes = {}
    python_sources = 0
    for name, content in files.items():
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,48}', name) or not isinstance(content, str):
            raise ValueError('unsafe artifact name or content')
        raw = content.encode('utf-8')
        if not raw or len(raw) > MAX_DRAFT or SENSITIVE_RE.search(content):
            raise ValueError('artifact invalid, oversized or appears to contain a secret')
        hashes[name] = sha256(raw)
        if name.endswith('.py'):
            tree = ast.parse(content, filename=name)
            python_sources += 1
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    for alias in node.names:
                        base = alias.name.split('.')[0]
                        if base in {'os', 'sys', 'subprocess', 'socket', 'ctypes', 'shutil', 'pickle',
                                    'urllib', 'requests', 'importlib', 'builtins', 'pathlib'}:
                            raise ValueError('unsafe import in draft; human handling required')
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {
                    'eval', 'exec', 'compile', '__import__', 'open', 'input'}:
                    raise ValueError('unsafe dynamic or I/O call in draft')
    if kind == 'python-scaffold' and python_sources < 2:
        raise ValueError('Python draft must include module and test source')
    return {'status': 'STATIC_CHECKS_PASSED', 'files': hashes, 'python_files_parsed': python_sources,
            'actual_tests_executed': 0, 'safe_to_execute': False,
            'note': 'AST checks do NOT establish code safety; independent human review required'}


def make_critique(job: dict[str, Any], checks: dict[str, Any]) -> dict[str, Any]:
    return {'verdict': 'DRAFT_ONLY', 'review_required': True,
            'issues': ['Acceptance criteria not independently validated',
                       'Only static checks run; generated code was not executed',
                       'No external sources or factual assertions verified'],
            'backend': job['backend'], 'external_deployment': 'DISABLED',
            'approval_grants': 'local review status only; no shell/cloud access'}


class Worker:
    def __init__(self, factory: Factory, *, delay: float = 0.30):
        self.factory, self.delay = factory, delay
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if self.thread is not None:
            return
        self.thread = threading.Thread(target=self.loop, daemon=True, name='shaggoth-one-worker')
        self.thread.start()

    def loop(self) -> None:
        while not self.stop_event.is_set():
            if self.factory.process_one(delay=self.delay) is None:
                self.stop_event.wait(0.30)

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=3)


class FactoryServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, factory: Factory, port: int = 8772, *, workers: bool = True):
        if not 0 <= port <= 65535:
            raise ValueError('invalid local port')
        self.factory = factory
        self.token = secrets.token_urlsafe(32)
        self.slots = threading.BoundedSemaphore(MAX_SSE_CLIENTS)
        self.worker = Worker(factory)
        super().__init__(('127.0.0.1', port), FactoryHandler)
        factory._server_running = True
        if workers:
            self.worker.start()

    def server_close(self) -> None:
        self.worker.stop()
        self.factory._server_running = False
        super().server_close()


class FactoryHandler(BaseHTTPRequestHandler):
    server: FactoryServer
    protocol_version = 'HTTP/1.1'

    def log_message(self, fmt, *args):
        return  # never print URLs, user task descriptions or tokens

    def _headers(self, code: int, mime: str, length: int | None, *, extra: dict[str, str] | None = None):
        self.send_response(code)
        self.send_header('Content-Type', mime)
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy',
                         "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
                         "img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        if length is not None:
            self.send_header('Content-Length', str(length))
        if extra:
            for key, val in extra.items():
                self.send_header(key, val)
        self.end_headers()

    def _send(self, code: int, payload: bytes, mime='application/json; charset=utf-8', *,
              headers: dict[str, str] | None = None):
        self._headers(code, mime, len(payload), extra=headers)
        self.wfile.write(payload)

    def _json(self, code: int, data: Any):
        self._send(code, canonical(data))

    def _host_ok(self) -> bool:
        host = self.headers.get('Host', '')
        port = self.server.server_port
        return host in {f'127.0.0.1:{port}', f'localhost:{port}'}

    def _origin_ok(self) -> bool:
        origin = self.headers.get('Origin')
        return not origin or origin in {f'http://127.0.0.1:{self.server.server_port}',
                                        f'http://localhost:{self.server.server_port}'}

    def _valid(self) -> bool:
        if not self._host_ok() or not self._origin_ok():
            self._json(403, {'error': 'loopback host/origin required'})
            return False
        return True

    def do_GET(self):
        if not self._valid():
            return
        url = urlsplit(self.path)
        if url.query or url.fragment:
            self._json(404, {'error': 'unexpected URL parameters'})
            return
        path = url.path
        if path == '/':
            html = (UI / 'index.html').read_text(encoding='utf-8').replace('@@CSRF_TOKEN@@', self.server.token)
            self._send(200, html.encode('utf-8'), 'text/html; charset=utf-8')
        elif path in ('/factory.css', '/factory.js'):
            name = path[1:]
            mime = 'text/css; charset=utf-8' if name.endswith('.css') else 'text/javascript; charset=utf-8'
            self._send(200, (UI / name).read_bytes(), mime)
        elif path == '/api/health':
            self._json(200, {'status': 'UP', 'name': 'Shaggoth Factory',
                             'uptime_seconds': self.server.factory.status()['uptime_seconds']})
        elif path == '/api/status':
            self._json(200, self.server.factory.status())
        elif path == '/events':
            self._sse()
        else:
            dl = re.fullmatch(r'/api/jobs/([0-9a-f]{32})/download', path)
            if dl:
                try:
                    data = self.server.factory.archive(dl.group(1))
                    self._send(200, data, 'application/zip', headers={
                        'Content-Disposition': f'attachment; filename="shaggoth-{dl.group(1)[:10]}.zip"'})
                except (KeyError, ValueError, OSError):
                    self._json(404, {'error': 'artifact not available or verification failed'})
            else:
                self._json(404, {'error': 'unknown endpoint'})

    def _sse(self):
        if not self.server.slots.acquire(blocking=False):
            self._json(429, {'error': 'live viewer limit reached'})
            return
        try:
            self._headers(200, 'text/event-stream; charset=utf-8', None,
                          extra={'Connection': 'close', 'X-Accel-Buffering': 'no'})
            for _ in range(35):
                data = canonical(self.server.factory.status())
                self.wfile.write(b'data: ' + data + b'\n\n')
                self.wfile.flush()
                time.sleep(1.5)
        except (OSError, BrokenPipeError, ConnectionResetError):
            pass
        finally:
            self.close_connection = True
            self.server.slots.release()

    def do_POST(self):
        if not self._valid():
            return
        if not secrets.compare_digest(self.headers.get('X-Factory-CSRF', ''), self.server.token):
            self._json(403, {'error': 'local operator token required'})
            return
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            self._json(415, {'error': 'JSON required'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            length = 0
        if not 1 <= length <= MAX_JOB_BYTES:
            self._json(413, {'error': 'request exceeds maximum size or is empty'})
            return
        try:
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('JSON object required')
            url = urlsplit(self.path)
            if url.query or url.fragment:
                raise ValueError('unexpected URL parameters')
            if url.path == '/api/jobs':
                if set(data) - {'kind', 'goal', 'backend', 'idempotency'}:
                    raise ValueError('unexpected job property')
                job = self.server.factory.submit(data.get('kind'), data.get('goal'),
                                                 data.get('backend', 'offline'),
                                                 idempotency=data.get('idempotency'))
                self._json(201, {'job': job})
            elif url.path == '/api/demo':
                if data:
                    raise ValueError('demo endpoint accepts no values')
                self._json(200, {'jobs': self.server.factory.seed_demo(repeat=True)})
            elif url.path == '/api/pause':
                if set(data) != {'paused'} or type(data['paused']) is not bool:
                    raise ValueError('paused must be boolean')
                self.server.factory.pause(data['paused'])
                self._json(200, {'paused': self.server.factory._pause.is_set()})
            else:
                match = re.fullmatch(r'/api/jobs/([0-9a-f]{32})/review', url.path)
                if not match or set(data) != {'action'}:
                    self._json(404, {'error': 'unknown endpoint'})
                    return
                job = self.server.factory.approve(match.group(1), data['action'])
                self._json(200, {'job': job})
        except (ValueError, PermissionError) as exc:
            self._json(400 if isinstance(exc, ValueError) else 403, {'error': str(exc)[:180]})
        except KeyError:
            self._json(404, {'error': 'job not found'})

    def do_PUT(self):
        self._json(405, {'error': 'method not allowed'})

    do_DELETE = do_PUT
    do_PATCH = do_PUT


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', type=Path, default=DEFAULT_STATE)
    parser.add_argument('--demo-policy', action='store_true',
                        help='standalone offline draft demonstration; NOT repository authority')
    parser.add_argument('--allow-ollama', action='store_true',
                        help='operator opt-in to fixed loopback 127.0.0.1:11434 for local drafts')
    parser.add_argument('--model', default='qwen2.5-coder:1.5b')
    subs = parser.add_subparsers(dest='action', required=True)
    srv = subs.add_parser('serve')
    srv.add_argument('--port', type=int, default=8772)
    srv.add_argument('--demo', action='store_true')
    srv.add_argument('--no-browser', action='store_true')
    demo = subs.add_parser('demo')
    subs.add_parser('status')
    sub = subs.add_parser('enqueue')
    sub.add_argument('--kind', choices=ALLOWED_KINDS, required=True)
    sub.add_argument('--goal', required=True)
    sub.add_argument('--backend', choices=ALLOWED_BACKENDS, default='offline')
    sub.add_argument('--idempotency')
    worker = subs.add_parser('work')
    worker.add_argument('--max-jobs', type=int, default=10)
    args = parser.parse_args(argv)
    try:
        f = Factory(ROOT, args.state_dir, demo_policy=args.demo_policy,
                    allow_ollama=args.allow_ollama, model=args.model)
        if args.action == 'status':
            print(json.dumps(f.status(), indent=2, sort_keys=True))
        elif args.action == 'enqueue':
            print(json.dumps(f.submit(args.kind, args.goal, args.backend,
                                      idempotency=args.idempotency), indent=2))
        elif args.action in ('demo', 'work'):
            if args.action == 'demo':
                f.seed_demo()
                count = 6
            else:
                count = max(1, min(48, args.max_jobs))
            processed = []
            for _ in range(count):
                job = f.process_one()
                if job is None:
                    break
                processed.append(job['id'])
            print(json.dumps({'processed': len(processed), 'jobs': f.jobs(),
                              'policy': f.policy(), 'scope': 'local draft only'}, indent=2))
        else:
            if args.demo:
                f.seed_demo()
            server = FactoryServer(f, args.port)
            address = f'http://127.0.0.1:{server.server_port}/'
            print('GPT-DOUG-SHAGGOTH FACTORY // LOCAL ONLY', flush=True)
            print(address, flush=True)
            print('Mode:', f.policy()['state'], '| Ollama:', args.allow_ollama,
                  '| 1 bounded worker; Ctrl+C to stop', flush=True)
            if not args.no_browser:
                webbrowser.open(address)
            try:
                server.serve_forever(poll_interval=0.25)
            finally:
                server.server_close()
    except (ValueError, PermissionError, OSError, sqlite3.Error) as exc:
        print(f'FACTORY ERROR: {type(exc).__name__}: {str(exc)[:160]}', file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print('Factory stopped by local operator', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
