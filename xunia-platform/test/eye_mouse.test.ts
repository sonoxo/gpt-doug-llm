import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { OntologyStore } from '../src/ontology.js';
import { AipEngine, ModelGateway } from '../src/aip.js';
import { createPlatformHandler } from '../src/server.js';
import { AuthPolicy, RateLimiter } from '../src/security.js';

test('Eye Mouse is public while camera permission remains route-scoped', async (t) => {
  const ontology = new OntologyStore();
  ontology.seed();
  const aip = new AipEngine(ontology, new ModelGateway('', ''));
  const policy = new AuthPolicy(true, JSON.stringify({
    'viewer-token': { role: 'viewer', subject: 'viewer' }
  }));
  const handler = createPlatformHandler(ontology, aip, policy, new RateLimiter(1000));
  const server = createServer((req, res) => void handler(req, res));
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise<void>((resolve) => server.close(() => resolve())));

  const address = server.address();
  assert.ok(address && typeof address === 'object');
  const base = `http://127.0.0.1:${address.port}`;

  const home = await fetch(`${base}/`);
  assert.equal(home.status, 200);
  assert.equal(home.headers.get('permissions-policy'), 'camera=(), microphone=(), geolocation=()');
  assert.doesNotMatch(home.headers.get('content-security-policy') ?? '', /cdn\.jsdelivr\.net/);

  const eye = await fetch(`${base}/eye-mouse`);
  assert.equal(eye.status, 200);
  assert.match(await eye.text(), /XUNIA Eye Mouse/);
  assert.equal(eye.headers.get('permissions-policy'), 'camera=(self), microphone=(), geolocation=()');
  assert.match(eye.headers.get('content-security-policy') ?? '', /cdn\.jsdelivr\.net/);
  assert.match(eye.headers.get('content-security-policy') ?? '', /storage\.googleapis\.com/);

  const script = await fetch(`${base}/eye-mouse.js`);
  assert.equal(script.status, 200);
  assert.match(script.headers.get('content-type') ?? '', /javascript/);
  assert.match(await script.text(), /FaceLandmarker/);

  const styles = await fetch(`${base}/eye-mouse.css`);
  assert.equal(styles.status, 200);
  assert.match(styles.headers.get('content-type') ?? '', /text\/css/);

  assert.equal((await fetch(`${base}/api/ontology`)).status, 401);
});
