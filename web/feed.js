(function () {
  const listEl = document.getElementById("feedList");
  const errEl = document.getElementById("feedError");

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function fmtDate(ts) {
    if (!ts) return "";
    try {
      return new Date(ts * 1000).toLocaleString();
    } catch (e) {
      return "";
    }
  }

  function render(ideas) {
    if (!ideas.length) {
      listEl.innerHTML = '<div class="empty">No shipped ideas yet.</div>';
      return;
    }
    listEl.innerHTML = "";
    for (const idea of ideas) {
      const card = document.createElement("div");
      card.className = "feed-card";
      card.innerHTML = `
        <h2>${escapeHtml(idea.title || "(untitled)")}</h2>
        <div class="meta"><span class="owner">@${escapeHtml(idea.owner || "operator")}</span> &middot; ${escapeHtml(fmtDate(idea.updated_at || idea.created_at))}</div>
        <div class="task">${escapeHtml(idea.task || "")}</div>
        <div class="output">${escapeHtml(idea.output || "")}</div>
        <button class="show-more" type="button">Show more</button>
      `;
      const output = card.querySelector(".output");
      const btn = card.querySelector(".show-more");
      btn.addEventListener("click", () => {
        output.classList.toggle("expanded");
        btn.textContent = output.classList.contains("expanded") ? "Show less" : "Show more";
      });
      listEl.appendChild(card);
    }
  }

  async function load() {
    try {
      const res = await fetch("/api/ideas/feed");
      if (!res.ok) {
        throw new Error("failed to load feed (" + res.status + ")");
      }
      const data = await res.json();
      render(data.ideas || []);
    } catch (e) {
      errEl.textContent = e.message || "failed to load feed";
      errEl.hidden = false;
    }
  }

  load();
})();
