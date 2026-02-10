/**
 * PWA Service Worker – Offline app shell + network-only API.
 * Caches same-origin static assets and index.html for offline loading;
 * all /api/ requests go to network only (no caching of PHI).
 */
const CACHE_VERSION = 'v2';
const APP_SHELL_CACHE = 'emr-app-shell-' + CACHE_VERSION;

function isSameOrigin(url) {
  try {
    return new URL(url).origin === self.location.origin;
  } catch {
    return false;
  }
}

function isApiRequest(url) {
  return url.includes('/api/');
}

function isAppShellRequest(request) {
  if (request.method !== 'GET') return false;
  if (!isSameOrigin(request.url)) return false;
  const path = new URL(request.url).pathname;
  return path === '/' || path.startsWith('/static/') || path === '/index.html';
}

function isNavigationRequest(request) {
  return request.mode === 'navigate';
}

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys
          .filter((key) => key.startsWith('emr-app-shell-') && key !== APP_SHELL_CACHE)
          .map((key) => caches.delete(key))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = event.request.url || '';

  // API: network only, return JSON 503 on failure (no caching of PHI)
  if (isApiRequest(url)) {
    event.respondWith(
      fetch(event.request, { cache: 'no-store' }).catch(() => {
        return new Response(
          JSON.stringify({
            error: 'Network error',
            message: 'Unable to reach the server. Check your connection.',
            detail: 'Network request failed',
          }),
          {
            status: 503,
            statusText: 'Service Unavailable',
            headers: { 'Content-Type': 'application/json' },
          }
        );
      })
    );
    return;
  }

  // App shell: network-first, fallback to cache for offline
  if (isAppShellRequest(event.request)) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const clone = response.clone();
          const reqUrl = new URL(event.request.url);
          const cacheKey = isNavigationRequest(event.request)
            ? self.location.origin + '/'
            : event.request.url;
          caches.open(APP_SHELL_CACHE).then((cache) => {
            cache.put(cacheKey, clone);
          });
          return response;
        })
        .catch(() => {
          if (isNavigationRequest(event.request)) {
            return caches.open(APP_SHELL_CACHE).then((cache) => {
              return cache.match(self.location.origin + '/').then((cached) => {
                return cached || new Response(
                  '<!DOCTYPE html><html><body><p>You are offline. Open the app when back online.</p></body></html>',
                  { headers: { 'Content-Type': 'text/html' } }
                );
              });
            });
          }
          return caches.match(event.request);
        })
    );
    return;
  }

  event.respondWith(
    fetch(event.request).catch(() => {
      return caches.match(event.request).then((cached) => {
        return cached || new Response('', { status: 504, statusText: 'Gateway Timeout' });
      });
    })
  );
});
