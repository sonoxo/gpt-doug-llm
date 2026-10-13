const assert = require('node:assert/strict');
const { createRequire } = require('node:module');
const { test } = require('node:test');

// Resolve the dependencies Express actually uses, including nested installs.
const expressRequire = createRequire(require.resolve('express'));
const proxyaddr = expressRequire('proxy-addr');
const qs = expressRequire('qs');

test('IPv4 clients cannot spoof forwarded addresses through short mapped-IPv6 trust prefixes', () => {
  const req = { socket: { remoteAddress: '203.0.113.9' }, headers: { 'x-forwarded-for': '10.1.2.3' } };
  for (const subnet of ['::ffff:10.0.0.0/8', '::/1']) {
    assert.equal(proxyaddr(req, proxyaddr.compile(subnet)), '203.0.113.9');
    assert.equal(proxyaddr(req, proxyaddr.compile([subnet, '127.0.0.1/32'])), '203.0.113.9');
  }
});

test('correctly scoped IPv4 and mapped-IPv6 proxy ranges still work', () => {
  for (const subnet of ['10.0.0.0/8', '::ffff:10.0.0.0/104']) {
    const trust = proxyaddr.compile(subnet);
    assert.equal(trust('10.1.2.3'), true);
    assert.equal(trust('203.0.113.9'), false);
    assert.equal(trust('::ffff:10.1.2.3'), true);
  }
});

test('query serialization does not invoke attacker-controlled constructor.isBuffer', () => {
  assert.doesNotThrow(() => qs.stringify({ value: { constructor: { isBuffer: 'not-a-function' } } }));
  assert.equal(qs.stringify({ tags: ['one', 'two'] }, { arrayFormat: 'repeat' }), 'tags=one&tags=two');
  assert.deepEqual(qs.parse('filter[name]=demo'), { filter: { name: 'demo' } });
});
