#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "${ROOT_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.env"
  set +a
fi

MODE="${1:-preview}"
TARGET="${2:-all}"
REF="${3:-}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/vercel_release.sh preview <web|api|all>
  bash scripts/vercel_release.sh prod <web|api|all>
  bash scripts/vercel_release.sh promote <web|api> <deployment_url_or_id>
  bash scripts/vercel_release.sh rollback <web|api> <deployment_url_or_id>

Examples:
  bash scripts/vercel_release.sh preview all
  bash scripts/vercel_release.sh prod all
  bash scripts/vercel_release.sh promote web https://nvc-practice-web-xxx.vercel.app
  bash scripts/vercel_release.sh rollback api dpl_xxxxxxxxx
EOF
}

ensure_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "[FAIL] missing required command: ${cmd}" >&2
    exit 1
  fi
}

normalize_target() {
  case "${1}" in
    backend)
      echo "api"
      ;;
    *)
      echo "${1}"
      ;;
  esac
}

run_vercel() {
  local project_dir="$1"
  shift
  if [[ -n "${VERCEL_TOKEN:-}" ]]; then
    vercel --cwd "${project_dir}" "$@" --token "${VERCEL_TOKEN}"
  else
    vercel --cwd "${project_dir}" "$@"
  fi
}

run_step() {
  local label="$1"
  shift
  echo
  echo "==> ${label}"

  local output
  local status
  set +e
  output="$("$@" 2>&1)"
  status=$?
  set -e

  echo "${output}"
  if [[ ${status} -ne 0 ]]; then
    return "${status}"
  fi

  local url
  url="$(printf '%s\n' "${output}" | grep -Eo '(Preview|Production): https://[^ ]+' | tail -1 | awk '{print $2}' || true)"
  if [[ -z "${url}" ]]; then
    url="$(printf '%s\n' "${output}" | grep -Eo 'https://[^ ]+\.vercel\.app' | tail -1 || true)"
  fi
  if [[ -n "${url}" ]]; then
    echo "[INFO] deployment url: ${url}"
  fi
}

deploy_one() {
  local target="$1"
  local mode="$2"
  local project_dir
  local label

  case "${target}" in
    web)
      project_dir="${ROOT_DIR}/web"
      label="web"
      ;;
    api)
      project_dir="${ROOT_DIR}/backend"
      label="api"
      ;;
    *)
      echo "[FAIL] unsupported target: ${target}" >&2
      usage
      exit 1
      ;;
  esac

  if [[ "${mode}" == "preview" ]]; then
    run_step "deploy ${label} preview" run_vercel "${project_dir}" deploy -y
    return
  fi

  if [[ "${mode}" == "prod" ]]; then
    run_step "deploy ${label} production" run_vercel "${project_dir}" deploy --prod -y
    return
  fi

  if [[ -z "${REF}" ]]; then
    echo "[FAIL] missing deployment ref for mode=${mode}" >&2
    usage
    exit 1
  fi

  if [[ "${mode}" == "promote" ]]; then
    run_step "promote ${label} deployment" run_vercel "${project_dir}" promote "${REF}" -y
    return
  fi

  if [[ "${mode}" == "rollback" ]]; then
    run_step "rollback ${label} deployment" run_vercel "${project_dir}" rollback "${REF}" -y
    return
  fi

  echo "[FAIL] unsupported mode: ${mode}" >&2
  usage
  exit 1
}

main() {
  ensure_cmd vercel
  TARGET="$(normalize_target "${TARGET}")"

  case "${MODE}" in
    preview|prod)
      if [[ "${TARGET}" == "all" ]]; then
        deploy_one "web" "${MODE}"
        deploy_one "api" "${MODE}"
      else
        deploy_one "${TARGET}" "${MODE}"
      fi
      ;;
    promote|rollback)
      if [[ "${TARGET}" == "all" ]]; then
        echo "[FAIL] mode=${MODE} does not support target=all; choose web or api" >&2
        usage
        exit 1
      fi
      deploy_one "${TARGET}" "${MODE}"
      ;;
    *)
      echo "[FAIL] unsupported mode: ${MODE}" >&2
      usage
      exit 1
      ;;
  esac

  echo
  echo "[PASS] vercel release flow completed"
}

main "$@"
