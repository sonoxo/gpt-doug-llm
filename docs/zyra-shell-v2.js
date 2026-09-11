(() => {
  const path = location.pathname.replace(/\/+$/, '') || '/';
  const base = path.includes('/gpt-doug-llm') ? '/gpt-doug-llm/' : '/';
  const links = [
    ['Museum + HQ', base],
    ['Planet', `${base}planet/`],
    ['Planet xZoon', `${base}planet-xzoon/`],
    ['Maven Ontology', `${base}maven-ontology/`],
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
  style.id = 'xunia-accessibility-baseline';
  style.textContent = `
    .xunia-skip-link{position:fixed;left:14px;top:10px;z-index:9999;transform:translateY(-180%);background:#fff;color:#000;padding:12px 16px;border-radius:10px;font-weight:900;text-decoration:none;box-shadow:0 8px 30px #0008}
    .xunia-skip-link:focus{transform:translateY(0)}
    .xunia-sitebar nav a{min-height:44px;display:inline-flex;align-items:center}
    .xunia-sitebar a:focus-visible,.wrap a:focus-visible,.wrap button:focus-visible,.wrap input:focus-visible,.wrap select:focus-visible{outline:3px solid #a8ff60!important;outline-offset:3px!important}
    @media(prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:.001ms!important;animation-iteration-count:1!important;transition-duration:.001ms!important;scroll-behavior:auto!important}}
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
    </nav>`;

  document.body.prepend(bar);
  document.body.prepend(skip);
  document.documentElement.classList.add('zyra-shell-ready');
})();
