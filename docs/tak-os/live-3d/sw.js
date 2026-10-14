/* Public app shell only. No source responses, geolocation, TAK data or credentials cached. */
const CACHE='gpt-doug-live-earth-iphone-shell-v1';
const SHELL=['./index.html','./style.css','./iphone-grid.css','./iphone-grid.js','./ontology.js','./live-earth.js','./cesium-config.js','./manifest.webmanifest'];
const ALLOWED=new Set(SHELL.map(x=>x.slice(2)));
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)));self.skipWaiting()});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('gpt-doug-live-earth-iphone-shell-')&&k!==CACHE).map(k=>caches.delete(k)))));self.clients.claim()});
self.addEventListener('fetch',event=>{
 const request=event.request;if(request.method!=='GET')return;
 const url=new URL(request.url),base=new URL(self.registration.scope);
 if(url.origin!==base.origin||!url.pathname.startsWith(base.pathname))return;
 const relative=decodeURIComponent(url.pathname.slice(base.pathname.length))||'index.html';
 if(!ALLOWED.has(relative)||url.search)return;
 event.respondWith(fetch(request).then(response=>{
   if(response.ok){const clone=response.clone();event.waitUntil(caches.open(CACHE).then(c=>c.put(request,clone)))}
   return response;
 }).catch(()=>caches.match(request).then(r=>r||Response.error())));
});
