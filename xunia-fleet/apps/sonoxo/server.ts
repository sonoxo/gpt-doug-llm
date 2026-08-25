import { createServer, IncomingMessage, ServerResponse } from 'node:http';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { TelemetryStore, type HarvestEvent } from './store.js';

const PORT = Number(process.env.PORT ?? 3001);
const DB_PATH = process.env.SONOXO_DB_PATH ?? resolve(process.cwd(), 'database.sql');
const HARVEST_LOG = process.env.SONOXO_HARVEST_LOG ?? resolve(process.cwd(), '.xray/harvest/sonoxo.json');

const redact = (value: unknown): unknown => {
  const secretKeys = /token|secret|password|authorization|api[-_]?key/i;
  if (Array.isArray(value)) return value.map(redact);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value as Record<string, unknown>).map(([key, item]) => [key, secretKeys.test(key) ? '[REDACTED]' : redact(item)]));
  }
  return value;
};

const writeSummary = (summary: Record<string, unknown>) => {
  mkdirSync(resolve(HARVEST_LOG, '..'), { recursive: true });
  writeFileSync(HARVEST_LOG, `${JSON.stringify(redact(summary), null, 2)}\n`, 'utf8');
};

const readJson = async (req: IncomingMessage): Promise<unknown> => {
  const chunks: Buffer[] = [];
  for await (const chunk of req) chunks.push(Buffer.from(chunk));
  if (chunks.length === 0) return {};
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
};

const sendJson = (res: ServerResponse, status: number, body: unknown) => {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' });
  res.end(JSON.stringify(body));
};

export function createSonoxoServer(options: { dbPath?: string; harvestLog?: string } = {}) {
  const dbPath = options.dbPath ?? DB_PATH;
  const harvestLog = options.harvestLog ?? HARVEST_LOG;
  const store = new TelemetryStore(dbPath);

  const server = createServer(async (req, res) => {
    if (req.url !== '/api/sonoxo/harvest') {
      return sendJson(res, 404, { ok: false, error: 'not_found' });
    }

    if (req.method === 'GET') {
      return sendJson(res, 200, { ok: true, service: 'sonoxo', environment: 'dev', region: 'virginia-local', events: store.count() });
    }

    if (req.method !== 'POST') {
      res.setHeader('allow', 'GET, POST');
      return sendJson(res, 405, { ok: false, error: 'method_not_allowed' });
    }

    try {
      const body = await readJson(req) as Partial<HarvestEvent>;
      if (!body || typeof body.type !== 'string' || body.type.trim() === '') {
        return sendJson(res, 400, { ok: false, error: 'event_type_required' });
      }
      const event: HarvestEvent = { ...body, type: body.type.trim() };
      const receipt = store.ingest(event);
      const summary = {
        application: 'sonoxo',
        namespace: 'sonoxo',
        accepted: 1,
        totalEvents: store.count(),
        event: redact(event),
        receipt,
        updatedAt: new Date().toISOString(),
      };
      mkdirSync(resolve(harvestLog, '..'), { recursive: true });
      writeFileSync(harvestLog, `${JSON.stringify(summary, null, 2)}\n`, 'utf8');
      return sendJson(res, 202, { ok: true, ...receipt });
    } catch (error) {
      return sendJson(res, 400, { ok: false, error: 'invalid_json', detail: error instanceof Error ? error.message : 'unknown' });
    }
  });

  const close = () => new Promise<void>((resolveClose) => server.close(() => { store.close(); resolveClose(); }));
  return { server, store, close };
}

const isDirectExecution = Boolean(process.argv[1]) && import.meta.url === pathToFileURL(process.argv[1]).href;

if (isDirectExecution) {
  const app = createSonoxoServer();
  app.server.listen(PORT, '127.0.0.1', () => {
    writeSummary({ application: 'sonoxo', status: 'READY', port: PORT, pid: process.pid, startedAt: new Date().toISOString() });
    console.log(`[sonoxo] READY http://127.0.0.1:${PORT}/api/sonoxo/harvest`);
  });

  let stopping = false;
  const shutdown = async (signal: NodeJS.Signals) => {
    if (stopping) return;
    stopping = true;
    console.log(`[sonoxo] ${signal} received; draining`);
    await app.close();
    process.exitCode = 0;
  };
  process.once('SIGTERM', () => void shutdown('SIGTERM'));
  process.once('SIGINT', () => void shutdown('SIGINT'));
}
