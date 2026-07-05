#!/usr/bin/env python3
"""Diagnose voice integration environment without printing secrets."""

from __future__ import annotations

import os
import socket
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
ROOT_ENV = ROOT / ".env"
QUICKSTART_ENV = ROOT / "agent-quickstart-python" / "server" / ".env.local"

AGORA_REGIONAL_HOSTS = {
    "US": "api-us-west-1.agora.io",
    "EU": "api-eu-west-1.agora.io",
    "AP": "api-ap-southeast-1.agora.io",
    "CN": "api-cn-east-1.sd-rtn.com",
}


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        os.environ.setdefault(key, value)


def resolve_host(host: str, port: int = 443) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError:
        return []
    return sorted({info[4][0] for info in infos})


def format_ips(ips: list[str]) -> str:
    if not ips:
        return "unresolved"
    suffix = " (check network/DNS)" if any(ip.startswith("28.") for ip in ips) else ""
    return ",".join(ips[:4]) + suffix


def main() -> int:
    load_env_file(ROOT_ENV)
    load_env_file(QUICKSTART_ENV)

    database_url = os.environ.get("DATABASE_URL", "")
    supabase_url = os.environ.get("SUPABASE_URL", "")
    agora_app_id = os.environ.get("AGORA_APP_ID", "")
    agora_app_certificate = os.environ.get("AGORA_APP_CERTIFICATE", "")
    agora_area = os.environ.get("AGORA_AREA", "US").strip().upper() or "US"
    if agora_area not in AGORA_REGIONAL_HOSTS:
        agora_area = "US"

    print("voice-env-diagnostics")
    print(f"DATABASE_URL set: {bool(database_url)}")
    if database_url:
        parsed_db = urlsplit(database_url.replace("postgresql+asyncpg://", "postgresql://", 1))
        print(f"DATABASE_URL host: {parsed_db.hostname or '-'}")
        if parsed_db.hostname:
            print(f"DATABASE_URL resolved: {format_ips(resolve_host(parsed_db.hostname, parsed_db.port or 5432))}")

    print(f"SUPABASE_URL set: {bool(supabase_url)}")
    if supabase_url:
        parsed_supabase = urlsplit(supabase_url)
        print(f"SUPABASE_URL host: {parsed_supabase.hostname or '-'}")
        if parsed_supabase.hostname:
            print(f"SUPABASE_URL resolved: {format_ips(resolve_host(parsed_supabase.hostname, 443))}")

    print(f"AGORA_APP_ID set: {bool(agora_app_id)}")
    print(f"AGORA_APP_CERTIFICATE set: {bool(agora_app_certificate)}")
    print(f"AGORA_AREA: {agora_area}")
    agora_host = AGORA_REGIONAL_HOSTS[agora_area]
    print(f"AGORA_AREA host: {agora_host}")
    print(f"AGORA_AREA resolved: {format_ips(resolve_host(agora_host, 443))}")

    try:
        import agora_agent  # noqa: F401
    except Exception as exc:  # pragma: no cover - environment diagnostic only
        print(f"agora-agent import: failed ({type(exc).__name__})")
    else:
        print("agora-agent import: ok")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
