"""GPT-Doug-Chaos live local-only Rubik-style access-rule dashboard.

Standard-library read-only observability: real process uptime, connected SSE
clients, repository *source presence*, and locally validated governance policy.
A policy visualization is not an authorization mechanism and grants no access.
No remote probes, provider tokens, agent starts or external effects.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = Path(__file__).with_name('live_cube_ui')
POLICY_REL = 'safety-shield/ontology/universal-galactic-federation-guardrails-v1.json'
MAX_POLICY_BYTES = 128 * 1024
SSE_INTERVAL_SECONDS = 2.0
SSE_MAX_SECONDS = 70
MAX_SSE_CLIENTS = 8
MODULES = (
    ('GPT-DOUG', 'CORE REASONING', 'gpt_brain/kernel.py'),
    ('GPT-PINEAL', 'PROVENANCE & MEMORY', 'integrations/gpt-doug-pineal/src/pineal/store.py'),
    ('GPT-SHAGGOTH', 'DEFENSIVE POLICY', 'gpt_zyra_shaggoth/bridge.py'),
    ('GPT-CHAOS', 'SIMULATION CONTROL', 'gpt_chaos/runtime.py'),
    ('GPT-REDPANDA', 'LOCAL SUPERVISOR', 'redpanda-desktop/gpt_redpanda_llm.py'),
    ('BIO-GPT', 'EXACT MATH MODEL', 'research_lab/bio_gpt.py'),
    ('CURE SWARM', 'EVIDENCE RESEARCH', 'research_lab/cure_swarm.py'),
)
GUARDRAIL_EXPECTED = {
    'humanApprovalForContainment': True,
    'humanApprovalForConsequentialExternalAction': True,
    'externalThirdPartyAction': False,
    'destructiveAction': False,
    'credentialAcquisition': False,
    'targetExploitation': False,
    'uncontrolledAgentReplication': False,
    'autonomousFundsTransfer': False,
    'memoryRequiresProvenance': True,
}


def _within_repo(root: Path, relative: str) -> bool:
    """Find source files only within the configured root; do not follow symlinks."""
    path = root
    for part in Path(relative).parts:
        path = path / part
        if path.is_symlink():
            return False
    return path.is_file()


def read_policy(root: Path) -> dict[str, Any]:
    relative = POLICY_REL
    if not _within_repo(root, relative):
        return {'state': 'UNVERIFIED', 'reason': 'governance source missing or linked',
                'controls_checked': 0, 'controls_total': len(GUARDRAIL_EXPECTED), 'fingerprint': None}
    path = root / relative
    try:
        if path.stat().st_size > MAX_POLICY_BYTES:
            raise ValueError('oversized governance source')
        raw = path.read_bytes()
        policy = json.loads(raw)
        if not isinstance(policy, dict):
            raise ValueError('not an object')
        controls = policy.get('guardrails')
        if not isinstance(controls, dict):
            raise ValueError('missing rules')
        matching = sum(controls.get(k) is v for k, v in GUARDRAIL_EXPECTED.items())
        valid = (policy.get('status') == 'ACTIVE'
                 and policy.get('mode') == 'DEFENSIVE_AUTHORIZED_ENVIRONMENTS_ONLY'
                 and matching == len(GUARDRAIL_EXPECTED))
        return {'state': 'MATCHED' if valid else 'REVIEW_REQUIRED',
                'reason': 'sampled governance checks satisfied' if valid else 'policy drift or incomplete rules',
                'controls_checked': matching, 'controls_total': len(GUARDRAIL_EXPECTED),
                'fingerprint': hashlib.sha256(raw).hexdigest()[:12]}
    except (OSError, UnicodeError, ValueError, TypeError):
        return {'state': 'UNVERIFIED', 'reason': 'cannot validate governance source',
                'controls_checked': 0, 'controls_total': len(GUARDRAIL_EXPECTED), 'fingerprint': None}


class LiveMonitor:
    def __init__(self, root: Path = ROOT) -> None:
        self.root = Path(root).resolve()
        self.boot_mono = time.monotonic()
        self._lock = threading.Lock()
        self._snapshots = 0
        self._requests = 0
        self._clients = 0
        self._slots = threading.BoundedSemaphore(MAX_SSE_CLIENTS)

    def request(self) -> None:
        with self._lock:
            self._requests += 1

    def admit_client(self) -> bool:
        if not self._slots.acquire(blocking=False):
            return False
        with self._lock:
            self._clients += 1
        return True

    def leave_client(self) -> None:
        with self._lock:
            self._clients -= 1
        self._slots.release()

    def snapshot(self) -> dict[str, Any]:
        policy = read_policy(self.root)
        sources = []
        for name, role, relative in MODULES:
            present = _within_repo(self.root, relative)
            sources.append({'name': name, 'role': role,
                            'source_state': 'PRESENT' if present else 'NOT_FOUND',
                            'runtime_state': 'NOT_VERIFIED',
                            'note': 'Source available; not proof of a running agent' if present
                                    else 'Module source was not found in this checkout'})
        with self._lock:
            self._snapshots += 1
            requests = self._requests
            clients = self._clients
            sequence = self._snapshots
        policy_ok = policy['state'] == 'MATCHED'
        axes = (
            {'id': 'identity', 'name': 'IDENTITY', 'state': 'LIMITED', 'detail': 'Bound to loopback only; no authenticated operator identity'},
            {'id': 'scope', 'name': 'SCOPE', 'state': 'ENFORCED', 'detail': 'Read-only GET/HEAD diagnostics; no execution endpoint'},
            {'id': 'consent', 'name': 'CONSENT', 'state': 'REVIEW', 'detail': 'Consequential actions require separate explicit human approval'},
            {'id': 'policy', 'name': 'POLICY', 'state': 'ENFORCED' if policy_ok else 'UNVERIFIED',
             'detail': 'Sample of project governance rules matches expected values' if policy_ok
                       else 'Local governance cannot be attested; fail closed'},
            {'id': 'resources', 'name': 'RESOURCES', 'state': 'ENFORCED', 'detail': 'No API tokens, cloud deployment, or outbound network connections'},
            {'id': 'audit', 'name': 'AUDIT', 'state': 'LIMITED', 'detail': 'Volatile in-memory counters only; no durable attestation'},
        )
        return {
            'name': 'GPT-DOUG-CHAOS', 'mode': 'LIVE_LOCAL_READ_ONLY',
            'timestamp_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'sequence': sequence, 'uptime_seconds': int(time.monotonic() - self.boot_mono),
            'http_requests': requests, 'connected_viewers': clients,
            'policy': policy, 'access_cube': list(axes),
            'modules': sources,
            'counts': {'source_present': sum(m['source_state'] == 'PRESENT' for m in sources),
                       'source_total': len(sources), 'running_agents_verified': 0,
                       'rules_enforced': sum(a['state'] == 'ENFORCED' for a in axes)},
            'security_boundary': {'local_only': True, 'read_only': True, 'network_outbound': False,
                                  'credential_access': False, 'external_actions': False,
                                  'authorization_by_cube_rotation': False},
            'disclaimer': 'This dashboard measures its own process and local files only; source-present is not running',
        }


class LoopbackServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, port: int, monitor: LiveMonitor) -> None:
        if not isinstance(port, int) or not 0 <= port <= 65535:
            raise ValueError('invalid port')
        super().__init__(('127.0.0.1', port), DashboardHandler)
        self.monitor = monitor


class DashboardHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'GPT-Doug-Chaos/1.0'
    sys_version = ''

    def log_message(self, format: str, *args: object) -> None:
        # Standard stdout access logs may contain query strings: avoid logging them.
        return

    def _headers(self, status: int, content_type: str, length: int | None = None) -> None:
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy',
                         "default-src 'none'; script-src 'self'; style-src 'self'; "
                         "connect-src 'self'; img-src 'self'; frame-ancestors 'none'; "
                         "base-uri 'none'; form-action 'none'")
        if length is not None:
            self.send_header('Content-Length', str(length))
        self.end_headers()

    def _write(self, code: int, data: bytes, typ: str, head_only: bool = False) -> None:
        self._headers(code, typ, len(data))
        if not head_only:
            self.wfile.write(data)

    def _safe_headers(self) -> bool:
        host = self.headers.get('Host', '')
        port = self.server.server_port
        if host not in (f'127.0.0.1:{port}', f'localhost:{port}'):
            return False
        origin = self.headers.get('Origin')
        if origin and origin not in (f'http://127.0.0.1:{port}', f'http://localhost:{port}'):
            return False
        return True

    def do_POST(self) -> None:
        self.server.monitor.request()
        self._write(405, b'Method Not Allowed', 'text/plain; charset=utf-8')

    def do_PUT(self) -> None:
        self.do_POST()

    def do_DELETE(self) -> None:
        self.do_POST()

    def do_HEAD(self) -> None:
        self._get(head_only=True)

    def do_GET(self) -> None:
        self._get(head_only=False)

    def _get(self, head_only: bool) -> None:
        self.server.monitor.request()
        if not self._safe_headers():
            self._write(403, b'Forbidden', 'text/plain; charset=utf-8', head_only)
            return
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.query or parsed.fragment:
            self._write(404, b'Not found', 'text/plain; charset=utf-8', head_only)
            return
        path = parsed.path
        files = {'/': ('index.html', 'text/html; charset=utf-8'),
                 '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                 '/styles.css': ('styles.css', 'text/css; charset=utf-8')}
        if path in files:
            filename, typ = files[path]
            try:
                data = (ASSET_DIR / filename).read_bytes()
            except OSError:
                self._write(503, b'Assets unavailable', 'text/plain; charset=utf-8', head_only)
                return
            self._write(200, data, typ, head_only)
        elif path in ('/api/status', '/api/health'):
            status = self.server.monitor.snapshot() if path == '/api/status' else {
                'name': 'GPT-DOUG-CHAOS', 'status': 'LOCAL_SERVER_RUNNING'}
            self._write(200, json.dumps(status, separators=(',', ':')).encode('utf-8'),
                        'application/json; charset=utf-8', head_only)
        elif path == '/events' and not head_only:
            self._stream()
        else:
            self._write(404, b'Not found', 'text/plain; charset=utf-8', head_only)

    def _stream(self) -> None:
        monitor = self.server.monitor
        if not monitor.admit_client():
            self._write(503, b'Too many live viewers', 'text/plain; charset=utf-8')
            return
        try:
            self._headers(200, 'text/event-stream; charset=utf-8')
            started = time.monotonic()
            while time.monotonic() - started < SSE_MAX_SECONDS:
                payload = json.dumps(monitor.snapshot(), separators=(',', ':'), ensure_ascii=True)
                frame = f'event: snapshot\ndata: {payload}\n\n'.encode('ascii')
                self.wfile.write(frame)
                self.wfile.flush()
                time.sleep(SSE_INTERVAL_SECONDS)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError, OSError):
            pass
        finally:
            monitor.leave_client()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command')
    serve = sub.add_parser('serve', help='start local real-time browser dashboard')
    serve.add_argument('--port', type=int, default=8767)
    serve.add_argument('--no-browser', action='store_true', help='print URL without opening browser')
    sub.add_parser('snapshot', help='print one actual local source/policy snapshot')
    args = parser.parse_args(argv)
    if args.command == 'snapshot':
        print(json.dumps(LiveMonitor(ROOT).snapshot(), indent=2))
        return 0
    if args.command not in (None, 'serve'):
        parser.print_help()
        return 2
    try:
        port = args.port if args.command == 'serve' else 8767
        monitor = LiveMonitor(ROOT)
        server = LoopbackServer(port, monitor)
    except (OSError, ValueError) as exc:
        print(f'GPT-DOUG-CHAOS startup failed: {type(exc).__name__}', flush=True)
        return 2
    url = f'http://127.0.0.1:{server.server_port}/'
    print('GPT-DOUG-CHAOS | Live Access Cube')
    print('Dashboard:', url)
    print('Actual agent runtimes are not started; sources are inspected read-only.')
    print('Use Ctrl+C to stop the dashboard.', flush=True)
    if not (args.command == 'serve' and args.no_browser):
        opened = False
        try:
            opened = bool(webbrowser.open_new_tab(url))
        except (OSError, RuntimeError):
            pass
        if not opened and sys.platform == 'darwin':
            # macOS fallback when Python's browser registry has no default.
            try:
                subprocess.Popen(['open', url], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, start_new_session=True)
            except OSError:
                print('Open the dashboard URL in your browser manually.', flush=True)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print('\nGPT-DOUG-CHAOS stopped.')
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
