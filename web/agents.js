const form = document.getElementById("taskForm");
const stagesEl = document.getElementById("stages");
const statusEl = document.getElementById("jobStatus");
const reviewEl = document.getElementById("reviewBox");
const saveIdeaBox = document.getElementById("saveIdeaBox");

let pollTimer = null;
let currentTask = null;
let currentRunId = null;

document.querySelectorAll(".tab-btn[data-tab]").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn[data-tab]").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
    if (btn.dataset.tab === "history") loadHistory();
    if (btn.dataset.tab === "ideas") loadIdeas();
  });
});

let acctMode = "login";
document.querySelectorAll(".tab-btn[data-acct-tab]").forEach(btn => {
  btn.addEventListener("click", () => {
    acctMode = btn.dataset.acctTab;
    document.querySelectorAll(".tab-btn[data-acct-tab]").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("acctSubmit").textContent = acctMode === "login" ? "Log in" : "Sign up";
  });
});

document.getElementById("accountForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errEl = document.getElementById("acctError");
  errEl.hidden = true;
  const username = document.getElementById("acctUsername").value.trim();
  const password = document.getElementById("acctPassword").value;
  try {
    await api(acctMode === "login" ? "/api/users/login" : "/api/users/signup", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    await loadWhoami();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.hidden = false;
  }
});

async function loadWhoami() {
  const { username } = await api("/api/users/me");
  const el = document.getElementById("whoami");
  const box = document.getElementById("accountBox");
  if (username) {
    el.textContent = `@${username}`;
    box.hidden = true;
  } else {
    el.textContent = "";
    box.hidden = false;
  }
}
loadWhoami();

async function loadWorkerStatus() {
  try {
    const s = await api("/api/worker/status");
    const el = document.getElementById("workerStatus");
    const lastTick = s.last_tick_at ? new Date(s.last_tick_at * 1000).toLocaleTimeString() : "never";
    el.textContent = s.current_idea_id
      ? `Processing idea ${s.current_idea_id}... (${s.processed_count} done so far)`
      : `Idle, watching for draft ideas. Processed: ${s.processed_count}. Last check: ${lastTick}.`;
  } catch {
    // worker status is best-effort UI chrome, not worth surfacing an error for
  }
}
loadWorkerStatus();
setInterval(loadWorkerStatus, 10000);

function escapeHtml(s) {
  return (s || "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

async function loadHistory() {
  const { runs } = await api("/api/agents/runs");
  const el = document.getElementById("historyList");
  el.innerHTML = runs.length ? runs.map(r => `
    <div class="stage-card history-item">
      <div>
        <div class="model">${r.passed === true ? "✓ passed" : r.passed === false ? "✗ failed" : "unreviewed"} · ${r.duration_s || "?"}s</div>
        <div class="out">${escapeHtml(r.task)}</div>
      </div>
    </div>`).join("") : `<div class="stage-card">No runs yet.</div>`;
}

async function loadIdeas() {
  const { ideas: list } = await api("/api/ideas");
  const el = document.getElementById("ideasList");
  el.innerHTML = list.length ? list.map(i => `
    <div class="stage-card idea-item">
      <div>
        <div class="model">${escapeHtml(i.title)} · @${escapeHtml(i.owner)}</div>
        <div class="out">${escapeHtml(i.task)}</div>
      </div>
      <div>
        <span class="status ${i.status}">${i.status}</span>
        ${i.status === "draft" ? `<button data-id="${i.id}" data-ship="1">Ship it</button>` : ""}
      </div>
    </div>`).join("") : `<div class="stage-card">No ideas saved yet.</div>`;

  el.querySelectorAll("button[data-ship]").forEach(btn => {
    btn.addEventListener("click", async () => {
      await api(`/api/ideas/${btn.dataset.id}/status`, { method: "POST", body: JSON.stringify({ status: "shipped" }) });
      loadIdeas();
    });
  });
}

document.getElementById("saveIdeaForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const title = document.getElementById("ideaTitle").value.trim();
  if (!currentRunId) return;
  await api("/api/ideas", { method: "POST", body: JSON.stringify({ run_id: currentRunId, title }) });
  saveIdeaBox.hidden = true;
  document.getElementById("ideaTitle").value = "";
});

async function api(path, opts = {}) {
  const res = await fetch(path, {
    ...opts,
    headers: { "Content-Type": "application/json", "X-Doug-Client": "agents", ...(opts.headers || {}) },
  });
  const body = await res.json();
  if (!res.ok && res.status !== 202) throw new Error(body.error || "request failed");
  return body;
}

function renderEvents(events) {
  stagesEl.innerHTML = events.map(e => {
    if (e.stage === "plan_done") {
      return `<div class="stage-card"><div class="model">Planner · ${e.model}</div><div class="out">${escapeHtml(e.output)}</div></div>`;
    }
    if (e.stage === "execute_done") {
      return `<div class="stage-card"><div class="model">Executor step ${e.step_index} · ${e.model}</div><div class="out"><strong>${escapeHtml(e.step)}</strong>\n\n${escapeHtml(e.output)}</div></div>`;
    }
    if (e.stage === "execute_start") {
      return `<div class="stage-card"><div class="model">Executor step ${e.step_index} · ${e.model} — running...</div></div>`;
    }
    if (e.stage === "plan_start") {
      return `<div class="stage-card"><div class="model">Planner · ${e.model} — running...</div></div>`;
    }
    if (e.stage === "review_start") {
      return `<div class="stage-card"><div class="model">Reviewer · ${e.model} — running...</div></div>`;
    }
    return "";
  }).join("");
}

function renderReview(review) {
  if (!review) return;
  reviewEl.hidden = false;
  reviewEl.className = review.passed ? "pass" : "fail";
  reviewEl.innerHTML = `
    <div class="model">Review verdict: ${review.passed === true ? "PASSED" : review.passed === false ? "FAILED" : "UNKNOWN"}</div>
    <div class="out">${escapeHtml(review.summary || "")}</div>
    ${(review.issues || []).length ? `<ul>${review.issues.map(i => `<li>${escapeHtml(i)}</li>`).join("")}</ul>` : ""}
  `;
}

async function poll(jobId) {
  const job = await api(`/api/agents/run/${jobId}`);
  renderEvents(job.events || []);

  if (job.status === "running") {
    statusEl.innerHTML = `<span class="status-pill running">running</span>`;
    pollTimer = setTimeout(() => poll(jobId), 1500);
  } else if (job.status === "done") {
    statusEl.innerHTML = `<span class="status-pill done">done in ${job.trace.duration_s}s</span>`;
    renderReview(job.trace.review);
    currentRunId = job.trace.run_id;
    saveIdeaBox.hidden = false;
  } else if (job.status === "error") {
    statusEl.innerHTML = `<span class="status-pill error">error</span>`;
    stagesEl.innerHTML += `<div class="stage-card">${escapeHtml(job.error)}</div>`;
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (pollTimer) clearTimeout(pollTimer);
  reviewEl.hidden = true;
  saveIdeaBox.hidden = true;
  currentRunId = null;
  stagesEl.innerHTML = "";
  const task = document.getElementById("taskInput").value.trim();
  try {
    const res = await api("/api/agents/run", { method: "POST", body: JSON.stringify({ task }) });
    statusEl.innerHTML = `<span class="status-pill running">starting...</span>`;
    poll(res.job_id);
  } catch (err) {
    statusEl.innerHTML = `<span class="status-pill error">${escapeHtml(err.message)}</span>`;
  }
});
