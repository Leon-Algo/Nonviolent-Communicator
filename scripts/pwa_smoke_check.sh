#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

required_files=(
  "web/manifest.webmanifest"
  "web/sw.js"
  "web/icons/icon-192.png"
  "web/icons/icon-512.png"
)

for path in "${required_files[@]}"; do
  if [[ ! -f "${path}" ]]; then
    echo "[FAIL] missing file: ${path}" >&2
    exit 1
  fi
done

node --check web/sw.js

python3 - <<'PY'
import json
from pathlib import Path

manifest_path = Path("web/manifest.webmanifest")
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

required_keys = ["name", "short_name", "start_url", "display", "theme_color", "icons"]
for key in required_keys:
    if key not in manifest:
        raise SystemExit(f"[FAIL] manifest missing key: {key}")

if manifest["display"] != "standalone":
    raise SystemExit("[FAIL] manifest display must be standalone")

icons = manifest.get("icons", [])
if not isinstance(icons, list) or len(icons) < 2:
    raise SystemExit("[FAIL] manifest icons must contain at least 2 entries")

sizes = {item.get("sizes", "") for item in icons if isinstance(item, dict)}
for expected in {"192x192", "512x512"}:
    if expected not in sizes:
        raise SystemExit(f"[FAIL] manifest icons missing size: {expected}")

print("[PASS] manifest validation")
PY

echo "[PASS] pwa smoke check completed"
