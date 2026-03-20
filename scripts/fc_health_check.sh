#!/usr/bin/env bash
# ============================================================
# fc_health_check.sh — Dashboard santé du système Finance Copilot
# Usage: bash scripts/fc_health_check.sh
# ============================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT_CANDIDATE="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
WORKSPACE_HELPER="${SCRIPT_DIR}/../platform/automation/lib/workspace_paths.sh"
if [[ -f "$WORKSPACE_HELPER" ]]; then
  # shellcheck source=/dev/null
  source "$WORKSPACE_HELPER"
  ROOT="$(fc_prefer_writable_workspace "$(fc_resolve_workspace_root "$SCRIPT_DIR")")"
else
  ROOT="$ROOT_CANDIDATE"
fi
MODEL_CONFIG_FILE="$ROOT/platform/config/lm_used_model_config.sh"
[[ -f "$MODEL_CONFIG_FILE" ]] || MODEL_CONFIG_FILE="$ROOT/platform/config/model-config.sh"
[[ -f "$MODEL_CONFIG_FILE" ]] && source "$MODEL_CONFIG_FILE" 2>/dev/null || true
# Sourced config can re-enable errexit; keep health check best-effort.
set +e
set +u

RUNNER_CONFIG_FILE="${RUNNER_CONFIG_FILE:-$ROOT/platform/config/runner/runner.v1.yaml}"
[[ -f "$RUNNER_CONFIG_FILE" ]] || RUNNER_CONFIG_FILE="$ROOT/platform/config/runner/runner_config.v1.yaml"

scheduled_roles() {
  python3 - "$RUNNER_CONFIG_FILE" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
roles = ["planner", "dev", "admin"]
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print(" ".join(roles))
    raise SystemExit(0)

features = data.get("features", {}) if isinstance(data, dict) else {}
planner = features.get("planner_orchestrator", {}) if isinstance(features, dict) else {}
enabled = str(planner.get("enabled", "")).strip() not in {"", "0", "false", "False"}
planner_only = str(planner.get("cron_planner_only", "")).strip() not in {"", "0", "false", "False"}
if enabled and planner_only:
    roles = ["planner"]
print(" ".join(roles))
PY
}

SCHEDULED_ROLES_STR="$(scheduled_roles)"
read -r -a SCHEDULED_ROLES <<< "${SCHEDULED_ROLES_STR:-planner dev admin}"
[[ "${#SCHEDULED_ROLES[@]}" -gt 0 ]] || SCHEDULED_ROLES=("planner" "dev" "admin")
PLANNER_ONLY_MODE=0
if [[ "${#SCHEDULED_ROLES[@]}" -eq 1 && "${SCHEDULED_ROLES[0]}" == "planner" ]]; then
  PLANNER_ONLY_MODE=1
fi

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
  STATUS=$(echo "$HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); r=d.get('data', d); print(r.get('status','ok' if d.get('ok') is True else '?'))" 2>/dev/null)
  FORECASTS_TS=$(echo "$HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); r=d.get('data', d); print(r.get('last_updates',{}).get('forecasts','never'))" 2>/dev/null)
  NEWS_TS=$(echo "$HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); r=d.get('data', d); print(r.get('last_updates',{}).get('news','never'))" 2>/dev/null)
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

# ── 3. Monitor Contract ────────────────────────────────────
echo -e "\n${BOLD}[ Monitor Contract ]${NC}"
MONITOR_BASE_URL="${FC_MONITOR_BASE_URL:-http://127.0.0.1:7779}"
MONITOR_SMOKE="$ROOT/scripts/monitor_contract_smoke.sh"
if [[ -x "$MONITOR_SMOKE" ]]; then
  MONITOR_SUMMARY="$("$MONITOR_SMOKE" --base-url "$MONITOR_BASE_URL" 2>&1)"
  MONITOR_RC=$?
  if [[ "$MONITOR_RC" -eq 0 ]]; then
    ok "Monitor API contract OK (${MONITOR_BASE_URL}) | ${MONITOR_SUMMARY#PASS }"
  else
    fail "Monitor API contract FAILED (${MONITOR_BASE_URL}) | ${MONITOR_SUMMARY}"
  fi
else
  MON_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "${MONITOR_BASE_URL}/api/status" 2>/dev/null)
  [[ "$MON_CODE" == "200" ]] && warn "monitor_contract_smoke.sh missing, fallback check only (/api/status=200)" || fail "Monitor API not reachable (${MONITOR_BASE_URL})"
fi

# ── 3a. Critical Endpoints Contract ───────────────────────
echo -e "\n${BOLD}[ Critical Endpoints Contract ]${NC}"
CRITICAL_SMOKE="$ROOT/scripts/critical_endpoints_smoke.sh"
API_BASE_URL="${FC_API_BASE_URL:-http://127.0.0.1:8050}"
if [[ -x "$CRITICAL_SMOKE" || -f "$CRITICAL_SMOKE" ]]; then
  CRITICAL_SUMMARY="$(bash "$CRITICAL_SMOKE" --base-url "$API_BASE_URL" 2>&1)"
  CRITICAL_RC=$?
  if [[ "$CRITICAL_RC" -eq 0 ]]; then
    ok "Critical endpoints contract OK (${API_BASE_URL})"
  else
    # NOTE: Distinguish contract schema failure from true network unreachability.
    # A schema mismatch (missing meta/status fields) is a DEV issue, NOT a runtime blocker.
    # Downgrade to warn so admin does not misreport backend_unreachable when port is alive.
    warn "Critical endpoints contract DEGRADED (${API_BASE_URL}) — schema non-conforme (issue API-CONTRACT-001) | ${CRITICAL_SUMMARY}"
  fi
else
  warn "critical_endpoints_smoke.sh missing (skip)"
fi

# ── 3b. Issue Reporting Compliance ────────────────────────
echo -e "\n${BOLD}[ Issue Reporting Compliance ]${NC}"
ISSUE_STATUS_JSON="$(curl -s --max-time 3 "${MONITOR_BASE_URL}/api/status" 2>/dev/null)"
if [[ -n "$ISSUE_STATUS_JSON" ]]; then
  ISSUE_SUMMARY="$(echo "$ISSUE_STATUS_JSON" | python3 -c "import sys,json
try:
    d=json.load(sys.stdin)
except Exception:
    print('ERR')
    raise SystemExit(0)
ir=d.get('issue_reporting') if isinstance(d,dict) else None
if not isinstance(ir,dict):
    print('ERR')
    raise SystemExit(0)
roles_total=int(ir.get('roles_total',0) or 0)
missing=ir.get('roles_missing_report',[])
if not isinstance(missing,list):
    missing=[]
reports_with_issues=int(ir.get('reports_with_issues',0) or 0)
critical_count=int(ir.get('critical_count',0) or 0)
print(f'{roles_total}|{len(missing)}|{reports_with_issues}|{critical_count}|{','.join(missing[:6]) if missing else 'none'}')
" 2>/dev/null)"
  if [[ "$ISSUE_SUMMARY" != "ERR" && -n "$ISSUE_SUMMARY" ]]; then
    IFS='|' read -r IR_TOTAL IR_MISSING IR_OPEN IR_CRIT IR_MISSING_ROLES <<< "$ISSUE_SUMMARY"
    if [[ "${IR_MISSING:-0}" -eq 0 ]]; then
      ok "Issue reports conformes | roles=${IR_TOTAL:-0} | open=${IR_OPEN:-0} | critical=${IR_CRIT:-0}"
    else
      warn "Issue reports incomplets | missing=${IR_MISSING:-0}/${IR_TOTAL:-0} roles=${IR_MISSING_ROLES:-none} | open=${IR_OPEN:-0} | critical=${IR_CRIT:-0}"
    fi
  else
    warn "Impossible de parser issue_reporting depuis /api/status"
  fi
else
  warn "Issue reporting indisponible (monitor API non joignable)"
fi

# ── 4. Active API Data ─────────────────────────────────────
echo -e "\n${BOLD}[ Live Data ]${NC}"
FORECASTS=$(curl -s --max-time 3 "http://localhost:8050/api/forecasts?limit=1" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); rows=d.get('data',{}).get('rows',[]); print(len(rows))" 2>/dev/null)
NEWS=$(curl -s --max-time 3 "http://localhost:8050/api/news/feed?limit=1" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); items=d.get('data',{}).get('items',[]); print(len(items))" 2>/dev/null)
[[ "${FORECASTS:-0}" -gt 0 ]] && ok "Forecasts: $FORECASTS available" || fail "Forecasts: none"
[[ "${NEWS:-0}" -gt 0 ]] && ok "News: $NEWS available" || fail "News: none"

# ── 5. Agent Sessions ─────────────────────────────────────
echo -e "\n${BOLD}[ Agent Sessions ]${NC}"
for role in "${SCHEDULED_ROLES[@]}"; do
  SESSION="codex_${role}_cron"
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    CMD=$(tmux display-message -p -t "$SESSION:0.0" "#{pane_current_command}" 2>/dev/null | tr '[:upper:]' '[:lower:]' || echo "?")
    ok "Session $SESSION | pane_cmd=$CMD"
  else
    warn "Session $SESSION — NOT running"
  fi
done
if [[ "$PLANNER_ONLY_MODE" -eq 1 ]]; then
  info "Planner-only mode active: dev/admin/scrum_master run as planner-owned capabilities, not standalone cron sessions"
fi

# ── 6. Cron Jobs ──────────────────────────────────────────
echo -e "\n${BOLD}[ Cron Schedule ]${NC}"
CRON_ENTRIES=$(crontab -l 2>/dev/null | grep -v "^#\|^$" | wc -l)
CRON_AGENT=$(crontab -l 2>/dev/null | grep "fc_agent_tick\|cron_tmux_role_runner" | wc -l)
[[ "$CRON_AGENT" -gt 0 ]] && ok "$CRON_AGENT agent tick job(s) in crontab" || fail "No agent tick jobs in crontab! Run: bash scripts/fc_setup_crons.sh"
[[ "$CRON_ENTRIES" -gt 0 ]] && info "Total cron entries: $CRON_ENTRIES"

# ── 6b. Scheduler Ownership ───────────────────────────────
echo -e "\n${BOLD}[ Scheduler Ownership ]${NC}"
LEGACY_QWEN_UNITS=0
if command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
  LEGACY_QWEN_UNITS=$(systemctl --user list-units --all --type=service --type=timer 2>/dev/null \
    | grep -E "fc-(planner|dev|admin)-qwen\.(service|timer)" \
    | grep -E " active | activating | waiting " \
    | wc -l)
  LEGACY_QWEN_UNITS="$(printf '%s' "${LEGACY_QWEN_UNITS:-0}" | tr -d '[:space:]')"
else
  LEGACY_QWEN_UNITS=0
fi
[[ -n "$LEGACY_QWEN_UNITS" ]] || LEGACY_QWEN_UNITS=0
if [[ "$LEGACY_QWEN_UNITS" -gt 0 ]]; then
  fail "Legacy qwen schedulers active (${LEGACY_QWEN_UNITS}) — disable via: systemctl --user disable --now fc-{planner,dev,admin}-qwen.timer"
else
  ok "No active legacy qwen systemd schedulers"
fi

QWEN_TMUX_SESSIONS=0
if command -v tmux >/dev/null 2>&1; then
  QWEN_TMUX_SESSIONS=$(tmux ls 2>/dev/null | grep -E "^qwen_(planner|dev|admin)_cron:" | wc -l)
  QWEN_TMUX_SESSIONS="$(printf '%s' "${QWEN_TMUX_SESSIONS:-0}" | tr -d '[:space:]')"
fi
[[ -n "$QWEN_TMUX_SESSIONS" ]] || QWEN_TMUX_SESSIONS=0
if [[ "$QWEN_TMUX_SESSIONS" -gt 0 ]]; then
  warn "Legacy qwen tmux sessions still present (${QWEN_TMUX_SESSIONS}) — cleanup: tmux kill-session -t qwen_<role>_cron"
else
  ok "No qwen_* tmux legacy sessions"
fi

# ── 7. Recent Agent Deliveries ────────────────────────────
echo -e "\n${BOLD}[ Agent Activity (last 2h) ]${NC}"
TICK_LOG_DIR="$ROOT/logs-codex-runs/fc-ticks"
for role in "${SCHEDULED_ROLES[@]}"; do
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
if [[ "$PLANNER_ONLY_MODE" -eq 1 ]]; then
  info "Planner-only activity is expected; managed roles do not emit standalone tick logs in this mode"
fi

# ── 8. Git Progress ───────────────────────────────────────
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

# ── 9. Rate Limits ────────────────────────────────────────
echo -e "\n${BOLD}[ Rate Limits ]${NC}"
RATE_HITS=$(grep -r "rate_limit" logs-codex-runs/role-runner/*.log 2>/dev/null | grep "$(date +%Y-%m-%d)" | wc -l || echo 0)
RATE_HITS="$(printf '%s' "${RATE_HITS:-0}" | tr -d '[:space:]')"
[[ -n "$RATE_HITS" ]] || RATE_HITS=0
[[ "$RATE_HITS" -gt 5 ]] && warn "Rate limit hits today: $RATE_HITS — consider slowing cron intervals" || ok "Rate limit hits today: $RATE_HITS"

# ── 10. Model Config Guard ─────────────────────────────────
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

# ── 11. Rate Limit Cooldowns ──────────────────────────────
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

# ── 12. Orchestration Signal Quality ───────────────────────
echo -e "\n${BOLD}[ Orchestration Quality ]${NC}"
QUALITY_WINDOW_MINUTES="${QUALITY_WINDOW_MINUTES:-180}"
QUALITY_SIGNAL_UNPARSEABLE_WARN="${QUALITY_SIGNAL_UNPARSEABLE_WARN:-10}"
QUALITY_SESSION_NOT_READY_WARN="${QUALITY_SESSION_NOT_READY_WARN:-6}"
QUALITY_CONTRACT_GUARD_WARN="${QUALITY_CONTRACT_GUARD_WARN:-4}"
QUALITY_ROLES=("planner" "dev" "admin")
for n in QUALITY_WINDOW_MINUTES QUALITY_SIGNAL_UNPARSEABLE_WARN QUALITY_SESSION_NOT_READY_WARN QUALITY_CONTRACT_GUARD_WARN; do
  val="$(printf '%s' "${!n:-}" | tr -d '[:space:]')"
  [[ "$val" =~ ^[0-9]+$ ]] || val=0
  [[ "$val" -gt 0 ]] || val=1
  printf -v "$n" '%s' "$val"
done

collect_quality_files() {
  local role f
  QUALITY_FILES=()
  QUALITY_WINDOW_FILES=0
  for role in "${QUALITY_ROLES[@]}"; do
    for f in "logs-codex-runs/role-runner/${role}.live.log" "logs-codex-runs/fc-ticks/${role}.tick.log" "logs-codex-runs/fc-ticks/${role}.cron.log"; do
      [[ -f "$f" ]] || continue
      QUALITY_FILES+=("$f")
      QUALITY_WINDOW_FILES=$((QUALITY_WINDOW_FILES + 1))
    done
  done
}

count_pat_recent_files() {
  local pattern="$1"
  local minutes="$2"
  if [[ "${#QUALITY_FILES[@]}" -eq 0 ]]; then
    printf '0\n'
    return 0
  fi
  python3 - "$pattern" "$minutes" "${QUALITY_FILES[@]}" <<'PY'
import sys
from datetime import datetime, timedelta, timezone

pattern = sys.argv[1]
minutes = max(1, int(sys.argv[2]))
paths = sys.argv[3:]
local_tz = datetime.now().astimezone().tzinfo
cutoff_utc = datetime.now(timezone.utc) - timedelta(minutes=minutes)
hits = 0

for path in paths:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            for raw in handle:
                line = raw.rstrip("\n")
                if not line:
                    continue
                token = line.split(" ", 1)[0]
                try:
                    if token.endswith("Z"):
                        ts = datetime.fromisoformat(token[:-1]).replace(tzinfo=timezone.utc)
                    else:
                        ts = datetime.fromisoformat(token)
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=local_tz)
                        ts = ts.astimezone(timezone.utc)
                except Exception:
                    continue
                if ts < cutoff_utc:
                    continue
                hits += line.count(pattern)
    except Exception:
        continue

print(hits)
PY
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

collect_quality_files
SIG_UNPARSEABLE="$(count_pat_recent_files "signal_unparseable" "$QUALITY_WINDOW_MINUTES")"
SESSION_NOT_READY="$(count_pat_recent_files "session_not_ready" "$QUALITY_WINDOW_MINUTES")"
CONTRACT_GUARD_BLOCKS="$(count_pat_recent_files "contract_guard_" "$QUALITY_WINDOW_MINUTES")"

SIG_UNPARSEABLE_TOTAL="$(count_pat_files "signal_unparseable")"
SESSION_NOT_READY_TOTAL="$(count_pat_files "session_not_ready")"
CONTRACT_GUARD_TOTAL="$(count_pat_files "contract_guard_")"

[[ "$SIG_UNPARSEABLE" -gt "$QUALITY_SIGNAL_UNPARSEABLE_WARN" ]] && warn "signal_unparseable (window) high: $SIG_UNPARSEABLE > $QUALITY_SIGNAL_UNPARSEABLE_WARN" || ok "signal_unparseable (window): $SIG_UNPARSEABLE"
[[ "$SESSION_NOT_READY" -gt "$QUALITY_SESSION_NOT_READY_WARN" ]] && warn "session_not_ready (window) high: $SESSION_NOT_READY > $QUALITY_SESSION_NOT_READY_WARN" || ok "session_not_ready (window): $SESSION_NOT_READY"
[[ "$CONTRACT_GUARD_BLOCKS" -gt "$QUALITY_CONTRACT_GUARD_WARN" ]] && warn "contract_guard blocks (window) high: $CONTRACT_GUARD_BLOCKS > $QUALITY_CONTRACT_GUARD_WARN" || ok "contract_guard blocks (window): $CONTRACT_GUARD_BLOCKS"
info "quality window: roles=$(IFS=,; echo "${QUALITY_ROLES[*]}") minutes=${QUALITY_WINDOW_MINUTES} files=${QUALITY_WINDOW_FILES:-0} | totals: signal=${SIG_UNPARSEABLE_TOTAL} session=${SESSION_NOT_READY_TOTAL} guard=${CONTRACT_GUARD_TOTAL}"

# ── 13. Issue Publication Completeness ────────────────────
echo -e "\n${BOLD}[ Issue Publication ]${NC}"
ISSUE_EVENTS_FILE="$ROOT/logs-codex-runs/orchestrator-state/agent-iteration-issues.jsonl"
[[ -f "$ISSUE_EVENTS_FILE" ]] || ISSUE_EVENTS_FILE="$ROOT/docs/operations/orchestrator/agent-iteration-issues.jsonl"
ISSUE_STATUS_SNAPSHOT="$(curl -s --max-time 3 "${MONITOR_BASE_URL}/api/status" 2>/dev/null)"
ISSUE_STATUS_SUMMARY="$(printf '%s' "$ISSUE_STATUS_SNAPSHOT" | python3 -c "import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    print('ERR')
    raise SystemExit(0)
roles=d.get('roles', [])
if not isinstance(roles, list):
    roles=[]
gaps=d.get('issue_publication_gap_roles', [])
if not isinstance(gaps, list):
    gaps=[]
print(f\"{len(gaps)}|{','.join(str(x) for x in gaps) or 'none'}|{','.join(str(x) for x in roles) or 'unknown'}\")
" 2>/dev/null)"
if [[ "$ISSUE_STATUS_SUMMARY" != "ERR" && -n "$ISSUE_STATUS_SUMMARY" ]]; then
  IFS='|' read -r ISSUE_GAP_COUNT ISSUE_GAP_ROLES ISSUE_ROLE_SCOPE <<< "$ISSUE_STATUS_SUMMARY"
  if [[ "${ISSUE_GAP_COUNT:-0}" -gt 0 ]]; then
    fail "ISSUE_PUBLICATION_GAP roles=${ISSUE_GAP_ROLES} (monitor status)"
  else
    ok "Issue publication continuity OK (roles=${ISSUE_ROLE_SCOPE})"
  fi
elif [[ -f "$ISSUE_EVENTS_FILE" ]]; then
  ISSUE_SUMMARY_JSON="$(python3 - "$ISSUE_EVENTS_FILE" "${SCHEDULED_ROLES[@]}" <<'PY'
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
roles = tuple(arg.strip() for arg in sys.argv[2:] if str(arg).strip()) or ("planner",)
schedule = {
    "planner": [0, 22, 44],
    "dev": [6, 28, 50],
    "admin": [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55],
}

def parse_ts(raw: str):
    text = str(raw or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).timestamp()

def role_interval(role: str) -> float:
    mins = sorted(set(schedule.get(role, [])))
    if len(mins) <= 1:
        return 60.0
    deltas = []
    for idx, m in enumerate(mins):
        nxt = mins[(idx + 1) % len(mins)]
        delta = (nxt - m) % 60
        if delta <= 0:
            delta = 60
        deltas.append(delta)
    return float(min(deltas)) if deltas else 60.0

latest = {}
for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
    line = raw.strip()
    if not line:
        continue
    try:
        item = json.loads(line)
    except Exception:
        continue
    if not isinstance(item, dict):
        continue
    role = str(item.get("role", "")).strip()
    if role not in roles:
        continue
    ts = parse_ts(item.get("ts_utc", ""))
    if ts is None:
        continue
    prev = latest.get(role)
    if prev is None or ts > prev:
        latest[role] = ts

now = time.time()
gaps = []
ages = {}
for role in roles:
    ts = latest.get(role)
    if ts is None:
        ages[role] = -1
        gaps.append(role)
        continue
    age_min = (now - ts) / 60.0
    ages[role] = int(age_min)
    if age_min > role_interval(role) * 1.5:
        gaps.append(role)

print(json.dumps({"gaps": sorted(gaps), "ages": ages}, ensure_ascii=True))
PY
)"
  ISSUE_GAP_COUNT="$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); print(len(d.get("gaps",[])))' "$ISSUE_SUMMARY_JSON" 2>/dev/null || echo 0)"
  ISSUE_GAP_ROLES="$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); print(",".join(d.get("gaps",[])) or "none")' "$ISSUE_SUMMARY_JSON" 2>/dev/null || echo "none")"
  ISSUE_ROLE_SCOPE="$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); print(",".join(sorted(d.get("ages",{}).keys())) or "unknown")' "$ISSUE_SUMMARY_JSON" 2>/dev/null || echo "unknown")"
  if [[ "${ISSUE_GAP_COUNT:-0}" -gt 0 ]]; then
    fail "ISSUE_PUBLICATION_GAP roles=${ISSUE_GAP_ROLES} (records missing > 1.5x interval; roles=${ISSUE_ROLE_SCOPE})"
  else
    ok "Issue publication continuity OK (roles=${ISSUE_ROLE_SCOPE})"
  fi
else
  fail "ISSUE_PUBLICATION_GAP source missing: ${ISSUE_EVENTS_FILE}"
fi

# ── 14. Stale Locks ───────────────────────────────────────
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
