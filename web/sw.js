const SW_VERSION = "v12";
const STATIC_CACHE_NAME = `nvc-static-${SW_VERSION}`;
const SHELL_CACHE_FILES = [
  "/styles.css",
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
  return ["style", "image", "font"].includes(request.destination);
}

async function networkFirst(request) {
  // 在线时永远先取新文件，避免同版本 SW 部署后样式/图标长期过期；
  // 离线时回退到缓存，保留原有的离线能力。
  try {
    const response = await fetch(request);
    await putStaticCache(request, response);
    return response;
  } catch {
    const cached = await matchStaticCache(request);
    if (cached) {
      return cached;
    }
    return buildOfflineTextResponse();
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

  if (isStaticCandidate(request, url)) {
    event.respondWith(
      networkFirst(request).catch(() => fetch(request).catch(() => buildOfflineTextResponse()))
    );
  }
});
