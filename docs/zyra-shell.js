(() => {
  const path = location.pathname.replace(/\/+$/, '') || '/';
  const base = path.includes('/gpt-doug-llm') ? '/gpt-doug-llm/' : '/';
  const links = [
    ['Home', base],
    ['Eye Mouse', `${base}eye-mouse/`],
    ['Status', `${base}status.html`],
    ['Metrics', `${base}metrics.html`],
    ['Pipeline', `${base}pipeline.html`],
  ];

  const current = (href) => {
    const normalized = href.replace(/\/+$/, '') || '/';
    const here = location.pathname.replace(/\/+$/, '') || '/';
    return here === normalized || (href.endsWith('/eye-mouse/') && here.endsWith('/eye-mouse'));
  };

  const bar = document.createElement('div');
  bar.className = 'xunia-sitebar';
  bar.setAttribute('role', 'banner');
  bar.innerHTML = `
    <a class="brand" href="${base}" aria-label="XUNIAverse home">
      <span class="brand-mark" aria-hidden="true">X</span>
      <span>XUNIA<small>ZYRA ECOSYSTEM</small></span>
    </a>
    <nav aria-label="Public site navigation">
      ${links.map(([label, href]) => `<a href="${href}"${current(href) ? ' aria-current="page"' : ''}>${label}</a>`).join('')}
      <a href="https://github.com/sonoxo/gpt-doug-llm" rel="noopener">GitHub ↗</a>
    </nav>`;

  document.body.prepend(bar);
  document.documentElement.classList.add('zyra-shell-ready');
})();
