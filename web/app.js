(() => {
  "use strict";

  const $ = (sel) => document.querySelector(sel);

  const chatLog = $("#chatLog");
  const composerForm = $("#composerForm");
  const composerInput = $("#composerInput");
  const sendBtn = $("#sendBtn");
  const stopBtn = $("#stopBtn");
  const regenBtn = $("#regenBtn");
  const historyList = $("#historyList");
  const projectList = $("#projectList");
  const newChatBtn = $("#newChatBtn");
  const newProjectForm = $("#newProjectForm");
  const newProjectName = $("#newProjectName");
  const activeProjectLabel = $("#activeProject");
  const runBtn = $("#runBtn");
  const stopProjectBtn = $("#stopProjectBtn");
  const runStatus = $("#runStatus");
  const buildLogs = $("#buildLogs");
  const previewFrame = $("#previewFrame");
  const previewEmpty = $("#previewEmpty");
  const fileListEl = $("#fileList");
  const statusDot = $("#statusDot");
  const connStatus = $("#connStatus");
  const modelSelect = $("#modelSelect");
  const providerPanelDot = $("#providerPanelDot");
  const providerPanelTitle = $("#providerPanelTitle");
  const providerPanelCopy = $("#providerPanelCopy");
  const workerSystemStatus = $("#workerSystemStatus");
  const memorySystemStatus = $("#memorySystemStatus");
  const projectSystemStatus = $("#projectSystemStatus");
  const systemDetail = $("#systemDetail");

  const STORAGE_KEY = "gpt-doug-conversations";
  const MODEL_KEY = "gpt-doug-model";

  let state = {
    conversations: loadConversations(),
    activeConvId: null,
    activeProject: null,
    controller: null, // AbortController for in-flight stream
    lastUserMessage: null,
  };

  function loadConversations() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }

  function saveConversations() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state.conversations));
  }

  function newConversation() {
    const conv = { id: crypto.randomUUID(), title: "New chat", messages: [] };
    state.conversations.unshift(conv);
    state.activeConvId = conv.id;
    saveConversations();
    renderHistory();
    renderChat();
  }

  function activeConv() {
    return state.conversations.find((c) => c.id === state.activeConvId) || null;
  }

  function renderHistory() {
    historyList.innerHTML = "";
    for (const conv of state.conversations) {
      const div = document.createElement("div");
      div.className = "side-item" + (conv.id === state.activeConvId ? " active" : "");
      div.textContent = conv.title || "New chat";
      div.title = conv.title || "New chat";
      div.addEventListener("click", () => {
        state.activeConvId = conv.id;
        renderHistory();
        renderChat();
      });
      historyList.appendChild(div);
    }
  }

  // ---------- chat rendering ----------

  function escapeHtml(s) {
    return s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  }

  function renderMarkdownish(text) {
    // Minimal fenced-code-block rendering; everything else stays plain text.
    const parts = text.split(/```/g);
    let html = "";
    for (let i = 0; i < parts.length; i++) {
      if (i % 2 === 0) {
        html += escapeHtml(parts[i]);
      } else {
        const lines = parts[i].split("\n");
        const first = lines[0];
        const code = lines.slice(1).join("\n");
        html += `<pre><code>${escapeHtml(code || first)}</code></pre>`;
      }
    }
    return html;
  }

  function parseGeneratedFiles(text) {
    // Looks for fenced blocks preceded by a "// filename: path" or "# filename: path" marker,
    // or a markdown heading like "**path/to/file**" right before the fence.
    const files = [];
    const fenceRe = /```[a-zA-Z0-9_-]*\n([\s\S]*?)```/g;
    const lines = text.split("\n");
    let match;
    const fenceStarts = [];
    let idx = 0;
    while ((match = fenceRe.exec(text)) !== null) {
      fenceStarts.push({ start: match.index, content: match[1] });
    }
    const markerRe = /(?:\/\/|#)\s*filename:\s*(\S+)/i;
    for (const fence of fenceStarts) {
      let name = null;
      let content = fence.content;

      // Marker as the first line inside the fence (model sometimes puts it there
      // despite instructions), e.g. ```html\n// filename: index.html\n<...>
      const contentLines = content.split("\n");
      const firstLineMatch = contentLines[0].match(markerRe);
      if (firstLineMatch) {
        name = firstLineMatch[1];
        content = contentLines.slice(1).join("\n").replace(/^\n/, "");
      }

      if (!name) {
        const before = text.slice(0, fence.start);
        const beforeLines = before.trim().split("\n");
        const lastLine = beforeLines[beforeLines.length - 1] || "";
        let m = lastLine.match(markerRe);
        if (m) name = m[1];
        if (!name) {
          m = lastLine.match(/\*\*([\w./-]+\.\w+)\*\*/);
          if (m) name = m[1];
        }
        if (!name) {
          m = lastLine.match(/^`([\w./-]+\.\w+)`$/);
          if (m) name = m[1];
        }
      }

      if (name) {
        files.push({ path: name.replace(/^\/+/, ""), content });
      }
    }
    return files;
  }

  function addMessageEl(role, text, opts = {}) {
    const wrap = document.createElement("div");
    wrap.className = `msg ${role}${opts.error ? " error" : ""}`;
    const roleLabel = document.createElement("div");
    roleLabel.className = "msg-role";
    roleLabel.textContent = role === "user" ? "You" : role === "doug" ? "Doug" : "System";
    const bubble = document.createElement("div");
    bubble.className = "msg-bubble" + (opts.streaming ? " cursor-blink" : "");
    bubble.innerHTML = renderMarkdownish(text || "");
    wrap.appendChild(roleLabel);
    wrap.appendChild(bubble);
    chatLog.appendChild(wrap);
    chatLog.scrollTop = chatLog.scrollHeight;
    return { wrap, bubble };
  }

  function renderChat() {
    chatLog.innerHTML = "";
    const conv = activeConv();
    if (!conv) return;
    if (!conv.messages.length) {
      const welcome = document.createElement("section");
      welcome.className = "welcome-card";
      welcome.innerHTML = `
        <div class="welcome-kicker">SECURE BUILD WORKSPACE</div>
        <h1>What are we building?</h1>
        <p>Chat with a configured provider, or keep working offline with projects, files, previews, logs, memory, tools, and security controls.</p>
        <div class="welcome-capabilities">
          <span>Projects</span><span>Live preview</span><span>Zyra guarded</span><span>Provider-ready</span>
        </div>`;
      chatLog.appendChild(welcome);
    }
    for (const m of conv.messages) {
      const { wrap } = addMessageEl(m.role === "user" ? "user" : "doug", m.content, { error: m.error });
      if (m.role === "assistant") {
        const files = parseGeneratedFiles(m.content);
        if (files.length) attachFileActions(wrap, files);
      }
    }
  }

  function attachFileActions(wrap, files) {
    const row = document.createElement("div");
    row.className = "file-chip-row";
    for (const f of files) {
      const chip = document.createElement("span");
      chip.className = "file-chip";
      chip.textContent = f.path;
      row.appendChild(chip);
    }
    wrap.appendChild(row);

    const btn = document.createElement("button");
    btn.className = "save-files-btn";
    btn.textContent = state.activeProject
      ? `Save ${files.length} file(s) to "${state.activeProject}"`
      : "Create a project first to save these files";
    btn.disabled = !state.activeProject;
    btn.addEventListener("click", () => saveFilesToProject(files, btn));
    wrap.appendChild(btn);
  }

  async function saveFilesToProject(files, btn) {
    if (!state.activeProject) return;
    btn.disabled = true;
    btn.textContent = "Saving...";
    try {
      const res = await fetch(`/api/projects/${encodeURIComponent(state.activeProject)}/files`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Doug-Client": "1" },
        body: JSON.stringify({ files }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "save failed");
      btn.textContent = `Saved ${data.written.length} file(s) ✓`;
      logLine(`Saved ${data.written.length} file(s) to project "${state.activeProject}": ${data.written.join(", ")}`);
      refreshFileList();
      runBtn.disabled = false;
    } catch (err) {
      btn.textContent = "Save failed — retry";
      btn.disabled = false;
      logLine(`ERROR saving files: ${err.message}`);
    }
  }

  // ---------- projects ----------

  async function refreshProjects() {
    try {
      const res = await fetch("/api/projects");
      const data = await res.json();
      projectList.innerHTML = "";
      for (const name of data.projects) {
        const div = document.createElement("div");
        div.className = "side-item" + (name === state.activeProject ? " active" : "");
        div.textContent = name;
        div.addEventListener("click", () => selectProject(name));
        projectList.appendChild(div);
      }
      if (projectSystemStatus) projectSystemStatus.textContent = `${data.projects.length} project${data.projects.length === 1 ? "" : "s"} in workspace`;
    } catch {
      /* ignore */
    }
  }

  function selectProject(name) {
    stopLogPolling();
    state.activeProject = name;
    activeProjectLabel.textContent = `Project: ${name}`;
    runBtn.disabled = false;
    runBtn.textContent = "▶ Run Project";
    stopProjectBtn.hidden = true;
    runStatus.textContent = "";
    runStatus.className = "run-status";
    previewFrame.hidden = true;
    previewEmpty.hidden = false;
    buildLogs.textContent = "";
    refreshProjects();
    refreshFileList();
    switchTab("files");
  }

  async function refreshFileList() {
    if (!state.activeProject) {
      fileListEl.innerHTML = '<div class="empty-state">No files yet.</div>';
      return;
    }
    try {
      const res = await fetch(`/api/projects/${encodeURIComponent(state.activeProject)}/files`);
      const data = await res.json();
      if (!data.files || !data.files.length) {
        fileListEl.innerHTML = '<div class="empty-state">No files yet — ask Doug to build something.</div>';
        return;
      }
      fileListEl.innerHTML = "";
      for (const f of data.files) {
        const row = document.createElement("div");
        row.className = "file-row";
        row.textContent = f;
        fileListEl.appendChild(row);
      }
    } catch {
      /* ignore */
    }
  }

  newProjectForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = newProjectName.value.trim();
    if (!name) return;
    if (!/^[a-zA-Z0-9_-]{1,64}$/.test(name)) {
      logLine("ERROR: project names may only contain letters, numbers, - and _");
      return;
    }
    try {
      const res = await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Doug-Client": "1" },
        body: JSON.stringify({ name }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "failed to create project");
      newProjectName.value = "";
      await refreshProjects();
      selectProject(name);
      logLine(`Created project "${name}"`);
    } catch (err) {
      logLine(`ERROR: ${err.message}`);
    }
  });

  runBtn.addEventListener("click", runProject);
  stopProjectBtn.addEventListener("click", stopProject);

  let logPollTimer = null;
  let knownLogLines = 0;

  function stopLogPolling() {
    if (logPollTimer) clearInterval(logPollTimer);
    logPollTimer = null;
    knownLogLines = 0;
  }

  async function runProject() {
    if (!state.activeProject) return;
    const project = state.activeProject;
    switchTab("logs");
    logLine(`\n$ run "${project}"`);
    runBtn.disabled = true;
    runBtn.textContent = "Starting...";
    try {
      const res = await fetch(`/api/projects/${encodeURIComponent(project)}/start`, {
        method: "POST",
        headers: { "X-Doug-Client": "1" },
      });
      const data = await res.json();

      if (data.ok) {
        // Real server process — point the preview straight at its port.
        logLine(`started ${data.kind || ""} server${data.cmd ? ` (${data.cmd})` : ""} on port ${data.port}`);
        runStatus.textContent = `● running on :${data.port}`;
        runStatus.className = "run-status live";
        stopProjectBtn.hidden = false;
        runBtn.textContent = "Restart";
        startLogPolling(project, data.port);
        // Give the process a moment to actually start listening before loading it.
        setTimeout(() => {
          previewFrame.src = `http://localhost:${data.port}/`;
          previewFrame.hidden = false;
          previewEmpty.hidden = true;
          switchTab("preview");
        }, 900);
      } else {
        // No runnable entry point (package.json/app.py/etc) — fall back to
        // treating it as a static site and serving index.html directly.
        logLine(data.error || "no server entry point found");
        await runStaticFallback(project);
      }
    } catch (err) {
      logLine(`ERROR: ${err.message}`);
    } finally {
      runBtn.disabled = false;
      if (runBtn.textContent === "Starting...") runBtn.textContent = "▶ Run Project";
    }
  }

  async function runStaticFallback(project) {
    logLine(`$ falling back to static preview for "${project}"`);
    try {
      const res = await fetch(`/api/projects/${encodeURIComponent(project)}/run`);
      const data = await res.json();
      for (const line of data.logs) logLine(line);
      if (data.ok && data.preview_url) {
        previewFrame.src = data.preview_url + "?t=" + Date.now();
        previewFrame.hidden = false;
        previewEmpty.hidden = true;
        switchTab("preview");
      } else {
        previewFrame.hidden = true;
        previewEmpty.hidden = false;
      }
    } catch (err) {
      logLine(`ERROR: ${err.message}`);
    }
  }

  function startLogPolling(project, port) {
    stopLogPolling();
    logPollTimer = setInterval(async () => {
      try {
        const res = await fetch(`/api/projects/${encodeURIComponent(project)}/status`);
        const data = await res.json();
        for (let i = knownLogLines; i < data.logs.length; i++) logLine(data.logs[i]);
        knownLogLines = data.logs.length;
        if (!data.running) {
          logLine(`$ process exited`);
          runStatus.textContent = "○ stopped";
          runStatus.className = "run-status";
          stopProjectBtn.hidden = true;
          runBtn.textContent = "▶ Run Project";
          stopLogPolling();
        }
      } catch {
        /* transient — keep polling */
      }
    }, 1500);
  }

  async function stopProject() {
    if (!state.activeProject) return;
    stopProjectBtn.disabled = true;
    try {
      await fetch(`/api/projects/${encodeURIComponent(state.activeProject)}/stop`, {
        method: "POST",
        headers: { "X-Doug-Client": "1" },
      });
      logLine(`$ stopped "${state.activeProject}"`);
      runStatus.textContent = "○ stopped";
      runStatus.className = "run-status";
      stopProjectBtn.hidden = true;
      runBtn.textContent = "▶ Run Project";
      stopLogPolling();
    } catch (err) {
      logLine(`ERROR stopping: ${err.message}`);
    } finally {
      stopProjectBtn.disabled = false;
    }
  }

  function logLine(line) {
    buildLogs.textContent += (buildLogs.textContent ? "\n" : "") + line;
    buildLogs.scrollTop = buildLogs.scrollHeight;
  }

  // ---------- tabs ----------

  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  function switchTab(name) {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
    document.querySelectorAll(".tab-pane").forEach((p) => p.classList.toggle("active", p.id === `tab-${name}`));
  }

  // ---------- streaming chat ----------

  composerForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = composerInput.value.trim();
    if (!text) return;
    composerInput.value = "";
    autoGrow();
    sendMessage(text);
  });

  composerInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      composerForm.requestSubmit();
    }
  });
  composerInput.addEventListener("input", autoGrow);
  function autoGrow() {
    composerInput.style.height = "auto";
    composerInput.style.height = Math.min(composerInput.scrollHeight, 160) + "px";
  }

  stopBtn.addEventListener("click", () => {
    if (state.controller) state.controller.abort();
  });

  regenBtn.addEventListener("click", () => {
    if (!state.lastUserMessage) return;
    const conv = activeConv();
    if (!conv) return;
    // Drop the last assistant message (and any trailing error) before regenerating.
    while (conv.messages.length && conv.messages[conv.messages.length - 1].role !== "user") {
      conv.messages.pop();
    }
    renderChat();
    streamAssistantReply(conv);
  });

  async function sendMessage(text) {
    if (!state.activeConvId) newConversation();
    const conv = activeConv();
    conv.messages.push({ role: "user", content: text });
    if (conv.title === "New chat") conv.title = text.slice(0, 40);
    state.lastUserMessage = text;
    saveConversations();
    renderHistory();
    addMessageEl("user", text);
    await streamAssistantReply(conv);
  }

  async function streamAssistantReply(conv) {
    setBusy(true);
    const { wrap, bubble } = addMessageEl("doug", "", { streaming: true });
    let full = "";
    const controller = new AbortController();
    state.controller = controller;

    try {
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Doug-Client": "1" },
        signal: controller.signal,
        body: JSON.stringify({
          messages: conv.messages.map(({ role, content }) => ({ role, content })),
          model: modelSelect.value || undefined,
        }),
      });
      if (!res.ok || !res.body) {
        throw new Error(`server responded ${res.status}`);
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const chunks = buf.split("\n\n");
        buf = chunks.pop();
        for (const chunk of chunks) {
          const line = chunk.trim();
          if (!line.startsWith("data:")) continue;
          const jsonStr = line.slice(5).trim();
          if (!jsonStr) continue;
          let evt;
          try {
            evt = JSON.parse(jsonStr);
          } catch {
            continue;
          }
          if (evt.error && evt.error !== "provider_not_configured") {
            throw new Error(evt.error);
          }
          const token = evt.message && evt.message.content ? evt.message.content : "";
          if (token) {
            full += token;
            bubble.innerHTML = renderMarkdownish(full) + '<span class="cursor-blink"></span>';
            chatLog.scrollTop = chatLog.scrollHeight;
          }
          if (evt.error === "provider_not_configured") {
            wrap.classList.add("offline-message");
          }
        }
      }
      bubble.innerHTML = renderMarkdownish(full);
      conv.messages.push({ role: "assistant", content: full });
      saveConversations();
      let files = parseGeneratedFiles(full);

      // GPT-Doug local models sometimes forget filename markers.
      // Infer common project filenames so Build Mode can still materialize
      // the application instead of leaving code trapped in chat.
      if (!files.length) {
        const blocks = [...full.matchAll(/```([a-zA-Z0-9_-]*)\\n([\\s\\S]*?)```/g)];

        files = blocks.map((m, i) => {
          const lang = (m[1] || "").toLowerCase();
          const body = m[2];

          let path = null;

          if (
            lang === "json" &&
            body.includes('"scripts"') &&
            body.includes('"name"')
          ) {
            path = "package.json";
          } else if (
            lang === "html" ||
            /<!doctype html|<html/i.test(body)
          ) {
            path = "index.html";
          } else if (lang === "css") {
            path = "style.css";
          } else if (
            ["javascript", "js"].includes(lang)
          ) {
            path = "script.js";
          } else if (
            ["typescript", "ts"].includes(lang)
          ) {
            path = "src/index.ts";
          } else if (
            ["jsx", "tsx"].includes(lang)
          ) {
            path = lang === "tsx" ? "src/App.tsx" : "src/App.jsx";
          } else if (lang === "python" || lang === "py") {
            path = "app.py";
          }

          return path ? { path, content: body } : null;
        }).filter(Boolean);
      }

      if (files.length) {
        attachFileActions(wrap, files);

        // BUILD MODE behavior:
        // if a project is selected, immediately materialize the files
        // instead of making the user manually click Save.
        if (state.activeProject) {
          try {
            const res = await fetch(
              `/api/projects/${encodeURIComponent(state.activeProject)}/files`,
              {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                  "X-Doug-Client": "1"
                },
                body: JSON.stringify({ files }),
              }
            );

            const data = await res.json();

            if (res.ok) {
              logLine(
                `AUTO-SAVED ${data.written.length} file(s): ${data.written.join(", ")}`
              );

              await refreshFileList();

              // If we now have something runnable, automatically attempt preview.
              setTimeout(() => runProject(), 300);
            } else {
              logLine(`AUTO-SAVE ERROR: ${data.error || "unknown error"}`);
            }
          } catch (saveErr) {
            logLine(`AUTO-SAVE ERROR: ${saveErr.message}`);
          }
        }
      }
    } catch (err) {
      if (err.name === "AbortError") {
        bubble.innerHTML = renderMarkdownish(full || "(stopped)");
        if (full) conv.messages.push({ role: "assistant", content: full });
        saveConversations();
      } else {
        wrap.classList.add("error");
        bubble.textContent = `Error talking to GPT Doug: ${err.message}`;
        conv.messages.push({ role: "assistant", content: `Error: ${err.message}`, error: true });
        saveConversations();
      }
    } finally {
      state.controller = null;
      setBusy(false);
    }
  }

  function setBusy(busy) {
    sendBtn.disabled = busy;
    stopBtn.hidden = !busy;
    regenBtn.hidden = busy || !state.lastUserMessage;
  }

  // ---------- health check ----------

  async function checkHealth() {
    try {
      const res = await fetch("/api/health");
      const data = await res.json();
      populateModelSelect(data.models || [], data.model);
      const zyra = data.zyra_active ? ` · Zyra ${data.zyra_policy_version} watching` : "";
      if (data.configured && data.model_available) {
        statusDot.className = "dot online";
        connStatus.textContent = `${data.provider} · ${data.model} ready${zyra}`;
      } else if (data.provider === "none") {
        statusDot.className = "dot online";
        connStatus.textContent = `Offline workspace ready${zyra}`;
      } else {
        statusDot.className = "dot offline";
        connStatus.textContent = `${data.provider || "AI provider"} needs configuration${zyra}`;
      }
      if (providerPanelDot) providerPanelDot.className = `dot ${data.provider === "none" || data.configured ? "online" : "offline"}`;
      if (providerPanelTitle) providerPanelTitle.textContent = data.provider === "none" ? "Offline / No AI Provider" : `${data.provider} · ${data.model || "Not configured"}`;
      if (providerPanelCopy) providerPanelCopy.textContent = data.provider === "none" ? "Workspace, memory, tools, projects, and security are available." : data.message;
    } catch {
      statusDot.className = "dot offline";
      connStatus.textContent = "Health check failed";
    }
  }

  async function checkWorkerStatus() {
    if (!workerSystemStatus) return;
    try {
      const res = await fetch("/api/worker/status");
      const data = await res.json();
      workerSystemStatus.textContent = data.running ? `Active · ${data.processed_count || 0} processed` : "Available · disabled by default";
    } catch {
      workerSystemStatus.textContent = "Status unavailable";
    }
    if (memorySystemStatus) memorySystemStatus.textContent = `${state.conversations.length} local conversation${state.conversations.length === 1 ? "" : "s"}`;
  }

  const systemDescriptions = {
    workers: ["Workers · opt-in automation", "Background workers are preserved and currently disabled by default. Enable them deliberately at server startup with <code>GPT_DOUG_ENABLE_WORKER=true</code>."],
    memory: ["Memory · local-first", "Conversation history stays in this browser via localStorage. Project files use the encrypted project store; no external AI provider is required."],
    terminal: ["Terminal · guarded runtime", "The secure terminal remains a local entrypoint protected by GPT Doug’s authentication, compliance, ASTRAL, Golden Shield, and Zyra controls. Launch it from the repository with <code>./gpt-doug</code>."],
    tools: ["Tools · project operations", "File creation, encrypted storage, project preview, process runner, logs, agent history, ontology, and security tools remain available in offline mode."],
  };
  document.querySelectorAll("[data-system]").forEach((card) => {
    card.addEventListener("click", () => {
      const [title, copy] = systemDescriptions[card.dataset.system];
      systemDetail.innerHTML = `<strong>${title}</strong><p>${copy}</p>`;
      document.querySelectorAll("[data-system]").forEach((item) => item.classList.toggle("active", item === card));
    });
  });

  let modelsPopulated = false;
  function populateModelSelect(models, defaultModel) {
    if (modelsPopulated) return;
    modelsPopulated = true;
    const saved = localStorage.getItem(MODEL_KEY);
    modelSelect.innerHTML = "";
    for (const name of (models.length ? models : ["offline"])) {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      modelSelect.appendChild(opt);
    }
    modelSelect.value = saved && models.includes(saved) ? saved : (defaultModel || "offline");
  }
  modelSelect.addEventListener("change", () => {
    localStorage.setItem(MODEL_KEY, modelSelect.value);
  });

  // ---------- init ----------

  newChatBtn.addEventListener("click", newConversation);

  renderHistory();
  if (state.conversations.length) {
    state.activeConvId = state.conversations[0].id;
    renderChat();
  }
  refreshProjects();
  checkHealth();
  checkWorkerStatus();
  setInterval(checkHealth, 15000);
  setInterval(checkWorkerStatus, 15000);
  regenBtn.hidden = true;
  stopBtn.hidden = true;
})();
