/* Public shell only. Build replaces this token; no private content enters CacheStorage. */
const BUILD = '__DRIVER_BUILD__';
const CACHE = 'fe-driver-shell-' + BUILD;
const MANIFEST = '/driver/asset-manifest.json';
let shell;
const hex = bytes => [...new Uint8Array(bytes)].map(n => n.toString(16).padStart(2, '0')).join('');

function validate(manifest) {
  if (manifest.version !== BUILD || manifest.entry !== '/driver/index.html' ||
      !Array.isArray(manifest.assets) || !manifest.assets.length || manifest.assets.length > 500) throw Error('Invalid shell manifest');
  const urls = new Set();
  for (const item of manifest.assets) {
    if (!item || !/^\/(?:assets\/[^?#]+|js\/[^/?#]+\.js|css\/[^/?#]+\.css|driver\/(?:index\.html|manifest\.webmanifest)|favicon\.ico)$/.test(item.url) ||
        item.url.includes('..') || !/^[a-f0-9]{64}$/.test(item.sha256) || urls.has(item.url)) throw Error('Unsafe shell asset');
    urls.add(item.url);
  }
  if (!urls.has(manifest.entry)) throw Error('Missing shell entry');
  return manifest;
}

async function publicResponse(url, hash) {
  const response = await fetch(url, { credentials: 'omit', cache: 'no-store', redirect: 'error' });
  if (response.status !== 200 || response.type === 'opaque') throw Error('Shell unavailable');
  if (hex(await crypto.subtle.digest('SHA-256', await response.clone().arrayBuffer())) !== hash) throw Error('Shell hash mismatch');
  return response;
}

self.addEventListener('install', event => event.waitUntil((async () => {
  const response = await fetch(MANIFEST, { credentials: 'omit', cache: 'no-store', redirect: 'error' });
  if (response.status !== 200) throw Error('Manifest unavailable');
  const manifest = validate(await response.json());
  const responses = await Promise.all(manifest.assets.map(item => publicResponse(item.url, item.sha256)));
  try {
    const cache = await caches.open(CACHE);
    for (let i = 0; i < responses.length; i++) await cache.put(manifest.assets[i].url, responses[i]);
    await cache.put(MANIFEST, new Response(JSON.stringify(manifest), { headers: { 'Content-Type': 'application/json' } }));
    shell = manifest;
  } catch (error) {
    await caches.delete(CACHE);
    throw error;
  }
})()));

// Updates wait for the driver's explicit action. Never claim or reload open pages.
self.addEventListener('message', event => {
  if (event.data?.type === 'ACTIVATE_DRIVER_UPDATE') self.skipWaiting();
});

async function manifest() {
  if (!shell) {
    const response = await (await caches.open(CACHE)).match(MANIFEST);
    if (!response) throw Error('Shell installation incomplete');
    shell = validate(await response.json());
  }
  return shell;
}

self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin ||
      request.headers.has('Authorization') || request.headers.has('X-Admin-Key') || request.headers.has('X-Api-Key')) return;
  const document = request.mode === 'navigate' && (url.pathname === '/driver/' || url.pathname === '/driver/index.html');
  if (document) {
    event.respondWith(fetch(request).catch(async () => {
      const current = await manifest();
      const response = await (await caches.open(CACHE)).match(current.entry);
      if (!response) throw Error('Offline shell unavailable');
      return response;
    }));
    return;
  }
  // Only manifest-pinned static paths are considered; API/auth traffic bypasses us.
  if (!/^\/(?:assets\/|js\/[^/?#]+\.js$|css\/[^/?#]+\.css$|driver\/manifest\.webmanifest$|favicon\.ico$)/.test(url.pathname) || url.search) return;
  event.respondWith((async () => {
    const current = await manifest();
    if (!current.assets.some(item => item.url === url.pathname)) return fetch(request);
    return (await (await caches.open(CACHE)).match(url.pathname)) || fetch(request);
  })());
});
