/* Source-claim explorer; intentionally makes no requests beyond its own static JSON. */
'use strict';
const NS = 'http://www.w3.org/2000/svg';
const palette = {
  economic_partners: '#eebf85', reactionary_politics: '#bc9994',
  investors_clients: '#bed4ea', unspecified: '#94a5f7'
};
const byId = id => document.getElementById(id);
const draw = (name, attributes = {}, text) => {
  const element = document.createElementNS(NS, name);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, String(value));
  if (text !== undefined) element.textContent = text;
  return element;
};
let data;
let selected = '';

function render() {
  const query = byId('search').value.trim().toLocaleLowerCase();
  const groupChoice = byId('category').value;
  const groups = data.groups.filter(group => {
    if (groupChoice && group.id !== groupChoice) return false;
    return !query || group.label.toLocaleLowerCase().includes(query) ||
      group.members.some(name => name.toLocaleLowerCase().includes(query));
  });
  if (selected && !groups.some(group => group.id === selected)) selected = '';
  const svg = byId('graph');
  svg.replaceChildren();
  const midX = 450, midY = 296;
  const axes = data.groups.map((group, index) => {
    const angle = (-Math.PI / 2) + 2 * Math.PI * index / data.groups.length;
    return {group, x: midX + 310 * Math.cos(angle), y: midY + 212 * Math.sin(angle)};
  });
  const shown = new Set(groups.map(group => group.id));
  for (const {group, x, y} of axes) {
    const active = shown.has(group.id);
    svg.append(draw('line', {
      x1: midX, y1: midY, x2: x, y2: y,
      stroke: palette[group.visual_category], 'stroke-width': active ? 2.8 : 0.8,
      'stroke-opacity': active ? .76 : .11
    }));
  }
  svg.append(draw('circle', {cx: midX, cy: midY, r: 82, fill: '#0e3a50', stroke: '#78e6ef', 'stroke-width': 2.5}));
  svg.append(draw('text', {x: midX, y: midY - 7, fill: '#eaf1ff', 'font-size': 25,
    'font-weight': 750, 'text-anchor': 'middle'}, 'PALANTIR'));
  svg.append(draw('text', {x: midX, y: midY + 19, fill: '#b5eaf0', 'font-size': 11,
    'text-anchor': 'middle'}, 'DIAGRAM FOCUS'));
  for (const {group, x, y} of axes) {
    const active = shown.has(group.id);
    const picked = selected === group.id;
    const node = draw('g', {class: 'node', tabindex: active ? 0 : -1,
      role: 'button', 'aria-label': `Inspect ${group.label}`, opacity: active ? 1 : .16});
    const width = 174, height = 62;
    node.append(draw('rect', {x: x - width / 2, y: y - height / 2, width, height,
      rx: 11, fill: picked ? '#214358' : '#14263c', stroke: palette[group.visual_category],
      'stroke-width': picked ? 3 : 1.5}));
    const shortLabel = group.label.length > 24 ? group.label.slice(0, 22) + '…' : group.label;
    node.append(draw('text', {x, y: y - 2, fill: '#eef5ff', 'font-size': 12,
      'text-anchor': 'middle', 'font-weight': 650}, shortLabel));
    node.append(draw('text', {x, y: y + 18, fill: palette[group.visual_category],
      'font-size': 10, 'text-anchor': 'middle'}, `${group.members.length} NAMES`));
    const inspect = () => { if (!active) return; selected = group.id; render(); };
    node.addEventListener('click', inspect);
    node.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); inspect(); }
    });
    svg.append(node);
  }
  const displayed = selected ? groups.filter(group => group.id === selected) : groups;
  const detail = byId('detail');
  detail.replaceChildren();
  const head = document.createElement('strong');
  head.textContent = selected ? displayed[0].label : (query ? 'Matching categories' : 'All categories');
  detail.append(head);
  const sub = document.createElement('span');
  sub.textContent = `${displayed.reduce((sum, group) => sum + group.members.length, 0)} names • unverified image transcription`;
  detail.append(sub);
  const list = byId('members');
  list.replaceChildren();
  for (const group of displayed) {
    const matchGroup = group.label.toLocaleLowerCase().includes(query);
    for (const name of group.members) {
      if (query && !matchGroup && !name.toLocaleLowerCase().includes(query)) continue;
      const li = document.createElement('li');
      li.textContent = name;
      const small = document.createElement('small');
      small.textContent = `${group.label} / DIAGRAM ONLY`;
      li.append(small);
      list.append(li);
    }
  }
  if (!list.children.length) {
    const li = document.createElement('li');
    li.textContent = 'No matching diagram names.';
    list.append(li);
  }
}

async function start() {
  try {
    const response = await fetch('./palantir-ecosystem-data.json', {cache: 'no-store'});
    if (!response.ok) throw new Error(`Source returned HTTP ${response.status}`);
    data = await response.json();
    if (data.schema_version !== 1 || data.source.verification_status !== 'unverified' ||
        data.controls.mode !== 'offline_read_only' || data.controls.third_party_access ||
        data.controls.external_writes || data.controls.independent_verification) {
      throw new Error('The source fails the read-only provenance policy');
    }
    byId('count-groups').textContent = data.groups.length;
    byId('count-entities').textContent = data.groups.reduce((n, g) => n + g.members.length, 0);
    byId('count-links').textContent = data.groups.length +
      data.groups.reduce((n, g) => n + g.members.length, 0);
    byId('digest').textContent = data.source.sha256.slice(0, 16) + '…';
    for (const group of data.groups) {
      const option = document.createElement('option');
      option.value = group.id;
      option.textContent = group.label;
      byId('category').append(option);
    }
    byId('search').addEventListener('input', render);
    byId('category').addEventListener('change', () => { selected = byId('category').value; render(); });
    render();
  } catch (error) {
    byId('detail').textContent = 'Dataset unavailable: ' + error.message;
    byId('detail').classList.add('error');
  }
}
start();
