(() => {
  'use strict';

  const GRAPH_URL =
    '../maven-ontology/ontology.json';

  const HISTORY_URL =
    './history.json';

  const colors = {
    agent: '#45e7ff',
    system: '#9b6cff',
    knowledge: '#55f7a5',
    security: '#ff4fd8',
    governance: '#ffd166'
  };

  let liveGraph = null;
  let activeGraph = null;
  let history = {
    snapshots: []
  };

  let selectedId = null;
  let tab = 'lineage';
  let timelineIndex = 0;
  let timelineTimer = null;
  let simulationGraph = null;

  const disabledClusters =
    new Set();

  const esc = value =>
    String(
      value ?? ''
    )
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');

  async function fetchJson(url) {
    const response =
      await fetch(
        url +
        (
          url.includes('?')
            ? '&'
            : '?'
        )
        + 't='
        + Date.now(),
        {
          cache: 'no-store'
        }
      );

    if (!response.ok) {
      throw new Error(
        `${response.status} ${url}`
      );
    }

    return response.json();
  }

  function clone(value) {
    return JSON.parse(
      JSON.stringify(value)
    );
  }

  function mapNodes(graph) {
    return new Map(
      (graph?.nodes || []).map(
        node => [
          node.id,
          node
        ]
      )
    );
  }

  function edgeMaps(graph) {
    const up = new Map();
    const down = new Map();

    for (
      const node
      of graph?.nodes || []
    ) {
      up.set(
        node.id,
        []
      );

      down.set(
        node.id,
        []
      );
    }

    for (
      const edge
      of graph?.links || []
    ) {
      if (edge.length !== 3) {
        continue;
      }

      if (
        down.has(edge[0])
      ) {
        down
          .get(edge[0])
          .push(edge);
      }

      if (
        up.has(edge[1])
      ) {
        up
          .get(edge[1])
          .push(edge);
      }
    }

    return {
      up,
      down
    };
  }

  function walk(
    graph,
    root,
    direction
  ) {
    const maps =
      edgeMaps(graph);

    const edges =
      direction === 'up'
        ? maps.up
        : maps.down;

    const depth =
      new Map([
        [
          root,
          0
        ]
      ]);

    const parent =
      new Map();

    const queue = [
      root
    ];

    while (queue.length) {
      const current =
        queue.shift();

      for (
        const edge
        of edges.get(
          current
        ) || []
      ) {
        const next =
          direction === 'up'
            ? edge[0]
            : edge[1];

        if (
          depth.has(next)
        ) {
          continue;
        }

        depth.set(
          next,
          depth.get(
            current
          ) + 1
        );

        parent.set(
          next,
          {
            from: current,
            edge
          }
        );

        queue.push(next);
      }
    }

    return {
      depth,
      parent
    };
  }

  function nodeDate(node) {
    const p =
      node?.provenance || {};

    const u =
      p.upstream || {};

    const values = [
      p.generatedAt,
      p.approvedAt,
      p.verifiedAt,
      p.createdAt,
      p.date,
      u.generatedAt,
      u.approvedAt,
      u.verifiedAt,
      u.date
    ];

    for (
      const value
      of values
    ) {
      if (!value) continue;

      const date =
        new Date(value);

      if (
        !Number.isNaN(
          date.getTime()
        )
      ) {
        return date;
      }
    }

    return null;
  }

  function quality(graph) {
    const nodes =
      graph?.nodes || [];

    const links =
      graph?.links || [];

    const degree =
      Object.fromEntries(
        nodes.map(
          n => [
            n.id,
            0
          ]
        )
      );

    for (
      const edge
      of links
    ) {
      if (
        degree[edge[0]]
        !== undefined
      ) {
        degree[edge[0]]++;
      }

      if (
        degree[edge[1]]
        !== undefined
      ) {
        degree[edge[1]]++;
      }
    }

    const now =
      Date.now();

    return {
      low: nodes.filter(
        n =>
          Number(
            n.confidence || 0
          ) < 0.95
      ),

      critical: nodes.filter(
        n =>
          Number(
            n.confidence || 0
          ) < 0.80
      ),

      stale: nodes.filter(
        n => {
          const d =
            nodeDate(n);

          return (
            d &&
            (
              now -
              d.getTime()
            ) > 86400000
          );
        }
      ),

      orphan: nodes.filter(
        n =>
          degree[n.id] === 0
      )
    };
  }

  function difference(
    before,
    after
  ) {
    const a =
      new Set(
        (
          before?.nodes || []
        ).map(
          n => n.id
        )
      );

    const b =
      new Set(
        (
          after?.nodes || []
        ).map(
          n => n.id
        )
      );

    const ae =
      new Set(
        (
          before?.links || []
        ).map(
          JSON.stringify
        )
      );

    const be =
      new Set(
        (
          after?.links || []
        ).map(
          JSON.stringify
        )
      );

    return {
      addedNodes:
        [...b].filter(
          x => !a.has(x)
        ),

      removedNodes:
        [...a].filter(
          x => !b.has(x)
        ),

      addedLinks:
        [...be]
          .filter(
            x => !ae.has(x)
          )
          .map(JSON.parse),

      removedLinks:
        [...ae]
          .filter(
            x => !be.has(x)
          )
          .map(JSON.parse)
    };
  }

  const panel =
    document.createElement(
      'section'
    );

  panel.id =
    'xz-analytics-lab';

  panel.innerHTML = `
    <header class="xa-head">
      <div>
        <div class="xa-kicker">
          PLANET xZOON
        </div>

        <div class="xa-title">
          ONTOLOGY ANALYTICS LAB
        </div>
      </div>

      <div class="xa-head-right">
        <span id="xa-mode">
          LIVE
        </span>

        <button id="xa-close">
          CLOSE
        </button>
      </div>
    </header>

    <div class="xa-tools">
      <input
        id="xa-node-search"
        placeholder="Find object..."
      >

      <select id="xa-node"></select>

      <div id="xa-cluster-buttons"></div>
    </div>

    <nav class="xa-tabs">
      <button data-tab="lineage">LINEAGE</button>
      <button data-tab="impact">IMPACT</button>
      <button data-tab="timeline">TIME TRAVEL</button>
      <button data-tab="quality">QUALITY</button>
      <button data-tab="query">SEMANTIC QUERY</button>
      <button data-tab="scenario">WHAT-IF</button>
      <button data-tab="inspect">INSPECT</button>
      <button data-tab="actions">ACTIONS</button>
    </nav>

    <main id="xa-content"></main>
  `;

  const style =
    document.createElement(
      'style'
    );

  style.textContent = `
    #xz-analytics-lab{
      position:fixed;
      z-index:200000;
      left:18px;
      right:18px;
      top:80px;
      bottom:18px;
      display:none;
      overflow:auto;
      padding:16px;
      box-sizing:border-box;
      border:1px solid #45e7ff88;
      border-radius:15px;
      color:#e9fbff;
      background:
        linear-gradient(
          155deg,
          #020914fa,
          #061522f7
        );
      box-shadow:
        0 0 60px #45e7ff22;
      backdrop-filter:blur(20px);
      font-family:
        ui-monospace,
        SFMono-Regular,
        Menlo,
        monospace
    }

    .xa-head,
    .xa-tools,
    .xa-tabs,
    .xa-actions,
    .xa-two{
      display:flex;
      gap:8px;
      align-items:center
    }

    .xa-head{
      justify-content:space-between
    }

    .xa-kicker{
      color:#45e7ff;
      font-size:9px;
      letter-spacing:.18em
    }

    .xa-title{
      color:white;
      font-size:20px;
      font-weight:900
    }

    .xa-head-right{
      display:flex;
      gap:8px;
      align-items:center
    }

    #xa-mode{
      color:#55f7a5;
      font-size:10px
    }

    .xa-tools{
      margin-top:13px;
      flex-wrap:wrap
    }

    .xa-tools input,
    .xa-tools select,
    .xa-query,
    .xa-scenario select,
    .xa-scenario input,
    .xa-scenario textarea{
      background:#020b14;
      color:#eafaff;
      border:1px solid #1d6288;
      border-radius:7px;
      padding:8px;
      box-sizing:border-box
    }

    #xa-node-search{
      width:220px
    }

    #xa-node{
      min-width:300px
    }

    .xa-tabs{
      margin:12px 0;
      flex-wrap:wrap
    }

    #xz-analytics-lab button{
      cursor:pointer;
      background:#061522;
      color:#bcefff;
      border:1px solid #24698f;
      border-radius:7px;
      padding:7px 9px;
      font:
        800 9px
        ui-monospace,
        monospace
    }

    #xz-analytics-lab button:hover,
    #xz-analytics-lab button.active{
      border-color:#45e7ff;
      color:white;
      box-shadow:0 0 13px #45e7ff22
    }

    #xa-cluster-buttons button.off{
      opacity:.3
    }

    .xa-card{
      border:1px solid #17435e;
      border-radius:9px;
      padding:11px;
      margin:8px 0;
      background:#04101a
    }

    .xa-card h3{
      margin:0 0 7px;
      color:#45e7ff;
      font-size:10px;
      letter-spacing:.09em
    }

    .xa-card p,
    .xa-card li{
      color:#a7c4d4;
      font-size:10px;
      line-height:1.55
    }

    .xa-grid{
      display:grid;
      grid-template-columns:
        repeat(
          4,
          minmax(0,1fr)
        );
      gap:7px
    }

    .xa-grid .xa-card{
      margin:0
    }

    .xa-metric{
      font-size:22px;
      font-weight:900;
      color:white
    }

    .xa-mini{
      width:100%;
      height:420px;
      border:1px solid #164863;
      border-radius:9px;
      background:
        radial-gradient(
          circle,
          #092440,
          #020812 70%
        )
    }

    .xa-two{
      align-items:stretch
    }

    .xa-two > div{
      flex:1;
      min-width:0
    }

    .xa-list{
      max-height:320px;
      overflow:auto
    }

    .xa-item{
      padding:7px;
      border-bottom:
        1px solid #ffffff0c;
      font-size:9px;
      cursor:pointer
    }

    .xa-item:hover{
      background:#0b1d2b
    }

    .xa-good{color:#55f7a5}
    .xa-warn{color:#ffd166}
    .xa-bad{color:#ff6f79}

    .xa-query{
      width:100%;
      font-size:12px
    }

    .xa-code{
      max-height:360px;
      overflow:auto;
      white-space:pre-wrap;
      word-break:break-word;
      padding:10px;
      border-radius:7px;
      background:#01070d;
      color:#9bdcf5;
      font-size:9px
    }

    .xa-scenario{
      display:grid;
      gap:8px
    }

    .xa-timeline{
      width:100%
    }

    .xa-impact{
      color:#ffd166;
      font-weight:900
    }

    .xa-action-result{
      white-space:pre-wrap;
      font-size:9px;
      color:#9ad7ec
    }

    @media(max-width:850px){
      .xa-grid{
        grid-template-columns:
          repeat(2,minmax(0,1fr))
      }

      .xa-two{
        display:block
      }

      #xa-node{
        min-width:0;
        width:100%
      }
    }
  `;

  document.head.appendChild(
    style
  );

  document.body.appendChild(
    panel
  );

  const $ =
    id =>
      document.getElementById(
        id
      );

  function canonicalType(node) {
    return String(
      node?.type ||
      node?.objectType ||
      'other'
    ).toLowerCase();
  }

  function typeColor(node) {
    const type =
      canonicalType(node);

    if (
      Number(
        node?.confidence || 0
      ) < 0.80
    ) {
      return '#ff5964';
    }

    if (
      Number(
        node?.confidence || 0
      ) < 0.95
    ) {
      return '#ffd166';
    }

    return (
      colors[type] ||
      '#eafaff'
    );
  }

  function populateNodes() {
    const graph =
      activeGraph ||
      liveGraph;

    if (!graph) return;

    const select =
      $('xa-node');

    const search =
      $('xa-node-search')
        .value
        .toLowerCase()
        .trim();

    const nodes =
      [...graph.nodes]
      .filter(
        node =>
          !search ||
          String(
            node.label ||
            node.id
          )
          .toLowerCase()
          .includes(search) ||
          String(
            node.objectType ||
            node.type ||
            ''
          )
          .toLowerCase()
          .includes(search)
      )
      .sort(
        (a,b) =>
          String(
            a.label || a.id
          )
          .localeCompare(
            String(
              b.label || b.id
            )
          )
      );

    select.innerHTML =
      nodes
      .map(
        node =>
          `<option value="${esc(node.id)}">${esc(node.label || node.id)} · ${esc(node.objectType || node.type || '')}</option>`
      )
      .join('');

    if (
      selectedId &&
      nodes.some(
        n =>
          n.id === selectedId
      )
    ) {
      select.value =
        selectedId;
    } else if (
      nodes.length
    ) {
      selectedId =
        nodes[0].id;

      select.value =
        selectedId;
    }
  }

  function clusterControls() {
    const types = [
      'agent',
      'system',
      'knowledge',
      'security',
      'governance'
    ];

    const holder =
      $('xa-cluster-buttons');

    holder.innerHTML = '';

    for (
      const type
      of types
    ) {
      const button =
        document.createElement(
          'button'
        );

      button.textContent =
        type.toUpperCase();

      if (
        disabledClusters.has(
          type
        )
      ) {
        button.classList.add(
          'off'
        );
      }

      button.onclick =
        () => {
          if (
            disabledClusters.has(
              type
            )
          ) {
            disabledClusters.delete(
              type
            );
          } else {
            disabledClusters.add(
              type
            );
          }

          clusterControls();
          render();
        };

      holder.appendChild(
        button
      );
    }
  }

  function lineageSet(
    graph,
    root
  ) {
    const upstream =
      walk(
        graph,
        root,
        'up'
      );

    const downstream =
      walk(
        graph,
        root,
        'down'
      );

    const ids =
      new Set([
        ...upstream.depth.keys(),
        ...downstream.depth.keys()
      ]);

    return {
      upstream,
      downstream,
      ids
    };
  }

  function miniGraph(
    container,
    graph,
    root
  ) {
    if (
      !graph ||
      !root
    ) {
      container.innerHTML =
        '<div class="xa-card">No graph selected.</div>';
      return;
    }

    const nodes =
      mapNodes(graph);

    const lineage =
      lineageSet(
        graph,
        root
      );

    let ids =
      [...lineage.ids]
      .filter(
        id => {
          const node =
            nodes.get(id);

          return (
            node &&
            !disabledClusters.has(
              canonicalType(node)
            )
          );
        }
      );

    if (
      !ids.includes(root)
    ) {
      ids.unshift(root);
    }

    const upstream =
      lineage.upstream.depth;

    const downstream =
      lineage.downstream.depth;

    const groups = {
      up: {},
      down: {}
    };

    for (
      const id
      of ids
    ) {
      if (id === root) {
        continue;
      }

      if (
        upstream.has(id)
      ) {
        const d =
          upstream.get(id);

        (
          groups.up[d] ||= []
        ).push(id);

      } else if (
        downstream.has(id)
      ) {
        const d =
          downstream.get(id);

        (
          groups.down[d] ||= []
        ).push(id);
      }
    }

    const maxDepth =
      Math.max(
        1,
        ...[
          ...upstream.values(),
          ...downstream.values()
        ]
      );

    const positions =
      new Map([
        [
          root,
          {
            x: 600,
            y: 210
          }
        ]
      ]);

    function place(
      direction,
      sign
    ) {
      for (
        const [
          depth,
          list
        ]
        of Object.entries(
          groups[direction]
        )
      ) {
        const d =
          Number(depth);

        const x =
          600 +
          sign *
          (
            500 *
            d /
            maxDepth
          );

        list.forEach(
          (
            id,
            index
          ) => {
            positions.set(
              id,
              {
                x,
                y:
                  35 +
                  (
                    350 *
                    (
                      index + 1
                    )
                    /
                    (
                      list.length + 1
                    )
                  )
              }
            );
          }
        );
      }
    }

    place(
      'up',
      -1
    );

    place(
      'down',
      1
    );

    const ns =
      'http://www.w3.org/2000/svg';

    const svg =
      document.createElementNS(
        ns,
        'svg'
      );

    svg.setAttribute(
      'viewBox',
      '0 0 1200 420'
    );

    svg.classList.add(
      'xa-mini'
    );

    for (
      const edge
      of graph.links || []
    ) {
      const a =
        positions.get(
          edge[0]
        );

      const b =
        positions.get(
          edge[1]
        );

      if (!a || !b) {
        continue;
      }

      const line =
        document.createElementNS(
          ns,
          'line'
        );

      line.setAttribute(
        'x1',
        a.x
      );

      line.setAttribute(
        'y1',
        a.y
      );

      line.setAttribute(
        'x2',
        b.x
      );

      line.setAttribute(
        'y2',
        b.y
      );

      line.setAttribute(
        'stroke',
        '#45e7ff55'
      );

      line.setAttribute(
        'stroke-width',
        '1.5'
      );

      svg.appendChild(
        line
      );
    }

    for (
      const [
        id,
        pos
      ]
      of positions
    ) {
      const node =
        nodes.get(id);

      if (!node) continue;

      const group =
        document.createElementNS(
          ns,
          'g'
        );

      group.style.cursor =
        'pointer';

      const circle =
        document.createElementNS(
          ns,
          'circle'
        );

      circle.setAttribute(
        'cx',
        pos.x
      );

      circle.setAttribute(
        'cy',
        pos.y
      );

      circle.setAttribute(
        'r',
        id === root
          ? 10
          : 6
      );

      circle.setAttribute(
        'fill',
        typeColor(node)
      );

      circle.setAttribute(
        'stroke',
        id === root
          ? '#ffffff'
          : '#ffffff33'
      );

      const text =
        document.createElementNS(
          ns,
          'text'
        );

      text.setAttribute(
        'x',
        pos.x + 11
      );

      text.setAttribute(
        'y',
        pos.y + 3
      );

      text.setAttribute(
        'fill',
        '#dff7ff'
      );

      text.setAttribute(
        'font-size',
        '10'
      );

      text.textContent =
        String(
          node.label ||
          node.id
        ).slice(
          0,
          36
        );

      group.onclick =
        () => {
          selectedId =
            node.id;

          populateNodes();
          render();
        };

      group.appendChild(
        circle
      );

      group.appendChild(
        text
      );

      svg.appendChild(
        group
      );
    }

    container.replaceChildren(
      svg
    );
  }

  function renderLineage() {
    const graph =
      activeGraph;

    const nodes =
      mapNodes(graph);

    const node =
      nodes.get(
        selectedId
      );

    if (!node) return;

    const lin =
      lineageSet(
        graph,
        selectedId
      );

    const up =
      [...lin.upstream.depth.keys()]
      .filter(
        id =>
          id !== selectedId
      );

    const down =
      [...lin.downstream.depth.keys()]
      .filter(
        id =>
          id !== selectedId
      );

    $('xa-content').innerHTML = `
      <div class="xa-grid">
        <div class="xa-card">
          <h3>SELECTED OBJECT</h3>
          <div class="xa-metric">${esc(node.label || node.id)}</div>
        </div>

        <div class="xa-card">
          <h3>UPSTREAM</h3>
          <div class="xa-metric">${up.length}</div>
        </div>

        <div class="xa-card">
          <h3>DOWNSTREAM</h3>
          <div class="xa-metric">${down.length}</div>
        </div>

        <div class="xa-card">
          <h3>CONFIDENCE</h3>
          <div class="xa-metric">${Number(node.confidence || 0).toFixed(2)}</div>
        </div>
      </div>

      <div class="xa-card">
        <h3>FULL UPSTREAM / DOWNSTREAM LINEAGE</h3>
        <div id="xa-mini-holder"></div>
      </div>

      <div class="xa-two">
        <div class="xa-card">
          <h3>UPSTREAM SOURCES / DEPENDENCIES</h3>
          <div class="xa-list">
            ${
              up.map(
                id =>
                  `<div class="xa-item" data-node="${esc(id)}">${esc(nodes.get(id)?.label || id)}</div>`
              ).join('')
              ||
              '<div class="xa-item">None</div>'
            }
          </div>
        </div>

        <div class="xa-card">
          <h3>DOWNSTREAM DEPENDENCIES</h3>
          <div class="xa-list">
            ${
              down.map(
                id =>
                  `<div class="xa-item" data-node="${esc(id)}">${esc(nodes.get(id)?.label || id)}</div>`
              ).join('')
              ||
              '<div class="xa-item">None</div>'
            }
          </div>
        </div>
      </div>
    `;

    miniGraph(
      $('xa-mini-holder'),
      graph,
      selectedId
    );

    bindNodeItems();
  }

  function renderImpact() {
    const graph =
      activeGraph;

    const nodes =
      mapNodes(graph);

    const node =
      nodes.get(
        selectedId
      );

    const downstream =
      walk(
        graph,
        selectedId,
        'down'
      );

    const affected =
      [...downstream.depth.keys()]
      .filter(
        id =>
          id !== selectedId
      );

    const counts = {};

    for (
      const id
      of affected
    ) {
      const n =
        nodes.get(id);

      const type =
        n?.objectType ||
        n?.type ||
        'Other';

      counts[type] =
        (
          counts[type] || 0
        ) + 1;
    }

    $('xa-content').innerHTML = `
      <div class="xa-card">
        <h3>IMPACT ANALYSIS</h3>

        <div class="xa-impact">
          ${esc(node?.label || selectedId)}
          currently has a downstream blast radius of
          ${affected.length} object(s).
        </div>

        <p>
          This is a read-only dependency calculation.
          Use it before schema edits, actions, releases,
          or pull-request merges.
        </p>
      </div>

      <div class="xa-grid">
        ${
          Object.entries(
            counts
          )
          .map(
            ([type,count]) =>
              `<div class="xa-card"><h3>${esc(type)}</h3><div class="xa-metric">${count}</div></div>`
          )
          .join('')
          ||
          '<div class="xa-card">No downstream dependencies.</div>'
        }
      </div>

      <div class="xa-card">
        <h3>AFFECTED OBJECTS</h3>

        <div class="xa-list">
          ${
            affected.map(
              id => {
                const n =
                  nodes.get(id);

                return `<div class="xa-item" data-node="${esc(id)}">${esc(n?.label || id)} · depth ${downstream.depth.get(id)}</div>`;
              }
            ).join('')
            ||
            '<div class="xa-item">No downstream impact.</div>'
          }
        </div>
      </div>
    `;

    bindNodeItems();
  }

  function snapshotGraph(index) {
    const snap =
      history.snapshots[
        index
      ];

    if (!snap) {
      return;
    }

    timelineIndex =
      index;

    activeGraph =
      snap.graph;

    if (
      !activeGraph.nodes.some(
        n =>
          n.id === selectedId
      )
    ) {
      selectedId =
        activeGraph.nodes[0]?.id ||
        null;
    }

    $('xa-mode').textContent =
      snap.kind === 'live'
        ? 'LIVE SNAPSHOT'
        : `TIME TRAVEL · ${snap.shortSha}`;

    populateNodes();
  }

  function renderTimeline() {
    const snaps =
      history.snapshots || [];

    if (!snaps.length) {
      $('xa-content').innerHTML =
        '<div class="xa-card">No historical ontology snapshots found yet.</div>';
      return;
    }

    timelineIndex =
      Math.min(
        timelineIndex,
        snaps.length - 1
      );

    const snap =
      snaps[
        timelineIndex
      ];

    const drift =
      snap.drift || {};

    $('xa-content').innerHTML = `
      <div class="xa-card">
        <h3>GIT-DRIVEN ONTOLOGY TIME TRAVEL</h3>

        <input
          id="xa-time"
          class="xa-timeline"
          type="range"
          min="0"
          max="${snaps.length - 1}"
          value="${timelineIndex}"
        >

        <div class="xa-actions">
          <button id="xa-rewind">
            REWIND
          </button>

          <button id="xa-play">
            PLAY
          </button>

          <button id="xa-live">
            RETURN LIVE
          </button>
        </div>
      </div>

      <div class="xa-card">
        <h3>${esc(snap.shortSha)} · ${esc(snap.message)}</h3>

        <p>
          ${esc(snap.date)}
        </p>

        <p>
          +${drift.addedNodes?.length || 0} nodes ·
          -${drift.removedNodes?.length || 0} nodes ·
          +${drift.addedLinks?.length || 0} links ·
          -${drift.removedLinks?.length || 0} links
        </p>

        <p class="${drift.schemaReviewRequired ? 'xa-warn' : 'xa-good'}">
          ${
            drift.schemaReviewRequired
              ? 'SCHEMA DRIFT DETECTED · REVIEW REQUIRED'
              : 'NO OBJECT/RELATION TYPE SCHEMA DRIFT'
          }
        </p>
      </div>

      <div class="xa-card">
        <h3>GRAPH AT THIS POINT IN TIME</h3>
        <div id="xa-time-graph"></div>
      </div>
    `;

    miniGraph(
      $('xa-time-graph'),
      snap.graph,
      selectedId
    );

    $('xa-time').oninput =
      event => {
        snapshotGraph(
          Number(
            event.target.value
          )
        );

        renderTimeline();
      };

    $('xa-rewind').onclick =
      () => {
        snapshotGraph(
          Math.max(
            0,
            timelineIndex - 1
          )
        );

        renderTimeline();
      };

    $('xa-live').onclick =
      () => {
        clearInterval(
          timelineTimer
        );

        activeGraph =
          liveGraph;

        timelineIndex =
          snaps.length - 1;

        $('xa-mode').textContent =
          'LIVE';

        populateNodes();
        renderTimeline();
      };

    $('xa-play').onclick =
      () => {
        clearInterval(
          timelineTimer
        );

        timelineTimer =
          setInterval(
            () => {
              if (
                timelineIndex >=
                snaps.length - 1
              ) {
                clearInterval(
                  timelineTimer
                );

                return;
              }

              snapshotGraph(
                timelineIndex + 1
              );

              renderTimeline();
            },
            1200
          );
      };
  }

  function renderQuality() {
    const graph =
      activeGraph;

    const q =
      quality(graph);

    const current =
      history.snapshots[
        timelineIndex
      ];

    const drift =
      current?.drift || {};

    $('xa-content').innerHTML = `
      <div class="xa-grid">
        <div class="xa-card">
          <h3>TRUST &lt; 0.95</h3>
          <div class="xa-metric xa-warn">${q.low.length}</div>
        </div>

        <div class="xa-card">
          <h3>TRUST &lt; 0.80</h3>
          <div class="xa-metric xa-bad">${q.critical.length}</div>
        </div>

        <div class="xa-card">
          <h3>STALE &gt; 24H</h3>
          <div class="xa-metric xa-warn">${q.stale.length}</div>
        </div>

        <div class="xa-card">
          <h3>ORPHANS</h3>
          <div class="xa-metric xa-bad">${q.orphan.length}</div>
        </div>
      </div>

      <div class="xa-card">
        <h3>SCHEMA / LINEAGE DRIFT</h3>

        <p class="${drift.schemaReviewRequired ? 'xa-warn' : 'xa-good'}">
          ${
            drift.schemaReviewRequired
              ? 'Object/relation type change detected. Authorization cannot be inferred automatically; manual governance review is required.'
              : 'No object/relation type schema change detected in this snapshot.'
          }
        </p>

        <p>
          Added nodes:
          ${drift.addedNodes?.length || 0} ·
          Removed nodes:
          ${drift.removedNodes?.length || 0} ·
          Added links:
          ${drift.addedLinks?.length || 0} ·
          Removed links:
          ${drift.removedLinks?.length || 0}
        </p>
      </div>

      <div class="xa-two">
        <div class="xa-card">
          <h3>LOW TRUST HEATMAP</h3>

          <div class="xa-list">
            ${
              q.low.map(
                n =>
                  `<div class="xa-item ${Number(n.confidence || 0) < .8 ? 'xa-bad' : 'xa-warn'}" data-node="${esc(n.id)}">${esc(n.label || n.id)} · ${Number(n.confidence || 0).toFixed(2)}</div>`
              ).join('')
              ||
              '<div class="xa-item xa-good">No low-trust objects.</div>'
            }
          </div>
        </div>

        <div class="xa-card">
          <h3>FRESHNESS / ORPHAN FLAGS</h3>

          <div class="xa-list">
            ${
              [
                ...q.stale.map(
                  n =>
                    `<div class="xa-item xa-warn" data-node="${esc(n.id)}">STALE · ${esc(n.label || n.id)}</div>`
                ),
                ...q.orphan.map(
                  n =>
                    `<div class="xa-item xa-bad" data-node="${esc(n.id)}">ORPHAN · ${esc(n.label || n.id)}</div>`
                )
              ].join('')
              ||
              '<div class="xa-item xa-good">No freshness/orphan flags.</div>'
            }
          </div>
        </div>
      </div>
    `;

    bindNodeItems();
  }

  function semanticSearch(
    query,
    graph
  ) {
    const q =
      query
      .toLowerCase()
      .trim();

    let results =
      [...graph.nodes];

    const trust =
      q.match(
        /trust\s+(?:below|under|<)\s*([0-9.]+)/
      );

    if (trust) {
      const limit =
        Number(
          trust[1]
        );

      results =
        results.filter(
          n =>
            Number(
              n.confidence || 0
            ) < limit
        );
    }

    if (
      q.includes(
        'unverified'
      )
    ) {
      results =
        results.filter(
          n =>
            n.status !==
            'verified'
        );
    }

    if (
      q.includes(
        'verified'
      ) &&
      !q.includes(
        'unverified'
      )
    ) {
      results =
        results.filter(
          n =>
            n.status ===
            'verified'
        );
    }

    for (
      const category
      of [
        'governance',
        'security',
        'knowledge',
        'system',
        'agent'
      ]
    ) {
      if (
        q.includes(
          category
        )
      ) {
        results =
          results.filter(
            n =>
              canonicalType(n)
              .includes(category) ||
              String(
                n.objectType || ''
              )
              .toLowerCase()
              .includes(category)
        );
      }
    }

    const objectTerms = [
      'control',
      'artifact',
      'dataset',
      'mission',
      'requirement',
      'source',
      'evidence',
      'finding',
      'platform',
      'branch',
      'commit',
      'pullrequest'
    ];

    for (
      const term
      of objectTerms
    ) {
      if (
        q.includes(term)
      ) {
        results =
          results.filter(
            n =>
              String(
                n.objectType ||
                n.type ||
                ''
              )
              .toLowerCase()
              .includes(term) ||
              String(
                n.label || ''
              )
              .toLowerCase()
              .includes(term)
          );
      }
    }

    if (
      q.includes(
        'stale'
      ) ||
      q.includes(
        '24-hour'
      ) ||
      q.includes(
        '24 hour'
      )
    ) {
      const stale =
        new Set(
          quality(
            graph
          ).stale.map(
            n => n.id
          )
        );

      results =
        results.filter(
          n =>
            stale.has(n.id)
        );
    }

    if (
      q.includes(
        'linked to'
      ) &&
      q.includes(
        'agent'
      )
    ) {
      const nodes =
        mapNodes(graph);

      const linked =
        new Set();

      for (
        const edge
        of graph.links
      ) {
        const a =
          nodes.get(
            edge[0]
          );

        const b =
          nodes.get(
            edge[1]
          );

        if (
          canonicalType(a)
          .includes('agent') &&
          a?.status !==
          'inactive'
        ) {
          linked.add(
            b?.id
          );
        }

        if (
          canonicalType(b)
          .includes('agent') &&
          b?.status !==
          'inactive'
        ) {
          linked.add(
            a?.id
          );
        }
      }

      results =
        results.filter(
          n =>
            linked.has(n.id)
        );
    }

    const quoted =
      [...query.matchAll(
        /"([^"]+)"/g
      )]
      .map(
        x =>
          x[1]
          .toLowerCase()
      );

    for (
      const term
      of quoted
    ) {
      results =
        results.filter(
          n =>
            JSON.stringify(n)
            .toLowerCase()
            .includes(term)
        );
    }

    return results;
  }

  function renderQuery() {
    $('xa-content').innerHTML = `
      <div class="xa-card">
        <h3>NATURAL LANGUAGE SEMANTIC SEARCH</h3>

        <input
          id="xa-query"
          class="xa-query"
          value="Show all unverified Governance controls linked to active Agents"
        >

        <div class="xa-actions" style="margin-top:8px">
          <button id="xa-query-local">
            SEARCH GRAPH
          </button>

          <button id="xa-query-aip">
            ASK FOUNDRY / AIP
          </button>
        </div>

        <p>
          Local semantic search always works.
          Foundry/AIP activates only when a published
          Query API name and server-side credentials
          are configured.
        </p>
      </div>

      <div class="xa-card">
        <h3>RESULTS</h3>
        <div id="xa-query-results"></div>
      </div>
    `;

    $('xa-query-local').onclick =
      () => {
        const query =
          $('xa-query').value;

        const results =
          semanticSearch(
            query,
            activeGraph
          );

        $('xa-query-results').innerHTML =
          `<p>${results.length} matching object(s)</p>`
          +
          `<div class="xa-list">${
            results.map(
              n =>
                `<div class="xa-item" data-node="${esc(n.id)}">${esc(n.label || n.id)} · ${esc(n.objectType || n.type || '')} · ${esc(n.status || '')}</div>`
            ).join('')
          }</div>`;

        bindNodeItems();
      };

    $('xa-query-aip').onclick =
      async () => {
        const out =
          $('xa-query-results');

        out.textContent =
          'Querying Foundry...';

        try {
          const response =
            await fetch(
              '/xzoon-api/aip-query',
              {
                method: 'POST',
                headers: {
                  'Content-Type':
                    'application/json'
                },
                body: JSON.stringify({
                  query:
                    $('xa-query').value
                })
              }
            );

          const result =
            await response.json();

          out.innerHTML =
            `<pre class="xa-code">${esc(JSON.stringify(result,null,2))}</pre>`;

        } catch (error) {
          out.textContent =
            error.message;
        }
      };
  }

  function applyScenario(
    graph,
    operation,
    source,
    target,
    relation
  ) {
    const copy =
      clone(graph);

    const node =
      copy.nodes.find(
        n =>
          n.id === source
      );

    if (
      operation ===
      'candidate' &&
      node
    ) {
      node.status =
        'candidate';
    }

    if (
      operation ===
      'trust090' &&
      node
    ) {
      node.confidence =
        0.90;
    }

    if (
      operation ===
      'remove-node'
    ) {
      copy.nodes =
        copy.nodes.filter(
          n =>
            n.id !== source
        );

      copy.links =
        copy.links.filter(
          e =>
            e[0] !== source &&
            e[1] !== source
        );
    }

    if (
      operation ===
      'remove-first-link'
    ) {
      const index =
        copy.links.findIndex(
          e =>
            e[0] === source ||
            e[1] === source
        );

      if (
        index >= 0
      ) {
        copy.links.splice(
          index,
          1
        );
      }
    }

    if (
      operation ===
      'add-link' &&
      source &&
      target &&
      relation
    ) {
      copy.links.push([
        source,
        target,
        relation
      ]);
    }

    return copy;
  }

  function renderScenario() {
    const graph =
      activeGraph;

    const options =
      graph.nodes
      .map(
        n =>
          `<option value="${esc(n.id)}">${esc(n.label || n.id)}</option>`
      )
      .join('');

    $('xa-content').innerHTML = `
      <div class="xa-card xa-scenario">
        <h3>WHAT-IF SANDBOX</h3>

        <select id="xa-operation">
          <option value="candidate">Mark selected object candidate</option>
          <option value="trust090">Set trust to 0.90</option>
          <option value="remove-node">Remove object</option>
          <option value="remove-first-link">Remove first connected relationship</option>
          <option value="add-link">Add relationship</option>
        </select>

        <select id="xa-source">
          ${options}
        </select>

        <select id="xa-target">
          ${options}
        </select>

        <input
          id="xa-relation"
          value="REQUIRES"
          placeholder="Relationship"
        >

        <div class="xa-actions">
          <button id="xa-simulate">
            SIMULATE
          </button>

          <button id="xa-sim-reset">
            RESET SANDBOX
          </button>
        </div>

        <p>
          Simulation never writes to Foundry,
          Maven, GitHub, or the live ontology.
        </p>
      </div>

      <div id="xa-scenario-result"></div>
    `;

    $('xa-source').value =
      selectedId;

    $('xa-simulate').onclick =
      () => {
        simulationGraph =
          applyScenario(
            graph,
            $('xa-operation').value,
            $('xa-source').value,
            $('xa-target').value,
            $('xa-relation').value
          );

        const diff =
          difference(
            graph,
            simulationGraph
          );

        const downstream =
          simulationGraph.nodes.some(
            n =>
              n.id === selectedId
          )
          ? walk(
              simulationGraph,
              selectedId,
              'down'
            )
          : {
              depth:
                new Map()
            };

        $('xa-scenario-result').innerHTML = `
          <div class="xa-card">
            <h3>SIMULATION RESULT</h3>

            <p>
              Added nodes:
              ${diff.addedNodes.length} ·
              Removed nodes:
              ${diff.removedNodes.length} ·
              Added links:
              ${diff.addedLinks.length} ·
              Removed links:
              ${diff.removedLinks.length}
            </p>

            <p>
              Simulated downstream blast radius:
              ${Math.max(0,downstream.depth.size - 1)}
            </p>
          </div>

          <div class="xa-two">
            <div class="xa-card">
              <h3>LIVE BRANCH</h3>
              <div id="xa-live-mini"></div>
            </div>

            <div class="xa-card">
              <h3>SCENARIO BRANCH</h3>
              <div id="xa-sim-mini"></div>
            </div>
          </div>
        `;

        miniGraph(
          $('xa-live-mini'),
          graph,
          selectedId
        );

        miniGraph(
          $('xa-sim-mini'),
          simulationGraph,
          selectedId
        );
      };

    $('xa-sim-reset').onclick =
      () => {
        simulationGraph =
          null;

        $('xa-scenario-result').innerHTML =
          '<div class="xa-card">Sandbox cleared.</div>';
      };
  }

  function renderInspect() {
    const graph =
      activeGraph;

    const nodes =
      mapNodes(graph);

    const node =
      nodes.get(
        selectedId
      );

    if (!node) return;

    const edges =
      graph.links.filter(
        edge =>
          edge[0] ===
            selectedId ||
          edge[1] ===
            selectedId
      );

    const historical =
      history.snapshots.filter(
        snap =>
          snap.graph.nodes.some(
            n =>
              n.id ===
              selectedId
          )
      );

    $('xa-content').innerHTML = `
      <div class="xa-grid">
        <div class="xa-card">
          <h3>OBJECT TYPE</h3>
          <div class="xa-metric">${esc(node.objectType || node.type || '')}</div>
        </div>

        <div class="xa-card">
          <h3>STATUS</h3>
          <div class="xa-metric">${esc(node.status || 'unknown')}</div>
        </div>

        <div class="xa-card">
          <h3>CONFIDENCE</h3>
          <div class="xa-metric">${Number(node.confidence || 0).toFixed(2)}</div>
        </div>

        <div class="xa-card">
          <h3>RELATIONSHIPS</h3>
          <div class="xa-metric">${edges.length}</div>
        </div>
      </div>

      <div class="xa-two">
        <div class="xa-card">
          <h3>PROPERTY VALUES / RAW OBJECT JSON</h3>
          <pre class="xa-code">${esc(JSON.stringify(node,null,2))}</pre>
        </div>

        <div class="xa-card">
          <h3>PROVENANCE / CODE BINDINGS</h3>
          <pre class="xa-code">${esc(JSON.stringify(node.provenance || {},null,2))}</pre>
        </div>
      </div>

      <div class="xa-card">
        <h3>ACTIVE TELEMETRY / HISTORY</h3>

        <p>
          Seen in ${historical.length}
          historical/live ontology snapshot(s).
        </p>

        <div class="xa-list">
          ${
            historical.slice(-20).reverse().map(
              s =>
                `<div class="xa-item">${esc(s.date)} · ${esc(s.shortSha)} · ${esc(s.message)}</div>`
            ).join('')
          }
        </div>
      </div>

      <div class="xa-card">
        <h3>CONNECTED OBJECTS</h3>

        <pre class="xa-code">${esc(JSON.stringify(edges,null,2))}</pre>
      </div>
    `;
  }

  async function action(
    name,
    extra = {}
  ) {
    if (
      !confirm(
        `Approve governed action: ${name}?`
      )
    ) {
      return;
    }

    const output =
      $('xa-action-output');

    output.textContent =
      'Running...';

    try {
      const response =
        await fetch(
          '/xzoon-api/action',
          {
            method: 'POST',
            headers: {
              'Content-Type':
                'application/json'
            },
            body: JSON.stringify({
              action: name,
              nodeId: selectedId,
              approved: true,
              ...extra
            })
          }
        );

      const result =
        await response.json();

      output.textContent =
        JSON.stringify(
          result,
          null,
          2
        );

    } catch (error) {
      output.textContent =
        error.message;
    }
  }

  function renderActions() {
    $('xa-content').innerHTML = `
      <div class="xa-card">
        <h3>GOVERNED KINETIC ACTIONS</h3>

        <p>
          Actions below are allowlisted,
          require explicit confirmation,
          and do not expose arbitrary shell execution.
          Remote Foundry writes remain locked.
        </p>

        <div class="xa-actions">
          <button id="xa-validate">
            VALIDATE GRAPH
          </button>

          <button id="xa-reverify">
            REVERIFY OBJECT
          </button>

          <button id="xa-maven-sync">
            SYNC VERIFIED MAVEN PROOF
          </button>

          <button id="xa-checks">
            RUN REPO CHECKS
          </button>

          <button id="xa-agent-task">
            QUEUE AGENT TASK
          </button>
        </div>
      </div>

      <div class="xa-card">
        <h3>ACTION RESULT</h3>

        <pre
          id="xa-action-output"
          class="xa-action-result"
        >No action executed.</pre>
      </div>
    `;

    $('xa-validate').onclick =
      () =>
        action(
          'validate_graph'
        );

    $('xa-reverify').onclick =
      () =>
        action(
          'reverify_object'
        );

    $('xa-maven-sync').onclick =
      () =>
        action(
          'sync_verified_maven_proof'
        );

    $('xa-checks').onclick =
      () =>
        action(
          'repo_checks'
        );

    $('xa-agent-task').onclick =
      () => {
        const task =
          prompt(
            'Describe the governed agent task to queue:'
          );

        if (task) {
          action(
            'queue_agent_task',
            {
              task
            }
          );
        }
      };
  }

  function render() {
    if (!activeGraph) {
      return;
    }

    document
      .querySelectorAll(
        '.xa-tabs button'
      )
      .forEach(
        button => {
          button.classList.toggle(
            'active',
            button.dataset.tab ===
              tab
          );
        }
      );

    if (
      tab === 'lineage'
    ) {
      renderLineage();
    }

    if (
      tab === 'impact'
    ) {
      renderImpact();
    }

    if (
      tab === 'timeline'
    ) {
      renderTimeline();
    }

    if (
      tab === 'quality'
    ) {
      renderQuality();
    }

    if (
      tab === 'query'
    ) {
      renderQuery();
    }

    if (
      tab === 'scenario'
    ) {
      renderScenario();
    }

    if (
      tab === 'inspect'
    ) {
      renderInspect();
    }

    if (
      tab === 'actions'
    ) {
      renderActions();
    }
  }

  function bindNodeItems() {
    document
      .querySelectorAll(
        '[data-node]'
      )
      .forEach(
        element => {
          element.onclick =
            () => {
              selectedId =
                element.dataset.node;

              populateNodes();

              tab =
                'inspect';

              render();
            };
        }
      );
  }

  async function refresh() {
    try {
      const [
        graph,
        historyData
      ] =
        await Promise.all([
          fetchJson(
            GRAPH_URL
          ),
          fetchJson(
            HISTORY_URL
          ).catch(
            () => ({
              snapshots: []
            })
          )
        ]);

      liveGraph =
        graph;

      history =
        historyData;

      if (
        !activeGraph ||
        $('xa-mode').textContent ===
          'LIVE'
      ) {
        activeGraph =
          liveGraph;
      }

      timelineIndex =
        Math.max(
          0,
          history.snapshots.length - 1
        );

      if (
        !selectedId ||
        !activeGraph.nodes.some(
          n =>
            n.id ===
            selectedId
        )
      ) {
        selectedId =
          activeGraph.nodes[0]?.id ||
          null;
      }

      populateNodes();
      clusterControls();

      if (
        panel.style.display !==
        'none'
      ) {
        render();
      }

    } catch (error) {
      console.error(
        'xZOON analytics:',
        error
      );
    }
  }

  function openLab(
    requestedTab = 'lineage'
  ) {
    tab =
      requestedTab;

    panel.style.display =
      'block';

    render();
  }

  function installToolbar() {
    const toolbar =
      document.querySelector(
        '.xz-toolbar'
      );

    if (!toolbar) return;

    const analytics =
      document.createElement(
        'button'
      );

    analytics.textContent =
      'Analyze';

    analytics.onclick =
      () =>
        openLab(
          'lineage'
        );

    const rewind =
      document.createElement(
        'button'
      );

    rewind.textContent =
      'Rewind';

    rewind.onclick =
      () => {
        if (
          history.snapshots.length
        ) {
          timelineIndex =
            Math.max(
              0,
              history.snapshots.length - 2
            );

          snapshotGraph(
            timelineIndex
          );
        }

        openLab(
          'timeline'
        );
      };

    toolbar.appendChild(
      analytics
    );

    toolbar.appendChild(
      rewind
    );
  }

  document
    .querySelectorAll(
      '.xa-tabs button'
    )
    .forEach(
      button => {
        button.onclick =
          () => {
            tab =
              button.dataset.tab;

            render();
          };
      }
    );

  $('xa-close').onclick =
    () => {
      panel.style.display =
        'none';
    };

  $('xa-node').onchange =
    event => {
      selectedId =
        event.target.value;

      render();
    };

  $('xa-node-search').oninput =
    populateNodes;

  document.addEventListener(
    'click',
    event => {
      const row =
        event.target.closest(
          '.xz-row'
        );

      if (!row) {
        return;
      }

      const label =
        row.querySelector(
          'b'
        )?.textContent
        ?.trim();

      if (!label) {
        return;
      }

      const node =
        liveGraph?.nodes.find(
          n =>
            n.label === label
        );

      if (node) {
        selectedId =
          node.id;

        populateNodes();
      }
    }
  );

  document.addEventListener(
    'contextmenu',
    event => {
      const row =
        event.target.closest(
          '.xz-row'
        );

      if (!row) {
        return;
      }

      event.preventDefault();

      const label =
        row.querySelector(
          'b'
        )?.textContent
        ?.trim();

      const node =
        liveGraph?.nodes.find(
          n =>
            n.label === label
        );

      if (node) {
        selectedId =
          node.id;

        populateNodes();
        openLab(
          'actions'
        );
      }
    }
  );

  installToolbar();

  refresh();

  setInterval(
    refresh,
    5000
  );

  window.xzoonAnalytics = {
    open: openLab,
    lineage: () =>
      openLab(
        'lineage'
      ),
    impact: () =>
      openLab(
        'impact'
      ),
    timeline: () =>
      openLab(
        'timeline'
      ),
    quality: () =>
      openLab(
        'quality'
      )
  };
})();
