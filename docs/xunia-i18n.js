(() => {
  "use strict";

  const API = "https://xunia-ops-api.onrender.com/api/translate";
  const STORAGE_KEY = "xunia.language";
  const rtl = new Set(["ar","arc","dv","fa","he","ku","ps","sd","ug","ur","yi"]);
  const languageTags = [
    "auto","en","es","fr","de","it","pt","nl","pl","uk","ru","ar","fa","he","tr","el",
    "ro","hu","cs","sk","bg","sr","hr","sl","sq","mk","hy","ka","az","kk","uz","mn",
    "hi","bn","ur","pa","gu","mr","ta","te","kn","ml","ne","si","th","vi","id","ms",
    "fil","zh-CN","zh-TW","ja","ko","sw","am","so","ha","yo","ig","zu","xh","af",
    "et","lv","lt","fi","sv","no","da","is","ga","cy","mt","eu","ca","gl"
  ];

  const original = new WeakMap();
  const rendered = new WeakMap();
  let current = "en";
  let busy = false;
  let rerun = false;
  let nativeTranslator = null;
  let nativeTarget = null;

  const baseCode = tag => String(tag || "en").trim().replace("_","-").toLowerCase().split("-")[0];
  const normalize = tag => {
    const raw = String(tag || "en").trim().replace("_","-");
    const lower = raw.toLowerCase();
    if (lower === "auto") return "auto";
    if (lower === "zh-cn" || lower === "zh-hans" || lower === "zh-sg") return "zh-CN";
    if (lower === "zh-tw" || lower === "zh-hant" || lower === "zh-hk") return "zh-TW";
    const base = lower.split("-")[0];
    return /^[a-z]{2,3}$/.test(base) ? base : "en";
  };
  const detected = () => normalize((navigator.languages && navigator.languages[0]) || navigator.language || "en");
  const resolvedTarget = value => value === "auto" ? detected() : normalize(value);

  function isExcluded(node) {
    const el = node && node.parentElement;
    if (!el) return true;
    return !!el.closest("script,style,code,pre,noscript,svg,canvas,textarea,input,select,option,[contenteditable='true'],[data-no-translate],.xunia-i18n");
  }

  function shouldTranslate(text) {
    const t = String(text || "").trim();
    if (t.length < 2) return false;
    if (/^(https?:\/\/|www\.|[\w.+-]+@[\w.-]+\.)/i.test(t)) return false;
    if (/^[\d\s.,:;|/+\-_=()[\]{}%#@!?•·—–→↗↻●○◌]+$/.test(t)) return false;
    return /[A-Za-z]/.test(t);
  }

  function byteLength(value) {
    return new TextEncoder().encode(String(value)).length;
  }

  function splitText(text, maxBytes = 430) {
    const value = String(text);
    if (byteLength(value) <= maxBytes) return [value];
    const parts = value.match(/[^.!?。！？]+[.!?。！？]?\s*/g) || [value];
    const chunks = [];
    let chunk = "";
    for (const part of parts) {
      const candidate = chunk + part;
      if (chunk && byteLength(candidate) > maxBytes) {
        chunks.push(chunk);
        chunk = part;
      } else {
        chunk = candidate;
      }
      if (byteLength(chunk) > maxBytes) {
        let rest = chunk;
        chunk = "";
        while (byteLength(rest) > maxBytes) {
          let cut = Math.min(rest.length, 300);
          while (cut > 20 && byteLength(rest.slice(0, cut)) > maxBytes) cut -= 10;
          chunks.push(rest.slice(0, cut));
          rest = rest.slice(cut);
        }
        chunk = rest;
      }
    }
    if (chunk) chunks.push(chunk);
    return chunks;
  }

  function cacheKey(target, text) {
    let hash = 2166136261;
    for (let i = 0; i < text.length; i++) {
      hash ^= text.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }
    return "xunia.i18n." + target + "." + (hash >>> 0).toString(36);
  }

  function getCached(target, text) {
    try { return localStorage.getItem(cacheKey(target, text)); } catch { return null; }
  }

  function setCached(target, text, translated) {
    try { localStorage.setItem(cacheKey(target, text), translated); } catch {}
  }

  async function getNativeTranslator(target) {
    if (!("Translator" in globalThis)) return null;
    if (nativeTranslator && nativeTarget === target) return nativeTranslator;
    try {
      const opts = { sourceLanguage: "en", targetLanguage: target };
      if (typeof Translator.availability === "function") {
        const availability = await Translator.availability(opts);
        if (availability === "unavailable") return null;
      }
      nativeTranslator = await Translator.create(opts);
      nativeTarget = target;
      return nativeTranslator;
    } catch {
      return null;
    }
  }

  async function remoteTranslate(target, texts) {
    const response = await fetch(API, {
      method: "POST",
      mode: "cors",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source: "en", target, texts })
    });
    if (!response.ok) throw new Error("translation HTTP " + response.status);
    const data = await response.json();
    return Array.isArray(data.translations) ? data.translations : texts;
  }

  async function translateStrings(target, strings) {
    const out = new Array(strings.length);
    const missing = [];
    strings.forEach((text, index) => {
      const hit = getCached(target, text);
      if (hit) out[index] = hit;
      else missing.push({ text, index });
    });
    if (!missing.length) return out;

    const native = await getNativeTranslator(target);
    if (native) {
      for (const item of missing) {
        try {
          const pieces = splitText(item.text);
          const translated = [];
          for (const piece of pieces) translated.push(await native.translate(piece));
          out[item.index] = translated.join("");
          setCached(target, item.text, out[item.index]);
        } catch {
          out[item.index] = item.text;
        }
      }
      return out;
    }

    for (let i = 0; i < missing.length; i += 12) {
      const batch = missing.slice(i, i + 12);
      try {
        const values = await remoteTranslate(target, batch.map(x => x.text));
        batch.forEach((item, j) => {
          out[item.index] = values[j] || item.text;
          if (out[item.index] !== item.text) setCached(target, item.text, out[item.index]);
        });
      } catch {
        batch.forEach(item => { out[item.index] = item.text; });
      }
    }
    return out;
  }

  function collectTextNodes(root = document.body) {
    if (!root) return [];
    const nodes = [];
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (isExcluded(node)) continue;
      const value = node.nodeValue || "";
      if (!shouldTranslate(value)) continue;
      if (!original.has(node)) original.set(node, value);
      nodes.push(node);
    }
    return nodes;
  }

  function setDirection(target) {
    const code = baseCode(target);
    document.documentElement.lang = target === "auto" ? detected() : target;
    document.documentElement.dir = rtl.has(code) ? "rtl" : "ltr";
    document.body && document.body.classList.toggle("xunia-rtl", rtl.has(code));
  }

  function updateStatus(message) {
    const status = document.querySelector(".xunia-i18n-status");
    if (status) status.textContent = message;
  }

  async function applyLanguage(selection) {
    const target = resolvedTarget(selection);
    current = target;
    setDirection(target);
    try { localStorage.setItem(STORAGE_KEY, selection); } catch {}

    if (busy) { rerun = true; return; }
    busy = true;
    updateStatus(target === "en" ? "English" : "Translating…");

    try {
      const nodes = collectTextNodes();
      if (target === "en") {
        nodes.forEach(node => {
          const source = original.get(node);
          if (source != null) {
            node.nodeValue = source;
            rendered.set(node, source);
          }
        });
        updateStatus("English");
        return;
      }

      const sourceTexts = nodes.map(node => original.get(node) || node.nodeValue || "");
      const translations = await translateStrings(target, sourceTexts);
      nodes.forEach((node, i) => {
        const next = translations[i] || sourceTexts[i];
        node.nodeValue = next;
        rendered.set(node, next);
      });
      updateStatus(target.toUpperCase());
    } finally {
      busy = false;
      if (rerun) {
        rerun = false;
        queueMicrotask(() => applyLanguage(selection));
      }
    }
  }

  function languageName(tag, uiLocale) {
    if (tag === "auto") return "AUTO · Device language";
    try {
      const dn = new Intl.DisplayNames([uiLocale || "en"], { type: "language" });
      return dn.of(tag) || tag;
    } catch {
      return tag;
    }
  }

  function buildUI() {
    if (document.querySelector(".xunia-i18n")) return;
    const compact = window.top !== window.self;
    const wrap = document.createElement("div");
    wrap.className = "xunia-i18n" + (compact ? " compact" : "");
    wrap.setAttribute("data-no-translate", "true");
    wrap.innerHTML = `
      <button class="xunia-i18n-toggle" type="button" aria-expanded="false" aria-label="Language and translation">🌐 <span class="xunia-i18n-status">AUTO</span></button>
      <div class="xunia-i18n-panel" hidden>
        <label>
          <span>Language</span>
          <select class="xunia-i18n-select" aria-label="Choose interface language"></select>
        </label>
        <p>Auto-detects your device language. Uses on-device translation when available and a public translation fallback for public XUNIA interface text.</p>
      </div>`;

    const style = document.createElement("style");
    style.textContent = `
      .xunia-i18n{position:fixed;z-index:2147483000;right:max(12px,env(safe-area-inset-right));bottom:max(12px,env(safe-area-inset-bottom));font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;direction:ltr}
      .xunia-i18n-toggle{min-height:44px;border:1px solid rgba(70,243,255,.34);border-radius:999px;padding:9px 12px;background:rgba(5,9,16,.92);color:#eff7ff;font:800 11px system-ui;box-shadow:0 10px 35px #0008;backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);touch-action:manipulation}
      .xunia-i18n-panel{position:absolute;right:0;bottom:52px;width:min(320px,calc(100vw - 24px));padding:14px;border:1px solid rgba(70,243,255,.28);border-radius:16px;background:rgba(5,9,16,.98);box-shadow:0 24px 70px #000b;color:#eff7ff}
      .xunia-i18n-panel label{display:grid;gap:7px;font-size:11px;font-weight:850;text-transform:uppercase;letter-spacing:.08em}
      .xunia-i18n-select{width:100%;min-height:46px;border:1px solid #2b4050;border-radius:11px;background:#0b121a;color:#fff;padding:10px 12px;font-size:16px}
      .xunia-i18n-panel p{margin:10px 0 0;color:#8da3b4;font-size:11px;line-height:1.45;text-transform:none;letter-spacing:0}
      .xunia-i18n.compact{right:8px;bottom:8px}.xunia-i18n.compact .xunia-i18n-toggle{min-height:40px;padding:7px 10px;font-size:10px}
      .xunia-rtl{text-align:right}.xunia-rtl .xunia-i18n{direction:ltr}
      @media(max-width:480px){.xunia-i18n{right:max(8px,env(safe-area-inset-right));bottom:max(8px,env(safe-area-inset-bottom))}.xunia-i18n-panel{width:min(340px,calc(100vw - 16px))}}
    `;
    document.head.append(style);
    document.body.append(wrap);

    const select = wrap.querySelector(".xunia-i18n-select");
    const uiLocale = (navigator.languages && navigator.languages[0]) || navigator.language || "en";
    for (const tag of languageTags) {
      const option = document.createElement("option");
      option.value = tag;
      option.textContent = languageName(tag, uiLocale);
      select.append(option);
    }

    const saved = (() => {
      try { return localStorage.getItem(STORAGE_KEY) || "auto"; } catch { return "auto"; }
    })();
    select.value = languageTags.includes(saved) ? saved : "auto";

    const toggle = wrap.querySelector(".xunia-i18n-toggle");
    const panel = wrap.querySelector(".xunia-i18n-panel");
    toggle.addEventListener("click", () => {
      const open = panel.hidden;
      panel.hidden = !open;
      toggle.setAttribute("aria-expanded", String(open));
    });
    select.addEventListener("change", () => {
      panel.hidden = true;
      toggle.setAttribute("aria-expanded", "false");
      applyLanguage(select.value);
    });

    document.addEventListener("keydown", event => {
      if (event.key === "Escape" && !panel.hidden) {
        panel.hidden = true;
        toggle.setAttribute("aria-expanded", "false");
      }
    });

    applyLanguage(select.value);
  }

  const observer = new MutationObserver(records => {
    if (busy || current === "en") return;
    let externalChange = false;
    for (const record of records) {
      if (record.type === "characterData") {
        const node = record.target;
        if (isExcluded(node)) continue;
        const last = rendered.get(node);
        if (last !== node.nodeValue && shouldTranslate(node.nodeValue)) {
          original.set(node, node.nodeValue);
          externalChange = true;
        }
      } else if (record.addedNodes && record.addedNodes.length) {
        externalChange = true;
      }
    }
    if (externalChange) {
      clearTimeout(observer.timer);
      observer.timer = setTimeout(() => {
        const selection = (() => {
          try { return localStorage.getItem(STORAGE_KEY) || "auto"; } catch { return "auto"; }
        })();
        applyLanguage(selection);
      }, 350);
    }
  });

  const start = () => {
    buildUI();
    observer.observe(document.body, { subtree: true, childList: true, characterData: true });
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
