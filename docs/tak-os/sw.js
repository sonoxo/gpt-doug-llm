/* Cache only the free, public, same-origin app shell. Never cache map tiles or operational data. */
const CACHE = 'gpt-doug-tak-os-simulator-v1';
const SHELL = ['./', './index.html', './manifest.webmanifest', './icon.svg'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)));
  self.skipWaiting();
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('gpt-doug-tak-os-') && key !== CACHE).map(key => caches.delete(key)))));
  self.clients.claim();
});
self.addEventListener('fetch', event => {
  const req = event.request;
  const url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== self.location.origin) return;
  if (!url.pathname.includes('/tak-os/')) return;
  // Never cache map tiles or user data: only immutable, public app-shell assets.
  const path = url.pathname.split('/').pop();
  if (!['','index.html','icon.svg','manifest.webmanifest'].includes(path)) return;
  event.respondWith(fetch(req).then(response => {
    if (response.ok && response.type === 'basic') {
      const copy = response.clone();
      caches.open(CACHE).then(cache => cache.put(req,copy));
    }
    return response;
  }).catch(() => caches.match(req).then(cached => cached || (path === '' ? caches.match('./index.html') : Response.error()))));
});
