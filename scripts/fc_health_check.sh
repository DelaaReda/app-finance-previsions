#!/usr/bin/env bash
# ============================================================
# fc_health_check.sh — Dashboard santé du système Finance Copilot
# Usage: bash scripts/fc_health_check.sh
# ============================================================
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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
ACTIVE_ROLES=("planner" "backend_engineer" "frontend_engineer" "data_analyst")
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
for role in "planner" "backend_engineer" "frontend_engineer" "data_analyst"; do
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
[[ "$RATE_HITS" -gt 5 ]] && warn "Rate limit hits today: $RATE_HITS — consider slowing cron intervals" || ok "Rate limit hits today: $RATE_HITS"

echo -e "\n${BOLD}═══════════════════════════════════════════════════${NC}"
echo -e "  Run: ${BLUE}bash scripts/fc_setup_crons.sh${NC} to install/reinstall crons"
echo -e "  Run: ${BLUE}bash scripts/fc_health_check.sh${NC} to re-check"
echo -e "${BOLD}═══════════════════════════════════════════════════${NC}\n"
