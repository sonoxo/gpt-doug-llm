import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { XuniaChain } from '../src/chain.js';
import { COIN, Wallet, formatXun } from '../src/crypto.js';

test('mining creates XUN and signed transfer settles with fee', () => {
  const dir = mkdtempSync(join(tmpdir(), 'xunia-'));
  const path = join(dir, 'chain.json');
  const chain = new XuniaChain(path);
  const alice = Wallet.create();
  const bob = Wallet.create();

  const mined = chain.mine(alice.address, 1);
  assert.equal(mined.height, 1);
  assert.equal(chain.balance(alice.address), 1_000n * COIN);

  const tx = alice.signPayment(bob.address, 25n * COIN, 1n * COIN, chain.nonce(alice.address));
  chain.submit(tx);
  const settled = chain.mine(alice.address, 1);

  assert.equal(settled.transactions.length, 1);
  assert.equal(chain.balance(bob.address), 25n * COIN);
  assert.equal(chain.nonce(alice.address), 1);
  assert.equal(formatXun(chain.balance(alice.address)), '1975.00000000');
  assert.equal(chain.validateChain(), true);

  const reloaded = new XuniaChain(path);
  assert.equal(reloaded.balance(bob.address), 25n * COIN);
  assert.equal(JSON.parse(readFileSync(path, 'utf8')).chainId, 'xunia-main-v1');
});

test('rejects forged signatures and overspending', () => {
  const dir = mkdtempSync(join(tmpdir(), 'xunia-'));
  const chain = new XuniaChain(join(dir, 'chain.json'));
  const alice = Wallet.create();
  const bob = Wallet.create();
  const mallory = Wallet.create();
  chain.mine(alice.address, 1);

  const valid = alice.signPayment(bob.address, 10n * COIN, 0n, 0);
  assert.throws(() => chain.submit({ ...valid, signature: mallory.signPayment(bob.address, 1n, 0n, 0).signature }), /invalid transaction signature/);

  const tooMuch = alice.signPayment(bob.address, 2_000n * COIN, 0n, 0);
  assert.throws(() => chain.submit(tooMuch), /insufficient funds/);
});
