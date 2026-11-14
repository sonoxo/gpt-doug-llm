/* Glass Onion / ZYRA JUKEBOX public-navigation guard.
 * Client-side defense-in-depth only. It cannot secure provider accounts,
 * prevent redirects after navigation, or replace server-side authorization.
 * No tokens, account IDs or entered URLs are logged or persisted here.
 */
(function (root) {
  'use strict';
  const HOSTS = Object.freeze({
    archive: ['archive.org', 'www.archive.org'],
    soundcloud: ['soundcloud.com', 'www.soundcloud.com', 'w.soundcloud.com'],
    youtube: ['youtube.com', 'www.youtube.com', 'youtu.be'],
    bandcamp: ['bandcamp.com', 'www.bandcamp.com'],
    audius: ['audius.co'],
    jamendo: ['jamendo.com', 'www.jamendo.com']
  });
  const SECRET_QUERY_KEYS = new Set([
    'access_token','id_token','refresh_token','api_key','apikey','password',
    'secret','client_secret','authorization','auth','code','session',
    'jwt','otp','pin','account','account_number','routing','iban','ssn','card'
  ]);
  function check(service, raw) {
    if (!Object.prototype.hasOwnProperty.call(HOSTS, service)) {
      return { allowed: false, reason: 'unregistered_service' };
    }
    if (typeof raw !== 'string' || !raw || raw.length > 2048 || /[\\\x00-\x1f\x7f]/.test(raw)) {
      return { allowed: false, reason: 'invalid_url' };
    }
    try {
      const url = new URL(raw);
      if (url.protocol !== 'https:' || url.username || url.password ||
          (url.port && url.port !== '443') || !HOSTS[service].includes(url.hostname.toLowerCase())) {
        return { allowed: false, reason: 'unapproved_destination' };
      }
      for (const key of url.searchParams.keys()) {
        if (SECRET_QUERY_KEYS.has(key.trim().toLowerCase())) {
          return { allowed: false, reason: 'sensitive_parameter' };
        }
      }
      return { allowed: true, reason: 'reviewed_public_destination' };
    } catch (_) {
      return { allowed: false, reason: 'invalid_url' };
    }
  }
  const api = Object.freeze({ check, version: 'glass-onion/music-v1' });
  root.GlassOnionMusicShield = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
