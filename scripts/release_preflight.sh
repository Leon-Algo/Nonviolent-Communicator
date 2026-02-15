#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

API_BASE_URL="${1:-${API_BASE_URL:-https://nvc-practice-api.vercel.app}}"
SKIP_REMOTE_API_SMOKE="${SKIP_REMOTE_API_SMOKE:-0}"
SKIP_RLS_ISOLATION="${SKIP_RLS_ISOLATION:-0}"
SKIP_OFNR_EVAL="${SKIP_OFNR_EVAL:-0}"
RUN_ONLINE_OFNR_EVAL="${RUN_ONLINE_OFNR_EVAL:-0}"
RUN_DB_TESTS="${RUN_DB_TESTS:-0}"

step() {
  echo
  echo "==> $1"
}

ensure_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "[FAIL] missing required command: ${cmd}" >&2
    exit 1
  fi
}

ensure_cmd pytest
ensure_cmd node
ensure_cmd bash
ensure_cmd python3

step "backend tests"
if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
RUN_DB_TESTS="${RUN_DB_TESTS}" pytest backend/tests -q

step "frontend script syntax"
node --check web/app.js

step "shell script syntax"
bash -n scripts/api_smoke_test.sh
bash -n scripts/rls_isolation_check.sh
bash -n scripts/supabase_jwt_api_smoke_test.sh
bash -n scripts/release_preflight.sh
bash -n scripts/pwa_smoke_check.sh
bash -n scripts/vercel_release.sh

step "pwa smoke checks"
bash scripts/pwa_smoke_check.sh

if [[ "${SKIP_OFNR_EVAL}" == "1" ]]; then
  echo
  echo "[SKIP] OFNR eval skipped (SKIP_OFNR_EVAL=1)"
else
  step "OFNR eval regression (offline)"
  python scripts/run_ofnr_eval.py --mode offline

  if [[ "${RUN_ONLINE_OFNR_EVAL}" == "1" ]]; then
    step "OFNR eval regression (online)"
    python scripts/run_ofnr_eval.py --mode online
  else
    echo
    echo "[SKIP] online OFNR eval skipped (RUN_ONLINE_OFNR_EVAL!=1)"
  fi
fi

if [[ "${SKIP_RLS_ISOLATION}" == "1" ]]; then
  echo
  echo "[SKIP] RLS isolation check skipped (SKIP_RLS_ISOLATION=1)"
else
  step "RLS isolation check (Supabase REST)"
  bash scripts/rls_isolation_check.sh
fi

if [[ "${SKIP_REMOTE_API_SMOKE}" == "1" ]]; then
  echo
  echo "[SKIP] Supabase JWT API smoke skipped (SKIP_REMOTE_API_SMOKE=1)"
else
  step "Supabase JWT API smoke (${API_BASE_URL})"
  bash scripts/supabase_jwt_api_smoke_test.sh "${API_BASE_URL}"
fi

echo

echo "[PASS] release preflight completed"

if declare -F deactivate >/dev/null 2>&1; then
  deactivate
fi
