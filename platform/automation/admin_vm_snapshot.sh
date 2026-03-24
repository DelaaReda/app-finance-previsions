#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OPENCLAW_ROOT="/home/venom/.openclaw"
SNAP_ROOT="${ADMIN_SNAPSHOT_ROOT:-${OPENCLAW_ROOT}/snapshots}"
TS="$(date +%Y%m%d-%H%M%S-%Z)"
SNAP_NAME="vm-restart-${TS}"
NOTE="pre-vm-restart"
TMUX_CAPTURE_LINES="${TMUX_SNAPSHOT_LINES:-1800}"
RECENT_SESSION_FILES="${SNAPSHOT_RECENT_SESSION_FILES:-80}"
RECENT_CRON_LINES="${SNAPSHOT_RECENT_CRON_LINES:-2500}"

usage() {
  cat <<'EOF'
Usage: admin_vm_snapshot.sh [options]

Options:
  --name <snapshot-name>             Custom snapshot directory name (under ~/.openclaw/snapshots)
  --note <text>                      Note written in META.txt
  --tmux-capture-lines <n>           Lines captured per tmux pane (default: 1800)
  --recent-session-files <n>         Number of recent openclaw session jsonl files copied (default: 80)
  --recent-cron-lines <n>            Lines kept per cron run ledger file (default: 2500)
  -h, --help                         Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name)
      SNAP_NAME="${2:?missing value for --name}"
      shift 2
      ;;
    --note)
      NOTE="${2:?missing value for --note}"
      shift 2
      ;;
    --tmux-capture-lines)
      TMUX_CAPTURE_LINES="${2:?missing value for --tmux-capture-lines}"
      shift 2
      ;;
    --recent-session-files)
      RECENT_SESSION_FILES="${2:?missing value for --recent-session-files}"
      shift 2
      ;;
    --recent-cron-lines)
      RECENT_CRON_LINES="${2:?missing value for --recent-cron-lines}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if ! [[ "$TMUX_CAPTURE_LINES" =~ ^[0-9]+$ ]] || [[ "$TMUX_CAPTURE_LINES" -lt 200 ]]; then
  echo "Invalid --tmux-capture-lines: $TMUX_CAPTURE_LINES" >&2
  exit 2
fi
if ! [[ "$RECENT_SESSION_FILES" =~ ^[0-9]+$ ]] || [[ "$RECENT_SESSION_FILES" -lt 1 ]]; then
  echo "Invalid --recent-session-files: $RECENT_SESSION_FILES" >&2
  exit 2
fi
if ! [[ "$RECENT_CRON_LINES" =~ ^[0-9]+$ ]] || [[ "$RECENT_CRON_LINES" -lt 200 ]]; then
  echo "Invalid --recent-cron-lines: $RECENT_CRON_LINES" >&2
  exit 2
fi

SNAP_DIR="${SNAP_ROOT}/${SNAP_NAME}"
mkdir -p "${SNAP_DIR}"/{openclaw,cron,tmux,sessions,workspace,resume,role-state}

run_capture() {
  local out="$1"
  shift
  {
    printf '### command:'
    for part in "$@"; do
      printf ' %q' "$part"
    done
    printf '\n'
    "$@"
  } >"$out" 2>&1 || true
}

list_recent_files() {
  local dir="$1"
  local name_glob="$2"
  local limit="$3"
  find "$dir" -maxdepth 1 -type f -name "$name_glob" -printf '%T@ %p\n' 2>/dev/null \
    | sort -nr \
    | awk '{print $2}' \
    | sed -n "1,${limit}p"
}

copy_if_exists() {
  local src="$1"
  local dst="$2"
  if [[ -e "$src" ]]; then
    mkdir -p "$(dirname "$dst")"
    cp -a "$src" "$dst"
  fi
}

now_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
now_local="$(date '+%Y-%m-%d %H:%M:%S %Z')"
{
  echo "snapshot_name=${SNAP_NAME}"
  echo "snapshot_ts_utc=${now_utc}"
  echo "snapshot_ts_local=${now_local}"
  echo "workspace=${ROOT}"
  echo "openclaw_root=${OPENCLAW_ROOT}"
  echo "note=${NOTE}"
  echo "hostname=$(hostname)"
} > "${SNAP_DIR}/META.txt"

run_capture "${SNAP_DIR}/openclaw-status.txt" openclaw status
run_capture "${SNAP_DIR}/openclaw-status-deep.txt" openclaw status --deep
run_capture "${SNAP_DIR}/openclaw-doctor.txt" openclaw doctor
run_capture "${SNAP_DIR}/openclaw-agents-list.txt" openclaw agents list
run_capture "${SNAP_DIR}/gateway-service-status.txt" systemctl --user status openclaw-gateway.service --no-pager -n 120
run_capture "${SNAP_DIR}/app-status.txt" bash -lc "cd '${ROOT}' && git status --short --branch"

{
  echo "model=$(openclaw config get agents.defaults.model.primary 2>/dev/null || echo unknown)"
  echo "thinking=$(openclaw config get agents.defaults.thinkingDefault 2>/dev/null || echo unknown)"
} > "${SNAP_DIR}/openclaw-config-keys.txt"

copy_if_exists "${OPENCLAW_ROOT}/openclaw.json" "${SNAP_DIR}/openclaw/openclaw.json"
copy_if_exists "${OPENCLAW_ROOT}/cron/jobs.json" "${SNAP_DIR}/cron/jobs.json"
copy_if_exists "${OPENCLAW_ROOT}/agents/main/sessions/sessions.json" "${SNAP_DIR}/sessions/sessions.json"

if command -v openclaw >/dev/null 2>&1; then
  if openclaw cron list --json > "${SNAP_DIR}/cron/cron-list.json" 2>/dev/null; then
    if command -v jq >/dev/null 2>&1; then
      jq -r '.jobs[]? | [.id,.name,.state.lastStatus] | @tsv' "${SNAP_DIR}/cron/cron-list.json" > "${SNAP_DIR}/cron/cron-index.tsv" || true
      while IFS=$'\t' read -r job_id job_name _status; do
        [[ -n "${job_id}" ]] || continue
        safe_name="$(printf '%s' "${job_name:-job}" | tr ' /:' '___')"
        openclaw cron runs --id "${job_id}" --limit 20 > "${SNAP_DIR}/cron/runs-${safe_name}-${job_id}.json" 2>&1 || true
      done < "${SNAP_DIR}/cron/cron-index.tsv"
    fi
  else
    run_capture "${SNAP_DIR}/cron/cron-list.txt" openclaw cron list
  fi
fi

if [[ -d "${OPENCLAW_ROOT}/cron/runs" ]]; then
  mkdir -p "${SNAP_DIR}/cron/runs-ledger"
  while IFS= read -r run_file; do
    base="$(basename "$run_file")"
    tail -n "${RECENT_CRON_LINES}" "$run_file" > "${SNAP_DIR}/cron/runs-ledger/${base}" || true
  done < <(find "${OPENCLAW_ROOT}/cron/runs" -maxdepth 1 -type f -name '*.jsonl' | sort)
fi

if [[ -d "${OPENCLAW_ROOT}/cron/role-state" ]]; then
  cp -a "${OPENCLAW_ROOT}/cron/role-state/." "${SNAP_DIR}/role-state/" || true
fi
find "${SNAP_DIR}/role-state" -maxdepth 1 -type f -printf '%f\n' 2>/dev/null | sort > "${SNAP_DIR}/role-state/INDEX.txt" || true

if command -v tmux >/dev/null 2>&1 && tmux ls >/dev/null 2>&1; then
  {
    echo "### tmux ls"
    tmux ls || true
    echo
    echo "### tmux panes"
    tmux list-panes -a -F '#S:#I.#P cmd=#{pane_current_command} pid=#{pane_pid} title=#{pane_title}' || true
  } > "${SNAP_DIR}/tmux-inventory.txt"

  tmux list-panes -a -F '#S:#I.#P' > "${SNAP_DIR}/tmux/panes.list" || true
  while IFS= read -r pane; do
    [[ -n "$pane" ]] || continue
    pane_safe="$(printf '%s' "$pane" | tr ':.' '__')"
    tmux capture-pane -p -J -S "-${TMUX_CAPTURE_LINES}" -E -1 -t "$pane" > "${SNAP_DIR}/tmux/${pane_safe}.scrollback.txt" 2>/dev/null || true
  done < "${SNAP_DIR}/tmux/panes.list"
else
  echo "tmux_not_available_or_no_server" > "${SNAP_DIR}/tmux-inventory.txt"
fi

if [[ -d "${OPENCLAW_ROOT}/agents/main/sessions" ]]; then
  mkdir -p "${SNAP_DIR}/sessions/recent-jsonl"
  while IFS= read -r session_file; do
    [[ -n "$session_file" ]] || continue
    cp -a "$session_file" "${SNAP_DIR}/sessions/recent-jsonl/" || true
  done < <(list_recent_files "${OPENCLAW_ROOT}/agents/main/sessions" '*.jsonl' "${RECENT_SESSION_FILES}")
  ls -1 "${OPENCLAW_ROOT}/agents/main/sessions/"*.lock 2>/dev/null > "${SNAP_DIR}/sessions/active-locks.list" || true
fi

copy_if_exists "${ROOT}/SOUL.md" "${SNAP_DIR}/workspace/SOUL.md"
copy_if_exists "${ROOT}/USER.md" "${SNAP_DIR}/workspace/USER.md"
copy_if_exists "${ROOT}/MEMORY.md" "${SNAP_DIR}/workspace/MEMORY.md"
copy_if_exists "${ROOT}/docs/ops/ADMIN_TEAM_CHAT.md" "${SNAP_DIR}/workspace/ADMIN_TEAM_CHAT.md"
copy_if_exists "${ROOT}/docs/ops/ADMIN_TEAM_ITERATIONS.md" "${SNAP_DIR}/workspace/ADMIN_TEAM_ITERATIONS.md"
copy_if_exists "${ROOT}/logs-codex-runs/orchestrator-state/agent-watchdog.md" "${SNAP_DIR}/workspace/agent-watchdog.md"
if [[ ! -f "${SNAP_DIR}/workspace/agent-watchdog.md" ]]; then
  copy_if_exists "${ROOT}/docs/operations/orchestrator/agent-watchdog.md" "${SNAP_DIR}/workspace/agent-watchdog.md"
fi
copy_if_exists "${ROOT}/docs/ops/TMUX_SESSION_HANDOFF_ADMINAPP_CODEX.md" "${SNAP_DIR}/workspace/TMUX_SESSION_HANDOFF_ADMINAPP_CODEX.md"

latest_admin_agents_handoff="$(list_recent_files "${ROOT}/docs/ops" 'TMUX_HANDOFF_admin-agents_*.md' 1 || true)"
if [[ -n "${latest_admin_agents_handoff}" ]]; then
  cp -a "${latest_admin_agents_handoff}" "${SNAP_DIR}/workspace/" || true
fi
latest_clawsentinel_handoff="$(list_recent_files "${ROOT}/docs/ops" 'TMUX_HANDOFF_clawsentinel_*.md' 1 || true)"
if [[ -n "${latest_clawsentinel_handoff}" ]]; then
  cp -a "${latest_clawsentinel_handoff}" "${SNAP_DIR}/workspace/" || true
fi

today_memory="${ROOT}/memory/$(date +%F).md"
yesterday_memory="${ROOT}/memory/$(date -d 'yesterday' +%F).md"
copy_if_exists "${today_memory}" "${SNAP_DIR}/workspace/"
copy_if_exists "${yesterday_memory}" "${SNAP_DIR}/workspace/"

{
  echo "# Admin Resume Packet"
  echo
  echo "- snapshot: ${SNAP_DIR}"
  echo "- generated_utc: ${now_utc}"
  echo "- generated_local: ${now_local}"
  echo "- note: ${NOTE}"
  echo
  echo "## Restart Checklist"
  echo "1. Boot VM."
  echo "2. Run: bash scripts/admin_vm_restore.sh --snapshot '${SNAP_DIR}'"
  echo "3. Verify: openclaw status --deep ; openclaw cron list ; tmux ls"
  echo
  echo "## Preserved Assets"
  echo "- openclaw status/doctor/config snapshots"
  echo "- cron list + per-job recent runs + jobs.json"
  echo "- role-state files from ~/.openclaw/cron/role-state"
  echo "- tmux pane scrollback captures"
  echo "- recent openclaw session jsonl files + sessions.json"
  echo "- admin continuity docs (chat/iterations/watchdog/handoffs)"
  echo
  echo "## Key Files To Reopen"
  echo "- docs/ops/ADMIN_TEAM_CHAT.md"
  echo "- docs/ops/ADMIN_TEAM_ITERATIONS.md"
  echo "- docs/operations/orchestrator/agent-watchdog.md"
  echo "- memory/$(date +%F).md"
} > "${SNAP_DIR}/resume/ADMIN_RESUME_PACKET.md"

ln -sfn "${SNAP_DIR}" "${SNAP_ROOT}/vm-restart-latest"

echo "SNAPSHOT_OK"
echo "snapshot_dir=${SNAP_DIR}"
echo "resume_packet=${SNAP_DIR}/resume/ADMIN_RESUME_PACKET.md"
echo "latest_link=${SNAP_ROOT}/vm-restart-latest"
echo "restore_cmd=bash scripts/admin_vm_restore.sh --snapshot '${SNAP_DIR}'"
