// Portfolio service worker.
// Strategy:
//   - Precache the app shell (HTML routes + CSS/JS/favicon/manifest) on install.
//   - Navigation requests: network-first, fall back to cached shell (offline).
//   - Fingerprinted assets (?v=hash): network, cached copy as offline fallback.
//   - Other static same-origin GETs: stale-while-revalidate.
//   - API POSTs: always network (never cached — results depend on input).

const VERSION = "v4";
const SHELL_CACHE = `fq-shell-${VERSION}`;
const RUNTIME_CACHE = `fq-runtime-${VERSION}`;

const SHELL_URLS = [
  "/",
  "/financial-statements",
  "/bank-reconciliation",
  "/audit-analytics",
  "/stress-test",
  "/retirement",
  "/methodology",
  "/static/style.css",
  "/static/acct.js",
  "/static/financial_statements.js",
  "/static/bank_rec.js",
  "/static/audit_analytics.js",
  "/static/samples/trial_balance.csv",
  "/static/samples/book_ledger.csv",
  "/static/samples/bank_statement.csv",
  "/static/samples/ap_disbursements.csv",
  "/static/stress_test.js",
  "/static/retirement.js",
  "/static/favicon.svg",
  "/static/icons/apple-touch-icon.png",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/icon-maskable-512.png",
  "/manifest.webmanifest",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL_URLS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== SHELL_CACHE && k !== RUNTIME_CACHE)
          .map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Navigation: network-first, fall back to cache, then to "/" shell.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((res) => {
          const copy = res.clone();
          caches.open(SHELL_CACHE).then((c) => c.put(request, copy));
          return res;
        })
        .catch(() =>
          caches.match(request).then((hit) => hit || caches.match("/"))
        )
    );
    return;
  }

  // Fingerprinted assets (?v=<hash>): the URL changes whenever the file does,
  // so go to the network and keep a copy; offline, fall back to any cached
  // version of the same file.
  if (url.searchParams.has("v")) {
    event.respondWith(
      fetch(request)
        .then((res) => {
          if (res && res.status === 200) {
            const copy = res.clone();
            caches.open(RUNTIME_CACHE).then((c) => c.put(request, copy));
          }
          return res;
        })
        .catch(() => caches.match(request, { ignoreSearch: true }))
    );
    return;
  }

  // Other static assets: stale-while-revalidate.
  event.respondWith(
    caches.match(request).then((cached) => {
      const networkFetch = fetch(request)
        .then((res) => {
          if (res && res.status === 200 && res.type === "basic") {
            const copy = res.clone();
            caches.open(RUNTIME_CACHE).then((c) => c.put(request, copy));
          }
          return res;
        })
        .catch(() => cached);
      return cached || networkFetch;
    })
  );
});
