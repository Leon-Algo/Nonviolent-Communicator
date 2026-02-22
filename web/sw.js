const SW_VERSION = "v7";
const STATIC_CACHE_NAME = `nvc-static-${SW_VERSION}`;
const SHELL_CACHE_FILES = [
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
  if (request.mode === "navigate") return false;
  return ["script", "style", "image", "font"].includes(request.destination);
}

async function cacheFirst(request) {
  const cacheKey = request;

  const cached = await matchStaticCache(cacheKey, { ignoreSearch: request.mode === "navigate" });
  if (cached) {
    return cached;
  }

  try {
    const response = await fetch(request);
    await putStaticCache(cacheKey, response);
    return response;
  } catch {
    return buildOfflineTextResponse();
  }
}

async function networkFirstApi(request) {
  try {
    return await fetch(request);
  } catch {
    return buildOfflineApiResponse();
  }
}

async function openStaticCache() {
  try {
    return await caches.open(STATIC_CACHE_NAME);
  } catch {
    return null;
  }
}

async function matchStaticCache(cacheKey, options = {}) {
  const cache = await openStaticCache();
  if (!cache) return null;
  try {
    return await cache.match(cacheKey, options);
  } catch {
    return null;
  }
}

async function putStaticCache(cacheKey, response) {
  if (!response || !response.ok) return;
  const cache = await openStaticCache();
  if (!cache) return;
  try {
    await cache.put(cacheKey, response.clone());
  } catch {
    // Ignore cache write failures and keep serving network response.
  }
}

function buildOfflineTextResponse() {
  return new Response("offline", {
    status: 503,
    statusText: "Service Unavailable",
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}

function buildOfflineApiResponse() {
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

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const cache = await openStaticCache();
      if (!cache) return;
      try {
        await cache.addAll(SHELL_CACHE_FILES);
      } catch {
        // Keep install successful even if a subset of static files cannot be cached.
      }
    })()
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys().catch(() => []);
      const staleKeys = keys.filter(
        (key) => key.startsWith("nvc-static-") && key !== STATIC_CACHE_NAME
      );
      await Promise.all(staleKeys.map((key) => caches.delete(key)));
      // Do not claim existing clients immediately in this migration version.
      // This avoids forcing an automatic controller switch + reload loop
      // for users still running older app.js runtime logic.
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
    event.respondWith(
      cacheFirst(request).catch(() => fetch(request).catch(() => buildOfflineTextResponse()))
    );
  }
});
