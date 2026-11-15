/* CL1-AURA / ECO-SHAGGOTH: local-only clickable spatial client.
 * No dependencies, external requests, credentials, transactions or shell actions.
 */
(function () {
  "use strict";
  const byId = (id) => document.getElementById(id);
  const canvas = byId("world");
  const ctx = canvas.getContext("2d");
  const layers = byId("layers");
  const telemetry = byId("telemetry");
  const inspector = byId("connections");
  const search = byId("find");
  const colors = {
    CORE: "#b4ffdf", DEFENSE: "#bbacf4", INTELLIGENCE: "#d9c18a",
    MUSIC: "#91deea", FINANCE: "#d9a19c", INFRA: "#8dd6c9"
  };
  const state = {
    graph: null, health: {}, selected: "shaggoth", layer: "ALL",
    yaw: 0.12, pitch: 0.26, zoom: 1, panX: 0, panY: 0,
    points: [], dragging: null, showLabels: true, frame: 0,
    w: 600, h: 500
  };
  const clamp = (v, low, high) => Math.max(low, Math.min(high, v));

  function notify(message) {
    byId("hint").textContent = message;
  }

  function resize() {
    const box = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    state.w = Math.max(10, box.width);
    state.h = Math.max(10, box.height);
    canvas.width = Math.floor(state.w * dpr);
    canvas.height = Math.floor(state.h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function projected(node) {
    const v = node.xyz;
    const yaw = state.yaw, pitch = state.pitch;
    const xx = v[0] * Math.cos(yaw) - v[2] * Math.sin(yaw);
    const zz = v[0] * Math.sin(yaw) + v[2] * Math.cos(yaw);
    const yy = v[1] * Math.cos(pitch) - zz * Math.sin(pitch);
    const depth = v[1] * Math.sin(pitch) + zz * Math.cos(pitch);
    const scale = Math.min(state.w / 18.4, state.h / 12.0) * state.zoom;
    const perspective = 1 / Math.max(0.7, 1 + depth * 0.018);
    return {
      x: state.w / 2 + state.panX + xx * scale * perspective,
      y: state.h / 2 + state.panY - yy * scale * 0.72 * perspective,
      depth: depth
    };
  }

  function visible(node) {
    return state.layer === "ALL" || node.layer === state.layer;
  }

  function drawStars() {
    ctx.fillStyle = "rgba(132,197,189,0.15)";
    for (let i = 0; i < 115; i++) {
      const x = ((i * 3137 + 227) % 991) / 991 * state.w;
      const y = ((i * 931 + 41) % 811) / 811 * state.h;
      const pulse = 0.25 + 0.3 * Math.sin(state.frame / 36 + i);
      ctx.globalAlpha = pulse;
      ctx.fillRect(x, y, 1.3, 1.3);
    }
    ctx.globalAlpha = 1;
  }

  function drawShaggoth(core) {
    if (!core) return;
    ctx.save();
    ctx.globalCompositeOperation = "screen";
    for (let arm = 0; arm < 11; arm++) {
      const phase = arm * Math.PI * 2 / 11;
      ctx.beginPath();
      for (let i = 0; i <= 38; i++) {
        const t = i / 38;
        const r = t * (18 + 41 * state.zoom);
        const angle = phase + 0.32 * Math.sin(state.frame * 0.018 + t * 5 + arm);
        const x = core.x + Math.cos(angle) * r;
        const y = core.y + Math.sin(angle) * r * 0.62;
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.strokeStyle = arm % 3 === 0 ? "rgba(200,182,255,0.27)" : "rgba(129,250,209,0.21)";
      ctx.lineWidth = 1.6;
      ctx.stroke();
    }
    const gradient = ctx.createRadialGradient(core.x, core.y, 2, core.x, core.y, 66);
    gradient.addColorStop(0, "rgba(153,255,223,0.27)");
    gradient.addColorStop(0.4, "rgba(89,224,188,0.10)");
    gradient.addColorStop(1, "rgba(89,224,188,0)");
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(core.x, core.y, 66, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  function draw() {
    if (!state.graph || !ctx) return;
    const w = state.w, h = state.h;
    ctx.clearRect(0, 0, w, h);
    drawStars();
    state.points = state.graph.nodes.filter(visible).map(function (node) {
      return Object.assign({ node: node }, projected(node));
    });
    const lookup = new Map(state.points.map(function (point) { return [point.node.id, point]; }));
    const core = lookup.get("shaggoth");
    drawShaggoth(core);

    for (const edge of state.graph.edges) {
      const a = lookup.get(edge.source), b = lookup.get(edge.target);
      if (!a || !b) continue;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.lineWidth = 1;
      ctx.strokeStyle = "rgba(127,190,178,0.23)";
      ctx.stroke();
      const phase = ((state.frame * 0.004 + edge.source.length * 0.12 + edge.target.length * 0.07) % 1);
      const px = a.x + (b.x - a.x) * phase;
      const py = a.y + (b.y - a.y) * phase;
      ctx.fillStyle = "rgba(164,254,214,0.68)";
      ctx.beginPath(); ctx.arc(px, py, 2.1, 0, 2 * Math.PI); ctx.fill();
    }

    for (const point of state.points.slice().sort(function (a, b) { return b.depth - a.depth; })) {
      const node = point.node;
      const selected = node.id === state.selected;
      const color = colors[node.layer] || "#9aced1";
      ctx.beginPath();
      ctx.arc(point.x, point.y, selected ? 9 : 5.5, 0, Math.PI * 2);
      ctx.strokeStyle = selected ? "#edfff8" : color;
      ctx.lineWidth = selected ? 2 : 1.1;
      ctx.shadowColor = color;
      ctx.shadowBlur = selected ? 22 : 11;
      ctx.stroke();
      ctx.shadowBlur = 0;
      ctx.beginPath();
      ctx.arc(point.x, point.y, selected ? 3.6 : 2.7, 0, Math.PI * 2);
      ctx.fillStyle = selected ? "#f3fff8" : color;
      ctx.fill();
      if (state.showLabels) {
        const name = node.short || node.name;
        ctx.font = selected ? "bold 12px Menlo, monospace" : "11px Menlo, monospace";
        const width = ctx.measureText(name).width + 18;
        point.labelWidth = width;
        ctx.fillStyle = selected ? "rgba(14,35,31,0.95)" : "rgba(9,22,22,0.78)";
        ctx.fillRect(point.x + 10, point.y - 12, width, 24);
        ctx.fillStyle = selected ? "#e7fffb" : color;
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";
        ctx.fillText(name, point.x + 18, point.y + 0.2);
      } else point.labelWidth = 0;
    }
    byId("coords").textContent = "YAW " + Math.round(state.yaw * 180 / Math.PI) +
      "° / TILT " + Math.round(state.pitch * 180 / Math.PI) +
      "° / ZOOM " + state.zoom.toFixed(2);
    state.frame++;
    requestAnimationFrame(draw);
  }

  function renderLayers() {
    layers.replaceChildren();
    const options = ["ALL"].concat(Array.from(new Set(state.graph.nodes.map(function (n) {return n.layer;}))));
    for (const layer of options) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = layer === state.layer ? "active" : "";
      const title = document.createElement("span");
      title.textContent = (layer === state.layer ? "◆ " : "  ") + layer;
      const count = document.createElement("small");
      count.textContent = layer === "ALL" ? state.graph.nodes.length :
        state.graph.nodes.filter(function (n) { return n.layer === layer; }).length;
      button.append(title, count);
      button.addEventListener("click", function () {
        state.layer = layer;
        const selected = state.graph.nodes.find(function (n) { return n.id === state.selected; });
        if (selected && layer !== "ALL" && selected.layer !== layer) {
          const first = state.graph.nodes.find(function (n) { return n.layer === layer; });
          if (first) state.selected = first.id;
        }
        renderLayers(); renderInspector(); notify("Layer filter: " + layer);
      });
      layers.appendChild(button);
    }
  }

  function selectNode(id) {
    if (!state.graph.nodes.some(function (node) {return node.id === id;})) return;
    state.selected = id;
    const selected = state.graph.nodes.find(function (n) { return n.id === id; });
    if (state.layer !== "ALL" && selected.layer !== state.layer) {
      state.layer = "ALL";
      renderLayers();
    }
    renderInspector();
    notify("Inspecting " + selected.name + " — topology, not an active service assertion.");
  }

  function renderInspector() {
    const node = state.graph.nodes.find(function (n) {return n.id === state.selected;});
    if (!node) return;
    byId("nodeName").textContent = node.name;
    byId("nodeLayer").textContent = node.layer;
    byId("nodeStatus").textContent = state.health[node.id] || "MAPPED";
    byId("nodeKind").textContent = node.kind;
    byId("nodeSource").textContent = node.source || "Repository ontology";
    byId("nodeDetails").textContent = node.details ||
      "Architectural node; status depends on independently running local services.";
    byId("selection").textContent = "◉ " + node.name;
    inspector.replaceChildren();
    const edges = state.graph.edges.filter(function (e) {
      return e.source === node.id || e.target === node.id;
    });
    for (const edge of edges) {
      const other = edge.source === node.id ? edge.target : edge.source;
      const next = state.graph.nodes.find(function (n) { return n.id === other; });
      if (!next) continue;
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = (next.short || next.name) + "  /  " + edge.relation;
      button.addEventListener("click", function () { selectNode(next.id); });
      inspector.appendChild(button);
    }
  }

  function renderTelemetry() {
    telemetry.replaceChildren();
    for (const id of ["ollama", "cl1", "jukebox", "nexus", "bank", "vault"]) {
      const node = state.graph.nodes.find(function (n) { return n.id === id; });
      if (!node) continue;
      const button = document.createElement("button");
      button.type = "button";
      const name = document.createElement("span");
      name.textContent = node.short || node.name;
      const status = document.createElement("span");
      const value = state.health[id] || "UNTESTED";
      status.textContent = value;
      status.className = value === "LISTENING" ? "up" :
        value === "OFFLINE" ? "off" : "other";
      button.append(name, status);
      button.addEventListener("click", function () { selectNode(id); });
      telemetry.appendChild(button);
    }
  }

  async function refreshStatus() {
    try {
      const response = await fetch("/api/status", {cache:"no-store", credentials:"omit"});
      if (!response.ok) throw new Error("status not available");
      const packet = await response.json();
      state.health = packet.health || {};
      byId("systemStatus").textContent = "LOCAL TELEMETRY ACTIVE";
      renderTelemetry();
      renderInspector();
    } catch (_) {
      byId("systemStatus").textContent = "LOCAL STATUS UNAVAILABLE";
    }
  }

  function canvasPoint(event) {
    const bounds = canvas.getBoundingClientRect();
    return {x:event.clientX - bounds.left, y:event.clientY - bounds.top};
  }

  function findPoint(x, y) {
    let match = null;
    let best = Infinity;
    for (const point of state.points) {
      const dx = x - point.x, dy = Math.abs(y - point.y);
      const radius = Math.hypot(dx, y-point.y);
      const inLabel = state.showLabels && dx >= 8 && dx <= 12 + (point.labelWidth || 0) &&
        dy < 13;
      if ((radius < 21 || inLabel) && radius < best) {
        best = radius; match = point.node;
      }
    }
    return match;
  }

  function onPointerDown(e) {
    if (e.button !== 0) return;
    const p = canvasPoint(e);
    state.dragging = {x:p.x, y:p.y, moved:false};
    canvas.setPointerCapture(e.pointerId);
    const node = findPoint(p.x, p.y);
    if (node) selectNode(node.id);
    canvas.focus();
  }

  function onPointerMove(e) {
    if (!state.dragging) return;
    const p = canvasPoint(e);
    const dx = p.x - state.dragging.x, dy = p.y - state.dragging.y;
    if (Math.abs(dx) + Math.abs(dy) > 1) {
      state.yaw += dx * 0.008;
      state.pitch = clamp(state.pitch - dy * 0.006, -1.2, 1.2);
      state.dragging.moved = true;
      state.dragging.x = p.x; state.dragging.y = p.y;
    }
  }

  function onPointerUp() {
    state.dragging = null;
  }

  function control(action) {
    if (action === "rotate-left") state.yaw -= 0.20;
    else if (action === "rotate-right") state.yaw += 0.20;
    else if (action === "zoom-in") state.zoom = clamp(state.zoom * 1.18, 0.45, 3);
    else if (action === "zoom-out") state.zoom = clamp(state.zoom / 1.18, 0.45, 3);
    else if (action === "reset") {
      state.yaw = 0.12; state.pitch = 0.26; state.zoom = 1;
      state.panX = 0; state.panY = 0; state.layer = "ALL";
      renderLayers();
    }
    else if (action === "scan") refreshStatus();
    else if (action === "toggle-labels") state.showLabels = !state.showLabels;
  }

  canvas.addEventListener("pointerdown", onPointerDown);
  canvas.addEventListener("pointermove", onPointerMove);
  canvas.addEventListener("pointerup", onPointerUp);
  canvas.addEventListener("pointercancel", onPointerUp);
  canvas.addEventListener("wheel", function (e) {
    e.preventDefault();
    state.zoom = clamp(state.zoom * (e.deltaY < 0 ? 1.09 : 0.92), 0.45, 3);
  }, {passive:false});
  canvas.addEventListener("keydown", function (e) {
    const actions = {
      ArrowLeft:"rotate-left", ArrowRight:"rotate-right",
      "+":"zoom-in", "=":"zoom-in", "-":"zoom-out",
      r:"scan", R:"scan"
    };
    if (actions[e.key]) {
      e.preventDefault(); control(actions[e.key]);
    }
  });
  document.querySelectorAll("[data-action]").forEach(function (button) {
    button.addEventListener("click", function () {control(button.dataset.action);});
  });
  search.addEventListener("input", function () {
    if (!state.graph) return;
    const value = search.value.trim().toLowerCase();
    if (!value) return;
    const node = state.graph.nodes.find(function (n) {
      return n.name.toLowerCase().includes(value) || n.id.includes(value);
    });
    if (node) selectNode(node.id);
  });

  async function init() {
    if (!ctx) {
      notify("Canvas unavailable in this browser.");
      return;
    }
    try {
      const response = await fetch("/api/topology", {cache:"no-store", credentials:"omit"});
      if (!response.ok) throw new Error("topology unavailable");
      state.graph = await response.json();
      if (!Array.isArray(state.graph.nodes) || !Array.isArray(state.graph.edges)) {
        throw new Error("invalid topology");
      }
      resize();
      window.addEventListener("resize", resize);
      renderLayers(); renderInspector(); await refreshStatus();
      byId("worldStats").textContent = state.graph.nodes.length +
        " NODES • " + state.graph.edges.length + " LINKS • LIVE SPATIAL";
      draw();
      setInterval(refreshStatus, 7000);
    } catch (_) {
      byId("systemStatus").textContent = "TOPOLOGY UNAVAILABLE";
      notify("Could not load local CL1-AURA topology; check the server terminal.");
    }
  }

  init();
})();
