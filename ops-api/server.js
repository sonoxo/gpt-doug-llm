const http = require("http");
const https = require("https");

const PORT = Number(process.env.PORT || 10000);
const translateCache = new Map();
const translateRate = new Map();

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

const allowedTranslateOrigins = new Set([
  "https://xunia.org",
  "https://www.xunia.org",
  "https://gpt-doug-robotics-intel.onrender.com",
  "http://localhost",
  "http://127.0.0.1"
]);

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
          "User-Agent": "XUNIA-Ops-Health/1.1",
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

function getJson(url, timeoutMs = 10000, headers = {}) {
  return new Promise(resolve => {
    const req = https.get(url, {
      headers: {
        "User-Agent": "XUNIA-Ops/1.1",
        "Accept": "application/json",
        ...headers
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

  const commit = await getJson("https://api.github.com/repos/sonoxo/gpt-doug-llm/commits/main", 10000, {
    "Accept": "application/vnd.github+json"
  });
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

function corsOrigin(req) {
  const origin = String(req.headers.origin || "");
  if (allowedTranslateOrigins.has(origin)) return origin;
  if (/^https:\/\/[^/]+\.xunia\.org$/i.test(origin)) return origin;
  return "";
}

function send(res, status, body, type = "application/json; charset=utf-8", extraHeaders = {}) {
  res.writeHead(status, {
    "Content-Type": type,
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    ...extraHeaders
  });
  res.end(body);
}

function readJson(req, maxBytes = 24000) {
  return new Promise((resolve, reject) => {
    let body = "";
    let bytes = 0;
    req.setEncoding("utf8");
    req.on("data", chunk => {
      bytes += Buffer.byteLength(chunk);
      if (bytes > maxBytes) {
        reject(new Error("body_too_large"));
        req.destroy();
        return;
      }
      body += chunk;
    });
    req.on("end", () => {
      try { resolve(JSON.parse(body || "{}")); }
      catch { reject(new Error("invalid_json")); }
    });
    req.on("error", reject);
  });
}

function rateLimit(req) {
  const now = Date.now();
  const windowMs = 60_000;
  const limit = 12;
  const key = String(req.headers["x-forwarded-for"] || req.socket.remoteAddress || "unknown").split(",")[0].trim();
  const entry = translateRate.get(key);
  if (!entry || now - entry.started >= windowMs) {
    translateRate.set(key, { started: now, count: 1 });
    return true;
  }
  entry.count += 1;
  return entry.count <= limit;
}

function validLanguage(tag) {
  return /^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})?$/.test(String(tag || ""));
}

async function translateOne(source, target, text) {
  const key = source + "|" + target + "|" + text;
  if (translateCache.has(key)) return translateCache.get(key);

  const url =
    "https://api.mymemory.translated.net/get?q=" +
    encodeURIComponent(text) +
    "&langpair=" +
    encodeURIComponent(source + "|" + target);

  const data = await getJson(url, 10000);
  const translated =
    data &&
    data.responseData &&
    typeof data.responseData.translatedText === "string" &&
    data.responseData.translatedText.trim()
      ? data.responseData.translatedText
      : text;

  translateCache.set(key, translated);
  if (translateCache.size > 4000) {
    const first = translateCache.keys().next().value;
    if (first) translateCache.delete(first);
  }
  return translated;
}

async function translatePayload(body) {
  const source = String(body.source || "en").trim();
  const target = String(body.target || "").trim();
  const texts = Array.isArray(body.texts) ? body.texts : [];

  if (source !== "en") throw new Error("source_must_be_en");
  if (!validLanguage(target)) throw new Error("invalid_target");
  if (!texts.length || texts.length > 12) throw new Error("invalid_text_count");

  let totalBytes = 0;
  const clean = texts.map(value => {
    const text = String(value || "");
    const bytes = Buffer.byteLength(text, "utf8");
    totalBytes += bytes;
    if (!text.trim() || bytes > 450) throw new Error("invalid_text");
    return text;
  });
  if (totalBytes > 5000) throw new Error("payload_too_large");

  const translations = [];
  for (const text of clean) {
    translations.push(await translateOne(source, target, text));
  }

  return {
    source,
    target,
    provider: "MyMemory public translation API",
    generated_at: new Date().toISOString(),
    translations
  };
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, "http://localhost");
  const origin = corsOrigin(req);

  if (req.method === "OPTIONS") {
    if (url.pathname === "/api/translate" && !origin) {
      return send(res, 403, JSON.stringify({ error: "origin_not_allowed" }));
    }
    res.writeHead(204, {
      "Access-Control-Allow-Origin": origin || "*",
      "Vary": "Origin",
      "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type"
    });
    return res.end();
  }

  if (url.pathname === "/health" && req.method === "GET") {
    return send(res, 200, JSON.stringify({ ok: true, service: "xunia-ops-api", time: new Date().toISOString() }), "application/json; charset=utf-8", {
      "Access-Control-Allow-Origin": "*"
    });
  }

  if (url.pathname === "/api/status" && req.method === "GET") {
    try {
      return send(res, 200, JSON.stringify(await statusPayload(), null, 2), "application/json; charset=utf-8", {
        "Access-Control-Allow-Origin": "*"
      });
    } catch (err) {
      return send(res, 500, JSON.stringify({ error: "status_failed", detail: String(err.message || err) }), "application/json; charset=utf-8", {
        "Access-Control-Allow-Origin": "*"
      });
    }
  }

  if (url.pathname === "/api/translate" && req.method === "POST") {
    if (!origin) return send(res, 403, JSON.stringify({ error: "origin_not_allowed" }));
    if (!rateLimit(req)) return send(res, 429, JSON.stringify({ error: "rate_limited" }), "application/json; charset=utf-8", {
      "Access-Control-Allow-Origin": origin,
      "Vary": "Origin"
    });

    try {
      const body = await readJson(req);
      const payload = await translatePayload(body);
      return send(res, 200, JSON.stringify(payload), "application/json; charset=utf-8", {
        "Access-Control-Allow-Origin": origin,
        "Vary": "Origin"
      });
    } catch (err) {
      const message = String(err.message || err);
      const status = message === "body_too_large" ? 413 : 400;
      return send(res, status, JSON.stringify({ error: message }), "application/json; charset=utf-8", {
        "Access-Control-Allow-Origin": origin,
        "Vary": "Origin"
      });
    }
  }

  if (req.method !== "GET") {
    return send(res, 405, JSON.stringify({ error: "method_not_allowed" }));
  }

  return send(res, 200, JSON.stringify({
    service: "XUNIA Ops API",
    endpoints: ["/health", "/api/status", "/api/translate"],
    mode: "PUBLIC_DEFENSIVE_SITUATIONAL_AWARENESS"
  }, null, 2), "application/json; charset=utf-8", {
    "Access-Control-Allow-Origin": "*"
  });
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`XUNIA Ops API listening on 0.0.0.0:${PORT}`);
});
