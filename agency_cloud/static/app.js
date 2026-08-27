const $ = (id) => document.getElementById(id);

const state = {
  token: sessionStorage.getItem("zyraToken") || "",
  workspace: sessionStorage.getItem("zyraWorkspace") || "",
};

$("token").value = state.token;
$("workspace").value = state.workspace;

function headers(withWorkspace = true) {
  const value = {
    "Authorization": `Bearer ${state.token}`,
    "Content-Type": "application/json",
  };
  if (withWorkspace && state.workspace) value["X-Zyra-Workspace"] = state.workspace;
  return value;
}

async function api(path, options = {}, withWorkspace = true) {
  const response = await fetch(path, {
    ...options,
    headers: { ...headers(withWorkspace), ...(options.headers || {}) },
  });
  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = body && typeof body === "object" ? body.detail || JSON.stringify(body) : body;
    throw new Error(`${response.status} ${detail || response.statusText}`);
  }
  return body;
}

function output(id, value) {
  const element = $(id);
  element.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function setConnection(ok, text) {
  const element = $("connectionStatus");
  element.textContent = text;
  element.classList.toggle("ok", ok);
  element.classList.toggle("bad", !ok);
}

function readForm(form) {
  return Object.fromEntries(new FormData(form).entries());
}

async function refreshStatus() {
  const data = await api("/api/v1/status");
  $("metricCases").textContent = data.counts.cases;
  $("metricIntel").textContent = data.counts.intel;
  $("metricReports").textContent = data.counts.reports;
  $("metricAlerts").textContent = data.counts.alerts;
  $("metricAudit").textContent = data.auditChain.valid ? "VALID" : "HOLD";
  $("metricLock").textContent = data.locks?.ontology?.present ? "PRESENT" : "NONE";
  setConnection(true, "CONNECTED");
  return data;
}

async function connect() {
  state.token = $("token").value.trim();
  state.workspace = $("workspace").value.trim();
  sessionStorage.setItem("zyraToken", state.token);
  sessionStorage.setItem("zyraWorkspace", state.workspace);
  try {
    await refreshStatus();
    await Promise.allSettled([load("cases"), load("reports"), load("alerts")]);
  } catch (error) {
    setConnection(false, "ACCESS HOLD");
    alert(error.message);
  }
}

async function discoverWorkspaces() {
  state.token = $("token").value.trim();
  sessionStorage.setItem("zyraToken", state.token);
  try {
    const workspaces = await api("/api/v1/workspaces", {}, false);
    output("casesOutput", { command: "DISCOVER WORKSPACES", workspaces });
    if (workspaces.length && !state.workspace) {
      state.workspace = workspaces[0].id;
      $("workspace").value = state.workspace;
      sessionStorage.setItem("zyraWorkspace", state.workspace);
    }
  } catch (error) {
    output("casesOutput", `WORKSPACE DISCOVERY HOLD // ${error.message}`);
  }
}

async function load(kind) {
  const map = {
    cases: ["/api/v1/cases", "casesOutput"],
    intel: ["/api/v1/intel", "intelOutput"],
    reports: ["/api/v1/reports", "reportsOutput"],
    alerts: ["/api/v1/alerts", "alertsOutput"],
  };
  const [path, target] = map[kind];
  try {
    output(target, await api(path));
  } catch (error) {
    output(target, `COMMAND HOLD // ${error.message}`);
  }
}

$("connectBtn").addEventListener("click", connect);
$("discoverBtn").addEventListener("click", discoverWorkspaces);
document.querySelectorAll("[data-load]").forEach((button) => {
  button.addEventListener("click", () => load(button.dataset.load));
});

$("caseForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = readForm(event.currentTarget);
  try {
    const created = await api("/api/v1/cases", { method: "POST", body: JSON.stringify(data) });
    output("casesOutput", created);
    event.currentTarget.reset();
    await refreshStatus();
  } catch (error) {
    output("casesOutput", `CASE CREATION HOLD // ${error.message}`);
  }
});

$("intelForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = readForm(event.currentTarget);
  try {
    const created = await api("/api/v1/intel", { method: "POST", body: JSON.stringify(data) });
    output("intelOutput", created);
    event.currentTarget.reset();
    await refreshStatus();
  } catch (error) {
    output("intelOutput", `INTEL INGEST HOLD // ${error.message}`);
  }
});

$("ontologyForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const { question } = readForm(event.currentTarget);
  output("ontologyOutput", "QUERYING MASTER-LOCKED INTELLIGENCE...");
  try {
    const data = await api("/api/v1/ontology/query", { method: "POST", body: JSON.stringify({ question }) }, false);
    output("ontologyOutput", data.result);
  } catch (error) {
    output("ontologyOutput", `ONTOLOGY QUERY HOLD // ${error.message}`);
  }
});

$("ontologyStatusBtn").addEventListener("click", async () => {
  try {
    const data = await api("/api/v1/ontology/status", {}, false);
    output("ontologyOutput", data.result);
  } catch (error) {
    output("ontologyOutput", `ONTOLOGY STATUS HOLD // ${error.message}`);
  }
});

$("glassForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const { question } = readForm(event.currentTarget);
  output("glassOutput", "PEELING LOCKED INTELLIGENCE LAYERS...");
  try {
    const data = await api("/api/v1/glassonion/query", { method: "POST", body: JSON.stringify({ question }) }, false);
    output("glassOutput", data.result);
  } catch (error) {
    output("glassOutput", `GLASSONION QUERY HOLD // ${error.message}`);
  }
});

$("glassStatusBtn").addEventListener("click", async () => {
  try {
    const data = await api("/api/v1/glassonion/status", {}, false);
    output("glassOutput", data.result);
  } catch (error) {
    output("glassOutput", `GLASSONION STATUS HOLD // ${error.message}`);
  }
});

$("liveBtn").addEventListener("click", async () => {
  try {
    output("liveOutput", await api("/api/v1/live/changes", {}, false));
  } catch (error) {
    output("liveOutput", `LIVE INTEL HOLD // ${error.message}`);
  }
});

$("auditBtn").addEventListener("click", async () => {
  try {
    output("auditOutput", await api("/api/v1/audit/verify", {}, false));
  } catch (error) {
    output("auditOutput", `AUDIT VERIFICATION HOLD // ${error.message}`);
  }
});

if (state.token && state.workspace) connect();
