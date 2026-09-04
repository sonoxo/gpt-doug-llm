(() => {
  const BRAND = 'THE GREEN HOUSE';
  const SUBTITLE = 'ECO · BIO · PHARMA · FDA · GLOBAL INTELLIGENCE';

  document.title = 'The Green House — Global Intelligence Monitor';

  const mount = () => {
    if (document.getElementById('green-house-runtime-brand')) return;

    const style = document.createElement('style');
    style.id = 'green-house-runtime-brand-style';
    style.textContent = `
      #green-house-runtime-brand {
        position: fixed;
        right: 12px;
        bottom: 12px;
        z-index: 2147483000;
        display: grid;
        gap: 2px;
        padding: 9px 12px;
        border: 1px solid rgba(118,255,165,.45);
        border-radius: 8px;
        background: rgba(5,20,12,.88);
        color: #b8ffd0;
        font: 700 11px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace;
        letter-spacing: .08em;
        box-shadow: 0 0 24px rgba(31,255,116,.12);
        backdrop-filter: blur(10px);
        pointer-events: none;
      }
      #green-house-runtime-brand small {
        color: rgba(210,255,224,.72);
        font-size: 8px;
        font-weight: 600;
        letter-spacing: .04em;
      }
      #green-house-runtime-brand .gh-provenance {
        color: rgba(210,255,224,.48);
        font-size: 7px;
      }
    `;
    document.head.appendChild(style);

    const badge = document.createElement('aside');
    badge.id = 'green-house-runtime-brand';
    badge.setAttribute('aria-label', 'The Green House runtime identity');
    badge.innerHTML = `<span>${BRAND}</span><small>${SUBTITLE}</small><span class="gh-provenance">WorldMonitor engine · AGPL-3.0</span>`;
    document.body.appendChild(badge);

    // Replace only obvious UI branding nodes, never source/license/documentation text.
    const applyBrand = (root = document) => {
      const selectors = 'h1,[class*="brand"],[class*="Brand"],[class*="logo"],[class*="Logo"]';
      root.querySelectorAll?.(selectors).forEach((el) => {
        if (el.children.length === 0 && /^world\s*monitor$/i.test((el.textContent || '').trim())) {
          el.textContent = BRAND;
        }
      });
    };

    applyBrand();
    new MutationObserver(() => applyBrand()).observe(document.body, { childList: true, subtree: true });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount, { once: true });
  } else {
    mount();
  }
})();
