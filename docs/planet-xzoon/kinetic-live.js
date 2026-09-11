(() => {
  'use strict';

  const SOURCE = '../maven-ontology/ontology.json';

  let graph = {nodes: [], links: []};
  let fingerprint = '';
  let flash = 0;
  let frame = 0;
  let lastLoad = 0;

  const stage = document.querySelector('.xz-stage');
  if (!stage) return;

  stage.style.position = 'relative';

  const canvas = document.createElement('canvas');
  canvas.id = 'xz-kinetic-layer';

  Object.assign(canvas.style, {
    position: 'absolute',
    inset: '0',
    width: '100%',
    height: '100%',
    zIndex: '3',
    pointerEvents: 'none'
  });

  stage.appendChild(canvas);

  const ctx = canvas.getContext('2d');

  const hud = document.createElement('div');
  hud.id = 'xz-kinetic-hud';

  Object.assign(hud.style, {
    position: 'absolute',
    zIndex: '5',
    right: '14px',
    top: '14px',
    width: '220px',
    padding: '12px',
    border: '1px solid #45e7ff',
    borderRadius: '10px',
    background: '#020914e8',
    color: '#dffaff',
    font: '700 10px ui-monospace,SFMono-Regular,Menlo,monospace',
    boxShadow: '0 0 30px #45e7ff33',
    pointerEvents: 'none'
  });

  stage.appendChild(hud);

  const status = document.createElement('div');
  status.textContent = 'KINETIC GRAPH ONLINE';

  Object.assign(status.style, {
    color: '#55f7a5',
    marginBottom: '8px',
    letterSpacing: '.12em'
  });

  hud.appendChild(status);

  const stats = document.createElement('div');
  hud.appendChild(stats);

  function resize() {
    const r = stage.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    canvas.width = Math.floor(r.width * dpr);
    canvas.height = Math.floor(r.height * dpr);

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  window.addEventListener('resize', resize);
  resize();

  function project(lat, lon, rot, w, h) {
    const phi = Number(lat || 0) * Math.PI / 180;
    const lambda = Number(lon || 0) * Math.PI / 180 + rot;

    let x = Math.cos(phi) * Math.sin(lambda);
    let y = Math.sin(phi);
    let z = Math.cos(phi) * Math.cos(lambda);

    const tilt = 0.14;
    const ct = Math.cos(tilt);
    const st = Math.sin(tilt);

    const yy = y * ct - z * st;
    const zz = y * st + z * ct;

    y = yy;
    z = zz;

    const R = Math.min(w, h) * 0.34;

    return {
      x: w / 2 + x * R,
      y: h / 2 - y * R,
      z,
      R
    };
  }

  function typeColor(type) {
    switch (type) {
      case 'agent': return '#45e7ff';
      case 'system': return '#9b6cff';
      case 'knowledge': return '#55f7a5';
      case 'security': return '#ff4fd8';
      case 'governance': return '#ffd166';
      default: return '#ffffff';
    }
  }

  async function loadGraph() {
    try {
      const r = await fetch(
        SOURCE + '?t=' + Date.now(),
        {cache: 'no-store'}
      );

      if (!r.ok) throw new Error('HTTP ' + r.status);

      const incoming = await r.json();

      const next =
        incoming?.meta?.liveSync?.graphFingerprint ||
        JSON.stringify(incoming).length.toString();

      if (fingerprint && next !== fingerprint) {
        flash = 1;
        status.textContent = 'GRAPH MUTATION DETECTED';
      } else {
        status.textContent = 'KINETIC GRAPH ONLINE';
      }

      fingerprint = next;

      graph = {
        nodes: Array.isArray(incoming.nodes) ? incoming.nodes : [],
        links: Array.isArray(incoming.links) ? incoming.links : []
      };

      lastLoad = Date.now();

      stats.innerHTML =
        'NODES&nbsp;&nbsp;&nbsp; ' + graph.nodes.length +
        '<br>LINKS&nbsp;&nbsp;&nbsp; ' + graph.links.length +
        '<br>GRAPH&nbsp;&nbsp;&nbsp; ' +
        String(fingerprint).slice(0, 14) +
        '<br>SYNC&nbsp;&nbsp;&nbsp;&nbsp; ' +
        new Date().toLocaleTimeString();

    } catch (err) {
      status.textContent = 'GRAPH SOURCE ERROR';
      status.style.color = '#ff7070';
      console.error(err);
    }
  }

  setInterval(loadGraph, 2000);
  loadGraph();

  function drawGrid(cx, cy, R, t) {
    ctx.save();

    ctx.strokeStyle = 'rgba(69,231,255,.20)';
    ctx.lineWidth = 1;

    for (let i = 0; i < 5; i++) {
      const rr = R * (0.30 + i * 0.16);

      ctx.beginPath();
      ctx.arc(
        cx,
        cy,
        rr,
        t * (0.15 + i * 0.03),
        t * (0.15 + i * 0.03) + Math.PI * 1.15
      );
      ctx.stroke();
    }

    ctx.restore();
  }

  function drawScanner(cx, cy, R, t) {
    const a = t * 0.8;

    ctx.save();

    ctx.translate(cx, cy);
    ctx.rotate(a);

    const grad = ctx.createLinearGradient(0, 0, R, 0);
    grad.addColorStop(0, 'rgba(69,231,255,.04)');
    grad.addColorStop(1, 'rgba(69,231,255,.65)');

    ctx.strokeStyle = grad;
    ctx.lineWidth = 2;

    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(R, 0);
    ctx.stroke();

    ctx.restore();
  }

  function draw() {
    requestAnimationFrame(draw);

    const r = stage.getBoundingClientRect();
    const w = r.width;
    const h = r.height;

    ctx.clearRect(0, 0, w, h);

    frame++;

    const t = performance.now() / 1000;

    /* deliberately obvious motion */
    const rot = t * 0.23;

    const R = Math.min(w, h) * 0.34;
    const cx = w / 2;
    const cy = h / 2;

    drawGrid(cx, cy, R, t);
    drawScanner(cx, cy, R, t);

    const map = new Map(
      graph.nodes.map(n => [n.id, n])
    );

    /*
      MOVING DATA PACKETS:
      each ontology relationship gets a traveling pulse.
    */
    graph.links.forEach((edge, index) => {
      const a = map.get(edge[0]);
      const b = map.get(edge[1]);

      if (!a || !b) return;

      const p = project(a.lat, a.lon, rot, w, h);
      const q = project(b.lat, b.lon, rot, w, h);

      if (p.z < -0.12 || q.z < -0.12) return;

      const mx = (p.x + q.x) / 2;
      const my = (p.y + q.y) / 2 - 30;

      ctx.strokeStyle = 'rgba(69,231,255,.25)';
      ctx.lineWidth = 1.3;

      ctx.beginPath();
      ctx.moveTo(p.x, p.y);
      ctx.quadraticCurveTo(mx, my, q.x, q.y);
      ctx.stroke();

      const speed = 0.24 + (index % 7) * 0.025;
      const u = (t * speed + index * 0.117) % 1;

      const one = 1 - u;

      const bx =
        one * one * p.x +
        2 * one * u * mx +
        u * u * q.x;

      const by =
        one * one * p.y +
        2 * one * u * my +
        u * u * q.y;

      ctx.shadowBlur = 16;
      ctx.shadowColor = '#55f7ff';
      ctx.fillStyle = '#ffffff';

      ctx.beginPath();
      ctx.arc(bx, by, 2.6, 0, Math.PI * 2);
      ctx.fill();

      ctx.shadowBlur = 0;
    });

    /*
      PULSING REAL ONTOLOGY NODES
    */
    graph.nodes.forEach((node, index) => {
      const p = project(
        node.lat,
        node.lon,
        rot,
        w,
        h
      );

      if (p.z < -0.08) return;

      const color = typeColor(node.type);

      const pulse =
        1 +
        Math.sin(t * 4.5 + index * 0.7) * 0.35;

      const radius =
        (4 + Math.max(0, p.z) * 4) * pulse;

      ctx.shadowBlur = 22;
      ctx.shadowColor = color;
      ctx.fillStyle = color;

      ctx.beginPath();
      ctx.arc(
        p.x,
        p.y,
        radius,
        0,
        Math.PI * 2
      );
      ctx.fill();

      ctx.shadowBlur = 0;

      ctx.strokeStyle = color;
      ctx.globalAlpha = 0.32;

      ctx.beginPath();
      ctx.arc(
        p.x,
        p.y,
        radius + 5 + ((t * 14 + index) % 12),
        0,
        Math.PI * 2
      );
      ctx.stroke();

      ctx.globalAlpha = 1;
    });

    /*
      VISIBLE ORBITING SATELLITES
    */
    for (let i = 0; i < 10; i++) {
      const a =
        t * (0.32 + i * 0.012) +
        i * Math.PI * 2 / 10;

      const rr =
        R * (1.05 + (i % 3) * 0.06);

      const x = cx + Math.cos(a) * rr;
      const y =
        cy +
        Math.sin(a) *
        rr *
        (0.34 + (i % 2) * 0.08);

      ctx.fillStyle =
        i % 2 ? '#9b6cff' : '#45e7ff';

      ctx.shadowBlur = 18;
      ctx.shadowColor = ctx.fillStyle;

      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fill();

      ctx.shadowBlur = 0;
    }

    /*
      LARGE FLASH ONLY WHEN THE ONTOLOGY HASH CHANGES.
    */
    if (flash > 0) {
      ctx.strokeStyle =
        `rgba(85,247,165,${flash})`;

      ctx.lineWidth = 6;

      ctx.beginPath();
      ctx.arc(
        cx,
        cy,
        R * (1.05 + (1 - flash) * 0.4),
        0,
        Math.PI * 2
      );
      ctx.stroke();

      flash -= 0.015;

      if (flash < 0) flash = 0;
    }

    /*
      HEARTBEAT: proves renderer is alive even
      when no external graph mutation occurs.
    */
    const heartbeat =
      document.getElementById('xz-kinetic-heartbeat');

    if (heartbeat) {
      heartbeat.style.opacity =
        String(0.45 + Math.sin(t * 5) * 0.4);
    }
  }

  const heartbeat = document.createElement('div');
  heartbeat.id = 'xz-kinetic-heartbeat';
  heartbeat.textContent = '● LIVE RENDER';

  Object.assign(heartbeat.style, {
    position: 'absolute',
    zIndex: '5',
    right: '16px',
    bottom: '48px',
    color: '#55f7a5',
    font: '800 10px ui-monospace,SFMono-Regular,Menlo,monospace',
    textShadow: '0 0 12px #55f7a5'
  });

  stage.appendChild(heartbeat);

  draw();
})();
