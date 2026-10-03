const DEFAULTS = {
  loopEnabled: false,
  intervalMs: 2000,
  shieldEnabled: true,
  activeTabId: null,
  latestSnapshot: null,
  latestSnapshotAt: null,
  latestScan: null,
  latestScanAt: null,
  writesArmedUntil: 0,
  actionLog: []
};

const WRITE_ARM_MAX_MS = 5 * 60 * 1000;
const MUTATING_ACTIONS = new Set(["click", "type"]);
const ALLOWED = [
  /^https:\/\/[^/]+\.palantirfoundry\.com\//i,
  /^https:\/\/github\.com\//i,
  /^https?:\/\/localhost(?::\d+)?\//i
];

const allowedUrl = (url = "") => ALLOWED.some((rx) => rx.test(url));
const now = () => Date.now();

async function readState() {
  return { ...DEFAULTS, ...(await chrome.storage.local.get(DEFAULTS)) };
}

async function writeState(patch) {
  await chrome.storage.local.set(patch);
  return readState();
}

async function activeTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) throw new Error("No active tab");
  if (!allowedUrl(tab.url || "")) throw new Error("This tab is outside the gateway allowlist");
  return tab;
}

async function ensureContentScript(tabId) {
  try {
    await chrome.tabs.sendMessage(tabId, { type: "PING" });
  } catch {
    await chrome.scripting.executeScript({ target: { tabId }, files: ["content.js"] });
  }
}

async function relay(tabId, message) {
  await ensureContentScript(tabId);
  return chrome.tabs.sendMessage(tabId, message);
}

function armStatus(state) {
  const remainingMs = Math.max(0, Number(state.writesArmedUntil || 0) - now());
  return { armed: remainingMs > 0, remainingMs, remainingSeconds: Math.ceil(remainingMs / 1000) };
}

async function updateBadge() {
  const state = await readState();
  const arm = armStatus(state);
  const text = arm.armed ? "ARM" : state.loopEnabled ? "LOOP" : state.shieldEnabled ? "CG" : "";
  await chrome.action.setBadgeText({ text });
}

async function recordAction(tabId, action, result) {
  const state = await readState();
  const tab = await chrome.tabs.get(tabId);
  const arm = armStatus(state);
  const entry = {
    at: new Date().toISOString(),
    tabId,
    origin: (() => { try { return new URL(tab.url).origin; } catch { return "unknown"; } })(),
    action: action?.type || "unknown",
    selector: action?.selector || null,
    writeArmed: arm.armed,
    ok: Boolean(result?.ok),
    error: result?.error || null
  };
  const actionLog = [entry, ...(state.actionLog || [])].slice(0, 200);
  await writeState({ actionLog });
}

chrome.runtime.onInstalled.addListener(async () => {
  await chrome.storage.local.set(DEFAULTS);
  await updateBadge();
});

chrome.tabs.onUpdated.addListener(async (tabId, changeInfo) => {
  if (changeInfo.status !== "loading") return;
  const state = await readState();
  if (state.activeTabId === tabId && state.writesArmedUntil) {
    await writeState({ writesArmedUntil: 0 });
    await updateBadge();
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  (async () => {
    if (message?.type === "SNAPSHOT_PUSH") {
      await writeState({
        latestSnapshot: message.snapshot,
        latestSnapshotAt: new Date().toISOString(),
        latestScan: message.snapshot?.security || null,
        latestScanAt: new Date().toISOString(),
        activeTabId: sender.tab?.id ?? null
      });
      sendResponse({ ok: true });
      return;
    }

    if (message?.type === "GET_STATUS") {
      const state = await readState();
      let tab = null;
      try { tab = await activeTab(); } catch {}
      sendResponse({ ok: true, state: { ...state, writeArm: armStatus(state) }, tab: tab ? { id: tab.id, title: tab.title, url: tab.url } : null });
      return;
    }

    if (message?.type === "SET_LOOP") {
      const tab = await activeTab();
      const intervalMs = Math.max(1000, Math.min(30000, Number(message.intervalMs) || 2000));
      const enabled = Boolean(message.enabled);
      const result = await relay(tab.id, { type: "SET_LOOP", enabled, intervalMs });
      await writeState({ loopEnabled: enabled, intervalMs, activeTabId: tab.id });
      await updateBadge();
      sendResponse({ ok: true, result });
      return;
    }

    if (message?.type === "SET_SHIELD") {
      const enabled = Boolean(message.enabled);
      const tab = await activeTab();
      await writeState({ shieldEnabled: enabled, activeTabId: tab.id });
      const result = await relay(tab.id, { type: "SET_SHIELD", enabled });
      await updateBadge();
      sendResponse({ ok: true, result });
      return;
    }

    if (message?.type === "ARM_WRITES") {
      const tab = await activeTab();
      const requested = Math.max(30000, Number(message.durationMs) || WRITE_ARM_MAX_MS);
      const durationMs = Math.min(WRITE_ARM_MAX_MS, requested);
      const writesArmedUntil = now() + durationMs;
      await writeState({ writesArmedUntil, activeTabId: tab.id });
      await updateBadge();
      sendResponse({ ok: true, writesArmedUntil, durationMs });
      return;
    }

    if (message?.type === "DISARM_WRITES") {
      await writeState({ writesArmedUntil: 0 });
      await updateBadge();
      sendResponse({ ok: true });
      return;
    }

    if (message?.type === "PANIC_STOP") {
      let tab = null;
      try { tab = await activeTab(); } catch {}
      if (tab?.id) {
        try { await relay(tab.id, { type: "SET_LOOP", enabled: false, intervalMs: 2000 }); } catch {}
      }
      await writeState({ loopEnabled: false, writesArmedUntil: 0 });
      await updateBadge();
      sendResponse({ ok: true });
      return;
    }

    if (message?.type === "SNAPSHOT_NOW" || message?.type === "SCAN_NOW") {
      const tab = await activeTab();
      const result = await relay(tab.id, { type: message.type });
      sendResponse(result);
      return;
    }

    if (message?.type === "ACTION") {
      const tab = await activeTab();
      const state = await readState();
      const action = message.action || {};
      if (MUTATING_ACTIONS.has(action.type) && !armStatus(state).armed) {
        const result = { ok: false, error: "Write actions are disarmed. Arm writes from the popup first." };
        await recordAction(tab.id, action, result);
        sendResponse(result);
        return;
      }
      const result = await relay(tab.id, { type: "ACTION", action, shieldEnabled: state.shieldEnabled });
      await recordAction(tab.id, action, result);
      sendResponse(result);
      return;
    }

    throw new Error("Unknown message type");
  })().catch((error) => sendResponse({ ok: false, error: String(error?.message || error) }));
  return true;
});
