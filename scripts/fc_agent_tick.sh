#!/usr/bin/env bash
# ============================================================
# fc_agent_tick.sh — Lance un tick d'agent via cron_tmux_role_runner
# Usage: fc_agent_tick.sh <role>
# Features:
#   - Fallback automatique vers qwen-code si codex est rate-limited
#   - Timeout réduit pour éviter stale locks (360s)
#   - Détection VM resume et kill des sessions stales
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
WORKSPACE_HELPER="${SCRIPT_DIR}/../platform/automation/lib/workspace_paths.sh"
if [[ ! -f "$WORKSPACE_HELPER" ]]; then
  echo "Missing workspace helper: $WORKSPACE_HELPER" >&2
  exit 2
fi
# shellcheck source=/dev/null
source "$WORKSPACE_HELPER"

ROOT="$(fc_prefer_writable_workspace "$(fc_resolve_workspace_root "$SCRIPT_DIR")")"
ROLE="${1:-}"
LOG_DIR="$ROOT/logs-codex-runs/fc-ticks"
LOCK_DIR="/tmp/fc-agent-locks"
# Source config early so qwen fallback path can be overridden in one place.
source "$ROOT/platform/config/lm_used_model_config.sh" 2>/dev/null || true
QWEN_BIN_CANDIDATE="${TMUX_ROLE_QWEN_BIN:-${LM_USED_QWEN_BIN:-${LM_FALLBACK_BIN:-/home/venom/.npm-global/bin/qwen}}}"
QWEN_BIN="$QWEN_BIN_CANDIDATE"
CODEX_RL_CACHE_DIR="${FC_ROLE_STATE_DIR:-${TMUX_ROLE_STATE_DIR:-${HOME}/.openclaw/cron/role-state}}"
CODEX_RL_CACHE_FILE="${CODEX_RL_CACHE_DIR}/codex.rate_limit_gate_cache"
QWEN_RL_CACHE_FILE="${CODEX_RL_CACHE_DIR}/qwen.rate_limit_gate_cache"
# Backoffs réduits: schedules anti-collision évitent la saturation en rafale.
# On borne explicitement pour éviter les valeurs legacy trop longues (ex: 780/900).
ROLE_RATE_LIMIT_BACKOFF_SECONDS="${FC_ROLE_RATE_LIMIT_BACKOFF_SECONDS:-240}"
# Gap de reprise VM: 30 min par défaut (évite kill à chaque tick normal ~22min).
VM_RESUME_KILL_GAP_SECONDS="${FC_VM_RESUME_KILL_GAP_SECONDS:-1800}"
# Timeout global du tick (runner + overhead) avec marge pour éviter rc=124 de bord.
TICK_TIMEOUT_SECONDS="${FC_TICK_TIMEOUT_SECONDS:-540}"

# Assure que qwen est accessible même dans un shell non-login
export PATH="/home/venom/.npm-global/bin:$PATH"

mkdir -p "$LOG_DIR" "$LOCK_DIR"

if [[ -z "$ROLE" ]]; then
  echo "Usage: $0 <role|vision-architect-tasks-planner>" >&2
  exit 1
fi

ROLE_INPUT="$ROLE"
LEGACY_ROLE_ALIAS_MODE="${FC_LEGACY_ROLE_ALIAS_MODE:-skip}"
# === CONSOLIDATION 2026-03-02: 10 rôles → 3 ===
# Tout ce qui était backend_engineer / frontend_engineer / data_analyst → dev
# Tout ce qui était architect / po / scrum_master / analyst → planner
# Tout ce qui était clawsentinel / infra_engineer / qa → admin
case "$ROLE" in
  backend_engineer|frontend_engineer|data_analyst|integrator)
    if [[ "$LEGACY_ROLE_ALIAS_MODE" == "map" ]]; then
      echo "[fc_tick] Role '$ROLE_INPUT' consolidated into 'dev' (legacy alias mode=map)" >&2
      ROLE="dev"
    else
      echo "[fc_tick] Role '$ROLE_INPUT' is legacy; skip tick to avoid lock contention (set FC_LEGACY_ROLE_ALIAS_MODE=map to map)" >&2
      exit 0
    fi
    ;;
  analyst|architect|po|scrum_master|vision-architect-tasks-planner|vision_architect_tasks_planner)
    if [[ "$ROLE" == "vision-architect-tasks-planner" || "$ROLE" == "vision_architect_tasks_planner" ]]; then
      ROLE="planner"
    elif [[ "$LEGACY_ROLE_ALIAS_MODE" == "map" ]]; then
      echo "[fc_tick] Role '$ROLE_INPUT' consolidated into 'planner' (legacy alias mode=map)" >&2
      ROLE="planner"
    else
      echo "[fc_tick] Role '$ROLE_INPUT' is legacy; skip tick to avoid lock contention (set FC_LEGACY_ROLE_ALIAS_MODE=map to map)" >&2
      exit 0
    fi
    ;;
  clawsentinel|infra_engineer|qa|tester)
    if [[ "$LEGACY_ROLE_ALIAS_MODE" == "map" ]]; then
      echo "[fc_tick] Role '$ROLE_INPUT' consolidated into 'admin' (legacy alias mode=map)" >&2
      ROLE="admin"
    else
      echo "[fc_tick] Role '$ROLE_INPUT' is legacy; skip tick to avoid lock contention (set FC_LEGACY_ROLE_ALIAS_MODE=map to map)" >&2
      exit 0
    fi
    ;;
esac

ROLE_RL_CACHE_FILE="${CODEX_RL_CACHE_DIR}/${ROLE}.rate_limit_gate_cache"
ROLE_STATE_CONTRACT_FILE="${CODEX_RL_CACHE_DIR}/${ROLE}.last_contract"

# 3 rôles actifs seulement
case "$ROLE" in
  dev|planner|admin) ;;
  *)
    echo "[fc_tick] Role '$ROLE_INPUT' (canonical=$ROLE) not in active set {dev,planner,admin}, skipping" >&2
    exit 0
    ;;
esac

LOCK="$LOCK_DIR/$ROLE.lock"
LOCK_META="${LOCK}.meta"
LOG="$LOG_DIR/$ROLE.tick.log"
TRILOCK_ORDER="tick>run>memory"
LOCK_ACQUIRED=0
LOCK_MODE="none"
LOCK_ACQUIRED_AT=0
LOCK_DIR_FALLBACK=""

ts() { date '+%Y-%m-%dT%H:%M:%S'; }

meta_field() {
  local key="$1"
  local file="$2"
  [[ -f "$file" ]] || return 1
  sed -n "s/.*${key}=\\([^[:space:]]*\\).*/\\1/p" "$file" | head -n 1
}

release_tick_lock() {
  local rc="${1:-0}"
  local now_epoch hold_s
  now_epoch="$(date +%s)"
  hold_s=0
  if [[ "$LOCK_ACQUIRED_AT" =~ ^[0-9]+$ ]] && [[ "$LOCK_ACQUIRED_AT" -gt 0 ]]; then
    hold_s=$(( now_epoch - LOCK_ACQUIRED_AT ))
    if [[ "$hold_s" -lt 0 ]]; then
      hold_s=0
    fi
  fi
  if [[ "$LOCK_ACQUIRED" == "1" ]]; then
    echo "$(ts) [TRILOCK_RELEASE] layer=tick role=$ROLE mode=$LOCK_MODE hold_s=$hold_s release_reason=exit_rc_${rc}" >> "$LOG"
  fi
  if [[ -n "$LOCK_DIR_FALLBACK" ]]; then
    rmdir "$LOCK_DIR_FALLBACK" >/dev/null 2>&1 || true
  fi
  rm -f "$LOCK_META" >/dev/null 2>&1 || true
}

# Prevent overlap
if command -v flock >/dev/null 2>&1; then
  exec 9>"$LOCK"
  if ! flock -n 9; then
    holder_meta="unknown_holder"
    holder_age_s="unknown"
    if [[ -f "$LOCK_META" ]]; then
      holder_meta="$(tr '\n' ' ' < "$LOCK_META" | tr -s ' ' | cut -c1-220)"
      holder_start_epoch="$(meta_field "start_epoch" "$LOCK_META" || true)"
      if [[ "$holder_start_epoch" =~ ^[0-9]+$ ]]; then
        holder_age_s=$(( $(date +%s) - holder_start_epoch ))
      fi
    fi
    echo "$(ts) [TRILOCK_SKIP] layer=tick role=$ROLE reason=busy lock_file=$LOCK holder_age_s=$holder_age_s holder=$holder_meta" >> "$LOG"
    exit 0
  fi
  LOCK_ACQUIRED=1
  LOCK_MODE="flock"
else
  LOCK_DIR_FALLBACK="${LOCK}.dirlock"
  if ! mkdir "$LOCK_DIR_FALLBACK" 2>/dev/null; then
    echo "$(ts) [TRILOCK_SKIP] layer=tick role=$ROLE reason=busy_dirlock lock_dir=$LOCK_DIR_FALLBACK" >> "$LOG"
    exit 0
  fi
  LOCK_ACQUIRED=1
  LOCK_MODE="dirlock"
fi

LOCK_ACQUIRED_AT="$(date +%s)"
printf 'pid=%s host=%s start_epoch=%s start_utc=%s role=%s layer=tick order=%s lock_file=%s\n' \
  "$$" "${HOSTNAME:-unknown}" "$LOCK_ACQUIRED_AT" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$ROLE" "$TRILOCK_ORDER" "$LOCK" > "$LOCK_META"
echo "$(ts) [TRILOCK_ACQUIRE] layer=tick role=$ROLE mode=$LOCK_MODE lock_file=$LOCK order=$TRILOCK_ORDER" >> "$LOG"
trap 'release_tick_lock $?' EXIT

normalize_seconds() {
  local raw="${1:-}"
  local fallback="$2"
  local min="$3"
  local max="$4"
  if ! [[ "$raw" =~ ^[0-9]+$ ]]; then
    echo "$fallback"
    return 0
  fi
  if (( raw < min )); then
    echo "$fallback"
    return 0
  fi
  if (( raw > max )); then
    echo "$max"
    return 0
  fi
  echo "$raw"
}

resolve_executable() {
  local candidate="${1:-}"
  if [[ -z "$candidate" ]]; then
    return 1
  fi
  if [[ "$candidate" == */* ]]; then
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
    # Cross-env safety: config may carry a VM path while binary exists in PATH.
    local base="${candidate##*/}"
    if [[ -n "$base" ]]; then
      command -v "$base" 2>/dev/null && return 0
    fi
    command -v qwen 2>/dev/null || return 1
    return 0
  fi
  command -v "$candidate" 2>/dev/null || return 1
}

run_with_timeout_portable() {
  local timeout_seconds="$1"
  shift

  if command -v timeout >/dev/null 2>&1; then
    timeout "$timeout_seconds" "$@"
    return $?
  fi

  if command -v gtimeout >/dev/null 2>&1; then
    gtimeout "$timeout_seconds" "$@"
    return $?
  fi

  if command -v python3 >/dev/null 2>&1; then
    python3 - "$timeout_seconds" "$@" <<'PY'
import subprocess
import sys

timeout = int(sys.argv[1])
cmd = sys.argv[2:]

try:
    res = subprocess.run(cmd, timeout=timeout)
    sys.exit(res.returncode)
except subprocess.TimeoutExpired:
    sys.exit(124)
PY
    return $?
  fi

  "$@"
}

refresh_memory_symlinks() {
  local memory_dir="$ROOT/memory"
  local today_utc yesterday_utc
  mkdir -p "$memory_dir"
  today_utc="$(date -u +%F)"
  yesterday_utc="$(date -u -d 'yesterday' +%F 2>/dev/null || true)"
  if [[ -z "$today_utc" ]]; then
    return 0
  fi
  if [[ ! -f "$memory_dir/${today_utc}.md" ]]; then
    printf '# Daily Memory %s\n\n' "$today_utc" > "$memory_dir/${today_utc}.md"
  fi
  ln -sfn "${today_utc}.md" "$memory_dir/today.md"
  if [[ -n "$yesterday_utc" ]]; then
    ln -sfn "${yesterday_utc}.md" "$memory_dir/yesterday.md"
  fi
}

ROLE_RATE_LIMIT_BACKOFF_SECONDS="$(normalize_seconds "$ROLE_RATE_LIMIT_BACKOFF_SECONDS" "240" "60" "240")"
VM_RESUME_KILL_GAP_SECONDS="$(normalize_seconds "$VM_RESUME_KILL_GAP_SECONDS" "1800" "900" "86400")"
TICK_TIMEOUT_SECONDS="$(normalize_seconds "$TICK_TIMEOUT_SECONDS" "540" "300" "900")"

echo "" >> "$LOG"
echo "$(ts) [START] role=$ROLE" >> "$LOG"

# ============================================================
# VM Resume detection
# ============================================================
RESUME_FILE="/tmp/fc_last_tick_$ROLE"
NOW_EPOCH="$(date +%s)"
LAST_EPOCH=0
[[ -f "$RESUME_FILE" ]] && LAST_EPOCH="$(cat "$RESUME_FILE" 2>/dev/null || echo 0)"
echo "$NOW_EPOCH" > "$RESUME_FILE"

GAP=$((NOW_EPOCH - LAST_EPOCH))
SESSION="codex_${ROLE}_cron"
[[ "$ROLE" == "planner" ]] && SESSION="codex_planner_cron"

# If gap is abnormally large, VM likely woke from sleep — kill stale session
if [[ "$LAST_EPOCH" -gt 0 && "$GAP" -gt "$VM_RESUME_KILL_GAP_SECONDS" ]]; then
  echo "$(ts) [RESUME] gap=${GAP}s>${VM_RESUME_KILL_GAP_SECONDS}s, killing stale session $SESSION" >> "$LOG"
  tmux kill-session -t "$SESSION" 2>/dev/null || true
  sleep 1
fi

# ============================================================
# Qwen fallback gate
# Vérifie si codex est rate-limited → bascule vers qwen
# Vérifie aussi si qwen lui-même est rate-limited → skip
# ============================================================
is_rl_cache_active() {
  local cache_file="$1"
  [[ ! -f "$cache_file" ]] && return 1
  local payload until_ts
  payload="$(cat "$cache_file" 2>/dev/null || true)"
  until_ts="${payload%%|*}"
  [[ "$until_ts" =~ ^[0-9]+$ ]] || { rm -f "$cache_file"; return 1; }
  [[ "$(date +%s)" -lt "$until_ts" ]] && return 0
  rm -f "$cache_file"
  return 1
}

cache_reason() {
  local cache_file="$1"
  [[ -f "$cache_file" ]] || { echo "none"; return 0; }
  cat "$cache_file" 2>/dev/null | cut -d'|' -f2 | cut -c1-100
}

set_rl_cache() {
  local cache_file="$1"
  local ttl_seconds="$2"
  local reason="${3:-rate_limit_detected}"
  local until_ts=$(( $(date +%s) + ttl_seconds ))
  printf '%s|%s\n' "$until_ts" "$reason" > "$cache_file"
}

AGENT_MODE="codex"
AGENT_BIN_EFFECTIVE="codex"
CODEX_COOLDOWN_ACTIVE=0
ENABLE_QWEN_FALLBACK="${FC_ENABLE_QWEN_FALLBACK:-0}"

if ! [[ "$ENABLE_QWEN_FALLBACK" =~ ^[01]$ ]]; then
  ENABLE_QWEN_FALLBACK=0
fi

if is_rl_cache_active "$ROLE_RL_CACHE_FILE"; then
  echo "$(ts) [SKIP] role cooldown active (${ROLE_RL_CACHE_FILE}) reason=$(cache_reason "$ROLE_RL_CACHE_FILE")" >> "$LOG"
  exit 0
fi

if is_rl_cache_active "$CODEX_RL_CACHE_FILE"; then
  CODEX_COOLDOWN_ACTIVE=1
fi

if [[ "$CODEX_COOLDOWN_ACTIVE" -eq 1 ]]; then
  RL_REASON="$(cache_reason "$CODEX_RL_CACHE_FILE")"
  if [[ "$ENABLE_QWEN_FALLBACK" != "1" ]]; then
    echo "$(ts) [CODEX_COOLDOWN] codex rate-limited (${RL_REASON}); qwen fallback disabled, keeping codex rate-limit gate" >> "$LOG"
  else
    echo "$(ts) [QWEN_FALLBACK] codex rate-limited (${RL_REASON}), switching to qwen" >> "$LOG"

    if is_rl_cache_active "$QWEN_RL_CACHE_FILE"; then
      echo "$(ts) [SKIP] qwen also rate-limited, skipping tick for $ROLE" >> "$LOG"
      exit 0
    fi

    RESOLVED_QWEN_BIN="$(resolve_executable "$QWEN_BIN" || true)"
    if [[ -z "$RESOLVED_QWEN_BIN" ]]; then
      echo "$(ts) [SKIP] qwen not executable (candidate=$QWEN_BIN), skipping tick" >> "$LOG"
      exit 0
    fi
    QWEN_BIN="$RESOLVED_QWEN_BIN"

    AGENT_MODE="qwen"
    AGENT_BIN_EFFECTIVE="$QWEN_BIN"
    SESSION="qwen_${ROLE}_cron"
    echo "$(ts) [AGENT] using qwen fallback: $QWEN_BIN" >> "$LOG"
  fi
fi

# ============================================================
# Ensure tmux session exists
# ============================================================
LAUNCH_CMD="codex --no-alt-screen"
if [[ "$AGENT_MODE" == "qwen" ]]; then
  LAUNCH_CMD="${QWEN_BIN} --channel CI --approval-mode yolo --chat-recording false -o text"
fi

if ! tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "$(ts) [START_SESSION] $SESSION agent=$AGENT_MODE" >> "$LOG"
  tmux new-session -d -s "$SESSION" -c "$ROOT" \
    "bash -lc 'export PATH=/home/venom/.npm-global/bin:\$PATH; unset NO_COLOR; export TERM=xterm-256color FORCE_COLOR=1; exec $LAUNCH_CMD'"
  sleep 3
fi

# ============================================================
# Source config et lancer le tick
# Timeout global du tick: configurable, marge pour precheck+primary+retry+overhead.
# PROMPT_TIMEOUT_SECONDS=210s pour laisser le temps à un reasoning high sans dépasser budget.
# ============================================================
cd "$ROOT"
source platform/config/lm_used_model_config.sh 2>/dev/null || true
refresh_memory_symlinks

# ------------------------------------------------------------
# Résolution du modèle et du thinking par rôle
# Source unique: platform/config/lm_used_model_config.sh
# LM_ROLE_<ROLE>_MODEL / LM_ROLE_<ROLE>_THINKING
# ------------------------------------------------------------
resolve_role_model() {
  local role="${1:-${ROLE}}"
  local varname="LM_ROLE_${role^^}_MODEL"
  varname="${varname//-/_}"
  printf '%s' "${!varname:-${LM_USED_ROLE_MODEL:-gpt-5.2}}"
}

resolve_role_thinking() {
  local role="${1:-${ROLE}}"
  local varname="LM_ROLE_${role^^}_THINKING"
  varname="${varname//-/_}"
  printf '%s' "${!varname:-${LM_USED_ROLE_THINKING:-high}}"
}

normalize_codex_model() {
  local raw="${1:-gpt-5.2}"
  local stripped="${raw#openai-codex/}"
  case "$stripped" in
    gpt-5.2|gpt-5.3-codex-spark|gpt-5.3-codex)
      printf '%s\n' "$stripped" ;;
    gpt-5.3-spark)
      printf 'gpt-5.3-codex-spark\n' ;;
    qwen)
      printf 'qwen\n' ;;
    *)
      printf 'gpt-5.2\n' ;;
  esac
}

normalize_reasoning_effort() {
  local raw="${1:-high}"
  local normalized
  normalized="$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
  case "$normalized" in
    ""|default|auto|none)
      printf 'high\n' ;;
    xhigh|extra|extra_high|veryhigh|max|maximum)
      printf 'high\n' ;;
    minimal|low|medium|high)
      printf '%s\n' "$normalized" ;;
    *)
      printf 'high\n' ;;
  esac
}

RESOLVED_ROLE_MODEL="$(resolve_role_model "$ROLE")"
RESOLVED_ROLE_THINKING="$(resolve_role_thinking "$ROLE")"
CANDIDATE_ROLE_MODEL="${TMUX_ROLE_CODEX_MODEL:-${RESOLVED_ROLE_MODEL}}"
RAW_ROLE_THINKING="${TMUX_ROLE_CODEX_THINKING:-${RESOLVED_ROLE_THINKING}}"
CANDIDATE_ROLE_THINKING="$(normalize_reasoning_effort "$RAW_ROLE_THINKING")"
SANITIZED_ROLE_MODEL="$(normalize_codex_model "$CANDIDATE_ROLE_MODEL")"

if [[ "$CANDIDATE_ROLE_MODEL" != "$SANITIZED_ROLE_MODEL" ]]; then
  echo "$(ts) [MODEL_GUARD] role=$ROLE model=$CANDIDATE_ROLE_MODEL -> $SANITIZED_ROLE_MODEL" >> "$LOG"
fi
if [[ "$RAW_ROLE_THINKING" != "$CANDIDATE_ROLE_THINKING" ]]; then
  echo "$(ts) [THINKING_GUARD] role=$ROLE thinking=$RAW_ROLE_THINKING -> $CANDIDATE_ROLE_THINKING" >> "$LOG"
fi
echo "$(ts) [MODEL] role=$ROLE model=$SANITIZED_ROLE_MODEL thinking=${CANDIDATE_ROLE_THINKING:-default}" >> "$LOG"
export TMUX_ROLE_CODEX_MODEL="$SANITIZED_ROLE_MODEL"
export TMUX_ROLE_CODEX_THINKING="$CANDIDATE_ROLE_THINKING"
ROLE_RATE_LIMIT_CACHE_TTL_SECONDS="${TMUX_ROLE_RATE_LIMIT_CACHE_TTL_SECONDS:-180}"
ROLE_RATE_LIMIT_CACHE_TTL_SECONDS="$(normalize_seconds "$ROLE_RATE_LIMIT_CACHE_TTL_SECONDS" "180" "60" "180")"
export TMUX_ROLE_RATE_LIMIT_CACHE_TTL_SECONDS="$ROLE_RATE_LIMIT_CACHE_TTL_SECONDS"
ROLE_MIN_REFLECTION_PASSES="${TMUX_ROLE_MIN_REFLECTION_PASSES:-${LM_USED_ROLE_MIN_REFLECTION_PASSES:-2}}"
ROLE_MIN_REFLECTION_PASSES="$(normalize_seconds "$ROLE_MIN_REFLECTION_PASSES" "2" "1" "2")"
export TMUX_ROLE_MIN_REFLECTION_PASSES="$ROLE_MIN_REFLECTION_PASSES"

# Rôles avec qwen comme agent PRIMAIRE (pas fallback — zéro quota codex)
if [[ "$SANITIZED_ROLE_MODEL" == "qwen" ]]; then
  RESOLVED_QWEN_BIN="$(resolve_executable "$QWEN_BIN" || true)"
  if [[ -z "$RESOLVED_QWEN_BIN" ]]; then
    echo "$(ts) [SKIP] qwen primary role=$ROLE but qwen not executable (candidate=$QWEN_BIN)" >> "$LOG"
    exit 0
  fi
  QWEN_BIN="$RESOLVED_QWEN_BIN"
  AGENT_MODE="qwen"
  AGENT_BIN_EFFECTIVE="$QWEN_BIN"
  SESSION="qwen_${ROLE}_cron"
  echo "$(ts) [AGENT] qwen primary (not fallback) role=$ROLE" >> "$LOG"
fi

# Lire allow_file_edits depuis le cron-map pour ce rôle (évite mode read-only incorrect)
CRON_MAP_FILE="$ROOT/docs/operations/orchestrator/parallel-role-cron-map.json"
if [[ -f "$CRON_MAP_FILE" ]]; then
  ALLOW_FILE_EDITS_FROM_MAP=$(python3 -c "
import json,sys
try:
    data=json.load(open(sys.argv[1]))
    for r in data.get(\"roles\",[]):
        if r.get(\"role\")==sys.argv[2]:
            print(int(r.get(\"allow_file_edits\",0)))
            break
    else:
        print(0)
except Exception:
    print(0)
" "$CRON_MAP_FILE" "$ROLE" 2>/dev/null || echo 0)
  export TMUX_ROLE_ALLOW_FILE_EDITS="${ALLOW_FILE_EDITS_FROM_MAP:-0}"
  echo "$(ts) [CONFIG] role=$ROLE allow_file_edits=$TMUX_ROLE_ALLOW_FILE_EDITS" >> "$LOG"
fi
export TMUX_ROLE_AGENT_BIN="$AGENT_BIN_EFFECTIVE"
export TMUX_ROLE_RATE_LIMIT_QWEN_FALLBACK="${TMUX_ROLE_RATE_LIMIT_QWEN_FALLBACK:-$ENABLE_QWEN_FALLBACK}"
# SDK primary : codex exec direct, évite le paste 36KB dans la TUI tmux
export TMUX_ROLE_RETRY_ENGINE_DEFAULT="${TMUX_ROLE_RETRY_ENGINE_DEFAULT:-sdk}"
# Session reuse: économise ~40% de tokens (pas de re-lecture contexte à chaque tick)
export TMUX_ROLE_CODEX_EXEC_RESUME="${TMUX_ROLE_CODEX_EXEC_RESUME:-1}"
# Budget explicite pour limiter rc=124: probe(~10s)+primary(210s)+retry(90s)+overhead.
export PROMPT_TIMEOUT_SECONDS="${PROMPT_TIMEOUT_SECONDS:-210}"
export RETRY_PROMPT_TIMEOUT_SECONDS="${RETRY_PROMPT_TIMEOUT_SECONDS:-90}"
export TMUX_ROLE_STALL_ABORT_SECONDS="${TMUX_ROLE_STALL_ABORT_SECONDS:-80}"

# Role-specific overrides to reduce planner/admin timeout churn on heavy context ticks.
case "$ROLE" in
  planner)
    export TMUX_ROLE_CODEX_MODEL="${FC_PLANNER_MODEL:-gpt-5.3-codex-spark}"
    export PROMPT_TIMEOUT_SECONDS="${FC_PLANNER_PROMPT_TIMEOUT_SECONDS:-300}"
    export RETRY_PROMPT_TIMEOUT_SECONDS="${FC_PLANNER_RETRY_TIMEOUT_SECONDS:-120}"
    export TMUX_ROLE_STALL_ABORT_SECONDS="${FC_PLANNER_STALL_ABORT_SECONDS:-90}"
    TICK_TIMEOUT_SECONDS="$(normalize_seconds "${FC_PLANNER_TICK_TIMEOUT_SECONDS:-420}" "$TICK_TIMEOUT_SECONDS" "300" "900")"
    # Planner: keep resume enabled by default for faster/stabler ticks.
    export TMUX_ROLE_CODEX_EXEC_RESUME="${FC_PLANNER_CODEX_EXEC_RESUME:-1}"
    export TMUX_ROLE_RATE_LIMIT_PRECHECK="${FC_PLANNER_RATE_LIMIT_PRECHECK:-0}"
    export TMUX_ROLE_CODEX_THINKING="${FC_PLANNER_THINKING:-high}"
    export TMUX_ROLE_MIN_REFLECTION_PASSES="${FC_PLANNER_MIN_REFLECTION_PASSES:-1}"
    ;;
  dev)
    export TMUX_ROLE_RATE_LIMIT_PRECHECK="${FC_DEV_RATE_LIMIT_PRECHECK:-0}"
    export TMUX_ROLE_CODEX_EXEC_RESUME="${FC_DEV_CODEX_EXEC_RESUME:-1}"
    export PROMPT_TIMEOUT_SECONDS="${FC_DEV_PROMPT_TIMEOUT_SECONDS:-300}"
    export RETRY_PROMPT_TIMEOUT_SECONDS="${FC_DEV_RETRY_TIMEOUT_SECONDS:-120}"
    TICK_TIMEOUT_SECONDS="$(normalize_seconds "${FC_DEV_TICK_TIMEOUT_SECONDS:-540}" "$TICK_TIMEOUT_SECONDS" "300" "900")"
    export TMUX_ROLE_STALL_ABORT_SECONDS="${FC_DEV_STALL_ABORT_SECONDS:-80}"
    ;;
  admin)
    export TMUX_ROLE_CODEX_MODEL="${FC_ADMIN_MODEL:-gpt-5.3-codex-spark}"
    # Admin defaults slightly raised; final budget remains adaptive in cron_tmux_role_runner.sh
    export PROMPT_TIMEOUT_SECONDS="${FC_ADMIN_PROMPT_TIMEOUT_SECONDS:-360}"
    export RETRY_PROMPT_TIMEOUT_SECONDS="${FC_ADMIN_RETRY_TIMEOUT_SECONDS:-150}"
    export TMUX_ROLE_STALL_ABORT_SECONDS="${FC_ADMIN_STALL_ABORT_SECONDS:-85}"
    TICK_TIMEOUT_SECONDS="$(normalize_seconds "${FC_ADMIN_TICK_TIMEOUT_SECONDS:-540}" "$TICK_TIMEOUT_SECONDS" "300" "900")"
    export TMUX_ROLE_CODEX_EXEC_RESUME="${FC_ADMIN_CODEX_EXEC_RESUME:-1}"
    export TMUX_ROLE_RATE_LIMIT_PRECHECK="${FC_ADMIN_RATE_LIMIT_PRECHECK:-0}"
    export TMUX_ROLE_CODEX_THINKING="${FC_ADMIN_THINKING:-medium}"
    export TMUX_ROLE_MEMORY_PROFILE="${FC_ADMIN_MEMORY_PROFILE:-analysis}"
    export TMUX_ROLE_MEMORY_DAILY_LINES="${FC_ADMIN_MEMORY_DAILY_LINES:-4}"
    export TMUX_ROLE_MEMORY_ROLE_HISTORY_LINES="${FC_ADMIN_MEMORY_ROLE_HISTORY_LINES:-2}"
    export TMUX_ROLE_MEMORY_MAX_LINE_CHARS="${FC_ADMIN_MEMORY_MAX_LINE_CHARS:-120}"
    ;;
esac

FINAL_ROLE_THINKING="$(normalize_reasoning_effort "${TMUX_ROLE_CODEX_THINKING:-$CANDIDATE_ROLE_THINKING}")"
if [[ "${TMUX_ROLE_CODEX_THINKING:-$CANDIDATE_ROLE_THINKING}" != "$FINAL_ROLE_THINKING" ]]; then
  echo "$(ts) [THINKING_GUARD_FINAL] role=$ROLE thinking=${TMUX_ROLE_CODEX_THINKING:-$CANDIDATE_ROLE_THINKING} -> $FINAL_ROLE_THINKING" >> "$LOG"
fi
export TMUX_ROLE_CODEX_THINKING="$FINAL_ROLE_THINKING"

EFFECTIVE_ROLE_MODEL="${TMUX_ROLE_CODEX_MODEL:-$SANITIZED_ROLE_MODEL}"
EFFECTIVE_ROLE_THINKING="${TMUX_ROLE_CODEX_THINKING:-default}"
echo "$(ts) [MODEL_EFFECTIVE] role=$ROLE model=$EFFECTIVE_ROLE_MODEL thinking=$EFFECTIVE_ROLE_THINKING resume=${TMUX_ROLE_CODEX_EXEC_RESUME:-1} precheck=${TMUX_ROLE_RATE_LIMIT_PRECHECK:-1}" >> "$LOG"

echo "$(ts) [TICK] role=$ROLE agent=$AGENT_MODE session=$SESSION timeout=${TICK_TIMEOUT_SECONDS}s" >> "$LOG"

set +e
RESULT="$(run_with_timeout_portable "$TICK_TIMEOUT_SECONDS" bash scripts/cron_tmux_role_runner.sh "$ROLE" 2>&1)"
RC=$?
set -e

echo "$(ts) [END] role=$ROLE agent=$AGENT_MODE rc=$RC" >> "$LOG"

# Log dernière ligne du résultat pour diagnostic rapide
if [[ -n "$RESULT" ]]; then
  # Sanitize: strip non-UTF8 bytes and ANSI codes before writing to log
  LAST_LINE="$(echo "$RESULT" | tail -1 | LC_ALL=C sed 's/[\x80-\xff]/?/g' | sed 's/\x1b\[[0-9;]*[A-Za-z]//g' | cut -c1-160)"
  echo "$(ts) [RESULT_TAIL] $LAST_LINE" >> "$LOG"

  extract_contract_value_from_text() {
    local key="$1"
    local text="$2"
    printf '%s\n' "$text" \
      | tr -d '\r' \
      | sed -n "s/^.*${key}:[[:space:]]*//p" \
      | head -1 \
      | sed 's/[[:space:]]*$//'
  }

  extract_contract_value_from_file() {
    local key="$1"
    local file="$2"
    [[ -f "$file" ]] || return 0
    sed -n "s/^${key}:[[:space:]]*//p" "$file" | head -1 | tr -d '\r' | sed 's/[[:space:]]*$//'
  }

  STATUS_LINE="$(extract_contract_value_from_text "STATUS" "$RESULT")"
  DELTA_LINE="$(extract_contract_value_from_text "DELTA" "$RESULT")"
  VERDICT_LINE="$(extract_contract_value_from_text "VERDICT" "$RESULT")"
  BLOCKER_LINE="$(extract_contract_value_from_text "BLOCKER_ID" "$RESULT")"
  NEXT_ACTION_LINE="$(extract_contract_value_from_text "NEXT_ACTION_UNIQUE" "$RESULT")"
  EVIDENCE_LINE="$(extract_contract_value_from_text "EVIDENCE" "$RESULT")"
  CONTRACT_SOURCE="runner_output"

  # Fallback robustesse: si la sortie runner ne contient pas toutes les clés,
  # relire le contrat persistant du rôle (state_dir) pour garder un log tick utile.
  if [[ -f "$ROLE_STATE_CONTRACT_FILE" ]]; then
    if [[ -z "$STATUS_LINE" ]]; then
      STATUS_LINE="$(extract_contract_value_from_file "STATUS" "$ROLE_STATE_CONTRACT_FILE")"
      CONTRACT_SOURCE="state_file"
    fi
    if [[ -z "$DELTA_LINE" ]]; then
      DELTA_LINE="$(extract_contract_value_from_file "DELTA" "$ROLE_STATE_CONTRACT_FILE")"
      CONTRACT_SOURCE="state_file"
    fi
    if [[ -z "$VERDICT_LINE" ]]; then
      VERDICT_LINE="$(extract_contract_value_from_file "VERDICT" "$ROLE_STATE_CONTRACT_FILE")"
      CONTRACT_SOURCE="state_file"
    fi
    if [[ -z "$BLOCKER_LINE" ]]; then
      BLOCKER_LINE="$(extract_contract_value_from_file "BLOCKER_ID" "$ROLE_STATE_CONTRACT_FILE")"
      CONTRACT_SOURCE="state_file"
    fi
    if [[ -z "$NEXT_ACTION_LINE" ]]; then
      NEXT_ACTION_LINE="$(extract_contract_value_from_file "NEXT_ACTION_UNIQUE" "$ROLE_STATE_CONTRACT_FILE")"
      CONTRACT_SOURCE="state_file"
    fi
    if [[ -z "$EVIDENCE_LINE" ]]; then
      EVIDENCE_LINE="$(extract_contract_value_from_file "EVIDENCE" "$ROLE_STATE_CONTRACT_FILE")"
      CONTRACT_SOURCE="state_file"
    fi
  fi

  if [[ -n "$STATUS_LINE$DELTA_LINE$VERDICT_LINE$BLOCKER_LINE$NEXT_ACTION_LINE" ]]; then
    echo "$(ts) [CONTRACT] source=${CONTRACT_SOURCE} status=$(printf '%s' "${STATUS_LINE:-?}" | cut -c1-20) delta=$(printf '%s' "${DELTA_LINE:-?}" | cut -c1-40) verdict=$(printf '%s' "${VERDICT_LINE:-?}" | cut -c1-16) blocker=$(printf '%s' "${BLOCKER_LINE:-NONE}" | cut -c1-42) next_action=$(printf '%s' "${NEXT_ACTION_LINE:-?}" | cut -c1-90)" >> "$LOG"
  fi

  if [[ -n "$EVIDENCE_LINE" ]]; then
    evidence_get() {
      local key="$1"
      printf '%s\n' "$EVIDENCE_LINE" \
        | tr ';' '\n' \
        | sed -n "s/^[[:space:]]*${key}=//p" \
        | head -1 \
        | sed 's/[[:space:]]*$//'
    }

    TASK_UPDATE="$(evidence_get task_update)"
    STREAM_ID="$(evidence_get stream_id)"
    TASK_ID="$(evidence_get task_id)"
    RUN_NOTE="$(evidence_get run_note)"
    ROOT_CAUSE="$(evidence_get root_cause)"
    FIX_APPLIED="$(evidence_get fix_applied)"
    VERIFY_NOTE="$(evidence_get verify)"
    ISSUE_COUNT="$(evidence_get issue_count)"
    ISSUE_SEVERITY="$(evidence_get issue_severity)"
    ISSUES_LIST="$(evidence_get issues)"

    if [[ -n "$TASK_UPDATE$STREAM_ID$TASK_ID$RUN_NOTE$ROOT_CAUSE$FIX_APPLIED$VERIFY_NOTE$ISSUE_COUNT$ISSUE_SEVERITY$ISSUES_LIST" ]]; then
      echo "$(ts) [ACTION] task_update=$(printf '%s' "${TASK_UPDATE:-?}" | cut -c1-24) stream=$(printf '%s' "${STREAM_ID:-?}" | cut -c1-24) task=$(printf '%s' "${TASK_ID:-?}" | cut -c1-28) issue_count=$(printf '%s' "${ISSUE_COUNT:-?}" | cut -c1-5) issue_severity=$(printf '%s' "${ISSUE_SEVERITY:-?}" | cut -c1-12) issues=$(printf '%s' "${ISSUES_LIST:-?}" | cut -c1-44) run_note=$(printf '%s' "${RUN_NOTE:-?}" | cut -c1-70) root_cause=$(printf '%s' "${ROOT_CAUSE:-?}" | cut -c1-40) fix=$(printf '%s' "${FIX_APPLIED:-?}" | cut -c1-40) verify=$(printf '%s' "${VERIFY_NOTE:-?}" | cut -c1-40)" >> "$LOG"
    fi
  fi
fi

if printf '%s\n' "$RESULT" | rg -qi '(^|[[:space:]])STATUS:[[:space:]]*RATE_LIMIT_SKIP($|[[:space:]])|(^|[[:space:]])DELTA:[[:space:]]*RATE_LIMIT_BACKOFF($|[[:space:]])|(^|[[:space:]])NEXT_ACTION_UNIQUE:[[:space:]]*RATE_LIMIT_[A-Z0-9_]+_WAIT_[A-Z0-9_]+_[0-9]+|(^|[[:space:]])BLOCKER_ID:[[:space:]]*AGENT_RATE_LIMIT_[A-Z0-9_]+' \
  || printf '%s\n' "$RESULT" | rg -qi 'api[[:space:]_-]*rate[[:space:]_-]*limit[[:space:]_-]*reached|api-rate-limit-reached|too many requests|insufficient_quota|quota[[:space:]_-]*(exceeded|exhausted|reached)|((http|status|code|error)[^0-9]{0,8}429([^0-9]|$))|(429[^[:cntrl:]]{0,40}(too many requests|rate[[:space:]_-]*limit|insufficient_quota|quota[[:space:]_-]*(exceeded|exhausted|reached)))'; then
  set_rl_cache "$ROLE_RL_CACHE_FILE" "$ROLE_RATE_LIMIT_BACKOFF_SECONDS" "role_rate_limit_${ROLE}"
  echo "$(ts) [BACKOFF] applied role=${ROLE_RATE_LIMIT_BACKOFF_SECONDS}s due_to=rate_limit" >> "$LOG"
fi
