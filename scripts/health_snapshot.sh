#!/usr/bin/env bash
# health_snapshot.sh — Snapshot santé + métriques vélocité
# Appelé en cron toutes les 30min et par monitor_agents.sh
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
export FC_WORKSPACE_ROOT="$ROOT"

python3 << 'PY'
import json, re, time
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
import os

ts_now = datetime.now(timezone.utc)
ts_str = ts_now.strftime('%Y-%m-%dT%H:%M:%SZ')
now_ep = ts_now.timestamp()
STATE_DIR = Path('/home/venom/.openclaw/cron/role-state')
ROOT = Path(os.environ.get('FC_WORKSPACE_ROOT', '.')).resolve()

canonical_orch = ROOT / 'docs' / 'operations' / 'orchestrator'
legacy_orch = ROOT / 'docs' / 'orchestrator-ops'

def _json_dict(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding='utf-8', errors='ignore'))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def resolve_primary_orchestrator_root() -> Path:
    candidates = []
    for d in (canonical_orch, legacy_orch):
        if d.exists():
            score = 0.0
            queue_path = d / 'priority-queue.json'
            workboard_path = d / 'parallel-workstreams.json'
            if queue_path.exists():
                score += 40.0
            if workboard_path.exists():
                score += 40.0
            latest = max(
                queue_path.stat().st_mtime if queue_path.exists() else 0.0,
                workboard_path.stat().st_mtime if workboard_path.exists() else 0.0,
            )
            score += min(30.0, max(0.0, (time.time() - latest) / -60.0 + 30.0)) if latest > 0 else 0.0
            candidates.append((score, d))
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    return canonical_orch

PRIMARY_ORCH = resolve_primary_orchestrator_root()

WRITE_ORCH_ROOTS = []
seen = set()
for d in (canonical_orch, legacy_orch, PRIMARY_ORCH):
    try:
        key = str(d.resolve())
    except Exception:
        key = str(d)
    if key in seen:
        continue
    seen.add(key)
    WRITE_ORCH_ROOTS.append(d)

for d in WRITE_ORCH_ROOTS:
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

def load_json(p):
    return _json_dict(PRIMARY_ORCH / p)

# ── Workboard ────────────────────────────────────────────────────────────────
wb    = load_json('parallel-workstreams.json')
tasks = wb.get('tasks', [])
by_state = defaultdict(int)
for t in tasks: by_state[t.get('state','?')] += 1

done_total = by_state['DONE'] + by_state['CLOSED'] + by_state['PASS']
ready_n    = by_state['READY']
ip_n       = by_state['IN_PROGRESS']

# Vélocité: tâches complétées dans les 24h et 7j via updated_at
done_24h = done_7d = 0
for t in tasks:
    if t.get('state') not in ('DONE','CLOSED','PASS'): continue
    ts_raw = t.get('updated_at') or t.get('completed_at') or ''
    if not ts_raw: continue
    try:
        ep = datetime.fromisoformat(ts_raw.replace('Z','+00:00')).timestamp()
        if ep > now_ep - 86400:     done_24h += 1
        if ep > now_ep - 7*86400:   done_7d  += 1
    except: pass

# ── Priority queue ────────────────────────────────────────────────────────────
pq      = load_json('priority-queue.json')
items   = pq.get('items', [])
top_level = [i for i in items if re.fullmatch(r'BATCH-\d{2}', str(i.get('id', '')).strip())]
queue_rows = top_level if top_level else items
q_ready  = sum(1 for i in queue_rows if i.get('state') == 'READY')
q_closed = sum(1 for i in queue_rows if i.get('state') in ('CLOSED','DONE','PASS'))
q_total  = len(queue_rows)

# ── Agents ───────────────────────────────────────────────────────────────────
agent_states = {}
for role in ['planner', 'dev', 'admin']:
    cf = STATE_DIR / f'{role}.last_contract'
    if not cf.exists(): continue
    lines = cf.read_text(encoding='utf-8', errors='ignore').splitlines()
    verdict  = next((l.split(':',1)[-1].strip() for l in lines if l.startswith('VERDICT:')),  '?')
    status   = next((l.split(':',1)[-1].strip() for l in lines if l.startswith('STATUS:')),   '?')
    blocker  = next((l.split(':',1)[-1].strip() for l in lines if l.startswith('BLOCKER_ID:')),'NONE')
    delta    = next((l.split(':',1)[-1].strip() for l in lines if l.startswith('DELTA:')),    '?')
    agent_states[role] = {'verdict': verdict, 'status': status, 'blocker': blocker, 'delta': delta}

def is_rate_limit_state(state):
    blocker = (state.get('blocker') or '').upper()
    status = (state.get('status') or '').upper()
    delta = (state.get('delta') or '').upper()
    return (
        blocker.startswith('AGENT_RATE_LIMIT_')
        or status in ('RATE_LIMIT_SKIP', 'RATE_LIMIT_BACKOFF')
        or delta == 'RATE_LIMIT_BACKOFF'
    )

blocked_agents = [
    role for role, state in agent_states.items()
    if (state.get('blocker') or '').upper() not in ('', 'NONE') and not is_rate_limit_state(state)
]
rate_limited_agents = [role for role, state in agent_states.items() if is_rate_limit_state(state)]
blocked_detail = "|".join(
    f"{role}:{(agent_states.get(role, {}).get('blocker') or 'NONE')}"
    for role in blocked_agents
) if blocked_agents else "none"
rate_limit_detail = "|".join(
    f"{role}:{(agent_states.get(role, {}).get('blocker') or agent_states.get(role, {}).get('status') or 'RATE_LIMIT')}"
    for role in rate_limited_agents
) if rate_limited_agents else "none"

# ── Rate limits ───────────────────────────────────────────────────────────────
rl_active = []
for bin_name in ['codex', 'qwen']:
    f = STATE_DIR / f'{bin_name}.rate_limit_gate_cache'
    if f.exists():
        try:
            until = int(f.read_text(encoding='utf-8', errors='ignore').strip().split('|')[0])
            if until > now_ep:
                rl_active.append({'model': bin_name, 'remaining_s': int(until - now_ep)})
            else:
                f.unlink()
        except: pass

# ── Freshness ticks ───────────────────────────────────────────────────────────
tick_age_min = {}
for role in ['planner', 'dev', 'admin']:
    log = Path(f'logs-codex-runs/fc-ticks/{role}.tick.log')
    if not log.exists(): tick_age_min[role] = -1; continue
    ts_raw = None
    for line in reversed(log.read_text(encoding='utf-8', errors='ignore').splitlines()):
        m = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', line)
        if m and ('[END]' in line or '[SKIP]' in line):
            ts_raw = m.group(1); break
    if ts_raw:
        ep = datetime.strptime(ts_raw, '%Y-%m-%dT%H:%M:%S').astimezone(timezone.utc).timestamp()
        tick_age_min[role] = int((now_ep - ep) / 60)
    else:
        tick_age_min[role] = -1

stale_agents = [r for r, age in tick_age_min.items() if age > 45]

# ── Proofs ───────────────────────────────────────────────────────────────────
proofs_dir = canonical_orch / 'proofs'
if not proofs_dir.exists():
    proofs_dir = PRIMARY_ORCH / 'proofs'
proofs_count = len(list(proofs_dir.iterdir())) if proofs_dir.exists() else 0

# ── Health global ─────────────────────────────────────────────────────────────
health = 'OK'
if blocked_agents:
    health = 'DEGRADED'
elif rl_active or rate_limited_agents:
    # Rate-limit is a temporary WAIT state, not a hard block.
    health = 'STALE'
if stale_agents and health == 'OK':
    health = 'STALE'

snapshot = {
    'ts_utc':          ts_str,
    'health':          health,
    'workboard': {
        'total':       len(tasks),
        'done':        done_total,
        'ready':       ready_n,
        'in_progress': ip_n,
    },
    'velocity': {
        'done_24h':    done_24h,
        'done_7d':     done_7d,
        'proofs':      proofs_count,
    },
    'queue': {
        'total':       q_total,
        'ready':       q_ready,
        'closed':      q_closed,
    },
    'agents':          agent_states,
    'blocked_agents':  blocked_agents,
    'rate_limited_agents': rate_limited_agents,
    'stale_agents':    stale_agents,
    'rate_limits':     rl_active,
    'tick_age_min':    tick_age_min,
}

# ── Append kpi-history.jsonl ──────────────────────────────────────────────────
for orch_dir in WRITE_ORCH_ROOTS:
    # ── Append kpi-history.jsonl ──────────────────────────────────────────────
    jsonl_path = orch_dir / 'kpi-history.jsonl'
    try:
        with open(jsonl_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(snapshot, ensure_ascii=False) + '\n')
    except Exception:
        pass

    # ── Update executors-monitoring-latest.json ───────────────────────────────
    mon_path = orch_dir / 'executors-monitoring-latest.json'
    try:
        mon = json.loads(mon_path.read_text(encoding='utf-8', errors='ignore'))
    except Exception:
        mon = {'roles': {}}

    roles_map = mon.get('roles')
    if not isinstance(roles_map, dict):
        roles_map = {}
        mon['roles'] = roles_map

    for role, state in agent_states.items():
        entry = roles_map.get(role, {})
        if not isinstance(entry, dict):
            entry = {}
        entry.update({'verdict': state['verdict'], 'status': state['status'],
                      'blocker_id': state['blocker'], 'delta': state['delta'],
                      'ts_utc': ts_str, 'source': 'health_snapshot'})
        roles_map[role] = entry

    mon['updated_at'] = ts_str
    mon['health'] = health
    mon['velocity'] = snapshot['velocity']
    try:
        mon_path.write_text(json.dumps(mon, indent=2, ensure_ascii=False), encoding='utf-8')
    except Exception:
        pass

# ── Sortie console ────────────────────────────────────────────────────────────
icon = {'OK':'✅','DEGRADED':'⚠️ ','STALE':'🔶'}.get(health,'❓')
print(f"{ts_str} {icon} health={health}  done={done_total}  ready={ready_n}  "
      f"done_24h={done_24h}  done_7d={done_7d}  "
      f"blocked={blocked_agents}  blocked_detail={blocked_detail}  "
      f"stale={stale_agents}  rl={[r['model'] for r in rl_active]}  rl_detail={rate_limit_detail}")
PY
