#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/venom/analyse-financiere"
STATE_DIR="${DG_MONITOR_STATE_DIR:-$HOME/.openclaw/state/dg_monitor}"
mkdir -p "$STATE_DIR"

cd "$ROOT"

# 1) Refresh a current baseline view (fast, deterministic)
line="$(bash scripts/dg_monitor_tick.sh | head -n 1 || true)"
if [[ -z "$line" ]]; then
  echo "DG15 ALERT: monitor tick produced no output"
  exit 0
fi

# 2) Extract fields from the baseline
cron_error_jobs="$(printf '%s' "$line" | sed -n 's/.* error=\([0-9][0-9]*\).*/\1/p' | head -n1)"
unhealthy="$(printf '%s' "$line" | sed -n 's/.* unhealthy=\([^ ]*\).*/\1/p' | head -n1)"
cron_mgr="$(printf '%s' "$line" | sed -n 's/.* cron_mgr="\([^"]*\)".*/\1/p' | head -n1)"
app="$(printf '%s' "$line" | sed -n 's/.* app="\([^"]*\)".*/\1/p' | head -n1)"

ts_local="$(TZ=America/New_York date '+%Y-%m-%d %H:%M %Z')"

# 3) Targeted file reads (inspired by other admin/role crons)

# Priority queue (what is READY/BLOCKED right now)
queue_ready=""
queue_blocked=""
if [[ -f docs/orchestrator-ops/priority-queue.json ]]; then
  queue_ready="$(jq -r '[.items[]? | select((.state//"")=="READY") | (.id//"")] | map(select(length>0)) | join(",")' docs/orchestrator-ops/priority-queue.json 2>/dev/null || true)"
  queue_blocked="$(jq -r '[.items[]? | select((.state//"")=="BLOCKED") | (.id//"")] | map(select(length>0)) | join(",")' docs/orchestrator-ops/priority-queue.json 2>/dev/null || true)"
fi
[[ -n "$queue_ready" ]] || queue_ready="none"
[[ -n "$queue_blocked" ]] || queue_blocked="none"

# Role blockers from role-state (source of truth when tmux logs are noisy)
role_blockers=""
role_blockers_issue=0
for r in planner dev tester qa; do
  f="$HOME/.openclaw/cron/role-state/${r}.last_contract"
  b="NONE"
  if [[ -f "$f" ]]; then
    b="$(sed -n 's/^BLOCKER_ID:[[:space:]]*//p' "$f" | tail -n 1 | tr -d '\r' | sed 's/[[:space:]]*$//' )"
  fi
  [[ -n "$b" ]] || b="UNKNOWN"
  if [[ "$b" != "NONE" ]]; then
    role_blockers_issue=1
  fi
  if [[ -z "$role_blockers" ]]; then
    role_blockers="${r}:${b}"
  else
    role_blockers+=" ${r}:${b}"
  fi
done

# Latest OpenClaw gate verdict (batch gate artifacts)
gate_latest="none"
if ls finance-app/openclaw-gates/*.md >/dev/null 2>&1; then
  gate_file="$(ls -1t finance-app/openclaw-gates/*.md 2>/dev/null | head -n 1 || true)"
  if [[ -n "$gate_file" ]]; then
    gate_verdict="$(rg -n '^VERDICT:' "$gate_file" | head -n 1 | sed 's/^.*VERDICT:[[:space:]]*//' | tr -d '\r' | sed 's/[[:space:]]*$//' )"
    gate_latest="$(basename "$gate_file" | sed 's/\.md$//' ):${gate_verdict:-UNKNOWN}"
  fi
fi

# Parallel workstreams board (high-level state)
ws_summary="unknown"
if [[ -f docs/orchestrator-ops/parallel-workstreams.json ]]; then
  ws_summary="$(jq -r '[.tasks[]?.state] | group_by(.) | map("\(.[0]):\(length)") | join(" ")' docs/orchestrator-ops/parallel-workstreams.json 2>/dev/null || echo unknown)"
  [[ -n "$ws_summary" ]] || ws_summary="unknown"
fi

# Tri-admin chat tail (latest intent/blocker)
chat_tail=""
if [[ -f docs/ops/ADMIN_TEAM_CHAT.md ]]; then
  chat_tail="$(tail -n 2 docs/ops/ADMIN_TEAM_CHAT.md | tr '\n' ' ' | sed 's/  */ /g' | sed 's/[[:space:]]*$//')"
fi
[[ -n "$chat_tail" ]] || chat_tail="(no_chat_tail)"

# Watchdog tail (operational risk notes)
watch_tail=""
if [[ -f docs/orchestrator-ops/agent-watchdog.md ]]; then
  watch_tail="$(tail -n 1 docs/orchestrator-ops/agent-watchdog.md | tr -d '\r' | sed 's/[[:space:]]*$//')"
fi
[[ -n "$watch_tail" ]] || watch_tail="(no_watchdog_tail)"

# 4) Detect important problems
important=0
reasons=()

if [[ -n "$cron_error_jobs" && "$cron_error_jobs" != "0" ]]; then
  important=1
  reasons+=("cron_error=${cron_error_jobs}")
fi

if [[ -n "$unhealthy" && "$unhealthy" != "none" ]]; then
  important=1
  reasons+=("unhealthy=${unhealthy}")
fi

if printf '%s' "$app" | rg -qi 'Backend.*(ARRET|DOWN|STOP|KO)'; then
  important=1
  reasons+=("backend_down")
fi

if [[ "$role_blockers_issue" -eq 1 ]]; then
  important=1
  reasons+=("role_blockers")
fi

# 5) Update memory every 15m (with file lock)
mem_file="memory/$(date +%F).md"
mkdir -p memory
if [[ ! -f "$mem_file" ]]; then
  printf '# %s\n\n' "$(date +%F)" > "$mem_file"
fi

lock_file="$STATE_DIR/memory.lock"
if command -v flock >/dev/null 2>&1; then
  {
    exec 9>"$lock_file"
    flock -x 9
    printf -- "- [%s] DG15 tick: app=\"%s\" errors=%s unhealthy=%s ready=%s blocked=%s roles=[%s] gate=%s workstreams=\"%s\"\n" \
      "$ts_local" "$app" "${cron_error_jobs:-?}" "${unhealthy:-?}" "$queue_ready" "$queue_blocked" "$role_blockers" "$gate_latest" "$ws_summary" >> "$mem_file"
  } || true
else
  printf -- "- [%s] DG15 tick: app=\"%s\" errors=%s unhealthy=%s ready=%s blocked=%s roles=[%s] gate=%s workstreams=\"%s\"\n" \
    "$ts_local" "$app" "${cron_error_jobs:-?}" "${unhealthy:-?}" "$queue_ready" "$queue_blocked" "$role_blockers" "$gate_latest" "$ws_summary" >> "$mem_file"
fi

# 6) Output for delivery (compact)
if [[ "$important" -eq 1 ]]; then
  reason_txt="$(IFS=,; echo "${reasons[*]}")"
  echo "DG15 ALERT ($ts_local): $reason_txt | gate=$gate_latest | ready=$queue_ready | blocked=$queue_blocked | roles=[$role_blockers] | unhealthy=$unhealthy | app=$app"
  echo "TRIAGE: $(bash scripts/triage_now.sh | sed -n 's/^TOP //p' | head -n 1)"
  echo "WORK: $ws_summary"
  echo "CHAT: $chat_tail"
  echo "WATCH: $watch_tail"
else
  echo "DG15 OK ($ts_local): gate=$gate_latest | ready=$queue_ready | blocked=$queue_blocked | roles=[$role_blockers] | app=$app"
fi
