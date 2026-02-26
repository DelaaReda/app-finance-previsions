#!/usr/bin/env bash
set -euo pipefail

MODE="admins-only"
ROLE="planner"
DRY_RUN=0
STATUS_ONLY=0
STOP_SESSIONS=0
ROLE_MAP_FILE="${ORCHESTRATION_ROLE_MAP_FILE:-docs/orchestrator-ops/parallel-role-cron-map.json}"

ROLE_MAP=(
  "planner:09d045db-b12a-4486-a743-57b761d52e50"
  "dev:dfd61f17-206f-4feb-ab14-6ae4ce54f04c"
  "tester:36bed423-e965-4a19-a43a-c8ffbff751d8"
  "qa:454dc361-14bb-4f71-8ca2-ec86708c503f"
  "architect:bde5885a-388f-4fe4-a8b7-a146521d9e9d"
  "po:44f08bd9-b9c0-4ab5-8882-cc91d402c8db"
  "scrum_master:8e5b1bd7-f319-48d8-b8f7-c906c024135f"
  "clawsentinel:25756cb4-57f1-41c7-83d4-66fd67a0164d"
)

ADMIN_MAP=(
  "admin-agents:838deae5-fa39-4052-b31d-66013faccee0"
  "adminapp-codex:fbccac5b-1028-4c9a-b021-c1998d3bad97"
  "stale-sweep-autoheal:"
)

usage() {
  cat <<'EOF'
Usage: set_orchestration_mode.sh [options]

Options:
  --mode <admins-only|sequential|parallel|paused>  Target mode (default: admins-only)
  --role <role>                              Role used for sequential mode (default: planner)
  --stop-sessions                            Kill mapped tmux sessions after mode apply
  --status                                   Print cron status only (no changes)
  --dry-run                                  Print planned actions without applying
  -h, --help                                 Show help
EOF
}

role_map_contains() {
  local role="$1"
  local pair=""
  for pair in "${ROLE_MAP[@]}"; do
    if [[ "${pair%%:*}" == "$role" ]]; then
      return 0
    fi
  done
  return 1
}

set_role_map_entry() {
  local role="$1"
  local id="$2"
  local pair=""
  local i=0
  for i in "${!ROLE_MAP[@]}"; do
    pair="${ROLE_MAP[$i]}"
    if [[ "${pair%%:*}" == "$role" ]]; then
      ROLE_MAP[$i]="${role}:${id}"
      return 0
    fi
  done
  ROLE_MAP+=("${role}:${id}")
}

load_dynamic_role_map() {
  local line=""
  local role=""
  local id=""
  if [[ ! -f "$ROLE_MAP_FILE" ]]; then
    return 0
  fi
  while IFS='|' read -r role id; do
    [[ -z "$role" || -z "$id" ]] && continue
    set_role_map_entry "$role" "$id"
  done < <(jq -r '.roles[]? | select((.role // "") != "" and (.id // "") != "") | "\(.role)|\(.id)"' "$ROLE_MAP_FILE" 2>/dev/null || true)
}

find_role_id() {
  local role="$1"
  local pair=""
  for pair in "${ROLE_MAP[@]}"; do
    if [[ "${pair%%:*}" == "$role" ]]; then
      printf '%s\n' "${pair#*:}"
      return 0
    fi
  done
  return 1
}

find_admin_id() {
  local admin="$1"
  local pair=""
  local id=""
  local name=""
  for pair in "${ADMIN_MAP[@]}"; do
    if [[ "${pair%%:*}" == "$admin" ]]; then
      id="${pair#*:}"
      if [[ -n "$id" ]]; then
        printf '%s\n' "$id"
        return 0
      fi
      break
    fi
  done
  case "$admin" in
    admin-agents) name="admin-agents-supervisor-15m" ;;
    adminapp-codex) name="adminapp-codex-sync-10m" ;;
    stale-sweep-autoheal) name="stale-sweep-autoheal-7m" ;;
    *) name="" ;;
  esac
  if [[ -n "$name" ]]; then
    id="$(printf '%s' "$CURRENT_CRON_JSON" | jq -r --arg n "$name" '.jobs[]? | select(.name==$n) | .id' | head -n 1 || true)"
    if [[ -n "$id" && "$id" != "null" ]]; then
      printf '%s\n' "$id"
      return 0
    fi
  fi
  return 1
}

session_for_role() {
  case "$1" in
    planner) echo "codex_planner_cron" ;;
    analyst) echo "codex_analyst_cron" ;;
    dev) echo "codex_dev_cron" ;;
    backend_engineer) echo "codex_backend_engineer_cron" ;;
    frontend_engineer) echo "codex_frontend_engineer_cron" ;;
    integrator) echo "codex_integrator_cron" ;;
    data_analyst) echo "codex_data_analyst_cron" ;;
    infra_engineer) echo "codex_infra_engineer_cron" ;;
    tester) echo "codex_tester_cron" ;;
    qa) echo "codex_qa_cron" ;;
    architect) echo "codex_architect_cron" ;;
    po) echo "codex_po_cron" ;;
    scrum_master) echo "codex_scrum_master_cron" ;;
    clawsentinel) echo "clawsentinel" ;;
    admin-agents) echo "admin-agents-sync-cron" ;;
    adminapp-codex) echo "adminapp_codex_sync" ;;
    stale-sweep-autoheal) echo "" ;;
    *) return 1 ;;
  esac
}

load_dynamic_role_map

CURRENT_CRON_JSON='{"jobs":[]}'

refresh_current_cron_json() {
  CURRENT_CRON_JSON="$(openclaw cron list --json 2>/dev/null || echo '{"jobs":[]}')"
}

cron_id_exists() {
  local id="$1"
  [[ -z "$id" ]] && return 1
  printf '%s' "$CURRENT_CRON_JSON" | jq -e --arg id "$id" '.jobs[]? | select(.id==$id)' >/dev/null 2>&1
}

disable_all_roles() {
  local pair=""
  local id=""
  for pair in "${ROLE_MAP[@]}"; do
    id="${pair#*:}"
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "DRY_RUN disable role_id=$id"
    else
      if ! cron_id_exists "$id"; then
        echo "SKIP disable role_id=$id reason=missing"
        continue
      fi
      openclaw cron disable "$id" >/dev/null 2>&1 || true
    fi
  done
}

enable_all_admins() {
  local pair=""
  local admin=""
  local id=""
  for pair in "${ADMIN_MAP[@]}"; do
    admin="${pair%%:*}"
    id="$(find_admin_id "$admin" || true)"
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "DRY_RUN enable admin=${admin} admin_id=${id:-missing}"
    else
      if [[ -z "$id" ]] || ! cron_id_exists "$id"; then
        echo "SKIP enable admin=${admin} admin_id=${id:-missing} reason=missing"
        continue
      fi
      openclaw cron enable "$id" >/dev/null 2>&1 || true
    fi
  done
}

disable_all_admins() {
  local pair=""
  local admin=""
  local id=""
  for pair in "${ADMIN_MAP[@]}"; do
    admin="${pair%%:*}"
    id="$(find_admin_id "$admin" || true)"
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "DRY_RUN disable admin=${admin} admin_id=${id:-missing}"
    else
      if [[ -z "$id" ]] || ! cron_id_exists "$id"; then
        echo "SKIP disable admin=${admin} admin_id=${id:-missing} reason=missing"
        continue
      fi
      openclaw cron disable "$id" >/dev/null 2>&1 || true
    fi
  done
}

enable_role() {
  local role="$1"
  local id=""
  id="$(find_role_id "$role")"
  if [[ -z "$id" ]]; then
    echo "SKIP enable role=$role reason=id_not_found"
    return 0
  fi
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "DRY_RUN enable role=$role role_id=$id"
  else
    if ! cron_id_exists "$id"; then
      echo "SKIP enable role=$role role_id=$id reason=missing"
      return 0
    fi
    openclaw cron enable "$id" >/dev/null 2>&1 || true
  fi
}

enable_all_roles() {
  local pair=""
  local role=""
  for pair in "${ROLE_MAP[@]}"; do
    role="${pair%%:*}"
    enable_role "$role"
  done
}

stop_disabled_sessions() {
  local keep_role="${1:-}"
  local pair=""
  local role=""
  local sess=""

  for pair in "${ROLE_MAP[@]}"; do
    role="${pair%%:*}"
    if [[ -n "$keep_role" && "$role" == "$keep_role" ]]; then
      continue
    fi
    sess="$(session_for_role "$role" || true)"
    if [[ -n "$sess" ]]; then
      if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "DRY_RUN kill session=$sess"
      else
        tmux kill-session -t "$sess" >/dev/null 2>&1 || true
      fi
    fi
  done

  for pair in "${ADMIN_MAP[@]}"; do
    role="${pair%%:*}"
    sess="$(session_for_role "$role" || true)"
    if [[ -n "$sess" ]]; then
      if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "DRY_RUN kill session=$sess"
      else
        tmux kill-session -t "$sess" >/dev/null 2>&1 || true
      fi
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

if [[ "$STATUS_ONLY" -eq 1 ]]; then
  openclaw cron list
  exit 0
fi

refresh_current_cron_json

case "$MODE" in
  admins-only)
    disable_all_roles
    enable_all_admins
    if [[ "$STOP_SESSIONS" -eq 1 ]]; then
      stop_disabled_sessions
    fi
    ;;
  sequential)
    if ! find_role_id "$ROLE" >/dev/null 2>&1; then
      echo "Unsupported role for sequential mode: $ROLE" >&2
      exit 2
    fi
    disable_all_roles
    enable_role "$ROLE"
    enable_all_admins
    if [[ "$STOP_SESSIONS" -eq 1 ]]; then
      stop_disabled_sessions "$ROLE"
    fi
    ;;
  parallel)
    enable_all_roles
    enable_all_admins
    ;;
  paused)
    disable_all_roles
    disable_all_admins
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

echo "ORCHESTRATION_MODE_APPLIED mode=${MODE} role=${ROLE} dry_run=${DRY_RUN} stop_sessions=${STOP_SESSIONS}"
openclaw cron list
