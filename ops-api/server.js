const http = require("http");
const https = require("https");

const PORT = Number(process.env.PORT || 10000);
const translateCache = new Map();
const translateRate = new Map();
const trackingRate = new Map();

const sensorPolicy = {
  schema: "xunia.sensor-governance.v1",
  namespace: "GALACTIC_FEDERATION.SENSOR_GOVERNANCE",
  mode: "AUTHORIZED_SENSORS_ONLY",
  public_ui_max_coordinate_decimals: 2,
  allowed_object_types: new Set([
    "infrastructure_asset",
    "authorized_fleet_vehicle",
    "environmental_sensor",
    "weather_cell",
    "public_event",
    "synthetic_contact"
  ]),
  prohibited_object_types: new Set([
    "person",
    "face",
    "biometric_identity",
    "license_plate_owner",
    "private_vehicle",
    "private_residence",
    "weapon_target",
    "live_military_unit"
  ])
};

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

const liveClients = new Set();
let liveTimer = null;
let liveSequence = 0;
let liveCache = null;
let previousLive = null;
const LIVE_INTERVAL_MS = 15000;

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

function compactPalantir(value) {
  return {
    configured: Boolean(value && value.configured),
    connected: Boolean(value && value.connected),
    mode: value && value.mode ? String(value.mode) : "UNAVAILABLE",
    ontology_bound: Boolean(value && value.ontology_bound),
    object_type_count: Number.isFinite(Number(value && value.object_type_count)) ? Number(value.object_type_count) : null,
    action_type_count: Number.isFinite(Number(value && value.action_type_count)) ? Number(value.action_type_count) : null,
    checked_at: value && value.checked_at ? value.checked_at : null
  };
}

function compactQuakes(value) {
  const features = Array.isArray(value && value.features) ? value.features : [];
  return features.slice(0, 12).map(feature => {
    const coords = feature && feature.geometry && Array.isArray(feature.geometry.coordinates)
      ? feature.geometry.coordinates
      : [];
    const props = feature && feature.properties ? feature.properties : {};
    return {
      id: String(feature && feature.id || ""),
      magnitude: Number.isFinite(Number(props.mag)) ? Number(props.mag) : null,
      place: String(props.place || "Regional event").slice(0, 160),
      observed_at: Number.isFinite(Number(props.time)) ? new Date(Number(props.time)).toISOString() : null,
      latitude: Number.isFinite(Number(coords[1])) ? roundCoord(coords[1], 1) : null,
      longitude: Number.isFinite(Number(coords[0])) ? roundCoord(coords[0], 1) : null,
      depth_km: Number.isFinite(Number(coords[2])) ? Math.round(Number(coords[2])) : null
    };
  });
}

function deriveLiveEvents(next, prev) {
  const events = [];
  if (!prev) {
    events.push({ type: "system", level: "info", message: "MAVEN live fabric initialized" });
    return events;
  }

  const prevServices = new Map((prev.ops && prev.ops.services || []).map(x => [x.id, x]));
  for (const svc of next.ops && next.ops.services || []) {
    const before = prevServices.get(svc.id);
    if (!before || before.reachable !== svc.reachable || before.http_status !== svc.http_status) {
      events.push({
        type: "service",
        level: svc.reachable ? "good" : "warn",
        message: svc.name + " " + (svc.reachable ? "reachable" : "degraded") + " · HTTP " + svc.http_status
      });
    }
  }

  if (
    !prev.palantir ||
    prev.palantir.connected !== next.palantir.connected ||
    prev.palantir.mode !== next.palantir.mode ||
    prev.palantir.ontology_bound !== next.palantir.ontology_bound
  ) {
    events.push({
      type: "palantir",
      level: next.palantir.connected ? "good" : "info",
      message: "Palantir " + next.palantir.mode + (next.palantir.ontology_bound ? " · ontology bound" : "")
    });
  }

  const prevQuakes = new Set((prev.earthquakes || []).map(x => x.id));
  for (const quake of next.earthquakes || []) {
    if (quake.id && !prevQuakes.has(quake.id)) {
      events.push({
        type: "earthquake",
        level: "info",
        message: "USGS M" + (quake.magnitude ?? "—") + " · " + quake.place
      });
    }
  }
  return events.slice(0, 12);
}

async function buildLiveSnapshot() {
  const [ops, palantirRaw, quakeRaw] = await Promise.all([
    statusPayload(),
    getJson("https://xunia-palantir-bridge.onrender.com/api/status", 6500),
    getJson("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_day.geojson", 6500)
  ]);

  const snapshot = {
    schema: "xunia.maven.live.v1",
    sequence: ++liveSequence,
    generated_at: new Date().toISOString(),
    interval_ms: LIVE_INTERVAL_MS,
    mode: "PUBLIC_DEFENSIVE_SITUATIONAL_AWARENESS",
    ops,
    palantir: compactPalantir(palantirRaw),
    earthquakes: compactQuakes(quakeRaw),
    events: [],
    policy: {
      public_and_authorized_sources_only: true,
      public_geolocation_precision: "coarse",
      person_tracking: false,
      biometric_identification: false,
      precise_targeting: false,
      weapon_control: false,
      autonomous_external_action: false
    }
  };
  snapshot.events = deriveLiveEvents(snapshot, previousLive);
  previousLive = snapshot;
  liveCache = snapshot;
  return snapshot;
}

function writeSse(res, eventName, payload) {
  res.write("event: " + eventName + "\n");
  res.write("data: " + JSON.stringify(payload) + "\n\n");
}

async function refreshLiveFabric() {
  try {
    const snapshot = await buildLiveSnapshot();
    for (const res of liveClients) {
      try { writeSse(res, "snapshot", snapshot); } catch {}
    }
  } catch (err) {
    const payload = { generated_at: new Date().toISOString(), error: String(err.message || err) };
    for (const res of liveClients) {
      try { writeSse(res, "error", payload); } catch {}
    }
  }
}

function ensureLiveFabric() {
  if (liveTimer) return;
  refreshLiveFabric();
  liveTimer = setInterval(refreshLiveFabric, LIVE_INTERVAL_MS);
}

function stopLiveFabricIfIdle() {
  if (liveClients.size || !liveTimer) return;
  clearInterval(liveTimer);
  liveTimer = null;
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

function trackingRateLimit(req) {
  const now = Date.now();
  const windowMs = 60_000;
  const limit = 30;
  const key = String(req.headers["x-forwarded-for"] || req.socket.remoteAddress || "unknown").split(",")[0].trim();
  const entry = trackingRate.get(key);
  if (!entry || now - entry.started >= windowMs) {
    trackingRate.set(key, { started: now, count: 1 });
    return true;
  }
  entry.count += 1;
  return entry.count <= limit;
}

function roundCoord(value, decimals = 2) {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  const factor = 10 ** decimals;
  return Math.round(n * factor) / factor;
}

function sensorSchemaPayload() {
  return {
    schema: sensorPolicy.schema,
    namespace: sensorPolicy.namespace,
    mode: sensorPolicy.mode,
    generated_at: new Date().toISOString(),
    allowed_object_types: [...sensorPolicy.allowed_object_types],
    prohibited_object_types: [...sensorPolicy.prohibited_object_types],
    controls: {
      explicit_authorization_required: true,
      provenance_required: true,
      public_ui_coarse_geolocation_only: true,
      public_ui_max_coordinate_decimals: sensorPolicy.public_ui_max_coordinate_decimals,
      facial_recognition: false,
      biometric_identification: false,
      license_plate_owner_lookup: false,
      covert_person_tracking: false,
      private_residence_monitoring: false,
      weapon_targeting: false,
      fire_control: false,
      autonomous_external_action: false,
      persisted_by_validation_endpoint: false
    }
  };
}

function validateTrackingPayload(body) {
  const blockedKeys = [
    "person_id","face_embedding","face_id","biometric_id","plate_text",
    "plate_owner","private_residence_id","weapon_target_id","fire_control_id"
  ];
  for (const key of blockedKeys) {
    if (body && Object.prototype.hasOwnProperty.call(body, key)) throw new Error("prohibited_field:" + key);
  }

  const sourceId = String(body.source_id || "").trim();
  const objectType = String(body.object_type || "").trim();
  const observedAt = String(body.observed_at || "").trim();
  const authorizationScope = String(body.authorization_scope || "").trim();
  const purpose = String(body.purpose || "").trim();

  if (!sourceId || !objectType || !observedAt || !authorizationScope || !purpose) {
    throw new Error("missing_required_field");
  }
  if (sensorPolicy.prohibited_object_types.has(objectType)) throw new Error("prohibited_object_type");
  if (!sensorPolicy.allowed_object_types.has(objectType)) throw new Error("unsupported_object_type");
  if (authorizationScope.toLowerCase() === "unknown" || authorizationScope.toLowerCase() === "none") {
    throw new Error("authorization_scope_required");
  }
  if (Number.isNaN(Date.parse(observedAt))) throw new Error("invalid_observed_at");

  let latitude = null;
  let longitude = null;
  if (body.latitude !== undefined || body.longitude !== undefined) {
    latitude = Number(body.latitude);
    longitude = Number(body.longitude);
    if (!Number.isFinite(latitude) || latitude < -90 || latitude > 90) throw new Error("invalid_latitude");
    if (!Number.isFinite(longitude) || longitude < -180 || longitude > 180) throw new Error("invalid_longitude");
    latitude = roundCoord(latitude, sensorPolicy.public_ui_max_coordinate_decimals);
    longitude = roundCoord(longitude, sensorPolicy.public_ui_max_coordinate_decimals);
  }

  let confidence = body.confidence === undefined ? null : Number(body.confidence);
  if (confidence !== null && (!Number.isFinite(confidence) || confidence < 0 || confidence > 1)) {
    throw new Error("invalid_confidence");
  }

  return {
    schema: "xunia.tracking.observation.v1",
    source_id: sourceId.slice(0, 160),
    provider: String(body.provider || "xunia").slice(0, 80),
    object_type: objectType,
    observed_at: new Date(observedAt).toISOString(),
    authorization_scope: authorizationScope.slice(0, 160),
    purpose: purpose.slice(0, 240),
    confidence,
    latitude,
    longitude,
    provenance_url: typeof body.provenance_url === "string" ? body.provenance_url.slice(0, 500) : null,
    public_precision: latitude === null ? "none" : sensorPolicy.public_ui_max_coordinate_decimals + "_decimals"
  };
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
    if ((url.pathname === "/api/translate" || url.pathname === "/api/tracking/validate") && !origin) {
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

  if (url.pathname === "/api/live" && req.method === "GET") {
    res.writeHead(200, {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      "Connection": "keep-alive",
      "Access-Control-Allow-Origin": "*",
      "X-Accel-Buffering": "no"
    });
    res.write(": gpt-maven-live\n\n");
    liveClients.add(res);
    if (liveCache) writeSse(res, "snapshot", liveCache);
    ensureLiveFabric();

    const heartbeat = setInterval(() => {
      try { res.write(": ping " + Date.now() + "\n\n"); } catch {}
    }, 12000);

    req.on("close", () => {
      clearInterval(heartbeat);
      liveClients.delete(res);
      stopLiveFabricIfIdle();
    });
    return;
  }

  if (url.pathname === "/api/live/snapshot" && req.method === "GET") {
    try {
      const snapshot = liveCache || await buildLiveSnapshot();
      return send(res, 200, JSON.stringify(snapshot, null, 2), "application/json; charset=utf-8", {
        "Access-Control-Allow-Origin": "*"
      });
    } catch (err) {
      return send(res, 503, JSON.stringify({ error: "live_snapshot_failed", detail: String(err.message || err) }), "application/json; charset=utf-8", {
        "Access-Control-Allow-Origin": "*"
      });
    }
  }

  if (url.pathname === "/api/sensors/policy" && req.method === "GET") {
    return send(res, 200, JSON.stringify(sensorSchemaPayload(), null, 2), "application/json; charset=utf-8", {
      "Access-Control-Allow-Origin": "*"
    });
  }

  if (url.pathname === "/api/tracking/schema" && req.method === "GET") {
    return send(res, 200, JSON.stringify({
      ...sensorSchemaPayload(),
      observation_schema: {
        required: ["source_id","object_type","observed_at","authorization_scope","purpose"],
        optional: ["provider","confidence","latitude","longitude","provenance_url"],
        validation_only: true,
        persistence: false,
        actionable: false
      }
    }, null, 2), "application/json; charset=utf-8", {
      "Access-Control-Allow-Origin": "*"
    });
  }

  if (url.pathname === "/api/tracking/validate" && req.method === "POST") {
    if (!origin) return send(res, 403, JSON.stringify({ error: "origin_not_allowed" }));
    if (!trackingRateLimit(req)) return send(res, 429, JSON.stringify({ error: "rate_limited" }), "application/json; charset=utf-8", {
      "Access-Control-Allow-Origin": origin,
      "Vary": "Origin"
    });

    try {
      const body = await readJson(req, 12000);
      const normalized = validateTrackingPayload(body);
      return send(res, 200, JSON.stringify({
        ok: true,
        normalized,
        persisted: false,
        actionable: false,
        policy: sensorPolicy.namespace
      }, null, 2), "application/json; charset=utf-8", {
        "Access-Control-Allow-Origin": origin,
        "Vary": "Origin"
      });
    } catch (err) {
      return send(res, 400, JSON.stringify({ error: String(err.message || err) }), "application/json; charset=utf-8", {
        "Access-Control-Allow-Origin": origin,
        "Vary": "Origin"
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
    endpoints: ["/health", "/api/status", "/api/live", "/api/live/snapshot", "/api/sensors/policy", "/api/tracking/schema", "/api/tracking/validate", "/api/translate"],
    mode: "PUBLIC_DEFENSIVE_SITUATIONAL_AWARENESS"
  }, null, 2), "application/json; charset=utf-8", {
    "Access-Control-Allow-Origin": "*"
  });
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`XUNIA Ops API listening on 0.0.0.0:${PORT}`);
});
