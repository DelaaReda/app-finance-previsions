#!/usr/bin/env bash
set -euo pipefail

AWS_APP_HOST="${AWS_APP_HOST:-3.98.20.77}"
AWS_APP_USER="${AWS_APP_USER:-ubuntu}"
AWS_APP_SSH_KEY="${AWS_APP_SSH_KEY:-/Users/venom/.ssh/id_aws_lightsail}"
LOCAL_SCRIPT="${LOCAL_SCRIPT:-/Users/venom/Documents/analyse-financiere/scripts/aws_ec2_idle_stop.sh}"
REMOTE_SCRIPT="${REMOTE_SCRIPT:-/usr/local/bin/finance-copilot-idle-stop}"
IDLE_MINUTES="${IDLE_MINUTES:-10}"
IDLE_STOP_MODE="${AWS_EC2_IDLE_STOP_MODE:-reachability_watchdog}"
PUBLIC_APP_BASE_URL="${FC_PUBLIC_APP_BASE_URL:-http://3.98.20.77}"

SSH_CMD=(
  ssh
  -i "${AWS_APP_SSH_KEY}"
  -o StrictHostKeyChecking=accept-new
  "${AWS_APP_USER}@${AWS_APP_HOST}"
)

SCP_CMD=(
  scp
  -i "${AWS_APP_SSH_KEY}"
  -o StrictHostKeyChecking=accept-new
)

remote_exec() {
  "${SSH_CMD[@]}" "$@"
}

main() {
  if [[ ! -f "${LOCAL_SCRIPT}" ]]; then
    echo "Missing local script: ${LOCAL_SCRIPT}" >&2
    exit 1
  fi

  "${SCP_CMD[@]}" "${LOCAL_SCRIPT}" "${AWS_APP_USER}@${AWS_APP_HOST}:/tmp/finance-copilot-idle-stop"

  remote_exec "sudo install -m 0755 /tmp/finance-copilot-idle-stop '${REMOTE_SCRIPT}'"
  remote_exec "rm -f /tmp/finance-copilot-idle-stop"
  remote_exec "cat <<'EOF' | sudo tee /etc/systemd/system/finance-copilot-idle-stop.service >/dev/null
[Unit]
Description=Finance Copilot EC2 delivery watchdog
After=network-online.target nginx.service
Wants=network-online.target

[Service]
Type=oneshot
Environment=IDLE_MINUTES=${IDLE_MINUTES}
Environment=AWS_EC2_IDLE_STOP_MODE=${IDLE_STOP_MODE}
Environment=FC_PUBLIC_APP_BASE_URL=${PUBLIC_APP_BASE_URL}
ExecStart=${REMOTE_SCRIPT}
EOF"

  remote_exec "cat <<'EOF' | sudo tee /etc/systemd/system/finance-copilot-idle-stop.timer >/dev/null
[Unit]
Description=Run Finance Copilot delivery watchdog every 2 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=2min
Unit=finance-copilot-idle-stop.service

[Install]
WantedBy=timers.target
EOF"

  remote_exec "sudo systemctl daemon-reload && sudo systemctl enable --now finance-copilot-idle-stop.timer && sudo systemctl restart finance-copilot-idle-stop.timer"
  remote_exec "systemctl --no-pager --full status finance-copilot-idle-stop.timer"
}

main "$@"
