#!/usr/bin/env bash
# health_snapshot.sh — Snapshot santé + métriques vélocité
# Appelé en cron toutes les 30min et par monitor_agents.sh
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
WORKSPACE_HELPER="${SCRIPT_DIR}/../platform/automation/lib/workspace_paths.sh"
if [[ -n "${FC_WORKSPACE_ROOT:-}" ]]; then
  ROOT="${FC_WORKSPACE_ROOT}"
elif [[ -f "$WORKSPACE_HELPER" ]]; then
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
import sys
import urllib.request

ts_now = datetime.now(timezone.utc)
ts_str = ts_now.strftime('%Y-%m-%dT%H:%M:%SZ')
now_ep = ts_now.timestamp()
STATE_DIR = Path(os.environ.get('FC_ROLE_STATE_DIR', '/home/venom/.openclaw/cron/role-state'))
ROOT = Path(os.environ.get('FC_WORKSPACE_ROOT', '.')).resolve()
AUTOMATION_ROOT = ROOT / 'platform' / 'automation'
if str(AUTOMATION_ROOT) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_ROOT))
MONITOR_BASE_URL = os.environ.get('FC_MONITOR_BASE_URL', os.environ.get('FC_PUBLIC_MONITOR_BASE_URL', 'http://3.98.20.77:8080')).rstrip('/')
API_BASE_URL = os.environ.get('FC_GATE_API_BASE_URL', os.environ.get('FC_PUBLIC_APP_BASE_URL', 'http://3.98.20.77')).rstrip('/')
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

def _source_version(prefix: str, path: Path) -> str:
    try:
        stat = path.stat()
        digest = __import__('hashlib').sha1(path.read_bytes()).hexdigest()[:12]
        return f"{prefix}_{int(stat.st_mtime)}_{digest}"
    except Exception:
        return ""


def _none_like(value) -> bool:
    token = re.sub(r'[\s_/\-]+', '', str(value or '').strip().lower())
    return token in {'', 'none', 'na', 'null'}


def _stale_context_record(record: dict, queue_version: str, workboard_version: str) -> bool:
    record_queue = str(record.get('queue_version', '')).strip()
    record_workboard = str(record.get('workboard_version', '')).strip()
    queue_mismatch = bool(queue_version and record_queue and record_queue != queue_version)
    workboard_mismatch = bool(workboard_version and record_workboard and record_workboard != workboard_version)
    return queue_mismatch or workboard_mismatch


def _rebuild_monitor_summary(roles_map: dict, queue_version: str, workboard_version: str) -> dict:
    stale_context_roles = sorted(
        name
        for name, data in roles_map.items()
        if isinstance(data, dict) and _stale_context_record(data, queue_version, workboard_version)
    )
    stale_context_set = set(stale_context_roles)
    active_roles = {
        name: data for name, data in roles_map.items() if isinstance(data, dict) and name not in stale_context_set
    }
    issue_roles = sorted(
        name for name, data in active_roles.items() if int(data.get('issue_count', 0) or 0) > 0
    )
    issue_reporting_missing_roles = sorted(
        name for name, data in active_roles.items() if not bool(data.get('issue_reporting_ok', False))
    )
    critical_issue_roles = sorted(
        name
        for name, data in active_roles.items()
        if str(data.get('issue_severity', '')).strip().lower() == 'critical'
    )
    blocker_roles = sorted(
        name for name, data in active_roles.items() if not _none_like(str(data.get('blocker_id', '')))
    )
    request_roles = sorted(
        name
        for name, data in active_roles.items()
        if not _none_like(str(data.get('tool_request', ''))) or not _none_like(str(data.get('skill_request', '')))
    )
    return {
        'roles_total': len(roles_map),
        'fresh_roles_total': len(active_roles),
        'stale_context_open': len(stale_context_roles),
        'issues_open': len(issue_roles),
        'issue_reports_open': len(issue_roles),
        'issue_reporting_missing_count': len(issue_reporting_missing_roles),
        'issue_reporting_missing_roles': issue_reporting_missing_roles[:8],
        'critical_count': len(critical_issue_roles),
        'critical_issue_roles': critical_issue_roles[:8],
        'process_issues_open': 0,
        'delivery_gaps_open': len(issue_roles),
        'delivery_probe_loops_open': 0,
        'flow_gaps_open': 0,
        'blockers_open': len(blocker_roles),
        'tool_skill_requests_open': len(request_roles),
        'issue_roles': issue_roles[:8],
        'process_issue_roles': [],
        'delivery_probe_roles': [],
        'flow_gap_roles': [],
        'delivery_gap_roles': issue_roles[:8],
        'blocker_roles': blocker_roles[:8],
        'tool_skill_request_roles': request_roles[:8],
        'stale_context_roles': stale_context_roles[:8],
        'context_versions': {
            'queue_version': queue_version or 'unknown',
            'workboard_version': workboard_version or 'unknown',
        },
    }

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

def iteration_issue_roles() -> dict:
    candidates = [
        runtime_state_orch / 'agent-iteration-issues-latest.json',
        canonical_orch / 'agent-iteration-issues-latest.json',
        legacy_orch / 'agent-iteration-issues-latest.json',
    ]
    seen = set()
    for path in candidates:
        key = str(path)
        if key in seen or not path.exists():
            continue
        seen.add(key)
        data = _json_dict(path)
        roles = data.get('roles', {}) if isinstance(data, dict) else {}
        if isinstance(roles, dict) and roles:
            return roles
    return {}

def active_planner_subagent_roles() -> list[str]:
    try:
        from runtime.truth.dispatch_snapshot import build_stable_planner_dispatch_snapshot

        snapshot = build_stable_planner_dispatch_snapshot(ROOT, recent_limit=24)
        roles = []
        for item in snapshot.get("active", []):
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "").strip().lower()
            if role and role not in roles:
                roles.append(role)
        return roles
    except Exception:
        return []

def runtime_truth_snapshot() -> dict:
    try:
        from runtime.truth.runtime_truth_reader import build_runtime_truth_snapshot

        snapshot = build_runtime_truth_snapshot(ROOT, state_limit=12, event_limit=24)
        return snapshot if isinstance(snapshot, dict) else {}
    except Exception:
        return {}

def active_cycle_batch_ids(payload: dict) -> list[str]:
    if not isinstance(payload, dict):
        return []
    active_cycle = payload.get('active_cycle')
    if not isinstance(active_cycle, dict):
        return []
    raw_ids = active_cycle.get('active_batch_ids')
    if not isinstance(raw_ids, list):
        return []
    return [str(item).strip().upper() for item in raw_ids if str(item).strip()]

def canonical_runtime_idle(queue_payload: dict, workboard_payload: dict, runtime_truth: dict) -> bool:
    product_delivery_state = runtime_truth.get('product_delivery_state')
    if isinstance(product_delivery_state, dict):
        active_batch_id = str(product_delivery_state.get('active_batch_id') or '').strip().upper()
        delivery_phase = str(product_delivery_state.get('phase') or '').strip()
        if not active_batch_id and delivery_phase in {'product_done_ops_dirty', 'idle_ready_for_next_batch'}:
            return True
    queue_active = active_cycle_batch_ids(queue_payload)
    workboard_active = active_cycle_batch_ids(workboard_payload)
    if queue_active or workboard_active:
        return False
    graph_state_count = int(runtime_truth.get('graph_state_count', 0) or 0)
    recent_event_count = int(runtime_truth.get('recent_event_count', 0) or 0)
    sqlite_path = Path(str(runtime_truth.get('sqlite_path') or '').strip())
    sqlite_present = bool(sqlite_path) and sqlite_path.exists()
    event_store_primary = bool(runtime_truth.get('event_store_primary', False))
    return (event_store_primary or sqlite_present) and graph_state_count == 0 and recent_event_count == 0

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
    monitor_status = _http_json(f'{MONITOR_BASE_URL}/api/status?lite=1')
    api_health = _http_json(f'{API_BASE_URL}/api/health')
    recommendations = _http_json(f'{API_BASE_URL}/api/recommendations/daily?limit=3')
    forecasts = _http_json(f'{API_BASE_URL}/api/forecasts?horizon=short&limit=24')
    api_health_data = api_health.get('data', {}) if isinstance(api_health, dict) else {}
    api_health_data = api_health_data if isinstance(api_health_data, dict) else {}
    last_updates = api_health_data.get('last_updates', {}) if isinstance(api_health_data, dict) else {}
    last_updates = last_updates if isinstance(last_updates, dict) else {}

    # Treat a missing/timeout monitor-lite payload as neutral for product widget
    # health so operator-plane latency does not downgrade an otherwise healthy API.
    monitor_state = 'ok' if not monitor_status else normalize_widget_state(monitor_status.get('health'))
    recommendations_state = endpoint_state(recommendations)
    forecasts_state = combine_widget_states(
        endpoint_state(forecasts),
        normalize_widget_state(api_health_data.get('status') or 'ok'),
        normalize_widget_state('fresh' if last_updates.get('forecasts') else 'unknown'),
    )
    news_state = combine_widget_states(
        monitor_state,
        normalize_widget_state('fresh' if last_updates.get('news') else 'unknown'),
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
            'freshness': 'fresh' if last_updates.get('news') else 'unknown',
            'updated_at': str(last_updates.get('news') or ''),
        },
        'forecasts': {
            'state': forecasts_state,
            'status': str(forecasts.get('status') or api_health_data.get('status') or 'unknown'),
            'freshness': 'fresh' if last_updates.get('forecasts') else 'unknown',
            'updated_at': str(last_updates.get('forecasts') or ''),
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
            'forecasts_status': str(forecasts.get('status') or api_health_data.get('status') or 'unknown'),
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
waiting_dep_n = by_state['WAITING_DEP']

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
q_waiting_dep = sum(1 for i in queue_rows if str(i.get('state', '')).upper() == 'WAITING_DEP')
q_in_progress = sum(1 for i in queue_rows if str(i.get('state', '')).upper() == 'IN_PROGRESS')
runtime_truth = runtime_truth_snapshot()
canonical_idle = canonical_runtime_idle(pq, wb, runtime_truth)

# ── Agents ───────────────────────────────────────────────────────────────────
execution_mode = str(RUNTIME_STATE.get('execution_mode') or '').strip().lower()
scheduled_roles = ['planner'] if execution_mode == 'planner_experimental' else ['planner', 'dev', 'admin']
capability_roles = [role for role in active_planner_subagent_roles() if role not in scheduled_roles]
iteration_roles = iteration_issue_roles()
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

if execution_mode == 'planner_experimental':
    for role in ('dev', 'admin', 'scrum_master'):
        payload = iteration_roles.get(role, {}) if isinstance(iteration_roles, dict) else {}
        if not isinstance(payload, dict):
            continue
        if str(payload.get('source') or '').strip() != 'planner_active_cycle_check':
            continue
        status = str(payload.get('status') or '').strip().upper()
        if not status:
            continue
        if status == 'IN_PROGRESS':
            verdict = 'GO_WITH_CAUTION'
            delta = 'CAPABILITY_ACTIVE'
        elif status in {'READY', 'READY_DEV', 'READY_PLANNER'}:
            verdict = 'GO_WITH_CAUTION'
            delta = 'CAPABILITY_READY'
        elif status == 'WAITING_DEP':
            verdict = 'WAIT'
            delta = 'DEPENDENCY_WAIT'
        elif status == 'PASS':
            verdict = 'PASS'
            delta = 'NO_DELTA'
        elif status == 'BLOCKED':
            verdict = 'BLOCKED'
            delta = 'BLOCKED'
        else:
            verdict = status
            delta = status
        agent_states[role] = {
            'verdict': verdict,
            'status': status,
            'blocker': 'NONE',
            'delta': delta,
        }

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
    planner_residue_only = (
        planner_blocker in {'SQLITE_RUNTIME_RESIDUE_ACTIVE', 'RUNTIME_TRUTH_RESIDUE_ACTIVE'}
        or planner_delta in {
            'REPAIR_ORCHESTRATION_BLOCKED_PAR_RESIDU_SQLITE',
            'AUTOBATCH_BLOQUE_PAR_RESIDU_SQLITE',
        }
    )
    if planner_residue_only:
        no_active_runtime_work = q_ready == 0 and ip_n == 0
        if canonical_idle and no_active_runtime_work:
            planner_state['status'] = 'IDLE'
            planner_state['verdict'] = 'IDLE'
            planner_state['blocker'] = 'NONE'
            planner_state['delta'] = 'NO_ACTIVE_CANONICAL_WORK'

    demotable_planner_statuses = {'PASS', 'WAIT', 'BLOCKED', 'IN_PROGRESS', 'READY', 'UNKNOWN', 'MUTED'}
    if canonical_idle and str(planner_state.get('status') or '').strip().upper() in demotable_planner_statuses:
        if planner_blocker not in {'RUN_LOCK_BUSY', 'LOCK_BUSY', 'RUN_LOCK_HELD', 'BACKEND_API_UNREACHABLE', 'MONITOR_API_UNREACHABLE', 'BACKEND_AND_MONITOR_UNREACHABLE', 'API_DOWN', 'CONTRACT_PARSE_FAILED', 'CONTRACT_GUARD_BLOCK'}:
            planner_state['status'] = 'IDLE'
            planner_state['verdict'] = 'IDLE'
            planner_state['blocker'] = 'NONE'
            planner_state['delta'] = 'NO_ACTIVE_CANONICAL_WORK'

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

if execution_mode == 'planner_experimental' and not capability_roles and q_ready == 0 and ip_n == 0:
    for role in ('dev', 'admin', 'scrum_master'):
        state = agent_states.get(role)
        if not isinstance(state, dict) or role in scheduled_roles:
            continue
        age_min = tick_age_min.get(role, -1)
        if age_min in range(0, 46):
            continue
        if str(state.get('status') or '').strip().upper() == 'PASS' and str(state.get('delta') or '').strip().upper() == 'NO_DELTA':
            state['status'] = 'WAIT'
            state['delta'] = 'NO_ACTIVE_CAPABILITY'

stale_agents = [r for r, age in tick_age_min.items() if r in scheduled_roles and age > 45]

# ── Proofs ───────────────────────────────────────────────────────────────────
proofs_dir = canonical_orch / 'proofs'
if not proofs_dir.exists():
    proofs_dir = PRIMARY_ORCH / 'proofs'
proofs_count = len(list(proofs_dir.iterdir())) if proofs_dir.exists() else 0

# ── Health global ─────────────────────────────────────────────────────────────
latest_summary_stale_context_open = 0
latest_summary_stale_context_roles = []
try:
    existing_mon = json.loads((canonical_orch / 'executors-monitoring-latest.json').read_text(encoding='utf-8', errors='ignore'))
    existing_summary = existing_mon.get('summary', {}) if isinstance(existing_mon, dict) else {}
    if isinstance(existing_summary, dict):
        latest_summary_stale_context_open = int(existing_summary.get('stale_context_open') or 0)
        roles_raw = existing_summary.get('stale_context_roles', [])
        if isinstance(roles_raw, list):
            latest_summary_stale_context_roles = [str(role).strip() for role in roles_raw if str(role).strip()]
except Exception:
    latest_summary_stale_context_open = 0
    latest_summary_stale_context_roles = []

relevant_runtime_roles = set(scheduled_roles) | set(capability_roles)
relevant_stale_context_roles = [
    role
    for role in latest_summary_stale_context_roles
    if role in relevant_runtime_roles and tick_age_min.get(role, -1) not in range(0, 46)
]

delivery_runway_present = any(
    (
        q_ready > 0,
        q_waiting_dep > 0,
        q_in_progress > 0,
        ready_n > 0,
        ip_n > 0,
        waiting_dep_n > 0,
    )
)
rate_limit_backoff_non_blocking = bool((rl_active or rate_limited_agents) and not blocked_agents and delivery_runway_present)
if rate_limit_backoff_non_blocking:
    stale_agents = [role for role in stale_agents if role not in rate_limited_agents]

health = 'OK'
health_reason = 'normal'
if blocked_agents:
    health = 'DEGRADED'
    health_reason = 'hard_blocker'
elif rl_active or rate_limited_agents:
    # Rate-limit is a temporary WAIT state. Keep STALE only when there is no
    # remaining runway for delivery work.
    if rate_limit_backoff_non_blocking:
        health_reason = 'rate_limit_backoff_non_blocking'
    else:
        health = 'STALE'
        health_reason = 'rate_limit_backoff'
if stale_agents and health == 'OK':
    health = 'STALE'
    health_reason = 'stale_ticks'
if latest_summary_stale_context_open > 0 and health == 'OK' and relevant_stale_context_roles:
    # Preserve stale-context protection only for roles that are still part of the
    # current runtime perimeter and still stale now, not for legacy unscheduled roles.
    health = 'STALE'
    health_reason = 'stale_context'
critical_widget_health = build_critical_widget_health()
critical_widget_state = str(critical_widget_health.get('state') or 'unknown').lower()
if critical_widget_state == 'stale' and health == 'OK':
    health = 'STALE'
    health_reason = 'critical_widget_stale'
elif critical_widget_state in {'degraded', 'error', 'unknown'} and health != 'DEGRADED':
    health = 'DEGRADED'
    health_reason = 'critical_widget_degraded'

snapshot = {
    'ts_utc':          ts_str,
    'health':          health,
    'health_reason':   health_reason,
    'execution_mode':  execution_mode or 'parallel_roles',
    'scheduled_roles': scheduled_roles,
    'capability_roles': capability_roles,
    'delivery_runway_present': delivery_runway_present,
    'rate_limit_backoff_non_blocking': rate_limit_backoff_non_blocking,
    'workboard': {
        'total':       len(tasks),
        'done':        done_total,
        'ready':       ready_n,
        'in_progress': ip_n,
        'waiting_dep': waiting_dep_n,
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
        'waiting_dep': q_waiting_dep,
        'in_progress': q_in_progress,
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
    queue_version = _source_version('queue', resolve_orchestrator_json_path('priority-queue.json'))
    workboard_version = _source_version('workboard', resolve_orchestrator_json_path('parallel-workstreams.json'))

    cleared_health_snapshot_fields = {
        'next_action_unique': 'none',
        'next': 'owner=none; action=none',
        'action_summary': 'none',
        'task_update': 'none_no_signal',
        'exec_report': 'none',
        'run_note': 'none',
        'root_cause': 'none',
        'fix_applied': 'none',
        'verify': 'none',
        'issues': 'none',
        'issue_count': 0,
        'issue_severity': 'none',
        'issue_codes': [],
        'issue_reporting_ok': True,
        'issue_reporting_errors': [],
        'suggestions': 'none',
        'stream_id': 'none',
        'task_id': 'none',
        'tool_request': 'none',
        'skill_request': 'none',
        'tools_used': '',
        'channels_read': '',
        'impact_assessment': '',
        'impact_action': '',
    }

    for role, state in agent_states.items():
        entry = roles_map.get(role, {})
        if not isinstance(entry, dict):
            entry = {}
        entry.update(cleared_health_snapshot_fields)
        entry.update({
            'verdict': state['verdict'],
            'status': state['status'],
            'blocker_id': state['blocker'],
            'delta': state['delta'],
            'ts_utc': ts_str,
            'source': 'health_snapshot',
            'queue_version': queue_version,
            'workboard_version': workboard_version,
        })
        roles_map[role] = entry

    mon['generated_at'] = ts_str
    mon['updated_at'] = ts_str
    mon['updated_at_utc'] = ts_str
    mon['health'] = health
    mon['summary'] = _rebuild_monitor_summary(roles_map, queue_version, workboard_version)
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
