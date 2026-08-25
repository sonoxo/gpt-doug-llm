import { createServer } from 'node:http';
import { XuniaChain } from './chain.js';
import { formatXun } from './crypto.js';

const PORT = Number(process.env.XUNIA_PORT ?? 4317);
const DATA = process.env.XUNIA_DATA ?? '.xunia/chain.json';
const SONOXO_URL = process.env.SONOXO_URL ?? 'http://127.0.0.1:3001/api/sonoxo/harvest';
const chain = new XuniaChain(DATA);

const telemetry = async (type: string, payload: unknown) => {
  if (process.env.SONOXO_TELEMETRY !== '1') return;
  try {
    await fetch(SONOXO_URL, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ type, payload }) });
  } catch { /* telemetry must never stop consensus */ }
};

const readJson = async (req: import('node:http').IncomingMessage) => {
  const chunks: Buffer[] = [];
  for await (const chunk of req) chunks.push(Buffer.from(chunk));
  return chunks.length ? JSON.parse(Buffer.concat(chunks).toString('utf8')) : {};
};

const send = (res: import('node:http').ServerResponse, status: number, body: unknown) => {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' });
  res.end(JSON.stringify(body));
};

const server = createServer(async (req, res) => {
  try {
    const url = new URL(req.url ?? '/', `http://${req.headers.host ?? 'localhost'}`);
    if (req.method === 'GET' && url.pathname === '/health') return send(res, 200, { ok: true, chainId: chain.chainId, height: chain.tip().height, mempool: chain.mempool.length });
    if (req.method === 'GET' && url.pathname === '/chain') return send(res, 200, { chainId: chain.chainId, blocks: chain.blocks });
    if (req.method === 'GET' && url.pathname.startsWith('/balance/')) {
      const address = decodeURIComponent(url.pathname.slice('/balance/'.length));
      const sats = chain.balance(address);
      return send(res, 200, { address, atomic: sats.toString(), xun: formatXun(sats), nonce: chain.nonce(address) });
    }
    if (req.method === 'POST' && url.pathname === '/tx') {
      const tx = await readJson(req);
      const id = chain.submit(tx);
      void telemetry('xunia.tx.accepted', { id, height: chain.tip().height });
      return send(res, 202, { ok: true, id });
    }
    if (req.method === 'POST' && url.pathname === '/mine') {
      const body = await readJson(req) as { miner?: string; difficulty?: number };
      if (!body.miner) return send(res, 400, { ok: false, error: 'miner_required' });
      const block = chain.mine(body.miner, body.difficulty);
      void telemetry('xunia.block.mined', { height: block.height, hash: block.hash, txs: block.transactions.length });
      return send(res, 201, { ok: true, block });
    }
    if (req.method === 'GET' && url.pathname === '/') {
      res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
      return res.end(`<!doctype html><meta charset="utf-8"><title>XUNIA Chain</title><style>body{font-family:system-ui;background:#0b0d10;color:#eef;max-width:900px;margin:48px auto;padding:20px}code{background:#191d24;padding:2px 6px;border-radius:6px}</style><h1>XUNIA Chain</h1><p>Native coin: <b>XUN</b></p><p>Chain: <code>${chain.chainId}</code></p><p>Height: <b>${chain.tip().height}</b></p><p>Mempool: <b>${chain.mempool.length}</b></p><p>API: <code>/health</code> <code>/chain</code> <code>/balance/:address</code> <code>POST /tx</code> <code>POST /mine</code></p>`);
    }
    return send(res, 404, { ok: false, error: 'not_found' });
  } catch (error) {
    return send(res, 400, { ok: false, error: error instanceof Error ? error.message : 'request_failed' });
  }
});

server.listen(PORT, '127.0.0.1', () => console.log(`[xunia] node ready http://127.0.0.1:${PORT}`));

let stopping = false;
const shutdown = (signal: string) => {
  if (stopping) return;
  stopping = true;
  console.log(`[xunia] ${signal}; shutting down`);
  server.close(() => process.exit(0));
};
process.once('SIGTERM', () => shutdown('SIGTERM'));
process.once('SIGINT', () => shutdown('SIGINT'));
