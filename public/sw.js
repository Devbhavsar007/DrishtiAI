// DrishtiAI Service Worker — PWA Offline & Caching
// v3: network-first for HTML to prevent stale-cache black screen
const CACHE_NAME = 'drishti-ai-v3';
const PRECACHE_URLS = [
  '/icon-192.png',
  '/icon-512.png',
  '/manifest.json',
];

// Install: pre-cache essential static assets (NOT index.html — always fetch fresh)
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_URLS);
    })
  );
  self.skipWaiting();
});

// Activate: clean up ALL old caches immediately
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// Fetch strategy:
//  • Navigation requests (HTML pages): NETWORK-FIRST (prevents stale black screen)
//  • API calls: bypass SW entirely
//  • Hashed assets (/assets/*): cache-first (Vite hashes guarantee uniqueness)
//  • Everything else: network-first with cache fallback
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // Never intercept API calls — let them go straight to the network
  if (
    url.pathname.startsWith('/api') ||
    url.pathname.startsWith('/analyze') ||
    url.pathname.startsWith('/translate') ||
    url.pathname.startsWith('/results')
  ) {
    return;
  }

  // NAVIGATION REQUESTS (HTML pages): always try network first
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Cache the fresh HTML for offline fallback
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          return response;
        })
        .catch(() => {
          // Offline: serve cached HTML if available
          return caches.match(request).then((cached) => {
            return cached || caches.match('/');
          });
        })
    );
    return;
  }

  // HASHED ASSETS (Vite output in /assets/): cache-first (immutable filenames)
  if (url.pathname.startsWith('/assets/')) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request).then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        });
      })
    );
    return;
  }

  // ALL OTHER REQUESTS: network-first with cache fallback
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok && url.origin === self.location.origin) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return response;
      })
      .catch(() => {
        return caches.match(request);
      })
  );
});
