/* GLASS ONION / GPT-DOUG-MAX / ZYRA JUKEBOX
 * Browser-only defense-in-depth for cooperating Jukebox playback/navigation.
 * Never an identity provider, DRM control, redirect guard or bank firewall.
 */
(function (root) {
  'use strict';
  const HOSTS = Object.freeze({
    archive: ['archive.org', 'www.archive.org'],
    soundcloud: ['soundcloud.com', 'www.soundcloud.com', 'w.soundcloud.com'],
    youtube: ['youtube.com', 'www.youtube.com', 'youtu.be'],
    bandcamp: ['bandcamp.com', 'www.bandcamp.com'],
    audius: ['audius.co'],
    jamendo: ['jamendo.com', 'www.jamendo.com'],
  });
  const RADIO_DIRECTORIES = new Set([
    'de1.api.radio-browser.info',
    'nl1.api.radio-browser.info',
    'at1.api.radio-browser.info',
  ]);
  const SECRET_QUERY_KEYS = new Set([
    'access_token', 'id_token', 'refresh_token', 'token', 'api_key',
    'apikey', 'password', 'passwd', 'secret', 'client_secret',
    'authorization', 'auth', 'code', 'session', 'jwt', 'otp', 'pin',
    'account', 'account_number', 'routing', 'iban', 'ssn', 'card',
  ]);
  const PRIVATE_HOST_SUFFIXES = [
    '.localhost', '.local', '.lan', '.internal', '.home', '.invalid',
    '.test', '.onion', '.example',
  ];
  const localFileURLs = new Set();

  function reject(reason) { return { allowed: false, reason }; }
  function allow(reason) { return { allowed: true, reason }; }

  function publicHttps(raw) {
    if (typeof raw !== 'string' || !raw || raw.length > 2048 ||
        /[\\\x00-\x1f\x7f]/.test(raw)) return { result: reject('invalid_url') };
    try {
      const u = new URL(raw);
      const host = u.hostname.toLowerCase();
      if (u.protocol !== 'https:' || u.username || u.password ||
          (u.port && u.port !== '443') || host.endsWith('.')) {
        return { result: reject('unsafe_url') };
      }
      if (!host.includes('.') || host === 'localhost' ||
          PRIVATE_HOST_SUFFIXES.some(suffix => host.endsWith(suffix)) ||
          host.includes(':') || /^\d+\.\d+\.\d+\.\d+$/.test(host)) {
        return { result: reject('private_or_ip_destination') };
      }
      for (const key of u.searchParams.keys()) {
        if (SECRET_QUERY_KEYS.has(key.trim().toLowerCase())) {
          return { result: reject('sensitive_query_parameter') };
        }
      }
      // OAuth implicit flows may carry tokens in URL fragments, not query strings.
      if (/(^|[&#])(?:access_token|refresh_token|id_token|token|code|secret|session|auth)=/i.test(u.hash.slice(1))) {
        return { result: reject('sensitive_url_fragment') };
      }
      return { host, result: allow('public_https_destination') };
    } catch (_) {
      return { result: reject('invalid_url') };
    }
  }

  function check(service, raw) {
    if (!Object.prototype.hasOwnProperty.call(HOSTS, service)) {
      return reject('unregistered_service');
    }
    const parsed = publicHttps(raw);
    if (!parsed.result.allowed) return parsed.result;
    if (!HOSTS[service].includes(parsed.host)) return reject('unapproved_destination');
    return allow('reviewed_public_destination');
  }

  function checkRadioDirectory(raw) {
    const parsed = publicHttps(raw);
    if (!parsed.result.allowed) return parsed.result;
    return RADIO_DIRECTORIES.has(parsed.host)
      ? allow('reviewed_radio_directory')
      : reject('unapproved_radio_directory');
  }

  function checkRadioStream(raw) {
    const parsed = publicHttps(raw);
    if (!parsed.result.allowed) return parsed.result;
    // Radio stations are third parties: checking a URL cannot vouch for
    // redirects, DNS resolution, live content, uptime or provider safety.
    return allow('public_https_radio_stream');
  }

  function registerLocalFile(raw) {
    if (typeof raw !== 'string' || !raw.startsWith('blob:') ||
        raw.length > 2048 || /[\x00-\x1f\x7f]/.test(raw)) return false;
    try {
      const file = new URL(raw);
      const base = root.location?.origin;
      if (file.protocol !== 'blob:' || !base ||
          !raw.startsWith('blob:' + base + '/')) return false;
    } catch (_) { return false; }
    if (localFileURLs.size >= 32) localFileURLs.delete(localFileURLs.values().next().value);
    localFileURLs.add(raw);
    return true;
  }

  function checkAudioSource(raw) {
    if (localFileURLs.has(raw)) return allow('user_selected_local_file');
    return check('archive', raw);
  }

  function checkMediaItem(item) {
    if (!item || typeof item !== 'object') return reject('invalid_media_item');
    if (item.kind === 'radio') return checkRadioStream(item.url);
    if (item.kind === 'soundcloud') return check('soundcloud', item.url);
    if (item.kind === 'youtube') return check('youtube', item.url);
    if (item.kind === 'direct') return checkAudioSource(item.url);
    return reject('unapproved_media_kind');
  }

  const api = Object.freeze({
    check, checkRadioDirectory, checkRadioStream,
    registerLocalFile, checkAudioSource, checkMediaItem,
    version: 'glass-onion/music-max-v2',
  });
  root.GlassOnionMusicShield = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
