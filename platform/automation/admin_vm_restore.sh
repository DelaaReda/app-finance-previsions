#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd -P)"
WORKSPACE_HELPER="${SCRIPT_DIR}/lib/workspace_paths.sh"
if [[ ! -f "$WORKSPACE_HELPER" ]]; then
  echo "Missing workspace helper: $WORKSPACE_HELPER" >&2
  exit 2
fi
# shellcheck source=/dev/null
source "$WORKSPACE_HELPER"
ROOT="$(fc_prefer_writable_workspace "$(fc_resolve_workspace_root "$SCRIPT_DIR")")"
OPENCLAW_ROOT="/home/venom/.openclaw"
SNAP_ROOT="${ADMIN_SNAPSHOT_ROOT:-${OPENCLAW_ROOT}/snapshots}"
SNAPSHOT=""
DRY_RUN=0
SKIP_ROLE_STATE=0
PREWARM_ROLE_SESSIONS=1

usage() {
  cat <<'EOF'
Usage: admin_vm_restore.sh [options]

Options:
  --snapshot <path>           Snapshot directory (default: ~/.openclaw/snapshots/vm-restart-latest)
  --dry-run                   Print actions without executing them
  --skip-role-state           Do not restore ~/.openclaw/cron/role-state files
  --no-prewarm-role-sessions  Do not prewarm codex_*_cron tmux sessions
  -h, --help                  Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --snapshot)
      SNAPSHOT="${2:?missing value for --snapshot}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --skip-role-state)
      SKIP_ROLE_STATE=1
      shift
      ;;
    --no-prewarm-role-sessions)
      PREWARM_ROLE_SESSIONS=0
      shift
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

if [[ -z "$SNAPSHOT" ]]; then
  if [[ -L "${SNAP_ROOT}/vm-restart-latest" || -d "${SNAP_ROOT}/vm-restart-latest" ]]; then
    SNAPSHOT="$(readlink -f "${SNAP_ROOT}/vm-restart-latest")"
  else
    SNAPSHOT="$(ls -1dt "${SNAP_ROOT}/vm-restart-"* 2>/dev/null | head -n 1 || true)"
  fi
fi

if [[ -z "$SNAPSHOT" || ! -d "$SNAPSHOT" ]]; then
  echo "Snapshot not found: ${SNAPSHOT:-<empty>}" >&2
  exit 3
fi

run_cmd() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '[dry-run]'
    for part in "$@"; do
      printf ' %q' "$part"
    done
    printf '\n'
    return 0
  fi
  "$@"
}

latest_file() {
  local pattern="$1"
  ls -1t ${pattern} 2>/dev/null | head -n 1 || true
}

pane_cmd() {
  local target="$1"
  tmux display-message -p -t "$target" "#{pane_current_command}" 2>/dev/null | tr '[:upper:]' '[:lower:]'
}

ensure_tmux_session() {
  local session="$1"
  local role_name="$2"
  local handoff_file="$3"
  local resume_packet="$4"
  local target="${session}:0.0"
  local cmd=""

  if ! tmux has-session -t "$session" 2>/dev/null; then
    run_cmd tmux new-session -d -s "$session" -c "$ROOT"
  fi
  run_cmd tmux set-option -t "$session" history-limit 200000

  cmd="$(pane_cmd "$target" || true)"
  if [[ ! "$cmd" =~ (codex|node) ]]; then
    run_cmd tmux send-keys -t "$target" C-c
    run_cmd tmux send-keys -t "$target" "cd $ROOT" C-m
    run_cmd tmux send-keys -t "$target" "codex --no-alt-screen" C-m
  fi

  run_cmd tmux send-keys -t "$target" "printf '[RESTORE] snapshot=${SNAPSHOT} role=${role_name}\\n'" C-m
  if [[ -f "$resume_packet" ]]; then
    run_cmd tmux send-keys -t "$target" "sed -n '1,200p' '$resume_packet'" C-m
  fi
  if [[ -n "$handoff_file" && -f "$handoff_file" ]]; then
    run_cmd tmux send-keys -t "$target" "sed -n '1,200p' '$handoff_file'" C-m
  fi
}

prewarm_role_session() {
  local session="$1"
  local target="${session}:0.0"
  local cmd=""
  if ! tmux has-session -t "$session" 2>/dev/null; then
    run_cmd tmux new-session -d -s "$session" -c "$ROOT"
  fi
  run_cmd tmux set-option -t "$session" history-limit 200000
  cmd="$(pane_cmd "$target" || true)"
  if [[ ! "$cmd" =~ (codex|node) ]]; then
    run_cmd tmux send-keys -t "$target" C-c
    run_cmd tmux send-keys -t "$target" "cd $ROOT" C-m
    run_cmd tmux send-keys -t "$target" "codex --no-alt-screen" C-m
  fi
  run_cmd tmux send-keys -t "$target" "echo '[PREWARM] restored after VM reboot from snapshot ${SNAPSHOT}'" C-m
}

if [[ "$DRY_RUN" -eq 0 ]]; then
  mkdir -p "${OPENCLAW_ROOT}/cron/role-state"
fi

if [[ "$SKIP_ROLE_STATE" -eq 0 && -d "${SNAPSHOT}/role-state" ]]; then
  run_cmd cp -a "${SNAPSHOT}/role-state/." "${OPENCLAW_ROOT}/cron/role-state/"
fi

service_active="$(systemctl --user is-active openclaw-gateway.service 2>/dev/null || true)"
if [[ "$service_active" != "active" ]]; then
  run_cmd systemctl --user restart openclaw-gateway.service
  run_cmd sleep 2
fi

run_cmd systemctl --user is-active openclaw-gateway.service
run_cmd openclaw status --deep
run_cmd openclaw cron list

if command -v tmux >/dev/null 2>&1; then
  resume_packet="${SNAPSHOT}/resume/ADMIN_RESUME_PACKET.md"
  adminapp_handoff="${ROOT}/docs/ops/TMUX_SESSION_HANDOFF_ADMINAPP_CODEX.md"
  admin_agents_handoff="$(latest_file "${ROOT}/docs/ops/TMUX_HANDOFF_admin-agents_*.md")"
  clawsentinel_handoff="$(latest_file "${ROOT}/docs/ops/TMUX_HANDOFF_clawsentinel_*.md")"

  ensure_tmux_session "adminapp_codex_sync" "adminapp-codex" "${adminapp_handoff}" "${resume_packet}"
  ensure_tmux_session "admin-agents-sync-cron" "admin-agents" "${admin_agents_handoff}" "${resume_packet}"
  ensure_tmux_session "clawsentinel" "clawsentinel" "${clawsentinel_handoff}" "${resume_packet}"

  if [[ "$PREWARM_ROLE_SESSIONS" -eq 1 ]]; then
    for session in \
      codex_planner_cron \
      codex_dev_cron \
      codex_tester_cron \
      codex_qa_cron \
      codex_architect_cron \
      codex_po_cron \
      codex_scrum_master_cron
    do
      prewarm_role_session "$session"
    done
  fi
fi

if [[ "$DRY_RUN" -eq 0 ]]; then
  bash "${ROOT}/scripts/adminapp_codex_cron_tick.sh" >/tmp/adminapp-restore-tick.log 2>&1 || true
  ADMIN_AGENTS_FALLBACK_SESSION="admin-agents-sync-cron" \
    bash "${ROOT}/scripts/admin_agents_tmux_tick.sh" >/tmp/admin-agents-restore-tick.log 2>&1 || true
fi

echo "RESTORE_OK"
echo "snapshot_dir=${SNAPSHOT}"
echo "role_state_restored=$((1-SKIP_ROLE_STATE))"
echo "gateway_status=$(systemctl --user is-active openclaw-gateway.service 2>/dev/null || echo unknown)"
echo "sessions_hint=tmux attach -t adminapp_codex_sync | tmux attach -t admin-agents-sync-cron | tmux attach -t clawsentinel"
