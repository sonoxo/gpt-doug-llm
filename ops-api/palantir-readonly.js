const https = require("https");

let tokenCache = null;

function cfg() {
  const hostname = String(process.env.PALANTIR_FOUNDRY_HOSTNAME || "").trim().replace(/\/+$/, "");
  return {
    hostname,
    clientId: String(process.env.PALANTIR_CLIENT_ID || "").trim(),
    clientSecret: String(process.env.PALANTIR_CLIENT_SECRET || "").trim(),
    ontology: String(process.env.PALANTIR_ONTOLOGY || "").trim(),
    scopes: String(process.env.PALANTIR_SCOPES || "api:ontologies-read").trim()
  };
}

function configured(c = cfg()) {
  return Boolean(c.hostname && c.clientId && c.clientSecret && c.ontology);
}

function requestJson(urlString, { method = "GET", headers = {}, body = null, timeoutMs = 12000 } = {}) {
  return new Promise((resolve, reject) => {
    const url = new URL(urlString);
    if (url.protocol !== "https:") return reject(new Error("palantir_https_required"));

    const req = https.request(url, { method, headers }, res => {
      let raw = "";
      res.setEncoding("utf8");
      res.on("data", chunk => { raw += chunk; });
      res.on("end", () => {
        let data = null;
        try { data = raw ? JSON.parse(raw) : {}; } catch {}
        if ((res.statusCode || 500) >= 400) {
          const err = new Error("palantir_http_" + res.statusCode);
          err.statusCode = res.statusCode;
          return reject(err);
        }
        resolve(data);
      });
    });

    req.setTimeout(timeoutMs, () => {
      req.destroy(new Error("palantir_timeout"));
    });
    req.on("error", reject);
    if (body) req.write(body);
    req.end();
  });
}

async function getToken(c = cfg()) {
  const now = Date.now();
  if (tokenCache && tokenCache.expiresAt > now + 60000) return tokenCache.accessToken;

  const form = new URLSearchParams({
    grant_type: "client_credentials",
    client_id: c.clientId,
    client_secret: c.clientSecret,
    scope: c.scopes
  }).toString();

  const data = await requestJson(c.hostname + "/multipass/api/oauth2/token", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "Content-Length": Buffer.byteLength(form)
    },
    body: form
  });

  if (!data || !data.access_token) throw new Error("palantir_token_missing");
  tokenCache = {
    accessToken: data.access_token,
    expiresAt: now + Math.max(60, Number(data.expires_in || 300)) * 1000
  };
  return tokenCache.accessToken;
}

async function api(path, c = cfg()) {
  const token = await getToken(c);
  return requestJson(c.hostname + path, {
    headers: {
      "Authorization": "Bearer " + token,
      "Accept": "application/json"
    }
  });
}

async function status() {
  const c = cfg();
  if (!configured(c)) {
    return {
      configured: false,
      connected: false,
      mode: "READ_ONLY_STANDBY",
      ontology_bound: false,
      object_type_count: null,
      action_type_count: null,
      required_env: [
        "PALANTIR_FOUNDRY_HOSTNAME",
        "PALANTIR_CLIENT_ID",
        "PALANTIR_CLIENT_SECRET",
        "PALANTIR_ONTOLOGY"
      ]
    };
  }

  try {
    const ontologyKey = encodeURIComponent(c.ontology);
    const [ontologies, objectTypes, actionTypes] = await Promise.all([
      api("/api/v2/ontologies", c),
      api("/api/v2/ontologies/" + ontologyKey + "/objectTypes?pageSize=500", c),
      api("/api/v2/ontologies/" + ontologyKey + "/actionTypes?pageSize=500", c)
    ]);

    const available = Array.isArray(ontologies && ontologies.data) ? ontologies.data : [];
    const bound = available.some(o => o && (o.apiName === c.ontology || o.rid === c.ontology));

    return {
      configured: true,
      connected: true,
      mode: "READ_ONLY_CONNECTED",
      ontology_bound: bound,
      object_type_count: Array.isArray(objectTypes && objectTypes.data) ? objectTypes.data.length : 0,
      action_type_count: Array.isArray(actionTypes && actionTypes.data) ? actionTypes.data.length : 0,
      scope: c.scopes,
      checked_at: new Date().toISOString()
    };
  } catch (err) {
    return {
      configured: true,
      connected: false,
      mode: "READ_ONLY_ERROR",
      ontology_bound: false,
      object_type_count: null,
      action_type_count: null,
      error: String(err.message || err),
      checked_at: new Date().toISOString()
    };
  }
}

module.exports = { status };
