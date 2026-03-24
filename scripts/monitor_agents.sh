#!/usr/bin/env bash
# monitor_agents.sh — Dashboard orchestration lean
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
WORKSPACE_HELPER="${SCRIPT_DIR}/../platform/automation/lib/workspace_paths.sh"
if [[ -f "$WORKSPACE_HELPER" ]]; then
  # shellcheck source=/dev/null
  source "$WORKSPACE_HELPER"
  ROOT="$(fc_prefer_writable_workspace "$(fc_resolve_workspace_root "$SCRIPT_DIR")")"
else
  ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
fi
cd "$ROOT"

WATCH=0; COMPACT=0
for arg in "$@"; do
  [[ "$arg" == "--watch"   ]] && WATCH=1
  [[ "$arg" == "--compact" ]] && COMPACT=1
done

DEFAULT_STATE_DIR="/home/venom/.openclaw/cron/role-state"
ALT_STATE_DIR="${HOME}/.openclaw/cron/role-state"
if [[ -d "$DEFAULT_STATE_DIR" ]]; then
  STATE_DIR="${TMUX_ROLE_STATE_DIR:-$DEFAULT_STATE_DIR}"
else
  STATE_DIR="${TMUX_ROLE_STATE_DIR:-$ALT_STATE_DIR}"
fi
LIVE_LOG="$ROOT/logs-codex-runs/role-runner"
TICK_LOG="$ROOT/logs-codex-runs/fc-ticks"

iso_to_epoch_local() {
  local iso_ts="$1"
  python3 - "$iso_ts" <<'PY'
import sys
from datetime import datetime
value = (sys.argv[1] or "").strip()
if not value:
    print(0)
    raise SystemExit(0)
try:
    # tick logs store local naive timestamps (no timezone suffix)
    dt = datetime.fromisoformat(value)
    print(int(dt.timestamp()))
except Exception:
    print(0)
PY
}

show_status() {
  printf '\n╔══════════════════════════════════════════════════════════╗\n'
  printf '║  🟦 Finance Copilot — Orchestration              %s  ║\n' "$(date '+%H:%M:%S')"
  printf '╠══════════════════════════════════════════════════════════╣\n'

  # Rate limits
  _rl_any=0
  for _bin in codex qwen; do
    _f="$STATE_DIR/${_bin}.rate_limit_gate_cache"
    if [[ -f "$_f" ]]; then
      _payload=$(cat "$_f"); _until="${_payload%%|*}"
      _rem=$(( _until - $(date +%s) ))
      if [[ $_rem -gt 0 ]]; then
        printf '  ⚠  %s rate-limit: %ds restant\n' "$_bin" "$_rem"
        _rl_any=1
      else
        rm -f "$_f"
      fi
    fi
  done
  [[ $_rl_any -eq 0 ]] && printf '  ✅ Codex + Qwen libres\n'

  # Scheduler ownership conflicts (legacy qwen timers/services + tmux sessions)
  _legacy_units=0
  if command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
    _legacy_units=$(systemctl --user list-units --all --type=service --type=timer 2>/dev/null \
      | grep -E "fc-(planner|dev|admin)-qwen\.(service|timer)" \
      | grep -E " active | activating | waiting " \
      | wc -l)
    _legacy_units="$(printf '%s' "${_legacy_units:-0}" | tr -d '[:space:]')"
  fi
  [[ -n "${_legacy_units:-}" ]] || _legacy_units=0
  if [[ "$_legacy_units" -gt 0 ]]; then
    printf '  ⚠  legacy qwen systemd schedulers actifs: %s\n' "$_legacy_units"
  else
    printf '  ✅ Ownership scheduler: cron canonique seul\n'
  fi

  _legacy_tmux=0
  if command -v tmux >/dev/null 2>&1; then
    _legacy_tmux=$(tmux ls 2>/dev/null | grep -E "^qwen_(planner|dev|admin)_cron:" | wc -l)
    _legacy_tmux="$(printf '%s' "${_legacy_tmux:-0}" | tr -d '[:space:]')"
  fi
  [[ -n "${_legacy_tmux:-}" ]] || _legacy_tmux=0
  if [[ "$_legacy_tmux" -gt 0 ]]; then
    printf '  ⚠  sessions legacy qwen_* encore présentes: %s\n' "$_legacy_tmux"
  fi

  # Queue + Workboard
  printf '\n'
python3 - << 'PY'
import json
import re
from pathlib import Path
import time

ROOT = Path('.').resolve()
CANONICAL_ORCH = ROOT / 'docs' / 'operations' / 'orchestrator'
LEGACY_ORCH = ROOT / 'docs' / 'orchestrator-ops'

def resolve_orch_root() -> Path:
    candidates = []
    for d in (CANONICAL_ORCH, LEGACY_ORCH):
        if not d.exists():
            continue
        score = 0.0
        queue = d / 'priority-queue.json'
        board = d / 'parallel-workstreams.json'
        if queue.exists():
            score += 20.0
        if board.exists():
            score += 20.0
        latest = max(
            queue.stat().st_mtime if queue.exists() else 0.0,
            board.stat().st_mtime if board.exists() else 0.0,
        )
        if latest > 0:
            age_m = max(0.0, (time.time() - latest) / 60.0)
            score += max(0.0, 20.0 - min(20.0, age_m))
        candidates.append((score, d))
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    return CANONICAL_ORCH

ORCH_ROOT = resolve_orch_root()

def sym(s):
    return {'READY':'▶','IN_PROGRESS':'⟳','WAITING_DEP':'◌','DONE':'✓','CLOSED':'✓'}.get(s,'?')

try:
    pq = json.loads((ORCH_ROOT / 'priority-queue.json').read_text(encoding='utf-8', errors='ignore'))
    items = pq.get('items', [])
    top_level = [i for i in items if re.fullmatch(r'BATCH-\d{2}', str(i.get('id', '')).strip())]
    rows = top_level if top_level else items
    closed = sum(1 for i in rows if i.get('state') in ('CLOSED','DONE','PASS'))
    active = [i for i in rows if i.get('state') not in ('CLOSED','DONE','PASS')]
    print(f"  QUEUE  {closed}/{len(rows)} clos  |  {len(active)} actif(s)")
    for i in active[:3]:
        print(f"    {sym(i.get('state','?'))}  {i.get('id','?'):20s}  [{i.get('state','?')}]")
except Exception as e:
    print(f"  QUEUE: {e}")

try:
    wb = json.loads((ORCH_ROOT / 'parallel-workstreams.json').read_text(encoding='utf-8', errors='ignore'))
    tasks = wb.get('tasks', [])
    ready  = [t for t in tasks if t.get('state')=='READY']
    ip     = [t for t in tasks if t.get('state')=='IN_PROGRESS']
    done   = sum(1 for t in tasks if t.get('state') in ('DONE','CLOSED','PASS'))
    print(f"\n  WORKBOARD  {done} DONE  {len(ip)} IN_PROGRESS  {len(ready)} READY")
    for t in (ip + ready)[:6]:
        role_display = t.get('assignee') or t.get('role','?')
        print(f"    {sym(t['state'])}  {t.get('id','?'):28s}  role={role_display}")
except Exception as e:
    print(f"  WORKBOARD: {e}")
PY

  printf '\n╠══════════════════════════════════════════════════════════╣\n'
  printf '  AGENTS\n\n'

  # Agents: planner / dev / admin
  for _role in planner dev admin; do
    case "$_role" in
      planner) _sched=":0,22,44"  ;;
      dev)     _sched=":6,28,50"  ;;
      admin)   _sched="*/5" ;;
    esac

    # Age dernier tick
    _tlog="$TICK_LOG/$_role.tick.log"
    _age="?"
    if [[ -f "$_tlog" ]]; then
      _lts=$(grep -Eo '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}' "$_tlog" 2>/dev/null | tail -1)
      if [[ -n "${_lts:-}" ]]; then
        _epoch="$(iso_to_epoch_local "$_lts")"
        if [[ "${_epoch:-0}" -gt 0 ]]; then
          _age="$(( ($(date +%s) - _epoch) / 60 ))m"
        fi
      fi
    fi

    printf '  %-8s  %-12s  age: %s\n' "$_role" "$_sched" "$_age"

    # Contrat
    _cf="$STATE_DIR/$_role.last_contract"
    if [[ -f "$_cf" ]]; then
      _verdict=$(grep -m1 "^VERDICT:"    "$_cf" | cut -d: -f2- | tr -d ' \r')
      _status=$(grep  -m1 "^STATUS:"     "$_cf" | cut -d: -f2- | tr -d ' \r')
      _delta=$(grep   -m1 "^DELTA:"      "$_cf" | cut -d: -f2- | tr -d ' \r' | cut -c1-40)
      _blocker=$(grep -m1 "^BLOCKER_ID:" "$_cf" | cut -d: -f2- | tr -d ' \r')
      _next=$(grep    -m1 "^NEXT:"       "$_cf" | cut -d: -f2- | tr -d '\r' | sed 's/^ *//' | cut -c1-60)
      _evidence=$(grep -m1 "^EVIDENCE:"  "$_cf" | cut -d: -f2- | tr -d '\r')
      _issues=$(printf '%s\n' "$_evidence" | tr ';' '\n' | sed -n 's/^[[:space:]]*issues=//p' | head -1 | sed 's/[[:space:]]*$//')
      _issue_count=$(printf '%s\n' "$_evidence" | tr ';' '\n' | sed -n 's/^[[:space:]]*issue_count=//p' | head -1 | sed 's/[[:space:]]*$//')
      _issue_sev=$(printf '%s\n' "$_evidence" | tr ';' '\n' | sed -n 's/^[[:space:]]*issue_severity=//p' | head -1 | sed 's/[[:space:]]*$//')
      _is_rate_limit=0
      if [[ "$_blocker" =~ ^AGENT_RATE_LIMIT_ ]] || [[ "$_status" == "RATE_LIMIT_SKIP" ]] || [[ "$_status" == "RATE_LIMIT_BACKOFF" ]] || [[ "$_delta" == "RATE_LIMIT_BACKOFF" ]]; then
        _is_rate_limit=1
        [[ "$_verdict" == "BLOCKED" || -z "$_verdict" ]] && _verdict="WAIT"
        [[ "$_status" == "BLOCKED" || -z "$_status" ]] && _status="RATE_LIMIT_SKIP"
        [[ "$_blocker" =~ ^AGENT_RATE_LIMIT_ ]] && _blocker="NONE"
      fi
      case "$_verdict" in
        PASS|GO)  _icon="✅" ;;
        WAIT)     _icon="🔵" ;;
        BLOCKED)  _icon="🔴" ;;
        *)        _icon="⚪" ;;
      esac
      printf '    %s  %-8s  %-14s  %s\n' "$_icon" "$_verdict" "$_status" "$_delta"
      [[ "${_blocker:-NONE}" != "NONE" && -n "${_blocker:-}" && "$_is_rate_limit" -ne 1 ]] && \
        printf '    ↳ blocker: %s\n' "$_blocker"
      if [[ -n "${_issue_count}${_issue_sev}${_issues}" ]]; then
        printf '    ↳ issues: count=%s sev=%s codes=%s\n' \
          "${_issue_count:-?}" \
          "${_issue_sev:-?}" \
          "$(printf '%s' "${_issues:-none}" | cut -c1-54)"
      fi
      printf '    ↳ %s\n' "$_next"
    else
      printf '    ⚪  (pas de contrat)\n'
    fi

    # Dernier tick
    if [[ "$COMPACT" -eq 0 && -f "$_tlog" ]]; then
      _tline=$(grep -E "\[END\]|\[SKIP\]|\[BACKOFF\]" "$_tlog" 2>/dev/null | tail -1)
      if [[ -n "${_tline:-}" ]]; then
        _tts=$(printf '%s\n' "$_tline" | grep -Eo '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}' | head -1)
        _trc=$(printf '%s\n' "$_tline" | sed -n 's/.*rc=\([0-9][0-9]*\).*/\1/p' | head -1)
        _tag=$(printf '%s\n' "$_tline" | sed -n 's/.*agent=\([A-Za-z0-9_][A-Za-z0-9_]*\).*/\1/p' | head -1)
        _tic="✔"; [[ "${_trc:-1}" != "0" ]] && _tic="✘"
        printf '    %s  %s  %s  rc=%s\n' "$_tic" "${_tts:-?}" "${_tag:-?}" "${_trc:-?}"
      fi
    fi

    # Live trace (dernière action)
    _ll="$LIVE_LOG/$_role.live.log"
    if [[ -f "$_ll" ]]; then
      _ev=$(tail -1 "$_ll" | python3 -c "import sys,re; m=re.search(r'role=\S+ (\S+)', sys.stdin.read()); print(m.group(1) if m else '')" 2>/dev/null)
      [[ -n "${_ev:-}" ]] && printf '    ↳ live: %s\n' "$_ev"
    fi
    printf '\n'
  done

  # KPI
  # ── Prochains ticks ────────────────────────────────────────────────────────
  if [[ "$COMPACT" -eq 0 ]]; then
    printf '╠══════════════════════════════════════════════════════════╣\n'
    python3 - << 'PY2'
from datetime import datetime, timezone
now = datetime.now(timezone.utc)
m   = now.minute
schedules = {
    'planner':  [0,22,44],
    'dev':      [6,28,50],
    'admin':    [0,5,10,15,20,25,30,35,40,45,50,55],
}
print("  PROCHAINS TICKS:")
for role, mins in schedules.items():
    next_m = next((x for x in sorted(mins) if x > m), sorted(mins)[0])
    wait   = (next_m - m) if next_m > m else (60 - m + next_m)
    print(f"    {role:10s}  :{next_m:02d}  dans ~{wait}min")
PY2
  fi

  if [[ "$COMPACT" -eq 0 ]]; then
    printf '╠══════════════════════════════════════════════════════════╣\n'
    python3 - << 'PY'
import json
from pathlib import Path
try:
    import json as _j
    lines = [l for l in Path('logs-codex-runs/orchestrator-state/kpi-history.jsonl').read_text().splitlines() if l.strip()]
    last = {}
    for line in reversed(lines):
        try:
            d = _j.loads(line)
            if d.get("workboard") or d.get("done_total"):
                last = d; break
        except: pass
    ts     = last.get("ts_utc","?")[11:16]  # HH:MM
    wb     = last.get("workboard", {})
    vel    = last.get("velocity", {})
    done   = wb.get("done") or last.get("done_total", "?")
    ready  = wb.get("ready", "-")
    d24    = vel.get("done_24h") or last.get("done_24h", "-")
    d7     = vel.get("done_7d", "-")
    proofs = vel.get("proofs", "-")
    health = last.get("health", "OK")
    stale  = last.get("stale_agents", [])
    blocked= last.get("blocked_agents", [])
    icon   = {"OK":"✅","DEGRADED":"⚠️ ","STALE":"🔶"}.get(health,"❓")
    print(f"  {icon} snapshot {ts}  done={done}  ready={ready}  24h={d24}  7j={d7}  proofs={proofs}")
    if stale:   print(f"     🔶 stale: {', '.join(stale)}")
    if blocked: print(f"     🔴 blocked: {', '.join(blocked)}")
except Exception as e:
    print(f"  KPI: {e}")
PY
  fi

  printf '╚══════════════════════════════════════════════════════════╝\n\n'
}

if [[ "$WATCH" -eq 1 ]]; then
  while true; do
    clear; show_status
    printf '  [Ctrl+C — refresh 30s]\n'
    sleep 30
  done
else
  show_status
fi
