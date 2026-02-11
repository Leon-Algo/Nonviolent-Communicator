#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8000}"
USER_ID="${2:-8a4c3f2a-2f88-4c74-9bc0-3123d26df302}"
AUTH_HEADER="Authorization: Bearer mock_${USER_ID}"
CONTENT_TYPE="Content-Type: application/json"

echo "Using BASE_URL=${BASE_URL}"
echo "Using mock user=${USER_ID}"

create_scene_payload='{
  "title":"和同事沟通延期风险",
  "template_id":"PEER_FEEDBACK",
  "counterparty_role":"PEER",
  "relationship_level":"TENSE",
  "goal":"确认新的里程碑并明确责任",
  "pain_points":["对方容易防御","我会急躁"],
  "context":"这个需求已经两次延期，影响发布节奏",
  "power_dynamic":"PEER_LEVEL"
}'

echo "[1/4] create scene"
scene_resp="$(curl -sS -X POST "${BASE_URL}/api/v1/scenes" -H "${AUTH_HEADER}" -H "${CONTENT_TYPE}" -d "${create_scene_payload}")"
echo "${scene_resp}" | jq .
scene_id="$(echo "${scene_resp}" | jq -r '.scene_id')"

echo "[2/4] create session"
create_session_payload="$(jq -n --arg sid "${scene_id}" '{"scene_id":$sid,"target_turns":6}')"
session_resp="$(curl -sS -X POST "${BASE_URL}/api/v1/sessions" -H "${AUTH_HEADER}" -H "${CONTENT_TYPE}" -d "${create_session_payload}")"
echo "${session_resp}" | jq .
session_id="$(echo "${session_resp}" | jq -r '.session_id')"

echo "[3/4] create message with feedback"
create_message_payload='{
  "client_message_id":"4c16e607-2c2f-4a89-bf20-4a33317b640a",
  "content":"你们总是拖延，根本不专业。"
}'
message_resp="$(curl -sS -X POST "${BASE_URL}/api/v1/sessions/${session_id}/messages" -H "${AUTH_HEADER}" -H "${CONTENT_TYPE}" -d "${create_message_payload}")"
echo "${message_resp}" | jq .
first_user_message_id="$(echo "${message_resp}" | jq -r '.user_message_id')"

echo "[4/4] retry same client_message_id (idempotency check)"
retry_resp="$(curl -sS -X POST "${BASE_URL}/api/v1/sessions/${session_id}/messages" -H "${AUTH_HEADER}" -H "${CONTENT_TYPE}" -d "${create_message_payload}")"
echo "${retry_resp}" | jq .
retry_user_message_id="$(echo "${retry_resp}" | jq -r '.user_message_id')"

if [[ "${first_user_message_id}" != "${retry_user_message_id}" ]]; then
  echo "Idempotency check failed: expected same user_message_id, got ${first_user_message_id} vs ${retry_user_message_id}" >&2
  exit 1
fi

echo "Smoke test complete."
