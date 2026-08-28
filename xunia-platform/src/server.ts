import { randomUUID } from 'node:crypto';
import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { OntologyStore } from './ontology.js';
import { AipEngine } from './aip.js';
import { AuthPolicy, RateLimiter, securityHeaders, type Principal, type Role } from './security.js';

const PORT = Number(process.env.XUNIA_PLATFORM_PORT ?? 4400);
const HOST = process.env.XUNIA_PLATFORM_HOST ?? '127.0.0.1';
const PUBLIC = path.resolve(process.cwd(), 'public');
const DATA_DIR = process.env.XUNIA_DATA_DIR?.trim();
const MAX_BODY = Math.max(1_024, Number(process.env.XUNIA_MAX_BODY_BYTES ?? 1_000_000));
const EYE_MOUSE_PATHS = new Set(['/eye-mouse', '/eye-mouse.js', '/eye-mouse.css']);

export const ontology = new OntologyStore(DATA_DIR ? path.join(DATA_DIR, 'ontology.json') : undefined);
ontology.seed();
export const aip = new AipEngine(ontology, undefined, DATA_DIR ? path.join(DATA_DIR, 'aip.json') : undefined);
export const auth = new AuthPolicy();
export const limiter = new RateLimiter();

const metrics = {
  startedAt: Date.now(),
  requests: 0,
  errors: 0,
  aipRuns: 0,
  approvals: 0,
  denied: 0,
  rateLimited: 0
};

const json = (res: ServerResponse, status: number, payload: unknown) => {
  res.statusCode = status;
  res.setHeader('content-type', 'application/json; charset=utf-8');
  res.setHeader('cache-control', 'no-store');
  res.end(JSON.stringify(payload));
};

const text = (res: ServerResponse, status: number, payload: string, type = 'text/plain; charset=utf-8') => {
  res.statusCode = status;
  res.setHeader('content-type', type);
  res.setHeader('cache-control', 'no-store');
  res.end(payload);
};

const body = async (req: IncomingMessage) => {
  const chunks: Buffer[] = [];
  let bytes = 0;
  for await (const chunk of req) {
    const part = Buffer.from(chunk);
    bytes += part.length;
    if (bytes > MAX_BODY) throw new Error('request_too_large');
    chunks.push(part);
  }
  if (!chunks.length) return {};
  return JSON.parse(Buffer.concat(chunks).toString('utf8')) as Record<string, unknown>;
};

const serve = async (res: ServerResponse, file: string, type: string) => {
  try {
    const data = await readFile(path.join(PUBLIC, file));
    res.statusCode = 200;
    res.setHeader('content-type', type);
    res.setHeader('cache-control', 'no-store');
    res.end(data);
  } catch {
    json(res, 404, { ok: false, error: 'not_found' });
  }
};

const clientKey = (req: IncomingMessage) => {
  const forwarded = req.headers['x-forwarded-for'];
  if (process.env.XUNIA_TRUST_PROXY === '1' && typeof forwarded === 'string') return forwarded.split(',')[0].trim();
  return req.socket.remoteAddress ?? 'unknown';
};

const requireRole = (res: ServerResponse, principal: Principal | null, policy: AuthPolicy, role: Role) => {
  if (!principal) {
    metrics.denied += 1;
    json(res, 401, { ok: false, error: 'authentication_required' });
    return false;
  }
  if (!policy.permits(principal, role)) {
    metrics.denied += 1;
    json(res, 403, { ok: false, error: 'forbidden', requiredRole: role });
    return false;
  }
  return true;
};

const isPublicPath = (pathname: string) => [
  '/', '/app.js', '/styles.css', '/auth.css', '/health', '/ready', '/api/session',
  ...EYE_MOUSE_PATHS
].includes(pathname);

function metricsText() {
  const uptime = Math.floor((Date.now() - metrics.startedAt) / 1000);
  return [
    '# TYPE xunia_platform_uptime_seconds gauge',
    `xunia_platform_uptime_seconds ${uptime}`,
    '# TYPE xunia_platform_requests_total counter',
    `xunia_platform_requests_total ${metrics.requests}`,
    '# TYPE xunia_platform_errors_total counter',
    `xunia_platform_errors_total ${metrics.errors}`,
    '# TYPE xunia_platform_aip_runs_total counter',
    `xunia_platform_aip_runs_total ${metrics.aipRuns}`,
    '# TYPE xunia_platform_approvals_total counter',
    `xunia_platform_approvals_total ${metrics.approvals}`,
    '# TYPE xunia_platform_denied_total counter',
    `xunia_platform_denied_total ${metrics.denied}`,
    '# TYPE xunia_platform_rate_limited_total counter',
    `xunia_platform_rate_limited_total ${metrics.rateLimited}`,
    `xunia_platform_ontology_objects ${ontology.snapshot().objects.length}`,
    `xunia_platform_audit_records ${aip.audits.length}`,
    ''
  ].join('\n');
}

export function createPlatformHandler(
  store = ontology,
  engine = aip,
  policy = auth,
  rateLimiter = limiter
) {
  return async (req: IncomingMessage, res: ServerResponse) => {
    const requestId = typeof req.headers['x-request-id'] === 'string' && req.headers['x-request-id'].length <= 100
      ? req.headers['x-request-id']
      : randomUUID();
    metrics.requests += 1;

    try {
      const url = new URL(req.url ?? '/', `http://${req.headers.host ?? 'localhost'}`);
      const eyeMouseRequest = EYE_MOUSE_PATHS.has(url.pathname);
      securityHeaders(res, requestId, policy.corsOrigin, {
        camera: eyeMouseRequest,
        visionAssets: eyeMouseRequest
      });

      if (req.method === 'OPTIONS') {
        res.statusCode = 204;
        return res.end();
      }

      if (!['/health', '/ready'].includes(url.pathname) && !rateLimiter.allow(clientKey(req))) {
        metrics.rateLimited += 1;
        res.setHeader('retry-after', '60');
        return json(res, 429, { ok: false, error: 'rate_limit_exceeded' });
      }

      const principal = policy.authenticate(req);

      if (req.method === 'GET' && url.pathname === '/health') {
        return json(res, 200, {
          ok: true,
          service: 'xunia-platform',
          version: '1.0.0',
          ontologyObjects: store.snapshot().objects.length,
          agents: engine.agents.size,
          tools: engine.tools.list().length,
          uptimeSeconds: Math.floor((Date.now() - metrics.startedAt) / 1000)
        });
      }

      if (req.method === 'GET' && url.pathname === '/ready') {
        const ontologyState = store.persistenceStatus();
        const aipState = engine.persistenceStatus();
        const ready = policy.ready() && ontologyState.ok && aipState.ok;
        return json(res, ready ? 200 : 503, { ok: ready, auth: policy.sanitized(), persistence: { ontology: ontologyState, aip: aipState } });
      }

      if (req.method === 'GET' && url.pathname === '/api/session') {
        return json(res, 200, {
          authRequired: policy.required,
          authenticated: Boolean(principal?.authenticated),
          principal: principal ? { subject: principal.subject, role: principal.role } : null
        });
      }

      if (!isPublicPath(url.pathname) && !principal) {
        metrics.denied += 1;
        return json(res, 401, { ok: false, error: 'authentication_required' });
      }

      if (req.method === 'GET' && url.pathname === '/metrics') {
        if (process.env.XUNIA_METRICS_PUBLIC !== '1' && !requireRole(res, principal, policy, 'viewer')) return;
        return text(res, 200, metricsText(), 'text/plain; version=0.0.4; charset=utf-8');
      }

      if (req.method === 'GET' && url.pathname === '/api/platform/status') {
        if (!requireRole(res, principal, policy, 'viewer')) return;
        return json(res, 200, {
          name: 'XUNIA Platform',
          version: '1.0.0',
          modules: ['ontology', 'datasets', 'aip', 'workflows', 'audit', 'operations'],
          auth: policy.sanitized(),
          persistence: { ontology: store.persistenceStatus(), aip: engine.persistenceStatus() },
          auditIntegrity: engine.verifyAuditChain(),
          integrations: {
            chain: process.env.XUNIA_CHAIN_URL ?? 'http://127.0.0.1:4317',
            sonoxo: process.env.SONOXO_URL ?? 'http://127.0.0.1:3001/api/sonoxo/harvest',
            modelGateway: engine.model.status()
          }
        });
      }

      if (req.method === 'GET' && url.pathname === '/api/ontology') {
        if (!requireRole(res, principal, policy, 'viewer')) return;
        return json(res, 200, store.snapshot());
      }

      if (req.method === 'GET' && url.pathname === '/api/ontology/types') {
        if (!requireRole(res, principal, policy, 'viewer')) return;
        return json(res, 200, { types: store.types() });
      }

      if (req.method === 'GET' && url.pathname === '/api/ontology/search') {
        if (!requireRole(res, principal, policy, 'viewer')) return;
        return json(res, 200, { objects: store.search(url.searchParams.get('q') ?? '', url.searchParams.get('type') ?? undefined) });
      }

      const objectRead = url.pathname.match(/^\/api\/ontology\/objects\/([^/]+)$/);
      if (req.method === 'GET' && objectRead) {
        if (!requireRole(res, principal, policy, 'viewer')) return;
        const object = store.getObject(decodeURIComponent(objectRead[1]));
        return object ? json(res, 200, { object, neighbors: store.neighbors(object.id) }) : json(res, 404, { ok: false, error: 'object_not_found' });
      }

      if (req.method === 'POST' && url.pathname === '/api/ontology/objects') {
        if (!requireRole(res, principal, policy, 'editor')) return;
        const input = await body(req);
        const object = store.upsertObject({
          id: String(input.id ?? ''),
          type: String(input.type ?? ''),
          properties: typeof input.properties === 'object' && input.properties ? input.properties as Record<string, unknown> : {}
        });
        return json(res, 201, { ok: true, object });
      }

      if (req.method === 'POST' && url.pathname === '/api/ontology/links') {
        if (!requireRole(res, principal, policy, 'editor')) return;
        const input = await body(req);
        const link = store.upsertLink({
          id: String(input.id ?? ''),
          type: String(input.type ?? ''),
          from: String(input.from ?? ''),
          to: String(input.to ?? ''),
          properties: typeof input.properties === 'object' && input.properties ? input.properties as Record<string, unknown> : {}
        });
        return json(res, 201, { ok: true, link });
      }

      if (req.method === 'DELETE' && objectRead) {
        if (!requireRole(res, principal, policy, 'editor')) return;
        const deleted = store.deleteObject(decodeURIComponent(objectRead[1]), url.searchParams.get('cascade') === '1');
        return deleted ? json(res, 200, { ok: true }) : json(res, 404, { ok: false, error: 'object_not_found' });
      }

      const linkDelete = url.pathname.match(/^\/api\/ontology\/links\/([^/]+)$/);
      if (req.method === 'DELETE' && linkDelete) {
        if (!requireRole(res, principal, policy, 'editor')) return;
        const deleted = store.deleteLink(decodeURIComponent(linkDelete[1]));
        return deleted ? json(res, 200, { ok: true }) : json(res, 404, { ok: false, error: 'link_not_found' });
      }

      if (req.method === 'GET' && url.pathname === '/api/aip/agents') {
        if (!requireRole(res, principal, policy, 'viewer')) return;
        return json(res, 200, { agents: [...engine.agents.values()] });
      }

      if (req.method === 'POST' && url.pathname === '/api/aip/agents') {
        if (!requireRole(res, principal, policy, 'admin')) return;
        const input = await body(req);
        const agent = engine.registerAgent({
          id: String(input.id ?? ''),
          name: String(input.name ?? ''),
          system: String(input.system ?? ''),
          tools: Array.isArray(input.tools) ? input.tools.map(String) : [],
          approvalFor: Array.isArray(input.approvalFor) ? input.approvalFor.map(String) as ('low'|'medium'|'high')[] : ['medium', 'high']
        });
        return json(res, 201, { ok: true, agent });
      }

      if (req.method === 'GET' && url.pathname === '/api/aip/tools') {
        if (!requireRole(res, principal, policy, 'viewer')) return;
        return json(res, 200, { tools: engine.tools.list() });
      }

      if (req.method === 'GET' && url.pathname === '/api/aip/audit') {
        if (!requireRole(res, principal, policy, 'viewer')) return;
        return json(res, 200, { records: engine.audits.slice(-500).reverse(), integrity: engine.verifyAuditChain() });
      }

      if (req.method === 'GET' && url.pathname === '/api/aip/audit/verify') {
        if (!requireRole(res, principal, policy, 'viewer')) return;
        return json(res, 200, engine.verifyAuditChain());
      }

      if (req.method === 'GET' && url.pathname === '/api/aip/runs') {
        if (!requireRole(res, principal, policy, 'viewer')) return;
        return json(res, 200, { runs: engine.listRuns(Number(url.searchParams.get('limit') ?? 100)) });
      }

      const runRead = url.pathname.match(/^\/api\/aip\/runs\/([^/]+)$/);
      if (req.method === 'GET' && runRead) {
        if (!requireRole(res, principal, policy, 'viewer')) return;
        const run = engine.getRun(decodeURIComponent(runRead[1]));
        return run ? json(res, 200, { run }) : json(res, 404, { ok: false, error: 'run_not_found' });
      }

      if (req.method === 'POST' && url.pathname === '/api/aip/run') {
        if (!requireRole(res, principal, policy, 'operator')) return;
        const input = await body(req);
        const contextIds = Array.isArray(input.contextIds) ? input.contextIds.map(String) : [];
        const run = await engine.run(String(input.agentId ?? 'xunia-analyst'), String(input.message ?? ''), contextIds, principal!.subject);
        metrics.aipRuns += 1;
        return json(res, 201, { ok: true, run });
      }

      const approve = url.pathname.match(/^\/api\/aip\/runs\/([^/]+)\/approve\/([^/]+)$/);
      if (req.method === 'POST' && approve) {
        if (!requireRole(res, principal, policy, 'admin')) return;
        const run = await engine.approve(decodeURIComponent(approve[1]), decodeURIComponent(approve[2]), principal!.subject);
        metrics.approvals += 1;
        return json(res, 200, { ok: true, run });
      }

      if (req.method === 'GET' && url.pathname === '/') return serve(res, 'index.html', 'text/html; charset=utf-8');
      if (req.method === 'GET' && url.pathname === '/app.js') return serve(res, 'app.js', 'text/javascript; charset=utf-8');
      if (req.method === 'GET' && url.pathname === '/styles.css') return serve(res, 'styles.css', 'text/css; charset=utf-8');
      if (req.method === 'GET' && url.pathname === '/auth.css') return serve(res, 'auth.css', 'text/css; charset=utf-8');
      if (req.method === 'GET' && url.pathname === '/eye-mouse') return serve(res, 'eye-mouse.html', 'text/html; charset=utf-8');
      if (req.method === 'GET' && url.pathname === '/eye-mouse.js') return serve(res, 'eye-mouse.js', 'text/javascript; charset=utf-8');
      if (req.method === 'GET' && url.pathname === '/eye-mouse.css') return serve(res, 'eye-mouse.css', 'text/css; charset=utf-8');

      return json(res, 404, { ok: false, error: 'not_found' });
    } catch (error) {
      metrics.errors += 1;
      const message = error instanceof Error ? error.message : 'request_failed';
      if (message === 'request_too_large') return json(res, 413, { ok: false, error: message });
      if (error instanceof SyntaxError) return json(res, 400, { ok: false, error: 'invalid_json' });
      return json(res, 400, { ok: false, error: message });
    }
  };
}

export const handler = createPlatformHandler();

if (process.argv[1] && import.meta.url === new URL(`file://${process.argv[1]}`).href) {
  const server = createServer((req, res) => void handler(req, res));
  server.requestTimeout = 30_000;
  server.headersTimeout = 15_000;
  server.keepAliveTimeout = 5_000;
  server.maxRequestsPerSocket = 1_000;
  server.listen(PORT, HOST, () => console.log(`[xunia-platform] ready http://${HOST}:${PORT} auth=${auth.required ? 'required' : 'dev-open'} persistence=${DATA_DIR ? 'file' : 'memory'}`));

  let stopping = false;
  const shutdown = (signal: string) => {
    if (stopping) return;
    stopping = true;
    console.log(`[xunia-platform] ${signal}; draining`);
    server.close(() => process.exit(0));
    setTimeout(() => process.exit(1), 10_000).unref();
  };
  process.once('SIGTERM', () => shutdown('SIGTERM'));
  process.once('SIGINT', () => shutdown('SIGINT'));
}
