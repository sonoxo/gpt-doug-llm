(() => {
  const path = location.pathname.replace(/\/+$/, '') || '/';
  const base = path.includes('/gpt-doug-llm') ? '/gpt-doug-llm/' : '/';
  const links = [
    ['Museum + HQ', base],
    ['Planet', `${base}planet/`],
    ['Documentation', `${base}documentation.html`],
    ['Resources', `${base}resources.html`],
    ['Arcade', `${base}arcade/`],
    ['Experiments', `${base}experiments.html`],
    ['Status', `${base}status.html`],
    ['Metrics', `${base}metrics.html`],
    ['Pipeline', `${base}pipeline.html`],
  ];

  const current = (href) => {
    const normalized = href.replace(/\/+$/, '') || '/';
    const here = location.pathname.replace(/\/+$/, '') || '/';
    return here === normalized;
  };

  const style = document.createElement('style');
  style.id = 'xunia-public-accessibility-styles';
  style.textContent = `
    .xunia-skip-link{position:fixed;left:14px;top:10px;z-index:9999;transform:translateY(-180%);background:#fff;color:#000;padding:12px 16px;border-radius:10px;font-weight:900;text-decoration:none;box-shadow:0 8px 30px #0008}
    .xunia-skip-link:focus{transform:translateY(0)}
    .xunia-sitebar nav a,.xunia-a11y-toggle{min-height:44px;display:inline-flex;align-items:center;justify-content:center}
    .xunia-a11y-toggle{border:1px solid #353a64;border-radius:999px;background:#12152b;color:#eff7ff;padding:8px 12px;font:inherit;font-size:12px;font-weight:800;cursor:pointer}
    .xunia-sitebar a:focus-visible,.xunia-sitebar button:focus-visible,.xunia-a11y-panel button:focus-visible,.wrap a:focus-visible,.wrap button:focus-visible,.wrap input:focus-visible,.wrap select:focus-visible{outline:3px solid #a8ff60!important;outline-offset:3px!important}
    .xunia-a11y-panel{position:fixed;right:18px;top:74px;z-index:90;width:min(360px,calc(100vw - 28px));padding:16px;border:1px solid #3b416c;border-radius:16px;background:#090b1bf5;box-shadow:0 18px 70px #000a;color:#eff7ff;backdrop-filter:blur(18px)}
    .xunia-a11y-panel[hidden]{display:none}
    .xunia-a11y-panel h2{margin:0 0 5px;font-size:18px}.xunia-a11y-panel p{margin:0 0 12px;color:#cfd8ff;font-size:14px;line-height:1.55}
    .xunia-a11y-actions{display:grid;grid-template-columns:1fr;gap:8px}.xunia-a11y-actions button{min-height:48px;border:1px solid #353a64;border-radius:10px;background:#11142a;color:#eff7ff;text-align:left;padding:10px 12px;font-weight:800;cursor:pointer}.xunia-a11y-actions button[aria-pressed="true"]{border-color:#46f3ff;background:#122236;box-shadow:inset 0 0 0 1px #46f3ff55}
    html.xunia-comfort-view body{--dim:#c4cde3!important;--text-muted:#c4cde3!important}html.xunia-comfort-view .zyra-hero p,html.xunia-comfort-view .zyra-card p,html.xunia-comfort-view .hq-note,html.xunia-comfort-view .museum-map p,html.xunia-comfort-view .zyra-footer{font-size:17px!important;line-height:1.75!important}html.xunia-comfort-view .xunia-sitebar nav a{font-size:14px!important}html.xunia-comfort-view .zyra-card h2{font-size:23px!important}
    html.xunia-high-contrast body{--bg:#000!important;--surface:#050505!important;--surface-2:#0a0a0a!important;--line:#6f7898!important;--dim:#e3e7f3!important;--ink:#fff!important;background:#000!important}html.xunia-high-contrast .zyra-hero,html.xunia-high-contrast .zyra-card,html.xunia-high-contrast .motion-panel{background:#050505!important;border-color:#7c86a8!important}html.xunia-high-contrast .xunia-sitebar{background:#000!important}
    html.xunia-reduce-motion *,html.xunia-reduce-motion *::before,html.xunia-reduce-motion *::after{animation-duration:.001ms!important;animation-iteration-count:1!important;transition-duration:.001ms!important;scroll-behavior:auto!important}
    @media(max-width:700px){.xunia-sitebar{gap:8px}.xunia-a11y-toggle{width:100%;margin-top:6px}.xunia-a11y-panel{top:12px;right:14px}.xunia-sitebar nav{overflow-x:auto;flex-wrap:nowrap!important;justify-content:flex-start!important;padding-bottom:4px}.xunia-sitebar nav a{white-space:nowrap}}
  `;
  document.head.append(style);

  const main = document.querySelector('main');
  if (main && !main.id) main.id = 'xunia-main-content';

  const skip = document.createElement('a');
  skip.className = 'xunia-skip-link';
  skip.href = '#xunia-main-content';
  skip.textContent = 'Skip to main content';

  const bar = document.createElement('div');
  bar.className = 'xunia-sitebar';
  bar.setAttribute('role', 'banner');
  bar.innerHTML = `
    <a class="brand" href="${base}" aria-label="XUNIA Museum and Headquarters home">
      <span class="brand-mark" aria-hidden="true">X</span>
      <span>XUNIA<small>MUSEUM + HQ</small></span>
    </a>
    <nav aria-label="Public site navigation">
      ${links.map(([label, href]) => `<a href="${href}"${current(href) ? ' aria-current="page"' : ''}>${label}</a>`).join('')}
      <a href="https://github.com/sonoxo" rel="noopener">Repository Fleet ↗</a>
    </nav>
    <button class="xunia-a11y-toggle" type="button" aria-expanded="false" aria-controls="xunia-accessibility-panel">Accessibility</button>`;

  const panel = document.createElement('section');
  panel.id = 'xunia-accessibility-panel';
  panel.className = 'xunia-a11y-panel';
  panel.hidden = true;
  panel.setAttribute('aria-label', 'Accessibility preferences');
  panel.innerHTML = `
    <h2>Accessibility</h2>
    <p>Make XUNIA easier to read and navigate. These preferences stay on this device.</p>
    <div class="xunia-a11y-actions">
      <button type="button" data-pref="comfort" aria-pressed="false">Larger, clearer text</button>
      <button type="button" data-pref="contrast" aria-pressed="false">Higher contrast</button>
      <button type="button" data-pref="motion" aria-pressed="false">Reduce motion and visual effects</button>
    </div>`;

  document.body.prepend(panel);
  document.body.prepend(bar);
  document.body.prepend(skip);

  const storageKey = 'xunia-public-accessibility-v1';
  let state = { comfort: false, contrast: false, motion: matchMedia('(prefers-reduced-motion: reduce)').matches };
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || '{}');
    state = { ...state, ...saved };
  } catch (_) {}

  const applyState = () => {
    document.documentElement.classList.toggle('xunia-comfort-view', !!state.comfort);
    document.documentElement.classList.toggle('xunia-high-contrast', !!state.contrast);
    document.documentElement.classList.toggle('xunia-reduce-motion', !!state.motion);
    panel.querySelectorAll('[data-pref]').forEach((button) => {
      button.setAttribute('aria-pressed', String(!!state[button.dataset.pref]));
    });
    try { localStorage.setItem(storageKey, JSON.stringify(state)); } catch (_) {}
  };

  const toggle = bar.querySelector('.xunia-a11y-toggle');
  toggle.addEventListener('click', () => {
    panel.hidden = !panel.hidden;
    toggle.setAttribute('aria-expanded', String(!panel.hidden));
    if (!panel.hidden) panel.querySelector('button')?.focus();
  });
  panel.addEventListener('click', (event) => {
    const button = event.target.closest('[data-pref]');
    if (!button) return;
    state[button.dataset.pref] = !state[button.dataset.pref];
    applyState();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !panel.hidden) {
      panel.hidden = true;
      toggle.setAttribute('aria-expanded', 'false');
      toggle.focus();
    }
  });

  applyState();
  document.documentElement.classList.add('zyra-shell-ready');
})();
