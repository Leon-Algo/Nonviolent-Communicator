#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "${ROOT_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.env"
  set +a
fi

MODE="${1:-deploy}"
PROJECT_NAME="${2:-${CF_PAGES_PROJECT_NAME:-}}"
BRANCH="${3:-}"
PUBLISH_DIR="${4:-${ROOT_DIR}/web}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/cloudflare_pages_release.sh deploy <project_name> [branch] [publish_dir]

Examples:
  bash scripts/cloudflare_pages_release.sh deploy nvc-practice-web-cf
  bash scripts/cloudflare_pages_release.sh deploy nvc-practice-web-cf preview ./web

Required env vars:
  CLOUDFLARE_API_TOKEN
  CLOUDFLARE_ACCOUNT_ID

Optional env vars:
  CF_PAGES_PROJECT_NAME (used when project_name arg is omitted)
EOF
}

ensure_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "[FAIL] missing required command: ${cmd}" >&2
    exit 1
  fi
}

ensure_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "[FAIL] missing required env: ${name}" >&2
    exit 1
  fi
}

resolve_branch() {
  if [[ -n "${BRANCH}" ]]; then
    echo "${BRANCH}"
    return
  fi

  if git -C "${ROOT_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git -C "${ROOT_DIR}" rev-parse --abbrev-ref HEAD
    return
  fi

  echo "main"
}

deploy_pages() {
  local branch
  branch="$(resolve_branch)"

  if [[ ! -d "${PUBLISH_DIR}" ]]; then
    echo "[FAIL] publish directory not found: ${PUBLISH_DIR}" >&2
    exit 1
  fi

  echo
  echo "==> deploy cloudflare pages"
  echo "[INFO] project: ${PROJECT_NAME}"
  echo "[INFO] branch: ${branch}"
  echo "[INFO] publish dir: ${PUBLISH_DIR}"

  npx --yes wrangler pages deploy "${PUBLISH_DIR}" \
    --project-name "${PROJECT_NAME}" \
    --branch "${branch}" \
    --commit-dirty=true

  echo
  echo "[PASS] cloudflare pages deploy completed"
}

main() {
  ensure_cmd npx
  ensure_env CLOUDFLARE_API_TOKEN
  ensure_env CLOUDFLARE_ACCOUNT_ID

  if [[ -z "${PROJECT_NAME}" ]]; then
    echo "[FAIL] missing project_name argument (or CF_PAGES_PROJECT_NAME env)" >&2
    usage
    exit 1
  fi

  case "${MODE}" in
    deploy)
      deploy_pages
      ;;
    *)
      echo "[FAIL] unsupported mode: ${MODE}" >&2
      usage
      exit 1
      ;;
  esac
}

main "$@"
