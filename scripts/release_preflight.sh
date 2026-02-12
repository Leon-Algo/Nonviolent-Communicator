#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

API_BASE_URL="${1:-${API_BASE_URL:-https://nvc-practice-api.vercel.app}}"
SKIP_REMOTE_API_SMOKE="${SKIP_REMOTE_API_SMOKE:-0}"

step() {
  echo
  echo "==> $1"
}

step "backend unit tests"
source .venv/bin/activate
pytest backend/tests -q

deactivate || true

step "frontend script syntax"
node --check web/app.js

step "shell script syntax"
bash -n scripts/api_smoke_test.sh
bash -n scripts/rls_isolation_check.sh
bash -n scripts/supabase_jwt_api_smoke_test.sh

step "RLS isolation check (Supabase REST)"
bash scripts/rls_isolation_check.sh

if [[ "${SKIP_REMOTE_API_SMOKE}" == "1" ]]; then
  echo
  echo "[SKIP] Supabase JWT API smoke skipped (SKIP_REMOTE_API_SMOKE=1)"
else
  step "Supabase JWT API smoke (${API_BASE_URL})"
  bash scripts/supabase_jwt_api_smoke_test.sh "${API_BASE_URL}"
fi

echo

echo "[PASS] release preflight completed"
