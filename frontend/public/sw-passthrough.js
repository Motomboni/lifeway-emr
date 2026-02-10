/**
 * Minimal pass-through Service Worker for EMR PWA.
 *
 * All API requests (/api/ or /api/v1/) go to the network only – no caching, no 503 Offline.
 * This prevents other SWs (e.g. from PWA extensions) from returning "Offline"
 * for API calls when the app is actually online.
 */
self.addEventListener('fetch', (event) => {
  const url = event.request.url || '';
  const isApi = url.includes('/api/');
  // Pass API requests straight to network; never cache or return "Offline"
  if (isApi) {
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
  event.respondWith(fetch(event.request));
});

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});
