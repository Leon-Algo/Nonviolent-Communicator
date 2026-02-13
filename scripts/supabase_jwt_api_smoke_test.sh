#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "${ROOT_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.env"
  set +a
fi

require_env() {
  local key="$1"
  if [[ -z "${!key:-}" ]]; then
    echo "Missing required env: ${key}" >&2
    exit 1
  fi
}

require_env SUPABASE_URL
require_env SUPABASE_ANON_KEY

for cmd in curl jq python3; do
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "Missing required command: ${cmd}" >&2
    exit 1
  fi
done

API_BASE_URL="${1:-${API_BASE_URL:-https://nvc-practice-api.vercel.app}}"
API_BASE_URL="${API_BASE_URL%/}"

LAST_STATUS=""
LAST_BODY=""

request_json() {
  local method="$1"
  local url="$2"
  local auth_header="${3:-}"
  local payload="${4:-}"

  local -a args
  args=(
    -sS
    -w $'\n%{http_code}'
    -X "${method}"
    "${url}"
    -H "Content-Type: application/json"
  )

  if [[ -n "${auth_header}" ]]; then
    args+=( -H "Authorization: Bearer ${auth_header}" )
  fi

  if [[ -n "${payload}" ]]; then
    args+=( -d "${payload}" )
  fi

  local response
  response="$(curl "${args[@]}")"
  LAST_BODY="${response%$'\n'*}"
  LAST_STATUS="${response##*$'\n'}"
}

expect_status() {
  local expected="$1"
  local action="$2"
  if [[ "${LAST_STATUS}" != "${expected}" ]]; then
    echo "[FAIL] ${action}: expected ${expected}, got ${LAST_STATUS}" >&2
    echo "${LAST_BODY}" | jq . >&2 || echo "${LAST_BODY}" >&2
    exit 1
  fi
}

expect_2xx() {
  local action="$1"
  if [[ "${LAST_STATUS}" -lt 200 || "${LAST_STATUS}" -ge 300 ]]; then
    echo "[FAIL] ${action}: expected 2xx, got ${LAST_STATUS}" >&2
    echo "${LAST_BODY}" | jq . >&2 || echo "${LAST_BODY}" >&2
    exit 1
  fi
}

random_uuid() {
  python3 - <<'PY'
import uuid
print(uuid.uuid4())
PY
}

now_ts="$(date +%s)"
email="jwt_smoke_${now_ts}@example.com"
password="JwtSmoke!123456"

echo "Using API_BASE_URL=${API_BASE_URL}"
echo "Using test email=${email}"

echo "[1/7] signup and login with Supabase"
signup_payload="$(jq -n --arg email "${email}" --arg password "${password}" '{email:$email,password:$password}')"
response="$(curl -sS -w $'\n%{http_code}' -X POST "${SUPABASE_URL%/}/auth/v1/signup" \
  -H "Content-Type: application/json" \
  -H "apikey: ${SUPABASE_ANON_KEY}" \
  -d "${signup_payload}")"
LAST_BODY="${response%$'\n'*}"
LAST_STATUS="${response##*$'\n'}"
if [[ "${LAST_STATUS}" -lt 200 || "${LAST_STATUS}" -ge 300 ]]; then
  echo "signup status=${LAST_STATUS}, continue to login" >&2
fi

login_payload="$(jq -n --arg email "${email}" --arg password "${password}" '{email:$email,password:$password}')"
response="$(curl -sS -w $'\n%{http_code}' -X POST "${SUPABASE_URL%/}/auth/v1/token?grant_type=password" \
  -H "Content-Type: application/json" \
  -H "apikey: ${SUPABASE_ANON_KEY}" \
  -d "${login_payload}")"
LAST_BODY="${response%$'\n'*}"
LAST_STATUS="${response##*$'\n'}"
expect_2xx "Supabase password login"
access_token="$(echo "${LAST_BODY}" | jq -r '.access_token // empty')"
if [[ -z "${access_token}" ]]; then
  echo "[FAIL] Supabase login did not return access_token" >&2
  echo "${LAST_BODY}" | jq . >&2 || echo "${LAST_BODY}" >&2
  exit 1
fi

echo "[2/7] create scene via backend (JWT)"
scene_payload='{
  "title":"JWT smoke scene",
  "template_id":"PEER_FEEDBACK",
  "counterparty_role":"PEER",
  "relationship_level":"TENSE",
  "goal":"validate jwt flow",
  "pain_points":["smoke"],
  "context":"jwt e2e smoke",
  "power_dynamic":"PEER_LEVEL"
}'
request_json "POST" "${API_BASE_URL}/api/v1/scenes" "${access_token}" "${scene_payload}"
expect_status "201" "create scene"
scene_id="$(echo "${LAST_BODY}" | jq -r '.scene_id // empty')"
if [[ -z "${scene_id}" ]]; then
  echo "[FAIL] scene_id missing" >&2
  echo "${LAST_BODY}" | jq . >&2 || echo "${LAST_BODY}" >&2
  exit 1
fi

echo "[3/7] create session via backend (JWT)"
session_payload="$(jq -n --arg sid "${scene_id}" '{scene_id:$sid,target_turns:6}')"
request_json "POST" "${API_BASE_URL}/api/v1/sessions" "${access_token}" "${session_payload}"
expect_status "201" "create session"
session_id="$(echo "${LAST_BODY}" | jq -r '.session_id // empty')"
if [[ -z "${session_id}" ]]; then
  echo "[FAIL] session_id missing" >&2
  echo "${LAST_BODY}" | jq . >&2 || echo "${LAST_BODY}" >&2
  exit 1
fi

echo "[4/7] create message and check idempotency"
client_message_id="$(random_uuid)"
message_payload="$(jq -n --arg cmid "${client_message_id}" '{client_message_id:$cmid,content:"你们总是拖延，根本不专业。"}')"
request_json "POST" "${API_BASE_URL}/api/v1/sessions/${session_id}/messages" "${access_token}" "${message_payload}"
expect_status "200" "create message"
first_msg_id="$(echo "${LAST_BODY}" | jq -r '.user_message_id // empty')"
if [[ -z "${first_msg_id}" ]]; then
  echo "[FAIL] user_message_id missing" >&2
  echo "${LAST_BODY}" | jq . >&2 || echo "${LAST_BODY}" >&2
  exit 1
fi

request_json "POST" "${API_BASE_URL}/api/v1/sessions/${session_id}/messages" "${access_token}" "${message_payload}"
expect_status "200" "retry message"
retry_msg_id="$(echo "${LAST_BODY}" | jq -r '.user_message_id // empty')"
if [[ "${first_msg_id}" != "${retry_msg_id}" ]]; then
  echo "[FAIL] idempotency mismatch: ${first_msg_id} vs ${retry_msg_id}" >&2
  exit 1
fi

echo "[5/7] create summary"
request_json "POST" "${API_BASE_URL}/api/v1/sessions/${session_id}/summary" "${access_token}" ""
expect_status "200" "create summary"
summary_id="$(echo "${LAST_BODY}" | jq -r '.summary_id // empty')"
if [[ -z "${summary_id}" ]]; then
  echo "[FAIL] summary_id missing" >&2
  echo "${LAST_BODY}" | jq . >&2 || echo "${LAST_BODY}" >&2
  exit 1
fi

echo "[6/7] check session history list/detail"
request_json "GET" "${API_BASE_URL}/api/v1/sessions?limit=10&offset=0" "${access_token}" ""
expect_status "200" "session history list"
history_total="$(echo "${LAST_BODY}" | jq -r '.total // 0')"
if [[ "${history_total}" -lt 1 ]]; then
  echo "[FAIL] expected history total >= 1, got ${history_total}" >&2
  exit 1
fi

request_json "GET" "${API_BASE_URL}/api/v1/sessions/${session_id}/history" "${access_token}" ""
expect_status "200" "session history detail"
history_session_id="$(echo "${LAST_BODY}" | jq -r '.session_id // empty')"
if [[ "${history_session_id}" != "${session_id}" ]]; then
  echo "[FAIL] history session id mismatch: ${history_session_id} vs ${session_id}" >&2
  exit 1
fi

echo "[7/7] check weekly progress endpoint"
week_start="$(date +%F)"
request_json "GET" "${API_BASE_URL}/api/v1/progress/weekly?week_start=${week_start}" "${access_token}" ""
expect_status "200" "weekly progress"

echo "[PASS] Supabase JWT API smoke test completed"
