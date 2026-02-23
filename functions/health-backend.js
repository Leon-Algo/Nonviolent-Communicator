const DEFAULT_PROXY_ORIGIN = "https://nvc-practice-api.vercel.app";

function resolveProxyOrigin(env) {
  const raw = String(env?.API_PROXY_ORIGIN || DEFAULT_PROXY_ORIGIN).trim();
  return raw.replace(/\/+$/, "");
}

export async function onRequest(context) {
  const proxyOrigin = resolveProxyOrigin(context.env);
  const targetUrl = `${proxyOrigin}/health`;

  try {
    const response = await fetch(targetUrl, {
      method: "GET",
      headers: { accept: "application/json" },
      redirect: "follow",
    });
    const text = await response.text();
    const headers = new Headers({
      "content-type": response.headers.get("content-type") || "application/json; charset=utf-8",
      "cache-control": "no-store",
      "x-api-proxy": "cloudflare-pages",
      "x-upstream-url": targetUrl,
    });
    return new Response(text, {
      status: response.status,
      statusText: response.statusText,
      headers,
    });
  } catch (error) {
    return new Response(
      JSON.stringify({
        error_code: "UPSTREAM_UNAVAILABLE",
        message: String(error?.message || error || "upstream unavailable"),
      }),
      {
        status: 502,
        headers: {
          "content-type": "application/json; charset=utf-8",
          "cache-control": "no-store",
          "x-api-proxy": "cloudflare-pages",
          "x-upstream-url": targetUrl,
        },
      }
    );
  }
}
