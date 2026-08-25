import test from 'node:test';
import assert from 'node:assert/strict';
import type { IncomingMessage } from 'node:http';
import { mkdtempSync, readFileSync } from 'node:fs';
import { randomBytes } from 'node:crypto';
import os from 'node:os';
import path from 'node:path';
import { JsonState } from '../src/persistence.js';
import { AuthPolicy } from '../src/security.js';
import { SovereigntyPolicy } from '../src/sovereignty.js';

test('sovereignty enforces realm, region, egress, and policy fingerprint', () => {
  const config = {
    mode: 'enforced' as const,
    realm: 'xunia-us-va',
    region: 'us-va',
    allowedRegions: ['us-va'],
    airGapped: false,
    allowedEgressOrigins: ['https://models.example.gov'],
    keyAuthority: 'customer' as const,
    customerKeyId: 'kms://customer/xunia',
    requireEncryptedState: true,
    expectedFingerprint: ''
  };
  const policy = new SovereigntyPolicy(config);
  assert.equal(policy.evaluateRequest('xunia-us-va', 'us-va').allowed, true);
  assert.equal(policy.evaluateRequest('other-realm', 'us-va').reason, 'realm_mismatch');
  assert.equal(policy.evaluateRequest('xunia-us-va', 'eu-west').reason, 'region_not_allowed');
  assert.equal(policy.evaluateEgress('http://127.0.0.1:4317/health').allowed, true);
  assert.equal(policy.evaluateEgress('https://models.example.gov/v1/chat').allowed, true);
  assert.equal(policy.evaluateEgress('https://unapproved.example.com/v1/chat').reason, 'egress_origin_not_allowlisted');
  assert.equal(policy.ready(true).ok, true);

  const locked = new SovereigntyPolicy({ ...config, expectedFingerprint: policy.fingerprint() });
  assert.equal(locked.ready(true).ok, true);
  const wrong = new SovereigntyPolicy({ ...config, expectedFingerprint: '0'.repeat(64) });
  assert.equal(wrong.ready(true).ok, false);
});

test('air-gapped sovereignty denies public egress even when an origin is listed', () => {
  const policy = new SovereigntyPolicy({
    mode: 'enforced',
    realm: 'airgap',
    region: 'edge-1',
    allowedRegions: ['edge-1'],
    airGapped: true,
    allowedEgressOrigins: ['https://example.com'],
    keyAuthority: 'customer',
    customerKeyId: 'hsm://edge/key',
    requireEncryptedState: false,
    expectedFingerprint: ''
  });
  assert.equal(policy.evaluateEgress('https://example.com').reason, 'air_gap_external_egress_denied');
  assert.equal(policy.evaluateEgress('http://sonoxo:3001/api/sonoxo/harvest').allowed, true);
});

test('sovereignty-off RBAC permits a realm-bound credential without rewriting it', () => {
  const policy = new SovereigntyPolicy({
    mode: 'off',
    realm: 'realm-a',
    region: 'us-va',
    allowedRegions: ['us-va'],
    keyAuthority: 'platform',
    requireEncryptedState: false
  });
  const auth = new AuthPolicy(true, JSON.stringify({
    token: { role: 'viewer', subject: 'viewer', realm: 'realm-b' }
  }), '', policy);
  const req = { headers: { authorization: 'Bearer token' } } as unknown as IncomingMessage;
  const principal = auth.authenticate(req);
  assert.ok(principal);
  assert.equal(principal.realm, 'realm-b');
  assert.equal(auth.permits(principal, 'viewer'), true);
  assert.equal(auth.ready(), true);
});

test('enforced sovereignty readiness requires at least one realm-usable credential', () => {
  const policy = new SovereigntyPolicy({
    mode: 'enforced',
    realm: 'realm-a',
    region: 'us-va',
    allowedRegions: ['us-va'],
    keyAuthority: 'platform',
    requireEncryptedState: false,
    expectedFingerprint: ''
  });
  const wrongRealm = new AuthPolicy(true, JSON.stringify({
    wrong: { role: 'admin', subject: 'admin', realm: 'realm-b' }
  }), '', policy);
  assert.equal(wrongRealm.ready(), false);
  const badReq = { headers: { authorization: 'Bearer wrong' } } as unknown as IncomingMessage;
  assert.equal(wrongRealm.authenticate(badReq), null);

  const usable = new AuthPolicy(true, JSON.stringify({
    good: { role: 'admin', subject: 'admin', realm: 'realm-a' }
  }), '', policy);
  assert.equal(usable.ready(), true);
  const goodReq = { headers: { authorization: 'Bearer good' } } as unknown as IncomingMessage;
  assert.equal(usable.authenticate(goodReq)?.realm, 'realm-a');
});

test('JsonState encrypts persisted sovereign state with AES-256-GCM', () => {
  const dir = mkdtempSync(path.join(os.tmpdir(), 'xunia-sovereign-state-'));
  const file = path.join(dir, 'state.json');
  const key = randomBytes(32).toString('base64');
  const state = new JsonState<{ secret: string }>(file, key);
  state.write({ secret: 'classified-test-value' });
  const raw = readFileSync(file, 'utf8');
  assert.doesNotMatch(raw, /classified-test-value/);
  assert.match(raw, /encrypted-state-v1/);
  assert.equal(state.status().encrypted, true);

  const reloaded = new JsonState<{ secret: string }>(file, key);
  assert.deepEqual(reloaded.read({ secret: '' }), { secret: 'classified-test-value' });
});
