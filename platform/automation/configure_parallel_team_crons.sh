#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd -P)"
cd "$ROOT"

DISABLE_PARALLEL_CRONS_FILE="${ROOT}/.parallel-crons-disabled"
CONFIGS_DIR="${ROOT}/configs"
if [[ -f "$DISABLE_PARALLEL_CRONS_FILE" ]]; then
  echo "Parallel cron provisioning disabled via $DISABLE_PARALLEL_CRONS_FILE" >&2
  exit 0
fi

MODEL_CONFIG_FILE="${ROOT}/platform/config/lm_used_model_config.sh"
if [[ ! -f "$MODEL_CONFIG_FILE" ]]; then
  MODEL_CONFIG_FILE="${CONFIGS_DIR}/model-config.sh"
fi
if [[ -f "$MODEL_CONFIG_FILE" ]]; then
  # shellcheck source=SCRIPTDIR_UP/platform/config/model-config.sh
  source "$MODEL_CONFIG_FILE"
fi

APPLY=0
ENABLE_AFTER_CREATE=0
THINKING_LEVEL="${PARALLEL_CRON_THINKING:-${LM_USED_ROLE_THINKING:-${MODEL_CONFIG_ROLE_THINKING:-${MODEL_CONFIG_PARALLEL_ROLE_THINKING}}}}"
TIMEOUT_SECONDS="${PARALLEL_CRON_TIMEOUT_SECONDS:-900}"
MAP_FILE="${PARALLEL_ROLE_MAP_FILE:-docs/orchestrator-ops/parallel-role-cron-map.json}"
TOPOLOGY_FILE="${PARALLEL_ROLE_TOPOLOGY_FILE:-docs/orchestrator-ops/parallel-role-topology.json}"
ENABLE_STALE_SWEEP="${PARALLEL_ENABLE_STALE_SWEEP:-1}"
STALE_SWEEP_JOB_NAME="${PARALLEL_STALE_SWEEP_JOB_NAME:-stale-sweep-autoheal-7m}"
STALE_SWEEP_EVERY="${PARALLEL_STALE_SWEEP_EVERY:-7m}"
STALE_SWEEP_AGENT="${PARALLEL_STALE_SWEEP_AGENT:-adminapp-codex}"
STALE_SWEEP_THINKING="${PARALLEL_STALE_SWEEP_THINKING:-$THINKING_LEVEL}"
STALE_SWEEP_TIMEOUT_SECONDS="${PARALLEL_STALE_SWEEP_TIMEOUT_SECONDS:-420}"
STALE_SWEEP_THRESHOLD_SECONDS="${PARALLEL_STALE_SWEEP_THRESHOLD_SECONDS:-330}"
ENABLE_DG_ALERT="${PARALLEL_ENABLE_DG_ALERT:-1}"
DG_ALERT_JOB_NAME="${PARALLEL_DG_ALERT_JOB_NAME:-dg-alert-15m}"
DG_ALERT_EVERY="${PARALLEL_DG_ALERT_EVERY:-15m}"
DG_ALERT_AGENT="${PARALLEL_DG_ALERT_AGENT:-adminapp-codex}"
DG_ALERT_THINKING="${PARALLEL_DG_ALERT_THINKING:-$THINKING_LEVEL}"
DG_ALERT_TIMEOUT_SECONDS="${PARALLEL_DG_ALERT_TIMEOUT_SECONDS:-300}"
ROLE_PROMPT_TIMEOUT_SECONDS="${PARALLEL_ROLE_PROMPT_TIMEOUT_SECONDS:-180}"
ROLE_RETRY_PROMPT_TIMEOUT_SECONDS="${PARALLEL_ROLE_RETRY_PROMPT_TIMEOUT_SECONDS:-90}"
ROLE_RECOVERY_THRESHOLD="${PARALLEL_ROLE_RECOVERY_THRESHOLD:-2}"
ROLE_NO_DELTA_THRESHOLD="${PARALLEL_ROLE_NO_DELTA_THRESHOLD:-12}"
ROLE_STALL_ABORT_SECONDS="${PARALLEL_ROLE_STALL_ABORT_SECONDS:-75}"
ROLE_SKIP_RETRY_ON_TIMEOUT="${PARALLEL_ROLE_SKIP_RETRY_ON_TIMEOUT:-1}"
ROLE_RETRY_ENGINE_DEFAULT="${PARALLEL_ROLE_RETRY_ENGINE_DEFAULT:-sdk}"
ROLE_AGENT_BIN="${PARALLEL_ROLE_AGENT_BIN:-codex}"
ROLE_CODEX_EXEC_FALLBACK="${PARALLEL_ROLE_CODEX_EXEC_FALLBACK:-1}"
ROLE_CODEX_MODEL="${PARALLEL_ROLE_CODEX_MODEL:-${LM_USED_ROLE_MODEL:-${MODEL_CONFIG_ROLE_MODEL:-${MODEL_CONFIG_PARALLEL_ROLE_MODEL}}}}"
ROLE_CODEX_EXEC_RESUME="${PARALLEL_ROLE_CODEX_EXEC_RESUME:-1}"
ROLE_MIN_REFLECTION_PASSES="${PARALLEL_ROLE_MIN_REFLECTION_PASSES:-${LM_USED_ROLE_MIN_REFLECTION_PASSES:-${MODEL_CONFIG_PARALLEL_ROLE_MIN_REFLECTION_PASSES:-2}}}"
BACKUP_DIR="/home/venom/.openclaw/cron/backups"
TS="$(date +%Y%m%d-%H%M%S)"

DEFAULT_ROLE_PROFILES=(
  "planner|12m|1|vision-architect-tasks-planner: dispatch + analyst/architect/po/scrum regrouped lane"
  "backend_engineer|12m|1|Backend implementation lane"
  "frontend_engineer|12m|1|Frontend implementation lane"
  "integrator|15m|1|Cross-team integration lane"
  "data_analyst|17m|1|Data validation and metrics lane"
  "infra_engineer|20m|1|Infra and CI/CD acceleration lane"
  "dev|16m|1|Legacy generalist dev lane"
  "tester|15m|1|Test automation lane"
  "qa|20m|1|Quality gate and release lane"
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
  --stale-sweep-timeout <sec> Timeout for stale sweep job (default: 420)
  --stale-sweep-threshold <sec> Stale threshold passed to sweep tick (default: 330)
  --disable-dg-alert     Do not create/update monitoring digest cron
  --dg-alert-every <dur> Schedule for dg-alert job (default: 15m)
  --dg-alert-timeout <sec> Timeout for dg-alert job (default: 300)
  -h, --help        Show help
EOF
}

normalize_reasoning_level() {
  local raw="${1:-high}"
  local normalized
  normalized="$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
  case "$normalized" in
    minimal|low|medium|high) printf '%s\n' "$normalized" ;;
    xhigh|extra|extra_high|veryhigh|max|maximum|"") printf 'high\n' ;;
    *) printf 'high\n' ;;
  esac
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
    --disable-dg-alert)
      ENABLE_DG_ALERT=0
      shift
      ;;
    --dg-alert-every)
      DG_ALERT_EVERY="${2:-}"
      shift 2
      ;;
    --dg-alert-timeout)
      DG_ALERT_TIMEOUT_SECONDS="${2:-}"
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
  STALE_SWEEP_TIMEOUT_SECONDS=420
fi
if ! [[ "$STALE_SWEEP_THRESHOLD_SECONDS" =~ ^[0-9]+$ ]] || [[ "$STALE_SWEEP_THRESHOLD_SECONDS" -lt 60 ]]; then
  STALE_SWEEP_THRESHOLD_SECONDS=330
fi
if ! [[ "$ENABLE_DG_ALERT" =~ ^[01]$ ]]; then
  ENABLE_DG_ALERT=1
fi
if ! [[ "$DG_ALERT_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || [[ "$DG_ALERT_TIMEOUT_SECONDS" -lt 60 ]]; then
  DG_ALERT_TIMEOUT_SECONDS=300
fi
if ! [[ "$TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || [[ "$TIMEOUT_SECONDS" -lt 300 ]]; then
  TIMEOUT_SECONDS=900
fi
if ! [[ "$ROLE_PROMPT_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || [[ "$ROLE_PROMPT_TIMEOUT_SECONDS" -lt 90 ]]; then
  ROLE_PROMPT_TIMEOUT_SECONDS=180
fi
if ! [[ "$ROLE_RETRY_PROMPT_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || [[ "$ROLE_RETRY_PROMPT_TIMEOUT_SECONDS" -lt 45 ]]; then
  ROLE_RETRY_PROMPT_TIMEOUT_SECONDS=90
fi
if ! [[ "$ROLE_RECOVERY_THRESHOLD" =~ ^[0-9]+$ ]] || [[ "$ROLE_RECOVERY_THRESHOLD" -lt 1 ]]; then
  ROLE_RECOVERY_THRESHOLD=2
fi
if ! [[ "$ROLE_NO_DELTA_THRESHOLD" =~ ^[0-9]+$ ]] || [[ "$ROLE_NO_DELTA_THRESHOLD" -lt 1 ]]; then
  ROLE_NO_DELTA_THRESHOLD=12
fi
if ! [[ "$ROLE_STALL_ABORT_SECONDS" =~ ^[0-9]+$ ]]; then
  ROLE_STALL_ABORT_SECONDS=75
fi
if ! [[ "$ROLE_SKIP_RETRY_ON_TIMEOUT" =~ ^[01]$ ]]; then
  ROLE_SKIP_RETRY_ON_TIMEOUT=1
fi
if [[ "$ROLE_RETRY_ENGINE_DEFAULT" != "tmux" && "$ROLE_RETRY_ENGINE_DEFAULT" != "sdk" ]]; then
  ROLE_RETRY_ENGINE_DEFAULT="sdk"
fi
if [[ -z "$ROLE_AGENT_BIN" ]]; then
  ROLE_AGENT_BIN="codex"
fi
if ! [[ "$ROLE_CODEX_EXEC_FALLBACK" =~ ^[01]$ ]]; then
  ROLE_CODEX_EXEC_FALLBACK=1
fi
if ! [[ "$ROLE_CODEX_EXEC_RESUME" =~ ^[01]$ ]]; then
  ROLE_CODEX_EXEC_RESUME=1
fi
if ! [[ "$ROLE_MIN_REFLECTION_PASSES" =~ ^[0-9]+$ ]] || [[ "$ROLE_MIN_REFLECTION_PASSES" -lt 2 ]]; then
  ROLE_MIN_REFLECTION_PASSES=2
fi
THINKING_LEVEL="$(normalize_reasoning_level "$THINKING_LEVEL")"
STALE_SWEEP_THINKING="$(normalize_reasoning_level "$STALE_SWEEP_THINKING")"
DG_ALERT_THINKING="$(normalize_reasoning_level "$DG_ALERT_THINKING")"
if [[ "${ROLE_AGENT_BIN,,}" != "codex" ]]; then
  if [[ "$ROLE_RETRY_ENGINE_DEFAULT" == "sdk" ]]; then
    ROLE_RETRY_ENGINE_DEFAULT="tmux"
  fi
  ROLE_CODEX_EXEC_FALLBACK=0
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
    *) echo "logs-codex-runs/role-runner/$1.live.log" ;;
  esac
}

timeout_seconds_for_role() {
  local role="$1"
  case "$role" in
    architect)
      printf '%s\n' "${PARALLEL_CRON_TIMEOUT_ARCHITECT_SECONDS:-900}"
      ;;
    *)
      printf '%s\n' "$TIMEOUT_SECONDS"
      ;;
  esac
}

thinking_level_for_role() {
  local role="$1"
  local level=""
  case "$role" in
    architect)
      level="${PARALLEL_CRON_THINKING_ARCHITECT:-${LM_USED_ROLE_THINKING:-${MODEL_CONFIG_ROLE_THINKING:-high}}}"
      ;;
    *)
      level="$THINKING_LEVEL"
      ;;
  esac
  normalize_reasoning_level "$level"
}

model_for_role() {
  local role="$1"
  local varname="LM_ROLE_${role^^}_MODEL"
  varname="${varname//-/_}"
  printf '%s\n' "${!varname:-${ROLE_CODEX_MODEL}}"
}

message_for_role() {
  local role="$1"
  local allow_edits="$2"
  local role_model="$3"
  local role_runner_arg="$role"
  if [[ "$role" == "planner" ]]; then
    role_runner_arg="vision-architect-tasks-planner"
  fi
  cat <<EOF
Execute exactly this shell command and return ONLY its stdout, verbatim, no explanation.
Never call send/message/delivery actions.
Command: TMUX_ROLE_AGENT_BIN=${ROLE_AGENT_BIN} TMUX_ROLE_RETRY_ENGINE_DEFAULT=${ROLE_RETRY_ENGINE_DEFAULT} PROMPT_TIMEOUT_SECONDS=${ROLE_PROMPT_TIMEOUT_SECONDS} RETRY_PROMPT_TIMEOUT_SECONDS=${ROLE_RETRY_PROMPT_TIMEOUT_SECONDS} TMUX_ROLE_RECOVERY_THRESHOLD=${ROLE_RECOVERY_THRESHOLD} TMUX_ROLE_NO_DELTA_THRESHOLD=${ROLE_NO_DELTA_THRESHOLD} TMUX_ROLE_STALL_ABORT_SECONDS=${ROLE_STALL_ABORT_SECONDS} SKIP_RETRY_ON_TIMEOUT=${ROLE_SKIP_RETRY_ON_TIMEOUT} TMUX_ROLE_CODEX_EXEC_FALLBACK=${ROLE_CODEX_EXEC_FALLBACK} TMUX_ROLE_CODEX_MODEL=${role_model} TMUX_ROLE_CODEX_EXEC_RESUME=${ROLE_CODEX_EXEC_RESUME} TMUX_ROLE_MIN_REFLECTION_PASSES=${ROLE_MIN_REFLECTION_PASSES} TMUX_ROLE_ALLOW_FILE_EDITS=${allow_edits} bash scripts/cron_tmux_role_runner.sh ${role_runner_arg}
EOF
}

message_for_stale_sweep() {
  cat <<EOF
Execute exactly this shell command and return ONLY its stdout, verbatim, no explanation.
Never call send/message/delivery actions.
Command: STALE_SWEEP_THRESHOLD_SECONDS=${STALE_SWEEP_THRESHOLD_SECONDS} bash scripts/stale_cron_tick.sh
EOF
}

message_for_dg_alert() {
  cat <<EOF
Execute exactly this shell command and return ONLY its stdout, verbatim, no explanation.
Never call send/message/delivery actions.
Command: bash scripts/dg_alert_15m.sh
EOF
}

find_job_id_by_name() {
  local name="$1"
  openclaw cron list --json | jq -r --arg n "$name" '.jobs[]? | select(.name==$n) | .id' | head -n 1
}

disable_job_if_exists() {
  local name="$1"
  local id=""
  id="$(find_job_id_by_name "$name" || true)"
  if [[ "$APPLY" -eq 0 ]]; then
    echo "PLAN legacy_job_disable name=${name} existing_id=${id:-none}"
    return 0
  fi
  if [[ -n "$id" ]]; then
    openclaw cron disable "$id" >/dev/null 2>&1 || true
    echo "APPLIED legacy_job_disable name=${name} id=${id}"
  fi
}

upsert_job() {
  local role="$1"
  local every="$2"
  local allow_edits="$3"
  local desc="$4"
  local role_timeout=""
  local role_thinking=""
  local name=""
  local agent_id=""
  local id=""
  local msg=""
  local role_model=""

  name="$(job_name_for_role "$role")"
  agent_id="$(agent_for_role "$role")"
  role_timeout="$(timeout_seconds_for_role "$role")"
  role_thinking="$(thinking_level_for_role "$role")"
  if [[ -z "$role_thinking" ]]; then
    role_thinking="$THINKING_LEVEL"
  fi
  if ! [[ "$role_timeout" =~ ^[0-9]+$ ]] || [[ "$role_timeout" -lt 60 ]]; then
    role_timeout="$TIMEOUT_SECONDS"
  fi
  role_model="$(model_for_role "$role")"
  msg="$(message_for_role "$role" "$allow_edits" "$role_model")"
  id="$(find_job_id_by_name "$name" || true)"

  if [[ "$APPLY" -eq 0 ]]; then
    echo "PLAN role=${role} name=${name} agent=${agent_id} model=${role_model} every=${every} allow_file_edits=${allow_edits} existing_id=${id:-none}"
    return 0
  fi

  if [[ -n "$id" ]]; then
    openclaw cron edit "$id" \
      --name "$name" \
      --description "$desc" \
      --agent "$agent_id" \
      --every "$every" \
      --thinking "$role_thinking" \
      --model "$role_model" \
      --session isolated \
      --no-deliver \
      --wake now \
      --timeout-seconds "$role_timeout" \
      --message "$msg" >/dev/null
  else
    openclaw cron add \
      --name "$name" \
      --description "$desc" \
      --agent "$agent_id" \
      --every "$every" \
      --thinking "$role_thinking" \
      --model "$role_model" \
      --session isolated \
      --no-deliver \
      --wake now \
      --timeout-seconds "$role_timeout" \
      --message "$msg" >/dev/null
    id="$(find_job_id_by_name "$name" || true)"
  fi

  if [[ "$ENABLE_AFTER_CREATE" -eq 1 && -n "$id" ]]; then
    openclaw cron enable "$id" >/dev/null 2>&1 || true
  fi

  echo "APPLIED role=${role} name=${name} agent=${agent_id} model=${role_model} id=${id:-unknown} every=${every} allow_file_edits=${allow_edits} timeout=${role_timeout} thinking=${role_thinking}"
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
      --model "$ROLE_CODEX_MODEL" \
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
      --model "$ROLE_CODEX_MODEL" \
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

upsert_dg_alert_job() {
  local id=""
  local msg=""
  local desc="Continuous delivery-health digest and auto-escalation hints"
  id="$(find_job_id_by_name "$DG_ALERT_JOB_NAME" || true)"
  msg="$(message_for_dg_alert)"

  if [[ "$ENABLE_DG_ALERT" -eq 0 ]]; then
    if [[ "$APPLY" -eq 0 ]]; then
      echo "PLAN utility=dg_alert name=${DG_ALERT_JOB_NAME} enabled=0 existing_id=${id:-none}"
      return 0
    fi
    if [[ -n "$id" ]]; then
      openclaw cron disable "$id" >/dev/null 2>&1 || true
      echo "APPLIED utility=dg_alert name=${DG_ALERT_JOB_NAME} id=${id} action=disabled"
    else
      echo "APPLIED utility=dg_alert name=${DG_ALERT_JOB_NAME} id=none action=skip_missing"
    fi
    return 0
  fi

  if [[ "$APPLY" -eq 0 ]]; then
    echo "PLAN utility=dg_alert name=${DG_ALERT_JOB_NAME} agent=${DG_ALERT_AGENT} every=${DG_ALERT_EVERY} timeout=${DG_ALERT_TIMEOUT_SECONDS} existing_id=${id:-none}"
    return 0
  fi

  if [[ -n "$id" ]]; then
    openclaw cron edit "$id" \
      --name "$DG_ALERT_JOB_NAME" \
      --description "$desc" \
      --agent "$DG_ALERT_AGENT" \
      --every "$DG_ALERT_EVERY" \
      --thinking "$DG_ALERT_THINKING" \
      --model "$ROLE_CODEX_MODEL" \
      --session isolated \
      --no-deliver \
      --wake now \
      --timeout-seconds "$DG_ALERT_TIMEOUT_SECONDS" \
      --message "$msg" >/dev/null
  else
    openclaw cron add \
      --name "$DG_ALERT_JOB_NAME" \
      --description "$desc" \
      --agent "$DG_ALERT_AGENT" \
      --every "$DG_ALERT_EVERY" \
      --thinking "$DG_ALERT_THINKING" \
      --model "$ROLE_CODEX_MODEL" \
      --session isolated \
      --no-deliver \
      --wake now \
      --timeout-seconds "$DG_ALERT_TIMEOUT_SECONDS" \
      --message "$msg" >/dev/null
    id="$(find_job_id_by_name "$DG_ALERT_JOB_NAME" || true)"
  fi

  if [[ "$ENABLE_AFTER_CREATE" -eq 1 && -n "$id" ]]; then
    openclaw cron enable "$id" >/dev/null 2>&1 || true
  fi
  echo "APPLIED utility=dg_alert name=${DG_ALERT_JOB_NAME} agent=${DG_ALERT_AGENT} id=${id:-unknown} every=${DG_ALERT_EVERY} timeout=${DG_ALERT_TIMEOUT_SECONDS}"
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

# Coordination lanes merged into planner: disable old dedicated loops when present.
disable_job_if_exists "analyst-tmux-loop"
disable_job_if_exists "architect-tmux-loop"
disable_job_if_exists "po-tmux-loop"
disable_job_if_exists "scrum-master-tmux-loop"
disable_job_if_exists "analyst-tmux-14m"
disable_job_if_exists "architect-tmux-25m"
disable_job_if_exists "po-tmux-25m"
disable_job_if_exists "scrum-master-tmux-25m"

upsert_stale_sweep_job
sleep 1
upsert_dg_alert_job
sleep 1

cron_json="$(openclaw cron list --json)"
map_tmp="$(mktemp)"
{
  echo '{'
  echo '  "generatedAtUtc": "'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'",'
  echo '  "thinking": "'"$THINKING_LEVEL"'",'
  echo '  "timeoutSeconds": '"$TIMEOUT_SECONDS"','
  echo '  "minReflectionPasses": '"$ROLE_MIN_REFLECTION_PASSES"','
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
    role_timeout="$(timeout_seconds_for_role "$role")"
    role_thinking="$(thinking_level_for_role "$role")"
    role_model="$(model_for_role "$role")"
    if [[ -z "$role_thinking" ]]; then
      role_thinking="$THINKING_LEVEL"
    fi
    if [[ ! "$role_timeout" =~ ^[0-9]+$ ]] || [[ "$role_timeout" -lt 60 ]]; then
      role_timeout="$TIMEOUT_SECONDS"
    fi
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
      --arg role_thinking "$role_thinking" \
      --arg role_model "$role_model" \
      --argjson role_timeout "$role_timeout" \
      --argjson wip_limit "$wip_limit" \
      --argjson provisioned "$provisioned" \
      --argjson allow_file_edits "$allow_edits" \
      '{role:$role,id:$id,name:$name,agent_id:$agent_id,every:$every,model:$role_model,thinking:$role_thinking,timeout_seconds:$role_timeout,lane:$lane,wip_limit:$wip_limit,allow_file_edits:$allow_file_edits,provisioned:$provisioned,session_name:$session_name,trace_file:$trace_file}'
  done

  echo '  ],'
  echo '  "utility_jobs": ['
  utility_first=1
  stale_id="$(printf '%s' "$cron_json" | jq -r --arg n "$STALE_SWEEP_JOB_NAME" '.jobs[]? | select(.name==$n) | .id' | head -n 1)"
  stale_provisioned=0
  if [[ -n "$stale_id" ]]; then
    stale_provisioned=1
  fi
  if [[ "$ENABLE_STALE_SWEEP" -eq 1 ]]; then
    if [[ "$utility_first" -eq 0 ]]; then
      echo '    ,'
    fi
    utility_first=0
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
  dg_alert_id="$(printf '%s' "$cron_json" | jq -r --arg n "$DG_ALERT_JOB_NAME" '.jobs[]? | select(.name==$n) | .id' | head -n 1)"
  dg_alert_provisioned=0
  if [[ -n "$dg_alert_id" ]]; then
    dg_alert_provisioned=1
  fi
  if [[ "$ENABLE_DG_ALERT" -eq 1 ]]; then
    if [[ "$utility_first" -eq 0 ]]; then
      echo '    ,'
    fi
    utility_first=0
    jq -nc \
      --arg name "$DG_ALERT_JOB_NAME" \
      --arg id "$dg_alert_id" \
      --arg agent_id "$DG_ALERT_AGENT" \
      --arg every "$DG_ALERT_EVERY" \
      --arg thinking "$DG_ALERT_THINKING" \
      --argjson timeout "$DG_ALERT_TIMEOUT_SECONDS" \
      --argjson provisioned "$dg_alert_provisioned" \
      '{name:$name,id:$id,agent_id:$agent_id,every:$every,thinking:$thinking,timeout_seconds:$timeout,provisioned:$provisioned}'
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
