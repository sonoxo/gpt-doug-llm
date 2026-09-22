(() => {
  if (globalThis.__XUNIA_ZYRA_CHAOTIC_GOOD_GATEWAY__) return;
  globalThis.__XUNIA_ZYRA_CHAOTIC_GOOD_GATEWAY__ = true;

  let loopTimer = null;
  let loopIntervalMs = 2000;
  let shieldEnabled = true;

  const ALLOWED_DESTINATIONS = [
    (u) => u.protocol === "https:" && u.hostname.endsWith(".palantirfoundry.com"),
    (u) => u.protocol === "https:" && u.hostname === "github.com",
    (u) => (u.protocol === "http:" || u.protocol === "https:") && u.hostname === "localhost"
  ];

  const short = (value, max = 240) => String(value ?? "").replace(/\s+/g, " ").trim().slice(0, max);

  function isVisible(el) {
    const style = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.visibility !== "hidden" && style.display !== "none" && rect.width > 0 && rect.height > 0;
  }

  function cssHint(el) {
    if (el.id) return `#${CSS.escape(el.id)}`;
    const testId = el.getAttribute("data-testid");
    if (testId) return `[data-testid="${CSS.escape(testId)}"]`;
    const name = el.getAttribute("name");
    if (name) return `${el.tagName.toLowerCase()}[name="${CSS.escape(name)}"]`;
    const aria = el.getAttribute("aria-label");
    if (aria) return `${el.tagName.toLowerCase()}[aria-label="${CSS.escape(aria)}"]`;
    return el.tagName.toLowerCase();
  }

  function interactiveElement(el) {
    const tag = el.tagName.toLowerCase();
    const inputType = tag === "input" ? (el.getAttribute("type") || "text").toLowerCase() : null;
    return {
      tag,
      selectorHint: cssHint(el),
      role: el.getAttribute("role"),
      type: inputType,
      text: inputType === "password" ? "[password-field]" : short(el.innerText || el.getAttribute("aria-label") || el.getAttribute("placeholder") || ""),
      ariaLabel: short(el.getAttribute("aria-label") || ""),
      placeholder: inputType === "password" ? "" : short(el.getAttribute("placeholder") || ""),
      disabled: Boolean(el.disabled || el.getAttribute("aria-disabled") === "true")
    };
  }

  function safeUrl(raw, base = location.href) {
    try { return new URL(raw, base); } catch { return null; }
  }

  function allowedDestination(url) {
    return Boolean(url && ALLOWED_DESTINATIONS.some((check) => check(url)));
  }

  function securityScan() {
    const findings = [];
    const add = (severity, code, detail) => findings.push({ severity, code, detail: short(detail, 320) });
    const current = new URL(location.href);
    const localhost = current.hostname === "localhost";
    const passwordFields = [...document.querySelectorAll('input[type="password"]')].filter(isVisible);

    if (!localhost && current.protocol !== "https:") add("critical", "INSECURE_PAGE_PROTOCOL", `Page uses ${current.protocol}`);
    if (current.hostname.includes("xn--")) add("high", "PUNYCODE_HOST", `Hostname contains punycode: ${current.hostname}`);
    if (current.protocol === "http:" && passwordFields.length) add("critical", "PASSWORD_ON_HTTP", `${passwordFields.length} visible password field(s) on HTTP`);

    const mixed = [...document.querySelectorAll('img[src],script[src],iframe[src],link[href]')]
      .map((el) => safeUrl(el.getAttribute("src") || el.getAttribute("href")))
      .filter((url) => current.protocol === "https:" && url?.protocol === "http:");
    if (mixed.length) add("high", "MIXED_CONTENT_REFERENCE", `${mixed.length} HTTP resource reference(s) found on HTTPS page`);

    const forms = [...document.forms];
    let crossOriginForms = 0;
    let insecureForms = 0;
    for (const form of forms) {
      const action = safeUrl(form.getAttribute("action") || location.href);
      if (!action) continue;
      if (action.origin !== current.origin) crossOriginForms += 1;
      if (current.protocol === "https:" && action.protocol === "http:") insecureForms += 1;
    }
    if (insecureForms) add("critical", "HTTPS_FORM_TO_HTTP", `${insecureForms} form(s) submit from HTTPS to HTTP`);
    if (crossOriginForms) add("high", "CROSS_ORIGIN_FORM", `${crossOriginForms} cross-origin form action(s) detected`);

    const jsLinks = [...document.querySelectorAll('a[href^="javascript:"]')].filter(isVisible).length;
    if (jsLinks) add("medium", "JAVASCRIPT_LINK", `${jsLinks} visible javascript: link(s) detected`);

    const externalOrigins = [...new Set(
      [...document.querySelectorAll("a[href]")]
        .map((el) => safeUrl(el.getAttribute("href")))
        .filter((url) => url && /^https?:$/.test(url.protocol) && url.origin !== current.origin)
        .map((url) => url.origin)
    )].slice(0, 12);

    const weights = { critical: 60, high: 30, medium: 15, low: 5 };
    const riskScore = Math.min(100, findings.reduce((sum, f) => sum + (weights[f.severity] || 0), 0));
    const state = riskScore >= 60 ? "RED" : riskScore >= 30 ? "AMBER" : "GREEN";
    return {
      at: new Date().toISOString(),
      state,
      riskScore,
      findings,
      externalOrigins,
      passwordFieldCount: passwordFields.length,
      shieldEnabled
    };
  }

  function snapshot() {
    const candidates = [...document.querySelectorAll("button,a,input,textarea,select,[role='button'],[contenteditable='true']")]
      .filter(isVisible)
      .slice(0, 120)
      .map(interactiveElement);
    return {
      at: new Date().toISOString(),
      title: document.title,
      url: location.href,
      viewport: { width: innerWidth, height: innerHeight, scrollX, scrollY },
      headings: [...document.querySelectorAll("h1,h2,h3")].filter(isVisible).slice(0, 30).map((el) => short(el.innerText)),
      interactive: candidates,
      security: securityScan()
    };
  }

  async function pushSnapshot() {
    const snap = snapshot();
    try { await chrome.runtime.sendMessage({ type: "SNAPSHOT_PUSH", snapshot: snap }); } catch {}
    return snap;
  }

  function setLoop(enabled, intervalMs = 2000) {
    if (loopTimer) clearInterval(loopTimer);
    loopTimer = null;
    loopIntervalMs = Math.max(1000, Math.min(30000, Number(intervalMs) || 2000));
    if (enabled) {
      pushSnapshot();
      loopTimer = setInterval(pushSnapshot, loopIntervalMs);
    }
    return { ok: true, enabled: Boolean(enabled), intervalMs: loopIntervalMs };
  }

  function setShield(enabled) {
    shieldEnabled = Boolean(enabled);
    return { ok: true, shieldEnabled };
  }

  function getElement(selector) {
    if (!selector || typeof selector !== "string") throw new Error("A CSS selector is required");
    const el = document.querySelector(selector);
    if (!el) throw new Error(`No element matches selector: ${selector}`);
    if (!isVisible(el)) throw new Error(`Element is not visible: ${selector}`);
    return el;
  }

  function formHazardFor(el) {
    const form = el.closest?.("form");
    if (!form) return null;
    const action = safeUrl(form.getAttribute("action") || location.href);
    if (!action) return null;
    if (location.protocol === "https:" && action.protocol === "http:") return "Blocked: form would submit from HTTPS to HTTP";
    if (action.origin !== location.origin) return `Blocked: form would submit cross-origin to ${action.origin}`;
    return null;
  }

  function navigationHazardFor(el) {
    const anchor = el.closest?.("a[href]");
    if (!anchor) return null;
    const raw = anchor.getAttribute("href") || "";
    if (raw.trim().toLowerCase().startsWith("javascript:")) return "Blocked: javascript: navigation is outside the gateway policy";
    const url = safeUrl(raw);
    if (url && /^https?:$/.test(url.protocol) && !allowedDestination(url)) return `Blocked: destination is outside the gateway allowlist (${url.origin})`;
    return null;
  }

  function doAction(action, useShield = true) {
    if (!action || typeof action !== "object") throw new Error("Missing action");
    const type = action.type;

    if (type === "click") {
      const el = getElement(action.selector);
      if (el.disabled || el.getAttribute("aria-disabled") === "true") throw new Error("Element is disabled");
      if (useShield && shieldEnabled) {
        const hazard = formHazardFor(el) || navigationHazardFor(el);
        if (hazard) throw new Error(hazard);
      }
      el.scrollIntoView({ block: "center", inline: "center" });
      el.click();
      return { ok: true, type };
    }

    if (type === "type") {
      const el = getElement(action.selector);
      const tag = el.tagName.toLowerCase();
      const inputType = (el.getAttribute("type") || "text").toLowerCase();
      if (["password", "file", "hidden"].includes(inputType)) throw new Error(`Typing into ${inputType} inputs is blocked`);
      if (!(tag === "input" || tag === "textarea" || el.isContentEditable)) throw new Error("Target is not a text-editable element");
      if (useShield && shieldEnabled) {
        const hazard = formHazardFor(el);
        if (hazard) throw new Error(hazard);
      }
      el.focus();
      if (el.isContentEditable) {
        el.textContent = String(action.text ?? "");
        el.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: null }));
      } else {
        const proto = tag === "textarea" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
        const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
        if (setter) setter.call(el, String(action.text ?? ""));
        else el.value = String(action.text ?? "");
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
      }
      return { ok: true, type };
    }

    if (type === "scroll") {
      const y = Math.max(-3000, Math.min(3000, Number(action.deltaY) || 0));
      window.scrollBy({ top: y, behavior: "smooth" });
      return { ok: true, type, deltaY: y };
    }

    if (type === "focus") {
      const el = getElement(action.selector);
      el.scrollIntoView({ block: "center", inline: "center" });
      el.focus();
      return { ok: true, type };
    }

    if (type === "highlight") {
      const el = getElement(action.selector);
      const old = el.style.outline;
      el.style.outline = "3px solid currentColor";
      setTimeout(() => { el.style.outline = old; }, 1800);
      return { ok: true, type };
    }

    throw new Error(`Unsupported action: ${type}`);
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    (async () => {
      if (message?.type === "PING") return { ok: true };
      if (message?.type === "SET_LOOP") return setLoop(message.enabled, message.intervalMs);
      if (message?.type === "SET_SHIELD") return setShield(message.enabled);
      if (message?.type === "SNAPSHOT_NOW") return { ok: true, snapshot: await pushSnapshot() };
      if (message?.type === "SCAN_NOW") {
        const scan = securityScan();
        await pushSnapshot();
        return { ok: true, scan };
      }
      if (message?.type === "ACTION") {
        const result = doAction(message.action, message.shieldEnabled !== false);
        await pushSnapshot();
        return result;
      }
      throw new Error("Unknown content message");
    })().then(sendResponse).catch((error) => sendResponse({ ok: false, error: String(error?.message || error) }));
    return true;
  });
})();
