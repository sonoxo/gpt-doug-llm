(() => {
  'use strict';

  const endpoint = '../maven-ontology/ontology.json';
  const pollMs = 3000;

  let lastFingerprint = null;
  let loading = false;

  function badge() {
    let el = document.getElementById('xz-foundry-live');

    if (el) return el;

    el = document.createElement('span');
    el.id = 'xz-foundry-live';

    Object.assign(el.style, {
      marginLeft: '10px',
      padding: '5px 8px',
      border: '1px solid #55f7a5',
      borderRadius: '999px',
      fontFamily: 'ui-monospace,SFMono-Regular,Menlo,monospace',
      fontSize: '9px',
      color: '#55f7a5',
      boxShadow: '0 0 12px #55f7a533'
    });

    el.textContent = 'FOUNDRY SYNC...';

    const host =
      document.querySelector('.xz-live') ||
      document.querySelector('.xz-head');

    if (host) host.appendChild(el);

    return el;
  }

  function log(message) {
    const stream = document.getElementById('xz-stream');

    if (!stream) return;

    const row = document.createElement('div');
    row.className = 'xz-event';
    row.innerHTML =
      '<b>Foundry</b> ' +
      String(message)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    stream.prepend(row);

    while (stream.children.length > 12) {
      stream.lastChild.remove();
    }
  }

  async function poll() {
    if (loading) return;

    loading = true;

    const b = badge();

    try {
      const url =
        endpoint +
        '?t=' +
        Date.now();

      const response = await fetch(url, {
        cache: 'no-store'
      });

      if (!response.ok) {
        throw new Error('HTTP ' + response.status);
      }

      const ontology = await response.json();

      const sync =
        ontology.meta &&
        ontology.meta.liveSync
          ? ontology.meta.liveSync
          : {};

      const fingerprint =
        sync.graphFingerprint || 'unknown';

      const real =
        sync.remotePutVerified === true &&
        sync.remoteGetVerified === true &&
        sync.sha256Verified === true;

      b.textContent = real
        ? 'FOUNDRY VERIFIED · LIVE'
        : 'ONTOLOGY LIVE';

      b.style.color = real
        ? '#55f7a5'
        : '#ffd166';

      b.style.borderColor = real
        ? '#55f7a5'
        : '#ffd166';

      if (fingerprint !== lastFingerprint) {
        const previous = lastFingerprint;
        lastFingerprint = fingerprint;

        const loadButton =
          document.getElementById('xz-maven');

        if (loadButton) {
          loadButton.click();
        }

        if (previous !== null) {
          log(
            'graph updated · ' +
            fingerprint.slice(0, 12)
          );
        } else {
          log(
            'real Maven graph loaded · ' +
            fingerprint.slice(0, 12)
          );
        }
      }
    } catch (error) {
      b.textContent = 'FOUNDRY SYNC ERROR';
      b.style.color = '#ff7070';
      b.style.borderColor = '#ff7070';

      console.error(
        '[Planet xZoon live sync]',
        error
      );
    } finally {
      loading = false;
    }
  }

  window.addEventListener(
    'DOMContentLoaded',
    () => {
      badge();
      poll();
      setInterval(poll, pollMs);
    }
  );
})();
