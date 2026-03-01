#!/usr/bin/env bash
# ============================================================
# agent_health.sh — Tableau de bord santé agents en temps réel
# Usage: bash scripts/agent_health.sh [--watch]
# ============================================================
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BOLD='\033[1m'; RED='\033[31m'; GREEN='\033[32m'; YELLOW='\033[33m'; BLUE='\033[34m'; CYAN='\033[36m'; NC='\033[0m'

show_health() {
  clear
  echo -e "${BOLD}${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
  echo -e "${BOLD}${BLUE}║         FINANCE COPILOT — AGENT HEALTH DASHBOARD         ║${NC}"
  echo -e "${BOLD}${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
  echo "  $(date '+%Y-%m-%d %H:%M:%S')"
  echo ""

  # === SERVICES ===
  echo -e "${BOLD}SERVICES${NC}"
  backend_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8050/api/health" 2>/dev/null || echo "000")
  frontend_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:5173/" 2>/dev/null || echo "000")
  [[ "$backend_status" == "200" ]] && echo -e "  Backend  (8050): ${GREEN}● UP${NC}" || echo -e "  Backend  (8050): ${RED}● DOWN (HTTP $backend_status)${NC}"
  [[ "$frontend_status" == "200" ]] && echo -e "  Frontend (5173): ${GREEN}● UP${NC}" || echo -e "  Frontend (5173): ${RED}● DOWN (HTTP $frontend_status)${NC}"
  
  # Check browser  
  browser_running=$(openclaw browser status 2>/dev/null | grep "running: true" | wc -l)
  [[ "$browser_running" -gt 0 ]] && echo -e "  Browser  (CDP):  ${GREEN}● RUNNING${NC}" || echo -e "  Browser  (CDP):  ${YELLOW}● STOPPED${NC}"
  echo ""

  # === TMUX SESSIONS ===
  echo -e "${BOLD}AGENT SESSIONS${NC}"
  sessions=$(tmux ls 2>/dev/null || echo "")
  if [[ -z "$sessions" ]]; then
    echo -e "  ${RED}No active sessions${NC}"
  else
    while IFS= read -r line; do
      session=$(echo "$line" | cut -d: -f1)
      created=$(echo "$line" | grep -oP 'created \K.*' || echo "?")
      # Get last output
      last=$(tmux capture-pane -pt "$session" -S -3 2>/dev/null | grep -v "^$" | tail -1 | cut -c1-60 || echo "")
      echo -e "  ${CYAN}$session${NC}: $last"
    done <<< "$sessions"
  fi
  echo ""

  # === RECENT AGENT WORK ===
  echo -e "${BOLD}RECENT GIT COMMITS (agents)${NC}"
  cd "$ROOT"
  git log --oneline -6 --format="  %Cgreen%h%Creset %s  %Cdim%cr%Creset" 2>/dev/null || echo "  (no commits)"
  echo ""

  # === BATCH STATE ===
  echo -e "${BOLD}BATCH STATE${NC}"
  python3 - <<'PY' 2>/dev/null || echo "  (error reading queue)"
import json, sys
with open("docs/orchestrator-ops/priority-queue.json") as f:
    q = json.load(f)
symbols = {"CLOSED":"✅","DONE":"✅","IN_PROGRESS":"🔄","READY":"📋","BLOCKED":"🚫","PLANNED":"💤"}
for item in q.get("items",[]):
    s = item.get("state","?")
    icon = symbols.get(s,"❓")
    print(f"  {icon} {item['id']:10} {s:12} {item['title'][:40]}")
PY
  echo ""

  # === LAST AGENT LOGS ===
  echo -e "${BOLD}LAST TICK LOGS${NC}"
  for role in planner backend_engineer frontend_engineer data_analyst; do
    logfile="$ROOT/logs-codex-runs/fc-ticks/$role.cron.log"
    if [[ -f "$logfile" ]]; then
      last_ts=$(grep "\[START\]\|\[END\]\|\[TICK\]" "$logfile" | tail -1 | cut -c1-60 || echo "?")
      echo -e "  ${CYAN}$role${NC}: $last_ts"
    else
      echo -e "  ${CYAN}$role${NC}: ${YELLOW}no log${NC}"
    fi
  done
  echo ""

  # === API DATA FRESHNESS ===
  echo -e "${BOLD}DATA QUALITY${NC}"
  news_total=$(curl -s "http://localhost:8050/api/news/feed?limit=1" 2>/dev/null | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['data']['total'])" 2>/dev/null || echo "?")
  forecast_total=$(curl -s "http://localhost:8050/api/forecasts?limit=1" 2>/dev/null | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['data']['total'])" 2>/dev/null || echo "?")
  echo -e "  News: ${GREEN}$news_total articles${NC}  Forecasts: ${GREEN}$forecast_total${NC}"
}

if [[ "${1:-}" == "--watch" ]]; then
  while true; do show_health; sleep 15; done
else
  show_health
fi
