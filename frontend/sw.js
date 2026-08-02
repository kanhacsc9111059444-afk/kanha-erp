/* KanhaERP PWA — offline shell cache */
const CACHE = "kanha-shell-v4";
const PRECACHE = [
  "/",
  "/assets/manifest.json",
  "/assets/favicon.svg",
  "/assets/css/app.css?v=form14",
  "/assets/js/api.js?v=form14",
  "/assets/js/app.js?v=form14",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  // Never cache API — always live process
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/auth/")) return;
  // CSS/JS: network-first so clock/UI fixes show immediately
  if (url.pathname.startsWith("/assets/css/") || url.pathname.startsWith("/assets/js/") || url.pathname === "/") {
    event.respondWith(
      fetch(req)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy));
          }
          return res;
        })
        .catch(() => caches.match(req).then((hit) => hit || caches.match("/")))
    );
    return;
  }
  event.respondWith(
    caches.match(req).then((hit) =>
      hit ||
      fetch(req)
        .then((res) => {
          if (res.ok && url.pathname.startsWith("/assets/")) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy));
          }
          return res;
        })
        .catch(() => hit || caches.match("/"))
    )
  );
});
