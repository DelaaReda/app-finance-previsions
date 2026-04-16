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
  $(basename "$0") <status|remote-status|start|stop|restart|public-status|instance-status|start-instance>

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
      return 0
      ;;
    pending|stopping)
      aws_cmd ec2 wait instance-running \
        --region "${AWS_EC2_REGION}" \
        --instance-ids "${AWS_EC2_INSTANCE_ID}"
      wait_for_ssh
      ;;
    stopped|stopped*)
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

public_status() {
  curl -fsS "${AWS_APP_PUBLIC_BASE_URL%/}/api/health"
  echo
  echo "---"
  curl -fsS "${AWS_APP_MONITOR_BASE_URL%/}/api/status?lite=1"
}

case "${1:-}" in
  status)
    ensure_up
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
