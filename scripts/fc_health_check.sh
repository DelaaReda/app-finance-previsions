#!/usr/bin/env bash
# ============================================================
# fc_health_check.sh — Dashboard santé du système Finance Copilot
# Usage: bash scripts/fc_health_check.sh
# ============================================================
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_CONFIG_FILE="$ROOT/platform/config/lm_used_model_config.sh"
[[ -f "$MODEL_CONFIG_FILE" ]] || MODEL_CONFIG_FILE="$ROOT/platform/config/model-config.sh"
[[ -f "$MODEL_CONFIG_FILE" ]] && source "$MODEL_CONFIG_FILE" 2>/dev/null || true
# Sourced config can re-enable errexit; keep health check best-effort.
set +e
set +u

GREEN='\033[0;32m' RED='\033[0;31m' YELLOW='\033[1;33m' BLUE='\033[0;34m' NC='\033[0m' BOLD='\033[1m'
ok()   { echo -e "  ${GREEN}✅${NC} $*"; }
warn() { echo -e "  ${YELLOW}⚠️ ${NC} $*"; }
fail() { echo -e "  ${RED}❌${NC} $*"; }
info() { echo -e "  ${BLUE}ℹ️ ${NC} $*"; }

echo -e "${BOLD}═══════════════════════════════════════════════════${NC}"
echo -e "${BOLD}   Finance Copilot — Health Check $(date '+%H:%M:%S')${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════════${NC}"

# ── 1. Backend API ────────────────────────────────────────
echo -e "\n${BOLD}[ Backend API ]${NC}"
HEALTH=$(curl -s --max-time 3 "http://localhost:8050/api/health" 2>/dev/null)
if [[ -n "$HEALTH" ]]; then
  STATUS=$(echo "$HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','?'))" 2>/dev/null)
  FORECASTS_TS=$(echo "$HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('last_updates',{}).get('forecasts','never'))" 2>/dev/null)
  NEWS_TS=$(echo "$HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('last_updates',{}).get('news','never'))" 2>/dev/null)
  if [[ "$STATUS" == "ok" ]]; then
    ok "Backend UP | forecasts: $FORECASTS_TS | news: $NEWS_TS"
  else
    fail "Backend status=$STATUS"
  fi
else
  fail "Backend NOT REACHABLE (port 8050)"
fi

# ── 2. Frontend ────────────────────────────────────────────
echo -e "\n${BOLD}[ Frontend ]${NC}"
FE_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "http://localhost:5173/" 2>/dev/null)
if [[ "$FE_CODE" == "200" ]]; then
  ok "Frontend UP (port 5173) HTTP $FE_CODE"
else
  fail "Frontend DOWN (port 5173) — code=$FE_CODE"
fi

# ── 3. Active API Data ─────────────────────────────────────
echo -e "\n${BOLD}[ Live Data ]${NC}"
FORECASTS=$(curl -s --max-time 3 "http://localhost:8050/api/forecasts?limit=1" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); rows=d.get('data',{}).get('rows',[]); print(len(rows))" 2>/dev/null)
NEWS=$(curl -s --max-time 3 "http://localhost:8050/api/news/feed?limit=1" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); items=d.get('data',{}).get('items',[]); print(len(items))" 2>/dev/null)
[[ "${FORECASTS:-0}" -gt 0 ]] && ok "Forecasts: $FORECASTS available" || fail "Forecasts: none"
[[ "${NEWS:-0}" -gt 0 ]] && ok "News: $NEWS available" || fail "News: none"

# ── 4. Agent Sessions ─────────────────────────────────────
echo -e "\n${BOLD}[ Agent Sessions ]${NC}"
ACTIVE_ROLES=("planner" "dev" "admin")
for role in "${ACTIVE_ROLES[@]}"; do
  SESSION="codex_${role}_cron"
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    CMD=$(tmux display-message -p -t "$SESSION:0.0" "#{pane_current_command}" 2>/dev/null | tr '[:upper:]' '[:lower:]' || echo "?")
    ok "Session $SESSION | pane_cmd=$CMD"
  else
    warn "Session $SESSION — NOT running"
  fi
done

# ── 5. Cron Jobs ──────────────────────────────────────────
echo -e "\n${BOLD}[ Cron Schedule ]${NC}"
CRON_ENTRIES=$(crontab -l 2>/dev/null | grep -v "^#\|^$" | wc -l)
CRON_AGENT=$(crontab -l 2>/dev/null | grep "fc_agent_tick\|cron_tmux_role_runner" | wc -l)
[[ "$CRON_AGENT" -gt 0 ]] && ok "$CRON_AGENT agent tick job(s) in crontab" || fail "No agent tick jobs in crontab! Run: bash scripts/fc_setup_crons.sh"
[[ "$CRON_ENTRIES" -gt 0 ]] && info "Total cron entries: $CRON_ENTRIES"

# ── 6. Recent Agent Deliveries ────────────────────────────
echo -e "\n${BOLD}[ Agent Activity (last 2h) ]${NC}"
TICK_LOG_DIR="$ROOT/logs-codex-runs/fc-ticks"
for role in "planner" "dev" "admin"; do
  LOG="$TICK_LOG_DIR/$role.tick.log"
  if [[ -f "$LOG" ]]; then
    LAST_START=$(grep "\[START\]" "$LOG" 2>/dev/null | tail -1 | cut -d' ' -f1)
    LAST_RC=$(grep "\[END\]" "$LOG" 2>/dev/null | tail -1 | grep -o 'rc=[0-9]*' || echo "rc=?")
    LAST_DELTA=$(grep "DELTA=" "$ROOT/memory/agents/$role.md" 2>/dev/null | tail -1 | grep -o 'DELTA=[A-Z_]*' | head -1 || echo "?")
    if [[ -n "$LAST_START" ]]; then
      [[ "$LAST_RC" == "rc=0" ]] && ok "$role | last_run=$LAST_START $LAST_RC | $LAST_DELTA" || warn "$role | last_run=$LAST_START $LAST_RC | $LAST_DELTA"
    else
      warn "$role | no tick logs yet"
    fi
  else
    warn "$role | no tick log"
  fi
done

# ── 7. Git Progress ───────────────────────────────────────
echo -e "\n${BOLD}[ Git Progress (last 24h) ]${NC}"
cd "$ROOT"
COMMITS=$(git log --oneline --since="24 hours ago" 2>/dev/null | wc -l)
RECENT=$(git log --oneline -3 --since="24 hours ago" 2>/dev/null)
if [[ "$COMMITS" -gt 0 ]]; then
  ok "$COMMITS commit(s) in last 24h"
  echo "$RECENT" | while read -r line; do info "  $line"; done
else
  warn "0 commits in last 24h"
fi

# ── 8. Rate Limits ────────────────────────────────────────
echo -e "\n${BOLD}[ Rate Limits ]${NC}"
RATE_HITS=$(grep -r "rate_limit" logs-codex-runs/role-runner/*.log 2>/dev/null | grep "$(date +%Y-%m-%d)" | wc -l || echo 0)
RATE_HITS="$(printf '%s' "${RATE_HITS:-0}" | tr -d '[:space:]')"
[[ -n "$RATE_HITS" ]] || RATE_HITS=0
[[ "$RATE_HITS" -gt 5 ]] && warn "Rate limit hits today: $RATE_HITS — consider slowing cron intervals" || ok "Rate limit hits today: $RATE_HITS"

# ── 9. Model Config Guard ─────────────────────────────────
echo -e "\n${BOLD}[ Model Config ]${NC}"
ROLE_MODEL_RAW="${TMUX_ROLE_CODEX_MODEL:-${LM_USED_ROLE_MODEL:-openai-codex/gpt-5.2}}"
ROLE_MODEL_NORM="${ROLE_MODEL_RAW#openai-codex/}"
case "$ROLE_MODEL_NORM" in
  gpt-5.2|gpt-5.3-codex-spark)
    ok "Role model configured: openai-codex/${ROLE_MODEL_NORM}"
    ;;
  gpt-5.3-spark)
    warn "Legacy role model detected (${ROLE_MODEL_RAW}) -> should be openai-codex/gpt-5.2"
    ;;
  *)
    warn "Unknown role model (${ROLE_MODEL_RAW}) -> recommend openai-codex/gpt-5.2"
    ;;
esac

# ── 10. Rate Limit Cooldowns ──────────────────────────────
echo -e "\n${BOLD}[ Rate Limit Cooldowns ]${NC}"
RATE_CACHE_DIR="$HOME/.openclaw/cron/role-state"
now_epoch="$(date +%s)"
show_cooldown() {
  local label="$1"
  local cache_file="$2"
  [[ -f "$cache_file" ]] || return 1
  local payload until_ts reason remaining
  payload="$(cat "$cache_file" 2>/dev/null || true)"
  until_ts="${payload%%|*}"
  reason="$(printf '%s' "$payload" | cut -d'|' -f2- | cut -c1-80)"
  [[ "$until_ts" =~ ^[0-9]+$ ]] || return 1
  remaining=$(( until_ts - now_epoch ))
  if [[ "$remaining" -gt 0 ]]; then
    warn "$label cooldown active: ${remaining}s (~$((remaining/60))m) reason=${reason:-none}"
    return 0
  fi
  return 1
}
COOLDOWN_ACTIVE=0
show_cooldown "global" "$RATE_CACHE_DIR/global.rate_limit_gate_cache" && COOLDOWN_ACTIVE=1 || true
for role in planner dev admin; do
  show_cooldown "$role" "$RATE_CACHE_DIR/${role}.rate_limit_gate_cache" && COOLDOWN_ACTIVE=1 || true
done
[[ "$COOLDOWN_ACTIVE" -eq 0 ]] && ok "No active role/global cooldown cache"

# ── 11. Orchestration Signal Quality ───────────────────────
echo -e "\n${BOLD}[ Orchestration Quality ]${NC}"
QUALITY_WINDOW_LINES="${QUALITY_WINDOW_LINES:-600}"
QUALITY_SIGNAL_UNPARSEABLE_WARN="${QUALITY_SIGNAL_UNPARSEABLE_WARN:-10}"
QUALITY_SESSION_NOT_READY_WARN="${QUALITY_SESSION_NOT_READY_WARN:-6}"
QUALITY_CONTRACT_GUARD_WARN="${QUALITY_CONTRACT_GUARD_WARN:-4}"
QUALITY_ROLES=("planner" "dev" "admin")
for n in QUALITY_WINDOW_LINES QUALITY_SIGNAL_UNPARSEABLE_WARN QUALITY_SESSION_NOT_READY_WARN QUALITY_CONTRACT_GUARD_WARN; do
  val="$(printf '%s' "${!n:-}" | tr -d '[:space:]')"
  [[ "$val" =~ ^[0-9]+$ ]] || val=0
  [[ "$val" -gt 0 ]] || val=1
  printf -v "$n" '%s' "$val"
done

collect_quality_window() {
  local out_file="$1"
  local role f
  : > "$out_file"
  QUALITY_WINDOW_FILES=0
  for role in "${QUALITY_ROLES[@]}"; do
    for f in "logs-codex-runs/role-runner/${role}.live.log" "logs-codex-runs/fc-ticks/${role}.tick.log" "logs-codex-runs/fc-ticks/${role}.cron.log"; do
      [[ -f "$f" ]] || continue
      tail -n "$QUALITY_WINDOW_LINES" "$f" >> "$out_file" 2>/dev/null || true
      QUALITY_WINDOW_FILES=$((QUALITY_WINDOW_FILES + 1))
    done
  done
}

count_pat() {
  local payload="$1"
  local pattern="$2"
  local n
  n="$(printf '%s\n' "$payload" | rg -o "$pattern" 2>/dev/null | wc -l || echo 0)"
  n="$(printf '%s' "${n:-0}" | tr -d '[:space:]')"
  [[ -n "$n" ]] || n=0
  printf '%s\n' "$n"
}

count_pat_files() {
  local pattern="$1"
  local role f one
  local n=0
  for role in "${QUALITY_ROLES[@]}"; do
    for f in "logs-codex-runs/role-runner/${role}.live.log" "logs-codex-runs/fc-ticks/${role}.tick.log" "logs-codex-runs/fc-ticks/${role}.cron.log"; do
      [[ -f "$f" ]] || continue
      one="$(rg -o "$pattern" "$f" 2>/dev/null | wc -l || echo 0)"
      one="$(printf '%s' "${one:-0}" | tr -d '[:space:]')"
      [[ -n "$one" ]] || one=0
      n=$((n + one))
    done
  done
  printf '%s\n' "$n"
}

QUALITY_WINDOW_TMP="$(mktemp)"
collect_quality_window "$QUALITY_WINDOW_TMP"
QUALITY_WINDOW_BLOB="$(cat "$QUALITY_WINDOW_TMP")"
rm -f "$QUALITY_WINDOW_TMP"
SIG_UNPARSEABLE="$(count_pat "$QUALITY_WINDOW_BLOB" "signal_unparseable")"
SESSION_NOT_READY="$(count_pat "$QUALITY_WINDOW_BLOB" "session_not_ready")"
CONTRACT_GUARD_BLOCKS="$(count_pat "$QUALITY_WINDOW_BLOB" "contract_guard_")"

SIG_UNPARSEABLE_TOTAL="$(count_pat_files "signal_unparseable")"
SESSION_NOT_READY_TOTAL="$(count_pat_files "session_not_ready")"
CONTRACT_GUARD_TOTAL="$(count_pat_files "contract_guard_")"

[[ "$SIG_UNPARSEABLE" -gt "$QUALITY_SIGNAL_UNPARSEABLE_WARN" ]] && warn "signal_unparseable (window) high: $SIG_UNPARSEABLE > $QUALITY_SIGNAL_UNPARSEABLE_WARN" || ok "signal_unparseable (window): $SIG_UNPARSEABLE"
[[ "$SESSION_NOT_READY" -gt "$QUALITY_SESSION_NOT_READY_WARN" ]] && warn "session_not_ready (window) high: $SESSION_NOT_READY > $QUALITY_SESSION_NOT_READY_WARN" || ok "session_not_ready (window): $SESSION_NOT_READY"
[[ "$CONTRACT_GUARD_BLOCKS" -gt "$QUALITY_CONTRACT_GUARD_WARN" ]] && warn "contract_guard blocks (window) high: $CONTRACT_GUARD_BLOCKS > $QUALITY_CONTRACT_GUARD_WARN" || ok "contract_guard blocks (window): $CONTRACT_GUARD_BLOCKS"
info "quality window: roles=$(IFS=,; echo "${QUALITY_ROLES[*]}") lines_per_file=${QUALITY_WINDOW_LINES} files=${QUALITY_WINDOW_FILES:-0} | totals: signal=${SIG_UNPARSEABLE_TOTAL} session=${SESSION_NOT_READY_TOTAL} guard=${CONTRACT_GUARD_TOTAL}"

# ── 12. Stale Locks ───────────────────────────────────────
echo -e "\n${BOLD}[ Stale Locks ]${NC}"
SHARED_LOCK_DIR="$ROOT/.tmp/openclaw-shared-locks"
ROLE_STATE_DIR="$HOME/.openclaw/cron/role-state"
SHARED_STALE=0
RUN_STALE=0
FC_STALE=0
[[ -d "$SHARED_LOCK_DIR" ]] && SHARED_STALE=$(find "$SHARED_LOCK_DIR" -name '*.lock' -mmin +30 2>/dev/null | wc -l || echo 0)
[[ -d "$ROLE_STATE_DIR" ]] && RUN_STALE=$(find "$ROLE_STATE_DIR" -name '*.run.lock' -mmin +20 2>/dev/null | wc -l || echo 0)
FC_STALE=$(find /tmp/fc-agent-locks -name '*.lock' -mmin +20 2>/dev/null | wc -l || echo 0)
SHARED_STALE="$(printf '%s' "${SHARED_STALE:-0}" | tr -d '[:space:]')"
RUN_STALE="$(printf '%s' "${RUN_STALE:-0}" | tr -d '[:space:]')"
FC_STALE="$(printf '%s' "${FC_STALE:-0}" | tr -d '[:space:]')"
[[ -n "$SHARED_STALE" ]] || SHARED_STALE=0
[[ -n "$RUN_STALE" ]] || RUN_STALE=0
[[ -n "$FC_STALE" ]] || FC_STALE=0
TOTAL_STALE=$(( 10#$SHARED_STALE + 10#$RUN_STALE + 10#$FC_STALE ))
if [[ "$TOTAL_STALE" -gt 0 ]]; then
  warn "stale locks detected: shared=${SHARED_STALE:-0} role_state=${RUN_STALE:-0} fc=${FC_STALE:-0}"
  info "Run: bash scripts/fc_reactivate_guard.sh --audit-only (auto-cleans stale locks)"
else
  ok "No stale locks detected"
fi

echo -e "\n${BOLD}═══════════════════════════════════════════════════${NC}"
echo -e "  Run: ${BLUE}bash scripts/fc_setup_crons.sh${NC} to install/reinstall crons"
echo -e "  Run: ${BLUE}bash scripts/fc_health_check.sh${NC} to re-check"
echo -e "${BOLD}═══════════════════════════════════════════════════${NC}\n"
