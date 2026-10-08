from __future__ import annotations

from collections import Counter
from typing import Any

from .atomic import stack_manifest
from .capabilities import CAPABILITY_CATALOG
from .config import SwarmConfig
from .connectors import ConnectorConfig
from .heartbeat import build_heartbeat
from .policy import CapabilityPolicy


def _capability_summary(policy: CapabilityPolicy) -> dict[str, Any]:
    totals = Counter(spec.risk.value for spec in CAPABILITY_CATALOG)
    enabled = Counter(
        spec.risk.value
        for spec in CAPABILITY_CATALOG
        if spec.name in policy.allowed
    )
    return {
        "total": len(CAPABILITY_CATALOG),
        "enabled": len(policy.allowed),
        "by_risk": {
            risk: {
                "enabled": enabled.get(risk, 0),
                "total": totals.get(risk, 0),
            }
            for risk in ("low", "medium", "high")
        },
    }


def _layer_metrics(
    layer_name: str,
    *,
    config: SwarmConfig,
    connectors: ConnectorConfig,
    policy: CapabilityPolicy,
    capability_summary: dict[str, Any],
    manifest: dict[str, Any],
) -> list[dict[str, str | int | bool]]:
    metrics: dict[str, list[dict[str, str | int | bool]]] = {
        "particle": [
            {"label": "Trace IDs", "value": "active"},
            {"label": "Digest", "value": "SHA-256"},
        ],
        "atom": [
            {"label": "Enabled capabilities", "value": capability_summary["enabled"]},
            {"label": "Supported capabilities", "value": capability_summary["total"]},
        ],
        "molecule": [
            {"label": "Max execution depth", "value": config.max_depth},
            {"label": "Composition", "value": "bounded"},
        ],
        "cell": [
            {"label": "Agent cells", "value": config.agent_count},
            {"label": "Adapter", "value": config.adapter},
        ],
        "swarm": [
            {"label": "Max fanout", "value": config.max_fanout},
            {"label": "Capacity", "value": config.agent_count},
        ],
        "service": [
            {"label": "Authorized endpoints", "value": len(connectors.endpoints)},
            {"label": "Connector retries", "value": connectors.max_retries},
        ],
        "fabric": [
            {"label": "Deployment", "value": "Compose + Kubernetes"},
            {"label": "Network base", "value": "default-deny"},
        ],
        "governance": [
            {"label": "Profile", "value": policy_profile_name(policy)},
            {"label": "Stack valid", "value": manifest["valid"]},
        ],
    }
    return metrics[layer_name]


def policy_profile_name(policy: CapabilityPolicy) -> str:
    from os import getenv

    return getenv("SHAGGOTH_CAPABILITY_PROFILE", "reasoning")


def build_visual_data() -> dict[str, Any]:
    config = SwarmConfig()
    connectors = ConnectorConfig.from_env()
    policy = CapabilityPolicy.from_env()
    manifest = stack_manifest()
    heartbeat = build_heartbeat()
    capability_summary = _capability_summary(policy)

    layers = []
    for layer in manifest["layers"]:
        enriched = dict(layer)
        enriched["metrics"] = _layer_metrics(
            layer["name"],
            config=config,
            connectors=connectors,
            policy=policy,
            capability_summary=capability_summary,
            manifest=manifest,
        )
        layers.append(enriched)

    return {
        "schema_version": 1,
        "heartbeat": heartbeat.as_dict(),
        "runtime": {
            "agent_capacity": config.agent_count,
            "max_fanout": config.max_fanout,
            "max_depth": config.max_depth,
            "adapter": config.adapter,
            "capability_profile": policy_profile_name(policy),
            "authorized_endpoint_count": len(connectors.endpoints),
            "service_version": connectors.service_version,
        },
        "capabilities": capability_summary,
        "atomic": {
            "valid": manifest["valid"],
            "layer_count": manifest["layer_count"],
            "errors": manifest["errors"],
            "layers": layers,
        },
    }


def render_visual_dashboard() -> str:
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Shaggoth Visual Data Layers</title>
<style>
:root {
  color-scheme: dark;
  --bg:#07100f;
  --panel:#0c1816;
  --panel2:#10211e;
  --line:#21443c;
  --text:#e7fff7;
  --muted:#8fb4aa;
  --good:#5ef0b0;
  --warn:#f4c95d;
  --bad:#ff6f7d;
  --accent:#70ffd1;
  --accent2:#7ac7ff;
}
*{box-sizing:border-box}
body{margin:0;background:
radial-gradient(circle at 15% 0%,rgba(62,145,117,.18),transparent 35%),
radial-gradient(circle at 90% 10%,rgba(70,121,168,.14),transparent 30%),
var(--bg);color:var(--text);font:14px/1.45 ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace}
main{max-width:1320px;margin:auto;padding:24px}
header{display:flex;gap:18px;align-items:center;justify-content:space-between;flex-wrap:wrap;margin-bottom:18px}
.brand{display:flex;align-items:center;gap:12px}
.pulse{width:14px;height:14px;border-radius:50%;background:var(--good);box-shadow:0 0 0 0 rgba(94,240,176,.55);animation:pulse 1.8s infinite}
@keyframes pulse{70%{box-shadow:0 0 0 10px rgba(94,240,176,0)}100%{box-shadow:0 0 0 0 rgba(94,240,176,0)}}
h1{font-size:20px;margin:0;letter-spacing:.04em}
.subtitle{color:var(--muted);margin-top:4px}
.controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
button{font:inherit;color:var(--text);background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:9px 12px;cursor:pointer}
button:hover,button:focus-visible{border-color:var(--accent);outline:none}
.live{font-size:12px;color:var(--muted)}
.kpis{display:grid;grid-template-columns:repeat(6,minmax(120px,1fr));gap:10px;margin-bottom:18px}
.kpi{background:rgba(12,24,22,.85);border:1px solid var(--line);border-radius:12px;padding:14px}
.kpi b{display:block;font-size:22px;margin-top:6px;color:var(--accent)}
.kpi span{color:var(--muted);font-size:12px}
.layout{display:grid;grid-template-columns:minmax(0,1.8fr) minmax(280px,.8fr);gap:16px}
.panel{background:rgba(12,24,22,.88);border:1px solid var(--line);border-radius:14px;padding:16px;min-width:0}
.panel h2{margin:0 0 12px;font-size:14px;color:var(--muted);font-weight:600;letter-spacing:.08em;text-transform:uppercase}
.layers{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;position:relative}
.layer{min-height:172px;text-align:left;padding:14px;border:1px solid var(--line);background:linear-gradient(145deg,rgba(16,33,30,.96),rgba(8,19,17,.96));border-radius:12px;position:relative;overflow:hidden}
.layer::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--series,var(--accent))}
.layer.selected{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}
.layer .id{font-size:11px;color:var(--muted)}
.layer .name{font-size:16px;font-weight:700;text-transform:uppercase;margin:4px 0 8px}
.layer .purpose{font-size:12px;color:#b9d6ce;min-height:54px}
.metric-row{display:flex;justify-content:space-between;gap:10px;border-top:1px solid rgba(33,68,60,.7);padding-top:7px;margin-top:7px;font-size:11px}
.metric-row span:first-child{color:var(--muted)}
.layer[data-id="0"]{--series:#73e7ff}.layer[data-id="1"]{--series:#6ef0bd}.layer[data-id="2"]{--series:#a2e36f}.layer[data-id="3"]{--series:#e5db6f}.layer[data-id="4"]{--series:#ffc76b}.layer[data-id="5"]{--series:#ffa070}.layer[data-id="6"]{--series:#d48cff}.layer[data-id="7"]{--series:#ff7896}
.detail h3{margin:0 0 5px;font-size:20px;text-transform:uppercase}
.detail .layer-id{color:var(--accent);font-size:12px}
.detail p{color:#c0dbd3}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}
.tag{border:1px solid var(--line);border-radius:999px;padding:4px 7px;color:var(--muted);font-size:11px}
.detail ul{padding-left:18px;color:#c0dbd3}
.capbar{margin:10px 0}
.capbar-head{display:flex;justify-content:space-between;color:var(--muted);font-size:11px;margin-bottom:5px}
.track{height:8px;background:#07100f;border:1px solid var(--line);border-radius:999px;overflow:hidden}
.fill{height:100%;background:linear-gradient(90deg,var(--accent2),var(--accent));width:0;transition:width .35s ease}
.footer{display:flex;justify-content:space-between;gap:12px;color:var(--muted);font-size:11px;margin-top:14px;flex-wrap:wrap}
.error{color:var(--bad)}
@media(max-width:1000px){.kpis{grid-template-columns:repeat(3,1fr)}.layers{grid-template-columns:repeat(2,1fr)}.layout{grid-template-columns:1fr}}
@media(max-width:560px){main{padding:14px}.kpis{grid-template-columns:repeat(2,1fr)}.layers{grid-template-columns:1fr}.layer{min-height:auto}}
@media(prefers-reduced-motion:reduce){.pulse{animation:none}.fill{transition:none}}
</style>
</head>
<body>
<main>
<header>
  <div class="brand">
    <div class="pulse" id="pulse" aria-hidden="true"></div>
    <div><h1>SHAGGOTH // VISUAL DATA LAYERS</h1><div class="subtitle">Atomic runtime topology · L0 → L7</div></div>
  </div>
  <div class="controls">
    <span class="live" id="updated">waiting for telemetry…</span>
    <button id="refresh" type="button">Refresh now</button>
    <button id="toggle" type="button">Pause live</button>
  </div>
</header>

<section class="kpis" aria-label="Runtime metrics">
  <div class="kpi"><span>Heartbeat</span><b id="heartbeat">—</b></div>
  <div class="kpi"><span>Agent cells</span><b id="agents">—</b></div>
  <div class="kpi"><span>Capabilities</span><b id="caps">—</b></div>
  <div class="kpi"><span>Max fanout</span><b id="fanout">—</b></div>
  <div class="kpi"><span>Max depth</span><b id="depth">—</b></div>
  <div class="kpi"><span>Authorized endpoints</span><b id="endpoints">—</b></div>
</section>

<div class="layout">
  <section class="panel">
    <h2>Atomic topology</h2>
    <div class="layers" id="layers" aria-live="polite"></div>
    <div class="footer"><span id="stackStatus">stack: —</span><span>click a layer to inspect its contract</span></div>
  </section>

  <aside class="panel detail" id="detail">
    <h2>Layer inspector</h2>
    <div class="layer-id" id="detailId">L0</div>
    <h3 id="detailName">particle</h3>
    <p id="detailPurpose">Loading layer data…</p>
    <div class="tags" id="deps"></div>
    <h2>Invariants</h2>
    <ul id="invariants"></ul>
    <h2>Capability risk</h2>
    <div id="riskBars"></div>
  </aside>
</div>
</main>

<script>
(() => {
  const root = document;
  let timer = null;
  let paused = false;
  let selected = 0;
  let state = null;

  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  const byId = id => root.getElementById(id);

  function renderRisk(data) {
    const host = byId("riskBars");
    host.innerHTML = "";
    ["low","medium","high"].forEach(risk => {
      const row = data.capabilities.by_risk[risk];
      const pct = row.total ? Math.round((row.enabled / row.total) * 100) : 0;
      const wrap = document.createElement("div");
      wrap.className = "capbar";
      wrap.innerHTML = '<div class="capbar-head"><span>'+esc(risk.toUpperCase())+'</span><span>'+row.enabled+' / '+row.total+'</span></div><div class="track"><div class="fill" style="width:'+pct+'%"></div></div>';
      host.appendChild(wrap);
    });
  }

  function inspect(layer) {
    selected = layer.id;
    byId("detailId").textContent = "L" + layer.id;
    byId("detailName").textContent = layer.name;
    byId("detailPurpose").textContent = layer.purpose;
    const deps = byId("deps");
    deps.innerHTML = "";
    (layer.dependencies.length ? layer.dependencies : ["root"]).forEach(dep => {
      const tag = document.createElement("span");
      tag.className = "tag";
      tag.textContent = "dep: " + dep;
      deps.appendChild(tag);
    });
    const inv = byId("invariants");
    inv.innerHTML = "";
    layer.invariants.forEach(item => {
      const li = document.createElement("li");
      li.textContent = item;
      inv.appendChild(li);
    });
    root.querySelectorAll(".layer").forEach(el => el.classList.toggle("selected", Number(el.dataset.id) === selected));
  }

  function renderLayers(data) {
    const host = byId("layers");
    host.innerHTML = "";
    data.atomic.layers.forEach(layer => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "layer";
      button.dataset.id = layer.id;
      button.setAttribute("aria-label", "Inspect layer " + layer.id + " " + layer.name);
      const metrics = layer.metrics.map(m => '<div class="metric-row"><span>'+esc(m.label)+'</span><strong>'+esc(m.value)+'</strong></div>').join("");
      button.innerHTML = '<div class="id">L'+layer.id+'</div><div class="name">'+esc(layer.name)+'</div><div class="purpose">'+esc(layer.purpose)+'</div>'+metrics;
      button.addEventListener("click", () => inspect(layer));
      host.appendChild(button);
    });
    inspect(data.atomic.layers.find(l => l.id === selected) || data.atomic.layers[0]);
  }

  function render(data) {
    state = data;
    byId("heartbeat").textContent = data.heartbeat.status.toUpperCase();
    byId("agents").textContent = data.runtime.agent_capacity;
    byId("caps").textContent = data.capabilities.enabled + "/" + data.capabilities.total;
    byId("fanout").textContent = data.runtime.max_fanout;
    byId("depth").textContent = data.runtime.max_depth;
    byId("endpoints").textContent = data.runtime.authorized_endpoint_count;
    byId("stackStatus").textContent = "stack: " + (data.atomic.valid ? "VALID" : "INVALID") + " · " + data.atomic.layer_count + " layers";
    byId("stackStatus").className = data.atomic.valid ? "" : "error";
    byId("pulse").style.background = data.heartbeat.status === "alive" ? "var(--good)" : "var(--warn)";
    byId("updated").textContent = "updated " + new Date(data.heartbeat.timestamp).toLocaleTimeString();
    renderLayers(data);
    renderRisk(data);
  }

  async function refresh() {
    try {
      const response = await fetch("/visual/data", {cache:"no-store"});
      if (!response.ok) throw new Error("HTTP " + response.status);
      render(await response.json());
    } catch (error) {
      byId("updated").textContent = "telemetry error: " + error.message;
      byId("updated").classList.add("error");
    }
  }

  byId("refresh").addEventListener("click", refresh);
  byId("toggle").addEventListener("click", () => {
    paused = !paused;
    byId("toggle").textContent = paused ? "Resume live" : "Pause live";
    if (!paused) refresh();
  });

  timer = setInterval(() => { if (!paused) refresh(); }, 3000);
  window.addEventListener("pagehide", () => clearInterval(timer), {once:true});
  refresh();
})();
</script>
</body>
</html>"""


