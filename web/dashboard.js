const rowsEl = document.getElementById("rows");
const statsEl = document.getElementById("stats");
const emptyEl = document.getElementById("empty");

function fmtUptime(s) {
  if (s == null) return "—";
  if (s < 60) return `${Math.round(s)}s`;
  if (s < 3600) return `${Math.round(s / 60)}m`;
  return `${(s / 3600).toFixed(1)}h`;
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    ...opts,
    headers: { ...(opts.headers || {}), "X-Doug-Client": "dashboard" },
  });
  return res.json();
}

async function refresh() {
  let data;
  try {
    data = await api("/api/dashboard");
  } catch {
    return;
  }

  const running = data.projects.filter(p => p.running).length;
  statsEl.innerHTML = `
    <div class="stat-card"><div class="label">Projects</div><div class="value">${data.projects.length}</div></div>
    <div class="stat-card"><div class="label">Running</div><div class="value">${running}</div></div>
    <div class="stat-card"><div class="label">Server uptime</div><div class="value">${fmtUptime(data.server_uptime_s)}</div></div>
    <div class="stat-card"><div class="label">Ollama</div><div class="value">${data.ollama?.ollama_reachable ? "online" : "offline"}</div></div>
  `;

  if (!data.projects.length) {
    emptyEl.hidden = false;
    rowsEl.innerHTML = "";
    return;
  }
  emptyEl.hidden = true;

  rowsEl.innerHTML = data.projects.map(p => {
    const r = p.running;
    const status = r && r.alive ? `<span class="badge running">running</span>` : `<span class="badge stopped">stopped</span>`;
    const toggle = r && r.alive
      ? `<button data-name="${p.name}" data-action="stop">Stop</button>`
      : `<button data-name="${p.name}" data-action="start">Start</button>`;
    return `
      <tr>
        <td>${p.name}</td>
        <td>${p.file_count}</td>
        <td>${status}</td>
        <td>${r ? r.port : "—"}</td>
        <td>${r ? r.pid : "—"}</td>
        <td>${r ? fmtUptime(r.uptime_s) : "—"}</td>
        <td class="actions">
          ${toggle}
          <button data-name="${p.name}" data-action="logs">Logs</button>
        </td>
      </tr>`;
  }).join("");
}

rowsEl.addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-action]");
  if (!btn) return;
  const { name, action } = btn.dataset;

  if (action === "start") {
    await api(`/api/projects/${encodeURIComponent(name)}/start`, { method: "POST" });
  } else if (action === "stop") {
    await api(`/api/projects/${encodeURIComponent(name)}/stop`, { method: "POST" });
  } else if (action === "logs") {
    const status = await api(`/api/projects/${encodeURIComponent(name)}/status`);
    alert((status.logs || []).slice(-40).join("\n") || "no logs yet");
    return;
  }
  refresh();
});

function escapeHtml(s) {
  return (s || "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

async function refreshPaidTasks() {
  const data = await api("/api/paid-tasks/all");
  const tasks = data.tasks || [];
  const paidRowsEl = document.getElementById("paidRows");
  const paidEmptyEl = document.getElementById("paidEmpty");

  if (!tasks.length) {
    paidEmptyEl.hidden = false;
    paidRowsEl.innerHTML = "";
    return;
  }
  paidEmptyEl.hidden = true;

  paidRowsEl.innerHTML = tasks.map(t => {
    const when = new Date(t.created_at * 1000).toLocaleString();
    const resultPreview = t.status === "done" ? escapeHtml((t.result || "").slice(0, 80)) + "..." : "—";
    return `
      <tr>
        <td>${when}</td>
        <td>${escapeHtml(t.task)}</td>
        <td><span class="badge ${t.status === 'done' ? 'running' : 'stopped'}">${t.status}</span></td>
        <td>${resultPreview}</td>
      </tr>`;
  }).join("");
}

refresh();
refreshPaidTasks();
setInterval(refresh, 3000);
setInterval(refreshPaidTasks, 5000);
