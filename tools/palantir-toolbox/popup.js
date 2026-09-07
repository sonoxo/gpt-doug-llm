import { DEFAULT_BRIDGE, PalantirToolboxClient } from "./foundry.js";

const $ = (id) => document.getElementById(id);
const els = {
  mode: $("mode"), bridgeUrl: $("bridgeUrl"), bridgeKey: $("bridgeKey"), foundryOrigin: $("foundryOrigin"), token: $("token"),
  bridgeRow: $("bridgeRow"), tokenRow: $("tokenRow"), statusOut: $("statusOut"), output: $("output"),
  ontology: $("ontology"), objectType: $("objectType")
};

function pretty(value) {
  return JSON.stringify(value, null, 2);
}

function setOutput(value) {
  els.output.textContent = typeof value === "string" ? value : pretty(value);
}

function setStatus(value) {
  els.statusOut.textContent = typeof value === "string" ? value : pretty(value);
}

function syncMode() {
  const direct = els.mode.value === "direct";
  els.bridgeRow.classList.toggle("hidden", direct);
  els.tokenRow.classList.toggle("hidden", !direct);
}

async function loadConfig() {
  const local = await chrome.storage.local.get(["palantirToolboxConfig"]);
  const session = await chrome.storage.session.get(["palantirToolboxToken", "palantirToolboxBridgeKey"]);
  const config = local.palantirToolboxConfig || {};
  els.mode.value = config.mode || "bridge";
  els.bridgeUrl.value = config.bridgeUrl || DEFAULT_BRIDGE;
  els.foundryOrigin.value = config.foundryOrigin || "";
  els.token.value = session.palantirToolboxToken || "";
  els.bridgeKey.value = session.palantirToolboxBridgeKey || "";
  syncMode();
}

async function saveConfig() {
  const config = {
    mode: els.mode.value,
    bridgeUrl: els.bridgeUrl.value.trim() || DEFAULT_BRIDGE,
    foundryOrigin: els.foundryOrigin.value.trim()
  };
  await chrome.storage.local.set({ palantirToolboxConfig: config });

  if (els.mode.value === "direct") {
    if (els.token.value.trim()) {
      await chrome.storage.session.set({ palantirToolboxToken: els.token.value.trim() });
    }
    await chrome.storage.session.remove("palantirToolboxBridgeKey");
  } else {
    if (els.bridgeKey.value.trim()) {
      await chrome.storage.session.set({ palantirToolboxBridgeKey: els.bridgeKey.value.trim() });
    }
    await chrome.storage.session.remove("palantirToolboxToken");
  }

  setStatus({
    saved: true,
    mode: config.mode,
    secretPersistence: "chrome.storage.session only"
  });
}

async function client() {
  const local = await chrome.storage.local.get(["palantirToolboxConfig"]);
  const session = await chrome.storage.session.get(["palantirToolboxToken", "palantirToolboxBridgeKey"]);
  const config = local.palantirToolboxConfig || {
    mode: els.mode.value,
    bridgeUrl: els.bridgeUrl.value.trim() || DEFAULT_BRIDGE,
    foundryOrigin: els.foundryOrigin.value.trim()
  };
  return new PalantirToolboxClient({
    ...config,
    bridgeKey: session.palantirToolboxBridgeKey || els.bridgeKey.value.trim(),
    token: session.palantirToolboxToken || els.token.value.trim()
  });
}

async function run(label, fn) {
  setOutput(`${label}…`);
  try {
    const result = await fn();
    setOutput(result);
    return result;
  } catch (error) {
    setOutput({ ok: false, error: error?.message || String(error) });
  }
}

els.mode.addEventListener("change", syncMode);
$("save").addEventListener("click", saveConfig);
$("clear").addEventListener("click", () => setOutput("Ready."));

$("status").addEventListener("click", async () => {
  await saveConfig();
  await run("Testing connection", async () => {
    const c = await client();
    const result = await c.status();
    setStatus(result);
    return result;
  });
});

$("listOntologies").addEventListener("click", () => run("Listing ontologies", async () => (await client()).listOntologies()));

$("listTypes").addEventListener("click", () => run("Listing object types", async () => {
  const ontology = els.ontology.value.trim();
  if (!ontology) throw new Error("Enter an ontology API name");
  return (await client()).listObjectTypes(ontology);
}));

$("listObjects").addEventListener("click", () => run("Listing objects", async () => {
  const ontology = els.ontology.value.trim();
  const objectType = els.objectType.value.trim();
  if (!ontology || !objectType) throw new Error("Enter ontology and object type API names");
  return (await client()).listObjects(ontology, objectType);
}));

$("showCapture").addEventListener("click", async () => {
  const data = await chrome.storage.session.get(["lastCapture"]);
  setOutput(data.lastCapture || { message: "No capture in this browser session yet." });
});

await loadConfig();
