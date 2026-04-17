#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

AWS_SYNC_HOST="${AWS_SYNC_HOST:-3.98.20.77}"
AWS_SYNC_USER="${AWS_SYNC_USER:-ubuntu}"
AWS_SYNC_KEY="${AWS_SYNC_KEY:-$HOME/.ssh/id_aws_lightsail}"
AWS_SYNC_DEST="${AWS_SYNC_DEST:-/home/${AWS_SYNC_USER}/analyse-financiere}"
MODE="${1:-sync}"
POLL_SECONDS="${AWS_SYNC_POLL_SECONDS:-5}"
AUTO_RESTART="${AWS_SYNC_AUTO_RESTART:-1}"
PUBLIC_BASE_URL="${AWS_PUBLIC_BASE_URL:-http://${AWS_SYNC_HOST}}"
MONITOR_BASE_URL="${AWS_MONITOR_BASE_URL:-http://${AWS_SYNC_HOST}:8080}"

SYNC_ITEMS=(
  "apps/api"
  "apps/web"
  "apps/monitor"
  "packages"
  "platform"
  "finance-copilot.sh"
  "scripts/monitor_stack_guard.sh"
  "scripts/critical_endpoints_smoke.sh"
  "scripts/fc_health_check.sh"
)

RSYNC_EXCLUDES=(
  ".git/"
  ".DS_Store"
  "._*"
  "**/__pycache__/"
  "**/.pytest_cache/"
  "**/.mypy_cache/"
  "**/.venv/"
  "**/node_modules/"
  "*.pyc"
  "*.pyo"
  "*.sqlite"
  "*.sqlite3"
  "*.db"
  "logs-codex-runs/"
  "memory/"
  "docs/operations/orchestrator/"
  "docs/ops/AGENT_MESSAGE_BUS.jsonl"
  "apps/api/runtime/api.log"
  "apps/api/runtime/*.pid"
  "apps/api/runtime/data/"
  "apps/api/runtime/cache/"
)

usage() {
  cat <<EOF
Usage:
  $(basename "$0") [sync|watch|restart]

Notes:
  Mac <-> UTM VM share the same workspace view. This is local workspace sharing only.
  Publication to AWS is a separate shared-workspace -> AWS step.
  Canonical operator path is Mac-side publication. If explicitly launched from the UTM VM, the same wrapper still publishes the shared workspace snapshot, not VM-local orchestration state.

Modes:
  sync     Push code/support files to AWS, then restart the app stack
  watch    Poll local files and re-run sync whenever something changes
  restart  Remote restart only, without syncing files

Environment overrides:
  AWS_SYNC_HOST        Remote EC2 host/IP (default: ${AWS_SYNC_HOST})
  AWS_SYNC_USER        SSH user (default: ${AWS_SYNC_USER})
  AWS_SYNC_KEY         SSH private key path (default: ${AWS_SYNC_KEY})
  AWS_SYNC_DEST        Remote workspace path (default: ${AWS_SYNC_DEST})
  AWS_SYNC_POLL_SECONDS  Poll interval for watch mode (default: ${POLL_SECONDS})
  AWS_SYNC_AUTO_RESTART  1 to restart after sync, 0 to sync only (default: ${AUTO_RESTART})
  AWS_PUBLIC_BASE_URL    Public app base URL (default: ${PUBLIC_BASE_URL})
  AWS_MONITOR_BASE_URL   Public monitor base URL (default: ${MONITOR_BASE_URL})
EOF
}

if [[ "${MODE}" == "-h" || "${MODE}" == "--help" || "${MODE}" == "help" ]]; then
  usage
  exit 0
fi

if [[ ! -f "${AWS_SYNC_KEY}" ]]; then
  echo "SSH key not found: ${AWS_SYNC_KEY}" >&2
  exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo "rsync is required but not installed." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but not installed." >&2
  exit 1
fi

SSH_CMD=(
  ssh
  -i "${AWS_SYNC_KEY}"
  -o StrictHostKeyChecking=accept-new
  -o ServerAliveInterval=30
  -o ServerAliveCountMax=3
)

remote_cmd() {
  "${SSH_CMD[@]}" "${AWS_SYNC_USER}@${AWS_SYNC_HOST}" "$@"
}

remote_prepare() {
  remote_cmd "cd '${AWS_SYNC_DEST}' && \
    if [ ! -x apps/api/src/.venv/bin/python3 ]; then \
      bash apps/api/runtime/bootstrap_backend_env.sh; \
    fi && \
    mkdir -p /home/${AWS_SYNC_USER}/.openclaw/cron/role-state && \
    sudo mkdir -p /home/venom/.openclaw/cron/role-state && \
    rm -rf apps/monitor/.venv && \
    ln -s ../api/src/.venv apps/monitor/.venv"
}

remote_restart() {
  remote_prepare
  remote_cmd "cd '${AWS_SYNC_DEST}' && ./finance-copilot.sh restart"
}

verify_remote() {
  # These localhost probes run on the remote EC2 host itself. They validate the
  # host-local app stack after publication; they are not VM-local orchestration checks.
  remote_cmd "curl -fsS http://127.0.0.1:8050/api/health >/dev/null \
    && curl -fsS http://127.0.0.1:5173/ >/dev/null \
    && curl -fsS http://127.0.0.1:7779/api/status?lite=1 >/dev/null"
}

verify_public() {
  curl -fsS "${PUBLIC_BASE_URL%/}/api/health" >/dev/null
  curl -fsS "${PUBLIC_BASE_URL%/}/" >/dev/null
  curl -fsS "${MONITOR_BASE_URL%/}/api/status?lite=1" >/dev/null
}

retry() {
  local attempts="${1:-10}"
  shift
  local delay="${1:-2}"
  shift
  local i=1
  while true; do
    if "$@"; then
      return 0
    fi
    if [[ "${i}" -ge "${attempts}" ]]; then
      return 1
    fi
    sleep "${delay}"
    i=$((i + 1))
  done
}

run_rsync() {
  local rsync_cmd=(
    rsync
    -az
    --human-readable
    --delete
    --partial
    -e "$(printf '%q ' "${SSH_CMD[@]}")"
  )

  local exclude
  for exclude in "${RSYNC_EXCLUDES[@]}"; do
    rsync_cmd+=("--exclude=${exclude}")
  done

  remote_cmd "mkdir -p '${AWS_SYNC_DEST}'"

  local sources=()
  local item
  for item in "${SYNC_ITEMS[@]}"; do
    if [[ -e "${WORKSPACE_ROOT}/${item}" ]]; then
      sources+=("./${item}")
    fi
  done

  (
    cd "${WORKSPACE_ROOT}"
    "${rsync_cmd[@]}" --relative "${sources[@]}" "${AWS_SYNC_USER}@${AWS_SYNC_HOST}:${AWS_SYNC_DEST}/"
  )
}

compute_stamp() {
  python3 - "${WORKSPACE_ROOT}" "${SYNC_ITEMS[@]}" <<'PY'
import hashlib
import os
import sys
from pathlib import Path

root = Path(sys.argv[1])
items = [root / p for p in sys.argv[2:]]

skip_dir_names = {'.git', '__pycache__', '.pytest_cache', '.mypy_cache', 'node_modules', '.venv'}
skip_prefixes = [
    str(root / 'logs-codex-runs'),
    str(root / 'memory'),
    str(root / 'docs/operations/orchestrator'),
]
skip_suffixes = ('.pyc', '.pyo', '.sqlite', '.sqlite3', '.db')
skip_exact = {
    str(root / 'apps/api/runtime/api.log'),
    str(root / 'docs/ops/AGENT_MESSAGE_BUS.jsonl'),
}
skip_contains = (
    '/apps/api/runtime/data/',
    '/apps/api/runtime/cache/',
)

h = hashlib.sha256()

def should_skip(path: Path) -> bool:
    s = str(path)
    if s in skip_exact:
        return True
    if any(s.startswith(prefix) for prefix in skip_prefixes):
        return True
    if any(marker in s for marker in skip_contains):
        return True
    if path.name in skip_dir_names:
        return True
    if path.suffix in skip_suffixes:
        return True
    return False

for item in items:
    if not item.exists():
        continue
    if item.is_file():
        st = item.stat()
        h.update(f"{item.relative_to(root)}:{st.st_size}:{int(st.st_mtime)}".encode())
        continue
    for dirpath, dirnames, filenames in os.walk(item):
        dirnames[:] = [d for d in dirnames if d not in skip_dir_names]
        base = Path(dirpath)
        if should_skip(base):
            dirnames[:] = []
            continue
        for name in sorted(filenames):
            p = base / name
            if should_skip(p):
                continue
            st = p.stat()
            h.update(f"{p.relative_to(root)}:{st.st_size}:{int(st.st_mtime)}".encode())

print(h.hexdigest())
PY
}

sync_once() {
  echo "Syncing app workspace to ${AWS_SYNC_USER}@${AWS_SYNC_HOST}:${AWS_SYNC_DEST}"
  run_rsync
  if [[ "${AUTO_RESTART}" == "1" ]]; then
    echo "Restarting remote Finance Copilot stack"
    remote_restart
  fi
  echo "Verifying remote localhost endpoints"
  retry 12 2 verify_remote
  echo "Verifying public URLs"
  retry 12 2 verify_public
  echo "Sync complete"
}

watch_loop() {
  local last_stamp=""
  while true; do
    local current_stamp
    current_stamp="$(compute_stamp)"
    if [[ "${current_stamp}" != "${last_stamp}" ]]; then
      sync_once
      last_stamp="${current_stamp}"
    fi
    sleep "${POLL_SECONDS}"
  done
}

case "${MODE}" in
  sync)
    sync_once
    ;;
  watch)
    watch_loop
    ;;
  restart)
    remote_restart
    verify_remote
    verify_public
    ;;
  *)
    echo "Unknown mode: ${MODE}" >&2
    usage >&2
    exit 1
    ;;
esac
