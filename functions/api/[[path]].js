const DEFAULT_PROXY_ORIGIN = "https://nvc-practice-api.vercel.app";

function resolveProxyOrigin(env) {
  const raw = String(env?.API_PROXY_ORIGIN || DEFAULT_PROXY_ORIGIN).trim();
  return raw.replace(/\/+$/, "");
}

function buildUpstreamUrl(requestUrl, env) {
  const proxyOrigin = resolveProxyOrigin(env);
  return `${proxyOrigin}${requestUrl.pathname}${requestUrl.search}`;
}

function buildProxyHeaders(request) {
  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("cf-connecting-ip");
  headers.delete("x-forwarded-host");
  headers.delete("x-forwarded-proto");
  return headers;
}

function buildProxyError(error) {
  const message = String(error?.message || error || "upstream unavailable");
  return new Response(
    JSON.stringify({
      error_code: "UPSTREAM_UNAVAILABLE",
      message,
    }),
    {
      status: 502,
      headers: {
        "content-type": "application/json; charset=utf-8",
        "cache-control": "no-store",
        "x-api-proxy": "cloudflare-pages",
      },
    }
  );
}

export async function onRequest(context) {
  const { request, env } = context;
  const requestUrl = new URL(request.url);
  const upstreamUrl = buildUpstreamUrl(requestUrl, env);
  const headers = buildProxyHeaders(request);
  headers.set("x-forwarded-host", requestUrl.host);
  headers.set("x-forwarded-proto", requestUrl.protocol.replace(":", ""));

  try {
    const response = await fetch(upstreamUrl, {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
      redirect: "manual",
    });

    const outHeaders = new Headers(response.headers);
    outHeaders.set("x-api-proxy", "cloudflare-pages");
    outHeaders.delete("content-encoding");
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: outHeaders,
    });
  } catch (error) {
    return buildProxyError(error);
  }
}
