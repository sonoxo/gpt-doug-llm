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

test('MAX denies malicious radio stream and directory URLs', () => {
  for (const url of [
    'http://radio.example.org/stream',
    'https://127.0.0.1/stream',
    'https://10.0.0.3/stream',
    'https://[::1]/stream',
    'https://local.lan/stream',
    'https://radio.internal/stream',
    'https://radio.onion/stream',
    'https://radio.example.org/stream?access_token=SECRET',
    'https://radio.example.org/stream#access_token=SECRET',
    'https://user:password@radio.example.org/stream',
  ]) {
    assert.equal(shield.checkRadioStream(url).allowed, false, url);
  }
  assert.equal(shield.checkRadioStream('https://radio.example.org/live.mp3').allowed, true);
  assert.equal(
    shield.checkRadioDirectory('https://de1.api.radio-browser.info/json/stations/topclick/60').allowed,
    true
  );
  assert.equal(
    shield.checkRadioDirectory('https://de1.api.radio-browser.info.evil.org/json/stations').allowed,
    false
  );
});

test('MAX direct playback only supports Archive and selected local files', () => {
  assert.equal(shield.checkAudioSource('https://archive.org/download/abc/track.mp3').allowed, true);
  assert.equal(shield.checkAudioSource('https://evil.example.org/song.mp3').allowed, false);
  assert.equal(shield.checkMediaItem({kind:'direct',url:'https://evil.example.org/song.mp3'}).allowed, false);
  assert.equal(shield.checkMediaItem({kind:'radio',url:'https://localhost/live'}).allowed, false);
  assert.equal(shield.checkMediaItem({kind:'youtube',url:'https://www.youtube.com/watch?v=123'}).allowed, true);
  globalThis.location = { origin: 'http://127.0.0.1:8787' };
  try {
    assert.equal(shield.registerLocalFile('blob:http://127.0.0.1:8787/selected-file'), true);
    assert.equal(shield.registerLocalFile('blob:https://evil.example.org/not-selected'), false);
    assert.equal(shield.checkAudioSource('blob:http://127.0.0.1:8787/selected-file').allowed, true);
    assert.equal(shield.checkAudioSource('blob:http://127.0.0.1:8787/other-file').allowed, false);
  } finally { delete globalThis.location; }
});

test('MAX Jukebox app and docs guard every playback path', () => {
  const fs = require('node:fs');
  for (const directory of [
    __dirname,
    require('node:path').resolve(__dirname, '../../docs/jukebox'),
  ]) {
    const app = fs.readFileSync(require('node:path').join(directory,'app.js'),'utf8');
    const radio = fs.readFileSync(require('node:path').join(directory,'radio.js'),'utf8');
    const controls = fs.readFileSync(require('node:path').join(directory,'controls-save.js'),'utf8');
    const html = fs.readFileSync(require('node:path').join(directory,'index.html'),'utf8');
    assert.ok(app.includes('checkAudioSource(url)'));
    assert.ok(app.includes('registerLocalFile(url)'));
    assert.ok(radio.includes('checkRadioStream(url)'));
    assert.ok(radio.includes('checkRadioDirectory(url)'));
    assert.ok(controls.includes('checkMediaItem(item)'));
    assert.ok(html.indexOf('glass-onion-shield.js') < html.indexOf('app.js'));
    assert.ok(!radio.includes('<img class="station-logo"'));
  }
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
    assert.deepEqual(docs.checkRadioStream(url), shield.checkRadioStream(url));
  }
});
