import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { OntologyStore } from './ontology.js';
import { AipEngine } from './aip.js';

const PORT = Number(process.env.XUNIA_PLATFORM_PORT ?? 4400);
const HOST = process.env.XUNIA_PLATFORM_HOST ?? '127.0.0.1';
const PUBLIC = path.resolve(process.cwd(), 'public');

export const ontology = new OntologyStore();
ontology.seed();
export const aip = new AipEngine(ontology);

const json = (res: ServerResponse, status: number, body: unknown) => {
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'cache-control': 'no-store',
    'x-content-type-options': 'nosniff'
  });
  res.end(JSON.stringify(body));
};

const body = async (req: IncomingMessage) => {
  const chunks: Buffer[] = [];
  let bytes = 0;
  for await (const chunk of req) {
    const part = Buffer.from(chunk);
    bytes += part.length;
    if (bytes > 1_000_000) throw new Error('request_too_large');
    chunks.push(part);
  }
  if (!chunks.length) return {};
  return JSON.parse(Buffer.concat(chunks).toString('utf8')) as Record<string, unknown>;
};

const serve = async (res: ServerResponse, file: string, type: string) => {
  try {
    const data = await readFile(path.join(PUBLIC, file));
    res.writeHead(200, { 'content-type': type, 'cache-control': 'no-store' });
    res.end(data);
  } catch {
    json(res, 404, { ok: false, error: 'not_found' });
  }
};

export const handler = async (req: IncomingMessage, res: ServerResponse) => {
  try {
    const url = new URL(req.url ?? '/', `http://${req.headers.host ?? 'localhost'}`);

    if (req.method === 'GET' && url.pathname === '/health') {
      return json(res, 200, {
        ok: true,
        service: 'xunia-platform',
        ontologyObjects: ontology.snapshot().objects.length,
        agents: aip.agents.size,
        tools: aip.tools.list().length
      });
    }

    if (req.method === 'GET' && url.pathname === '/api/platform/status') {
      return json(res, 200, {
        name: 'XUNIA Platform',
        version: '0.1.0',
        modules: ['ontology', 'datasets', 'aip', 'workflows', 'audit', 'operations'],
        integrations: {
          chain: process.env.XUNIA_CHAIN_URL ?? 'http://127.0.0.1:4317',
          sonoxo: process.env.SONOXO_URL ?? 'http://127.0.0.1:3001/api/sonoxo/harvest',
          modelGateway: process.env.XUNIA_MODEL_URL ? 'configured' : 'local-fallback'
        }
      });
    }

    if (req.method === 'GET' && url.pathname === '/api/ontology') {
      return json(res, 200, ontology.snapshot());
    }

    if (req.method === 'GET' && url.pathname === '/api/ontology/search') {
      return json(res, 200, {
        objects: ontology.search(url.searchParams.get('q') ?? '', url.searchParams.get('type') ?? undefined)
      });
    }

    if (req.method === 'POST' && url.pathname === '/api/ontology/objects') {
      const input = await body(req);
      const object = ontology.upsertObject({
        id: String(input.id ?? ''),
        type: String(input.type ?? ''),
        properties: typeof input.properties === 'object' && input.properties ? input.properties as Record<string, unknown> : {}
      });
      return json(res, 201, { ok: true, object });
    }

    if (req.method === 'POST' && url.pathname === '/api/ontology/links') {
      const input = await body(req);
      const link = ontology.upsertLink({
        id: String(input.id ?? ''),
        type: String(input.type ?? ''),
        from: String(input.from ?? ''),
        to: String(input.to ?? ''),
        properties: typeof input.properties === 'object' && input.properties ? input.properties as Record<string, unknown> : {}
      });
      return json(res, 201, { ok: true, link });
    }

    if (req.method === 'GET' && url.pathname === '/api/aip/agents') {
      return json(res, 200, { agents: [...aip.agents.values()] });
    }

    if (req.method === 'GET' && url.pathname === '/api/aip/tools') {
      return json(res, 200, { tools: aip.tools.list() });
    }

    if (req.method === 'GET' && url.pathname === '/api/aip/audit') {
      return json(res, 200, { records: aip.audits.slice(-500).reverse() });
    }

    if (req.method === 'POST' && url.pathname === '/api/aip/run') {
      const input = await body(req);
      const contextIds = Array.isArray(input.contextIds) ? input.contextIds.map(String) : [];
      const run = await aip.run(String(input.agentId ?? 'xunia-analyst'), String(input.message ?? ''), contextIds);
      return json(res, 201, { ok: true, run });
    }

    const approve = url.pathname.match(/^\/api\/aip\/runs\/([^/]+)\/approve\/([^/]+)$/);
    if (req.method === 'POST' && approve) {
      const run = await aip.approve(decodeURIComponent(approve[1]), decodeURIComponent(approve[2]));
      return json(res, 200, { ok: true, run });
    }

    if (req.method === 'GET' && url.pathname === '/') return serve(res, 'index.html', 'text/html; charset=utf-8');
    if (req.method === 'GET' && url.pathname === '/app.js') return serve(res, 'app.js', 'text/javascript; charset=utf-8');
    if (req.method === 'GET' && url.pathname === '/styles.css') return serve(res, 'styles.css', 'text/css; charset=utf-8');

    return json(res, 404, { ok: false, error: 'not_found' });
  } catch (error) {
    return json(res, 400, { ok: false, error: error instanceof Error ? error.message : 'request_failed' });
  }
};

if (process.argv[1] && import.meta.url === new URL(`file://${process.argv[1]}`).href) {
  const server = createServer((req, res) => void handler(req, res));
  server.listen(PORT, HOST, () => console.log(`[xunia-platform] ready http://${HOST}:${PORT}`));
  let stopping = false;
  const shutdown = (signal: string) => {
    if (stopping) return;
    stopping = true;
    console.log(`[xunia-platform] ${signal}; shutting down`);
    server.close(() => process.exit(0));
  };
  process.once('SIGTERM', () => shutdown('SIGTERM'));
  process.once('SIGINT', () => shutdown('SIGINT'));
}
