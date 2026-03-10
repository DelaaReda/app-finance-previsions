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
import urllib.request

ts_now = datetime.now(timezone.utc)
ts_str = ts_now.strftime('%Y-%m-%dT%H:%M:%SZ')
now_ep = ts_now.timestamp()
STATE_DIR = Path(os.environ.get('FC_ROLE_STATE_DIR', '/home/venom/.openclaw/cron/role-state'))
ROOT = Path(os.environ.get('FC_WORKSPACE_ROOT', '.')).resolve()
MONITOR_BASE_URL = os.environ.get('FC_MONITOR_BASE_URL', 'http://127.0.0.1:7779').rstrip('/')
API_BASE_URL = os.environ.get('FC_GATE_API_BASE_URL', 'http://127.0.0.1:8050').rstrip('/')
try:
    HEALTH_HTTP_TIMEOUT = float(os.environ.get('FC_HEALTH_SNAPSHOT_HTTP_TIMEOUT_SECONDS', '15') or '15')
except Exception:
    HEALTH_HTTP_TIMEOUT = 15.0
if HEALTH_HTTP_TIMEOUT <= 0:
    HEALTH_HTTP_TIMEOUT = 15.0

canonical_orch = ROOT / 'docs' / 'operations' / 'orchestrator'
legacy_orch = ROOT / 'docs' / 'orchestrator-ops'
runtime_state_orch = ROOT / 'logs-codex-runs' / 'orchestrator-state'

def _json_dict(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding='utf-8', errors='ignore'))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def _http_json(url: str) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=HEALTH_HTTP_TIMEOUT) as response:
            raw = response.read().decode('utf-8', errors='ignore')
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def resolve_primary_orchestrator_root() -> Path:
    candidates = []
    for d in (runtime_state_orch, canonical_orch, legacy_orch):
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
    return runtime_state_orch

def resolve_orchestrator_json_path(name: str) -> Path:
    candidates = []
    if str(name).startswith('planner-subagents-'):
        candidates.append(runtime_state_orch / name)
    candidates.extend([
        PRIMARY_ORCH / name,
        canonical_orch / name,
        legacy_orch / name,
    ])
    seen = set()
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        if path.exists():
            return path
    return candidates[0]

PRIMARY_ORCH = resolve_primary_orchestrator_root()
RUNTIME_STATE = _json_dict(ROOT / 'logs-codex-runs' / 'orchestrator-state' / 'runtime-state.json')

WRITE_ORCH_ROOTS = []
seen = set()
for d in (runtime_state_orch, canonical_orch, legacy_orch, PRIMARY_ORCH):
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
    return _json_dict(resolve_orchestrator_json_path(str(p)))

def active_planner_subagent_roles() -> list[str]:
    registry = load_json('planner-subagents-registry.json')
    active = registry.get('active', []) if isinstance(registry, dict) else []
    roles = []
    for item in active:
        if not isinstance(item, dict):
            continue
        role = str(item.get('target_role') or '').strip().lower()
        status = str(item.get('status') or '').strip().lower()
        if not role or status in {'', 'merged', 'closed', 'done', 'pass', 'failed', 'blocked'}:
            continue
        if role not in roles:
            roles.append(role)
    return roles

def normalize_widget_state(token) -> str:
    value = str(token or '').strip().lower()
    if value in {'', 'ok', 'healthy', 'pass', 'fresh', 'running'}:
        return 'ok' if value else 'unknown'
    if value in {'stale', 'warm'}:
        return 'stale'
    if value in {'degraded', 'partial', 'fallback', 'unknown'}:
        return 'degraded'
    return 'error'

def endpoint_state(payload: dict) -> str:
    if not isinstance(payload, dict) or not payload:
        return 'error'
    if payload.get('ok') is False:
        return 'error'
    return normalize_widget_state(payload.get('status') or 'ok')

def combine_widget_states(*states: str) -> str:
    rank = {'ok': 0, 'unknown': 1, 'stale': 2, 'degraded': 3, 'error': 4}
    winner = 'ok'
    for state in states:
        token = str(state or 'unknown').strip().lower() or 'unknown'
        if rank.get(token, 3) > rank.get(winner, 0):
            winner = token
    return winner

def build_critical_widget_health() -> dict:
    monitor_status = _http_json(f'{MONITOR_BASE_URL}/api/status')
    recommendations = _http_json(f'{API_BASE_URL}/api/recommendations/daily?limit=3')
    forecasts = _http_json(f'{API_BASE_URL}/api/forecasts?horizon=short&limit=24')
    product_value = monitor_status.get('product_value_metrics', {}) if isinstance(monitor_status, dict) else {}
    product_value = product_value if isinstance(product_value, dict) else {}
    freshness = product_value.get('data_freshness', {}) if isinstance(product_value, dict) else {}
    freshness = freshness if isinstance(freshness, dict) else {}
    news_meta = freshness.get('news', {}) if isinstance(freshness, dict) else {}
    news_meta = news_meta if isinstance(news_meta, dict) else {}
    forecasts_meta = product_value.get('forecasts', {}) if isinstance(product_value, dict) else {}
    forecasts_meta = forecasts_meta if isinstance(forecasts_meta, dict) else {}

    monitor_state = normalize_widget_state(monitor_status.get('health'))
    recommendations_state = endpoint_state(recommendations)
    forecasts_state = combine_widget_states(
        endpoint_state(forecasts),
        normalize_widget_state(forecasts_meta.get('status')),
        normalize_widget_state(forecasts_meta.get('freshness_status')),
    )
    news_state = combine_widget_states(
        monitor_state,
        normalize_widget_state(news_meta.get('state')),
    )
    hero_state = combine_widget_states(monitor_state, recommendations_state)
    judge_state = combine_widget_states(monitor_state, recommendations_state)
    deep_dive_state = combine_widget_states(hero_state, forecasts_state, news_state)
    widgets = {
        'hero': {
            'state': hero_state,
            'monitor_health': str(monitor_status.get('health') or 'unknown'),
            'recommendations_status': str(recommendations.get('status') or 'unknown'),
        },
        'news': {
            'state': news_state,
            'freshness': str(news_meta.get('state') or 'unknown'),
            'updated_at': str(news_meta.get('updated_at') or ''),
        },
        'forecasts': {
            'state': forecasts_state,
            'status': str(forecasts_meta.get('status') or forecasts.get('status') or 'unknown'),
            'freshness': str(forecasts_meta.get('freshness_status') or 'unknown'),
            'updated_at': str(forecasts_meta.get('updated_at') or ''),
        },
        'judge': {
            'state': judge_state,
            'monitor_health': str(monitor_status.get('health') or 'unknown'),
            'recommendations_status': str(recommendations.get('status') or 'unknown'),
        },
        'deep-dive': {
            'state': deep_dive_state,
            'monitor_health': str(monitor_status.get('health') or 'unknown'),
            'recommendations_status': str(recommendations.get('status') or 'unknown'),
            'forecasts_status': str(forecasts_meta.get('status') or forecasts.get('status') or 'unknown'),
        },
    }
    overall_state = 'ok'
    for widget in widgets.values():
        overall_state = combine_widget_states(overall_state, widget.get('state'))
    return {
        'ts_utc': ts_str,
        'state': overall_state,
        'monitor_base_url': MONITOR_BASE_URL,
        'api_base_url': API_BASE_URL,
        'widgets': widgets,
    }

# ── Workboard ────────────────────────────────────────────────────────────────
wb    = load_json('parallel-workstreams.json')
tasks = wb.get('tasks', [])
by_state = defaultdict(int)
for t in tasks: by_state[t.get('state','?')] += 1

done_total = by_state['DONE'] + by_state['CLOSED'] + by_state['PASS']
ready_n    = by_state['READY'] + by_state['READY_PLANNER'] + by_state['READY_DEV']
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
q_ready  = sum(1 for i in queue_rows if str(i.get('state', '')).upper() in {'READY', 'READY_PLANNER', 'READY_DEV'})
q_closed = sum(1 for i in queue_rows if i.get('state') in ('CLOSED','DONE','PASS'))
q_total  = len(queue_rows)

# ── Agents ───────────────────────────────────────────────────────────────────
execution_mode = str(RUNTIME_STATE.get('execution_mode') or '').strip().lower()
scheduled_roles = ['planner'] if execution_mode == 'planner_experimental' else ['planner', 'dev', 'admin']
capability_roles = [role for role in active_planner_subagent_roles() if role not in scheduled_roles]
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

planner_state = agent_states.get('planner')
if isinstance(planner_state, dict):
    planner_blocker = str(planner_state.get('blocker') or '').strip().upper()
    planner_delta = str(planner_state.get('delta') or '').strip().upper()
    planner_soft_blocker = (
        execution_mode == 'planner_experimental'
        and ip_n > 0
        and planner_blocker in {'PLANNER_NO_READY_TASK_AFTER_SYNC', 'DELIVERY_VALUE_INSUFFICIENT'}
    )
    if planner_soft_blocker:
        planner_state['status'] = 'IN_PROGRESS'
        planner_state['verdict'] = 'GO_WITH_CAUTION'
        planner_state['blocker'] = 'NONE'
        if planner_delta in {
            'NO_DELTA',
            'NO_DATA',
            'NONE',
            'SYNC_PRIORITY_THEN_CLAIM_FAILED',
            'DELIVERY_VALUE_INSUFFICIENT',
        }:
            planner_state['delta'] = 'PLANNER_DISPATCH_ACTIVE'

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
    if role in scheduled_roles and (state.get('blocker') or '').upper() not in ('', 'NONE') and not is_rate_limit_state(state)
]
rate_limited_agents = [role for role, state in agent_states.items() if role in scheduled_roles and is_rate_limit_state(state)]
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

stale_agents = [r for r, age in tick_age_min.items() if r in scheduled_roles and age > 45]

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
critical_widget_health = build_critical_widget_health()
critical_widget_state = str(critical_widget_health.get('state') or 'unknown').lower()
if critical_widget_state == 'stale' and health == 'OK':
    health = 'STALE'
elif critical_widget_state in {'degraded', 'error', 'unknown'} and health != 'DEGRADED':
    health = 'DEGRADED'

snapshot = {
    'ts_utc':          ts_str,
    'health':          health,
    'execution_mode':  execution_mode or 'parallel_roles',
    'scheduled_roles': scheduled_roles,
    'capability_roles': capability_roles,
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
    'critical_widget_health': critical_widget_health,
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
    mon['updated_at_utc'] = ts_str
    mon['health'] = health
    mon['velocity'] = snapshot['velocity']
    mon['health_snapshot'] = snapshot
    mon['critical_widget_health'] = critical_widget_health
    try:
        mon_path.write_text(json.dumps(mon, indent=2, ensure_ascii=False), encoding='utf-8')
    except Exception:
        pass

# ── Sortie console ────────────────────────────────────────────────────────────
icon = {'OK':'✅','DEGRADED':'⚠️ ','STALE':'🔶'}.get(health,'❓')
print(f"{ts_str} {icon} health={health}  done={done_total}  ready={ready_n}  "
      f"done_24h={done_24h}  done_7d={done_7d}  "
      f"blocked={blocked_agents}  blocked_detail={blocked_detail}  "
      f"stale={stale_agents}  rl={[r['model'] for r in rl_active]}  rl_detail={rate_limit_detail}  "
      f"critical_widgets={critical_widget_state}")
PY
