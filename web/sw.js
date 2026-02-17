const SW_VERSION = "v4";
const STATIC_CACHE_NAME = `nvc-static-${SW_VERSION}`;
const SHELL_CACHE_FILES = [
  "/",
  "/index.html",
  "/styles.css",
  "/app.js",
  "/manifest.webmanifest",
  "/icons/favicon-32.png",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/icon-maskable-192.png",
  "/icons/icon-maskable-512.png",
];

function isApiRequest(url) {
  return url.origin === self.location.origin && url.pathname.startsWith("/api/");
}

function isStaticCandidate(request, url) {
  if (request.method !== "GET") return false;
  if (url.origin !== self.location.origin) return false;
  if (isApiRequest(url)) return false;
  if (request.mode === "navigate") return true;
  return ["script", "style", "image", "font"].includes(request.destination);
}

async function cacheFirst(request) {
  const cache = await caches.open(STATIC_CACHE_NAME);
  const cacheKey = request.mode === "navigate" ? "/index.html" : request;
  const cached = await cache.match(cacheKey, { ignoreSearch: request.mode === "navigate" });
  if (cached) {
    return cached;
  }

  try {
    const response = await fetch(request);
    if (response && response.ok) {
      await cache.put(cacheKey, response.clone());
    }
    return response;
  } catch {
    if (request.mode === "navigate") {
      const fallback = await cache.match("/index.html");
      if (fallback) return fallback;
    }
    return new Response("offline", {
      status: 503,
      statusText: "Service Unavailable",
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }
}

async function networkFirstApi(request) {
  try {
    return await fetch(request);
  } catch {
    return new Response(
      JSON.stringify({
        error_code: "OFFLINE",
        message: "当前离线，无法访问服务端接口。",
      }),
      {
        status: 503,
        statusText: "Service Unavailable",
        headers: { "Content-Type": "application/json; charset=utf-8" },
      }
    );
  }
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE_NAME).then((cache) => cache.addAll(SHELL_CACHE_FILES))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      const staleKeys = keys.filter(
        (key) => key.startsWith("nvc-static-") && key !== STATIC_CACHE_NAME
      );
      await Promise.all(staleKeys.map((key) => caches.delete(key)));
      await self.clients.claim();
    })()
  );
});

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);

  if (isApiRequest(url)) {
    event.respondWith(networkFirstApi(request));
    return;
  }

  if (isStaticCandidate(request, url)) {
    event.respondWith(cacheFirst(request));
  }
});
