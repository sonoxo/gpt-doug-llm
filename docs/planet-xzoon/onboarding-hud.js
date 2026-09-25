(() => {
  'use strict';

  const ONTOLOGY = '../maven-ontology/ontology.json';
  const GITHUB = './github-live.json';

  let graph = null;
  let github = null;
  let step = 0;
  let paused = false;
  let lastFingerprint = null;
  let timer = null;

  const root = document.createElement('section');
  root.id = 'xzoon-explainer';

  root.setAttribute(
    'aria-label',
    'Planet xZoon ontology explainer'
  );

  root.innerHTML = `
    <div class="xo-head">
      <div>
        <div class="xo-eyebrow">PLANET xZOON GUIDE</div>
        <div class="xo-title">WHAT IS THE ONTOLOGY DOING?</div>
      </div>

      <div class="xo-live">
        <span class="xo-live-dot"></span>
        <span id="xo-live-text">READING GRAPH</span>
      </div>
    </div>

    <div class="xo-now" id="xo-now">
      Connecting to ontology...
    </div>

    <div class="xo-message">
      <div class="xo-step" id="xo-step"></div>
      <div class="xo-main" id="xo-main"></div>
      <div class="xo-detail" id="xo-detail"></div>
    </div>

    <div class="xo-metrics">
      <div>
        <span>NODES</span>
        <b id="xo-nodes">0</b>
      </div>

      <div>
        <span>LINKS</span>
        <b id="xo-links">0</b>
      </div>

      <div>
        <span>VERIFIED</span>
        <b id="xo-verified">0</b>
      </div>

      <div>
        <span>GRAPH</span>
        <b id="xo-hash">--------</b>
      </div>
    </div>

    <div class="xo-actions">
      <button id="xo-prev" type="button">BACK</button>

      <div class="xo-progress" id="xo-progress"></div>

      <button id="xo-pause" type="button">PAUSE</button>
      <button id="xo-next" type="button">NEXT</button>
      <button id="xo-hide" type="button">HIDE</button>
    </div>
  `;

  const launcher = document.createElement('button');

  launcher.id = 'xzoon-guide-launcher';
  launcher.type = 'button';
  launcher.textContent = '? EXPLAIN xZOON';

  const style = document.createElement('style');

  style.textContent = `
    #xzoon-explainer {
      position: fixed;
      left: 50%;
      bottom: 20px;
      transform: translateX(-50%);
      width: min(720px, calc(100vw - 34px));
      z-index: 100000;
      box-sizing: border-box;

      background:
        linear-gradient(
          145deg,
          rgba(3, 12, 25, .97),
          rgba(4, 22, 34, .95)
        );

      border: 1px solid rgba(69, 231, 255, .65);
      border-radius: 15px;
      padding: 15px 17px;

      color: #e8f7ff;

      box-shadow:
        0 0 0 1px rgba(155,108,255,.13),
        0 0 38px rgba(69,231,255,.17),
        inset 0 0 28px rgba(69,231,255,.035);

      backdrop-filter: blur(18px);

      font-family:
        ui-monospace,
        SFMono-Regular,
        Menlo,
        Monaco,
        Consolas,
        monospace;
    }

    #xzoon-explainer.xo-change {
      animation: xoGraphChange 1.4s ease-out;
    }

    @keyframes xoGraphChange {
      0% {
        border-color: #55f7a5;
        box-shadow:
          0 0 65px rgba(85,247,165,.75);
      }

      100% {
        border-color: rgba(69,231,255,.65);
      }
    }

    .xo-head {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 14px;
    }

    .xo-eyebrow {
      color: #45e7ff;
      font-size: 9px;
      letter-spacing: .18em;
      font-weight: 900;
    }

    .xo-title {
      margin-top: 3px;
      color: #ffffff;
      font-size: 16px;
      font-weight: 900;
      letter-spacing: .035em;
    }

    .xo-live {
      white-space: nowrap;
      color: #55f7a5;
      font-size: 9px;
      font-weight: 900;
      padding-top: 3px;
    }

    .xo-live-dot {
      display: inline-block;
      width: 7px;
      height: 7px;
      margin-right: 5px;
      border-radius: 50%;
      background: #55f7a5;

      box-shadow:
        0 0 10px #55f7a5,
        0 0 20px rgba(85,247,165,.5);

      animation: xoPulse 1.2s infinite;
    }

    @keyframes xoPulse {
      50% {
        opacity: .35;
        transform: scale(.7);
      }
    }

    .xo-now {
      margin-top: 11px;
      padding: 7px 9px;

      border-left: 2px solid #55f7a5;

      background:
        rgba(85,247,165,.055);

      color: #a9ffd3;

      font-size: 10px;
      line-height: 1.5;
    }

    .xo-message {
      min-height: 104px;
      padding: 13px 2px 8px;
    }

    .xo-step {
      color: #9b6cff;
      font-size: 9px;
      font-weight: 900;
      letter-spacing: .14em;
    }

    .xo-main {
      margin-top: 6px;
      color: #ffffff;
      font-size: 14px;
      line-height: 1.42;
      font-weight: 800;
    }

    .xo-detail {
      margin-top: 6px;
      color: #8fb3c8;
      font-size: 10px;
      line-height: 1.55;
    }

    .xo-metrics {
      display: grid;
      grid-template-columns:
        repeat(4, minmax(0, 1fr));

      gap: 7px;

      margin: 4px 0 12px;
    }

    .xo-metrics div {
      padding: 7px 8px;

      border: 1px solid rgba(69,231,255,.17);
      border-radius: 8px;

      background:
        rgba(3,11,20,.6);
    }

    .xo-metrics span {
      display: block;

      color: #628aa2;

      font-size: 8px;
      letter-spacing: .1em;
    }

    .xo-metrics b {
      display: block;

      margin-top: 3px;

      overflow: hidden;

      color: #dfffff;

      font-size: 10px;

      text-overflow: ellipsis;
    }

    .xo-actions {
      display: flex;
      align-items: center;
      gap: 7px;
    }

    .xo-actions button,
    #xzoon-guide-launcher {
      cursor: pointer;

      border:
        1px solid rgba(69,231,255,.35);

      border-radius: 7px;

      background: #061421;
      color: #bcefff;

      padding: 6px 8px;

      font:
        800 9px
        ui-monospace,
        SFMono-Regular,
        Menlo,
        monospace;
    }

    .xo-actions button:hover,
    #xzoon-guide-launcher:hover {
      border-color: #45e7ff;
      color: #ffffff;
    }

    .xo-progress {
      flex: 1;

      display: flex;
      justify-content: center;
      gap: 5px;
    }

    .xo-progress i {
      width: 5px;
      height: 5px;

      border-radius: 50%;

      background: #25465a;
    }

    .xo-progress i.active {
      background: #45e7ff;
      box-shadow: 0 0 8px #45e7ff;
    }

    #xzoon-guide-launcher {
      position: fixed;
      left: 50%;
      bottom: 18px;

      transform: translateX(-50%);

      display: none;

      z-index: 100000;

      padding: 8px 13px;

      border-color: #45e7ff;

      box-shadow:
        0 0 20px rgba(69,231,255,.25);
    }

    @media (max-width: 700px) {
      #xzoon-explainer {
        bottom: 8px;
      }

      .xo-metrics {
        grid-template-columns:
          repeat(2, minmax(0, 1fr));
      }

      .xo-title {
        font-size: 12px;
      }
    }
  `;

  document.head.appendChild(style);
  document.body.appendChild(root);
  document.body.appendChild(launcher);

  const $ = id =>
    document.getElementById(id);

  function sync() {
    return graph?.meta?.liveSync || {};
  }

  function counts() {
    const nodes =
      Array.isArray(graph?.nodes)
        ? graph.nodes
        : [];

    const links =
      Array.isArray(graph?.links)
        ? graph.links
        : [];

    const verified =
      nodes.filter(
        n => n.status === 'verified'
      ).length;

    return {
      nodes,
      links,
      verified
    };
  }

  const messages = [
    () => ({
      title:
        'This globe is a visual map of the XUNIA / GPT-DOUG knowledge model.',

      detail:
        'Each glowing dot is an ontology object. The globe turns structured software, evidence, systems, agents and governance concepts into something you can explore.'
    }),

    () => {
      const c = counts();

      return {
        title:
          `Right now xZOON has ${c.nodes.length} objects and ${c.links.length} relationships loaded.`,

        detail:
          'The HUD reads the same ontology JSON used by the visualizer. Counts shown here are graph data, not decorative numbers.'
      };
    },

    () => ({
      title:
        'Dots are things. Lines explain how those things relate.',

      detail:
        'Examples include Agent, System, Artifact, Evidence, Mission, Control, Dataset and Threat. Relationships can mean USES, GOVERNS, DERIVED_FROM, REQUIRES, EXECUTES, MITIGATES and more.'
    }),

    () => ({
      title:
        'Color and status help explain what kind of knowledge you are looking at.',

      detail:
        'Agents, systems, knowledge, security and governance use different visual categories. VERIFIED means the graph carries a verified state; CANDIDATE means it should not be treated as fully verified.'
    }),

    () => ({
      title:
        'Moving dots and packets are visualization — not proof that an external event happened.',

      detail:
        'Rotation, pulses, orbiters and traveling particles make relationships easier to see. A real data change is represented separately by a new source state or a changed graph fingerprint.'
    }),

    () => {
      const s = sync();

      const put =
        s.remotePutVerified === true;

      const get =
        s.remoteGetVerified === true;

      const sha =
        s.sha256Verified === true;

      return {
        title:
          put && get && sha
            ? 'The graph contains a cryptographically verified Foundry Maven release.'
            : 'The ontology tracks provenance and verification state.',

        detail:
          put && get && sha
            ? 'The recorded Maven artifact was remotely written, retrieved and checked with SHA-256. That verification is represented as Artifact and Evidence objects.'
            : 'Provenance tells you where knowledge came from and how its verification status was established.'
      };
    },

    () => {
      if (github) {
        const sha =
          github.headSha
            ? github.headSha.slice(0, 8)
            : 'unknown';

        return {
          title:
            `GitHub reality stream is watching repository state. Current HEAD: ${sha}.`,

          detail:
            `${github.commits || 0} recent commits, ${github.branches || 0} branches and ${github.openPullRequests || 0} open pull requests are represented by the live GitHub bridge.`
        };
      }

      return {
        title:
          'Live sources can update the ontology as the ecosystem changes.',

        detail:
          'Git commits, branches, pull requests, Foundry artifacts and other approved sources can become graph objects instead of being shown as static text.'
      };
    },

    () => ({
      title:
        'The graph fingerprint tells you whether the ontology itself changed.',

      detail:
        'If nodes or relationships change, the SHA-256 graph fingerprint changes. xZOON will flash the HUD and report REAL GRAPH CHANGE DETECTED.'
    }),

    () => ({
      title:
        'How to explore: click an object, search by name, and follow its relationships.',

      detail:
        'Use the object list to focus on a node. Ask: What is this? Where did it come from? What does it depend on? What does it govern? What evidence supports it?'
    }),

    () => ({
      title:
        'Think of Planet xZOON as a living digital map of the software ecosystem.',

      detail:
        'The goal is to show what exists, how it connects, what changed, where the evidence came from, and which parts are healthy, candidate or verified.'
    })
  ];

  function progress() {
    const holder = $('xo-progress');

    holder.innerHTML = '';

    messages.forEach((_, i) => {
      const dot =
        document.createElement('i');

      if (i === step) {
        dot.classList.add('active');
      }

      holder.appendChild(dot);
    });
  }

  function render() {
    const item = messages[step]();

    $('xo-step').textContent =
      `EXPLAINER ${step + 1} / ${messages.length}`;

    $('xo-main').textContent =
      item.title;

    $('xo-detail').textContent =
      item.detail;

    progress();
  }

  function next() {
    step =
      (step + 1) %
      messages.length;

    render();
  }

  function previous() {
    step =
      (
        step -
        1 +
        messages.length
      ) %
      messages.length;

    render();
  }

  function updateMetrics() {
    const c = counts();
    const s = sync();

    $('xo-nodes').textContent =
      c.nodes.length;

    $('xo-links').textContent =
      c.links.length;

    $('xo-verified').textContent =
      c.verified;

    $('xo-hash').textContent =
      String(
        s.graphFingerprint ||
        '--------'
      ).slice(0, 8);

    let mode =
      s.mode ||
      graph?.meta?.name ||
      'ONTOLOGY';

    $('xo-live-text').textContent =
      String(mode)
        .replaceAll('_', ' ')
        .slice(0, 34);

    const nowParts = [
      `READING ${c.nodes.length} OBJECTS`,
      `${c.links.length} RELATIONSHIPS`
    ];

    if (
      s.remotePutVerified === true &&
      s.remoteGetVerified === true &&
      s.sha256Verified === true
    ) {
      nowParts.push(
        'FOUNDRY MAVEN VERIFIED'
      );
    }

    if (github?.headSha) {
      nowParts.push(
        `GITHUB ${github.headSha.slice(0, 7)}`
      );
    }

    $('xo-now').textContent =
      'NOW: ' + nowParts.join(' · ');
  }

  function graphChanged(next) {
    if (
      lastFingerprint &&
      next &&
      next !== lastFingerprint
    ) {
      root.classList.remove(
        'xo-change'
      );

      void root.offsetWidth;

      root.classList.add(
        'xo-change'
      );

      $('xo-now').textContent =
        'REAL GRAPH CHANGE DETECTED · ONTOLOGY STATE UPDATED';

      step = 7;
      render();

      setTimeout(
        updateMetrics,
        2500
      );
    }

    if (next) {
      lastFingerprint = next;
    }
  }

  async function loadOntology() {
    try {
      const response = await fetch(
        ONTOLOGY +
        '?t=' +
        Date.now(),
        {
          cache: 'no-store'
        }
      );

      if (!response.ok) {
        throw new Error(
          `HTTP ${response.status}`
        );
      }

      const incoming =
        await response.json();

      const nextFingerprint =
        incoming?.meta
          ?.liveSync
          ?.graphFingerprint;

      graphChanged(
        nextFingerprint
      );

      graph = incoming;

      updateMetrics();

    } catch (error) {
      $('xo-now').textContent =
        'ONTOLOGY SOURCE UNAVAILABLE · ' +
        error.message;
    }
  }

  async function loadGithub() {
    try {
      const response = await fetch(
        GITHUB +
        '?t=' +
        Date.now(),
        {
          cache: 'no-store'
        }
      );

      if (!response.ok) {
        return;
      }

      github =
        await response.json();

      updateMetrics();

    } catch (_) {
      /* GitHub stream is optional */
    }
  }

  $('xo-next').onclick = () => {
    next();
  };

  $('xo-prev').onclick = () => {
    previous();
  };

  $('xo-pause').onclick = () => {
    paused = !paused;

    $('xo-pause').textContent =
      paused
        ? 'RESUME'
        : 'PAUSE';
  };

  $('xo-hide').onclick = () => {
    root.style.display = 'none';
    launcher.style.display = 'block';
  };

  launcher.onclick = () => {
    launcher.style.display = 'none';
    root.style.display = 'block';
    render();
  };

  document.addEventListener(
    'keydown',
    event => {
      if (
        event.key.toLowerCase() === 'h'
      ) {
        const hidden =
          root.style.display === 'none';

        root.style.display =
          hidden
            ? 'block'
            : 'none';

        launcher.style.display =
          hidden
            ? 'none'
            : 'block';
      }
    }
  );

  timer = setInterval(
    () => {
      if (!paused) {
        next();
      }
    },
    6500
  );

  setInterval(
    loadOntology,
    2500
  );

  setInterval(
    loadGithub,
    5000
  );

  render();
  loadOntology();
  loadGithub();
})();
