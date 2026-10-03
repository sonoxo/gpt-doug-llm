import test from 'node:test';
import assert from 'node:assert/strict';
import {
  mergeBridgeOrigins,
  resolveAppPort,
} from '../scripts/start-with-gpt-doug.mjs';

test('merges the required local app origins without duplicates', () => {
  assert.equal(
    mergeBridgeOrigins('https://example.test,http://localhost:8787', 8787),
    'https://example.test,http://localhost:8787,http://127.0.0.1:8787',
  );
});

test('uses a custom app port for both localhost forms', () => {
  assert.equal(
    mergeBridgeOrigins('', 9000),
    'http://localhost:9000,http://127.0.0.1:9000',
  );
});

test('validates the application port', () => {
  assert.equal(resolveAppPort('8787'), 8787);
  assert.throws(() => resolveAppPort('0'), /Invalid GrimTheBuilder port/);
  assert.throws(() => resolveAppPort('not-a-port'), /Invalid GrimTheBuilder port/);
});
