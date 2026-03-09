#!/usr/bin/env bash
# ============================================================
# FINANCE COPILOT — DEV TOOLS
# Usage: bash scripts/dev_tools.sh <command> [args]
# ============================================================
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"
API_BASE="http://localhost:8050/api"
FRONTEND_PORT=5173

usage() {
  cat <<'EOF'
Finance Copilot Dev Tools — available commands:

  BACKEND
    status          Check backend health + data freshness
    restart         Restart backend via systemd
    logs            Tail backend logs (last 50 lines)
    test-api        Test all main API endpoints
    refresh-data    Trigger forecast + news refresh jobs

  FRONTEND  
    frontend-status Check if frontend server is up
    open-browser    Open the app in a browser (xdg-open)

  WORKBOARD
    board           Show workboard status (all roles)
    board-role ROLE Show context for specific role
    claim ROLE      Claim next READY task for a role
    complete TASK   Mark task DONE (e.g. BATCH-03-BACKEND)
    block TASK MSG  Mark task BLOCKED with reason

  AGENTS
    agent-status    Show all tmux agent sessions + last output
    agent-log ROLE  Show last 30 lines of role log
    tick ROLE       Manually trigger one cron tick for a role

  GIT
    checkpoint MSG  git add -A && git commit with message

EOF
}

backend_status() {
  echo "=== Backend Health ==="
  curl -s "$API_BASE/health" | python3 -c "
import sys, json, datetime
d = json.load(sys.stdin)
print(f'Status: {d.get(\"status\",\"?\")} | Backend: {d.get(\"backend_up\",\"?\")}')
lu = d.get('last_updates', {})
now = datetime.datetime.utcnow()
for k, v in lu.items():
    if v:
        try:
            dt = datetime.datetime.fromisoformat(v.replace('Z',''))
            diff = now - dt
            mins = int(diff.total_seconds() / 60)
            print(f'  {k:15}: updated {mins}m ago ({v[:19]})')
        except:
            print(f'  {k:15}: {v}')
    else:
        print(f'  {k:15}: null (never)')
" 2>/dev/null || echo "❌ Backend DOWN — run: bash scripts/dev_tools.sh restart"
}

backend_restart() {
  echo "Restarting backend..."
  systemctl --user restart finance-backend
  sleep 3
  if systemctl --user is-active finance-backend >/dev/null 2>&1; then
    echo "✅ Backend restarted"
    backend_status
  else
    echo "❌ Restart failed — check: journalctl --user -u finance-backend -n 30"
  fi
}

backend_logs() {
  journalctl --user -u finance-backend -n ${1:-50} --no-pager
}

test_api() {
  echo "=== API Endpoint Tests ==="
  local ok=0 fail=0
  
  test_endpoint() {
    local name="$1" url="$2"
    local result
    if result=$(curl -fsS --max-time 5 "$url" 2>/dev/null); then
      local count
      count=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); data=d.get('data',{}); print(len(data.get('items') or data.get('rows') or data.get('tickers') or data.get('stocks') or []))" 2>/dev/null || echo "?")
      echo "  ✅ $name (count=$count)"
      ok=$((ok+1))
    else
      echo "  ❌ $name — FAILED ($url)"
      fail=$((fail+1))
    fi
  }
  
  test_endpoint "health"      "$API_BASE/health"
  test_endpoint "news/feed"   "$API_BASE/news/feed?limit=5"
  test_endpoint "forecasts"   "$API_BASE/forecasts?limit=5"
  test_endpoint "stocks/top"  "$API_BASE/stocks/top"
  test_endpoint "stocks/prices" "$API_BASE/stocks/prices"
  test_endpoint "backtests"   "$API_BASE/backtests"
  test_endpoint "judge"       "$API_BASE/judge?limit=3"
  
  echo ""
  echo "Result: $ok OK / $fail FAILED"
}

refresh_data() {
  echo "=== Triggering data refresh ==="
  local api_src="$ROOT/apps/api/src"
  local py_bin="python3"
  if [[ -x "$api_src/.venv/bin/python3" ]]; then
    py_bin="$api_src/.venv/bin/python3"
  fi

  PYTHONPATH="$api_src" "$py_bin" - <<PY || echo "Refresh attempted (some jobs may not be directly runnable)"
import os
import subprocess

root = ${ROOT@Q}
api_src = os.path.join(root, "apps/api/src")
py_bin = ${py_bin@Q}
env = {**os.environ, "PYTHONPATH": api_src}

print('Running forecasts job...')
try:
    r = subprocess.run(
        [py_bin, '-m', 'platform.legacy.jobs.forecasts_simple'],
        capture_output=True,
        text=True,
        cwd=api_src,
        env=env,
        timeout=60,
    )
    print('forecasts:', 'OK' if r.returncode == 0 else f'FAIL: {(r.stderr or r.stdout)[:200]}')
except subprocess.TimeoutExpired:
    print('forecasts: TIMEOUT(after=60s)')

print('Running news ingestion...')
try:
    r = subprocess.run(
        [py_bin, 'platform/legacy/jobs/news_ingest.py'],
        capture_output=True,
        text=True,
        cwd=api_src,
        env=env,
        timeout=120,
    )
    print('news:', 'OK' if r.returncode == 0 else f'FAIL: {(r.stderr or r.stdout)[:200]}')
except subprocess.TimeoutExpired:
    print('news: TIMEOUT(after=120s)')
PY
}

frontend_status() {
  if curl -fsS --max-time 3 "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1; then
    echo "✅ Frontend UP at http://localhost:$FRONTEND_PORT"
  else
    echo "❌ Frontend DOWN on port $FRONTEND_PORT"
    echo "To start: cd apps/web/src/domains/forecasts/pages && python3 -m http.server $FRONTEND_PORT &"
  fi
}

board_status() {
  python3 scripts/parallel_workstream.py status | python3 -c "
import sys, json
d = json.load(sys.stdin)
s = d['summary']
print(f'Board: {s[\"total\"]} total | {s[\"ready\"]} ready | {s[\"in_progress\"]} in_progress | {s[\"done\"]} done | {s.get(\"blocked\",0)} blocked')
print()
for role, info in d['by_role'].items():
    if info.get('ready') or info.get('in_progress'):
        for t in info.get('in_progress', []):
            print(f'  🔄 [{role}] {t[\"id\"]}: {t[\"title\"][:60]}')
        for t in info.get('ready', []):
            print(f'  📋 [{role}] {t[\"id\"]}: {t[\"title\"][:60]}')
"
}

board_role() {
  local role="${1:-planner}"
  python3 scripts/parallel_workstream.py context --role "$role"
}

claim_task() {
  local role="${1:-}"
  if [[ -z "$role" ]]; then echo "Usage: $0 claim ROLE"; exit 1; fi
  python3 scripts/parallel_workstream.py claim --role "$role"
}

complete_task() {
  local task="${1:-}"
  if [[ -z "$task" ]]; then echo "Usage: $0 complete TASK_ID"; exit 1; fi
  python3 scripts/parallel_workstream.py complete --task "$task" --role "${2:-}" --artifact "${3:-}" --notes "${4:-}"
}

agent_status() {
  echo "=== Agent Sessions ==="
  tmux ls 2>/dev/null | while IFS=: read -r session rest; do
    local last
    last=$(tmux capture-pane -pt "$session" -S -5 2>/dev/null | grep -E "STATUS|VERDICT|DELTA|NEXT_ACTION" | tail -3 | tr '\n' ' ' || echo "idle")
    printf "  %-35s %s\n" "$session" "${last:0:80}"
  done
}

agent_log() {
  local role="${1:-planner}"
  local log="logs-codex-runs/role-runner/${role}.live.log"
  if [[ -f "$log" ]]; then
    tail -30 "$log"
  else
    echo "No log found: $log"
    ls logs-codex-runs/role-runner/*.live.log 2>/dev/null | head -10
  fi
}

tick_role() {
  local role="${1:-}"
  if [[ -z "$role" ]]; then echo "Usage: $0 tick ROLE"; exit 1; fi
  echo "Triggering cron tick for: $role"
  bash scripts/cron_tmux_role_runner.sh "$role"
}

git_checkpoint() {
  local msg="${1:-checkpoint $(date '+%Y-%m-%d %H:%M')}"
  git add -A
  git commit -m "$msg" --no-verify
  echo "✅ Committed: $msg"
}

# Dispatch
cmd="${1:-help}"
shift || true
case "$cmd" in
  status|backend-status)    backend_status ;;
  restart|backend-restart)  backend_restart ;;
  logs|backend-logs)        backend_logs "$@" ;;
  test-api)                 test_api ;;
  refresh-data)             refresh_data ;;
  frontend-status)          frontend_status ;;
  board)                    board_status ;;
  board-role)               board_role "$@" ;;
  claim)                    claim_task "$@" ;;
  complete)                 complete_task "$@" ;;
  agent-status)             agent_status ;;
  agent-log)                agent_log "$@" ;;
  tick)                     tick_role "$@" ;;
  checkpoint)               git_checkpoint "$@" ;;
  help|--help|-h|"")        usage ;;
  *) echo "Unknown command: $cmd"; usage; exit 1 ;;
esac
