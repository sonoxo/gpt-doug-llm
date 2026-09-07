const DEFAULT_BRIDGE = "http://127.0.0.1:8765";

function normalizeFoundryOrigin(value) {
  const url = new URL(value);
  if (url.protocol !== "https:") throw new Error("Foundry origin must use HTTPS");
  if (!url.hostname.endsWith(".palantirfoundry.com")) {
    throw new Error("Foundry origin must be a palantirfoundry.com tenant");
  }
  if (url.username || url.password || url.search || url.hash) {
    throw new Error("Foundry origin must not contain credentials, query, or fragment");
  }
  return url.origin;
}

function cleanBridge(value) {
  const url = new URL(value || DEFAULT_BRIDGE);
  if (url.protocol !== "http:" || url.hostname !== "127.0.0.1") {
    throw new Error("Bridge must be http://127.0.0.1:<port>");
  }
  return url.origin;
}

async function jsonRequest(url, options = {}) {
  const response = await fetch(url, {
    redirect: "error",
    cache: "no-store",
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {})
    }
  });

  const text = await response.text();
  let payload = {};
  if (text) {
    try { payload = JSON.parse(text); }
    catch { payload = { raw: text.slice(0, 2000) }; }
  }
  if (!response.ok) {
    const detail = payload?.error || payload?.message || response.statusText;
    throw new Error(`HTTP ${response.status}: ${detail}`);
  }
  return payload;
}

export class PalantirToolboxClient {
  constructor({ mode = "bridge", bridgeUrl = DEFAULT_BRIDGE, foundryOrigin = "", token = "" } = {}) {
    this.mode = mode;
    this.bridgeUrl = cleanBridge(bridgeUrl);
    this.foundryOrigin = foundryOrigin ? normalizeFoundryOrigin(foundryOrigin) : "";
    this.token = token;
  }

  async request(path, { method = "GET", body } = {}) {
    if (!path.startsWith("/") || path.includes("://")) throw new Error("Unsafe request path");

    if (this.mode === "bridge") {
      return jsonRequest(`${this.bridgeUrl}${path}`, {
        method,
        body: body ? JSON.stringify(body) : undefined
      });
    }

    if (this.mode !== "direct") throw new Error("Unknown connection mode");
    if (!this.foundryOrigin) throw new Error("Configure Foundry origin");
    if (!this.token) throw new Error("Paste a short-lived bearer token for this browser session");

    return jsonRequest(`${this.foundryOrigin}${path}`, {
      method,
      body: body ? JSON.stringify(body) : undefined,
      headers: { Authorization: `Bearer ${this.token}` }
    });
  }

  status() {
    if (this.mode === "bridge") return this.request("/health");
    return Promise.resolve({
      ok: true,
      mode: "direct",
      foundryOrigin: this.foundryOrigin,
      tokenPersistence: "chrome.storage.session only"
    });
  }

  listOntologies(pageSize = 100) {
    if (this.mode === "bridge") return this.request(`/ontologies?pageSize=${encodeURIComponent(pageSize)}`);
    return this.request(`/api/v2/ontologies?pageSize=${encodeURIComponent(pageSize)}`);
  }

  listObjectTypes(ontology, pageSize = 100) {
    const o = encodeURIComponent(ontology);
    if (this.mode === "bridge") return this.request(`/ontologies/${o}/object-types?pageSize=${encodeURIComponent(pageSize)}`);
    return this.request(`/api/v2/ontologies/${o}/objectTypes?pageSize=${encodeURIComponent(pageSize)}`);
  }

  listObjects(ontology, objectType, pageSize = 50) {
    const o = encodeURIComponent(ontology);
    const t = encodeURIComponent(objectType);
    if (this.mode === "bridge") return this.request(`/ontologies/${o}/objects/${t}?pageSize=${encodeURIComponent(pageSize)}`);
    return this.request(`/api/v2/ontologies/${o}/objects/${t}?pageSize=${encodeURIComponent(pageSize)}`);
  }

  searchObjects(ontology, objectType, searchBody) {
    const o = encodeURIComponent(ontology);
    const t = encodeURIComponent(objectType);
    if (this.mode === "bridge") {
      return this.request(`/ontologies/${o}/objects/${t}/search`, { method: "POST", body: searchBody });
    }
    return this.request(`/api/v2/ontologies/${o}/objects/${t}/search`, { method: "POST", body: searchBody });
  }
}

export { DEFAULT_BRIDGE, normalizeFoundryOrigin };
