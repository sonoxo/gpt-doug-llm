(() => {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  const state = {
    targets: [],
    badges: [],
    pendingTarget: null,
    recognition: null,
    panel: null,
    mic: null,
  };

  const HIGH_IMPACT = /\b(delete|remove|destroy|terminate|revoke|grant|permission|submit|purchase|pay|deploy|publish|approve|merge|send|invite|create account|reset)\b/i;

  function ensureUi() {
    if (state.panel && state.mic) return;

    const panel = document.createElement('div');
    panel.id = 'nxyz-mm-panel';
    panel.textContent = 'NXYZ Mouse Mic ready';

    const mic = document.createElement('button');
    mic.id = 'nxyz-mm-mic';
    mic.type = 'button';
    mic.setAttribute('aria-label', 'NXYZ Mouse Mic');
    mic.textContent = '🎙️';
    mic.title = 'NXYZ Mouse Mic — click, then speak';
    mic.addEventListener('click', startListening);

    document.documentElement.append(panel, mic);
    state.panel = panel;
    state.mic = mic;
  }

  function setStatus(text) {
    ensureUi();
    state.panel.textContent = text;
  }

  function speak(text) {
    setStatus(text);
    try {
      speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.05;
      speechSynthesis.speak(utterance);
    } catch (_) {
      // Text status remains available even if speech synthesis is unavailable.
    }
  }

  function isVisible(el) {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return (
      rect.width > 2 &&
      rect.height > 2 &&
      style.display !== 'none' &&
      style.visibility !== 'hidden' &&
      Number(style.opacity || 1) !== 0 &&
      rect.bottom >= 0 &&
      rect.right >= 0 &&
      rect.top <= innerHeight &&
      rect.left <= innerWidth
    );
  }

  function targetName(el) {
    const aria = el.getAttribute('aria-label') || '';
    const title = el.getAttribute('title') || '';
    const text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
    const placeholder = el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement
      ? (el.placeholder || el.value || '')
      : '';
    return (aria || title || text || placeholder || el.getAttribute('name') || el.id || el.tagName)
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 180);
  }

  function scanTargets() {
    const selector = [
      'button',
      'a[href]',
      'input:not([type="hidden"])',
      'select',
      'textarea',
      '[role="button"]',
      '[role="link"]',
      '[role="menuitem"]',
      '[role="tab"]',
      '[role="option"]',
      '[aria-label]',
      '[tabindex]:not([tabindex="-1"])'
    ].join(',');

    const seen = new Set();
    const targets = [];
    for (const el of document.querySelectorAll(selector)) {
      if (seen.has(el) || !isVisible(el)) continue;
      seen.add(el);
      const name = targetName(el);
      if (!name) continue;
      const rect = el.getBoundingClientRect();
      targets.push({
        el,
        name,
        x: rect.left + rect.width / 2,
        y: rect.top + rect.height / 2,
      });
    }
    state.targets = targets.slice(0, 180);
    return state.targets;
  }

  function clearBadges() {
    for (const badge of state.badges) badge.remove();
    state.badges = [];
    document.querySelectorAll('.nxyz-mm-highlight').forEach((el) => el.classList.remove('nxyz-mm-highlight'));
  }

  function showTargets() {
    clearBadges();
    const targets = scanTargets();
    targets.forEach((target, index) => {
      const rect = target.el.getBoundingClientRect();
      const badge = document.createElement('div');
      badge.className = 'nxyz-mm-badge';
      badge.textContent = String(index + 1);
      badge.style.left = `${Math.max(4, rect.left)}px`;
      badge.style.top = `${Math.max(4, rect.top)}px`;
      document.documentElement.appendChild(badge);
      state.badges.push(badge);
    });
    speak(`${targets.length} clickable targets labeled. Say click number, followed by a number, or where is, followed by a label.`);
  }

  function words(text) {
    return text
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, ' ')
      .split(/\s+/)
      .filter((word) => word.length > 1);
  }

  function score(query, candidate) {
    const q = query.toLowerCase().trim();
    const c = candidate.toLowerCase().trim();
    if (!q || !c) return 0;
    if (c === q) return 1000;
    if (c.includes(q)) return 800 - Math.min(200, c.length - q.length);
    if (q.includes(c) && c.length > 3) return 650;

    const qWords = words(q);
    const cWords = new Set(words(c));
    let matched = 0;
    for (const word of qWords) if (cWords.has(word)) matched += 1;
    if (!qWords.length) return 0;
    return (matched / qWords.length) * 500;
  }

  function bestTarget(query) {
    const targets = scanTargets();
    let best = null;
    let bestScore = 0;
    for (const target of targets) {
      const s = score(query, target.name);
      if (s > bestScore) {
        best = target;
        bestScore = s;
      }
    }
    return bestScore >= 120 ? best : null;
  }

  function locationOf(target) {
    const horizontal = target.x < innerWidth / 3 ? 'left' : target.x > (innerWidth * 2) / 3 ? 'right' : 'center';
    const vertical = target.y < innerHeight / 3 ? 'top' : target.y > (innerHeight * 2) / 3 ? 'bottom' : 'middle';
    return `${vertical} ${horizontal}`;
  }

  function highlight(target) {
    clearBadges();
    target.el.classList.add('nxyz-mm-highlight');
    target.el.scrollIntoView({ block: 'center', inline: 'center', behavior: 'smooth' });
  }

  function describe(query) {
    const target = bestTarget(query);
    if (!target) {
      speak(`I could not find ${query} on this screen. Say show targets to label everything clickable.`);
      return;
    }
    highlight(target);
    speak(`${target.name} is in the ${locationOf(target)} of the screen. I highlighted it.`);
  }

  function clickTarget(target) {
    highlight(target);
    const highImpact = HIGH_IMPACT.test(target.name);
    if (highImpact) {
      state.pendingTarget = target;
      speak(`${target.name} may cause a significant change. I highlighted it but did not click. Say confirm click to continue, or cancel.`);
      return;
    }
    target.el.click();
    speak(`Clicked ${target.name}.`);
  }

  function clickByName(query) {
    const target = bestTarget(query);
    if (!target) {
      speak(`I could not find ${query}. Say show targets to label the screen.`);
      return;
    }
    clickTarget(target);
  }

  function clickByNumber(number) {
    if (!state.targets.length) scanTargets();
    const target = state.targets[number - 1];
    if (!target) {
      speak(`Target number ${number} is not available. Say show targets first.`);
      return;
    }
    clickTarget(target);
  }

  function handleCommand(raw) {
    const command = String(raw || '').trim();
    const lower = command.toLowerCase();
    if (!lower) return;
    setStatus(`Heard: ${command}`);

    if (/^(confirm|confirm click|yes click)$/.test(lower)) {
      if (!state.pendingTarget) {
        speak('There is no pending click to confirm.');
        return;
      }
      const target = state.pendingTarget;
      state.pendingTarget = null;
      target.el.click();
      speak(`Confirmed and clicked ${target.name}.`);
      return;
    }

    if (/^(cancel|never mind|stop)$/.test(lower)) {
      state.pendingTarget = null;
      clearBadges();
      speak('Cancelled.');
      return;
    }

    if (/^(show|show targets|label|label screen|number screen)$/.test(lower)) {
      showTargets();
      return;
    }

    if (/^(clear|clear labels|hide labels)$/.test(lower)) {
      clearBadges();
      speak('Labels cleared.');
      return;
    }

    if (/^(scroll down|page down)$/.test(lower)) {
      scrollBy({ top: innerHeight * 0.75, behavior: 'smooth' });
      speak('Scrolled down.');
      return;
    }

    if (/^(scroll up|page up)$/.test(lower)) {
      scrollBy({ top: -innerHeight * 0.75, behavior: 'smooth' });
      speak('Scrolled up.');
      return;
    }

    if (/^(help|what can i say)$/.test(lower)) {
      speak('Say show targets, where is Python Compute module, click Python Compute module, click number 12, scroll down, scroll up, clear labels, or cancel.');
      return;
    }

    let match = lower.match(/^click (?:number )?(\d+)$/);
    if (match) {
      clickByNumber(Number(match[1]));
      return;
    }

    match = command.match(/^(?:where is|find|show me|locate)\s+(.+)$/i);
    if (match) {
      describe(match[1]);
      return;
    }

    match = command.match(/^(?:click|open|select|press)\s+(.+)$/i);
    if (match) {
      clickByName(match[1]);
      return;
    }

    // Plain speech defaults to guidance, not automatic clicking.
    describe(command);
  }

  function startListening() {
    ensureUi();
    if (!SpeechRecognition) {
      speak('Voice recognition is not available in this browser. Use the extension popup to type a command instead.');
      return;
    }

    if (!state.recognition) {
      const recognition = new SpeechRecognition();
      recognition.lang = 'en-US';
      recognition.interimResults = false;
      recognition.continuous = false;
      recognition.maxAlternatives = 1;
      recognition.onstart = () => {
        state.mic.classList.add('nxyz-mm-listening');
        setStatus('Listening…');
      };
      recognition.onend = () => {
        state.mic.classList.remove('nxyz-mm-listening');
      };
      recognition.onerror = (event) => {
        speak(`Microphone error: ${event.error}. You can type commands from the extension popup.`);
      };
      recognition.onresult = (event) => {
        const transcript = event.results?.[0]?.[0]?.transcript || '';
        handleCommand(transcript);
      };
      state.recognition = recognition;
    }

    try {
      state.recognition.start();
    } catch (_) {
      // Ignore duplicate start while the recognition session is already active.
    }
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type === 'NXYZ_MOUSE_MIC_COMMAND') {
      handleCommand(message.command || '');
      sendResponse({ ok: true });
      return true;
    }
    if (message?.type === 'NXYZ_MOUSE_MIC_LISTEN') {
      startListening();
      sendResponse({ ok: true });
      return true;
    }
    return false;
  });

  ensureUi();
  setStatus('NXYZ Mouse Mic ready — click 🎙️ and speak');
})();
