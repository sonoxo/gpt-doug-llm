import assert from 'node:assert/strict';
import test from 'node:test';
import {handleRequest} from './worker.mjs';

function request(host, country, options = {}) {
  const value = new Request('https://' + host + '/museum?tab=maps', options);
  if (country !== undefined) Object.defineProperty(value, 'cf', {value: {country}});
  return value;
}

test('denies China without contacting origin', async () => {
  let calls = 0;
  const response = await handleRequest(request('xunia.org', 'CN'), async () => {
    calls++;
    return new Response('origin');
  });
  assert.equal(response.status, 403);
  assert.equal(response.headers.get('cache-control'), 'no-store');
  assert.equal(calls, 0);
});

test('country match is case-insensitive', async () => {
  const response = await handleRequest(request('www.xunia.org', 'cn'), async () => {
    throw new Error('denied request reached origin');
  });
  assert.equal(response.status, 403);
});

test('forwards non-China requests to GitHub Pages unchanged', async () => {
  const incoming = request('xunia.org', 'US', {headers: {'X-Request-Id': 'test'}});
  let observed;
  const response = await handleRequest(incoming, async (req) => {
    observed = req;
    return new Response('existing site', {status: 200});
  });
  assert.equal(response.status, 200);
  assert.equal(await response.text(), 'existing site');
  assert.equal(observed, incoming);
});

test('ignores spoofed CF-IPCountry header', async () => {
  const incoming = request('xunia.org', undefined, {headers: {'CF-IPCountry': 'CN'}});
  const response = await handleRequest(incoming, async () => new Response('allowed'));
  assert.equal(response.status, 200);
});

test('preview reports the domain is not protected', async () => {
  let originCalled = false;
  const response = await handleRequest(
    request('xunia-geo-guard-preview.example.workers.dev', 'US'), async () => {
      originCalled = true;
      return new Response('origin');
    });
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.service, 'xunia-geo-guard');
  assert.equal(body.domainProtected, false);
  assert.equal(body.mode, 'preview');
  assert.equal(originCalled, false);
});

test('blocks China on preview endpoint too', async () => {
  const response = await handleRequest(
    request('xunia-geo-guard-preview.example.workers.dev', 'CN'));
  assert.equal(response.status, 403);
});

test('refuses unrelated hosts', async () => {
  const response = await handleRequest(request('attacker.example', 'US'), async () => {
    throw new Error('must not fetch arbitrary host');
  });
  assert.equal(response.status, 421);
});
