#!/usr/bin/env python3
"""橘晴本地开发服务器：静态资源 + /api 代理。

为什么需要它：
  生产上 Cloudflare Pages Function 会把同源 /api/* 代理到后端，
  本地用 python -m http.server 没有这层代理，且浏览器 CORS 拦截
  跨域直连 api.leoalgo.site，所以本地打开后所有 API 都会失败。
  本脚本在原端口上补齐这一层：静态文件照发，/api/* 与
  /health-backend 转发到后端。

用法：
  python3 scripts/dev_server.py                 # 静态 :8787，代理到 http://localhost:8000
  BACKEND_URL=https://api.leoalgo.site python3 scripts/dev_server.py
  PORT=9000 python3 scripts/dev_server.py

只用标准库，无第三方依赖。
"""

import json
import os
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(ROOT_DIR, "web")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip("/")
PORT = int(os.environ.get("PORT", "8787"))

# 与生产 Pages Function 对齐：/api/* 透传，/health-backend 映射到后端 /health
PROXY_PREFIXES = ("/api/",)
PROXY_EXACT = {"/health-backend": "/health"}

HOP_BY_HOP = {
    "host",
    "connection",
    "content-length",
    "transfer-encoding",
    "keep-alive",
    "upgrade",
    "accept-encoding",  # 不让后端压缩，原样透传 body，避免解压错位
}
TIMEOUT_SECONDS = 180  # LLM 生成可能很慢


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    # -- 路由：代理 or 静态 -------------------------------------------------
    def _proxy_target(self):
        path = self.path.split("?", 1)[0]
        if path in PROXY_EXACT:
            return BACKEND_URL + PROXY_EXACT[path]
        if any(path.startswith(p) for p in PROXY_PREFIXES):
            return BACKEND_URL + self.path
        return None

    def _route(self):
        target = self._proxy_target()
        if target:
            self._proxy(target)
        elif self.command == "GET":
            super().do_GET()
        else:
            self.send_error(404, "Not Found")

    do_GET = _route
    do_POST = _route
    do_PUT = _route
    do_PATCH = _route
    do_DELETE = _route
    do_OPTIONS = _route

    # -- 代理实现 -----------------------------------------------------------
    def _proxy(self, target):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        req = urllib.request.Request(target, data=body, method=self.command)
        for name, value in self.headers.items():
            if name.lower() in HOP_BY_HOP:
                continue
            req.add_header(name, value)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                self._relay(resp.status, resp.headers, resp.read())
        except urllib.error.HTTPError as err:
            # 后端业务错误（4xx/5xx）原样透传，前端按正常错误处理
            self._relay(err.code, err.headers, err.read())
        except Exception as err:  # 后端没起来 / 网络不通
            payload = json.dumps(
                {
                    "detail": "本地代理连不上后端（%s）。先启动后端：cd backend && ../.venv/bin/uvicorn app.main:app --port 8000"
                    % err,
                },
                ensure_ascii=False,
            ).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    def _relay(self, status, headers, data):
        self.send_response(status)
        for name, value in headers.items():
            if name.lower() in HOP_BY_HOP or name.lower() == "content-length":
                continue
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if data:
            self.wfile.write(data)

    # -- 本地开发一律不缓存，避免旧 CSS/JS 粘在浏览器里 ----------------------
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("橘晴 dev server: http://localhost:%d  (静态: web/)" % PORT)
    print("代理 /api/* 与 /health-backend -> %s" % BACKEND_URL)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
