const http = require("http");
const os = require("os");
const { Worker } = require("worker_threads");

const PORT = Number(process.env.PORT || 10000);
const MAX_WORKERS = Math.min(Math.max(Number(process.env.GPTDOUG_MAX_WORKERS || 8), 1), 64);
const VIRTUAL_END = "999999999999999";
const AUTHORITY = "HUMAN_FIRST";

let state = {
  activeWorkers: 0,
  completedTasks: 0,
  queuedTasks: 0,
  lastRunAt: null,
};

function lightforceState() {
  const active = Number(state.activeWorkers || 0);
  const queued = Number(state.queuedTasks || 0);
  if (queued > MAX_WORKERS * 8) return "CRITICAL";
  const ratio = MAX_WORKERS ? active / MAX_WORKERS : 0;
  if (ratio >= 0.85) return "HOT";
  if (ratio >= 0.50) return "WARM";
  if (ratio > 0) return "COOL";
  return "COLD";
}

function telemetry() {
  const totalMem = os.totalmem();
  const freeMem = os.freemem();
  return {
    uptime_seconds: Math.round(process.uptime()),
    host_cpus: os.cpus().length,
    load_average: os.loadavg().map(v => Number(v.toFixed(2))),
    memory: {
      total_mb: Math.round(totalMem / 1048576),
      free_mb: Math.round(freeMem / 1048576),
      used_percent: totalMem ? Number((((totalMem - freeMem) / totalMem) * 100).toFixed(1)) : 0
    },
    worker_utilization_percent: MAX_WORKERS ? Number(((state.activeWorkers / MAX_WORKERS) * 100).toFixed(1)) : 0,
    lightforce: lightforceState()
  };
}

function send(res, code, obj) {
  const body = JSON.stringify(obj, null, 2);
  res.writeHead(code, {
    "Content-Type":"application/json; charset=utf-8",
    "Cache-Control":"no-store",
    "Access-Control-Allow-Origin":"*"
  });
  res.end(body);
}

function runWorker(taskId) {
  return new Promise((resolve, reject) => {
    const code = `
      const { parentPort, workerData } = require("worker_threads");
      let acc = 0;
      for (let i = 0; i < 250000; i++) acc = (acc + i + workerData.taskId) % 1000003;
      parentPort.postMessage({ taskId: workerData.taskId, checksum: acc });
    `;
    const worker = new Worker(code, { eval: true, workerData: { taskId } });
    state.activeWorkers++;
    worker.once("message", msg => {
      state.activeWorkers--;
      state.completedTasks++;
      resolve(msg);
    });
    worker.once("error", err => {
      state.activeWorkers--;
      reject(err);
    });
  });
}

async function executeBatch(count) {
  const total = Math.min(Math.max(Number(count || 1), 1), 1000);
  state.queuedTasks += total;
  state.lastRunAt = new Date().toISOString();
  const results = [];
  let cursor = 0;

  async function lane() {
    while (true) {
      const i = cursor++;
      if (i >= total) return;
      state.queuedTasks--;
      results.push(await runWorker(i));
    }
  }

  const lanes = Array.from({ length: Math.min(MAX_WORKERS, total) }, () => lane());
  await Promise.all(lanes);
  return results;
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, "http://localhost");

  if (url.pathname === "/health") {
    return send(res, 200, {
      ok: true,
      service: "gpt-doug-cloud-swarm",
      authority: AUTHORITY,
      host_cpus: os.cpus().length,
      max_real_workers: MAX_WORKERS,
      telemetry: telemetry(),
      virtual_namespace: { prefix: "gpt-doug", start: "00", end: VIRTUAL_END },
      autonomous_replication: false
    });
  }

  if (url.pathname === "/swarm/status") {
    return send(res, 200, {
      ...state,
      max_real_workers: MAX_WORKERS,
      virtual_agents: "gpt-doug00..gpt-doug" + VIRTUAL_END,
      mode: "VIRTUAL_NAMESPACE_REAL_BOUNDED_WORKERS",
      authority: AUTHORITY,
      telemetry: telemetry()
    });
  }

  if (url.pathname === "/swarm/run" && req.method === "POST") {
    const count = Number(url.searchParams.get("count") || 1);
    try {
      const results = await executeBatch(count);
      return send(res, 200, {
        ok: true,
        requested: count,
        executed: results.length,
        max_real_workers: MAX_WORKERS,
        sample: results.slice(0, 10)
      });
    } catch (err) {
      return send(res, 500, { ok:false, error:String(err.message || err) });
    }
  }

  return send(res, 200, {
    service:"GPT-DOUG Cloud Swarm",
    endpoints:["/health","/swarm/status","POST /swarm/run?count=100"],
    note:"Astronomical swarm identifiers are virtual; real worker concurrency is bounded."
  });
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`GPT-DOUG cloud swarm listening on ${PORT} with max ${MAX_WORKERS} real workers`);
});
