#!/usr/bin/env bash
set -euo pipefail

MODE="admins-only"
ROLE="planner"
DRY_RUN=0
STATUS_ONLY=0
STOP_SESSIONS=0

ROLE_MAP_FILE="${ORCHESTRATION_ROLE_MAP_FILE:-docs/orchestrator-ops/parallel-role-cron-map.json}"

BASELINE_ADMIN_JOBS=(
  "adminapp-codex-sync-10m"
  "admin-agents-supervisor-15m"
)
BASELINE_UTILITY_JOBS=(
  "stale-sweep-autoheal-7m"
  "dg-alert-15m"
)

# role|id|name|session
ROLE_MAP=()
EXPECTED_NAMES=()
CURRENT_CRON_JSON='{"jobs":[]}'

usage() {
  cat <<'EOF'
Usage: set_orchestration_mode.sh [options]

Options:
  --mode <admins-only|sequential|parallel|paused>  Target mode (default: admins-only)
  --role <role>                                    Role used for sequential mode (default: planner)
  --stop-sessions                                  Kill mapped tmux sessions after mode apply
  --status                                         Print cron status only (no changes)
  --dry-run                                        Print planned actions without applying
  -h, --help                                       Show help
EOF
}

refresh_current_cron_json() {
  CURRENT_CRON_JSON="$(openclaw cron list --all --json 2>/dev/null || openclaw cron list --json 2>/dev/null || echo '{"jobs":[]}')"
}

job_id_for_name() {
  local name="$1"
  local id=""
  id="$(printf '%s' "$CURRENT_CRON_JSON" | jq -r --arg n "$name" '.jobs[]? | select(.name==$n) | .id' | head -n 1 || true)"
  if [[ -n "$id" && "$id" != "null" ]]; then
    printf '%s\n' "$id"
  fi
}

set_map_entry() {
  local role="$1"
  local id="$2"
  local name="$3"
  local session="$4"
  ROLE_MAP+=("${role}|${id}|${name}|${session}")
}

load_dynamic_role_map() {
  ROLE_MAP=()
  if [[ -f "$ROLE_MAP_FILE" ]]; then
    while IFS='|' read -r role id name session; do
      [[ -z "$role" || -z "$id" ]] && continue
      set_map_entry "$role" "$id" "$name" "$session"
    done < <(jq -r '.roles[]? | select((.role // "") != "" and (.id // "") != "") | "\(.role)|\(.id)|\((.name // .role))|\((.session_name // ""))"' "$ROLE_MAP_FILE" 2>/dev/null || true)
  fi

  # Fallback to static baseline if map file is temporarily unavailable.
  if [[ ${#ROLE_MAP[@]} -eq 0 ]]; then
    set_map_entry "planner" "" "planner-tmux-loop" "codex_planner_cron"
    set_map_entry "analyst" "" "analyst-tmux-loop" "codex_analyst_cron"
    set_map_entry "architect" "" "architect-tmux-loop" "codex_architect_cron"
    set_map_entry "backend_engineer" "" "backend-engineer-tmux-loop" "codex_backend_engineer_cron"
    set_map_entry "frontend_engineer" "" "frontend-engineer-tmux-loop" "codex_frontend_engineer_cron"
    set_map_entry "data_analyst" "" "data-analyst-tmux-loop" "codex_data_analyst_cron"
    set_map_entry "infra_engineer" "" "infra-engineer-tmux-loop" "codex_infra_engineer_cron"
    set_map_entry "integrator" "" "integrator-tmux-loop" "codex_integrator_cron"
    set_map_entry "dev" "" "dev-tmux-loop" "codex_dev_cron"
    set_map_entry "tester" "" "tester-tmux-loop" "codex_tester_cron"
    set_map_entry "qa" "" "qa-tmux-loop" "codex_qa_cron"
    set_map_entry "clawsentinel" "" "clawsentinel-tmux-loop" "clawsentinel"
  fi

  EXPECTED_NAMES=()
  local entry=""
  for entry in "${ROLE_MAP[@]}"; do
    IFS='|' read -r _ _ name _ <<< "$entry"
    if [[ -n "$name" ]]; then
      EXPECTED_NAMES+=("$name")
    fi
  done
  EXPECTED_NAMES+=("${BASELINE_ADMIN_JOBS[@]}")
  EXPECTED_NAMES+=("${BASELINE_UTILITY_JOBS[@]}")
}

cron_id_exists() {
  local id="$1"
  [[ -z "$id" ]] && return 1
  printf '%s' "$CURRENT_CRON_JSON" | jq -e --arg id "$id" '.jobs[]? | select(.id==$id)' >/dev/null 2>&1
}

is_expected_name() {
  local candidate="$1"
  local expected=""
  for expected in "${EXPECTED_NAMES[@]}"; do
    if [[ "$expected" == "$candidate" ]]; then
      return 0
    fi
  done
  return 1
}

find_role_id() {
  local role="$1"
  local entry=""
  for entry in "${ROLE_MAP[@]}"; do
    IFS='|' read -r role_name id name _ <<< "$entry"
    if [[ "$role_name" == "$role" ]]; then
      if [[ -n "$id" ]]; then
        printf '%s\n' "$id"
        return 0
      fi
      if [[ -n "$name" ]]; then
        job_id_for_name "$name"
        return 0
      fi
    fi
  done
  return 1
}

role_name_from_role() {
  local role="$1"
  local entry=""
  for entry in "${ROLE_MAP[@]}"; do
    IFS='|' read -r role_name _ name _ <<< "$entry"
    if [[ "$role_name" == "$role" ]]; then
      printf '%s\n' "$name"
      return 0
    fi
  done
  return 1
}

session_for_role() {
  local role="$1"
  local entry=""
  for entry in "${ROLE_MAP[@]}"; do
    IFS='|' read -r role_name _ _ session <<< "$entry"
    if [[ "$role_name" == "$role" ]]; then
      printf '%s\n' "$session"
      return 0
    fi
  done

  case "$role" in
    admin-agents) echo "admin-agents-sync-cron" ;;
    adminapp-codex) echo "adminapp_codex_sync" ;;
    *) return 1 ;;
  esac
}

set_job_state() {
  local id="$1"
  local action="$2"
  local label="$3"

  if ! cron_id_exists "$id"; then
    echo "SKIP ${action} ${label} reason=missing"
    return 0
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "DRY_RUN ${action} ${label} id=${id}"
    return 0
  fi

  if [[ "$action" == "enable" ]]; then
    openclaw cron enable "$id" >/dev/null 2>&1 || true
  else
    openclaw cron disable "$id" >/dev/null 2>&1 || true
  fi
}

enable_role() {
  local role="$1"
  local role_id=""
  local role_name=""

  role_id="$(find_role_id "$role" || true)"
  role_name="$(role_name_from_role "$role" || true)"
  if [[ -z "$role_id" ]]; then
    echo "SKIP enable role=$role reason=id_not_found"
    return 0
  fi
  if [[ -z "$role_name" ]]; then
    role_name="$role"
  fi

  set_job_state "$role_id" enable "role=$role name=$role_name"
}

enable_roles() {
  local entry=""
  local role=""
  for entry in "${ROLE_MAP[@]}"; do
    IFS='|' read -r role _ _ _ <<< "$entry"
    enable_role "$role"
  done
}

disable_roles() {
  local entry=""
  local role=""
  local role_id=""
  local role_name=""
  for entry in "${ROLE_MAP[@]}"; do
    IFS='|' read -r role role_id role_name _ <<< "$entry"
    if [[ -z "$role_id" && -n "$role_name" ]]; then
      role_id="$(job_id_for_name "$role_name" || true)"
    fi
    set_job_state "$role_id" disable "role=$role"
  done
}

enable_governance_jobs() {
  local job_name=""
  local job_id=""
  for job_name in "${BASELINE_ADMIN_JOBS[@]}" "${BASELINE_UTILITY_JOBS[@]}"; do
    job_id="$(job_id_for_name "$job_name" || true)"
    set_job_state "$job_id" enable "job=$job_name"
  done
}

disable_governance_jobs() {
  local job_name=""
  local job_id=""
  for job_name in "${BASELINE_ADMIN_JOBS[@]}" "${BASELINE_UTILITY_JOBS[@]}"; do
    job_id="$(job_id_for_name "$job_name" || true)"
    set_job_state "$job_id" disable "job=$job_name"
  done
}

disable_unexpected_jobs() {
  local id=""
  local name=""
  while IFS='|' read -r id name; do
    [[ -z "$id" || "$id" == "null" ]] && continue
    if ! is_expected_name "$name"; then
      set_job_state "$id" disable "unexpected=$name"
    fi
  done < <(printf '%s\n' "$CURRENT_CRON_JSON" | jq -r '.jobs[]? | .id + "|" + .name' 2>/dev/null || true)
}

kill_session_if_present() {
  local session="$1"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "DRY_RUN kill session=$session"
    return 0
  fi
  tmux kill-session -t "$session" >/dev/null 2>&1 || true
}

stop_disabled_sessions() {
  local keep_role="${1:-}"
  local entry=""
  local role=""
  local session=""

  for entry in "${ROLE_MAP[@]}"; do
    IFS='|' read -r role _ _ session <<< "$entry"
    if [[ -n "$keep_role" && "$role" == "$keep_role" ]]; then
      continue
    fi
    if [[ -n "$session" ]]; then
      kill_session_if_present "$session"
    fi
  done

  for role in admin-agents adminapp-codex; do
    if [[ -n "$keep_role" && "$role" == "$keep_role" ]]; then
      continue
    fi
    session="$(session_for_role "$role" || true)"
    if [[ -n "$session" ]]; then
      kill_session_if_present "$session"
    fi
  done
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    --role)
      ROLE="${2:-}"
      shift 2
      ;;
    --stop-sessions)
      STOP_SESSIONS=1
      shift
      ;;
    --status)
      STATUS_ONLY=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

refresh_current_cron_json
load_dynamic_role_map

if [[ "$STATUS_ONLY" -eq 1 ]]; then
  openclaw cron list
  exit 0
fi

case "$MODE" in
  admins-only)
    disable_roles
    disable_unexpected_jobs
    enable_governance_jobs
    if [[ "$STOP_SESSIONS" -eq 1 ]]; then
      stop_disabled_sessions
    fi
    ;;
  sequential)
    if ! find_role_id "$ROLE" >/dev/null 2>&1; then
      echo "Unsupported role for sequential mode: $ROLE" >&2
      exit 2
    fi
    disable_roles
    disable_unexpected_jobs
    enable_role "$ROLE"
    enable_governance_jobs
    if [[ "$STOP_SESSIONS" -eq 1 ]]; then
      stop_disabled_sessions "$ROLE"
    fi
    ;;
  parallel)
    enable_roles
    enable_governance_jobs
    disable_unexpected_jobs
    ;;
  paused)
    disable_roles
    disable_governance_jobs
    disable_unexpected_jobs
    if [[ "$STOP_SESSIONS" -eq 1 ]]; then
      stop_disabled_sessions
    fi
    ;;
  *)
    echo "Unsupported mode: $MODE" >&2
    usage
    exit 2
    ;;
esac

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "DRY_RUN mode applied only (no changes committed)."
else
  echo "ORCHESTRATION_MODE_APPLIED mode=${MODE} role=${ROLE} dry_run=${DRY_RUN} stop_sessions=${STOP_SESSIONS}"
fi
openclaw cron list
