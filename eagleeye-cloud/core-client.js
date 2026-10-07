/* GPT-DOUG Core Platform client.
 * Read-only browser bridge for PUBLIC/TRAINING/SIMULATION event streams.
 * No secrets are embedded in this file.
 */
(() => {
  if (window.GPT_CORE) return;

  const local = ["localhost", "127.0.0.1"].includes(location.hostname);
  const configured = localStorage.getItem("gpt_doug_core_url");
  const base = (configured || (local
    ? "http://127.0.0.1:8090"
    : "https://gpt-doug-platform-core.onrender.com")).replace(/\/$/, "");

  const state = {
    base,
    connected: false,
    websocket: false,
    manifest: null,
    lastEventAt: null,
    lastError: null,
    reconnects: 0,
  };

  const emit = (name, detail) =>
    window.dispatchEvent(new CustomEvent("gpt-doug-core:" + name, { detail }));

  async function getJSON(path) {
    const res = await fetch(base + path, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!res.ok) throw new Error(path + " -> HTTP " + res.status);
    return res.json();
  }

  async function bootstrap() {
    try {
      const [manifest, events] = await Promise.all([
        getJSON("/api/v1/platform/manifest"),
        getJSON("/api/v1/public/events?limit=50"),
      ]);
      state.manifest = manifest;
      state.connected = true;
      state.lastError = null;
      emit("status", { ...state });
      emit("snapshot", events);
    } catch (err) {
      state.connected = false;
      state.lastError = String(err?.message || err);
      emit("status", { ...state });
    }
  }

  function websocketURL() {
    return base.replace(/^http:/, "ws:").replace(/^https:/, "wss:") + "/ws/v1/events";
  }

  let socket = null;
  let retryTimer = null;

  function connect() {
    clearTimeout(retryTimer);
    try {
      socket = new WebSocket(websocketURL());
    } catch (err) {
      state.lastError = String(err?.message || err);
      scheduleReconnect();
      return;
    }

    socket.onopen = () => {
      state.websocket = true;
      state.connected = true;
      state.reconnects = 0;
      state.lastError = null;
      emit("status", { ...state });
    };

    socket.onmessage = ev => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "platform_event" && msg.event) {
          state.lastEventAt = new Date().toISOString();
          emit("event", msg.event);
        } else if (msg.type === "platform_snapshot") {
          emit("snapshot", { events: msg.events || [] });
        } else if (msg.type === "heartbeat") {
          emit("heartbeat", msg);
        }
      } catch (err) {
        state.lastError = "event decode: " + String(err?.message || err);
        emit("status", { ...state });
      }
    };

    socket.onerror = () => {
      state.websocket = false;
    };

    socket.onclose = () => {
      state.websocket = false;
      state.connected = false;
      emit("status", { ...state });
      scheduleReconnect();
    };
  }

  function scheduleReconnect() {
    clearTimeout(retryTimer);
    state.reconnects += 1;
    const delay = Math.min(30000, 1000 * Math.pow(2, Math.min(state.reconnects, 5)));
    retryTimer = setTimeout(connect, delay);
  }

  function setBase(url) {
    const next = String(url || "").trim().replace(/\/$/, "");
    if (!/^https?:\/\//.test(next)) throw new Error("core URL must begin with http:// or https://");
    localStorage.setItem("gpt_doug_core_url", next);
    location.reload();
  }

  function clearBase() {
    localStorage.removeItem("gpt_doug_core_url");
    location.reload();
  }

  window.GPT_CORE = {
    state,
    bootstrap,
    reconnect: connect,
    setBase,
    clearBase,
    status: () => ({ ...state }),
  };

  bootstrap().finally(connect);
})();
