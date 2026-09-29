const http = require("http");
const https = require("https");

const PORT = Number(process.env.PORT || 10000);

const services = [
  { id: "maven", name: "GPT-DOUG MAVEN", url: "https://gpt-doug-robotics-intel.onrender.com/maven-geospatial.html" },
  { id: "robotics", name: "Robotics Intel", url: "https://gpt-doug-robotics-intel.onrender.com/" },
  { id: "xuniadao", name: "XuniaDAO Live", url: "https://xuniadao-live.onrender.com/" },
  { id: "swarm", name: "GPT-DOUG Swarm", url: "https://gptdoug-all-kinds-swarm.onrender.com/" },
  { id: "zyraflock", name: "ZyraFlock", url: "https://zyraflock.onrender.com/" },
  { id: "mmgis", name: "XUNIA MMGIS Forge", url: "https://xunia-mmgis-forge.onrender.com/" },
  { id: "planet", name: "XUNIA Planet", url: "https://xunia-planet.onrender.com/" },
  { id: "righttrack", name: "Right Track", url: "https://right-track-he91.onrender.com/api/health" }
];

function probe(url, timeoutMs = 10000) {
  return new Promise(resolve => {
    const started = Date.now();
    let settled = false;

    const done = result => {
      if (settled) return;
      settled = true;
      resolve({ ...result, latency_ms: Date.now() - started });
    };

    try {
      const req = https.get(url, {
        headers: {
          "User-Agent": "XUNIA-Ops-Health/1.0",
          "Accept": "text/html,application/json;q=0.9,*/*;q=0.8"
        }
      }, res => {
        res.resume();
        const status = Number(res.statusCode || 0);
        done({
          reachable: status > 0 && status < 500,
          http_status: status,
          location: res.headers.location || null
        });
      });

      req.setTimeout(timeoutMs, () => {
        req.destroy();
        done({ reachable: false, http_status: 0, error: "timeout" });
      });

      req.on("error", err => {
        done({ reachable: false, http_status: 0, error: err.code || err.message });
      });
    } catch (err) {
      done({ reachable: false, http_status: 0, error: err.message });
    }
  });
}

function getJson(url, timeoutMs = 10000) {
  return new Promise(resolve => {
    const req = https.get(url, {
      headers: {
        "User-Agent": "XUNIA-Ops-Health/1.0",
        "Accept": "application/vnd.github+json"
      }
    }, res => {
      let body = "";
      res.setEncoding("utf8");
      res.on("data", chunk => { body += chunk; });
      res.on("end", () => {
        try { resolve(JSON.parse(body)); } catch { resolve(null); }
      });
    });
    req.setTimeout(timeoutMs, () => { req.destroy(); resolve(null); });
    req.on("error", () => resolve(null));
  });
}

async function statusPayload() {
  const checks = await Promise.all(services.map(async svc => ({
    id: svc.id,
    name: svc.name,
    url: svc.url,
    ...(await probe(svc.url))
  })));

  const commit = await getJson("https://api.github.com/repos/sonoxo/gpt-doug-llm/commits/main");
  const online = checks.filter(x => x.reachable).length;

  return {
    schema: "xunia.ops.status.v1",
    generated_at: new Date().toISOString(),
    mode: "PUBLIC_DEFENSIVE_SITUATIONAL_AWARENESS",
    repository: {
      full_name: "sonoxo/gpt-doug-llm",
      branch: "main",
      sha: commit && commit.sha ? commit.sha : null
    },
    summary: {
      total: checks.length,
      reachable: online,
      degraded: checks.length - online
    },
    services: checks,
    policy: {
      precise_targeting: false,
      weapon_control: false,
      external_action: false,
      public_and_authorized_sources_only: true
    }
  };
}

function send(res, status, body, type = "application/json; charset=utf-8") {
  res.writeHead(status, {
    "Content-Type": type,
    "Access-Control-Allow-Origin": "*",
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff"
  });
  res.end(body);
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, "http://localhost");

  if (req.method === "OPTIONS") {
    res.writeHead(204, {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET,OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type"
    });
    return res.end();
  }

  if (req.method !== "GET") {
    return send(res, 405, JSON.stringify({ error: "method_not_allowed" }));
  }

  if (url.pathname === "/health") {
    return send(res, 200, JSON.stringify({ ok: true, service: "xunia-ops-api", time: new Date().toISOString() }));
  }

  if (url.pathname === "/api/status") {
    try {
      return send(res, 200, JSON.stringify(await statusPayload(), null, 2));
    } catch (err) {
      return send(res, 500, JSON.stringify({ error: "status_failed", detail: String(err.message || err) }));
    }
  }

  return send(res, 200, JSON.stringify({
    service: "XUNIA Ops API",
    endpoints: ["/health", "/api/status"],
    mode: "PUBLIC_DEFENSIVE_SITUATIONAL_AWARENESS"
  }, null, 2));
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`XUNIA Ops API listening on 0.0.0.0:${PORT}`);
});
