'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const shield = require('./glass-onion-shield.js');

test('known public music link can be navigated without account access', () => {
  for (const [name, url] of [
    ['soundcloud', 'https://soundcloud.com/search?q=music'],
    ['youtube', 'https://www.youtube.com/results?search_query=music'],
    ['archive', 'https://archive.org/advancedsearch.php?q=music'],
    ['bandcamp', 'https://bandcamp.com/search?q=ambient'],
  ]) assert.equal(shield.check(name, url).allowed, true);
});

test('reject phishing/lookalike hosts and unsafe schemes', () => {
  for (const url of [
    'https://soundcloud.com.evil.example/tracks',
    'http://soundcloud.com/search?q=x',
    'file:///etc/passwd',
    'https://user:pass@soundcloud.com/',
    'https://soundcloud.com:444/search',
    'https://127.0.0.1:8787/',
    'https://soundcloud.com\\@evil.example/',
  ]) assert.equal(shield.check('soundcloud', url).allowed, false, url);
});

test('refuse URLs with credentials, OAuth codes and billing details', () => {
  for (const key of ['access_token', 'client_secret', 'code', 'account_number']) {
    assert.equal(shield.check('youtube', 'https://youtube.com/watch?v=abc&' + key + '=SECRET').allowed, false);
  }
});

test('unknown provider is denied and no network call is performed', () => {
  assert.equal(shield.check('unregistered-bank', 'https://example.com/').allowed, false);
  assert.equal(shield.check('spotify', 'https://open.spotify.com/').allowed, false);
});

test('duplicated GitHub Pages shield has same policy', () => {
  const docs = require('../../docs/jukebox/glass-onion-shield.js');
  const cases = [
    ['soundcloud','https://soundcloud.com/search?q=abc'],
    ['youtube','https://youtube.com.evil.example/watch'],
    ['archive','https://archive.org/metadata/book'],
    ['bandcamp','https://bandcamp.com/search?q=hello'],
  ];
  for (const [service, url] of cases) {
    assert.deepEqual(docs.check(service, url), shield.check(service, url));
  }
});
