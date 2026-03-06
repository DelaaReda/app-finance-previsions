#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd -P)"
CONFIGS_DIR="${ROOT}/configs"
MODEL_CONFIG_FILE="${ROOT}/platform/config/lm_used_model_config.sh"
if [[ ! -f "$MODEL_CONFIG_FILE" ]]; then
  MODEL_CONFIG_FILE="${CONFIGS_DIR}/model-config.sh"
fi
if [[ -f "$MODEL_CONFIG_FILE" ]]; then
  # shellcheck source=../platform/config/model-config.sh
  source "$MODEL_CONFIG_FILE"
fi

TS="$(date +%Y%m%d-%H%M%S)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="/home/venom/.openclaw/cron/backups"
MODEL="${CRON_MODEL:-${LM_USED_DIRECT_CRON_MODEL:-${MODEL_CONFIG_DIRECT_CRON_MODEL:-${MODEL_CONFIG_ROLE_MODEL:-${LM_USED_ROLE_MODEL}}}}}"
THINKING="${CRON_THINKING:-${LM_USED_DIRECT_CRON_THINKING:-${MODEL_CONFIG_DIRECT_CRON_THINKING:-${MODEL_CONFIG_ROLE_THINKING:-${LM_USED_ROLE_THINKING}}}}}"

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
THINKING="$(normalize_reasoning_level "$THINKING")"

mkdir -p "${BACKUP_DIR}"
cp /home/venom/.openclaw/cron/jobs.json "${BACKUP_DIR}/jobs.${TS}.json"
openclaw cron list --json > "${BACKUP_DIR}/list.${TS}.json"

MSG_PLANNER=$(
cat <<EOF
Contexte: ${WORKDIR}. ROLE=planner-direct.
Methodologie obligatoire: docs/operations/ops/AGENT_WORKFLOW.md + docs/operations/ops/ENGINEERING_PLAYBOOK.md + docs/operations/ops/DIRECT_CRON_METHODOLOGY.md.
Sans dependance qwen_orchestrator.py ni tmux. Commandes shell uniquement via scripts/exec_safe.sh.
Lecture autorisee: docs/orchestrator-ops/priority-queue.json, docs/product/planning/WORKSTATE.md, evidence/gates/openclaw-gates/.
Interdictions: write/edit/git/commit/modification fichiers.
Sortie <=10 lignes: STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
Si aucun changement concret: DELTA: NO_DELTA.
EOF
)

MSG_DEV=$(
cat <<EOF
Contexte: ${WORKDIR}. ROLE=dev-direct.
Methodologie obligatoire: docs/operations/ops/AGENT_WORKFLOW.md + docs/operations/ops/ENGINEERING_PLAYBOOK.md + docs/operations/ops/DIRECT_CRON_METHODOLOGY.md.
Sans dependance qwen_orchestrator.py ni tmux. Toutes commandes via scripts/exec_safe.sh.
Executer: python3 scripts/validate_batch_state.py ; bash scripts/preflight_dispatch.sh ; python3 -m py_compile apps/api/src/platform/main.py ; bash scripts/backend_regression_gate.sh --no-live.
Optionnel: curl -fsS http://127.0.0.1:8050/api/health.
Interdictions: write/edit/git/commit/modification fichiers.
Sortie <=10 lignes: STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
Si aucun changement concret: DELTA: NO_DELTA.
EOF
)

MSG_TESTER=$(
cat <<EOF
Contexte: ${WORKDIR}. ROLE=tester-direct.
Methodologie obligatoire: docs/operations/ops/AGENT_WORKFLOW.md + docs/operations/ops/ENGINEERING_PLAYBOOK.md + docs/operations/ops/DIRECT_CRON_METHODOLOGY.md.
Sans dependance qwen_orchestrator.py ni tmux. Toutes commandes via scripts/exec_safe.sh.
Executer: bash scripts/backend_regression_gate.sh --no-live.
En cas d'echec, fournir le premier test KO et la commande de reproduction exacte.
Interdictions: write/edit/git/commit/modification fichiers.
Sortie <=10 lignes: STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
Si aucun changement concret: DELTA: NO_DELTA.
EOF
)

MSG_QA=$(
cat <<EOF
Contexte: ${WORKDIR}. ROLE=qa-direct.
Methodologie obligatoire: docs/operations/ops/AGENT_WORKFLOW.md + docs/operations/ops/ENGINEERING_PLAYBOOK.md + docs/operations/ops/API_ENDPOINT_BEST_PRACTICES.md + docs/operations/ops/DIRECT_CRON_METHODOLOGY.md.
Sans dependance qwen_orchestrator.py ni tmux. Commandes shell via scripts/exec_safe.sh.
Lecture autorisee: evidence/gates/openclaw-gates, docs/orchestrator-ops/priority-queue.json, docs/orchestrator-ops/parallel-workstreams.json.
Verifier coherence de preuve: VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE, artefacts recents.
Interdictions: write/edit/git/commit/modification fichiers.
Sortie <=10 lignes: STATUS, DELTA, EVIDENCE, RISKS, NEXT, VERDICT, BLOCKER_ID, NEXT_ACTION_UNIQUE.
Si aucun changement concret: DELTA: NO_DELTA.
EOF
)

openclaw cron edit 09d045db-b12a-4486-a743-57b761d52e50 \
  --name "planner-direct-5m" \
  --description "Direct role planner without orchestrator or tmux" \
  --agent "planner" \
  --every 5m --model "${MODEL}" --thinking "${THINKING}" --session isolated --no-deliver --wake now --timeout-seconds 150 \
  --message "${MSG_PLANNER}"

openclaw cron edit dfd61f17-206f-4feb-ab14-6ae4ce54f04c \
  --name "dev-direct-7m" \
  --description "Direct role dev without orchestrator or tmux" \
  --agent "dev" \
  --every 7m --model "${MODEL}" --thinking "${THINKING}" --session isolated --no-deliver --wake now --timeout-seconds 150 \
  --message "${MSG_DEV}"

openclaw cron edit 36bed423-e965-4a19-a43a-c8ffbff751d8 \
  --name "tester-direct-9m" \
  --description "Direct role tester without orchestrator or tmux" \
  --agent "tester" \
  --every 9m --model "${MODEL}" --thinking "${THINKING}" --session isolated --no-deliver --wake now --timeout-seconds 150 \
  --message "${MSG_TESTER}"

openclaw cron edit 454dc361-14bb-4f71-8ca2-ec86708c503f \
  --name "qa-direct-11m" \
  --description "Direct role qa without orchestrator or tmux" \
  --agent "qa" \
  --every 11m --model "${MODEL}" --thinking "${THINKING}" --session isolated --no-deliver --wake now --timeout-seconds 150 \
  --message "${MSG_QA}"

echo "backup_ts=${TS}"
