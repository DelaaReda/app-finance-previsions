#!/usr/bin/env bash
set -euo pipefail

AWS_APP_HOST="${AWS_APP_HOST:-3.98.20.77}"
AWS_APP_USER="${AWS_APP_USER:-ubuntu}"
AWS_APP_DIR="${AWS_APP_DIR:-/home/${AWS_APP_USER}/analyse-financiere}"
AWS_APP_PUBLIC_BASE_URL="${AWS_APP_PUBLIC_BASE_URL:-http://${AWS_APP_HOST}}"
AWS_APP_MONITOR_BASE_URL="${AWS_APP_MONITOR_BASE_URL:-http://${AWS_APP_HOST}:8080}"
AWS_EC2_INSTANCE_ID="${AWS_EC2_INSTANCE_ID:-i-0f5f483b8e25d26e0}"
AWS_EC2_REGION="${AWS_EC2_REGION:-ca-central-1}"
AWS_EC2_PROFILE="${AWS_EC2_PROFILE:-reda}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PROBE_SCRIPT="${AWS_PUBLIC_RUNTIME_PROBE_SCRIPT:-${SCRIPT_DIR}/aws_public_runtime_probe.py}"
ENSURE_UP_WOKE_INSTANCE=0

resolve_key() {
  if [[ -n "${AWS_APP_SSH_KEY:-}" && -f "${AWS_APP_SSH_KEY}" ]]; then
    printf '%s\n' "${AWS_APP_SSH_KEY}"
    return 0
  fi

  local candidates=(
    "$HOME/.ssh/id_aws_lightsail"
    "/home/venom/.ssh/id_aws_lightsail"
    "/Users/venom/.ssh/id_aws_lightsail"
  )
  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -f "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  return 1
}

usage() {
  cat <<EOF
Usage:
  $(basename "$0") <status|remote-status|start|stop|restart|public-status|raw-public-status|instance-status|start-instance>

Defaults:
  host         ${AWS_APP_HOST}
  user         ${AWS_APP_USER}
  app dir      ${AWS_APP_DIR}
  public app   ${AWS_APP_PUBLIC_BASE_URL}
  public monitor ${AWS_APP_MONITOR_BASE_URL}

Env overrides:
  AWS_APP_HOST
  AWS_APP_USER
  AWS_APP_DIR
  AWS_APP_SSH_KEY
  AWS_APP_PUBLIC_BASE_URL
  AWS_APP_MONITOR_BASE_URL
  AWS_EC2_INSTANCE_ID
  AWS_EC2_REGION
  AWS_EC2_PROFILE
EOF
}

KEY_PATH="$(resolve_key || true)"
if [[ -z "${KEY_PATH}" ]]; then
  echo "AWS SSH key not found. Set AWS_APP_SSH_KEY or install id_aws_lightsail on this machine." >&2
  exit 1
fi

SSH_CMD=(
  ssh
  -i "${KEY_PATH}"
  -o StrictHostKeyChecking=accept-new
  -o ServerAliveInterval=30
  -o ServerAliveCountMax=3
  "${AWS_APP_USER}@${AWS_APP_HOST}"
)

json_field() {
  local field="$1"
  local payload
  payload="$(cat)"
  python3 - "$field" "$payload" <<'PY'
import json
import sys

field = sys.argv[1]
payload = json.loads(sys.argv[2])
value = payload.get(field)
if isinstance(value, (dict, list)):
    print(json.dumps(value, separators=(",", ":"), sort_keys=True))
elif value is None:
    print("")
else:
    print(value)
PY
}

probe_public_url() {
  python3 "${PROBE_SCRIPT}" --url "$1"
}

print_maintenance_status() {
  local app_probe_json="$1"
  local monitor_probe_json="$2"
  python3 - "$app_probe_json" "$monitor_probe_json" <<'PY'
import json
import sys

app_probe = json.loads(sys.argv[1])
monitor_probe = json.loads(sys.argv[2])
maintenance = app_probe if app_probe.get("maintenance_active") else monitor_probe
command = str(maintenance.get("maintenance_command") or "restart").strip() or "restart"
age = maintenance.get("maintenance_age_s")
message = "EC2 publication/restart in progress; treat brief 502/monitor gaps as transient."
if isinstance(age, int):
    message += f" age_s={age}"

app_payload = {
    "ok": False,
    "status": "maintenance",
    "data": {
        "status": "maintenance",
        "backend_up": False,
        "reason": "runtime_restart_in_progress",
        "command": command,
        "age_s": age,
        "message": message,
    },
}
monitor_payload = {
    "health": "MAINTENANCE",
    "primary_status": "maintenance",
    "delivery_control": {
        "phase": "verifying_public_proof",
        "maintenance_active": True,
        "maintenance_reason": "runtime_restart_in_progress",
        "maintenance_command": command,
        "maintenance_age_s": age,
        "ec2_reachable": True,
    },
    "note": message,
}
print(json.dumps(app_payload, separators=(",", ":"), sort_keys=True))
print("---")
print(json.dumps(monitor_payload, separators=(",", ":"), sort_keys=True))
PY
}

remote_exec() {
  "${SSH_CMD[@]}" "$@"
}

aws_cmd() {
  if ! command -v aws >/dev/null 2>&1; then
    echo "aws CLI unavailable on this machine" >&2
    exit 1
  fi

  AWS_PROFILE="${AWS_EC2_PROFILE}" aws "$@"
}

instance_state() {
  aws_cmd ec2 describe-instances \
    --region "${AWS_EC2_REGION}" \
    --instance-ids "${AWS_EC2_INSTANCE_ID}" \
    --query 'Reservations[0].Instances[0].State.Name' \
    --output text
}

wait_for_ssh() {
  local max_attempts="${1:-60}"
  local attempt
  for ((attempt=1; attempt<=max_attempts; attempt+=1)); do
    if remote_exec "true" >/dev/null 2>&1; then
      return 0
    fi
    sleep 5
  done

  echo "SSH did not become reachable on ${AWS_APP_HOST}" >&2
  return 1
}

ensure_up() {
  local state
  state="$(instance_state)"
  case "${state}" in
    running)
      ENSURE_UP_WOKE_INSTANCE=0
      return 0
      ;;
    pending|stopping)
      ENSURE_UP_WOKE_INSTANCE=1
      aws_cmd ec2 wait instance-running \
        --region "${AWS_EC2_REGION}" \
        --instance-ids "${AWS_EC2_INSTANCE_ID}"
      wait_for_ssh
      ;;
    stopped|stopped*)
      ENSURE_UP_WOKE_INSTANCE=1
      aws_cmd ec2 start-instances \
        --region "${AWS_EC2_REGION}" \
        --instance-ids "${AWS_EC2_INSTANCE_ID}" >/dev/null
      aws_cmd ec2 wait instance-running \
        --region "${AWS_EC2_REGION}" \
        --instance-ids "${AWS_EC2_INSTANCE_ID}"
      wait_for_ssh
      ;;
    shutting-down|terminated)
      echo "Instance ${AWS_EC2_INSTANCE_ID} is ${state}" >&2
      exit 1
      ;;
    *)
      echo "Unknown instance state: ${state}" >&2
      exit 1
      ;;
  esac
}

ensure_app_runtime() {
  local app_url="${AWS_APP_PUBLIC_BASE_URL%/}/api/health"
  local app_probe app_state

  app_probe="$(probe_public_url "${app_url}")"
  app_state="$(json_field effective_state <<<"${app_probe}")"

  if [[ "${app_state}" == "ok" || "${app_state}" == "maintenance" ]]; then
    return 0
  fi

  remote_exec "cd '${AWS_APP_DIR}' && ./finance-copilot.sh start"
}

public_status() {
  local app_url="${AWS_APP_PUBLIC_BASE_URL%/}/api/health"
  local monitor_url="${AWS_APP_MONITOR_BASE_URL%/}/api/status?lite=1"
  local app_probe monitor_probe app_state monitor_state
  app_probe="$(probe_public_url "${app_url}")"
  monitor_probe="$(probe_public_url "${monitor_url}")"
  app_state="$(json_field effective_state <<<"${app_probe}")"
  monitor_state="$(json_field effective_state <<<"${monitor_probe}")"
  if [[ "${app_state}" == "ok" && "${monitor_state}" == "ok" ]]; then
    curl -fsS "${app_url}"
    echo
    echo "---"
    curl -fsS "${monitor_url}"
    return 0
  fi
  if [[ "${app_state}" == "maintenance" || "${monitor_state}" == "maintenance" ]]; then
    print_maintenance_status "${app_probe}" "${monitor_probe}"
    return 0
  fi
  curl -fsS "${app_url}"
  echo
  echo "---"
  curl -fsS "${monitor_url}"
}

case "${1:-}" in
  status)
    ensure_up
    ensure_app_runtime
    public_status
    ;;
  remote-status)
    ensure_up
    remote_exec "cd '${AWS_APP_DIR}' && ./finance-copilot.sh status"
    ;;
  start)
    ensure_up
    remote_exec "cd '${AWS_APP_DIR}' && ./finance-copilot.sh start"
    ;;
  stop)
    ensure_up
    remote_exec "cd '${AWS_APP_DIR}' && ./finance-copilot.sh stop"
    ;;
  restart)
    ensure_up
    remote_exec "cd '${AWS_APP_DIR}' && ./finance-copilot.sh restart"
    ;;
  public-status)
    ensure_up
    ensure_app_runtime
    public_status
    ;;
  raw-public-status)
    public_status
    ;;
  instance-status)
    instance_state
    ;;
  start-instance)
    ensure_up
    ;;
  -h|--help|help|"")
    usage
    ;;
  *)
    echo "Unknown command: ${1}" >&2
    usage >&2
    exit 1
    ;;
esac
