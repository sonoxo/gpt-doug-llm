/* Local-only OSIRIS visual controls and PINEAL public feed-health display. */
(() => {
  'use strict';
  const allowedRoutes = ['health','earthquakes','fires','weather','air-quality','space-weather','news','live-news','gdelt','markets'];
  const byId = id => document.getElementById(id);
  const boxes = [...document.querySelectorAll('#layers input[type=checkbox]')];
  let baseMap = 'http://127.0.0.1:3000/';
  let busy = false;

  function selectedLayers() {
    return boxes.filter(box => box.checked).map(box => box.value);
  }
  function updateMapLink() {
    const url = new URL(baseMap);
    const active = selectedLayers();
    url.searchParams.set('layers', active.join(','));
    byId('open-map').href = url.toString();
    byId('selected-count').textContent = active.length + ' SELECTED';
  }
  function shortTime(value) {
    if (!value) return '—';
    const t = new Date(value);
    return Number.isFinite(t.getTime()) ? t.toLocaleString() : '—';
  }
  function statusClass(text) {
    return ['ONLINE','DEGRADED','STALE','CLOCK_SKEW','UNAVAILABLE'].includes(text) ? text : 'UNAVAILABLE';
  }
  function makeRoute(name, record) {
    const status = statusClass(record && record.status);
    const row = document.createElement('div');
    row.className = 'route';
    const label = document.createElement('span');
    label.className = 'label';
    label.textContent = name.replaceAll('-', ' ');
    const flag = document.createElement('span');
    flag.className = 'status ' + status;
    flag.textContent = status === 'CLOCK_SKEW' ? 'CLOCK SKEW' : status;
    const stamp = document.createElement('span');
    stamp.className = 'stamp';
    stamp.textContent = shortTime(record && record.last_check_utc);
    if (record && record.latency_ms !== null && record.latency_ms !== undefined) {
      stamp.title = String(record.latency_ms) + ' ms request latency';
    }
    row.append(label, flag, stamp);
    return row;
  }

  function render(data) {
    let candidate;
    try {
      candidate = new URL(data.map_url);
      if (candidate.protocol === 'http:' && candidate.hostname === '127.0.0.1'
          && candidate.port && candidate.username === '' && candidate.password === '') {
        baseMap = candidate.origin + '/';
      }
    } catch (_) { /* Keep known local fallback. */ }
    updateMapLink();

    const processOK = Boolean(data.dashboard && data.dashboard.serving);
    byId('map-state').textContent = processOK ? 'SERVING' : 'OFFLINE';
    byId('map-state').className = 'metric-val ' + (processOK ? 'ok' : 'bad');

    const routes = data.safe_routes && typeof data.safe_routes === 'object' ? data.safe_routes : {};
    const present = allowedRoutes.filter(key => Object.hasOwn(routes, key));
    const online = present.filter(key => routes[key] && routes[key].status === 'ONLINE').length;
    const degraded = present.filter(key => routes[key] && routes[key].status !== 'ONLINE').length;
    byId('feed-count').textContent = online + ' / ' + allowedRoutes.length;
    byId('feed-count').className = 'metric-val ' + (online > 0 ? 'ok' : 'unavailable');
    byId('feed-degraded').textContent = degraded + (present.length ? '' : ' · UNKNOWN');
    byId('feed-degraded').className = 'metric-val ' + (degraded ? 'warn' : 'unavailable');
    byId('snapshot-state').textContent = present.length ? 'OBSERVED ' + present.length : 'NO SNAPSHOT';
    byId('snapshot-time').textContent = shortTime(data.snapshot_generated_at_utc);
    const container = byId('routes');
    container.replaceChildren(...allowedRoutes.map(name => makeRoute(name, routes[name])));

    const pineal = data.pineal || {};
    const pinealAvailable = pineal.state === 'LOCAL';
    byId('memory-count').textContent = pinealAvailable ? String(pineal.feed_health_records) : '—';
    byId('memory-count').className = 'metric-val ' + (pinealAvailable ? 'ok' : 'unavailable');
    byId('pineal-state').textContent = pinealAvailable ?
      'Local SQLite • ' + pineal.audit_entries + ' audit records (integrity not asserted)' :
      'PINEAL database not connected';
    byId('last-check').textContent = new Date().toLocaleTimeString();
  }

  async function refresh() {
    if (busy) return;
    busy = true;
    byId('refresh').disabled = true;
    const abort = new AbortController();
    const guard = window.setTimeout(() => abort.abort(), 7000);
    try {
      const response = await fetch('/api/status', {cache:'no-store',signal:abort.signal});
      if (!response.ok) throw Error('HTTP ' + response.status);
      const data = await response.json();
      render(data);
    } catch (_) {
      byId('map-state').textContent = 'UNAVAILABLE';
      byId('map-state').className = 'metric-val warn';
      byId('last-check').textContent = 'Status service unreachable';
    } finally {
      window.clearTimeout(guard);
      byId('refresh').disabled = false;
      busy = false;
    }
  }

  boxes.forEach(box => box.addEventListener('change', updateMapLink));
  byId('refresh').addEventListener('click', refresh);
  updateMapLink();
  const clock = () => byId('clock').textContent = 'UTC ' + new Date().toISOString().slice(11,19) + 'Z';
  clock();
  window.setInterval(clock,1000);
  refresh();
  window.setInterval(refresh,15000);
})();