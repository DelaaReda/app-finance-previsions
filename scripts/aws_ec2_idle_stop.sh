#!/usr/bin/env bash
set -euo pipefail

IDLE_MINUTES="${IDLE_MINUTES:-10}"
IDLE_STOP_MODE="${AWS_EC2_IDLE_STOP_MODE:-reachability_watchdog}"
ACCESS_LOG="${ACCESS_LOG:-/var/log/nginx/access.log}"
LOCK_META="${LOCK_META:-/home/ubuntu/analyse-financiere/logs-codex-runs/finance-copilot-runtime.lock.meta}"
PUBLIC_APP_BASE_URL="${FC_PUBLIC_APP_BASE_URL:-http://3.98.20.77}"
REACHABILITY_URL="${REACHABILITY_URL:-${PUBLIC_APP_BASE_URL%/}/api/health}"

log() {
  logger -t finance-copilot-idle-stop "$*"
}

imds_token() {
  curl -fsS -X PUT "http://169.254.169.254/latest/api/token" \
    -H "X-aws-ec2-metadata-token-ttl-seconds: 21600"
}

imds_get() {
  local token="$1"
  local path="$2"
  curl -fsS -H "X-aws-ec2-metadata-token: ${token}" "http://169.254.169.254/latest/${path}"
}

last_access_epoch() {
  if [[ -f "${ACCESS_LOG}" ]]; then
    stat -c %Y "${ACCESS_LOG}" 2>/dev/null || echo 0
    return 0
  fi
  echo 0
}

reachability_watchdog() {
  if curl -fsS --max-time 5 "${REACHABILITY_URL}" >/dev/null; then
    log "watchdog: public app reachable (${REACHABILITY_URL})"
  else
    log "watchdog: public app probe failed (${REACHABILITY_URL})"
  fi
}

legacy_http_idle_stop() {
  if ! [[ "${IDLE_MINUTES}" =~ ^[0-9]+$ ]] || [[ "${IDLE_MINUTES}" -lt 1 ]]; then
    echo "Invalid IDLE_MINUTES: ${IDLE_MINUTES}" >&2
    exit 2
  fi

  if [[ -f "${LOCK_META}" ]]; then
    log "skip: runtime lock active (${LOCK_META})"
    exit 0
  fi

  local now idle_seconds last_access age_seconds
  now="$(date +%s)"
  idle_seconds="$((IDLE_MINUTES * 60))"
  last_access="$(last_access_epoch)"

  if [[ "${last_access}" -le 0 ]]; then
    age_seconds="${idle_seconds}"
  else
    age_seconds="$((now - last_access))"
  fi

  if [[ "${age_seconds}" -lt "${idle_seconds}" ]]; then
    log "skip: recent HTTP activity (${age_seconds}s < ${idle_seconds}s)"
    exit 0
  fi

  if ! command -v aws >/dev/null 2>&1; then
    log "skip: aws CLI unavailable for opt-in legacy stop mode"
    exit 0
  fi

  local token instance_id region
  token="$(imds_token)"
  instance_id="$(imds_get "${token}" "meta-data/instance-id")"
  region="$(imds_get "${token}" "dynamic/instance-identity/document" | python3 -c 'import sys,json; print(json.load(sys.stdin)["region"])')"

  log "stopping instance ${instance_id} in ${region} after ${age_seconds}s idle (legacy opt-in mode)"
  aws ec2 stop-instances --region "${region}" --instance-ids "${instance_id}" >/dev/null
}

main() {
  case "${IDLE_STOP_MODE}" in
    disabled)
      log "skip: idle stop disabled (mode=${IDLE_STOP_MODE})"
      ;;
    reachability_watchdog)
      reachability_watchdog
      ;;
    http_idle_opt_in)
      legacy_http_idle_stop
      ;;
    *)
      log "skip: unknown mode=${IDLE_STOP_MODE}; using reachability watchdog semantics"
      reachability_watchdog
      ;;
  esac
}

main "$@"
