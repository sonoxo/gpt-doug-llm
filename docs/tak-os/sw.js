/* Offline cache for same-origin public app-shell only; do not cache CoT API or OSM imagery. */
const CACHE = 'gpt-doug-tak-os-chaos-swarm-v4';
const SHELL = ['./','./index.html','./app.js','./bridge.js','./swarm-ui.js','./styles.css','./icon.svg','./manifest.webmanifest'];
const ALLOWED = new Set(['','index.html','app.js','bridge.js','swarm-ui.js','styles.css','icon.svg','manifest.webmanifest']);
self.addEventListener('install', event => { event.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL))); self.skipWaiting(); });
self.addEventListener('activate', event => { event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith('gpt-doug-tak-os-') && k !== CACHE).map(k => caches.delete(k))))); self.clients.claim(); });
self.addEventListener('fetch', event => {
  const request = event.request, url = new URL(request.url), scope = new URL(self.registration.scope);
  if (request.method !== 'GET' || url.origin !== scope.origin || !url.pathname.startsWith(scope.pathname) || url.pathname.includes('/api/')) return;
  const relative = url.pathname.slice(scope.pathname.length);
  if (!ALLOWED.has(relative)) return;
  event.respondWith(fetch(request).then(response => {
    if (response.ok && response.type === 'basic') {
      const copy = response.clone(); caches.open(CACHE).then(cache => cache.put(request, copy));
    }
    return response;
  }).catch(() => caches.match(request).then(found => found || (relative === '' ? caches.match('./index.html') : Response.error()))));
});
