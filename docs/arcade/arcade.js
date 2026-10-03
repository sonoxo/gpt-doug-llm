(() => {
  "use strict";

  const BOUNTIES = {
    "pulse-flight": {
      name: "Pulse Flight", icon: "✦", reward: 25,
      milestone: "pulse-knowledge-lock-v1",
      fn: "task_knowledge",
      task: "Score 50+ and reach a 3-hit streak.",
      description: "Queries Task → referenced → KnowledgeEntry links."
    },
    "grid-drop": {
      name: "Grid Drop", icon: "▦", reward: 50,
      milestone: "grid-snapshot-v1",
      fn: "snapshot",
      task: "Charge all 25 ontology nodes.",
      description: "Persists an auditable ontology snapshot."
    },
    "nova-tycoon": {
      name: "Nova Tycoon", icon: "⚛", reward: 50,
      milestone: "nova-status-v1",
      fn: "status",
      task: "Upgrade the reactor to level 3.",
      description: "Reads live ontology object/link counts."
    },
    "orbit-runner": {
      name: "Orbit Runner", icon: "◎", reward: 50,
      milestone: "orbit-link-traverse-v1",
      fn: "task_result",
      task: "Collect 3 graph stars.",
      description: "Traverses Task → produced → Result links."
    },
    "signal-match": {
      name: "Signal Match", icon: "⌁", reward: 50,
      milestone: "signal-knowledge-audit-v1",
      fn: "knowledge",
      task: "Score 50+ with 3 or fewer misses.",
      description: "Audits KnowledgeEntry objects."
    }
  };

  const STORAGE_KEY = "xunia.arcade.receipts.v1";
  const PLAYER_KEY = "xunia.arcade.player.v1";
  const DAILY_MAX = 225;
  const signals = ["△", "○", "◇", "✦"];
  const gameOrder = Object.keys(BOUNTIES);

  const state = {
    selected: "pulse-flight",
    pulse: { score: 0, streak: 0, streakPeak: 0, target: rnd(1, 8) },
    grid: { cells: Array(25).fill(false) },
    nova: { credits: 0, level: 1 },
    orbit: { player: 24, star: 8, stars: 0 },
    signal: { target: "✦", score: 0, misses: 0 }
  };

  const root = document.getElementById("arcadeApp");
  if (!root) return;

  function rnd(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
  }

  function today() {
    return new Date().toISOString().slice(0, 10);
  }

  function playerId() {
    let id = localStorage.getItem(PLAYER_KEY);
    if (!id) {
      id = `player-${crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2)}`;
      localStorage.setItem(PLAYER_KEY, id);
    }
    return id;
  }

  function receipts() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  function saveReceipts(items) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  }

  function todayReceipts() {
    return receipts().filter(r => (r.created_at || "").slice(0, 10) === today());
  }

  function dailyBalance() {
    return todayReceipts().reduce((sum, r) => sum + Number(r.reward?.amount || 0), 0);
  }

  function lifetimeBalance() {
    return receipts().reduce((sum, r) => sum + Number(r.reward?.amount || 0), 0);
  }

  function alreadyAwarded(gameId) {
    return todayReceipts().some(r => r.game_id === gameId && r.milestone_id === BOUNTIES[gameId].milestone);
  }

  function metricsFor(gameId) {
    if (gameId === "pulse-flight") return { score: state.pulse.score, streak_peak: state.pulse.streakPeak };
    if (gameId === "grid-drop") return { charged: state.grid.cells.filter(Boolean).length };
    if (gameId === "nova-tycoon") return { level: state.nova.level, credits: state.nova.credits };
    if (gameId === "orbit-runner") return { stars: state.orbit.stars };
    return { score: state.signal.score, misses: state.signal.misses };
  }

  function eligible(gameId) {
    const m = metricsFor(gameId);
    if (gameId === "pulse-flight") return m.score >= 50 && m.streak_peak >= 3;
    if (gameId === "grid-drop") return m.charged >= 25;
    if (gameId === "nova-tycoon") return m.level >= 3;
    if (gameId === "orbit-runner") return m.stars >= 3;
    return m.score >= 50 && m.misses <= 3;
  }

  function award(gameId) {
    if (!eligible(gameId) || alreadyAwarded(gameId)) return false;
    const bounty = BOUNTIES[gameId];
    if (dailyBalance() + bounty.reward > DAILY_MAX) return false;

    const receipt = {
      schema_version: "1.0.0",
      object_type: "ArcadeRun",
      receipt_id: `arcade:${today()}:${gameId}:${crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2)}`,
      player_id: playerId(),
      game_id: gameId,
      milestone_id: bounty.milestone,
      metrics: metricsFor(gameId),
      ontology_action: { action_type: "RecordArcadeRun", ecosystem_function: bounty.fn },
      reward: { unit: "XBC", amount: bounty.reward, redeemable: false, cash_value: null },
      created_at: new Date().toISOString(),
      source: "xunia.org/arcade",
      trust_level: "client-attested"
    };

    const all = receipts();
    all.push(receipt);
    saveReceipts(all);
    toast(`BOUNTY AWARDED +${bounty.reward} XBC · ${bounty.name}`);
    return true;
  }

  function toast(message) {
    let node = document.getElementById("arcadeToast");
    if (!node) {
      node = document.createElement("div");
      node.id = "arcadeToast";
      node.className = "arcade-toast";
      document.body.appendChild(node);
    }
    node.textContent = message;
    node.classList.add("show");
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => node.classList.remove("show"), 2800);
  }

  function exportReceipts() {
    const payload = {
      schema_version: "1.0.0",
      export_type: "XUNIAArcadeBountyReceiptBundle",
      player_id: playerId(),
      exported_at: new Date().toISOString(),
      receipts: receipts()
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `xunia-arcade-bounties-${today()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function bountyCard(gameId) {
    const b = BOUNTIES[gameId];
    const done = alreadyAwarded(gameId);
    return `<div class="bounty-card ${done ? "done" : ""}"><div><div class="eyebrow">ONTOLOGY BOUNTY</div><strong>${b.task}</strong><p>${b.description}</p><code>${b.fn}()</code></div><div class="bounty-reward">${done ? "✓" : `+${b.reward}`}<small>${done ? "AWARDED" : "XBC"}</small></div></div>`;
  }

  function gameMenu() {
    return gameOrder.map(id => {
      const b = BOUNTIES[id];
      return `<button class="game-tab ${state.selected === id ? "active" : ""}" data-game="${id}"><span class="game-icon">${b.icon}</span><span><strong>${b.name}</strong><small>${b.task}</small></span><b>${alreadyAwarded(id) ? "✓" : `+${b.reward}`}</b></button>`;
    }).join("");
  }

  function pulseView() {
    const s = state.pulse;
    return `${bountyCard("pulse-flight")}<div class="game-head"><h2>Pulse Flight</h2><span>SCORE ${s.score}</span></div><div class="game-center"><p>TARGET KNOWLEDGE CHANNEL</p><div class="big">${s.target}</div><button class="primary" id="pulseFire">FIRE QUERY</button><p>STREAK ${s.streak} · PEAK ${s.streakPeak}</p></div>`;
  }

  function gridView() {
    const charged = state.grid.cells.filter(Boolean).length;
    return `${bountyCard("grid-drop")}<div class="game-head"><h2>Grid Drop</h2><span>NODES ${charged}/25</span></div><p class="game-help">Activate every node to complete the ontology snapshot graph.</p><div class="grid25">${state.grid.cells.map((on, i) => `<button class="node ${on ? "on" : ""}" data-node="${i}" aria-label="Ontology node ${i + 1}">${on ? "●" : ""}</button>`).join("")}</div><div class="game-center"><button class="secondary" id="gridReset">RESET GRAPH</button></div>`;
  }

  function novaView() {
    const s = state.nova;
    const cost = s.level * 50;
    return `${bountyCard("nova-tycoon")}<div class="game-head"><h2>Nova Tycoon</h2><span>${s.credits} CR</span></div><div class="game-center"><div class="big white">⚛</div><p>ONTOLOGY REACTOR LEVEL ${s.level}</p><button class="primary" id="novaGenerate">GENERATE +${s.level * 10}</button> <button class="secondary" id="novaUpgrade" ${s.credits < cost ? "disabled" : ""}>UPGRADE ${cost} CR</button></div>`;
  }

  function orbitView() {
    const s = state.orbit;
    return `${bountyCard("orbit-runner")}<div class="game-head"><h2>Orbit Runner</h2><span>LINK STARS ${s.stars}</span></div><p class="game-help">Traverse the graph with arrows/WASD or touch controls.</p><div class="orbit">${Array.from({length: 49}, (_, i) => { const cls = i === s.player ? "player" : i === s.star ? "star" : ""; const mark = i === s.player ? "◆" : i === s.star ? "✦" : ""; return `<div class="${cls}">${mark}</div>`; }).join("")}</div><div class="moves"><span></span><button data-move="0,-1">↑</button><span></span><button data-move="-1,0">←</button><button data-move="0,1">↓</button><button data-move="1,0">→</button></div>`;
  }

  function signalView() {
    const s = state.signal;
    return `${bountyCard("signal-match")}<div class="game-head"><h2>Signal Match</h2><span>${s.score} PTS · ${s.misses} MISS</span></div><div class="game-center"><p>CLASSIFY KNOWLEDGE SIGNAL</p><div class="big cyan">${s.target}</div><div class="signals">${signals.map(sig => `<button data-signal="${sig}">${sig}</button>`).join("")}</div></div>`;
  }

  function gameView() {
    const views = { "pulse-flight": pulseView, "grid-drop": gridView, "nova-tycoon": novaView, "orbit-runner": orbitView, "signal-match": signalView };
    return views[state.selected]();
  }

  function ledgerView() {
    const recent = receipts().slice(-5).reverse();
    return `<section class="ledger"><div class="ledger-head"><div><div class="eyebrow">BOUNTY LEDGER</div><h2>${lifetimeBalance()} XBC</h2><p>${dailyBalance()}/${DAILY_MAX} XBC awarded today</p></div><button class="secondary" id="exportReceipts">EXPORT RECEIPTS</button></div><div class="ledger-list">${recent.length ? recent.map(r => `<div class="ledger-row"><span>${BOUNTIES[r.game_id]?.icon || "◆"} ${BOUNTIES[r.game_id]?.name || r.game_id}</span><code>${r.ontology_action?.ecosystem_function || "ontology"}</code><strong>+${r.reward?.amount || 0} XBC</strong></div>`).join("") : `<p class="muted">Complete a bounty to create your first ArcadeRun receipt.</p>`}</div><p class="ledger-note">XBC are in-ecosystem bounty credits. Browser receipts are client-attested and have no cash or cryptocurrency value unless a separate governed redemption program is created.</p></section>`;
  }

  function render() {
    root.innerHTML = `<section class="arcade-hero"><div class="eyebrow">XUNIA // GPT-DOUG ONTOLOGY ARCADE</div><div class="hero-row"><div><h1>PLAY THE ONTOLOGY.</h1><p>Games now exercise bounded GPT‑DOUG ecosystem functions and mint auditable bounty receipts.</p></div><div class="balance"><b>${lifetimeBalance()}</b><span>XBC BALANCE</span></div></div><div class="badges"><span>ArcadeRun</span><span>BountyClaim</span><span>RecordArcadeRun</span><span>225 XBC DAILY BOARD</span></div></section><section class="arcade-grid"><aside class="game-list">${gameMenu()}</aside><main class="game-stage">${gameView()}</main></section>${ledgerView()}`;
    bind();
  }

  function bind() {
    root.querySelectorAll("[data-game]").forEach(btn => btn.addEventListener("click", () => { state.selected = btn.dataset.game; render(); }));
    document.getElementById("exportReceipts")?.addEventListener("click", exportReceipts);

    document.getElementById("pulseFire")?.addEventListener("click", () => {
      const s = state.pulse;
      const roll = rnd(1, 10);
      const hit = Math.abs(roll - s.target) <= 1;
      if (hit) { s.score += 10 + (s.streak * 2); s.streak += 1; s.streakPeak = Math.max(s.streakPeak, s.streak); } else s.streak = 0;
      s.target = rnd(1, 8);
      award("pulse-flight");
      render();
    });

    root.querySelectorAll("[data-node]").forEach(btn => btn.addEventListener("click", () => { const i = Number(btn.dataset.node); state.grid.cells[i] = !state.grid.cells[i]; award("grid-drop"); render(); }));
    document.getElementById("gridReset")?.addEventListener("click", () => { state.grid.cells = Array(25).fill(false); render(); });
    document.getElementById("novaGenerate")?.addEventListener("click", () => { state.nova.credits += state.nova.level * 10; render(); });
    document.getElementById("novaUpgrade")?.addEventListener("click", () => { const cost = state.nova.level * 50; if (state.nova.credits >= cost) { state.nova.credits -= cost; state.nova.level += 1; award("nova-tycoon"); } render(); });

    root.querySelectorAll("[data-move]").forEach(btn => btn.addEventListener("click", () => { const [dx, dy] = btn.dataset.move.split(",").map(Number); move(dx, dy); }));
    root.querySelectorAll("[data-signal]").forEach(btn => btn.addEventListener("click", () => { if (btn.dataset.signal === state.signal.target) state.signal.score += 10; else state.signal.misses += 1; state.signal.target = signals[rnd(0, signals.length - 1)]; award("signal-match"); render(); }));
  }

  function move(dx, dy) {
    const s = state.orbit;
    const x = s.player % 7, y = Math.floor(s.player / 7);
    const nx = Math.max(0, Math.min(6, x + dx)), ny = Math.max(0, Math.min(6, y + dy));
    s.player = ny * 7 + nx;
    if (s.player === s.star) { s.stars += 1; do s.star = rnd(0, 48); while (s.star === s.player); award("orbit-runner"); }
    render();
  }

  window.addEventListener("keydown", event => {
    if (state.selected !== "orbit-runner") return;
    const k = event.key.toLowerCase();
    const map = { arrowup: [0,-1], w: [0,-1], arrowdown: [0,1], s: [0,1], arrowleft: [-1,0], a: [-1,0], arrowright: [1,0], d: [1,0] };
    if (map[k]) { event.preventDefault(); move(...map[k]); }
  });

  render();
})();
