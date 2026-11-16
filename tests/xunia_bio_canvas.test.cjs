'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'docs/biological-data-center/app.js'), 'utf8');
const ontology = JSON.parse(fs.readFileSync(path.join(root, 'docs/biological-data-center/ontology.json'), 'utf8'));

test('real ontology reaches 3D Canvas nodes and edges without JS runtime errors', async () => {
  const elements = new Map();
  const canvasCalls = [];
  const drawContext = {
    setTransform(...args) { canvasCalls.push(['setTransform', ...args]); },
    clearRect() {},
    fillRect() {},
    save() {},
    restore() {},
    beginPath() {},
    ellipse(...args) { canvasCalls.push(['ellipse', ...args]); },
    stroke() {},
    arc(...args) { canvasCalls.push(['arc', ...args]); },
    fill() {},
    moveTo() {},
    lineTo() {},
    fillText(text) { canvasCalls.push(['fillText', text]); },
    measureText(text) { return { width: text.length * 7 }; },
    createRadialGradient() { return { addColorStop() {} }; },
  };
  function element(id) {
    if (elements.has(id)) return elements.get(id);
    const el = {
      id,
      textContent: '',
      children: [],
      classList: { toggle() {} },
      dataset: {},
      style: {},
      disabled: false,
      replaceChildren() { this.children = []; },
      append(...children) { this.children.push(...children); },
      appendChild(child) { this.children.push(child); return child; },
      addEventListener() {},
      getBoundingClientRect() { return { width: 940, height: 540, left: 0, top: 0 }; },
      getContext(type) { assert.equal(type, '2d'); return drawContext; },
      setPointerCapture() {},
      focus() {},
    };
    elements.set(id, el);
    return el;
  }
  const window = {
    matchMedia() { return { matches: false }; },
    devicePixelRatio: 1,
    addEventListener() {},
  };
  const document = {
    getElementById: element,
    createElement() { return element('dynamic-' + elements.size); },
    querySelectorAll() { return []; },
  };
  const errors = [];
  const requests = [];
  const context = {
    window,
    document,
    location: { hostname: 'xunia.org' },
    fetch: async (url) => {
      requests.push(url);
      if (url === './ontology.json') return { ok: true, json: async () => ontology };
      throw Error('Unexpected fetch: ' + url);
    },
    requestAnimationFrame: () => {},
    setInterval: () => {},
    console: { error: (...args) => errors.push(args), log() {} },
  };
  vm.runInNewContext(source, context, { filename: 'app.js' });
  await new Promise(resolve => setImmediate(resolve));
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(requests, ['./ontology.json']);
  assert.equal(errors.length, 0, 'JavaScript initialization failed: ' +
    errors.map(args => args.map(String).join(' ')).join(' | '));
  assert.ok(elements.has('nodeTitle'), 'Node inspector did not mount');
  assert.equal(elements.get('nodeTitle').textContent, ontology.nodes[0].name);
  assert.ok(canvasCalls.some(x => x[0] === 'ellipse'), 'expected organic nucleus rings');
  assert.ok(canvasCalls.filter(x => x[0] === 'arc').length >= ontology.nodes.length,
    'all nodes must be drawn with Canvas arcs');
  assert.ok(canvasCalls.some(x => x[0] === 'fillText'), 'node labels must be drawn');
  assert.ok(String(elements.get('camera').textContent).includes('ZOOM 1.00'),
    'camera footer must update after a complete draw');
  assert.deepEqual(errors, []);
});
