#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="${VM_RESUME_GUARD_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
cd "$ROOT"

STATE_DIR="${VM_RESUME_GUARD_STATE_DIR:-$HOME/.openclaw/state/vm_resume_guard}"
mkdir -p "$STATE_DIR"

LAST_EPOCH_FILE="$STATE_DIR/last_epoch.txt"
GAP_SECONDS="${VM_RESUME_GUARD_GAP_SECONDS:-420}"  # 7 minutes
FORCE="${VM_RESUME_GUARD_FORCE:-0}"

# After resume, we can "kick" a few key admin/infra crons to reduce long stalls.
KICK_ENABLED="${VM_RESUME_GUARD_KICK_ENABLED:-1}"
KICK_COOLDOWN_SECONDS="${VM_RESUME_GUARD_KICK_COOLDOWN_SECONDS:-600}"  # 10 minutes
KICK_LAST_FILE="$STATE_DIR/last_kick_epoch.txt"
ADMIN_CHAT_FILE="${VM_RESUME_GUARD_ADMIN_CHAT_FILE:-$ROOT/docs/ops/ADMIN_TEAM_CHAT.md}"
IMMUTABLE_LOCK_ENABLED="${VM_RESUME_GUARD_IMMUTABLE_LOCK_ENABLED:-0}"

now_epoch="$(date -u +%s)"
last_epoch="0"
if [[ -f "$LAST_EPOCH_FILE" ]]; then
  last_epoch="$(cat "$LAST_EPOCH_FILE" 2>/dev/null || echo 0)"
fi
if ! [[ "$last_epoch" =~ ^[0-9]+$ ]]; then
  last_epoch=0
fi

gap=$((now_epoch - last_epoch))
if [[ "$last_epoch" -eq 0 ]]; then
  gap=0
fi

printf '%s\n' "$now_epoch" > "$LAST_EPOCH_FILE"

is_resume=0
if [[ "$FORCE" == "1" ]]; then
  is_resume=1
elif [[ "$last_epoch" -gt 0 && "$gap" -ge "$GAP_SECONDS" ]]; then
  is_resume=1
fi

ensure_tmux_session() {
  local session="$1"
  if ! command -v tmux >/dev/null 2>&1; then
    return 0
  fi
  if tmux has-session -t "$session" 2>/dev/null; then
    return 0
  fi
  tmux new-session -d -s "$session" -c "$ROOT" >/dev/null 2>&1 || true
  tmux set-option -t "$session" history-limit 200000 >/dev/null 2>&1 || true
  tmux send-keys -t "$session:0.0" "cd $ROOT" C-m >/dev/null 2>&1 || true
  tmux send-keys -t "$session:0.0" "echo '[RESUME_GUARD] recreated tmux session $session'" C-m >/dev/null 2>&1 || true
}

planner_orchestrator_active() {
  if [[ "${FC_PLANNER_ORCHESTRATOR_ENABLED:-0}" == "1" && "${FC_PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY:-0}" == "1" ]]; then
    return 0
  fi
  local cfg=""
  if [[ -f "$ROOT/platform/config/runner/runner.v1.yaml" ]]; then
    cfg="$ROOT/platform/config/runner/runner.v1.yaml"
  elif [[ -f "$ROOT/platform/config/runner/runner_config.v1.yaml" ]]; then
    cfg="$ROOT/platform/config/runner/runner_config.v1.yaml"
  fi
  if [[ -n "$cfg" ]] && command -v jq >/dev/null 2>&1; then
    local enabled cron_only
    enabled="$(jq -r '.features.planner_orchestrator.enabled // 0' "$cfg" 2>/dev/null || echo 0)"
    cron_only="$(jq -r '.features.planner_orchestrator.cron_planner_only // 0' "$cfg" 2>/dev/null || echo 0)"
    [[ "$enabled" == "1" && "$cron_only" == "1" ]]
    return
  fi
  return 1
}

resume_guard_sessions() {
  local topology_file="${FC_ROLE_TOPOLOGY_FILE:-$ROOT/docs/operations/orchestrator/parallel-role-topology-active.json}"
  local -a sessions=("adminapp_codex_sync" "admin-agents-sync-cron" "clawsentinel")
  local -a topology_sessions=()
  if [[ ! -f "$topology_file" ]]; then
    topology_file="$ROOT/docs/orchestrator-ops/parallel-role-topology-active.json"
  fi
  if [[ -f "$topology_file" ]] && command -v jq >/dev/null 2>&1; then
    mapfile -t topology_sessions < <(jq -r '.roles[]? | select((.enabled // true) != false) | .session_name // empty' "$topology_file" 2>/dev/null)
    for session in "${topology_sessions[@]}"; do
      [[ -n "$session" ]] && sessions+=("$session")
    done
  elif planner_orchestrator_active; then
    sessions+=("codex_planner_cron")
  else
    sessions+=("codex_planner_cron" "codex_dev_cron" "codex_admin_cron")
  fi
  printf '%s\n' "${sessions[@]}" | awk 'NF && !seen[$0]++'
}

if [[ "$is_resume" -eq 0 ]]; then
  echo "VM_RESUME_GUARD status=OK resume=0 gap_s=${gap}"
  exit 0
fi

ts_local="$(TZ=America/New_York date '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null || date)"

# 1) Ensure gateway
svc="$(systemctl --user is-active openclaw-gateway.service 2>/dev/null || true)"
if [[ "$svc" != "active" ]]; then
  systemctl --user restart openclaw-gateway.service >/dev/null 2>&1 || true
  sleep 2
fi
svc2="$(systemctl --user is-active openclaw-gateway.service 2>/dev/null || true)"

# 2) Stale sweep apply (safe)
stale_out="$(bash scripts/stale_cron_tick.sh 2>/dev/null | tr '\n' ' ' | sed 's/  */ /g' | cut -c1-260 || true)"
[[ -n "$stale_out" ]] || stale_out="stale_tick_no_output"

# 3) Ensure infra sessions plus active role sessions from current topology/config
while IFS= read -r s; do
  [[ -n "$s" ]] || continue
  ensure_tmux_session "$s"
done < <(resume_guard_sessions)

# 4) Deterministic triage snapshot
triage_top="$(bash scripts/triage_now.sh 2>/dev/null | sed -n 's/^TOP //p' | head -n 1 | tr '\n' ' ' | sed 's/  */ /g' | cut -c1-240 || true)"
[[ -n "$triage_top" ]] || triage_top="TOP issue=unknown"

# 4b) Optional immutable lock for OpenClaw config (disabled by default to avoid blocking runtime updates)
config_file="$HOME/.openclaw/openclaw.json"
config_lock="unknown"
if [[ -f "$config_file" ]] && command -v lsattr >/dev/null 2>&1; then
  if lsattr "$config_file" | rg -q '^-+i'; then
    config_lock="locked"
  elif [[ "$IMMUTABLE_LOCK_ENABLED" == "1" ]]; then
    sudo chattr +i "$config_file" >/dev/null 2>&1 || true
    config_lock="locked_after_resume"
  else
    config_lock="unlocked_by_policy"
  fi
fi

# 5) Optional kick of key crons (best-effort, with cooldown)
maybe_kick() {
  local now_epoch last_epoch
  now_epoch="$(date -u +%s)"
  last_epoch="0"
  if [[ -f "$KICK_LAST_FILE" ]]; then
    last_epoch="$(cat "$KICK_LAST_FILE" 2>/dev/null || echo 0)"
  fi
  if ! [[ "$last_epoch" =~ ^[0-9]+$ ]]; then
    last_epoch=0
  fi
  if [[ $((now_epoch - last_epoch)) -lt "$KICK_COOLDOWN_SECONDS" ]]; then
    echo "cooldown"
    return 0
  fi

  # Names are stable; resolve IDs dynamically.
  local names=(
    "stale-sweep-autoheal-7m"
    "dg-monitor-2m"
    "dg-admin-router-5m"
    "admin-agents-supervisor-15m"
  )
  local cron_json
  cron_json="$(openclaw cron list --all --json 2>/dev/null || openclaw cron list --json 2>/dev/null || echo '{"jobs":[]}')"
  local ok=0
  for name in "${names[@]}"; do
    jid="$(printf '%s' "$cron_json" | jq -r --arg n "$name" '.jobs[]? | select(.name==$n) | (.id // empty)' | head -n 1)"
    [[ -z "$jid" ]] && continue
    openclaw cron run --timeout 90000 "$jid" >/dev/null 2>&1 || true
    ok=$((ok+1))
  done
  printf '%s\n' "$now_epoch" > "$KICK_LAST_FILE"
  echo "kicked=${ok}"
}

kick_status="disabled"
if [[ "$KICK_ENABLED" == "1" ]]; then
  kick_status="$(maybe_kick)"
fi

# 6) Journal to admin chat (one line)
if [[ -f "$ADMIN_CHAT_FILE" ]]; then
  printf -- "- [%s] [vm-resume-guard] TYPE: INFO MSG: resume_detected gap_s=%s gateway=%s kick=%s triage=%s\n" \
    "$ts_local" "$gap" "${svc2:-unknown}" "$kick_status" "$triage_top" >> "$ADMIN_CHAT_FILE"
fi

echo "VM_RESUME_GUARD status=RESUME_DETECTED ts=\"$ts_local\" gap_s=${gap} gateway=${svc2:-unknown} config_lock=${config_lock:-unknown} stale=\"$stale_out\" kick=\"$kick_status\" triage=\"$triage_top\""
