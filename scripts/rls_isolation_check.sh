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

for cmd in curl jq; do
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "Missing required command: ${cmd}" >&2
    exit 1
  fi
done

LAST_STATUS=""
LAST_BODY=""

request_supabase() {
  local method="$1"
  local url="$2"
  local token="${3:-}"
  local payload="${4:-}"
  shift 4 || true

  local -a args
  args=(
    -sS
    -w $'\n%{http_code}'
    -X "${method}"
    "${url}"
    -H "Content-Type: application/json"
    -H "apikey: ${SUPABASE_ANON_KEY}"
  )

  if [[ -n "${token}" ]]; then
    args+=( -H "Authorization: Bearer ${token}" )
  fi

  while (($#)); do
    args+=( -H "$1" )
    shift
  done

  if [[ -n "${payload}" ]]; then
    args+=( -d "${payload}" )
  fi

  local response
  response="$(curl "${args[@]}")"
  LAST_BODY="${response%$'\n'*}"
  LAST_STATUS="${response##*$'\n'}"
}

expect_2xx() {
  local action="$1"
  if [[ "${LAST_STATUS}" -lt 200 || "${LAST_STATUS}" -ge 300 ]]; then
    echo "[FAIL] ${action}: expected 2xx, got ${LAST_STATUS}" >&2
    echo "${LAST_BODY}" | jq . >&2 || echo "${LAST_BODY}" >&2
    exit 1
  fi
}

expect_non_2xx() {
  local action="$1"
  if [[ "${LAST_STATUS}" -ge 200 && "${LAST_STATUS}" -lt 300 ]]; then
    echo "[FAIL] ${action}: expected non-2xx, got ${LAST_STATUS}" >&2
    echo "${LAST_BODY}" | jq . >&2 || echo "${LAST_BODY}" >&2
    exit 1
  fi
}

signup_and_login() {
  local email="$1"
  local password="$2"

  local signup_payload
  signup_payload="$(jq -n --arg email "${email}" --arg password "${password}" '{email:$email,password:$password}')"
  request_supabase "POST" "${SUPABASE_URL%/}/auth/v1/signup" "" "${signup_payload}"

  local login_payload
  login_payload="$(jq -n --arg email "${email}" --arg password "${password}" '{email:$email,password:$password}')"
  request_supabase "POST" "${SUPABASE_URL%/}/auth/v1/token?grant_type=password" "" "${login_payload}"
  expect_2xx "login ${email}"

  local token
  token="$(echo "${LAST_BODY}" | jq -r '.access_token // empty')"
  if [[ -z "${token}" ]]; then
    echo "[FAIL] login ${email}: access_token missing" >&2
    echo "${LAST_BODY}" | jq . >&2 || echo "${LAST_BODY}" >&2
    exit 1
  fi

  echo "${token}"
}

fetch_user_id() {
  local token="$1"
  request_supabase "GET" "${SUPABASE_URL%/}/auth/v1/user" "${token}" ""
  expect_2xx "fetch auth user"

  local user_id
  user_id="$(echo "${LAST_BODY}" | jq -r '.id // empty')"
  if [[ -z "${user_id}" ]]; then
    echo "[FAIL] fetch auth user: id missing" >&2
    echo "${LAST_BODY}" | jq . >&2 || echo "${LAST_BODY}" >&2
    exit 1
  fi

  echo "${user_id}"
}

now_ts="$(date +%s)"
password="NvcRls!123456"
email_a="rls_a_${now_ts}@example.com"
email_b="rls_b_${now_ts}@example.com"

echo "[1/7] create/login user A and user B"
token_a="$(signup_and_login "${email_a}" "${password}")"
token_b="$(signup_and_login "${email_b}" "${password}")"
user_a_id="$(fetch_user_id "${token_a}")"
user_b_id="$(fetch_user_id "${token_b}")"
echo "user_a=${user_a_id}"
echo "user_b=${user_b_id}"

echo "[2/7] user A inserts scene"
scene_payload="$(jq -n \
  --arg uid "${user_a_id}" \
  '{
    user_id: $uid,
    title: "RLS scene by A",
    template_id: "PEER_FEEDBACK",
    counterparty_role: "PEER",
    relationship_level: "NEUTRAL",
    goal: "verify rls",
    pain_points: [],
    context: "rls integration test",
    power_dynamic: "PEER_LEVEL"
  }'
)"
request_supabase "POST" "${SUPABASE_URL%/}/rest/v1/scenes" "${token_a}" "${scene_payload}" "Prefer: return=representation"
if [[ "${LAST_STATUS}" -lt 200 || "${LAST_STATUS}" -ge 300 ]]; then
  if echo "${LAST_BODY}" | jq -r '.message // empty' | grep -q "row-level security policy"; then
    echo "[HINT] Execute db/migrations/0005_fix_request_user_id_claim_resolution.sql, then rerun." >&2
  fi
fi
expect_2xx "insert scene by user A"
scene_id="$(echo "${LAST_BODY}" | jq -r '.[0].id // empty')"
if [[ -z "${scene_id}" ]]; then
  echo "[FAIL] insert scene by user A: scene id missing" >&2
  echo "${LAST_BODY}" | jq . >&2 || echo "${LAST_BODY}" >&2
  exit 1
fi

echo "[3/7] user B cannot read user A scene"
request_supabase "GET" "${SUPABASE_URL%/}/rest/v1/scenes?id=eq.${scene_id}&select=id,user_id" "${token_b}" ""
expect_2xx "query scene by user B"
scene_count_b="$(echo "${LAST_BODY}" | jq 'length')"
if [[ "${scene_count_b}" -ne 0 ]]; then
  echo "[FAIL] user B unexpectedly sees user A scene" >&2
  echo "${LAST_BODY}" | jq . >&2 || echo "${LAST_BODY}" >&2
  exit 1
fi

echo "[4/7] user B cannot insert scene with user A id"
forbidden_scene_payload="$(jq -n \
  --arg uid "${user_a_id}" \
  '{
    user_id: $uid,
    title: "forbidden scene",
    template_id: "PEER_FEEDBACK",
    counterparty_role: "PEER",
    relationship_level: "NEUTRAL",
    goal: "forbidden",
    pain_points: [],
    context: "forbidden",
    power_dynamic: "PEER_LEVEL"
  }'
)"
request_supabase "POST" "${SUPABASE_URL%/}/rest/v1/scenes" "${token_b}" "${forbidden_scene_payload}" "Prefer: return=representation"
expect_non_2xx "insert scene by user B with user A id"

echo "[5/7] user A inserts session"
session_payload="$(jq -n --arg uid "${user_a_id}" --arg sid "${scene_id}" '{user_id:$uid,scene_id:$sid,target_turns:6,current_turn:0}')"
request_supabase "POST" "${SUPABASE_URL%/}/rest/v1/sessions" "${token_a}" "${session_payload}" "Prefer: return=representation"
expect_2xx "insert session by user A"
session_id="$(echo "${LAST_BODY}" | jq -r '.[0].id // empty')"
if [[ -z "${session_id}" ]]; then
  echo "[FAIL] insert session by user A: session id missing" >&2
  echo "${LAST_BODY}" | jq . >&2 || echo "${LAST_BODY}" >&2
  exit 1
fi

echo "[6/7] user B cannot read user A session"
request_supabase "GET" "${SUPABASE_URL%/}/rest/v1/sessions?id=eq.${session_id}&select=id,user_id,scene_id" "${token_b}" ""
expect_2xx "query session by user B"
session_count_b="$(echo "${LAST_BODY}" | jq 'length')"
if [[ "${session_count_b}" -ne 0 ]]; then
  echo "[FAIL] user B unexpectedly sees user A session" >&2
  echo "${LAST_BODY}" | jq . >&2 || echo "${LAST_BODY}" >&2
  exit 1
fi

echo "[7/7] user B cannot insert message into user A session"
forbidden_message_payload="$(jq -n --arg sid "${session_id}" '{session_id:$sid,role:"USER",turn_no:1,content:"forbidden"}')"
request_supabase "POST" "${SUPABASE_URL%/}/rest/v1/messages" "${token_b}" "${forbidden_message_payload}" "Prefer: return=representation"
expect_non_2xx "insert message by user B on user A session"

echo "[PASS] RLS isolation check completed successfully"
