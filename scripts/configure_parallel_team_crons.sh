#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

APPLY=0
ENABLE_AFTER_CREATE=0
THINKING_LEVEL="${PARALLEL_CRON_THINKING:-high}"
TIMEOUT_SECONDS="${PARALLEL_CRON_TIMEOUT_SECONDS:-480}"
MAP_FILE="${PARALLEL_ROLE_MAP_FILE:-docs/orchestrator-ops/parallel-role-cron-map.json}"
TOPOLOGY_FILE="${PARALLEL_ROLE_TOPOLOGY_FILE:-docs/orchestrator-ops/parallel-role-topology.json}"
ENABLE_STALE_SWEEP="${PARALLEL_ENABLE_STALE_SWEEP:-1}"
STALE_SWEEP_JOB_NAME="${PARALLEL_STALE_SWEEP_JOB_NAME:-stale-sweep-autoheal-7m}"
STALE_SWEEP_EVERY="${PARALLEL_STALE_SWEEP_EVERY:-7m}"
STALE_SWEEP_AGENT="${PARALLEL_STALE_SWEEP_AGENT:-adminapp-codex}"
STALE_SWEEP_THINKING="${PARALLEL_STALE_SWEEP_THINKING:-low}"
STALE_SWEEP_TIMEOUT_SECONDS="${PARALLEL_STALE_SWEEP_TIMEOUT_SECONDS:-180}"
STALE_SWEEP_THRESHOLD_SECONDS="${PARALLEL_STALE_SWEEP_THRESHOLD_SECONDS:-330}"
BACKUP_DIR="/home/venom/.openclaw/cron/backups"
TS="$(date +%Y%m%d-%H%M%S)"

DEFAULT_ROLE_PROFILES=(
  "planner|12m|0|Planner dispatch and dependency orchestration"
  "analyst|14m|0|Business analysis and requirement clarity"
  "architect|18m|0|Architecture constraints and guardrails"
  "backend_engineer|12m|1|Backend implementation lane"
  "frontend_engineer|12m|1|Frontend implementation lane"
  "integrator|15m|1|Cross-team integration lane"
  "data_analyst|17m|1|Data validation and metrics lane"
  "infra_engineer|20m|1|Infra and CI/CD acceleration lane"
  "dev|16m|1|Legacy generalist dev lane"
  "tester|15m|1|Test automation lane"
  "qa|20m|1|Quality gate and release lane"
  "po|30m|0|Scope and backlog value lane"
  "scrum_master|15m|0|Flow and blocker cadence lane"
  "clawsentinel|25m|0|Safety and anti-drift lane"
)
ROLE_PROFILES=("${DEFAULT_ROLE_PROFILES[@]}")

usage() {
  cat <<'EOF'
Usage: configure_parallel_team_crons.sh [options]

Options:
  --apply           Apply cron add/edit changes (default: dry-run)
  --enable          Enable jobs after create/edit (requires --apply)
  --map-file <p>    Output role map path (default: docs/orchestrator-ops/parallel-role-cron-map.json)
  --topology-file <p>  Input topology JSON (default: docs/orchestrator-ops/parallel-role-topology.json)
  --disable-stale-sweep  Do not create/update dedicated stale sweep cron
  --stale-sweep-every <dur>  Schedule for stale sweep job (default: 7m)
  --stale-sweep-timeout <sec> Timeout for stale sweep job (default: 180)
  --stale-sweep-threshold <sec> Stale threshold passed to sweep tick (default: 330)
  -h, --help        Show help
EOF
}

load_role_profiles_from_topology() {
  local loaded=()
  if [[ ! -f "$TOPOLOGY_FILE" ]]; then
    return 0
  fi
  mapfile -t loaded < <(jq -r '.roles[]? | select((.role // "") != "") | "\(.role)|\(.every // "15m")|\(.allow_file_edits // 0)|\(.description // "parallel role lane")"' "$TOPOLOGY_FILE" 2>/dev/null || true)
  if [[ "${#loaded[@]}" -gt 0 ]]; then
    ROLE_PROFILES=("${loaded[@]}")
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      APPLY=1
      shift
      ;;
    --enable)
      ENABLE_AFTER_CREATE=1
      shift
      ;;
    --map-file)
      MAP_FILE="${2:-}"
      shift 2
      ;;
    --topology-file)
      TOPOLOGY_FILE="${2:-}"
      shift 2
      ;;
    --disable-stale-sweep)
      ENABLE_STALE_SWEEP=0
      shift
      ;;
    --stale-sweep-every)
      STALE_SWEEP_EVERY="${2:-}"
      shift 2
      ;;
    --stale-sweep-timeout)
      STALE_SWEEP_TIMEOUT_SECONDS="${2:-}"
      shift 2
      ;;
    --stale-sweep-threshold)
      STALE_SWEEP_THRESHOLD_SECONDS="${2:-}"
      shift 2
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

if [[ "$ENABLE_AFTER_CREATE" -eq 1 && "$APPLY" -ne 1 ]]; then
  echo "--enable requires --apply" >&2
  exit 2
fi

if ! [[ "$ENABLE_STALE_SWEEP" =~ ^[01]$ ]]; then
  ENABLE_STALE_SWEEP=1
fi
if ! [[ "$STALE_SWEEP_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || [[ "$STALE_SWEEP_TIMEOUT_SECONDS" -lt 60 ]]; then
  STALE_SWEEP_TIMEOUT_SECONDS=180
fi
if ! [[ "$STALE_SWEEP_THRESHOLD_SECONDS" =~ ^[0-9]+$ ]] || [[ "$STALE_SWEEP_THRESHOLD_SECONDS" -lt 60 ]]; then
  STALE_SWEEP_THRESHOLD_SECONDS=330
fi

if ! command -v openclaw >/dev/null 2>&1; then
  echo "openclaw not found in PATH" >&2
  exit 5
fi

load_role_profiles_from_topology

role_slug() {
  printf '%s' "$1" | tr '_' '-'
}

agent_for_role() {
  printf '%s' "$1" | tr '-' '_'
}

job_name_for_role() {
  local role="$1"
  printf '%s-tmux-loop' "$(role_slug "$role")"
}

session_for_role() {
  local from_topology=""
  if [[ -f "$TOPOLOGY_FILE" ]]; then
    from_topology="$(jq -r --arg r "$1" '.roles[]? | select(.role==$r) | .session_name // empty' "$TOPOLOGY_FILE" 2>/dev/null | head -n 1 || true)"
  fi
  if [[ -n "$from_topology" ]]; then
    echo "$from_topology"
    return 0
  fi
  case "$1" in
    planner) echo "codex_planner_cron" ;;
    analyst) echo "codex_analyst_cron" ;;
    architect) echo "codex_architect_cron" ;;
    backend_engineer) echo "codex_backend_engineer_cron" ;;
    frontend_engineer) echo "codex_frontend_engineer_cron" ;;
    integrator) echo "codex_integrator_cron" ;;
    data_analyst) echo "codex_data_analyst_cron" ;;
    infra_engineer) echo "codex_infra_engineer_cron" ;;
    dev) echo "codex_dev_cron" ;;
    tester) echo "codex_tester_cron" ;;
    qa) echo "codex_qa_cron" ;;
    po) echo "codex_po_cron" ;;
    scrum_master) echo "codex_scrum_master_cron" ;;
    clawsentinel) echo "clawsentinel" ;;
    *) return 1 ;;
  esac
}

trace_for_role() {
  local from_topology=""
  if [[ -f "$TOPOLOGY_FILE" ]]; then
    from_topology="$(jq -r --arg r "$1" '.roles[]? | select(.role==$r) | .trace_file // empty' "$TOPOLOGY_FILE" 2>/dev/null | head -n 1 || true)"
  fi
  if [[ -n "$from_topology" ]]; then
    echo "$from_topology"
    return 0
  fi
  case "$1" in
    scrum_master) echo "logs-codex-runs/role-runner/scrum_master.live.log" ;;
    *) echo "logs-codex-runs/role-runner/$1.live.log" ;;
  esac
}

message_for_role() {
  local role="$1"
  local allow_edits="$2"
  cat <<EOF
Execute exactly this shell command and return ONLY its stdout, verbatim, no explanation.
Never call send/message/delivery actions.
Command: TMUX_ROLE_AGENT_BIN=codex TMUX_ROLE_RETRY_ENGINE_DEFAULT=sdk PROMPT_TIMEOUT_SECONDS=55 RETRY_PROMPT_TIMEOUT_SECONDS=30 TMUX_ROLE_RECOVERY_THRESHOLD=2 TMUX_ROLE_NO_DELTA_THRESHOLD=12 TMUX_ROLE_STALL_ABORT_SECONDS=18 SKIP_RETRY_ON_TIMEOUT=1 TMUX_ROLE_CODEX_EXEC_FALLBACK=1 TMUX_ROLE_CODEX_MODEL=gpt-5.3-codex TMUX_ROLE_CODEX_EXEC_RESUME=1 TMUX_ROLE_ALLOW_FILE_EDITS=${allow_edits} bash scripts/cron_tmux_role_runner.sh ${role}
EOF
}

message_for_stale_sweep() {
  cat <<EOF
Execute exactly this shell command and return ONLY its stdout, verbatim, no explanation.
Never call send/message/delivery actions.
Command: STALE_SWEEP_THRESHOLD_SECONDS=${STALE_SWEEP_THRESHOLD_SECONDS} bash scripts/stale_cron_tick.sh
EOF
}

find_job_id_by_name() {
  local name="$1"
  openclaw cron list --json | jq -r --arg n "$name" '.jobs[]? | select(.name==$n) | .id' | head -n 1
}

upsert_job() {
  local role="$1"
  local every="$2"
  local allow_edits="$3"
  local desc="$4"
  local name=""
  local agent_id=""
  local id=""
  local msg=""

  name="$(job_name_for_role "$role")"
  agent_id="$(agent_for_role "$role")"
  msg="$(message_for_role "$role" "$allow_edits")"
  id="$(find_job_id_by_name "$name" || true)"

  if [[ "$APPLY" -eq 0 ]]; then
    echo "PLAN role=${role} name=${name} agent=${agent_id} every=${every} allow_file_edits=${allow_edits} existing_id=${id:-none}"
    return 0
  fi

  if [[ -n "$id" ]]; then
    openclaw cron edit "$id" \
      --name "$name" \
      --description "$desc" \
      --agent "$agent_id" \
      --every "$every" \
      --thinking "$THINKING_LEVEL" \
      --session isolated \
      --no-deliver \
      --wake now \
      --timeout-seconds "$TIMEOUT_SECONDS" \
      --message "$msg" >/dev/null
  else
    openclaw cron add \
      --name "$name" \
      --description "$desc" \
      --agent "$agent_id" \
      --every "$every" \
      --thinking "$THINKING_LEVEL" \
      --session isolated \
      --no-deliver \
      --wake now \
      --timeout-seconds "$TIMEOUT_SECONDS" \
      --message "$msg" >/dev/null
    id="$(find_job_id_by_name "$name" || true)"
  fi

  if [[ "$ENABLE_AFTER_CREATE" -eq 1 && -n "$id" ]]; then
    openclaw cron enable "$id" >/dev/null 2>&1 || true
  fi

  echo "APPLIED role=${role} name=${name} agent=${agent_id} id=${id:-unknown} every=${every} allow_file_edits=${allow_edits}"
}

upsert_stale_sweep_job() {
  local id=""
  local msg=""
  local desc="Automatic stale-running cron auto-heal sweep"
  id="$(find_job_id_by_name "$STALE_SWEEP_JOB_NAME" || true)"
  msg="$(message_for_stale_sweep)"

  if [[ "$ENABLE_STALE_SWEEP" -eq 0 ]]; then
    if [[ "$APPLY" -eq 0 ]]; then
      echo "PLAN utility=stale_sweep name=${STALE_SWEEP_JOB_NAME} enabled=0 existing_id=${id:-none}"
      return 0
    fi
    if [[ -n "$id" ]]; then
      openclaw cron disable "$id" >/dev/null 2>&1 || true
      echo "APPLIED utility=stale_sweep name=${STALE_SWEEP_JOB_NAME} id=${id} action=disabled"
    else
      echo "APPLIED utility=stale_sweep name=${STALE_SWEEP_JOB_NAME} id=none action=skip_missing"
    fi
    return 0
  fi

  if [[ "$APPLY" -eq 0 ]]; then
    echo "PLAN utility=stale_sweep name=${STALE_SWEEP_JOB_NAME} agent=${STALE_SWEEP_AGENT} every=${STALE_SWEEP_EVERY} timeout=${STALE_SWEEP_TIMEOUT_SECONDS} existing_id=${id:-none}"
    return 0
  fi

  if [[ -n "$id" ]]; then
    openclaw cron edit "$id" \
      --name "$STALE_SWEEP_JOB_NAME" \
      --description "$desc" \
      --agent "$STALE_SWEEP_AGENT" \
      --every "$STALE_SWEEP_EVERY" \
      --thinking "$STALE_SWEEP_THINKING" \
      --session isolated \
      --no-deliver \
      --wake now \
      --timeout-seconds "$STALE_SWEEP_TIMEOUT_SECONDS" \
      --message "$msg" >/dev/null
  else
    openclaw cron add \
      --name "$STALE_SWEEP_JOB_NAME" \
      --description "$desc" \
      --agent "$STALE_SWEEP_AGENT" \
      --every "$STALE_SWEEP_EVERY" \
      --thinking "$STALE_SWEEP_THINKING" \
      --session isolated \
      --no-deliver \
      --wake now \
      --timeout-seconds "$STALE_SWEEP_TIMEOUT_SECONDS" \
      --message "$msg" >/dev/null
    id="$(find_job_id_by_name "$STALE_SWEEP_JOB_NAME" || true)"
  fi

  if [[ "$ENABLE_AFTER_CREATE" -eq 1 && -n "$id" ]]; then
    openclaw cron enable "$id" >/dev/null 2>&1 || true
  fi
  echo "APPLIED utility=stale_sweep name=${STALE_SWEEP_JOB_NAME} agent=${STALE_SWEEP_AGENT} id=${id:-unknown} every=${STALE_SWEEP_EVERY} timeout=${STALE_SWEEP_TIMEOUT_SECONDS}"
}

if [[ "$APPLY" -eq 1 ]]; then
  mkdir -p "$BACKUP_DIR"
  cp /home/venom/.openclaw/cron/jobs.json "${BACKUP_DIR}/jobs.parallel.${TS}.json"
  openclaw cron list --json > "${BACKUP_DIR}/list.parallel.${TS}.json"
fi

for line in "${ROLE_PROFILES[@]}"; do
  role="${line%%|*}"
  rest="${line#*|}"
  every="${rest%%|*}"
  rest="${rest#*|}"
  allow_edits="${rest%%|*}"
  desc="${rest#*|}"
  upsert_job "$role" "$every" "$allow_edits" "$desc"
  sleep 1
done

upsert_stale_sweep_job
sleep 1

cron_json="$(openclaw cron list --json)"
map_tmp="$(mktemp)"
{
  echo '{'
  echo '  "generatedAtUtc": "'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'",'
  echo '  "thinking": "'"$THINKING_LEVEL"'",'
  echo '  "timeoutSeconds": '"$TIMEOUT_SECONDS"','
  echo '  "roles": ['

  first=1
  for line in "${ROLE_PROFILES[@]}"; do
    role="${line%%|*}"
    rest="${line#*|}"
    every="${rest%%|*}"
    rest="${rest#*|}"
    allow_edits="${rest%%|*}"
    name="$(job_name_for_role "$role")"
    id="$(printf '%s' "$cron_json" | jq -r --arg n "$name" '.jobs[]? | select(.name==$n) | .id' | head -n 1)"
    session_name="$(session_for_role "$role" || true)"
    trace_file="$(trace_for_role "$role" || true)"
    lane="$(jq -r --arg r "$role" '.roles[]? | select(.role==$r) | .lane // ""' "$TOPOLOGY_FILE" 2>/dev/null | head -n 1 || true)"
    agent_id="$(agent_for_role "$role")"
    wip_limit="$(jq -r --arg r "$role" '.roles[]? | select(.role==$r) | .wip_limit // 0' "$TOPOLOGY_FILE" 2>/dev/null | head -n 1 || true)"
    if [[ ! "$wip_limit" =~ ^[0-9]+$ ]]; then
      wip_limit=0
    fi

    if [[ "$first" -eq 0 ]]; then
      echo '    ,'
    fi
    first=0
    provisioned=0
    if [[ -n "$id" ]]; then
      provisioned=1
    fi

    jq -nc \
      --arg role "$role" \
      --arg id "$id" \
      --arg name "$name" \
      --arg every "$every" \
      --arg agent_id "$agent_id" \
      --arg session_name "$session_name" \
      --arg trace_file "$trace_file" \
      --arg lane "$lane" \
      --argjson wip_limit "$wip_limit" \
      --argjson provisioned "$provisioned" \
      --argjson allow_file_edits "$allow_edits" \
      '{role:$role,id:$id,name:$name,agent_id:$agent_id,every:$every,lane:$lane,wip_limit:$wip_limit,allow_file_edits:$allow_file_edits,provisioned:$provisioned,session_name:$session_name,trace_file:$trace_file}'
  done

  echo '  ],'
  echo '  "utility_jobs": ['
  stale_id="$(printf '%s' "$cron_json" | jq -r --arg n "$STALE_SWEEP_JOB_NAME" '.jobs[]? | select(.name==$n) | .id' | head -n 1)"
  stale_provisioned=0
  if [[ -n "$stale_id" ]]; then
    stale_provisioned=1
  fi
  if [[ "$ENABLE_STALE_SWEEP" -eq 1 ]]; then
    jq -nc \
      --arg name "$STALE_SWEEP_JOB_NAME" \
      --arg id "$stale_id" \
      --arg agent_id "$STALE_SWEEP_AGENT" \
      --arg every "$STALE_SWEEP_EVERY" \
      --arg thinking "$STALE_SWEEP_THINKING" \
      --argjson timeout "$STALE_SWEEP_TIMEOUT_SECONDS" \
      --argjson threshold "$STALE_SWEEP_THRESHOLD_SECONDS" \
      --argjson provisioned "$stale_provisioned" \
      '{name:$name,id:$id,agent_id:$agent_id,every:$every,thinking:$thinking,timeout_seconds:$timeout,threshold_seconds:$threshold,provisioned:$provisioned}'
  fi
  echo '  ]'
  echo '}'
} > "$map_tmp"

mkdir -p "$(dirname "$MAP_FILE")"
python3 - "$map_tmp" "$MAP_FILE" <<'PY'
import json
import sys
from pathlib import Path

tmp_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])
obj = json.loads(tmp_path.read_text(encoding="utf-8"))
out_path.write_text(json.dumps(obj, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
print(f"ROLE_MAP_WRITTEN path={out_path} roles={len(obj.get('roles', []))}")
PY
rm -f "$map_tmp"

echo "PARALLEL_CRON_CONFIG_DONE apply=${APPLY} enable=${ENABLE_AFTER_CREATE} map=${MAP_FILE}"
