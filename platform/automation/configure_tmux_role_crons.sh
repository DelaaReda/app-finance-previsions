#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIGS_DIR="${WORKDIR}/configs"
MODEL_CONFIG_FILE="${WORKDIR}/platform/config/lm_used_model_config.sh"
if [[ ! -f "$MODEL_CONFIG_FILE" ]]; then
  MODEL_CONFIG_FILE="${CONFIGS_DIR}/model-config.sh"
fi
if [[ -f "$MODEL_CONFIG_FILE" ]]; then
  # shellcheck source=../platform/config/lm_used_model_config.sh
  source "$MODEL_CONFIG_FILE"
fi
BACKUP_DIR="/home/venom/.openclaw/cron/backups"
TS="$(date +%Y%m%d-%H%M%S)"
CRON_TIMEOUT_SECONDS="${CRON_TIMEOUT_SECONDS:-900}"
ROLE_PROMPT_TIMEOUT_SECONDS="${ROLE_PROMPT_TIMEOUT_SECONDS:-180}"
ROLE_RETRY_PROMPT_TIMEOUT_SECONDS="${ROLE_RETRY_PROMPT_TIMEOUT_SECONDS:-90}"
ROLE_RECOVERY_THRESHOLD="${ROLE_RECOVERY_THRESHOLD:-2}"
ROLE_SKIP_RETRY_ON_TIMEOUT="${ROLE_SKIP_RETRY_ON_TIMEOUT:-1}"
ROLE_NO_DELTA_THRESHOLD="${ROLE_NO_DELTA_THRESHOLD:-12}"
ROLE_STALL_ABORT_SECONDS="${ROLE_STALL_ABORT_SECONDS:-75}"
ROLE_AGENT_BIN="${ROLE_AGENT_BIN:-codex}"
ROLE_RETRY_ENGINE_DEFAULT="${ROLE_RETRY_ENGINE_DEFAULT:-sdk}"
ROLE_CODEX_EXEC_FALLBACK="${ROLE_CODEX_EXEC_FALLBACK:-1}"
ROLE_CODEX_MODEL="${ROLE_CODEX_MODEL:-${LM_USED_ROLE_MODEL:-${MODEL_CONFIG_ROLE_MODEL:-${MODEL_CONFIG_PARALLEL_ROLE_MODEL}}}}"
ROLE_THINKING="${ROLE_THINKING:-${LM_USED_ROLE_THINKING:-${MODEL_CONFIG_ROLE_THINKING:-${MODEL_CONFIG_PARALLEL_ROLE_THINKING}}}}"
ROLE_CODEX_EXEC_RESUME="${ROLE_CODEX_EXEC_RESUME:-1}"
ROLE_MIN_REFLECTION_PASSES="${ROLE_MIN_REFLECTION_PASSES:-${LM_USED_ROLE_MIN_REFLECTION_PASSES:-${MODEL_CONFIG_PARALLEL_ROLE_MIN_REFLECTION_PASSES:-5}}}"
ROLE_ALLOW_FILE_EDITS="${ROLE_ALLOW_FILE_EDITS:-auto}"
ADMIN_LOCK_SCRIPT="${OPENCLAW_CRON_ADMIN_LOCK_SCRIPT:-${WORKDIR}/scripts/cron_admin_lock.sh}"

if ! [[ "${CRON_TIMEOUT_SECONDS}" =~ ^[0-9]+$ ]] || [[ "${CRON_TIMEOUT_SECONDS}" -lt 300 ]]; then
  CRON_TIMEOUT_SECONDS=900
fi
if ! [[ "${ROLE_PROMPT_TIMEOUT_SECONDS}" =~ ^[0-9]+$ ]] || [[ "${ROLE_PROMPT_TIMEOUT_SECONDS}" -lt 90 ]]; then
  ROLE_PROMPT_TIMEOUT_SECONDS=180
fi
if ! [[ "${ROLE_RETRY_PROMPT_TIMEOUT_SECONDS}" =~ ^[0-9]+$ ]] || [[ "${ROLE_RETRY_PROMPT_TIMEOUT_SECONDS}" -lt 45 ]]; then
  ROLE_RETRY_PROMPT_TIMEOUT_SECONDS=90
fi
if ! [[ "${ROLE_RECOVERY_THRESHOLD}" =~ ^[0-9]+$ ]] || [[ "${ROLE_RECOVERY_THRESHOLD}" -lt 1 ]]; then
  ROLE_RECOVERY_THRESHOLD=2
fi
if ! [[ "${ROLE_SKIP_RETRY_ON_TIMEOUT}" =~ ^[01]$ ]]; then
  ROLE_SKIP_RETRY_ON_TIMEOUT=1
fi
if ! [[ "${ROLE_NO_DELTA_THRESHOLD}" =~ ^[0-9]+$ ]] || [[ "${ROLE_NO_DELTA_THRESHOLD}" -lt 1 ]]; then
  ROLE_NO_DELTA_THRESHOLD=12
fi
if ! [[ "${ROLE_STALL_ABORT_SECONDS}" =~ ^[0-9]+$ ]]; then
  ROLE_STALL_ABORT_SECONDS=75
fi
if [[ "${ROLE_RETRY_ENGINE_DEFAULT}" != "tmux" && "${ROLE_RETRY_ENGINE_DEFAULT}" != "sdk" ]]; then
  ROLE_RETRY_ENGINE_DEFAULT="sdk"
fi
if ! [[ "${ROLE_CODEX_EXEC_FALLBACK}" =~ ^[01]$ ]]; then
  ROLE_CODEX_EXEC_FALLBACK=1
fi
if ! [[ "${ROLE_CODEX_EXEC_RESUME}" =~ ^[01]$ ]]; then
  ROLE_CODEX_EXEC_RESUME=1
fi
if ! [[ "${ROLE_MIN_REFLECTION_PASSES}" =~ ^[0-9]+$ ]] || [[ "${ROLE_MIN_REFLECTION_PASSES}" -lt 5 ]]; then
  ROLE_MIN_REFLECTION_PASSES=5
fi

with_admin_lock() {
  if [[ -x "${ADMIN_LOCK_SCRIPT}" ]]; then
    "${ADMIN_LOCK_SCRIPT}" -- "$@"
  else
    "$@"
  fi
}

mkdir -p "${BACKUP_DIR}"
cp /home/venom/.openclaw/cron/jobs.json "${BACKUP_DIR}/jobs.${TS}.json"
with_admin_lock openclaw cron list --json > "${BACKUP_DIR}/list.${TS}.json"

msg_for_role() {
  local role="$1"
  cat <<EOF
Execute exactly this shell command and return ONLY its stdout, verbatim, no explanation.
Never call send/message/delivery actions.
Command: TMUX_ROLE_AGENT_BIN=${ROLE_AGENT_BIN} TMUX_ROLE_RETRY_ENGINE_DEFAULT=${ROLE_RETRY_ENGINE_DEFAULT} PROMPT_TIMEOUT_SECONDS=${ROLE_PROMPT_TIMEOUT_SECONDS} RETRY_PROMPT_TIMEOUT_SECONDS=${ROLE_RETRY_PROMPT_TIMEOUT_SECONDS} TMUX_ROLE_RECOVERY_THRESHOLD=${ROLE_RECOVERY_THRESHOLD} TMUX_ROLE_NO_DELTA_THRESHOLD=${ROLE_NO_DELTA_THRESHOLD} TMUX_ROLE_STALL_ABORT_SECONDS=${ROLE_STALL_ABORT_SECONDS} SKIP_RETRY_ON_TIMEOUT=${ROLE_SKIP_RETRY_ON_TIMEOUT} TMUX_ROLE_CODEX_EXEC_FALLBACK=${ROLE_CODEX_EXEC_FALLBACK} TMUX_ROLE_CODEX_MODEL=${ROLE_CODEX_MODEL} TMUX_ROLE_CODEX_EXEC_RESUME=${ROLE_CODEX_EXEC_RESUME} TMUX_ROLE_MIN_REFLECTION_PASSES=${ROLE_MIN_REFLECTION_PASSES} TMUX_ROLE_ALLOW_FILE_EDITS=${ROLE_ALLOW_FILE_EDITS} bash scripts/cron_tmux_role_runner.sh ${role}
EOF
}

agent_for_role() {
  printf '%s' "$1" | tr '-' '_'
}

upsert_existing() {
  local id="$1"
  local name="$2"
  local every="$3"
  local role="$4"
  local description="$5"
  local agent_id
  local msg
  agent_id="$(agent_for_role "${role}")"
  msg="$(msg_for_role "${role}")"
  with_admin_lock openclaw cron edit "${id}" \
    --name "${name}" \
    --description "${description}" \
    --agent "${agent_id}" \
    --every "${every}" \
    --model "${ROLE_CODEX_MODEL}" \
    --thinking "$ROLE_THINKING" \
    --session isolated \
    --no-deliver \
    --wake now \
    --timeout-seconds "${CRON_TIMEOUT_SECONDS}" \
    --message "${msg}"
}

find_job_id_by_name() {
  local name="$1"
  with_admin_lock openclaw cron list --json | jq -r --arg n "${name}" '.jobs[] | select(.name==$n) | .id' | head -n 1
}

upsert_by_name() {
  local name="$1"
  local every="$2"
  local role="$3"
  local description="$4"
  local agent_id
  local id
  local msg
  agent_id="$(agent_for_role "${role}")"
  msg="$(msg_for_role "${role}")"
  id="$(find_job_id_by_name "${name}" || true)"
  if [[ -n "${id}" ]]; then
    with_admin_lock openclaw cron edit "${id}" \
      --name "${name}" \
      --description "${description}" \
      --agent "${agent_id}" \
      --every "${every}" \
      --model "${ROLE_CODEX_MODEL}" \
      --thinking "$ROLE_THINKING" \
      --session isolated \
      --no-deliver \
      --wake now \
      --timeout-seconds "${CRON_TIMEOUT_SECONDS}" \
      --message "${msg}"
  else
    with_admin_lock openclaw cron add \
      --name "${name}" \
      --description "${description}" \
      --agent "${agent_id}" \
      --every "${every}" \
      --model "${ROLE_CODEX_MODEL}" \
      --thinking "$ROLE_THINKING" \
      --session isolated \
      --no-deliver \
      --wake now \
      --timeout-seconds "${CRON_TIMEOUT_SECONDS}" \
      --message "${msg}"
  fi
}

# Reuse existing IDs for all roles to avoid orphaned schedules and keep audit continuity.
# Rebalanced cadence to reduce cron lane pressure while keeping role continuity.
upsert_existing "09d045db-b12a-4486-a743-57b761d52e50" "planner-tmux-12m" "12m" "planner" "Planner tmux context loop (rebalanced cadence)"
sleep 8
upsert_existing "dfd61f17-206f-4feb-ab14-6ae4ce54f04c" "dev-tmux-15m" "15m" "dev" "Dev tmux context loop (rebalanced cadence)"
sleep 8
upsert_existing "36bed423-e965-4a19-a43a-c8ffbff751d8" "tester-tmux-15m" "15m" "tester" "Tester tmux context loop (rebalanced cadence)"
sleep 8
upsert_existing "454dc361-14bb-4f71-8ca2-ec86708c503f" "qa-tmux-20m" "20m" "qa" "QA tmux context loop (rebalanced cadence)"
sleep 8
upsert_existing "bde5885a-388f-4fe4-a8b7-a146521d9e9d" "architect-tmux-25m" "25m" "architect" "Architect tmux context loop (rebalanced cadence)"
sleep 8
upsert_existing "25756cb4-57f1-41c7-83d4-66fd67a0164d" "clawsentinel-tmux-25m" "25m" "clawsentinel" "ClawSentinel safety/quality tmux loop (rebalanced cadence)"

echo "backup_ts=${TS}"
