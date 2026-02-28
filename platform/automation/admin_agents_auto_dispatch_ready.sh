#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/venom/analyse-financiere"
cd "$ROOT"

STATE_DIR="${ADMIN_AGENTS_AUTO_DISPATCH_STATE_DIR:-$HOME/.openclaw/cron/admin-state}"
LOCK_FILE="$STATE_DIR/admin-agents-auto-dispatch.lock"
FINGERPRINT_FILE="$STATE_DIR/admin-agents-auto-dispatch.fingerprint"
CHAT_FILE="${ADMIN_AGENTS_CHAT_FILE:-docs/ops/ADMIN_TEAM_CHAT.md}"
QUEUE_FILE="${ADMIN_AGENTS_PRIORITY_QUEUE_FILE:-docs/orchestrator-ops/priority-queue.json}"
BOARD_FILE="${ADMIN_AGENTS_WORKBOARD_FILE:-docs/orchestrator-ops/parallel-workstreams.json}"

mkdir -p "$STATE_DIR"

CHANGE_PLAN="Vérifier la tâche; confirmer objectifs métier; valider dépendances; implémenter la solution minimale; vérifier tests; documenter résultat."
ARCH_CHECKS="Forecast-first API->UI; contrat stable avant refacto; observabilité minimale; dépendances cohérentes."

now_local="$(TZ=America/New_York date '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null || date '+%Y-%m-%d %H:%M:%S %Z')"

log_chat() {
  local type="$1"; shift
  local msg="$*"
  [[ -f "$CHAT_FILE" ]] || return 0
  printf -- "- [%s] [admin-agents] TYPE: %s MSG: %s\n" "$now_local" "$type" "$msg" >> "$CHAT_FILE"
}

# lock to prevent concurrent dispatch
if command -v flock >/dev/null 2>&1; then
  exec 9>"$LOCK_FILE"
  if ! flock -n 9; then
    echo "AUTO_DISPATCH status=NOOP reason=locked"
    exit 0
  fi
fi

# Read READY items
if [[ ! -f "$QUEUE_FILE" ]]; then
  echo "AUTO_DISPATCH status=NOOP reason=queue_missing"
  exit 0
fi

ready_ids="$(jq -r '[.items[]? | select((.state//"")=="READY") | (.id//"")] | map(select(length>0)) | unique | .[]' "$QUEUE_FILE" 2>/dev/null || true)"
ready_count="$(printf '%s\n' "$ready_ids" | sed '/^$/d' | wc -l | tr -d ' ')"

if [[ "$ready_count" -eq 0 ]]; then
  echo "AUTO_DISPATCH status=NOOP reason=no_ready"
  exit 0
fi

if [[ "$ready_count" -gt 1 ]]; then
  # refuse to auto-dispatch multiple ready items
  log_chat "ALERT" "exec_issue=QUEUE_MULTI_READY; evidence=${QUEUE_FILE}; impact=delivery; suggestion=prioriser_1_item_ready_manuellement"
  echo "AUTO_DISPATCH status=BLOCKED reason=multi_ready count=$ready_count"
  exit 0
fi

ready_id="$(printf '%s\n' "$ready_ids" | head -n 1)"

# Safety: only allow BATCH-* auto-dispatch for now
if [[ ! "$ready_id" =~ ^BATCH-[0-9]+$ ]]; then
  echo "AUTO_DISPATCH status=NOOP reason=ready_id_not_batch id=$ready_id"
  exit 0
fi

# Preflight gate
if ! bash scripts/preflight_dispatch.sh >/tmp/preflight_dispatch.out 2>/tmp/preflight_dispatch.err; then
  log_chat "ALERT" "exec_issue=DISPATCH_PREFLIGHT_BLOCKED; scope=${ready_id}; evidence=scripts/preflight_dispatch.sh; impact=delivery; suggestion=fix_preflight_then_retry"
  echo "AUTO_DISPATCH status=BLOCKED reason=preflight_failed id=$ready_id"
  exit 0
fi

# Ensure board exists / synced
if [[ ! -f "$BOARD_FILE" ]]; then
  python3 scripts/parallel_workstream.py sync-priority >/dev/null 2>&1 || true
fi

# Collect READY tasks for this batch with empty assignee
if [[ ! -f "$BOARD_FILE" ]]; then
  log_chat "ALERT" "exec_issue=WORKBOARD_MISSING; scope=${ready_id}; evidence=${BOARD_FILE}; impact=delivery; suggestion=parallel_workstream_sync_priority"
  echo "AUTO_DISPATCH status=BLOCKED reason=board_missing id=$ready_id"
  exit 0
fi

mapfile -t tasks < <(jq -r --arg pref "${ready_id}-" '.tasks[] | select(.state=="READY") | select((.id//"")|startswith($pref)) | select((.assignee//"")=="") | "\(.role)\t\(.id)"' "$BOARD_FILE" 2>/dev/null || true)

if [[ "${#tasks[@]}" -eq 0 ]]; then
  echo "AUTO_DISPATCH status=NOOP reason=no_unassigned_ready_tasks id=$ready_id"
  exit 0
fi

fingerprint="${ready_id}|$(printf '%s|' "${tasks[@]}" | tr '\n' ' ' | tr -s ' ' | cut -c1-600)"
last_fp="$(cat "$FINGERPRINT_FILE" 2>/dev/null || true)"
if [[ -n "$last_fp" && "$last_fp" == "$fingerprint" ]]; then
  echo "AUTO_DISPATCH status=NOOP reason=same_fingerprint id=$ready_id"
  exit 0
fi
printf '%s\n' "$fingerprint" > "$FINGERPRINT_FILE"

claimed=()
failed=()

for row in "${tasks[@]}"; do
  role="${row%%$'\t'*}"
  task_id="${row##*$'\t'}"
  # Attempt claim (idempotent-ish)
  if python3 scripts/parallel_workstream.py claim \
    --role "$role" \
    --task "$task_id" \
    --change-plan "$CHANGE_PLAN" \
    --architecture-checks "$ARCH_CHECKS" \
    >/tmp/auto_claim.out 2>/tmp/auto_claim.err; then
    claimed+=("${task_id}:${role}")
  else
    # If already claimed/race, treat as non-fatal
    failed+=("${task_id}:${role}")
  fi
done

if [[ "${#claimed[@]}" -gt 0 ]]; then
  log_chat "INFO" "auto_dispatch id=${ready_id}; claimed=$(IFS=,; echo "${claimed[*]}") ; failed=$(IFS=,; echo "${failed[*]:-none}")"
  echo "AUTO_DISPATCH status=OK id=$ready_id claimed=${#claimed[@]} failed=${#failed[@]}"
else
  log_chat "ALERT" "exec_issue=DISPATCH_CLAIM_FAILED; scope=${ready_id}; evidence=${BOARD_FILE}; impact=delivery; suggestion=claim_manuel_ou_verifier_locks"
  echo "AUTO_DISPATCH status=WARN id=$ready_id claimed=0 failed=${#failed[@]}"
fi
