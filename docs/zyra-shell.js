(() => {
  const path = location.pathname.replace(/\/+$/, '') || '/';
  const base = path.includes('/gpt-doug-llm') ? '/gpt-doug-llm/' : '/';
  const links = [
    ['Museum + HQ', base],
    ['Resources', `${base}resources.html`],
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
  document.documentElement.classList.add('zyra-shell-ready');
})();
