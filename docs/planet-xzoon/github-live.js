(() => {
  'use strict';

  const SOURCE = './github-live.json';

  let previousHead = null;
  let previousFingerprint = null;

  const box = document.createElement('div');

  Object.assign(box.style, {
    position: 'fixed',
    zIndex: '99999',
    left: '18px',
    bottom: '18px',
    width: '300px',
    padding: '13px',
    background: '#020914ee',
    border: '1px solid #9b6cff',
    borderRadius: '11px',
    color: '#dffaff',
    font: '700 10px ui-monospace,SFMono-Regular,Menlo,monospace',
    boxShadow: '0 0 32px #9b6cff44'
  });

  box.innerHTML = `
    <div style="color:#9b6cff;letter-spacing:.13em;margin-bottom:8px">
      GITHUB REALITY STREAM
    </div>
    <div id="gh-repo">connecting...</div>
    <div id="gh-head"></div>
    <div id="gh-counts"></div>
    <div id="gh-time"></div>
    <div id="gh-event"
         style="margin-top:8px;color:#55f7a5">
    </div>
    <div style="
      height:2px;
      background:#152338;
      margin-top:10px;
      overflow:hidden">
      <div id="gh-pulse"
           style="
             width:35%;
             height:100%;
             background:#45e7ff;
             animation:ghslide 1.5s linear infinite">
      </div>
    </div>
  `;

  document.body.appendChild(box);

  const style = document.createElement('style');

  style.textContent = `
    @keyframes ghslide {
      0% { transform:translateX(-120%); }
      100% { transform:translateX(390%); }
    }

    @keyframes ghflash {
      0% {
        box-shadow:
          inset 0 0 0 9999px rgba(85,247,165,.42);
      }
      100% {
        box-shadow:
          inset 0 0 0 9999px rgba(85,247,165,0);
      }
    }
  `;

  document.head.appendChild(style);

  function el(id) {
    return document.getElementById(id);
  }

  function flash() {
    document.body.style.animation =
      'ghflash .9s ease-out';

    setTimeout(() => {
      document.body.style.animation = '';
    }, 950);
  }

  async function poll() {
    try {
      const response = await fetch(
        SOURCE + '?t=' + Date.now(),
        {cache: 'no-store'}
      );

      if (!response.ok) {
        throw new Error(
          'HTTP ' + response.status
        );
      }

      const d = await response.json();

      el('gh-repo').textContent =
        'REPO    ' + d.repository;

      el('gh-head').textContent =
        'HEAD    ' +
        (d.headSha || 'none').slice(0, 12);

      el('gh-counts').textContent =
        'COMMITS ' + d.commits +
        '   BRANCHES ' + d.branches +
        '   PRs ' + d.openPullRequests;

      el('gh-time').textContent =
        'POLL    ' +
        new Date(
          d.polledAt
        ).toLocaleTimeString();

      if (
        previousHead &&
        d.headSha &&
        previousHead !== d.headSha
      ) {
        flash();

        el('gh-event').textContent =
          'NEW COMMIT → ' +
          d.latestCommit.shortSha +
          ' · ' +
          d.latestCommit.message;
      } else if (d.latestCommit) {
        el('gh-event').textContent =
          d.latestCommit.shortSha +
          ' · ' +
          d.latestCommit.message;
      }

      if (
        previousFingerprint &&
        d.fingerprint !== previousFingerprint
      ) {
        flash();
      }

      previousHead = d.headSha;
      previousFingerprint = d.fingerprint;

      box.style.borderColor =
        '#55f7a5';

    } catch (error) {
      box.style.borderColor =
        '#ff7070';

      el('gh-event').textContent =
        'SYNC ERROR · ' + error.message;
    }
  }

  poll();

  setInterval(
    poll,
    2000
  );
})();
