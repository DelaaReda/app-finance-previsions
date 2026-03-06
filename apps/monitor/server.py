#!/usr/bin/env python3
"""Finance Copilot — Monitor Web Server — http://localhost:7779"""
from __future__ import annotations
import json, os, re, subprocess, sys, time
import urllib.error
import urllib.request
import socket
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter, defaultdict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - Python without zoneinfo
    ZoneInfo = None

MONITOR_SRC_DIR = Path(__file__).resolve().parent / "src"
if str(MONITOR_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(MONITOR_SRC_DIR))

from collectors import (  # type: ignore
    collect_activity_events as monitor_collect_activity_events,
    collect_message_bus_snapshot as monitor_collect_message_bus_snapshot,
    detect_data_source as monitor_detect_data_source,
    detect_runtime_host_kind as monitor_detect_runtime_host_kind,
    load_workboard_snapshot as monitor_load_workboard_snapshot,
    safe_tail as monitor_safe_tail,
)
from aggregators import (  # type: ignore
    build_active_tasks as monitor_build_active_tasks,
    build_activity_summary as monitor_build_activity_summary,
    build_dependency_map as monitor_build_dependency_map,
    build_system_summary as monitor_build_system_summary,
    build_throughput as monitor_build_throughput,
    collect_role_intentions as monitor_collect_role_intentions,
    compute_health as monitor_compute_health,
    ensure_core_agents as monitor_ensure_core_agents,
)
from api import create_activity_router, create_doctor_router  # type: ignore

def _latest_mtime(paths: list[Path]) -> float:
    latest = 0.0
    for p in paths:
        try:
            if p.exists():
                latest = max(latest, float(p.stat().st_mtime))
        except Exception:
            continue
    return latest

def _workspace_writable(p: Path) -> bool:
    log_dir = p / "logs-codex-runs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        return False
    return os.access(log_dir, os.W_OK)

def _load_json_file(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def _probe_http_ok(url: str, timeout_s: float = 1.2) -> bool:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            status = int(getattr(resp, "status", 0) or 0)
            return 200 <= status < 300
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return False
    except Exception:
        return False

def _orchestrator_root_for_workspace(p: Path) -> Path | None:
    canonical = p / "docs" / "operations" / "orchestrator"
    legacy = p / "docs" / "orchestrator-ops"
    if canonical.exists() and legacy.exists():
        try:
            return canonical if canonical.stat().st_mtime >= legacy.stat().st_mtime else legacy
        except Exception:
            return canonical
    if canonical.exists():
        return canonical
    if legacy.exists():
        return legacy
    return None

def _score_root_candidate(p: Path) -> float:
    score = 0.0
    orch = _orchestrator_root_for_workspace(p)
    if orch is not None:
        score += 100.0
        queue_file = orch / "priority-queue.json"
        workboard_file = orch / "parallel-workstreams.json"
        queue_data = _load_json_file(queue_file) if queue_file.exists() else {}
        workboard_data = _load_json_file(workboard_file) if workboard_file.exists() else {}
        queue_items = queue_data.get("items", [])
        workboard_tasks = workboard_data.get("tasks", [])
        if isinstance(queue_items, list):
            score += min(40.0, float(len(queue_items)))
        if isinstance(workboard_tasks, list):
            score += min(40.0, float(len(workboard_tasks)))
        if queue_file.exists():
            score += 8.0
        if workboard_file.exists():
            score += 8.0
    tick_dir = p / "logs-codex-runs" / "fc-ticks"
    runner_dir = p / "logs-codex-runs" / "role-runner"
    if tick_dir.exists():
        score += 60.0
    if runner_dir.exists():
        score += 25.0
    if _workspace_writable(p):
        score += 55.0
    else:
        score -= 80.0
    # Bias toward the workspace that has the freshest runtime traces.
    tick_logs = list(tick_dir.glob("*.tick.log")) if tick_dir.exists() else []
    runner_logs = list(runner_dir.glob("*.live.log")) if runner_dir.exists() else []
    latest = _latest_mtime(tick_logs + runner_logs)
    if latest > 0:
        # More recent is better: invert by subtracting age bucket.
        age_minutes = max(0.0, (time.time() - latest) / 60.0)
        score += max(0.0, 80.0 - min(80.0, age_minutes))
    # Shared mounts can drift/lag; prefer canonical workspace unless explicitly forced.
    if "/shared/" in str(p):
        score -= 25.0
    return score

def resolve_root() -> Path:
    env_root = os.environ.get("FC_MONITOR_ROOT", "").strip()
    if env_root:
        p = Path(env_root).expanduser()
        if p.exists():
            return p
    candidates = [
        Path("/home/venom/analyse-financiere"),
        Path("/home/venom/shared/analyse-financiere"),
        Path.home() / "Documents" / "analyse-financiere",
        Path(__file__).resolve().parents[2],
    ]
    scored: list[tuple[float, Path]] = []
    for p in candidates:
        if not p.exists():
            continue
        scored.append((_score_root_candidate(p), p))
    if scored:
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]
    return Path(__file__).resolve().parents[2]


ROOT = resolve_root()
STATE = Path(os.environ.get("FC_MONITOR_STATE_DIR", "/home/venom/.openclaw/cron/role-state")).expanduser()
INSTANCE_ID = os.environ.get(
    "FC_MONITOR_INSTANCE_ID",
    f"{socket.gethostname()}:{ROOT}",
)


def _runner_config_path(root: Path) -> Path:
    primary = root / "platform" / "config" / "runner" / "runner.v1.yaml"
    if primary.exists():
        return primary
    return root / "platform" / "config" / "runner" / "runner_config.v1.yaml"


def _bool_token(value: object, default: bool = False) -> bool:
    token = str(value or "").strip()
    if not token:
        return default
    return token not in {"0", "false", "False"}


def _planner_orchestrator_flags(root: Path) -> tuple[bool, bool]:
    config = _load_json_file(_runner_config_path(root))
    features = config.get("features", {}) if isinstance(config, dict) else {}
    planner = features.get("planner_orchestrator", {}) if isinstance(features, dict) else {}
    enabled = _bool_token(os.environ.get("FC_PLANNER_ORCHESTRATOR_ENABLED"), _bool_token(planner.get("enabled"), False))
    cron_planner_only = _bool_token(
        os.environ.get("FC_PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY"),
        _bool_token(planner.get("cron_planner_only"), False),
    )
    experimental = os.environ.get("FC_EXPERIMENTAL_PLANNER_ONLY", "").strip()
    if experimental:
        enabled = _bool_token(experimental, enabled)
        cron_planner_only = _bool_token(experimental, cron_planner_only)
    return enabled, cron_planner_only


def _execution_mode(root: Path) -> str:
    enabled, cron_planner_only = _planner_orchestrator_flags(root)
    if enabled and cron_planner_only:
        return "planner_experimental"
    return "parallel_roles"


def _core_roles_for_root(root: Path) -> tuple[str, ...]:
    if _execution_mode(root) == "planner_experimental":
        return ("planner",)
    return ("planner", "dev", "admin", "scrum_master")


CORE_ROLES = _core_roles_for_root(ROOT)
ERROR_FEED_RECENT_MINUTES = max(10, int(os.environ.get("FC_MONITOR_ERROR_FEED_RECENT_MINUTES", "90")))
RUNTIME_DIAG_RECENT_MINUTES = max(10, int(os.environ.get("FC_MONITOR_RUNTIME_DIAG_RECENT_MINUTES", "90")))
AGENT_MESSAGES_RECENT_MINUTES = max(10, int(os.environ.get("FC_MONITOR_AGENT_MESSAGES_RECENT_MINUTES", "1440")))
ACTIVITY_FEED_ENABLED = str(os.environ.get("FC_MONITOR_ACTIVITY_FEED_ENABLED", "1")).strip() not in {"0", "false", "False"}
ACTIVITY_FEED_WINDOW_HOURS = max(1, int(os.environ.get("FC_MONITOR_ACTIVITY_WINDOW_HOURS", "6")))
ACTIVITY_FEED_MAX_EVENTS = max(50, int(os.environ.get("FC_MONITOR_ACTIVITY_MAX_EVENTS", "300")))
DEPENDENCY_MAP_ENABLED = str(os.environ.get("FC_MONITOR_DEP_GRAPH_ENABLED", "1")).strip() not in {"0", "false", "False"}
DEFAULT_SCHEDULE_MAP = {
    "planner": [0, 22, 44],
    "dev": [6, 28, 50],
    "admin": [12, 34, 56],
    "scrum_master": [3, 18, 33, 48],
}
ROLE_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")
ORCH_ROOT = _orchestrator_root_for_workspace(ROOT) or (ROOT / "docs" / "operations" / "orchestrator")
CANONICAL_ORCH_ROOT = ROOT / "docs" / "operations" / "orchestrator"
LEGACY_ORCH_ROOT = ROOT / "docs" / "orchestrator-ops"
ITERATION_ISSUES_EVENTS_FILE = Path(
    os.environ.get(
        "FC_MONITOR_ITERATION_ISSUES_EVENTS_FILE",
        str(CANONICAL_ORCH_ROOT / "agent-iteration-issues.jsonl"),
    )
).expanduser()
ITERATION_ISSUES_LATEST_FILE = Path(
    os.environ.get(
        "FC_MONITOR_ITERATION_ISSUES_LATEST_FILE",
        str(CANONICAL_ORCH_ROOT / "agent-iteration-issues-latest.json"),
    )
).expanduser()
# Backward-compat alias.
ITERATION_EVENTS_FILE = ITERATION_ISSUES_EVENTS_FILE
PLANNER_AUTONOMY_STATE_FILE = Path(
    os.environ.get(
        "FC_MONITOR_PLANNER_AUTONOMY_STATE_FILE",
        str(STATE / "planner_autonomy_state.json"),
    )
).expanduser()
ADMIN_TSHAPE_STATE_FILE = Path(
    os.environ.get(
        "FC_MONITOR_ADMIN_TSHAPE_STATE_FILE",
        str(STATE / "admin.tshape.state.json"),
    )
).expanduser()
ADMIN_AUTONOMY_STATE_FILE = Path(
    os.environ.get(
        "FC_MONITOR_ADMIN_AUTONOMY_STATE_FILE",
        str(STATE / "admin_autonomy_state.json"),
    )
).expanduser()
ADMIN_DISPATCH_LOG_FILE = Path(
    os.environ.get(
        "FC_MONITOR_ADMIN_DISPATCH_LOG_FILE",
        str(ROOT / "logs-codex-runs" / "fc-ticks" / "admin.dispatch.log"),
    )
).expanduser()
AGENT_MESSAGE_BUS_FILE = Path(
    os.environ.get(
        "FC_MONITOR_AGENT_MESSAGE_BUS_FILE",
        str(ROOT / "docs" / "ops" / "AGENT_MESSAGE_BUS.jsonl"),
    )
).expanduser()
PO_SCRUM_MASTER_REPORT_FILE = Path(
    os.environ.get(
        "FC_MONITOR_PO_SCRUM_MASTER_REPORT_FILE",
        str(ROOT / "docs" / "ops" / "PO_SCRUM_MASTER_REPORTS.md"),
    )
).expanduser()
DOCTOR_SCRIPT_FILE = Path(
    os.environ.get(
        "FC_MONITOR_DOCTOR_SCRIPT",
        str(ROOT / "scripts" / "fc_doctor.sh"),
    )
).expanduser()
DOCTOR_CACHE_TTL_SECONDS = max(5, int(os.environ.get("FC_MONITOR_DOCTOR_CACHE_TTL_SECONDS", "120")))
DOCTOR_RUN_TIMEOUT_SECONDS = max(2, int(os.environ.get("FC_MONITOR_DOCTOR_RUN_TIMEOUT_SECONDS", "4")))
_DOCTOR_CACHE: dict[str, object] = {"ts": 0.0, "payload": None}
_DOCTOR_RUNNING = False


def _iteration_issue_event_sources() -> list[Path]:
    candidates: list[Path] = []
    seen: set[str] = set()
    raw_candidates = [
        ITERATION_EVENTS_FILE,
        ITERATION_ISSUES_EVENTS_FILE,
        CANONICAL_ORCH_ROOT / "agent-iteration-issues.jsonl",
        LEGACY_ORCH_ROOT / "agent-iteration-issues.jsonl",
        ROOT / "logs-codex-runs" / "executor-monitoring" / "events.jsonl",
    ]
    for path in raw_candidates:
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(path)
    return candidates


def _message_bus_snapshot(now_iso: str) -> dict:
    return monitor_collect_message_bus_snapshot(
        bus_file=AGENT_MESSAGE_BUS_FILE,
        now_iso=now_iso,
        recent_minutes=AGENT_MESSAGES_RECENT_MINUTES,
        core_roles=CORE_ROLES,
    )


def _po_scrum_master_snapshot(message_bus_snapshot: dict) -> dict:
    def _lock_skip_streak(role_name: str) -> int:
        events_path = ROOT / f"logs-codex-runs/role-runner/{role_name}.events.log"
        lines = _tail_lines(events_path, 240)
        if not lines:
            return 0
        streak = 0
        seen_lock_event = False
        for raw in reversed(lines):
            line = str(raw or "").strip().lower()
            if "trilock_busy" in line or "trilock_skip" in line:
                streak += 1
                seen_lock_event = True
                continue
            if "trilock_acquired" in line:
                return streak if seen_lock_event else 0
            if seen_lock_event and "event=" in line:
                break
        return streak if seen_lock_event else 0

    role = "scrum_master"
    role_contract = contract(role)
    role_tick_age = tick_age(role)
    now_epoch = time.time()
    run_ts = ""
    report_ts = ""
    report_age_min = -1
    role_contract_file = STATE / f"{role}.last_contract"
    if role_contract_file.exists():
        try:
            run_mtime = float(role_contract_file.stat().st_mtime)
            run_ts = (
                datetime.fromtimestamp(run_mtime, tz=timezone.utc)
                .isoformat()
                .replace("+00:00", "Z")
            )
        except Exception:
            run_ts = ""
    if PO_SCRUM_MASTER_REPORT_FILE.exists():
        try:
            mtime = float(PO_SCRUM_MASTER_REPORT_FILE.stat().st_mtime)
            report_ts = (
                datetime.fromtimestamp(mtime, tz=timezone.utc)
                .isoformat()
                .replace("+00:00", "Z")
            )
            report_age_min = max(0, int((now_epoch - mtime) // 60))
        except Exception:
            report_ts = ""
            report_age_min = -1

    advisory_active = role_tick_age is not None and role_tick_age >= 0 and role_tick_age <= 180
    recent_posts = []
    for item in message_bus_snapshot.get("recent_posts", []) if isinstance(message_bus_snapshot, dict) else []:
        source = str(item.get("from", "")).strip().lower()
        if source in {"scrum_master", "po_scrum_master"}:
            recent_posts.append(item)
    tick_tail = _tail_lines(ROOT / f"logs-codex-runs/fc-ticks/{role}.tick.log", 24)
    runner_tail = _tail_lines(ROOT / f"logs-codex-runs/role-runner/{role}.live.log", 24)
    events_tail = _tail_lines(ROOT / f"logs-codex-runs/role-runner/{role}.events.log", 24)
    lock_skip_streak = _lock_skip_streak(role)
    return {
        "name": "po_scrum_master",
        "lane_role": "scrum_master",
        "mode": "scheduled_advisory",
        "active": advisory_active,
        "last_run": run_ts,
        "last_run_age_min": role_tick_age if role_tick_age is not None else -1,
        "status": role_contract.get("STATUS", "UNKNOWN") if role_contract else "UNKNOWN",
        "verdict": role_contract.get("VERDICT", "UNKNOWN") if role_contract else "UNKNOWN",
        "blocker": role_contract.get("BLOCKER_ID", "NONE") if role_contract else "NONE",
        "next": role_contract.get("NEXT", "") if role_contract else "",
        "last_report_path": str(PO_SCRUM_MASTER_REPORT_FILE),
        "last_report_ts": report_ts,
        "last_report_age_min": report_age_min,
        "lock_skip_streak": lock_skip_streak,
        "last_messages_posted": len(recent_posts),
        "recent_messages": recent_posts[:5],
        "tick_tail": tick_tail,
        "runner_tail": runner_tail,
        "events_tail": events_tail,
        "source": "runtime_contract" if role_contract else "monitor_snapshot",
    }


def _dynamic_workers_snapshot() -> dict:
    registry_path = orchestrator_file("dynamic-workers-registry.json")
    payload = _load_json_file(registry_path) if registry_path.exists() else {}
    workers = payload.get("workers", []) if isinstance(payload, dict) else []
    if not isinstance(workers, list):
        workers = []
    active = []
    recent = []
    for item in workers:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", "")).strip().lower()
        normalized = {
            "worker_id": str(item.get("worker_id", "")),
            "worker_type": str(item.get("worker_type", "")),
            "parent_role": str(item.get("parent_role", "")),
            "owner_task_id": str(item.get("owner_task_id", "")),
            "status": str(item.get("status", "")),
            "summary": str(item.get("summary", "")),
            "artifact": str(item.get("artifact", "")),
            "last_update_at": str(item.get("last_update_at", "")),
        }
        if status in {"spawned", "running"}:
            active.append(normalized)
        else:
            recent.append(normalized)
    return {
        "enabled": str(os.environ.get("FC_DYNAMIC_WORKERS_ENABLED", "0")).strip() not in {"0", "false", "False"},
        "registry_path": str(registry_path),
        "active_count": len(active),
        "active": active[:8],
        "recent": recent[-8:],
    }


def _planner_subagents_snapshot() -> dict:
    registry_path = orchestrator_file("planner-subagents-registry.json")
    payload = _load_json_file(registry_path) if registry_path.exists() else {}
    subagents = payload.get("subagents", []) if isinstance(payload, dict) else []
    if not isinstance(subagents, list):
        subagents = []
    active = []
    recent = []
    for item in subagents:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", "")).strip().lower()
        normalized = {
            "subagent_id": str(item.get("subagent_id", "")),
            "target_role": str(item.get("target_role", "")),
            "parent_role": str(item.get("parent_role", "")),
            "owner_task_id": str(item.get("owner_task_id", "")),
            "status": str(item.get("status", "")),
            "summary": str(item.get("summary", "")),
            "artifact": str(item.get("artifact", "")),
            "last_update_at": str(item.get("last_update_at", "")),
        }
        if status in {"spawned", "running"}:
            active.append(normalized)
        else:
            recent.append(normalized)
    enabled, cron_planner_only = _planner_orchestrator_flags(ROOT)
    return {
        "enabled": enabled,
        "cron_planner_only": cron_planner_only,
        "registry_path": str(registry_path),
        "active_count": len(active),
        "active": active[:8],
        "recent": recent[-8:],
    }


def _activity_bundle(window_hours: int, limit: int) -> dict:
    if not ACTIVITY_FEED_ENABLED:
        return {
            "enabled": False,
            "window_hours": int(window_hours),
            "limit": int(limit),
            "timeline": [],
            "throughput": {
                "tasks_completed_last_hour": 0,
                "artifacts_generated_last_hour": 0,
                "delivery_rate": 0.0,
            },
            "intentions": {},
            "quality": {},
            "tasks_active": [],
            "dependencies": {
                "nodes": [],
                "edges": [],
                "bottlenecks": [],
                "summary": {"nodes": 0, "edges": 0, "waiting_dep_tasks": 0, "bottleneck_count": 0},
                "explanations": [],
            },
            "system_summary": {
                "what_changed_last_15m": [],
                "events_by_role_last_15m": {},
                "current_bottleneck": "none",
                "recommended_next_action": "monitor",
                "intentions": {},
                "decision_trace_quality": {},
            },
            "sources": {},
        }

    safe_window = max(1, min(int(window_hours), 72))
    safe_limit = max(20, min(int(limit), 1000))
    workboard_snapshot = monitor_load_workboard_snapshot(ROOT)
    activity = monitor_collect_activity_events(
        root=ROOT,
        state_dir=STATE,
        window_hours=safe_window,
        limit=safe_limit,
    )
    timeline = activity.get("timeline", []) if isinstance(activity, dict) else []
    if not isinstance(timeline, list):
        timeline = []
    active_tasks = monitor_build_active_tasks(
        tasks=workboard_snapshot.get("tasks", []) if isinstance(workboard_snapshot, dict) else [],
        timeline=timeline,
        limit=min(240, safe_limit),
    )
    dependency_map = (
        monitor_build_dependency_map(workboard_snapshot.get("tasks", []) if isinstance(workboard_snapshot, dict) else [])
        if DEPENDENCY_MAP_ENABLED
        else {"nodes": [], "edges": [], "bottlenecks": [], "summary": {}, "explanations": []}
    )
    intentions_payload = monitor_collect_role_intentions(STATE)
    throughput = monitor_build_throughput(timeline)
    system_summary = monitor_build_system_summary(
        timeline=timeline,
        intentions=intentions_payload,
        dependency_map=dependency_map,
        active_tasks=active_tasks,
    )
    return {
        "enabled": True,
        "window_hours": safe_window,
        "limit": safe_limit,
        "timeline": timeline,
        "throughput": throughput,
        "intentions": intentions_payload.get("intentions", {}) if isinstance(intentions_payload, dict) else {},
        "quality": intentions_payload.get("decision_trace_quality", {}) if isinstance(intentions_payload, dict) else {},
        "tasks_active": active_tasks,
        "dependencies": dependency_map,
        "system_summary": system_summary,
        "sources": {
            **(activity.get("sources", {}) if isinstance(activity, dict) else {}),
            **(workboard_snapshot.get("paths", {}) if isinstance(workboard_snapshot, dict) else {}),
        },
    }


def _activity_summary_from_bundle(bundle: dict) -> dict:
    timeline = bundle.get("timeline", []) if isinstance(bundle, dict) else []
    if not isinstance(timeline, list):
        timeline = []
    summary = monitor_build_activity_summary(timeline)
    if not isinstance(summary, dict):
        summary = {}
    summary.setdefault("events_last_1h", 0)
    summary.setdefault("events_last_6h", 0)
    summary.setdefault("tasks_progressed_last_1h", 0)
    summary.setdefault("last_action_by_role", {})
    summary.setdefault("current_bottleneck", "none")
    return summary


def doctor_snapshot(force_refresh: bool = False) -> dict:
    global _DOCTOR_RUNNING
    now = time.time()
    cached_payload = _DOCTOR_CACHE.get("payload")
    cached_ts = float(_DOCTOR_CACHE.get("ts") or 0.0)
    if not force_refresh and isinstance(cached_payload, dict) and (now - cached_ts) <= DOCTOR_CACHE_TTL_SECONDS:
        return cached_payload

    # Prevent recursive refresh loops:
    # /api/status -> doctor_snapshot -> fc_doctor.sh -> /api/status.
    if _DOCTOR_RUNNING:
        if isinstance(cached_payload, dict) and cached_payload:
            return cached_payload
        return {
            "status": "degraded",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "checks": {},
            "meta": {
                "schema_version": "doctor.v1",
                "note": "doctor_refresh_in_progress",
            },
        }

    if not DOCTOR_SCRIPT_FILE.exists():
        payload = {
            "status": "error",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "checks": {},
            "meta": {
                "schema_version": "doctor.v1",
                "error": f"doctor script missing: {DOCTOR_SCRIPT_FILE}",
                "duration_ms": 0,
            },
        }
        _DOCTOR_CACHE["payload"] = payload
        _DOCTOR_CACHE["ts"] = now
        return payload

    try:
        _DOCTOR_RUNNING = True
        try:
            cp = subprocess.run(
                [str(DOCTOR_SCRIPT_FILE), "--json"],
                text=True,
                capture_output=True,
                check=False,
                timeout=DOCTOR_RUN_TIMEOUT_SECONDS,
                cwd=str(ROOT),
            )
            payload = {}
            try:
                payload = json.loads(cp.stdout or "{}")
            except Exception:
                payload = {}
            if not isinstance(payload, dict):
                payload = {}
            if not payload:
                payload = {
                    "status": "error",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "checks": {},
                    "meta": {
                        "schema_version": "doctor.v1",
                        "error": "doctor_invalid_json",
                        "rc": cp.returncode,
                        "stderr": (cp.stderr or "")[:240],
                    },
                }
            else:
                meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
                if not isinstance(meta, dict):
                    meta = {}
                meta["rc"] = cp.returncode
                payload["meta"] = meta
        except Exception as exc:
            payload = {
                "status": "error",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "checks": {},
                "meta": {
                    "schema_version": "doctor.v1",
                    "error": f"doctor_exec_failed:{exc}",
                },
            }
    finally:
        _DOCTOR_RUNNING = False

    _DOCTOR_CACHE["payload"] = payload
    _DOCTOR_CACHE["ts"] = now
    return payload


def _ordered_roles(roles: list[str] | set[str] | tuple[str, ...]) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for role in roles:
        r = (role or "").strip()
        if not r or not ROLE_NAME_RE.fullmatch(r):
            continue
        if r in seen:
            continue
        seen.add(r)
        cleaned.append(r)
    priority = list(CORE_ROLES)
    ordered = [r for r in priority if r in cleaned]
    ordered += sorted(r for r in cleaned if r not in priority)
    return tuple(ordered)


def _roles_from_topology() -> tuple[str, ...]:
    candidates = [
        ROOT / "docs" / "operations" / "orchestrator" / "parallel-role-topology-active.json",
        ROOT / "docs" / "orchestrator-ops" / "parallel-role-topology-active.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        roles_raw = data.get("roles") if isinstance(data, dict) else None
        if not isinstance(roles_raw, list):
            continue
        roles: list[str] = []
        for item in roles_raw:
            if isinstance(item, str):
                role = item.strip()
                if role:
                    roles.append(role)
                continue
            if not isinstance(item, dict):
                continue
            role = str(item.get("role", "")).strip()
            enabled = item.get("enabled", True)
            if role and enabled is not False:
                roles.append(role)
        ordered = _ordered_roles(roles)
        if ordered:
            return ordered
    return ()


def _roles_from_crontab() -> tuple[str, ...]:
    try:
        proc = subprocess.run(
            ["crontab", "-l"],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        return ()
    if proc.returncode != 0:
        return ()
    roles: list[str] = []
    for line in (proc.stdout or "").splitlines():
        if "fc_agent_tick.sh" not in line:
            continue
        m = re.search(r"fc_agent_tick\.sh\s+([A-Za-z0-9_]+)", line)
        if not m:
            continue
        roles.append(m.group(1).strip())
    ordered = _ordered_roles(roles)
    return ordered if ordered else ()

def discover_roles() -> tuple[str, ...]:
    env_roles = [r.strip() for r in os.environ.get("FC_MONITOR_ROLES", "").split(",") if r.strip()]
    if env_roles:
        ordered = _ordered_roles(env_roles)
        if ordered:
            return ordered
    cron_roles = _roles_from_crontab()
    if cron_roles:
        return cron_roles
    topology_roles = _roles_from_topology()
    if topology_roles:
        return topology_roles
    return CORE_ROLES


def active_roles() -> tuple[str, ...]:
    roles = discover_roles()
    return roles if roles else CORE_ROLES


def _role_has_monitor_artifacts(role: str) -> bool:
    candidate = str(role or "").strip()
    if not candidate or not ROLE_NAME_RE.fullmatch(candidate):
        return False
    probes = (
        ROOT / f"logs-codex-runs/fc-ticks/{candidate}.tick.log",
        ROOT / f"logs-codex-runs/fc-ticks/{candidate}.cron.log",
        ROOT / f"logs-codex-runs/role-runner/{candidate}.live.log",
        ROOT / f"logs-codex-runs/role-runner/{candidate}.events.log",
        STATE / f"{candidate}.last_contract",
    )
    for path in probes:
        if not path.exists():
            continue
        try:
            if path.stat().st_size > 0:
                return True
        except Exception:
            return True
    return False


def monitor_roles() -> tuple[str, ...]:
    roles = list(active_roles())
    for core_role in CORE_ROLES:
        if core_role not in roles:
            roles.append(core_role)
    if "scrum_master" not in roles:
        if _role_has_monitor_artifacts("scrum_master") or PO_SCRUM_MASTER_REPORT_FILE.exists():
            roles.append("scrum_master")
    ordered = _ordered_roles(roles)
    return ordered if ordered else CORE_ROLES


ROLE_CANONICAL_MAP = {
    "analyst": "planner",
    "architect": "planner",
    "po": "planner",
    "po_scrum_master": "scrum_master",
    "backend_engineer": "dev",
    "frontend_engineer": "dev",
    "data_analyst": "dev",
    "infra_engineer": "dev",
    "integrator": "dev",
    "tester": "dev",
    "qa": "dev",
    "clawsentinel": "admin",
}


def canonical_role(role: str) -> str:
    raw = (role or "").strip()
    if not raw:
        return "?"
    return ROLE_CANONICAL_MAP.get(raw, raw)


def _batch_sort_key(batch_id: str) -> tuple[int, str]:
    m = re.search(r"BATCH-(\d+)", str(batch_id or ""))
    return (int(m.group(1)) if m else 10**9, str(batch_id or ""))


def _merge_queue_display_rows(queue_items: list[dict], derived_batches: list[dict]) -> list[dict]:
    """Use queue as source-of-truth for list coverage and derived batches for live task counters."""
    derived_map: dict[str, dict] = {
        str(b.get("id", "")).strip(): b for b in derived_batches if str(b.get("id", "")).strip()
    }
    rows: list[dict] = []
    seen: set[str] = set()

    for item in queue_items:
        batch_id = str(item.get("id", "")).strip()
        if not batch_id:
            continue
        row = {
            "id": batch_id,
            "state": str(item.get("state", "")).upper() or "UNKNOWN",
        }
        if batch_id in derived_map:
            row.update(derived_map[batch_id])
            row["state"] = str(row.get("state", "")).upper() or "UNKNOWN"
        rows.append(row)
        seen.add(batch_id)

    for batch_id, derived in derived_map.items():
        if batch_id in seen:
            continue
        row = dict(derived)
        row["id"] = batch_id
        row["state"] = str(row.get("state", "")).upper() or "UNKNOWN"
        rows.append(row)

    rows.sort(key=lambda r: _batch_sort_key(str(r.get("id", ""))))
    return rows


LOG_KIND_LABELS = {
    "tick": "fc-ticks",
    "cron": "fc-cron",
    "runner": "runner-live",
    "events": "runner-events",
    "contract": "last-contract",
}

app = FastAPI(docs_url=None, redoc_url=None)
app.include_router(create_doctor_router(doctor_snapshot))
app.include_router(
    create_activity_router(
        lambda window, limit: _activity_bundle(window, limit),
        lambda window, limit: (
            lambda safe_window, safe_limit, items: {
                "window_hours": safe_window,
                "limit": safe_limit,
                "items": items,
                "tasks": items,
                "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
        )(
            max(1, min(int(window), 72)),
            max(10, min(int(limit), 300)),
            _activity_bundle(window, max(limit, 120)).get("tasks_active", [])[: max(10, min(int(limit), 300))],
        ),
        lambda limit: {
            **(_activity_bundle(ACTIVITY_FEED_WINDOW_HOURS, max(limit, ACTIVITY_FEED_MAX_EVENTS)).get("dependencies", {})),
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    )
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def jload(p):
    try: return json.loads(Path(p).read_text(encoding="utf-8"))
    except: return {}

def orchestrator_file(rel: str) -> Path:
    rel = (rel or "").strip().lstrip("/")
    canonical = ROOT / "docs" / "operations" / "orchestrator" / rel
    legacy = ROOT / "docs" / "orchestrator-ops" / rel
    existing = [p for p in (canonical, legacy) if p.exists()]
    if existing:
        try:
            existing.sort(key=lambda p: float(p.stat().st_mtime), reverse=True)
        except Exception:
            pass
        return existing[0]
    return canonical


def monitor_latest_snapshot() -> dict:
    data = jload(orchestrator_file("executors-monitoring-latest.json"))
    return data if isinstance(data, dict) else {}

def dev_parent_snapshot() -> dict:
    path = ROOT / "logs-codex-runs" / "dev-parent" / "latest.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _dev_autonomy_from_parent(parent: dict | None) -> dict:
    data = parent if isinstance(parent, dict) else {}
    return {
        "coaching_state": str(data.get("coaching_state", "RECOVERING") or "RECOVERING"),
        "none_no_signal_streak_24h": _int_or_default(data.get("none_signal_streak_24h"), 0),
        "channels_missing_streak_24h": _int_or_default(data.get("channels_missing_streak_24h"), 0),
        "contract_guard_block_count_24h": _int_or_default(data.get("contract_guard_block_count_24h"), 0),
        "issue_reporting_ok_rate_24h": _int_or_default(data.get("issue_reporting_ok_rate_24h"), 100),
        "delivery_actions_24h": _int_or_default(data.get("delivery_actions_24h"), 0),
        "enforced_delivery_count_24h": _int_or_default(data.get("enforced_delivery_count_24h"), 0),
        "stall_recovery_rate_24h": _int_or_default(data.get("stall_recovery_rate_24h"), 100),
        "ready_seen_without_claim_24h": _int_or_default(data.get("ready_seen_without_claim_24h"), 0),
    }

def contract(role):
    f = STATE / f"{role}.last_contract"
    if not f.exists(): return {}
    d = {}
    for l in f.read_text(encoding="utf-8", errors="ignore").splitlines():
        if ":" in l:
            k,_,v = l.partition(":"); d[k.strip()] = v.strip()
    return d

def contract_raw(role):
    f = STATE / f"{role}.last_contract"
    if not f.exists(): return ""
    return f.read_text(encoding="utf-8", errors="ignore")

def parse_evidence_kv(evidence_line: str) -> dict[str, str]:
    out: dict[str, str] = {}
    raw = (evidence_line or "").strip()
    if not raw:
        return out
    for part in raw.split(";"):
        seg = part.strip()
        if not seg or "=" not in seg:
            continue
        k, v = seg.split("=", 1)
        key = k.strip()
        if not key:
            continue
        out[key] = v.strip()
    return out

WEAK_EVIDENCE_MARKERS = {
    "?",
    "??",
    "???",
    "tbd",
    "todo",
    "to_do",
    "fixme",
    "a_faire",
    "coming_soon",
    "unknown",
    "pending",
    "later",
}
ISSUE_CODE_RE = re.compile(r"^[a-z0-9_]{3,64}$")
ISSUE_SEVERITIES = {"none", "low", "medium", "high", "critical"}
ISSUE_BLOCKED_MIN_SEVERITIES = {"medium", "high", "critical"}


def _is_empty_marker(value: str) -> bool:
    token = re.sub(r"\s+", "", str(value or "").strip().lower())
    return token in {"", "none", "na", "n/a", "null", "-", "non", "aucun", "aucune"}


def _is_placeholder_marker(value: str) -> bool:
    token = re.sub(r"\s+", "", str(value or "").strip().lower())
    if token in WEAK_EVIDENCE_MARKERS:
        return True
    return bool(re.fullmatch(r"[?.!_~\-]+", token))


def _is_weak_evidence(value: str) -> bool:
    text = str(value or "").strip()
    if _is_empty_marker(text) or _is_placeholder_marker(text):
        return True
    return len(text) < 3


def _has_required_kv_markers(raw: str, required_keys: tuple[str, ...]) -> bool:
    text = str(raw or "").strip().lower()
    if not text:
        return False
    for key in required_keys:
        if not re.search(rf"(^|[;,\s]){re.escape(key.lower())}=", text):
            return False
    return True


def _reuse_check_valid(raw: str) -> bool:
    value = str(raw or "").strip()
    if _is_weak_evidence(value):
        return False
    low = value.lower()
    if low == "none":
        return False
    if low.startswith("none"):
        return bool(re.match(r"^none\(.{3,}\)$", value, flags=re.IGNORECASE))
    return True


def _parse_issue_reporting(evidence: dict[str, str], blocker_id: str, task_update: str) -> dict:
    missing: list[str] = []
    errors: list[str] = []
    for key in ("issues", "issue_count", "issue_severity"):
        if key not in evidence:
            missing.append(key)

    issues_raw = str(evidence.get("issues", "none") or "none").strip()
    issue_count_raw = str(evidence.get("issue_count", "0") or "0").strip()
    issue_severity = str(evidence.get("issue_severity", "none") or "none").strip().lower()

    issue_codes: list[str] = []
    invalid_codes: list[str] = []
    issues_is_none = issues_raw.lower() == "none"
    if not issues_is_none:
        for token in issues_raw.split(","):
            code = token.strip().lower()
            if not code:
                continue
            if ISSUE_CODE_RE.fullmatch(code):
                issue_codes.append(code)
            else:
                invalid_codes.append(code)
        if invalid_codes:
            errors.append("invalid_codes")
        if not issue_codes:
            errors.append("no_valid_issue_code")

    issue_count = 0
    if re.fullmatch(r"\d+", issue_count_raw):
        issue_count = int(issue_count_raw)
    else:
        errors.append("issue_count_invalid")

    if issue_severity not in ISSUE_SEVERITIES:
        errors.append("issue_severity_invalid")

    if issues_is_none:
        if issue_count != 0 or issue_severity != "none":
            errors.append("none_inconsistent")
    else:
        if issue_count <= 0:
            errors.append("count_non_positive")
        if issue_count != len(issue_codes):
            errors.append("count_mismatch")
        if issue_severity == "none":
            errors.append("severity_none_with_issues")

    blocker_present = str(blocker_id or "").strip().upper() not in {"", "NONE", "N/A", "NULL"}
    if str(task_update or "").strip().lower() == "blocked" or blocker_present:
        if issues_is_none or issue_count < 1 or issue_severity not in ISSUE_BLOCKED_MIN_SEVERITIES:
            errors.append("blocked_without_issue_report")

    if issues_is_none:
        issues = "none"
        issue_codes = []
        issue_count = 0
        issue_severity = "none"
    else:
        issues = ",".join(issue_codes)
        if issue_count <= 0:
            issue_count = len(issue_codes)
        if issue_severity not in ISSUE_SEVERITIES:
            issue_severity = "medium"

    return {
        "issues": issues or "none",
        "issue_count": issue_count,
        "issue_severity": issue_severity,
        "issue_codes": issue_codes,
        "issue_reporting_ok": (not missing) and (not errors),
        "issue_reporting_errors": sorted(set(missing + errors)),
    }


def parse_contract_fields(role: str) -> dict:
    c = contract(role)
    evidence = parse_evidence_kv(c.get("EVIDENCE", ""))
    run_note = evidence.get("run_note", "")
    run_note_words = len([w for w in run_note.split() if w.strip()])
    task_update = evidence.get("task_update", "").strip().lower()
    issue_report = _parse_issue_reporting(evidence, c.get("BLOCKER_ID", ""), task_update)
    issues: list[str] = []
    weak_markers: list[str] = []
    invalid_markers: list[str] = []
    values_by_field = {
        "root_cause": evidence.get("root_cause", ""),
        "fix_applied": evidence.get("fix_applied", ""),
        "verify": evidence.get("verify", ""),
        "reuse_check": evidence.get("reuse_check", ""),
        "architecture_check": evidence.get("architecture_check", ""),
        "vision_alignment": evidence.get("vision_alignment", ""),
        "qa_proof": evidence.get("qa_proof", ""),
    }
    checks = {
        "task_update": bool(task_update),
        "run_note_5w": run_note_words >= 5,
        "root_cause": not _is_weak_evidence(values_by_field["root_cause"]),
        "fix_applied": not _is_weak_evidence(values_by_field["fix_applied"]),
        "verify": not _is_weak_evidence(values_by_field["verify"]),
        "reuse_check": not _is_weak_evidence(values_by_field["reuse_check"]),
        "architecture_check": not _is_weak_evidence(values_by_field["architecture_check"]),
        "vision_alignment": not _is_weak_evidence(values_by_field["vision_alignment"]),
        "qa_proof": not _is_weak_evidence(values_by_field["qa_proof"]),
    }

    for field_name, field_value in values_by_field.items():
        if _is_weak_evidence(field_value):
            weak_markers.append(field_name)

    # Contextual requirements based on task_update.
    if task_update in {"claim", "complete", "handoff"}:
        for key in ("root_cause", "reuse_check"):
            if not checks[key]:
                issues.append(f"missing_{key}")
    if task_update in {"complete", "handoff"}:
        for key in ("fix_applied", "verify"):
            if not checks[key]:
                issues.append(f"missing_{key}")
    if role == "dev" and task_update in {"claim", "complete", "handoff"}:
        for key in ("architecture_check", "vision_alignment"):
            if not checks[key]:
                issues.append(f"missing_{key}")
        if task_update in {"complete", "handoff"} and not checks["qa_proof"]:
            issues.append("missing_qa_proof")

    if checks["reuse_check"] and not _reuse_check_valid(values_by_field["reuse_check"]):
        invalid_markers.append("reuse_check")
        issues.append("invalid_reuse_check_format")

    if checks["architecture_check"] and not _has_required_kv_markers(
        values_by_field["architecture_check"], ("layer", "imports_ok", "path_target")
    ):
        invalid_markers.append("architecture_check")
        issues.append("invalid_architecture_check_format")

    if checks["vision_alignment"] and not _has_required_kv_markers(
        values_by_field["vision_alignment"], ("batch", "target", "impact")
    ):
        invalid_markers.append("vision_alignment")
        issues.append("invalid_vision_alignment_format")

    if task_update in {"complete", "handoff"}:
        if checks["verify"] and not _has_required_kv_markers(
            values_by_field["verify"], ("before", "after", "test")
        ):
            invalid_markers.append("verify")
            issues.append("invalid_verify_format")
        if checks["qa_proof"] and not _has_required_kv_markers(
            values_by_field["qa_proof"], ("test", "result")
        ):
            invalid_markers.append("qa_proof")
            issues.append("invalid_qa_proof_format")

    if not checks["run_note_5w"]:
        issues.append("run_note_too_short")

    score = 100
    for issue in issues:
        if issue.startswith("missing_"):
            score -= 14
        elif issue.startswith("invalid_"):
            score -= 11
        elif issue == "run_note_too_short":
            score -= 8
        else:
            score -= 10
    score = max(0, min(100, score))
    if score >= 80:
        quality = "STRONG"
    elif score >= 55:
        quality = "MEDIUM"
    else:
        quality = "WEAK"
    return {
        "role": role,
        "contract": c,
        "evidence": evidence,
        "task_update": task_update or "unknown",
        "reported_issues": issue_report.get("issues", "none"),
        "issue_count": int(issue_report.get("issue_count", 0)),
        "issue_severity": issue_report.get("issue_severity", "none"),
        "issue_codes": issue_report.get("issue_codes", []),
        "issue_reporting_ok": bool(issue_report.get("issue_reporting_ok", False)),
        "issue_reporting_errors": issue_report.get("issue_reporting_errors", []),
        "run_note_words": run_note_words,
        "quality_score": score,
        "quality": quality,
        "issues": issues,
        "weak_fields": weak_markers,
        "invalid_fields": invalid_markers,
        "checks": checks,
    }

def tick_age(role):
    log = ROOT / f"logs-codex-runs/fc-ticks/{role}.tick.log"
    if not log.exists():
        return None
    lines = _tail_lines(log, 480)
    for l in reversed(lines):
        if not any(x in l for x in ("[END]", "[SKIP]", "[BACKOFF]")):
            continue
        ep = _extract_ts_epoch(l)
        if ep is None:
            continue
        age = int((time.time() - ep) / 60)
        if age < 0:
            age = 0
        # Heuristic: if parsed timestamp looks stale but log file just changed,
        # prefer mtime to avoid timezone skew from naive tick timestamps.
        if age > 180:
            try:
                mtime_age = int((time.time() - log.stat().st_mtime) / 60)
                if 0 <= mtime_age <= 30:
                    return mtime_age
            except Exception:
                pass
        return age
    return None

def tick_hist(role, n=25):
    log = ROOT / f"logs-codex-runs/fc-ticks/{role}.tick.log"
    if not log.exists(): return []
    n = max(1, int(n))
    scan = max(160, n * 8)
    lines = _tail_lines(log, scan)
    out = []
    for l in reversed(lines):
        if len(out)>=n: break
        if not any(x in l for x in ("[END]","[SKIP]","[BACKOFF]")): continue
        ts=re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})",l)
        rc=re.search(r"rc=(\d+)",l); ag=re.search(r"agent=(\w+)",l)
        out.append({"ts":ts.group(1) if ts else "?","rc":int(rc.group(1)) if rc else None,
                    "agent":ag.group(1) if ag else "?",
                    "type":"SKIP" if "[SKIP]" in l else "BACKOFF" if "[BACKOFF]" in l else "END"})
    return out


def _role_state_counter(role: str, suffix: str) -> int:
    try:
        path = STATE / f"{role}.{suffix}"
        if not path.exists():
            return 0
        raw = path.read_text(encoding="utf-8", errors="ignore").strip()
        return int(raw) if raw.isdigit() else 0
    except Exception:
        return 0

def _tail_lines(path: Path, n: int) -> list[str]:
    if n <= 0:
        return []
    if not path.exists():
        return []
    try:
        proc = subprocess.run(
            ["tail", "-n", str(int(n)), str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=2.0,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.splitlines()
    except Exception:
        pass
    try:
        return path.read_text(encoding="utf-8", errors="ignore").splitlines()[-n:]
    except Exception:
        return []

def _tail_jsonl(path: Path, n: int) -> list[dict]:
    if n <= 0:
        return []
    if not path.exists():
        return []
    out: list[dict] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()[-n:]
        for line in lines:
            raw = line.strip()
            if not raw:
                continue
            try:
                item = json.loads(raw)
            except Exception:
                continue
            if isinstance(item, dict):
                out.append(item)
    except Exception:
        return []
    return out


def _int_or_default(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _parse_ts_epoch(raw: str) -> float | None:
    token = str(raw or "").strip()
    if not token:
        return None
    try:
        if token.endswith("Z"):
            token = token[:-1] + "+00:00"
        dt = datetime.fromisoformat(token)
        if dt.tzinfo is None:
            local_tz = datetime.now().astimezone().tzinfo or timezone.utc
            dt = dt.replace(tzinfo=local_tz)
        return float(dt.timestamp())
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            local_tz = datetime.now().astimezone().tzinfo or timezone.utc
            dt = datetime.strptime(token, fmt).replace(tzinfo=local_tz)
            return float(dt.timestamp())
        except Exception:
            continue
    return None


def _severity_token(value: str) -> str:
    token = str(value or "").strip().upper()
    return token if token in {"INFO", "WARN", "ERROR", "CRITICAL"} else "INFO"


def _role_interval_minutes(role: str) -> float:
    mins = DEFAULT_SCHEDULE_MAP.get(str(role or "").strip(), [])
    if not mins:
        return 15.0
    ordered = sorted({int(x) for x in mins if isinstance(x, int)})
    if len(ordered) <= 1:
        return 60.0
    deltas: list[int] = []
    for idx, minute in enumerate(ordered):
        nxt = ordered[(idx + 1) % len(ordered)]
        delta = (nxt - minute) % 60
        if delta <= 0:
            delta = 60
        deltas.append(delta)
    return float(min(deltas)) if deltas else 15.0


def _load_iteration_issue_rows(
    *,
    role: str = "",
    severity: str = "",
    recent_minutes: int = 180,
    n: int = 120,
) -> list[dict]:
    lines: list[str] = []
    scan = max(int(n) * 24, 3000)
    for candidate in _iteration_issue_event_sources():
        if not candidate.exists():
            continue
        candidate_lines = _tail_lines(candidate, scan)
        if candidate_lines:
            lines = candidate_lines
            break
    if not lines:
        return []
    role_filter = (role or "").strip().lower()
    severity_raw = str(severity or "").strip().upper()
    severity_filter = "" if severity_raw in {"", "ALL"} else _severity_token(severity_raw)
    out: list[dict] = []
    now_epoch = time.time()

    for raw in reversed(lines):
        line = raw.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except Exception:
            continue
        if not isinstance(item, dict):
            continue
        row_role = str(item.get("role", "")).strip().lower()
        if role_filter and row_role != role_filter:
            continue

        ts_raw = str(item.get("ts_utc", "") or "")
        ts_epoch = _parse_ts_epoch(ts_raw)
        if recent_minutes > 0 and ts_epoch is not None and (now_epoch - ts_epoch) > (recent_minutes * 60):
            continue

        issue_status = str(item.get("issue_status", "") or "").strip().lower()
        issue_count = _int_or_default(item.get("issue_count"), 0)
        if issue_status not in {"none", "has_issues"}:
            issue_status = ""
        if not issue_status:
            issue_status = "has_issues" if issue_count > 0 else "none"
        sev_raw = str(item.get("max_severity", "") or "").strip()
        if not sev_raw:
            sev_norm = str(item.get("issue_severity", "") or "").strip().lower()
            if sev_norm in {"critical"}:
                sev_raw = "CRITICAL"
            elif sev_norm in {"high"}:
                sev_raw = "ERROR"
            elif sev_norm in {"medium", "low"}:
                sev_raw = "WARN"
            else:
                sev_raw = "INFO"
        max_sev = _severity_token(sev_raw)
        issue_severity = str(item.get("issue_severity", "") or "").strip().lower()
        if issue_severity not in {"none", "low", "medium", "high", "critical"}:
            issue_severity = {
                "CRITICAL": "critical",
                "ERROR": "high",
                "WARN": "medium",
                "INFO": "none",
            }.get(max_sev, "none")
        if severity_filter and severity_filter != "INFO" and max_sev != severity_filter:
            continue
        if severity_filter == "INFO" and issue_status != "none":
            continue

        issues_raw = item.get("issues", [])
        issues = issues_raw if isinstance(issues_raw, list) else []
        issue_codes: list[str] = []
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            code = str(issue.get("code", "")).strip()
            if code:
                issue_codes.append(code)

        out.append(
            {
                "ts_utc": ts_raw,
                "tick_id": str(item.get("tick_id", "") or ""),
                "role": str(item.get("role", "") or ""),
                "agent_bin": str(item.get("agent_bin", "") or ""),
                "channel": str(item.get("channel", "") or ""),
                "source": str(item.get("source", "") or ""),
                "status": str(item.get("status", "") or ""),
                "verdict": str(item.get("verdict", "") or ""),
                "rc_primary": _int_or_default(item.get("rc_primary"), 0),
                "rc_retry": _int_or_default(item.get("rc_retry"), 0),
                "rc_final": _int_or_default(item.get("rc_final"), 0),
                "issue_status": issue_status,
                "issue_count": issue_count,
                "max_severity": max_sev,
                "issue_severity": issue_severity,
                "issue_codes": issue_codes,
                "issues": issues,
                "next_action": str(item.get("next_action", "") or ""),
                "queue_version": str(item.get("queue_version", "") or ""),
                "workboard_version": str(item.get("workboard_version", "") or ""),
                "issue_reporting_ok": bool(item.get("issue_reporting_ok", True)),
                "issue_reporting_errors": item.get("issue_reporting_errors", []),
                "evidence_paths": item.get("evidence_paths", []),
            }
        )
        if len(out) >= n:
            break
    return out


def _latest_issue_by_role(rows: list[dict]) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for row in rows:
        role = str(row.get("role", "")).strip()
        if not role:
            continue
        old = latest.get(role)
        if old is None:
            latest[role] = row
            continue
        old_ts = _parse_ts_epoch(str(old.get("ts_utc", "")))
        new_ts = _parse_ts_epoch(str(row.get("ts_utc", "")))
        if new_ts is None:
            continue
        if old_ts is None or new_ts > old_ts:
            latest[role] = row
    return latest


def _issue_summary_window(window_min: int = 60) -> dict:
    rows = _load_iteration_issue_rows(recent_minutes=window_min, n=6000)
    totals = {"INFO": 0, "WARN": 0, "ERROR": 0, "CRITICAL": 0}
    top_codes: Counter[str] = Counter()
    roles_touched: set[str] = set()
    issue_counts_by_role: Counter[str] = Counter()
    role_latest = _latest_issue_by_role(rows)
    mttr_samples: defaultdict[str, list[float]] = defaultdict(list)
    open_since: dict[str, float] = {}

    rows_sorted = sorted(rows, key=lambda r: _parse_ts_epoch(str(r.get("ts_utc", ""))) or 0.0)
    for row in rows_sorted:
        role = str(row.get("role", "")).strip()
        if not role:
            continue
        ts_epoch = _parse_ts_epoch(str(row.get("ts_utc", "")))
        if ts_epoch is None:
            continue
        issue_state = str(row.get("issue_status", "none")).lower()
        if issue_state == "has_issues":
            sev = _severity_token(row.get("max_severity", "INFO"))
            totals[sev] += 1
            roles_touched.add(role)
            issue_counts_by_role[role] += int(row.get("issue_count") or 0)
            for code in row.get("issue_codes", []):
                top_codes[str(code)] += 1
            open_since.setdefault(role, ts_epoch)
        else:
            started = open_since.pop(role, None)
            if started is not None and ts_epoch >= started:
                mttr_samples[role].append((ts_epoch - started) / 60.0)

    mttr: dict[str, float | None] = {}
    for role in sorted(set(list(mttr_samples.keys()) + list(role_latest.keys()))):
        samples = mttr_samples.get(role, [])
        if not samples:
            mttr[role] = None
            continue
        mttr[role] = round(sum(samples) / float(len(samples)), 2)

    now_epoch = time.time()
    issue_publication_gap_roles: list[str] = []
    roles_scope = active_roles()
    for role in roles_scope:
        latest = role_latest.get(role)
        if isinstance(latest, dict):
            report_ok = bool(latest.get("issue_reporting_ok", True))
            if not report_ok:
                issue_publication_gap_roles.append(role)
                continue
            ts_epoch = _parse_ts_epoch(str(latest.get("ts_utc", "")))
        else:
            ts_epoch = None
        allowed = _role_interval_minutes(role) * 1.5
        if ts_epoch is None:
            issue_publication_gap_roles.append(role)
            continue
        age_min = (now_epoch - ts_epoch) / 60.0
        if age_min > allowed:
            issue_publication_gap_roles.append(role)

    return {
        "window_min": window_min,
        "total_records": len(rows),
        "totals_by_severity": totals,
        "top_codes": [{"code": code, "count": count} for code, count in top_codes.most_common(8)],
        "roles_touched": sorted(roles_touched),
        "mttr_estimated_by_role": mttr,
        "issues_recent_by_role": {role: int(issue_counts_by_role.get(role, 0)) for role in roles_scope},
        "critical_open_count": int(totals.get("CRITICAL", 0)),
        "issue_publication_gap_roles": sorted(issue_publication_gap_roles),
        "role_latest": role_latest,
    }


def planner_autonomy_snapshot(now_ts: float | None = None) -> dict:
    now_epoch = float(now_ts if now_ts is not None else time.time())
    cutoff = now_epoch - 86400.0
    latest_path = orchestrator_file("planner-guardian-latest.json")
    events_path = orchestrator_file("planner-guardian-events.jsonl")

    latest = _load_json_file(latest_path) if latest_path.exists() else {}
    if not isinstance(latest, dict):
        latest = {}

    state = _load_planner_autonomy_state()
    if not isinstance(state, dict):
        state = {}

    ready_idle_streak = _int_or_default(latest.get("ready_idle_streak"), 0)
    low_score_streak = _int_or_default(latest.get("low_score_streak"), 0)
    runway_no_batch_streak = _int_or_default(latest.get("runway_no_batch_streak"), 0)

    autofix_count_24h = 0
    last_autofix_reason = ""
    if events_path.exists():
        lines = _tail_lines(events_path, 2400)
        for raw in reversed(lines):
            line = raw.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except Exception:
                continue
            if not isinstance(item, dict):
                continue
            ts = _parse_ts_epoch(
                str(item.get("ts_utc") or item.get("ts") or item.get("timestamp") or "")
            )
            if ts is not None and ts < cutoff:
                continue
            reason = str(
                item.get("reason")
                or item.get("autofix_reason")
                or item.get("detail")
                or item.get("message")
                or ""
            ).strip()
            ev_name = str(item.get("event") or item.get("kind") or "").strip().lower()
            action = str(item.get("action") or "").strip().lower()
            is_autofix = bool(item.get("autofix_applied"))
            if not is_autofix and ("autofix" in ev_name or "auto_fix" in ev_name or "auto-fix" in ev_name):
                is_autofix = True
            if not is_autofix and ("autofix" in action or "auto_fix" in action or "auto-fix" in action):
                is_autofix = True
            if not is_autofix and "autofix" in reason.lower():
                is_autofix = True
            if not is_autofix:
                continue
            autofix_count_24h += 1
            if not last_autofix_reason:
                last_autofix_reason = reason or ev_name or action

    if not last_autofix_reason:
        last_autofix_reason = str(latest.get("last_autofix_reason") or "").strip()

    since_ts = str(state.get("since_ts") or "").strip()
    age_min = -1
    if since_ts:
        ts_epoch = _parse_ts_epoch(since_ts)
        if ts_epoch is not None:
            age_min = max(0, int((now_epoch - ts_epoch) // 60))

    return {
        "active": bool(state.get("active", False)),
        "since_ts": since_ts,
        "age_min": age_min,
        "last_action": str(state.get("last_action", "idle") or "idle").strip() or "idle",
        "last_outcome": str(state.get("last_outcome", "none") or "none").strip() or "none",
        "reason": str(state.get("reason", "none") or "none").strip() or "none",
        "target_task": str(state.get("target_task", "none") or "none").strip() or "none",
        "issue_code": str(state.get("issue_code", "none") or "none").strip() or "none",
        "policy_enforced": bool(state.get("policy_enforced", True)),
        "wait_forbidden": bool(state.get("wait_forbidden", True)),
        "ready_idle_streak": ready_idle_streak,
        "low_score_streak": low_score_streak,
        "runway_no_batch_streak": runway_no_batch_streak,
        "autofix_count_24h": autofix_count_24h,
        "last_autofix_reason": last_autofix_reason,
        "source": str(state.get("source") or PLANNER_AUTONOMY_STATE_FILE),
    }


def admin_tshape_snapshot(now_ts: float | None = None) -> dict:
    now_epoch = float(now_ts if now_ts is not None else time.time())
    state_file = ADMIN_TSHAPE_STATE_FILE
    payload = {
        "active": False,
        "target_role": "",
        "since_ts": "",
        "reason_blocker": "NONE",
        "last_action": "idle",
        "resolved": True,
        "blocked_streak": 0,
        "blocked_roles": [],
        "age_min": -1,
        "source": str(state_file),
    }
    base = _load_admin_tshape_state()
    if not isinstance(base, dict):
        return payload

    since_ts = str(base.get("since_ts") or "").strip()
    age_min = -1
    if since_ts:
        ts_epoch = _parse_ts_epoch(since_ts)
        if ts_epoch is not None:
            age_min = max(0, int((now_epoch - ts_epoch) // 60))

    payload.update(
        {
            "active": bool(base.get("active", False)),
            "target_role": str(base.get("target_role") or "").strip(),
            "since_ts": since_ts,
            "reason_blocker": str(base.get("reason_blocker") or "NONE").strip() or "NONE",
            "last_action": str(base.get("last_action") or "idle").strip() or "idle",
            "resolved": bool(base.get("resolved", False)),
            "blocked_streak": _int_or_default(base.get("blocked_streak"), 0),
            "blocked_roles": base.get("blocked_roles", []) if isinstance(base.get("blocked_roles"), list) else [],
            "age_min": age_min,
            "source": str(base.get("source") or state_file),
        }
    )
    return payload


def admin_autonomy_snapshot(now_ts: float | None = None) -> dict:
    now_epoch = float(now_ts if now_ts is not None else time.time())
    state = _load_admin_autonomy_state()
    if not isinstance(state, dict):
        state = {}
    since_ts = str(state.get("since_ts") or "").strip()
    age_min = -1
    if since_ts:
        ts_epoch = _parse_ts_epoch(since_ts)
        if ts_epoch is not None:
            age_min = max(0, int((now_epoch - ts_epoch) // 60))
    streak = state.get("streak_by_role", {})
    if not isinstance(streak, dict):
        streak = {}
    needs_review = state.get("needs_human_review_by_role", {})
    if not isinstance(needs_review, dict):
        needs_review = {}
    return {
        "active": bool(state.get("active", False)),
        "trigger": str(state.get("trigger", "none") or "none").strip() or "none",
        "target_role": str(state.get("target_role", "") or "").strip(),
        "target_task": str(state.get("target_task", "none") or "none").strip() or "none",
        "reason_blocker": str(state.get("reason_blocker", "NONE") or "NONE").strip() or "NONE",
        "last_action": str(state.get("last_action", "idle") or "idle").strip() or "idle",
        "last_outcome": str(state.get("last_outcome", "none") or "none").strip() or "none",
        "last_action_seq": str(state.get("last_action_seq", "") or "").strip(),
        "since_ts": since_ts,
        "age_min": age_min,
        "streak_by_role": {
            "planner": _int_or_default(streak.get("planner"), 0),
            "dev": _int_or_default(streak.get("dev"), 0),
        },
        "needs_human_review_by_role": {
            "planner": bool(needs_review.get("planner", False)),
            "dev": bool(needs_review.get("dev", False)),
        },
        "source": str(state.get("source", ADMIN_AUTONOMY_STATE_FILE)),
    }


def admin_dispatch_snapshot(now_ts: float | None = None) -> dict:
    now_epoch = float(now_ts if now_ts is not None else time.time())
    payload = {
        "status": "unknown",
        "last_action": "none",
        "last_reason": "none",
        "dispatch_reason_code": "none",
        "autonomy_reason_code": "none",
        "stream_fairness_slot": 0,
        "cooldown_left_s": 0,
        "last_result_ts": "",
        "last_result_age_s": -1,
        "source": str(ADMIN_DISPATCH_LOG_FILE),
    }
    lines = _tail_lines(ADMIN_DISPATCH_LOG_FILE, 1200)
    if not lines:
        return payload
    last_result = ""
    for raw in reversed(lines):
        if "dispatch_result" in raw:
            last_result = raw.strip()
            break
    if not last_result:
        return payload
    ts_match = re.search(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)", last_result)
    if ts_match:
        last_ts = ts_match.group(1)
        payload["last_result_ts"] = last_ts
        ts_epoch = _parse_ts_epoch(last_ts)
        if ts_epoch is not None:
            payload["last_result_age_s"] = max(0, int(now_epoch - ts_epoch))
    result_kv = dict(re.findall(r"([a-zA-Z0-9_]+)=([^\s]+)", last_result))
    status = str(result_kv.get("status", "unknown")).strip().lower()
    reason = str(result_kv.get("reason", "none")).strip()
    dispatch_reason_code = str(result_kv.get("dispatch_reason_code", "none")).strip() or "none"
    autonomy_reason_code = str(result_kv.get("autonomy_reason_code", "none")).strip() or "none"
    slot = _int_or_default(result_kv.get("stream_fairness_slot"), 0)
    cooldown_left_s = 0
    m_cooldown = re.search(r"cooldown_active_(\d+)s", reason)
    if m_cooldown:
        cooldown_left_s = _int_or_default(m_cooldown.group(1), 0)
    payload.update(
        {
            "status": status,
            "last_action": "dispatch" if status == "ok" else "noop",
            "last_reason": reason or "none",
            "dispatch_reason_code": dispatch_reason_code,
            "autonomy_reason_code": autonomy_reason_code,
            "stream_fairness_slot": slot,
            "cooldown_left_s": cooldown_left_s,
        }
    )
    return payload


def _state_counts(items: list[dict], key: str = "state") -> dict[str, int]:
    counts: defaultdict[str, int] = defaultdict(int)
    for item in items:
        val = str(item.get(key, "?") or "?").upper()
        counts[val] += 1
    return dict(counts)

def _queue_workboard_mismatches(queue_items: list[dict], tasks: list[dict]) -> list[dict]:
    out: list[dict] = []
    for item in queue_items:
        batch_id = str(item.get("id", "")).strip()
        if not batch_id or not re.fullmatch(r"BATCH-\d{2}", batch_id):
            continue
        q_state = str(item.get("state", "")).upper()
        related = [t for t in tasks if str(t.get("id", "")).startswith(f"{batch_id}-")]
        if not related:
            # Planned/queued-only batches can legitimately have no instantiated tasks yet.
            if q_state in {"WAITING_DEP", "PLANNED", "READY_FOR_PARALLEL_DISPATCH"}:
                continue
            out.append({"batch": batch_id, "issue": "no_tasks_for_batch", "queue_state": q_state})
            continue
        ready = sum(1 for t in related if str(t.get("state", "")).upper() == "READY")
        in_prog = sum(1 for t in related if str(t.get("state", "")).upper() == "IN_PROGRESS")
        done = sum(1 for t in related if str(t.get("state", "")).upper() in {"DONE", "CLOSED", "PASS"})
        if q_state == "READY" and (ready + in_prog) == 0:
            out.append({"batch": batch_id, "issue": "queue_ready_but_no_ready_task", "queue_state": q_state, "tasks_done": done})
        # Transitional state is acceptable when stream remains active but the next
        # task is READY and has not been claimed yet.
        if q_state == "IN_PROGRESS" and in_prog == 0 and ready == 0:
            out.append({"batch": batch_id, "issue": "queue_in_progress_but_no_task_in_progress", "queue_state": q_state, "tasks_ready": ready})
    return out


def _batch_prefix(task_id: str) -> str:
    raw = (task_id or "").strip()
    m = re.match(r"^(BATCH-\d{2})\b", raw)
    if m:
        return m.group(1)
    parts = raw.split("-")
    if len(parts) >= 2 and parts[0] == "BATCH":
        return "-".join(parts[:2])
    return ""


def _derive_batches_from_workboard(tasks: list[dict]) -> list[dict]:
    by_batch: dict[str, dict] = {}
    for t in tasks:
        bid = _batch_prefix(str(t.get("id", "")))
        if not bid:
            continue
        state = str(t.get("state", "")).upper() or "UNKNOWN"
        node = by_batch.setdefault(bid, {"id": bid, "task_states": defaultdict(int), "tasks_total": 0})
        node["task_states"][state] += 1
        node["tasks_total"] += 1

    out: list[dict] = []
    for bid, node in by_batch.items():
        states: dict[str, int] = dict(node["task_states"])
        in_prog = states.get("IN_PROGRESS", 0)
        ready = states.get("READY", 0)
        open_non_ready = sum(v for k, v in states.items() if k not in {"DONE", "CLOSED", "PASS", "READY", "IN_PROGRESS"})
        closed = states.get("DONE", 0) + states.get("CLOSED", 0) + states.get("PASS", 0)
        total = int(node["tasks_total"])

        if in_prog > 0:
            batch_state = "IN_PROGRESS"
        elif ready > 0:
            batch_state = "READY"
        elif closed >= total and total > 0:
            batch_state = "CLOSED"
        elif open_non_ready > 0:
            batch_state = "WAITING_DEP"
        else:
            batch_state = "WAITING_DEP"

        out.append({
            "id": bid,
            "state": batch_state,
            "tasks_total": total,
            "ready": ready,
            "in_progress": in_prog,
            "closed": closed,
            "state_counts": states,
        })

    def _batch_num(item: dict) -> int:
        m = re.search(r"BATCH-(\d+)", str(item.get("id", "")))
        return int(m.group(1)) if m else 10**9

    out.sort(key=lambda x: (_batch_num(x), str(x.get("id", ""))))
    return out

def _find_last_tick_markers(lines: list[str]) -> tuple[str, str]:
    last_start = ""
    last_end = ""
    for line in reversed(lines):
        if not last_end and any(marker in line for marker in ("[END]", "[SKIP]", "[BACKOFF]")):
            last_end = line
        if not last_start and "[START]" in line:
            last_start = line
        if last_start and last_end:
            break
    return last_start, last_end

def latest_execution(role: str, tick_n: int = 35, runner_n: int = 55) -> dict:
    tick_log = ROOT / f"logs-codex-runs/fc-ticks/{role}.tick.log"
    runner_log = ROOT / f"logs-codex-runs/role-runner/{role}.live.log"
    events_log = ROOT / f"logs-codex-runs/role-runner/{role}.events.log"
    tick_lines = _tail_lines(tick_log, tick_n)
    runner_lines = _tail_lines(runner_log, runner_n)
    events_lines = _tail_lines(events_log, runner_n)
    last_start, last_end = _find_last_tick_markers(tick_lines)

    rc_match = re.search(r"rc=(\d+)", last_end or "")
    agent_match = re.search(r"agent=(\w+)", last_end or "")
    ts_match = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", last_end or "")
    if not ts_match:
        ts_match = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", last_start or "")

    merged = tick_lines + runner_lines + events_lines
    sev = defaultdict(int)
    for line in merged:
        sev[classify_log_line(line)] += 1

    return {
        "role": role,
        "tick_tail": tick_lines,
        "runner_tail": runner_lines,
        "events_tail": events_lines,
        "last_start": last_start,
        "last_end": last_end,
        "last_ts": ts_match.group(1) if ts_match else "",
        "last_rc": int(rc_match.group(1)) if rc_match else None,
        "last_agent": agent_match.group(1) if agent_match else "",
        "severity_counts": dict(sev),
    }

def _parse_runner_events(role: str, n: int = 160) -> list[dict]:
    log = ROOT / f"logs-codex-runs/role-runner/{role}.events.log"
    lines = _tail_lines(log, n)
    out: list[dict] = []
    for line in lines:
        m = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s+role=([a-zA-Z0-9_]+)\s+event=([a-zA-Z0-9_]+)\s+detail=(.*)$", line.strip())
        if not m:
            continue
        out.append({
            "ts": m.group(1),
            "role": m.group(2),
            "event": m.group(3),
            "detail": m.group(4),
        })
    return out

def execution_insight(role: str) -> dict:
    ex = latest_execution(role, tick_n=40, runner_n=80)
    cf = parse_contract_fields(role)
    events = _parse_runner_events(role, n=180)

    action_events = {
        "primary_structured_ok",
        "retry_structured_ok",
        "codex_fallback_structured_ok",
        "final_output",
    }
    error_hint = re.compile(r"(checkpoint_fallback|prompt_stall_abort|session_not_ready|contract_guard_external_failed|syntax_error|module not found|traceback|error)", re.I)
    warn_hint = re.compile(r"(rate_limit|backoff|retry_prompt_begin|go_with_caution|monitoring_publish_skipped)", re.I)

    e_counts: defaultdict[str, int] = defaultdict(int)
    interesting: list[dict] = []
    for ev in events:
        ev_name = str(ev.get("event", ""))
        detail = str(ev.get("detail", ""))
        if ev_name in action_events:
            e_counts["action"] += 1
            interesting.append(ev)
            continue
        if error_hint.search(ev_name) or error_hint.search(detail):
            e_counts["error"] += 1
            interesting.append(ev)
            continue
        if warn_hint.search(ev_name) or warn_hint.search(detail):
            e_counts["warn"] += 1
            continue
        e_counts["meta"] += 1

    task_update = cf.get("task_update", "unknown")
    quality = cf.get("quality", "WEAK")
    quality_score = int(cf.get("quality_score", 0))
    issues = cf.get("issues", [])

    if task_update in {"claim", "complete", "handoff"} and quality in {"STRONG", "MEDIUM"}:
        activity = "PRODUCTIVE"
    elif task_update in {"none_no_ready", "none_no_signal", "analysis_only"}:
        activity = "IDLE"
    else:
        activity = "CHECK"

    return {
        "role": role,
        "activity": activity,
        "task_update": task_update,
        "quality": quality,
        "quality_score": quality_score,
        "issues": issues[:8],
        "run_note_words": cf.get("run_note_words", 0),
        "last_rc": ex.get("last_rc"),
        "last_ts": ex.get("last_ts"),
        "last_agent": ex.get("last_agent"),
        "severity_counts": ex.get("severity_counts", {}),
        "event_counts": dict(e_counts),
        "interesting_events": interesting[-8:],
        "runner_events_tail": events[-24:],
        "contract_status": {
            "status": cf.get("contract", {}).get("STATUS", ""),
            "delta": cf.get("contract", {}).get("DELTA", ""),
            "verdict": cf.get("contract", {}).get("VERDICT", ""),
            "blocker_id": cf.get("contract", {}).get("BLOCKER_ID", ""),
            "next": cf.get("contract", {}).get("NEXT", ""),
        },
    }

def classify_log_line(line: str) -> str:
    txt = (line or "").strip()
    u = txt.upper()
    if not txt:
        return "empty"
    if any(k in u for k in (
        "ASK QUESTIONS, EDIT FILES, OR RUN COMMANDS.",
        "BE SPECIFIC FOR THE BEST RESULTS.",
        "/HELP FOR MORE INFORMATION.",
        "INSTALLED VIA HOMEBREW. PLEASE UPDATE WITH",
        "USING: 1 QWEN.MD FILE",
    )):
        return "meta"
    if re.search(r"^\(ESC TO CANCEL", u):
        return "meta"
    if any(k in u for k in ("CODER-MODEL", "SANDBOX (", "NO SANDBOX")):
        return "meta"
    if re.search(r"[\u2800-\u28ff]", txt):
        return "meta"
    if re.search(r"\brc=(1|2|124|13|22|43)\b", txt):
        return "error"
    if any(k in u for k in ("[ERROR]", "ERROR:", "TRACEBACK", "EXCEPTION", "MODULE NOT FOUND", "UNEXPECTED EOF", "SYNTAX ERROR")):
        return "error"
    if any(k in u for k in ("[BLOCKED]", "VERDICT: BLOCKED", "STATUS: BLOCKED")):
        return "error"
    if "BLOCKER_ID:" in u:
        m_blocker = re.search(r"BLOCKER_ID:\s*([A-Z0-9_\-?]+)", u)
        blocker = (m_blocker.group(1) if m_blocker else "").strip()
        if blocker and blocker not in {"NONE", "NO_BLOCKER", "?"}:
            return "error"
    if any(k in u for k in ("[BACKOFF]", "RATE_LIMIT", "[SKIP]", "GO_WITH_CAUTION", "WARN", "WARNING")):
        return "warn"
    if "[ACTION]" in u:
        return "action"
    if "[CONTRACT]" in u:
        return "contract"
    if any(k in u for k in ("VERDICT: PASS", "VERDICT: GO", "STATUS: COMPLETE", "STATUS: OK", "TEST_RESULT=PASS")):
        return "ok"
    if any(k in u for k in ("[START]", "[END]", "[TICK]", "[MODEL]", "[CONFIG]", "[MODEL_EFFECTIVE]", "PRIMARY_PROMPT_BEGIN", "PRIMARY_PROMPT_END", "FINAL_OUTPUT")):
        return "meta"
    return "normal"

def _extract_ts(line: str) -> str:
    m = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", line or "")
    return m.group(1) if m else ""


def _extract_ts_epoch(line: str) -> float | None:
    txt = (line or "").strip()
    if not txt:
        return None
    # 2026-03-03T23:40:09Z
    m_z = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})Z", txt)
    if m_z:
        try:
            return datetime.strptime(m_z.group(1), "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
        except Exception:
            pass
    # 2026-03-03T19:06:04-0500
    m_off = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4})", txt)
    if m_off:
        try:
            return datetime.strptime(m_off.group(1), "%Y-%m-%dT%H:%M:%S%z").timestamp()
        except Exception:
            pass
    # 2026-03-03T19:02:37 (naive timestamp)
    m_local = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", txt)
    if m_local:
        try:
            dt = datetime.strptime(m_local.group(1), "%Y-%m-%dT%H:%M:%S")
            now_epoch = time.time()
            candidates = []
            local_tz = datetime.now().astimezone().tzinfo
            if local_tz is not None:
                candidates.append(local_tz)
            log_tz_name = os.environ.get("FC_MONITOR_LOG_TZ", "America/Toronto").strip()
            if ZoneInfo is not None and log_tz_name:
                try:
                    candidates.append(ZoneInfo(log_tz_name))
                except Exception:
                    pass
            candidates.append(timezone.utc)
            best_epoch = None
            best_delta = None
            seen = set()
            for tz in candidates:
                key = str(tz)
                if key in seen:
                    continue
                seen.add(key)
                epoch = dt.replace(tzinfo=tz).timestamp()
                delta = abs(now_epoch - epoch)
                if best_delta is None or delta < best_delta:
                    best_delta = delta
                    best_epoch = epoch
            return best_epoch
        except Exception:
            return None
    return None


def _is_recent_line(line: str, recent_minutes: int, now_epoch: float | None = None) -> bool:
    if recent_minutes <= 0:
        return True
    epoch = _extract_ts_epoch(line)
    if epoch is None:
        return True
    if now_epoch is None:
        now_epoch = time.time()
    return (now_epoch - epoch) <= (recent_minutes * 60)

def resolve_role_log_path(role: str, kind: str) -> Path | None:
    role = (role or "").strip()
    kind = (kind or "").strip().lower()
    if not re.fullmatch(r"[A-Za-z0-9_]+", role):
        return None
    if kind == "tick":
        return ROOT / f"logs-codex-runs/fc-ticks/{role}.tick.log"
    if kind == "cron":
        return ROOT / f"logs-codex-runs/fc-ticks/{role}.cron.log"
    if kind == "runner":
        return ROOT / f"logs-codex-runs/role-runner/{role}.live.log"
    if kind == "events":
        return ROOT / f"logs-codex-runs/role-runner/{role}.events.log"
    if kind == "contract":
        return STATE / f"{role}.last_contract"
    return None

def rate_limits():
    out=[]
    for b in ["codex","qwen"]:
        f=STATE/f"{b}.rate_limit_gate_cache"
        if not f.exists(): continue
        try:
            until=int(f.read_text().strip().split("|")[0]); rem=int(until-time.time())
            if rem>0: out.append({"model":b,"remaining_s":rem})
            else: f.unlink()
        except: pass
    return out

def _parse_bool_token(value) -> bool:
    token = str(value or "").strip().lower()
    return token in {"1", "true", "yes", "on"}

def _load_planner_autonomy_state() -> dict:
    defaults = {
        "active": False,
        "since_ts": "",
        "last_action": "idle",
        "last_outcome": "none",
        "reason": "none",
        "target_task": "none",
        "issue_code": "none",
        "policy_enforced": True,
        "wait_forbidden": True,
        "source": "",
    }
    candidates = [
        PLANNER_AUTONOMY_STATE_FILE,
        STATE / "planner_autonomy_state.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        return {
            "active": bool(payload.get("active", False) or _parse_bool_token(payload.get("active"))),
            "since_ts": str(payload.get("since_ts", "") or "").strip(),
            "last_action": str(payload.get("last_action", "idle") or "idle").strip() or "idle",
            "last_outcome": str(payload.get("last_outcome", "none") or "none").strip() or "none",
            "reason": str(payload.get("reason", "none") or "none").strip() or "none",
            "target_task": str(payload.get("target_task", "none") or "none").strip() or "none",
            "issue_code": str(payload.get("issue_code", "none") or "none").strip() or "none",
            "policy_enforced": bool(payload.get("policy_enforced", True) or _parse_bool_token(payload.get("policy_enforced", True))),
            "wait_forbidden": bool(payload.get("wait_forbidden", True) or _parse_bool_token(payload.get("wait_forbidden", True))),
            "source": str(path),
        }
    return defaults

def _load_admin_tshape_state() -> dict:
    defaults = {
        "active": False,
        "target_role": "",
        "since_ts": "",
        "reason_blocker": "NONE",
        "last_action": "idle",
        "resolved": True,
        "blocked_roles": [],
        "source": "",
    }
    candidates = [
        ADMIN_TSHAPE_STATE_FILE,
        STATE / "admin.tshape.state.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        blocked_roles = payload.get("blocked_roles", [])
        if not isinstance(blocked_roles, list):
            blocked_roles = []
        blocked_roles = [str(r).strip() for r in blocked_roles if str(r).strip()]
        state = {
            "active": bool(payload.get("active", False) or _parse_bool_token(payload.get("active"))),
            "target_role": str(payload.get("target_role", "") or "").strip(),
            "since_ts": str(payload.get("since_ts", "") or "").strip(),
            "reason_blocker": str(payload.get("reason_blocker", "NONE") or "NONE").strip().upper(),
            "last_action": str(payload.get("last_action", "idle") or "idle").strip(),
            "resolved": bool(payload.get("resolved", True) or _parse_bool_token(payload.get("resolved"))),
            "blocked_roles": blocked_roles,
            "source": str(path),
        }
        if not state["reason_blocker"]:
            state["reason_blocker"] = "NONE"
        return state
    return defaults


def _load_admin_autonomy_state() -> dict:
    defaults = {
        "active": False,
        "trigger": "none",
        "target_role": "",
        "target_task": "none",
        "reason_blocker": "NONE",
        "last_action": "idle",
        "last_outcome": "none",
        "last_action_seq": "",
        "since_ts": "",
        "streak_by_role": {"planner": 0, "dev": 0},
        "needs_human_review_by_role": {"planner": False, "dev": False},
        "source": "",
    }
    candidates = [
        ADMIN_AUTONOMY_STATE_FILE,
        STATE / "admin_autonomy_state.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        streak = payload.get("streak_by_role", {})
        if not isinstance(streak, dict):
            streak = {}
        needs = payload.get("needs_human_review_by_role", {})
        if not isinstance(needs, dict):
            needs = {}
        return {
            "active": bool(payload.get("active", False) or _parse_bool_token(payload.get("active"))),
            "trigger": str(payload.get("trigger", "none") or "none").strip() or "none",
            "target_role": str(payload.get("target_role", "") or "").strip(),
            "target_task": str(payload.get("target_task", "none") or "none").strip() or "none",
            "reason_blocker": str(payload.get("reason_blocker", "NONE") or "NONE").strip() or "NONE",
            "last_action": str(payload.get("last_action", "idle") or "idle").strip() or "idle",
            "last_outcome": str(payload.get("last_outcome", "none") or "none").strip() or "none",
            "last_action_seq": str(payload.get("last_action_seq", "") or "").strip(),
            "since_ts": str(payload.get("since_ts", "") or "").strip(),
            "streak_by_role": {
                "planner": _int_or_default(streak.get("planner"), 0),
                "dev": _int_or_default(streak.get("dev"), 0),
            },
            "needs_human_review_by_role": {
                "planner": bool(needs.get("planner", False) or _parse_bool_token(needs.get("planner"))),
                "dev": bool(needs.get("dev", False) or _parse_bool_token(needs.get("dev"))),
            },
            "source": str(path),
        }
    return defaults

def kpi_last():
    path = orchestrator_file("kpi-history.jsonl")
    if not path.exists(): return {}
    for l in reversed(path.read_text(encoding="utf-8").splitlines()):
        try:
            d=json.loads(l)
            if d.get("workboard") or d.get("done_total"): return d
        except: pass
    return {}

def is_rate_limit_marker(verdict: str, status: str, delta: str, blocker: str) -> bool:
    b = (blocker or "").upper()
    s = (status or "").upper()
    d = (delta or "").upper()
    return b.startswith("AGENT_RATE_LIMIT_") or s in ("RATE_LIMIT_SKIP", "RATE_LIMIT_BACKOFF") or d == "RATE_LIMIT_BACKOFF"


def _unknown_agent_payload(role: str, source: str = "unknown") -> dict:
    return {
        "verdict": "UNKNOWN",
        "status": "UNKNOWN",
        "delta": "NO_DATA",
        "blocker": "NONE",
        "next": f"owner=admin; action=restore_runtime_sources_for_{role}",
        "schedule": "manual",
        "tick_age_min": -1,
        "next_tick_min": -1,
        "next_tick_at": "--",
        "planner_action_required": "",
        "soft_blocker": False,
        "tshape_active": False,
        "tshape_target_role": "",
        "session_not_ready_fallback_count": 0,
        "pending_messages_count": 0,
        "last_message_id": "",
        "last_message_action_status": "none",
        "quality_missing_fields": [],
        "quality_autofix_active": False,
        "actions_sent_60m": 0,
        "last_action_target": "",
        "last_action_message_id": "",
        "source": source,
    }

@app.get("/api/status")
def status():
    now=datetime.now(timezone.utc); m=now.minute
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    latest_snapshot = monitor_latest_snapshot()
    latest_roles_raw = latest_snapshot.get("roles", {})
    latest_roles = latest_roles_raw if isinstance(latest_roles_raw, dict) else {}
    # Canonical UI scope: active topology roles + advisory lanes with monitor evidence.
    roles = monitor_roles()
    pq=jload(orchestrator_file("priority-queue.json"))
    qi=pq.get("items",[])
    wb=jload(orchestrator_file("parallel-workstreams.json"))
    tasks=wb.get("tasks",[])
    derived_batches = _derive_batches_from_workboard(tasks)
    # Canonical source: priority-queue.json -> items[].
    # Keep derived fallback only when queue is empty/unavailable.
    queue_items = qi if isinstance(qi, list) else []
    if not queue_items and derived_batches:
        queue_items = [{"id": b.get("id"), "state": b.get("state")} for b in derived_batches]
    qa=[i for i in queue_items if i.get("state") not in ("CLOSED","DONE","PASS")]
    bs=defaultdict(int)
    for t in tasks: bs[t.get("state","?")] += 1
    done=bs["DONE"]+bs["CLOSED"]+bs["PASS"]
    ready_t=[{"id":t["id"],"role":canonical_role(t.get("assignee") or t.get("role","?")),"title":t.get("title","")[:60]} for t in tasks if str(t.get("state","")).upper() in {"READY","READY_PLANNER","READY_DEV"}]
    ip_t=[{"id":t["id"],"role":canonical_role(t.get("assignee") or t.get("role","?")),"title":t.get("title","")[:60]} for t in tasks if t.get("state")=="IN_PROGRESS"]
    queue_state_counts = _state_counts(queue_items, key="state")
    workboard_state_counts = _state_counts(tasks, key="state")
    mismatches = _queue_workboard_mismatches(queue_items, tasks)
    hs = latest_snapshot.get("health_snapshot", {}) if isinstance(latest_snapshot, dict) else {}
    hs_queue = hs.get("queue", {}) if isinstance(hs, dict) else {}
    hs_workboard = hs.get("workboard", {}) if isinstance(hs, dict) else {}
    planner_autonomy = planner_autonomy_snapshot()
    dispatcher_tshape = admin_tshape_snapshot()
    admin_autonomy = admin_autonomy_snapshot()
    admin_dispatch = admin_dispatch_snapshot()
    agent_messages = _message_bus_snapshot(now_iso)
    po_scrum_master = _po_scrum_master_snapshot(agent_messages)
    doctor = doctor_snapshot(force_refresh=False)
    planner_contract_health = parse_contract_fields("planner")
    planner_evidence_quality_score = _int_or_default(planner_contract_health.get("quality_score"), 0)

    queue_total = len(queue_items)
    queue_closed = len(queue_items) - len(qa)
    if queue_total == 0 and isinstance(hs_queue, dict) and hs_queue:
        queue_total = int(hs_queue.get("total") or 0)
        queue_closed = int(hs_queue.get("closed") or 0)

    queue_active_rows = [{"id": i["id"], "state": str(i.get("state", "")).upper()} for i in qa]
    queue_display_rows = _merge_queue_display_rows(queue_items, derived_batches)
    queue_display_total = len(queue_display_rows)
    queue_display_closed = sum(
        1 for b in queue_display_rows
        if str(b.get("state", "")).upper() in {"CLOSED", "DONE", "PASS"}
    )

    workboard_total = len(tasks)
    workboard_done = done
    workboard_ready = len(ready_t)
    workboard_in_progress = len(ip_t)
    if workboard_total == 0 and isinstance(hs_workboard, dict) and hs_workboard:
        workboard_total = int(hs_workboard.get("total") or 0)
        workboard_done = int(hs_workboard.get("done") or 0)
        workboard_ready = int(hs_workboard.get("ready") or 0)
        workboard_in_progress = int(hs_workboard.get("in_progress") or 0)

    doctor_checks = doctor.get("checks", {}) if isinstance(doctor, dict) else {}
    queue_workboard_check = doctor_checks.get("queue_workboard", {}) if isinstance(doctor_checks, dict) else {}
    queue_workboard_detail = (
        queue_workboard_check.get("detail", {})
        if isinstance(queue_workboard_check, dict) and isinstance(queue_workboard_check.get("detail"), dict)
        else {}
    )
    queue_workboard_integrity = {
        "status": str(queue_workboard_check.get("status", "unknown")) if isinstance(queue_workboard_check, dict) else "unknown",
        "mismatch_count": _int_or_default(queue_workboard_detail.get("mismatch_count"), len(mismatches)),
        "oldest_mismatch_age_s": _int_or_default(queue_workboard_detail.get("oldest_mismatch_age_s"), -1),
        "queue_only": queue_workboard_detail.get("queue_only", []),
        "workboard_only": queue_workboard_detail.get("workboard_only", []),
        "state_mismatch": queue_workboard_detail.get("state_mismatch", []),
    }

    monitor_ready_dev_from_workboard = str(os.environ.get("FC_MONITOR_READY_DEV_FROM_WORKBOARD", "1")).strip() == "1"

    dev_ready_task_ids_runtime: list[str] = []
    dev_claimable_ready_task_ids_runtime: list[str] = []
    for t in tasks:
        if not isinstance(t, dict):
            continue
        role_token = canonical_role(t.get("assignee") or t.get("role", ""))
        if role_token != "dev":
            continue
        state_up = str(t.get("state", "")).upper()
        if state_up not in {"READY", "READY_DEV", "IN_PROGRESS", "REVIEW"}:
            continue
        task_id = str(t.get("id", "")).strip()
        stream_id = str(t.get("stream_id") or _batch_prefix(task_id)).strip()
        if not task_id or not stream_id:
            continue
        if state_up in {"READY", "READY_DEV"}:
            dev_ready_task_ids_runtime.append(task_id)
            dev_claimable_ready_task_ids_runtime.append(task_id)

    dev_ready_count_runtime = len(dev_ready_task_ids_runtime)
    dev_claimable_ready_count_runtime = len(dev_claimable_ready_task_ids_runtime)
    dev_ready_runtime = dev_ready_count_runtime > 0
    dev_in_progress_runtime = any(
        str(t.get("state", "")).upper() == "IN_PROGRESS"
        and canonical_role(t.get("assignee") or t.get("role", "")) == "dev"
        for t in tasks
        if isinstance(t, dict)
    )
    dev_wait_allowed_runtime = not dev_ready_runtime and not dev_in_progress_runtime
    dev_wait_reason_runtime = "no_dev_ready_task" if dev_wait_allowed_runtime else "none"
    orchestrator_source = "canonical"
    for source_role in ("planner", "dev", "admin"):
        c_src = contract(source_role)
        ev_src = parse_evidence_kv(c_src.get("EVIDENCE", "")) if isinstance(c_src, dict) else {}
        src_val = str(ev_src.get("orchestrator_source", "")).strip().lower()
        if src_val in {"canonical", "legacy_fallback"}:
            orchestrator_source = src_val
            break
    dev_force_claim_events_60m = 0
    dev_events_log = resolve_role_log_path("dev", "events")
    now_epoch_status = time.time()
    if dev_events_log and dev_events_log.exists():
        for ln in _tail_lines(dev_events_log, 420):
            if "DEV_READY_FORCE_CLAIM" not in ln:
                continue
            if _is_recent_line(ln, 60, now_epoch_status):
                dev_force_claim_events_60m += 1

    planner_contract = contract("planner")
    planner_evidence = (
        parse_evidence_kv(planner_contract.get("EVIDENCE", ""))
        if isinstance(planner_contract, dict)
        else {}
    )
    if not isinstance(planner_evidence, dict):
        planner_evidence = {}
    planner_quality_missing_raw = str(planner_evidence.get("planner_quality_missing", "")).strip()
    planner_quality_missing_fields = [
        token.strip()
        for token in planner_quality_missing_raw.split(",")
        if token.strip() and token.strip().lower() not in {"none", "n/a", "na"}
    ]
    planner_quality_missing_count = len(planner_quality_missing_fields)
    planner_quality_score = _int_or_default(planner_evidence.get("planner_quality_score"), 100)
    if planner_quality_missing_count > 0 and planner_quality_score == 100:
        planner_quality_score = max(0, 100 - planner_quality_missing_count * 25)
    planner_quality_autofix_active = _parse_bool_token(planner_evidence.get("planner_quality_autofix"))

    scrum_actions_sent_60m = 0
    scrum_message_emit_skip_60m = 0
    scrum_last_action_target = ""
    scrum_last_action_message_id = ""
    scrum_events_log = resolve_role_log_path("scrum_master", "events")
    if scrum_events_log and scrum_events_log.exists():
        for ln in _tail_lines(scrum_events_log, 900):
            if not _is_recent_line(ln, 60, now_epoch_status):
                continue
            if "event=scrum_action_posted" in ln:
                scrum_actions_sent_60m += 1
                if not scrum_last_action_target:
                    m_target = re.search(r"\btarget=([a-z0-9_\-]+)", ln, re.IGNORECASE)
                    if m_target:
                        scrum_last_action_target = str(m_target.group(1)).strip().lower()
                if not scrum_last_action_message_id:
                    m_msg = re.search(r"\bmessage_id=([A-Za-z0-9_\-]+)", ln)
                    if m_msg:
                        scrum_last_action_message_id = str(m_msg.group(1)).strip()
            elif "event=scrum_action_skipped_cooldown" in ln or "event=scrum_action_skipped_dedup" in ln:
                scrum_message_emit_skip_60m += 1
    planner_policy_enforced = bool(planner_autonomy.get("wait_forbidden", True))
    planner_autonomy_last_action = str(planner_autonomy.get("last_action", "idle") or "idle").strip() or "idle"
    planner_autonomy_last_outcome = str(planner_autonomy.get("last_outcome", "none") or "none").strip() or "none"

    agents={}
    for role in roles:
        c=contract(role)
        ev = parse_evidence_kv(c.get("EVIDENCE", ""))
        snap = latest_roles.get(role, {}) if isinstance(latest_roles, dict) else {}
        if not isinstance(snap, dict):
            snap = {}
        mins=DEFAULT_SCHEDULE_MAP.get(role, [])
        nm = None
        wait = -1
        if mins:
            nm=next((x for x in sorted(mins) if x>m),sorted(mins)[0])
            wait=(nm-m) if nm>m else (60-m+nm)
        age=tick_age(role)
        source = "runtime_contract" if c else ("monitor_snapshot" if snap else "unknown")
        verdict = c.get("VERDICT") or snap.get("verdict") or "UNKNOWN"
        status_value = c.get("STATUS") or snap.get("status") or "UNKNOWN"
        delta_value = c.get("DELTA") or snap.get("delta") or "NO_DATA"
        blocker_value = c.get("BLOCKER_ID") or snap.get("blocker_id") or "NONE"
        if str(verdict).strip() in {"", "?"}:
            verdict = "UNKNOWN"
        if str(status_value).strip() in {"", "?"}:
            status_value = "UNKNOWN"
        if str(delta_value).strip() in {"", "?"}:
            delta_value = "NO_DATA"
        if str(blocker_value).strip().upper() in {"", "?", "N/A", "NULL"}:
            blocker_value = "NONE"
        planner_action_required = ""
        dev_wait_reason = "none"
        soft_blocker = False
        tshape_active = False
        tshape_target_role = ""
        if role == "planner":
            planner_action_required = str(ev.get("planner_action_required", "")).strip().lower()
            soft_blocker = planner_action_required in {"claim_ready", "create_or_claim", "create_or_claim_now", "dependency_regroup"}
            if not soft_blocker and str(blocker_value).upper() in {
                "HANDOFF_TO_MISSING",
                "PLANNER_BATCH_ID_INVALID",
                "MODE_ANALYSE_NO_EDITS",
                "CONTRACT_GUARD_BLOCK",
                "PLANNER_EVIDENCE_INCOMPLETE",
            }:
                soft_blocker = True

            planner_hard_blockers = {
                "RUN_LOCK_BUSY",
                "LOCK_BUSY",
                "RUN_LOCK_HELD",
                "SESSION_NOT_READY",
                "SESSION_NOT_READY_43",
                "BACKEND_API_UNREACHABLE",
                "MONITOR_API_UNREACHABLE",
                "BACKEND_AND_MONITOR_UNREACHABLE",
                "API_DOWN",
                "CONTRACT_PARSE_FAILED",
                "CONTRACT_GUARD_BLOCK",
            }
            planner_status_up = str(status_value or "").strip().upper()
            planner_blocker_up = str(blocker_value or "").strip().upper()
            planner_hard_incident = planner_blocker_up in planner_hard_blockers
            if planner_policy_enforced and planner_status_up in {"WAIT", "MUTED"} and not planner_hard_incident:
                status_value = "IN_PROGRESS"
                verdict = "GO_WITH_CAUTION"
                if str(delta_value or "").strip().upper() in {"NO_DELTA", "NO_DATA", "NONE"}:
                    delta_value = "PLANNER_AUTONOMY_ENFORCED"
                blocker_value = "NONE"
                soft_blocker = True

        if role == "dev":
            dev_wait_reason = dev_wait_reason_runtime
            if dev_wait_reason == "no_dev_ready_task":
                soft_blocker = True
            dev_status_up = str(status_value or "").strip().upper()
            if dev_wait_reason == "none" and dev_status_up in {"WAIT", "MUTED"}:
                status_value = "IN_PROGRESS"
                verdict = "GO_WITH_CAUTION"
                if str(delta_value or "").strip().upper() in {"NO_DELTA", "NO_DATA", "DEV_WAIT_NO_READY_TASK"}:
                    delta_value = "READY_ITEM_AVAILABLE_RUNTIME_CONTEXT"
                blocker_value = "NONE"

        if role == "admin":
            tshape_active = bool(dispatcher_tshape.get("active", False))
            tshape_target_role = str(dispatcher_tshape.get("target_role", "")).strip()
            admin_autonomy_active = bool(admin_autonomy.get("active", False))
            admin_autonomy_target_role = str(admin_autonomy.get("target_role", "")).strip()
            if tshape_active:
                soft_blocker = True
            if admin_autonomy_active:
                soft_blocker = True
            # Admin can emit stale false alarms from advisory checks; if doctor probes
            # confirm both APIs are reachable now, do not hard-block global health.
            admin_runtime_blockers = {
                "BACKEND_API_UNREACHABLE",
                "BACKEND_API_HEALTHCHECK_FAIL",
                "MONITOR_API_UNREACHABLE",
                "BACKEND_AND_MONITOR_UNREACHABLE",
                "RUNTIME_DOWN",
                "RUNTIME_DOWN_BLOCKS_READY_QUEUE",
                "RUNTIME_DEGRADED",
                "RUNTIME_DEGRADED_PORTS_8050_7779_DOWN",
                "RUNTIME_DEGRADED_PORTS_8050_7779_DOWN_CRONS_MISSING",
            }
            doctor_checks = doctor.get("checks", {}) if isinstance(doctor, dict) else {}
            providers_check = doctor_checks.get("providers", {}) if isinstance(doctor_checks, dict) else {}
            if isinstance(providers_check, dict):
                providers_detail = providers_check.get("detail") if isinstance(providers_check.get("detail"), dict) else providers_check
            else:
                providers_detail = {}
            providers_status = str(providers_check.get("status", "")).strip().lower() if isinstance(providers_check, dict) else ""
            api_now_ok = _probe_http_ok("http://127.0.0.1:8050/api/health") or bool(providers_detail.get("api_health_ok", False)) or providers_status == "ok"
            # Avoid self-probing /api/status while serving /api/status.
            mon_now_ok = bool(providers_detail.get("monitor_status_ok", False)) or providers_status == "ok"
            blocker_token = str(blocker_value or "").upper()
            blocker_norm = re.sub(r"[^A-Z0-9_]+", "_", blocker_token).strip("_")
            blocker_is_runtime = False
            for marker in admin_runtime_blockers:
                if blocker_norm == marker or blocker_norm.startswith(f"{marker}_") or marker in blocker_norm:
                    blocker_is_runtime = True
                    break
            admin_runtime_recovered = blocker_is_runtime and api_now_ok and mon_now_ok
            if admin_runtime_recovered:
                soft_blocker = True
                # Stale runtime blocker from previous tick: prefer current probe truth.
                ev["admin_runtime_recovered_from"] = blocker_norm or blocker_token
                ev["admin_runtime_override_applied"] = "1"
                blocker_value = "NONE"
                status_value = "PASS"
                verdict = "PASS"
                if str(delta_value or "").strip().upper() in {
                    "RUNTIME_DEGRADED",
                    "BACKEND_API_UNREACHABLE",
                    "MONITOR_API_UNREACHABLE",
                    "RUNTIME_DOWN",
                    "RUNTIME_DOWN_BLOCKS_READY_QUEUE",
                    "ADMIN_BLOCKED_RUNTIME_DOWN",
                    "RUNTIME_DEGRADED_PORTS_8050_7779_DOWN",
                    "RUNTIME_DEGRADED_PORTS_8050_7779_DOWN_CRONS_MISSING",
                    "RUNTIME_RECOVERED_SOFT",
                }:
                    delta_value = "RUNTIME_VERIFIED_OK"
        if is_rate_limit_marker(verdict, status_value, delta_value, blocker_value):
            if (verdict or "").upper() == "BLOCKED":
                verdict = "WAIT"
            if (status_value or "").upper() == "BLOCKED":
                status_value = "RATE_LIMIT_SKIP"
            if (blocker_value or "").upper().startswith("AGENT_RATE_LIMIT_"):
                blocker_value = "NONE"
        session_not_ready_fallback_count = _role_state_counter(role, "session_not_ready_fallback_count")
        pending_by_role = agent_messages.get("pending_by_role", {}) if isinstance(agent_messages, dict) else {}
        last_id_by_role = agent_messages.get("last_message_id_by_role", {}) if isinstance(agent_messages, dict) else {}
        last_action_status_by_role = (
            agent_messages.get("latest_action_status_by_role", {})
            if isinstance(agent_messages, dict)
            else {}
        )
        pending_count = _int_or_default(pending_by_role.get(role), 0) if isinstance(pending_by_role, dict) else 0
        last_message_id = str(last_id_by_role.get(role, "")).strip() if isinstance(last_id_by_role, dict) else ""
        last_message_action_status = (
            str(last_action_status_by_role.get(role, "none")).strip().lower()
            if isinstance(last_action_status_by_role, dict)
            else "none"
        )
        if last_message_action_status not in {"none", "done", "deferred", "blocked"}:
            last_message_action_status = "none"
        agents[role]={"verdict":verdict,"status":status_value,"delta":delta_value,
                      "blocker":blocker_value,"next":c.get("NEXT") or snap.get("next", ""),
                      "schedule":(f":{','.join(str(x) for x in mins)}" if mins else "manual"),
                      "tick_age_min":age,"next_tick_min":wait,
                      "next_tick_at":(f":{nm:02d}" if nm is not None else "--"),
                      "planner_action_required": planner_action_required,
                      "planner_policy_enforced": planner_policy_enforced if role == "planner" else False,
                      "dev_wait_reason": dev_wait_reason if role == "dev" else "none",
                      "dev_ready_count": (dev_ready_count_runtime if role == "dev" else 0),
                      "dev_wait_allowed": (1 if (role == "dev" and dev_wait_allowed_runtime) else 0),
                      "soft_blocker": soft_blocker,
                      "tshape_active": tshape_active,
                      "tshape_target_role": tshape_target_role,
                      "admin_autonomy_active": (admin_autonomy_active if role == "admin" else False),
                      "admin_autonomy_target_role": (admin_autonomy_target_role if role == "admin" else ""),
                      "session_not_ready_fallback_count": session_not_ready_fallback_count,
                      "pending_messages_count": pending_count,
                      "last_message_id": last_message_id,
                      "last_message_action_status": last_message_action_status,
                      "quality_missing_fields": (planner_quality_missing_fields if role == "planner" else []),
                      "quality_autofix_active": (planner_quality_autofix_active if role == "planner" else False),
                      "actions_sent_60m": (scrum_actions_sent_60m if role == "scrum_master" else 0),
                      "last_action_target": (scrum_last_action_target if role == "scrum_master" else ""),
                      "last_action_message_id": (scrum_last_action_message_id if role == "scrum_master" else ""),
                      "source": source}
    agents, incomplete_roles = monitor_ensure_core_agents(agents, core_roles=CORE_ROLES)
    kpi={}
    try:
        kd=kpi_last(); v=kd.get("velocity",{}); wb2=kd.get("workboard",{})
        lv = latest_snapshot.get("velocity", {}) if isinstance(latest_snapshot, dict) else {}
        if not isinstance(lv, dict):
            lv = {}
        kpi={"done_total":wb2.get("done") or kd.get("done_total") or hs_workboard.get("done"),
             "done_24h":v.get("done_24h") or kd.get("done_24h") or lv.get("done_24h"),
             "done_7d":v.get("done_7d") or lv.get("done_7d"),
             "proofs":v.get("proofs") or lv.get("proofs"),
             "ts":(kd.get("ts_utc","") or latest_snapshot.get("updated_at",""))[:16]}
    except: pass
    rl=rate_limits()
    core_agents = [agents.get(role, {}) for role in CORE_ROLES if isinstance(agents.get(role, {}), dict)]
    hard_blocked = any(
        (a.get("blocker", "NONE") not in ("NONE", ""))
        and not bool(a.get("soft_blocker"))
        and not is_rate_limit_marker(a.get("verdict", ""), a.get("status", ""), a.get("delta", ""), a.get("blocker", ""))
        for a in core_agents
    )
    rate_limited_agents = any(
        is_rate_limit_marker(a.get("verdict", ""), a.get("status", ""), a.get("delta", ""), a.get("blocker", ""))
        for a in core_agents
    )
    issues_summary_60 = _issue_summary_window(window_min=60)
    issues_recent_by_role = issues_summary_60.get("issues_recent_by_role", {})
    if not isinstance(issues_recent_by_role, dict):
        issues_recent_by_role = {}
    critical_count = _int_or_default(issues_summary_60.get("critical_open_count"), 0)
    issue_publication_gap_roles = issues_summary_60.get("issue_publication_gap_roles", [])
    if not isinstance(issue_publication_gap_roles, list):
        issue_publication_gap_roles = []
    role_latest_issue = issues_summary_60.get("role_latest", {})
    if not isinstance(role_latest_issue, dict):
        role_latest_issue = {}

    now_epoch = time.time()
    last_issue_by_role: dict[str, dict] = {}
    reports_with_issues = 0
    for role in roles:
        latest_issue = role_latest_issue.get(role, {})
        if not isinstance(latest_issue, dict):
            latest_issue = {}
        issue_codes = latest_issue.get("issue_codes", [])
        if not isinstance(issue_codes, list):
            issue_codes = []
        first_code = str(issue_codes[0]) if issue_codes else "none"
        ts_epoch = _parse_ts_epoch(str(latest_issue.get("ts_utc", "")))
        age_min = int((now_epoch - ts_epoch) / 60) if ts_epoch is not None else -1
        issue_count = _int_or_default(issues_recent_by_role.get(role), 0)
        if issue_count > 0:
            reports_with_issues += 1
        last_issue_by_role[role] = {
            "code": first_code,
            "age_min": age_min,
            "max_severity": _severity_token(latest_issue.get("max_severity", "INFO")),
        }

    issue_reporting = {
        "roles_total": len(roles),
        "roles_missing_report": sorted(issue_publication_gap_roles),
        "reports_with_issues": reports_with_issues,
        "critical_count": critical_count,
    }

    queue_path = orchestrator_file("priority-queue.json")
    workboard_path = orchestrator_file("parallel-workstreams.json")
    kpi_path = orchestrator_file("kpi-history.jsonl")
    runtime_paths = [
        queue_path,
        workboard_path,
        *[ROOT / f"logs-codex-runs/fc-ticks/{role}.tick.log" for role in roles],
    ]
    data_source, data_freshness_s = monitor_detect_data_source(runtime_paths, kpi_path)

    freshness_state = "fresh" if 0 <= data_freshness_s <= 240 else ("warm" if 0 <= data_freshness_s <= 900 else "stale")
    unknown_core_agents = all(str(a.get("source", "unknown")) == "unknown" for a in core_agents)
    force_degraded = bool(incomplete_roles) or data_source == "unknown" or unknown_core_agents
    summary = latest_snapshot.get("summary", {}) if isinstance(latest_snapshot, dict) else {}
    blocker_roles = summary.get("blocker_roles", []) if isinstance(summary, dict) else []
    blocker_roles = blocker_roles if isinstance(blocker_roles, list) else []
    health = monitor_compute_health(
        force_degraded=force_degraded,
        hard_blocked=hard_blocked,
        has_rate_limits=bool(rl),
        has_rate_limited_agents=rate_limited_agents,
        summary_blocker_roles=blocker_roles,
    )
    health_breakdown = {
        "core_roles": list(CORE_ROLES),
        "by_role": {
            role: {
                "status": str(agents.get(role, {}).get("status", "UNKNOWN")),
                "verdict": str(agents.get(role, {}).get("verdict", "UNKNOWN")),
                "blocker": str(agents.get(role, {}).get("blocker", "NONE")),
            }
            for role in CORE_ROLES
        },
    }

    queue_ready_planner = _int_or_default(queue_state_counts.get("READY_PLANNER"), 0)
    queue_ready_dev = _int_or_default(queue_state_counts.get("READY_DEV"), 0)
    queue_ready_legacy = _int_or_default(queue_state_counts.get("READY"), 0)
    ready_dev_display_count = dev_ready_count_runtime if monitor_ready_dev_from_workboard else queue_ready_dev
    ready_dev_source = "workboard_runtime" if monitor_ready_dev_from_workboard else "queue_state"
    queue_ready = queue_ready_planner + queue_ready_legacy + ready_dev_display_count
    queue_waiting_dep = _int_or_default(queue_state_counts.get("WAITING_DEP"), 0)
    queue_in_progress = _int_or_default(queue_state_counts.get("IN_PROGRESS"), 0)
    if queue_total == 0 and isinstance(hs_queue, dict) and hs_queue:
        queue_ready = _int_or_default(hs_queue.get("ready"), queue_ready)
        queue_waiting_dep = _int_or_default(hs_queue.get("waiting_dep"), queue_waiting_dep)
        queue_in_progress = _int_or_default(hs_queue.get("in_progress"), queue_in_progress)

    inter_batch_dependency_count = 0
    for item in queue_items:
        if not isinstance(item, dict):
            continue
        deps = item.get("depends_on", [])
        if isinstance(deps, list):
            inter_batch_dependency_count += sum(1 for dep in deps if str(dep).strip())
        elif str(deps).strip():
            inter_batch_dependency_count += 1

    sanitized_dependencies_24h = 0
    planner_autobatch_24h = 0
    events = wb.get("events", []) if isinstance(wb, dict) else []
    if isinstance(events, list):
        cutoff_epoch = now.timestamp() - 86400
        for event in events:
            if not isinstance(event, dict):
                continue
            kind = str(event.get("kind", "")).strip().lower()
            if kind not in {
                "auto_advance_queue",
                "dependency_policy_migration_v1",
                "dependency_policy_sanitize",
                "planner_autobatch_created",
            }:
                continue
            event_epoch = _parse_ts_epoch(event.get("at", ""))
            if event_epoch is None or event_epoch < cutoff_epoch:
                continue
            if kind == "planner_autobatch_created":
                planner_autobatch_24h += 1
                continue
            details = event.get("details", {})
            if not isinstance(details, dict):
                details = {}
            decoupled = _int_or_default(
                details.get("decoupled_total", details.get("decoupled_batches", 0)), 0
            )
            waiting_reclassified = _int_or_default(details.get("waiting_dep_reclassified"), 0)
            sanitized_dependencies_24h += max(0, decoupled) + max(0, waiting_reclassified)

    planner_passive_events_60m = 0
    guardian_events_path = orchestrator_file("planner-guardian-events.jsonl")
    if guardian_events_path.exists():
        cutoff_epoch_60 = now.timestamp() - 3600
        guardian_lines = _tail_lines(guardian_events_path, 2400)
        for raw in guardian_lines:
            line = raw.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except Exception:
                continue
            if not isinstance(item, dict):
                continue
            event_epoch = _parse_ts_epoch(
                str(item.get("ts_utc") or item.get("ts") or item.get("timestamp") or "")
            )
            if event_epoch is None or event_epoch < cutoff_epoch_60:
                continue
            issues = item.get("issues", [])
            if isinstance(issues, list):
                issue_tokens = {str(v).strip().lower() for v in issues if str(v).strip()}
            else:
                issue_tokens = {
                    tok.strip().lower()
                    for tok in str(issues or "").split(",")
                    if tok.strip()
                }
            if "planner_passive_forbidden_violation" in issue_tokens:
                planner_passive_events_60m += 1

    # Backward-compatible top-level summary used by legacy monitor consumers.
    batches_payload = {
        "total": queue_total,
        "closed": queue_closed,
        "ready": queue_ready,
        "waiting_dep": queue_waiting_dep,
        "in_progress": queue_in_progress,
        "display_total": queue_display_total,
        "display_closed": queue_display_closed,
    }
    orchestration_payload = {
        "dependency_policy": "single_batch",
        "inter_batch_dependency_count": inter_batch_dependency_count,
        "sanitized_dependencies_24h": sanitized_dependencies_24h,
        "planner_non_passive_policy": "enforced",
        "planner_passive_events_60m": planner_passive_events_60m,
        "planner_autobatch_24h": planner_autobatch_24h,
        "planner_quality_score": planner_quality_score,
        "planner_quality_missing_count": planner_quality_missing_count,
        "scrum_actions_sent_60m": scrum_actions_sent_60m,
        "scrum_message_emit_skip_60m": scrum_message_emit_skip_60m,
        "dev_ready_count": dev_ready_count_runtime,
        "dev_ready_tasks": dev_ready_task_ids_runtime[:8],
        "orchestrator_source": orchestrator_source,
        "dev_force_claim_events_60m": dev_force_claim_events_60m,
    }
    activity_bundle = _activity_bundle(ACTIVITY_FEED_WINDOW_HOURS, min(ACTIVITY_FEED_MAX_EVENTS, 220))
    activity_summary = _activity_summary_from_bundle(activity_bundle)
    dynamic_workers = _dynamic_workers_snapshot()
    planner_subagents = _planner_subagents_snapshot()
    execution_mode = _execution_mode(ROOT)

    payload = {"ts_utc":now.isoformat(),"health":health,
            "instance":INSTANCE_ID,
            "root":str(ROOT),
            "state_dir":str(STATE),
            "execution_mode": execution_mode,
            "roles":list(roles),
            "done": workboard_done,
            "ready": workboard_ready,
            "batches": batches_payload,
            "dev_parent": dev_parent_snapshot(),
            "issue_reporting": issue_reporting,
            "queue":{"total":queue_total,"closed":queue_closed,
                     "ready":queue_ready,"ready_planner_count":queue_ready_planner + queue_ready_legacy,"ready_dev_count":ready_dev_display_count,
                     "dev_ready_task_count":dev_ready_count_runtime,"dev_claimable_ready_count":dev_claimable_ready_count_runtime,
                     "ready_dev_source":ready_dev_source,"waiting_dep":queue_waiting_dep,"in_progress":queue_in_progress,
                     "active":queue_active_rows,
                     "display_total":queue_display_total,
                     "display_closed":queue_display_closed,
                     "display_batches":queue_display_rows,
                     "state_counts":queue_state_counts,
                     "mismatch_count":len(mismatches),
                     "mismatches":mismatches[:8]},
            "workboard":{"total":workboard_total,"done":workboard_done,"ready":workboard_ready,"in_progress":workboard_in_progress,
                         "ready_tasks":ready_t,"in_progress_tasks":ip_t,
                         "state_counts":workboard_state_counts},
            "orchestration": orchestration_payload,
            "activity_summary": activity_summary,
            "agents":agents,"rate_limits":rl,"kpi":kpi,"health_breakdown":health_breakdown,
            "planner_autonomy": planner_autonomy,
            "planner_policy_enforced": planner_policy_enforced,
            "planner_autonomy_last_action": planner_autonomy_last_action,
            "planner_autonomy_last_outcome": planner_autonomy_last_outcome,
            "dev_wait_reason": dev_wait_reason_runtime,
            "dev_ready_task_count": dev_ready_count_runtime,
            "dev_claimable_ready_count": dev_claimable_ready_count_runtime,
            "ready_dev_source": ready_dev_source,
            "dispatcher_tshape": dispatcher_tshape,
            "admin_autonomy": admin_autonomy,
            "admin_dispatch": admin_dispatch,
            "planner_evidence_quality_score": planner_evidence_quality_score,
            "queue_workboard_integrity": queue_workboard_integrity,
            "dynamic_workers": dynamic_workers,
            "planner_subagents": planner_subagents,
            "po_scrum_master": po_scrum_master,
            "agent_messages": agent_messages,
            "doctor": doctor,
            "issues_recent_by_role": issues_recent_by_role,
            "critical_open_count": critical_count,
            "issue_publication_gap_roles": issue_publication_gap_roles,
            "last_issue_by_role": last_issue_by_role,
            "runtime_freshness":{"seconds":data_freshness_s,"state":freshness_state},
            "data_freshness_s":data_freshness_s,
            "data_source":data_source,
            "agents_incomplete":incomplete_roles,
            "sources":{
                "queue":str(queue_path),
                "workboard":str(workboard_path),
                "kpi":str(kpi_path),
                "iteration_issues_events": str(ITERATION_ISSUES_EVENTS_FILE),
                "iteration_issues_latest": str(ITERATION_ISSUES_LATEST_FILE),
                "planner_guardian_latest": str(orchestrator_file("planner-guardian-latest.json")),
                "planner_guardian_events": str(orchestrator_file("planner-guardian-events.jsonl")),
                }}
    try:
        from apps.monitor.services.status_service import build_status_snapshot

        payload = build_status_snapshot(ROOT, lambda: payload)
    except Exception:
        pass
    return payload

@app.get("/api/ticks/{role}")
def ticks(role:str, n:int=25):
    roles = monitor_roles()
    if role=="all":
        return {r: tick_hist(r, n) for r in roles}
    return {"role":role,"ticks":tick_hist(role,n)}

@app.get("/api/contract/{role}")
def get_contract(role:str):
    raw=contract_raw(role)
    if not raw: return JSONResponse({"error":"not found"},status_code=404)
    return JSONResponse({"role":role,"contract":raw},media_type="application/json")

@app.get("/api/logs/{role}")
def logs(role:str, n:int=80):
    log=ROOT/f"logs-codex-runs/role-runner/{role}.live.log"
    if not log.exists(): return JSONResponse({"error":"not found"},status_code=404)
    return {"role":role,"lines":_tail_lines(log, n)}

@app.get("/api/logs/{role}/events")
def log_events(role:str, n:int=120):
    log = ROOT / f"logs-codex-runs/role-runner/{role}.events.log"
    if not log.exists():
        return JSONResponse({"error":"not found"}, status_code=404)
    return {"role": role, "lines": _tail_lines(log, n)}

@app.get("/api/planner/timeline")
def planner_timeline(n:int=150):
    timeline = orchestrator_file("planner-timeline.log")
    if not timeline.exists():
        return JSONResponse({"error":"not found"}, status_code=404)
    return {"role":"planner", "lines": _tail_lines(timeline, n)}

@app.get("/api/planner/log-bundle")
def planner_log_bundle(n:int=120):
    timeline = orchestrator_file("planner-timeline.log")
    audit = orchestrator_file("planner-audit-events.jsonl")
    guardian_events = orchestrator_file("planner-guardian-events.jsonl")
    guardian_latest = orchestrator_file("planner-guardian-latest.json")
    runner_events = ROOT / "logs-codex-runs/role-runner/planner.events.log"

    latest = {}
    if guardian_latest.exists():
        try:
            loaded = json.loads(guardian_latest.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(loaded, dict):
                latest = loaded
        except Exception:
            latest = {}

    return {
        "role": "planner",
        "guardian_latest": latest,
        "guardian_events": _tail_jsonl(guardian_events, n),
        "audit_events": _tail_jsonl(audit, n),
        "timeline": _tail_lines(timeline, n),
        "runner_events": _tail_lines(runner_events, n),
        "paths": {
            "timeline": str(timeline),
            "audit_events": str(audit),
            "guardian_events": str(guardian_events),
            "guardian_latest": str(guardian_latest),
            "runner_events": str(runner_events),
        },
    }

@app.get("/api/execution/{role}")
def execution(role: str, tick_n: int = 35, runner_n: int = 55):
    roles = monitor_roles()
    if role == "all":
        return {r: latest_execution(r, tick_n=tick_n, runner_n=runner_n) for r in roles}
    if role not in roles:
        return JSONResponse({"error": "invalid role"}, status_code=400)
    return latest_execution(role, tick_n=tick_n, runner_n=runner_n)

@app.get("/api/execution-insights/{role}")
def execution_insights(role: str):
    roles = monitor_roles()
    if role == "all":
        return {r: execution_insight(r) for r in roles}
    if role not in roles:
        return JSONResponse({"error": "invalid role"}, status_code=400)
    return execution_insight(role)

@app.get("/api/agent-insights")
def agent_insights():
    roles = monitor_roles()
    parent = dev_parent_snapshot()
    if not isinstance(parent, dict):
        parent = {}
    agents: dict[str, dict] = {}
    for role in roles:
        parsed = parse_contract_fields(role)
        ex = latest_execution(role, tick_n=80, runner_n=120)
        tick_tail = ex.get("tick_tail", []) or []
        runner_tail = ex.get("runner_tail", []) or []
        last_action = ""
        last_contract = ""
        for ln in reversed(tick_tail):
            if not last_action and "[ACTION]" in ln:
                last_action = ln
            if not last_contract and "[CONTRACT]" in ln:
                last_contract = ln
            if last_action and last_contract:
                break
        # Interesting execution if a concrete change is claimed/completed/handoff
        # and quality is not weak.
        t = parsed.get("task_update", "unknown")
        interesting = t in {"claim", "complete", "handoff"} and parsed.get("quality") in {"STRONG", "MEDIUM"}
        payload = {
            **parsed,
            "last_execution": {
                "last_ts": ex.get("last_ts", ""),
                "last_rc": ex.get("last_rc"),
                "last_agent": ex.get("last_agent", ""),
                "last_start": ex.get("last_start", ""),
                "last_end": ex.get("last_end", ""),
            },
            "last_action_line": last_action,
            "last_contract_line": last_contract,
            "runner_tail": runner_tail[-24:],
            "tick_tail": tick_tail[-24:],
            "interesting_execution": interesting,
        }
        if role == "dev":
            dev_autonomy = _dev_autonomy_from_parent(parent)
            payload["dev_parent"] = parent
            payload["dev_autonomy"] = dev_autonomy
            payload["channels_missing_streak_24h"] = dev_autonomy["channels_missing_streak_24h"]
            payload["none_signal_streak_24h"] = dev_autonomy["none_no_signal_streak_24h"]
            payload["contract_guard_block_count_24h"] = dev_autonomy["contract_guard_block_count_24h"]
            payload["issue_reporting_ok_rate_24h"] = dev_autonomy["issue_reporting_ok_rate_24h"]
            payload["coaching_state"] = dev_autonomy["coaching_state"]
            payload["delivery_actions_24h"] = dev_autonomy["delivery_actions_24h"]
            payload["enforced_delivery_count_24h"] = dev_autonomy["enforced_delivery_count_24h"]
            payload["stall_recovery_rate_24h"] = dev_autonomy["stall_recovery_rate_24h"]
            payload["ready_seen_without_claim_24h"] = dev_autonomy["ready_seen_without_claim_24h"]
        agents[role] = payload
    return {"roles": list(roles), "agents": agents}

@app.get("/api/dev-parent")
def dev_parent():
    snap = dev_parent_snapshot()
    if not snap:
        return JSONResponse({"error": "not found"}, status_code=404)
    return snap

@app.get("/api/log-catalog")
def log_catalog():
    roles = monitor_roles()
    data: dict[str, dict[str, dict]] = {}
    for role in roles:
        role_entry: dict[str, dict] = {}
        for kind in LOG_KIND_LABELS:
            p = resolve_role_log_path(role, kind)
            exists = bool(p and p.exists())
            size = 0
            if exists and p:
                try:
                    size = int(p.stat().st_size)
                except Exception:
                    size = 0
            role_entry[kind] = {
                "label": LOG_KIND_LABELS[kind],
                "path": str(p) if p else "",
                "exists": exists,
                "size_bytes": size,
            }
        data[role] = role_entry
    return {"roles": list(roles), "kinds": list(LOG_KIND_LABELS.keys()), "catalog": data}

@app.get("/api/log-view")
def log_view(role: str = "planner", kind: str = "tick", n: int = 180):
    roles = monitor_roles()
    role = (role or "").strip()
    kind = (kind or "").strip().lower()
    if role not in roles:
        return JSONResponse({"error": "invalid role"}, status_code=400)
    if kind not in LOG_KIND_LABELS:
        return JSONResponse({"error": "invalid kind"}, status_code=400)
    p = resolve_role_log_path(role, kind)
    if p is None:
        return JSONResponse({"error": "invalid target"}, status_code=400)
    n = max(20, min(int(n), 600))
    lines = _tail_lines(p, n)
    entries = []
    counts = {"error": 0, "warn": 0, "action": 0, "contract": 0, "ok": 0, "meta": 0, "normal": 0}
    for ln in lines:
        sev = classify_log_line(ln)
        if sev not in counts:
            counts[sev] = 0
        counts[sev] += 1
        entries.append({"ts": _extract_ts(ln), "severity": sev, "line": ln})
    return {
        "role": role,
        "kind": kind,
        "label": LOG_KIND_LABELS[kind],
        "path": str(p),
        "exists": p.exists(),
        "lines": lines,
        "entries": entries,
        "severity_counts": counts,
    }

@app.get("/api/error-feed")
def error_feed(n: int = 120, recent_minutes: int = ERROR_FEED_RECENT_MINUTES):
    max_lines = max(40, min(int(n), 400))
    recent_minutes = max(0, min(int(recent_minutes), 24 * 60))
    rows: list[dict] = []
    dropped_stale = 0
    now_epoch = time.time()
    for role in monitor_roles():
        for kind in ("tick", "cron", "runner", "events", "contract"):
            p = resolve_role_log_path(role, kind)
            if p is None or not p.exists():
                continue
            for ln in _tail_lines(p, max_lines):
                sev = classify_log_line(ln)
                if sev not in {"error", "warn"}:
                    continue
                if not _is_recent_line(ln, recent_minutes, now_epoch):
                    dropped_stale += 1
                    continue
                rows.append({
                    "ts": _extract_ts(ln),
                    "role": role,
                    "kind": kind,
                    "severity": sev,
                    "line": ln,
                })
    # ISO timestamps are lexicographically sortable.
    rows.sort(key=lambda x: x.get("ts", ""), reverse=True)
    return {
        "count": len(rows),
        "items": rows[:max_lines],
        "recent_minutes": recent_minutes,
        "dropped_stale": dropped_stale,
    }


@app.get("/api/issues/feed")
def issues_feed(n: int = 200, role: str = "", severity: str = "", window_min: int = 180):
    n = max(10, min(int(n), 600))
    window_min = max(1, min(int(window_min), 24 * 60))
    rows = _load_iteration_issue_rows(
        role=role,
        severity=severity,
        recent_minutes=window_min,
        n=n,
    )
    rows.sort(key=lambda r: str(r.get("ts_utc", "")), reverse=True)
    return {
        "count": len(rows),
        "items": rows[:n],
        "filters": {
            "role": role or "all",
            "severity": severity or "all",
            "window_min": window_min,
            "n": n,
        },
        "source": str(ITERATION_ISSUES_EVENTS_FILE),
        "source_aliases": [str(p) for p in _iteration_issue_event_sources() if str(p) != str(ITERATION_ISSUES_EVENTS_FILE)],
    }


@app.get("/api/issues/summary")
def issues_summary(window_min: int = 60):
    window_min = max(1, min(int(window_min), 24 * 60))
    summary = _issue_summary_window(window_min=window_min)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_min": window_min,
        "total_records": summary.get("total_records", 0),
        "totals_by_severity": summary.get("totals_by_severity", {}),
        "top_codes": summary.get("top_codes", []),
        "roles_touched": summary.get("roles_touched", []),
        "mttr_estimated_by_role": summary.get("mttr_estimated_by_role", {}),
        "issues_recent_by_role": summary.get("issues_recent_by_role", {}),
        "critical_open_count": summary.get("critical_open_count", 0),
        "issue_publication_gap_roles": summary.get("issue_publication_gap_roles", []),
        "source": str(ITERATION_ISSUES_EVENTS_FILE),
        "source_aliases": [str(p) for p in _iteration_issue_event_sources() if str(p) != str(ITERATION_ISSUES_EVENTS_FILE)],
    }


@app.get("/api/iteration-issues")
def iteration_issues(role: str = "", severity: str = "", recent_minutes: int = 180, n: int = 120):
    return issues_feed(n=n, role=role, severity=severity, window_min=recent_minutes)


# Doctor routes are mounted via layered router in apps/monitor/src/api/doctor_router.py

@app.get("/api/runtime-diagnostics")
def runtime_diagnostics():
    try:
        status_snapshot = status()
    except Exception:
        status_snapshot = {
            "health": "DEGRADED",
            "data_freshness_s": -1,
            "data_source": "unknown",
            "agents": {role: _unknown_agent_payload(role) for role in CORE_ROLES},
            "issue_publication_gap_roles": [],
            "dev_parent": {},
            "po_scrum_master": {
                "name": "po_scrum_master",
                "mode": "scheduled_advisory",
                "active": False,
                "last_run": "",
                "last_run_age_min": -1,
                "lock_skip_streak": 0,
                "last_messages_posted": 0,
                "source": "unknown",
            },
            "planner_evidence_quality_score": 0,
            "queue_workboard_integrity": {
                "status": "unknown",
                "mismatch_count": 0,
                "oldest_mismatch_age_s": -1,
                "queue_only": [],
                "workboard_only": [],
                "state_mismatch": [],
            },
            "admin_autonomy": {
                "active": False,
                "trigger": "none",
                "target_role": "",
                "target_task": "none",
                "reason_blocker": "NONE",
                "last_action": "idle",
                "last_outcome": "none",
                "age_min": -1,
                "streak_by_role": {"planner": 0, "dev": 0},
                "needs_human_review_by_role": {"planner": False, "dev": False},
            },
            "admin_dispatch": {
                "status": "unknown",
                "last_action": "none",
                "last_reason": "none",
                "dispatch_reason_code": "none",
                "autonomy_reason_code": "none",
                "stream_fairness_slot": 0,
                "cooldown_left_s": 0,
                "last_result_ts": "",
                "last_result_age_s": -1,
                "source": str(ADMIN_DISPATCH_LOG_FILE),
            },
            "agent_messages": {
                "open": 0,
                "open_count": 0,
                "delivered": 0,
                "delivered_count": 0,
                "actioned": 0,
                "actioned_count": 0,
                "closed": 0,
                "closed_count": 0,
                "delivered_recent": 0,
                "actioned_recent": 0,
                "closed_recent": 0,
                "expired": 0,
                "expired_count": 0,
                "posted": 0,
                "posted_count": 0,
                "pending_by_role": {"planner": 0, "dev": 0, "admin": 0},
                "open_by_role": {"planner": 0, "dev": 0, "admin": 0},
                "last_message_id_by_role": {"planner": "", "dev": "", "admin": ""},
                "latest_action_status_by_role": {"planner": "none", "dev": "none", "admin": "none"},
                "source": str(AGENT_MESSAGE_BUS_FILE),
            },
            "orchestration": {
                "dependency_policy": "single_batch",
                "inter_batch_dependency_count": 0,
                "sanitized_dependencies_24h": 0,
                "planner_non_passive_policy": "enforced",
                "planner_passive_events_60m": 0,
                "planner_autobatch_24h": 0,
                "planner_quality_score": 100,
                "planner_quality_missing_count": 0,
                "scrum_actions_sent_60m": 0,
                "scrum_message_emit_skip_60m": 0,
                "dev_ready_count": 0,
                "dev_ready_tasks": [],
                "orchestrator_source": "canonical",
                "dev_force_claim_events_60m": 0,
            },
        }
    status_agents = status_snapshot.get("agents", {}) if isinstance(status_snapshot, dict) else {}
    if not isinstance(status_agents, dict):
        status_agents = {role: _unknown_agent_payload(role) for role in CORE_ROLES}
    for core_role in CORE_ROLES:
        if core_role not in status_agents:
            status_agents[core_role] = _unknown_agent_payload(core_role)
    dev_parent_data = status_snapshot.get("dev_parent", {}) if isinstance(status_snapshot, dict) else {}
    if not isinstance(dev_parent_data, dict) or not dev_parent_data:
        dev_parent_data = dev_parent_snapshot()
    dev_autonomy_data = _dev_autonomy_from_parent(dev_parent_data)

    logs_root = ROOT / "logs-codex-runs"
    role_recovery_lines = _tail_lines(logs_root / "role-recovery.log", 5000)
    health_lines = _tail_lines(logs_root / "health-snapshot.log", 320)
    resume_lines = _tail_lines(logs_root / "vm-resume.log", 1200)
    admin_event_lines = _tail_lines(logs_root / "role-runner" / "admin.events.log", 700)

    perm_re = re.compile(r"(cannot create directory|operation not permitted|permission denied)", re.I)
    ts_re = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4})")
    recent_perm_hits: list[str] = []
    historical_perm_hits: list[str] = []
    last_perm_ts_epoch: float | None = None
    now_epoch = time.time()
    recent_window_seconds = RUNTIME_DIAG_RECENT_MINUTES * 60
    for ln in role_recovery_lines:
        line_epoch: float | None = None
        m_ts = ts_re.match((ln or "").strip())
        if m_ts:
            try:
                line_epoch = datetime.strptime(m_ts.group(1), "%Y-%m-%dT%H:%M:%S%z").timestamp()
            except Exception:
                line_epoch = None
        if not perm_re.search(ln):
            continue
        if line_epoch is not None and (now_epoch - line_epoch) <= recent_window_seconds:
            recent_perm_hits.append(ln)
        else:
            historical_perm_hits.append(ln)
        if line_epoch is not None and (last_perm_ts_epoch is None or line_epoch > last_perm_ts_epoch):
            last_perm_ts_epoch = line_epoch

    permission_last_error_ts = ""
    permission_last_error_age_min = -1
    if last_perm_ts_epoch is not None:
        permission_last_error_ts = (
            datetime.fromtimestamp(last_perm_ts_epoch, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
        permission_last_error_age_min = max(0, int((now_epoch - last_perm_ts_epoch) // 60))

    blocked_re = re.compile(r"blocked=\[(.*?)\]")
    last_health = health_lines[-1] if health_lines else ""
    last_blocked_roles: list[str] = []
    m_blocked = blocked_re.search(last_health)
    if m_blocked:
        payload = m_blocked.group(1)
        last_blocked_roles = re.findall(r"'([^']+)'", payload)

    degraded_recent = sum(1 for ln in health_lines[-80:] if "health=DEGRADED" in ln)
    stale_recent = sum(1 for ln in health_lines[-80:] if "health=STALE" in ln)

    resume_events = []
    for ln in resume_lines:
        m = re.search(r"status=RESUME_DETECTED.*?gap_s=(\d+)", ln)
        if not m:
            continue
        gap_s = int(m.group(1))
        ts_match = re.search(r'ts="([^"]+)"', ln)
        resume_events.append({
            "ts": ts_match.group(1) if ts_match else "",
            "gap_s": gap_s,
            "line": ln,
        })
    max_gap_s = max((e["gap_s"] for e in resume_events), default=0)

    timeout_re = re.compile(r"event=(primary_prompt_end|retry_prompt_end).*rc=124", re.I)
    admin_timeout_events = [ln for ln in admin_event_lines if timeout_re.search(ln)]
    admin_timeout_recent_lines = [
        ln for ln in admin_timeout_events if _is_recent_line(ln, RUNTIME_DIAG_RECENT_MINUTES, now_epoch)
    ]
    admin_timeout_recent = len(admin_timeout_recent_lines)

    planner_c = contract("planner")
    admin_contract = contract("admin")
    admin_evidence = parse_evidence_kv(admin_contract.get("EVIDENCE", ""))
    planner_blocker = (planner_c.get("BLOCKER_ID", "") or "").strip()
    planner_guard_block = planner_blocker == "PLANNER_BATCH_ID_INVALID"
    dispatcher_tshape = status_snapshot.get("dispatcher_tshape", {}) if isinstance(status_snapshot, dict) else {}
    if not isinstance(dispatcher_tshape, dict):
        dispatcher_tshape = {}
    admin_autonomy = status_snapshot.get("admin_autonomy", {}) if isinstance(status_snapshot, dict) else {}
    if not isinstance(admin_autonomy, dict):
        admin_autonomy = {}
    admin_dispatch = status_snapshot.get("admin_dispatch", {}) if isinstance(status_snapshot, dict) else {}
    if not isinstance(admin_dispatch, dict) or not admin_dispatch:
        admin_dispatch = admin_dispatch_snapshot(now_epoch)
    tshape_active = bool(dispatcher_tshape.get("active", False))
    tshape_age_min = _int_or_default(dispatcher_tshape.get("age_min"), -1)
    tshape_target_role = str(dispatcher_tshape.get("target_role", "")).strip()
    tshape_reason_blocker = str(dispatcher_tshape.get("reason_blocker", "NONE")).strip() or "NONE"
    admin_autonomy_active = bool(admin_autonomy.get("active", False))
    admin_autonomy_trigger = str(admin_autonomy.get("trigger", "none")).strip() or "none"
    admin_autonomy_target_role = str(admin_autonomy.get("target_role", "")).strip()
    admin_autonomy_target_task = str(admin_autonomy.get("target_task", "none")).strip() or "none"
    admin_autonomy_last_outcome = str(admin_autonomy.get("last_outcome", "none")).strip() or "none"
    admin_autonomy_age_min = _int_or_default(admin_autonomy.get("age_min"), -1)
    admin_autonomy_needs_review = admin_autonomy.get("needs_human_review_by_role", {})
    if not isinstance(admin_autonomy_needs_review, dict):
        admin_autonomy_needs_review = {}
    admin_dispatch_status = str(admin_dispatch.get("status", "unknown")).strip().lower() or "unknown"
    admin_dispatch_last_reason = str(admin_dispatch.get("last_reason", "none")).strip() or "none"
    admin_dispatch_last_action = str(admin_dispatch.get("last_action", "none")).strip() or "none"
    admin_dispatch_age_s = _int_or_default(admin_dispatch.get("last_result_age_s"), -1)
    dispatcher_starvation_s = 0
    if admin_dispatch_status in {"noop", "unknown"} and admin_dispatch_age_s >= 0:
        if admin_dispatch_last_reason.startswith("no_dispatch_needed") or admin_dispatch_last_reason == "none":
            dispatcher_starvation_s = admin_dispatch_age_s
    session_not_ready_fallback_count_by_role = {
        role: _role_state_counter(role, "session_not_ready_fallback_count")
        for role in CORE_ROLES
    }
    issue_gap_roles = status_snapshot.get("issue_publication_gap_roles", []) if isinstance(status_snapshot, dict) else []
    if not isinstance(issue_gap_roles, list):
        issue_gap_roles = []
    queue_snapshot = status_snapshot.get("queue", {}) if isinstance(status_snapshot, dict) else {}
    if not isinstance(queue_snapshot, dict):
        queue_snapshot = {}
    queue_state_counts = queue_snapshot.get("state_counts", {})
    if not isinstance(queue_state_counts, dict):
        queue_state_counts = {}
    queue_waiting_dep = _int_or_default(queue_state_counts.get("WAITING_DEP"), 0)
    queue_ready_planner = _int_or_default(queue_state_counts.get("READY_PLANNER"), 0)
    queue_ready_dev = _int_or_default(queue_state_counts.get("READY_DEV"), 0)
    queue_ready_legacy = _int_or_default(queue_state_counts.get("READY"), 0)
    queue_ready = queue_ready_planner + queue_ready_dev + queue_ready_legacy
    queue_in_progress = _int_or_default(queue_state_counts.get("IN_PROGRESS"), 0)
    planner_blocker_upper = str(status_agents.get("planner", {}).get("blocker", "")).strip().upper()
    planner_delta_upper = str(status_agents.get("planner", {}).get("delta", "")).strip().upper()
    planner_evidence_text = str(planner_c.get("EVIDENCE", "") or "")
    planner_policy_enforced_status = bool(status_snapshot.get("planner_policy_enforced", True))
    planner_autonomy_last_action = str(status_snapshot.get("planner_autonomy_last_action", "idle") or "idle").strip() or "idle"
    planner_autonomy_last_outcome = str(status_snapshot.get("planner_autonomy_last_outcome", "none") or "none").strip() or "none"
    orchestration_snapshot = status_snapshot.get("orchestration", {}) if isinstance(status_snapshot, dict) else {}
    if not isinstance(orchestration_snapshot, dict):
        orchestration_snapshot = {}
    planner_quality_score = _int_or_default(orchestration_snapshot.get("planner_quality_score"), 100)
    planner_quality_missing_count = _int_or_default(orchestration_snapshot.get("planner_quality_missing_count"), 0)
    scrum_actions_sent_60m = _int_or_default(orchestration_snapshot.get("scrum_actions_sent_60m"), 0)
    scrum_message_emit_skip_60m = _int_or_default(orchestration_snapshot.get("scrum_message_emit_skip_60m"), 0)
    dev_wait_reason = str(status_snapshot.get("dev_wait_reason", "none") or "none").strip() or "none"
    dev_contract = contract("dev")
    dev_evidence = parse_evidence_kv(dev_contract.get("EVIDENCE", ""))
    passive_with_ready_streak = _int_or_default(dev_evidence.get("passive_with_ready_streak"), 0)
    dev_claim_loop_count = _int_or_default(dev_evidence.get("dev_claim_loop_count"), 0)
    admin_runtime_override_applied = _int_or_default(admin_evidence.get("admin_runtime_override_applied"), 0)

    findings: list[dict] = []
    historical_perm_finding: dict | None = None
    if recent_perm_hits:
        findings.append({
            "id": "PERMISSION_ERRORS_RECENT",
            "severity": "critical",
            "title": "Permission denied in role-recovery",
            "detail": f"{len(recent_perm_hits)} recent hit(s) in role-recovery.log",
            "sample": recent_perm_hits[-1],
        })
    elif historical_perm_hits:
        historical_perm_finding = {
            "id": "PERMISSION_ERRORS_HISTORICAL",
            "severity": "info",
            "title": "Permission denied (historical) in role-recovery",
            "detail": f"{len(historical_perm_hits)} old hit(s), not recent",
            "sample": historical_perm_hits[-1],
        }
    if planner_guard_block:
        findings.append({
            "id": "PLANNER_CONTRACT_GUARD_BLOCK",
            "severity": "critical",
            "title": "Planner contract guard blocked",
            "detail": "BLOCKER_ID=PLANNER_BATCH_ID_INVALID",
            "sample": planner_c.get("NEXT", ""),
        })
    if admin_timeout_recent > 0:
        findings.append({
            "id": "ADMIN_TIMEOUT_BURSTS",
            "severity": "high",
            "title": "Admin prompt timeout bursts",
            "detail": f"{admin_timeout_recent} timeout event(s) rc=124 (recent window)",
            "sample": admin_timeout_recent_lines[-1] if admin_timeout_recent_lines else "",
        })
    if max_gap_s >= 1800:
        findings.append({
            "id": "VM_RESUME_LONG_GAP",
            "severity": "high",
            "title": "VM resume long gap detected",
            "detail": f"max gap_s={max_gap_s}",
            "sample": resume_events[-1]["line"] if resume_events else "",
        })
    if last_blocked_roles and _is_recent_line(last_health, RUNTIME_DIAG_RECENT_MINUTES, now_epoch):
        findings.append({
            "id": "BLOCKED_ROLES_RECENT",
            "severity": "high",
            "title": "Blocked roles seen in health snapshot",
            "detail": ",".join(last_blocked_roles),
            "sample": last_health,
        })
    if issue_gap_roles:
        findings.append({
            "id": "ISSUE_PUBLICATION_GAP",
            "severity": "high",
            "title": "ISSUE_PUBLICATION_GAP",
            "detail": ",".join(sorted(str(x) for x in issue_gap_roles)),
            "sample": "missing agent iteration issue publication within expected cadence",
        })
    dev_coaching_state = str(dev_autonomy_data.get("coaching_state", "RECOVERING") or "RECOVERING").upper()
    dev_none_streak_24h = _int_or_default(dev_autonomy_data.get("none_no_signal_streak_24h"), 0)
    dev_delivery_actions_24h = _int_or_default(dev_autonomy_data.get("delivery_actions_24h"), 0)
    dev_issue_ok_rate_24h = _int_or_default(dev_autonomy_data.get("issue_reporting_ok_rate_24h"), 100)
    if dev_coaching_state == "STALLED" or dev_none_streak_24h >= 3:
        stall_severity = "high" if (dev_coaching_state == "STALLED" or dev_none_streak_24h >= 6) else "warn"
        findings.append({
            "id": "DEV_STALL_LOOP",
            "severity": stall_severity,
            "title": "DEV_STALL_LOOP",
            "detail": (
                f"state={dev_coaching_state}; "
                f"none_no_signal_streak_24h={dev_none_streak_24h}; "
                f"delivery_actions_24h={dev_delivery_actions_24h}; "
                f"issue_ok_rate_24h={dev_issue_ok_rate_24h}"
            ),
            "sample": "dev lane is repeatedly passive while runtime stays active",
        })

    planner_passivity_corrected = (
        "planner_passivity_corrected" in planner_evidence_text.lower()
        or planner_delta_upper == "PLANNER_AUTONOMY_ENFORCED"
    )
    if planner_policy_enforced_status and planner_passivity_corrected:
        findings.append({
            "id": "PLANNER_PASSIVITY_VIOLATION_CORRECTED",
            "severity": "warn",
            "title": "PLANNER_PASSIVITY_VIOLATION_CORRECTED",
            "detail": (
                f"delta={planner_delta_upper or 'UNKNOWN'}; "
                f"last_action={planner_autonomy_last_action}; "
                f"last_outcome={planner_autonomy_last_outcome}"
            ),
            "sample": "planner passive output was normalized to create_or_claim_now",
        })

    if planner_quality_missing_count > 0:
        findings.append({
            "id": "PLANNER_QUALITY_INCOMPLETE",
            "severity": "warn",
            "title": "PLANNER_QUALITY_INCOMPLETE",
            "detail": (
                f"planner_quality_missing_count={planner_quality_missing_count}; "
                f"planner_quality_score={planner_quality_score}"
            ),
            "sample": "planner quality fields missing (soft autofix active, lane not hard-blocked)",
        })

    if dev_wait_reason == "no_dev_ready_task":
        findings.append({
            "id": "DEV_WAIT_NO_READY_TASK",
            "severity": "info",
            "title": "DEV_WAIT_NO_READY_TASK",
            "detail": "dev wait allowed because no dev READY/IN_PROGRESS task exists",
            "sample": "policy dev_wait_ready_task_only active",
        })

    if planner_policy_enforced_status and planner_autonomy_last_action in {
        "create_and_claim",
        "claim_ready",
        "create_top_level",
        "create_or_claim_now",
    }:
        findings.append({
            "id": "PLANNER_AUTONOMY_CREATE_CLAIM",
            "severity": "info",
            "title": "PLANNER_AUTONOMY_CREATE_CLAIM",
            "detail": (
                f"last_action={planner_autonomy_last_action}; "
                f"last_outcome={planner_autonomy_last_outcome}"
            ),
            "sample": "planner autonomy executed create/claim path",
        })
    if queue_waiting_dep >= 10 and queue_ready <= 1 and (planner_blocker_upper == "DEPENDENCY_WAIT" or queue_in_progress <= 2):
        findings.append({
            "id": "DEPENDENCY_FUNNEL_PLATEAU",
            "severity": "high",
            "title": "DEPENDENCY_FUNNEL_PLATEAU",
            "detail": (
                f"queue_waiting_dep={queue_waiting_dep}; "
                f"queue_ready={queue_ready}; "
                f"queue_in_progress={queue_in_progress}; "
                f"planner_blocker={planner_blocker_upper or 'NONE'}"
            ),
            "sample": "high WAITING_DEP with low READY indicates a dependency fan-in bottleneck",
        })
    if tshape_active and tshape_age_min >= RUNTIME_DIAG_RECENT_MINUTES:
        findings.append({
            "id": "T_SHAPE_TAKEOVER_ACTIVE",
            "severity": "high",
            "title": "T_SHAPE_TAKEOVER_ACTIVE",
            "detail": f"age_min={tshape_age_min}; target={tshape_target_role or 'unknown'}; blocker={tshape_reason_blocker}",
            "sample": "admin takeover still active beyond recent diagnostics window",
        })
    if admin_autonomy_active:
        findings.append({
            "id": "ADMIN_STALL_TAKEOVER_ACTIVE",
            "severity": "high",
            "title": "ADMIN_STALL_TAKEOVER_ACTIVE",
            "detail": (
                f"trigger={admin_autonomy_trigger}; target={admin_autonomy_target_role or 'none'}; "
                f"task={admin_autonomy_target_task}; outcome={admin_autonomy_last_outcome}"
            ),
            "sample": "admin autonomy takeover is active",
        })
    if any(bool(v) for v in admin_autonomy_needs_review.values()):
        review_roles = ",".join(sorted(k for k, v in admin_autonomy_needs_review.items() if bool(v)))
        findings.append({
            "id": "ADMIN_AUTONOMY_NEEDS_HUMAN_REVIEW",
            "severity": "error",
            "title": "ADMIN_AUTONOMY_NEEDS_HUMAN_REVIEW",
            "detail": f"roles={review_roles or 'unknown'}",
            "sample": "autonomy reached retry failsafe on target lane",
        })
    if admin_autonomy_last_outcome in {"deferred", "partial"} and admin_autonomy_age_min >= 0:
        findings.append({
            "id": "ADMIN_AUTONOMY_LOOP_GUARD",
            "severity": "warn",
            "title": "ADMIN_AUTONOMY_LOOP_GUARD",
            "detail": (
                f"outcome={admin_autonomy_last_outcome}; trigger={admin_autonomy_trigger}; "
                f"age_min={admin_autonomy_age_min}"
            ),
            "sample": "autonomy backoff/cooldown guard is active",
        })

    # Historical-only permission debt remains visible but should not overshadow live incidents.
    if historical_perm_finding:
        findings.append(historical_perm_finding)

    if not findings:
        findings.append({
            "id": "NO_RUNTIME_ANOMALY",
            "severity": "ok",
            "title": "No critical runtime anomaly in scanned window",
            "detail": "logs look stable in recent tails",
            "sample": "",
        })

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_freshness_s": status_snapshot.get("data_freshness_s", -1),
        "data_source": status_snapshot.get("data_source", "unknown"),
        "agents": status_agents,
        "po_scrum_master": status_snapshot.get("po_scrum_master", {}),
        "admin_autonomy": admin_autonomy,
        "admin_dispatch": admin_dispatch,
        "dev_autonomy": dev_autonomy_data,
        "agent_messages": status_snapshot.get("agent_messages", {}),
        "window": {
            "role_recovery_lines": len(role_recovery_lines),
            "health_snapshot_lines": len(health_lines),
            "vm_resume_lines": len(resume_lines),
            "admin_events_lines": len(admin_event_lines),
        },
        "signals": {
            "recent_window_minutes": RUNTIME_DIAG_RECENT_MINUTES,
            "permission_errors_recent": len(recent_perm_hits),
            "permission_errors_historical": len(historical_perm_hits),
            "permission_last_error_ts": permission_last_error_ts,
            "permission_last_error_age_min": permission_last_error_age_min,
            "health_degraded_recent": degraded_recent,
            "health_stale_recent": stale_recent,
            "health_last_blocked_roles": last_blocked_roles,
            "resume_detected_count": len(resume_events),
            "resume_max_gap_s": max_gap_s,
            "admin_timeout_events_recent": admin_timeout_recent,
            "admin_timeout_events_historical": max(0, len(admin_timeout_events) - admin_timeout_recent),
            "planner_guard_blocked": planner_guard_block,
            "planner_blocker_id": planner_blocker or "NONE",
            "tshape_takeover_active": tshape_active,
            "tshape_takeover_age_min": tshape_age_min,
            "tshape_takeover_target_role": tshape_target_role,
            "tshape_takeover_reason_blocker": tshape_reason_blocker,
            "admin_autonomy_active": admin_autonomy_active,
            "admin_autonomy_trigger": admin_autonomy_trigger,
            "admin_autonomy_target_role": admin_autonomy_target_role,
            "admin_autonomy_target_task": admin_autonomy_target_task,
            "admin_autonomy_last_outcome": admin_autonomy_last_outcome,
            "admin_autonomy_age_min": admin_autonomy_age_min,
            "admin_autonomy_needs_human_review": admin_autonomy_needs_review,
            "admin_dispatch_status": admin_dispatch_status,
            "admin_dispatch_last_action": admin_dispatch_last_action,
            "admin_dispatch_last_reason": admin_dispatch_last_reason,
            "dispatcher_starvation_s": dispatcher_starvation_s,
            "planner_policy_enforced": planner_policy_enforced_status,
            "planner_autonomy_last_action": planner_autonomy_last_action,
            "planner_autonomy_last_outcome": planner_autonomy_last_outcome,
            "planner_quality_score": planner_quality_score,
            "planner_quality_missing_count": planner_quality_missing_count,
            "scrum_actions_sent_60m": scrum_actions_sent_60m,
            "scrum_message_emit_skip_60m": scrum_message_emit_skip_60m,
            "dev_wait_reason": dev_wait_reason,
            "passive_with_ready_streak": passive_with_ready_streak,
            "dev_claim_loop_count": dev_claim_loop_count,
            "admin_runtime_override_applied": admin_runtime_override_applied,
            "session_not_ready_fallback_count_by_role": session_not_ready_fallback_count_by_role,
            "issue_publication_gap_roles": issue_gap_roles,
            "issue_publication_gap_count": len(issue_gap_roles),
            "dev_coaching_state": dev_coaching_state,
            "dev_none_no_signal_streak_24h": dev_none_streak_24h,
            "dev_delivery_actions_24h": dev_delivery_actions_24h,
            "dev_issue_reporting_ok_rate_24h": dev_issue_ok_rate_24h,
            "queue_waiting_dep": queue_waiting_dep,
            "queue_ready": queue_ready,
            "queue_in_progress": queue_in_progress,
            "dependency_funnel_plateau": bool(
                queue_waiting_dep >= 10
                and queue_ready <= 1
                and (planner_blocker_upper == "DEPENDENCY_WAIT" or queue_in_progress <= 2)
            ),
        },
        "top_findings": findings[:6],
    }
    try:
        from apps.monitor.services.runtime_diagnostics_service import build_runtime_diagnostics

        payload = build_runtime_diagnostics(ROOT, lambda: payload)
    except Exception:
        pass
    return payload

@app.get("/api/workboard")
def workboard():
    wb = jload(orchestrator_file("parallel-workstreams.json"))
    tasks = []
    for t in wb.get("tasks", []):
        deps = t.get("deps") or t.get("depends_on") or t.get("dependencies") or []
        if not isinstance(deps, list):
            deps = [str(deps)] if deps else []
        task_id = str(t.get("id", ""))
        tasks.append(
            {
                "id": task_id,
                "state": t.get("state"),
                "role": canonical_role(t.get("assignee") or t.get("role")),
                "owner": canonical_role(t.get("assignee") or t.get("role")),
                "title": t.get("title", "")[:60],
                "updated_at": t.get("updated_at", ""),
                "deps": deps,
                "depends_on": deps,
                "stream_id": t.get("stream_id") or _batch_prefix(task_id),
                "batch_id": _batch_prefix(task_id),
            }
        )
    return {"tasks": tasks, "items": tasks}



HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FC Monitor</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600;700&family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root {
  --ink:#05080d;--surface:#090e15;--panel:#0d1520;--lift:#111d2b;--raised:#162030;
  --edge:rgba(255,255,255,.055);--edge2:rgba(255,255,255,.10);
  --ink-text:#b8cfe0;--ghost:#4a6882;--dim:#243344;
  --aqua:#00d4ff;--emerald:#00e87a;--amber:#ffb340;--coral:#ff4d6a;--lavender:#9b7fff;--sky:#40a9ff;
  --gaq:rgba(0,212,255,.12);--gem:rgba(0,232,122,.10);--cor:rgba(255,77,106,.12);
  --mono:'IBM Plex Mono',monospace;--sans:'DM Sans',sans-serif;--r:8px;--r2:12px;
}
html{background:var(--ink)}
body{font-family:var(--mono);font-size:12px;line-height:1.5;color:var(--ink-text);background:var(--ink);min-height:100vh;overflow-x:hidden}
body::before{content:'';position:fixed;inset:0;z-index:0;background-image:radial-gradient(circle,rgba(0,212,255,.04) 1px,transparent 1px);background-size:32px 32px;pointer-events:none}
body::after{content:'';position:fixed;top:0;left:0;right:0;height:200px;z-index:0;background:radial-gradient(ellipse 80% 100% at 50% 0%,rgba(0,212,255,.06) 0%,transparent 100%);pointer-events:none}
header{position:sticky;top:0;z-index:100;height:52px;background:rgba(5,8,13,.92);backdrop-filter:blur(20px) saturate(180%);border-bottom:1px solid var(--edge);display:flex;align-items:center;padding:0 20px;gap:20px}
.hd-brand{display:flex;align-items:center;gap:10px;flex-shrink:0}
.hd-orb{width:28px;height:28px;border-radius:50%;background:conic-gradient(from 0deg,var(--aqua),var(--emerald),var(--aqua));box-shadow:0 0 12px rgba(0,212,255,.4);animation:spin 8s linear infinite;flex-shrink:0}
@keyframes spin{to{transform:rotate(360deg)}}
.hd-title{font-family:var(--sans);font-weight:700;font-size:14px;color:#fff;letter-spacing:-.01em}
.hd-sub{font-family:var(--mono);font-size:10px;color:var(--ghost);letter-spacing:.08em;text-transform:uppercase}
.hd-sep{width:1px;height:24px;background:var(--edge);flex-shrink:0}
.status-capsule{display:flex;align-items:center;gap:8px;padding:5px 12px;border-radius:99px;border:1px solid;font-size:11px;font-weight:600;letter-spacing:.05em;text-transform:uppercase}
.status-capsule.ok{color:var(--emerald);border-color:rgba(0,232,122,.3);background:rgba(0,232,122,.06)}
.status-capsule.err{color:var(--coral);border-color:rgba(255,77,106,.3);background:rgba(255,77,106,.06);animation:pulse-err 1.5s ease-in-out infinite}
.status-capsule.warn{color:var(--amber);border-color:rgba(255,179,64,.3);background:rgba(255,179,64,.06)}
@keyframes pulse-err{0%,100%{box-shadow:0 0 0 0 rgba(255,77,106,.3)}50%{box-shadow:0 0 0 4px rgba(255,77,106,0)}}
.status-dot{width:6px;height:6px;border-radius:50%;background:currentColor;flex-shrink:0}
.status-dot.live{animation:blink 1.2s ease-in-out infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.hd-spacer{flex:1}
.hd-meta{display:flex;align-items:center;gap:16px;font-size:11px;color:var(--ghost)}
.hd-btn{background:var(--lift);border:1px solid var(--edge);color:var(--ink-text);padding:5px 14px;border-radius:var(--r);font-family:var(--mono);font-size:11px;cursor:pointer;transition:all .15s;display:flex;align-items:center;gap:6px}
.hd-btn:hover{border-color:var(--aqua);color:var(--aqua);background:rgba(0,212,255,.06)}
.page{position:relative;z-index:1;max-width:1480px;margin:0 auto;padding:16px 16px 48px;display:grid;grid-template-columns:280px 1fr;gap:10px}
@media(max-width:960px){.page{grid-template-columns:1fr}}
.col-left{grid-column:1;display:flex;flex-direction:column;gap:10px}
.col-right{grid-column:2;display:flex;flex-direction:column;gap:10px}
.span2{grid-column:1/-1}
.panel{background:var(--panel);border:1px solid var(--edge);border-radius:var(--r2);overflow:hidden}
.panel-head{padding:9px 14px;background:var(--lift);border-bottom:1px solid var(--edge);display:flex;align-items:center;justify-content:space-between;gap:8px}
.panel-label{font-family:var(--sans);font-size:10px;font-weight:600;letter-spacing:.10em;text-transform:uppercase;color:var(--ghost)}
.panel-body{padding:14px}
.health-hero{text-align:center;padding:20px 14px 16px}
.health-ring-wrap{position:relative;width:80px;height:80px;margin:0 auto 12px}
.health-ring{width:80px;height:80px;border-radius:50%;position:relative;display:flex;align-items:center;justify-content:center}
.health-ring.ok{background:conic-gradient(var(--emerald) 100%,var(--dim) 0);box-shadow:0 0 20px rgba(0,232,122,.25)}
.health-ring.err{background:conic-gradient(var(--coral) 100%,var(--dim) 0);box-shadow:0 0 20px rgba(255,77,106,.25)}
.health-ring.warn{background:conic-gradient(var(--amber) 100%,var(--dim) 0)}
.health-ring-inner{position:absolute;inset:6px;background:var(--panel);border-radius:50%;display:flex;align-items:center;justify-content:center;flex-direction:column}
.health-pct{font-family:var(--sans);font-weight:700;font-size:18px;line-height:1;color:#fff}
.health-pct-label{font-size:8px;color:var(--ghost);letter-spacing:.05em;margin-top:2px}
.health-status-word{font-family:var(--sans);font-weight:700;font-size:20px;letter-spacing:-.01em;margin-bottom:3px}
.health-status-word.ok{color:var(--emerald)}.health-status-word.err{color:var(--coral)}.health-status-word.warn{color:var(--amber)}
.health-ts{font-size:10px;color:var(--ghost)}
.stat4{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:0 14px 14px}
.stat-tile{background:var(--lift);border:1px solid var(--edge);border-radius:var(--r);padding:10px 12px;position:relative;overflow:hidden}
.stat-tile::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;border-radius:var(--r) var(--r) 0 0}
.stat-tile.g::before{background:var(--emerald)}.stat-tile.b::before{background:var(--aqua)}.stat-tile.y::before{background:var(--amber)}.stat-tile.v::before{background:var(--lavender)}
.stat-n{font-family:var(--sans);font-weight:700;font-size:24px;color:#fff;line-height:1;margin-bottom:3px}
.stat-n.g{color:var(--emerald)}.stat-n.b{color:var(--aqua)}.stat-n.y{color:var(--amber)}.stat-n.v{color:var(--lavender)}
.stat-lbl{font-size:10px;color:var(--ghost);text-transform:uppercase;letter-spacing:.07em}
.progress-track{height:4px;background:var(--dim);border-radius:2px;overflow:hidden;margin-bottom:10px}
.progress-fill{height:100%;border-radius:2px;background:linear-gradient(90deg,var(--emerald),var(--aqua));transition:width .8s cubic-bezier(.4,0,.2,1);box-shadow:0 0 8px rgba(0,212,255,.3)}
.queue-list{display:flex;flex-direction:column;gap:6px}
.queue-states{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px}
.state-chip{font-size:10px;border:1px solid var(--edge);border-radius:999px;padding:2px 8px;background:var(--lift);color:var(--ghost)}
.state-chip.ready{color:var(--emerald);border-color:rgba(0,232,122,.35);background:rgba(0,232,122,.08)}
.state-chip.progress{color:var(--sky);border-color:rgba(64,169,255,.35);background:rgba(64,169,255,.08)}
.state-chip.wait{color:var(--amber);border-color:rgba(255,179,64,.35);background:rgba(255,179,64,.08)}
.state-chip.done{color:#8a9bad}
.queue-sync{font-size:10px;border:1px solid var(--edge);border-radius:var(--r);padding:6px 8px;margin-top:8px;line-height:1.5}
.queue-sync.ok{color:var(--emerald);border-color:rgba(0,232,122,.35);background:rgba(0,232,122,.08)}
.queue-sync.warn{color:var(--amber);border-color:rgba(255,179,64,.35);background:rgba(255,179,64,.08)}
.queue-sync.err{color:var(--coral);border-color:rgba(255,77,106,.35);background:rgba(255,77,106,.08)}
.queue-row{display:flex;align-items:center;justify-content:space-between;padding:8px 12px;background:var(--lift);border:1px solid var(--edge);border-left:3px solid;border-radius:var(--r);transition:background .15s}
.queue-row:hover{background:var(--raised)}
.queue-row.READY{border-left-color:var(--emerald)}.queue-row.READY_PLANNER{border-left-color:var(--emerald)}.queue-row.READY_DEV{border-left-color:var(--sky)}.queue-row.WAITING_DEP{border-left-color:var(--dim)}.queue-row.CLOSED{border-left-color:var(--dim);opacity:.45}
.queue-id{font-weight:700;font-size:12px;color:var(--ink-text)}
.queue-badge{font-size:10px;letter-spacing:.05em;text-transform:uppercase;padding:2px 7px;border-radius:3px}
.queue-badge.READY{color:var(--emerald);background:rgba(0,232,122,.1)}.queue-badge.READY_PLANNER{color:var(--emerald);background:rgba(0,232,122,.1)}.queue-badge.READY_DEV{color:var(--sky);background:rgba(64,169,255,.12)}.queue-badge.WAITING_DEP{color:var(--ghost);background:rgba(255,255,255,.04)}.queue-badge.CLOSED{color:var(--dim);background:transparent}
.alert-banner{background:rgba(255,77,106,.07);border:1px solid rgba(255,77,106,.35);border-left:4px solid var(--coral);border-radius:var(--r);padding:10px 14px;display:flex;align-items:center;gap:10px;color:var(--coral);font-size:11px;animation:slideDown .2s ease}
@keyframes slideDown{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}
.agents-row{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
@media(max-width:800px){.agents-row{grid-template-columns:1fr}}
.agent-tile{background:var(--panel);border:1px solid var(--edge);border-radius:var(--r2);overflow:hidden;cursor:pointer;transition:transform .15s,box-shadow .15s,border-color .2s}
.agent-tile:hover{transform:translateY(-3px);box-shadow:0 8px 24px rgba(0,0,0,.4);border-color:var(--edge2)}
.agent-stripe{height:3px;width:100%}
.agent-stripe.GO,.agent-stripe.PASS{background:linear-gradient(90deg,var(--emerald),var(--aqua));box-shadow:0 2px 8px rgba(0,232,122,.4)}
.agent-stripe.WAIT,.agent-stripe.READY{background:linear-gradient(90deg,var(--sky),var(--aqua));box-shadow:0 2px 8px rgba(64,169,255,.3)}
.agent-stripe.BLOCKED{background:linear-gradient(90deg,var(--coral),#ff8c40);box-shadow:0 2px 8px rgba(255,77,106,.4);animation:stripe-err .8s ease-in-out infinite alternate}
@keyframes stripe-err{from{opacity:.7}to{opacity:1}}
.agent-stripe.MUTED{background:var(--dim)}
.agent-inner{padding:14px}
.agent-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
.agent-name-wrap{display:flex;align-items:center;gap:8px}
.agent-name{font-family:var(--sans);font-weight:700;font-size:15px;color:#fff}
.agent-sched{font-size:10px;color:var(--ghost)}
.vc{padding:3px 8px;border-radius:4px;font-size:10px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;border:1px solid}
.vc.GO,.vc.PASS{color:var(--emerald);border-color:rgba(0,232,122,.35);background:rgba(0,232,122,.08)}
.vc.WAIT,.vc.READY{color:var(--sky);border-color:rgba(64,169,255,.35);background:rgba(64,169,255,.08)}
.vc.BLOCKED{color:var(--coral);border-color:rgba(255,77,106,.4);background:rgba(255,77,106,.10)}
.vc.MUTED{color:var(--ghost);border-color:var(--edge);background:transparent}
.agent-delta{font-size:11px;color:var(--ghost);background:var(--lift);border:1px solid var(--edge);border-radius:var(--r);padding:7px 10px;margin-bottom:8px;line-height:1.5;min-height:34px;word-break:break-word}
.agent-action-required{background:rgba(255,179,64,.12);border:1px solid rgba(255,179,64,.35);border-radius:var(--r);padding:5px 10px;color:var(--amber);font-size:10px;margin-bottom:8px;font-weight:700;letter-spacing:.05em;text-transform:uppercase}
.agent-action-required.msg-done{background:rgba(0,232,122,.10);border-color:rgba(0,232,122,.35);color:var(--emerald)}
.agent-action-required.msg-deferred{background:rgba(0,212,255,.10);border-color:rgba(0,212,255,.35);color:var(--aqua)}
.agent-action-required.msg-blocked{background:rgba(255,77,106,.10);border-color:rgba(255,77,106,.35);color:var(--coral)}
.agent-blocker{background:rgba(255,77,106,.07);border:1px solid rgba(255,77,106,.3);border-radius:var(--r);padding:5px 10px;color:var(--coral);font-size:10px;margin-bottom:8px;display:flex;align-items:center;gap:6px}
.agent-blocker.soft{background:rgba(255,179,64,.10);border-color:rgba(255,179,64,.35);color:var(--amber)}
.agent-next{font-size:10px;color:var(--ink-text);opacity:.7;line-height:1.55;margin-bottom:10px;min-height:28px}
.spark{display:flex;align-items:flex-end;gap:2px;height:22px;margin-bottom:8px}
.spark-bar{flex:1;border-radius:2px 2px 0 0;transition:height .3s ease}
.spark-bar.ok{background:var(--emerald);opacity:.65}.spark-bar.err{background:var(--coral);opacity:.9}.spark-bar.skip{background:var(--amber);opacity:.75}.spark-bar.empty{background:var(--dim);opacity:.3;height:4px!important}
.agent-footer{display:flex;align-items:center;justify-content:space-between;padding-top:8px;border-top:1px solid var(--edge)}
.next-lbl{font-size:10px;color:var(--ghost)}.next-time{font-size:10px;font-weight:700;color:var(--aqua)}
.age-chip{font-size:9px;padding:2px 7px;border-radius:3px;background:var(--lift);border:1px solid var(--edge);color:var(--ghost)}
.task-grid{display:flex;flex-wrap:wrap;gap:6px}
.task-chip{display:inline-flex;align-items:center;gap:7px;padding:5px 12px;border-radius:var(--r);font-size:11px;border:1px solid;transition:all .14s}
.task-chip:hover{transform:translateY(-1px)}
.task-chip.READY{border-color:rgba(0,232,122,.35);background:rgba(0,232,122,.07);color:var(--emerald)}.task-chip.READY_DEV{border-color:rgba(64,169,255,.35);background:rgba(64,169,255,.08);color:var(--sky)}
.task-chip.IN_PROGRESS{border-color:rgba(0,212,255,.4);background:rgba(0,212,255,.07);color:var(--aqua)}
.task-chip-role{opacity:.55;font-size:10px}
.tab-bar{display:flex;gap:5px;margin-bottom:10px}
.t-tab{padding:4px 13px;border-radius:var(--r);border:1px solid var(--edge);background:transparent;color:var(--ghost);font-family:var(--mono);font-size:11px;cursor:pointer;transition:all .12s}
.t-tab:hover{border-color:var(--edge2);color:var(--ink-text)}
.t-tab.on{background:var(--aqua);color:var(--ink);border-color:var(--aqua);font-weight:700}
.t-tab.on-v{background:var(--lavender);color:#fff;border-color:var(--lavender);font-weight:700}
.tick-scroll{max-height:240px;overflow-y:auto}
.tick-scroll::-webkit-scrollbar{width:3px}
.tick-scroll::-webkit-scrollbar-thumb{background:var(--dim);border-radius:2px}
.t-row{display:grid;grid-template-columns:140px 68px 60px 46px;gap:6px;align-items:center;padding:5px 8px;border-radius:4px;font-size:11px;border-bottom:1px solid rgba(255,255,255,.03);transition:background .1s}
.t-row:hover{background:var(--lift)}.t-row:last-child{border:none}
.t-ts{color:var(--ghost);font-size:10px}
.t-type{font-size:10px;letter-spacing:.05em}
.t-type.END{color:var(--ghost)}.t-type.SKIP{color:var(--amber)}.t-type.BACKOFF{color:var(--coral);font-weight:600}
.t-rc.ok{color:var(--emerald)}.t-rc.err{color:var(--coral)}.t-rc.skip{color:var(--amber)}
.contract-block{background:var(--ink);border:1px solid var(--edge);border-radius:var(--r);padding:14px;font-size:11px;line-height:1.9;max-height:220px;overflow-y:auto}
.contract-block::-webkit-scrollbar{width:3px}.contract-block::-webkit-scrollbar-thumb{background:var(--dim)}
.c-key{color:var(--aqua);font-weight:600}.c-ok{color:var(--emerald)}.c-err{color:var(--coral);font-weight:700}.c-muted{color:var(--ghost)}.c-warn{color:var(--amber);font-weight:700}
.link-row{display:flex;gap:14px;padding-top:10px;flex-wrap:wrap}
.ext-link{font-size:10px;color:var(--ghost);text-decoration:none;display:flex;align-items:center;gap:4px;transition:color .12s}
.ext-link:hover{color:var(--aqua)}
.planner-action-chip{display:inline-flex;align-items:center;gap:6px;padding:2px 8px;border-radius:999px;border:1px solid rgba(255,179,64,.35);background:rgba(255,179,64,.12);color:var(--amber);font-weight:700;letter-spacing:.05em;text-transform:uppercase}
.exec-meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:6px;margin-bottom:10px}
.exec-pill{background:var(--lift);border:1px solid var(--edge);border-radius:var(--r);padding:7px 9px;min-height:42px}
.exec-pill-label{font-size:9px;color:var(--ghost);text-transform:uppercase;letter-spacing:.07em;margin-bottom:2px}
.exec-pill-value{font-size:10px;color:var(--ink-text);word-break:break-word}
.exec-pill-value.ok{color:var(--emerald)}.exec-pill-value.err{color:var(--coral)}.exec-pill-value.skip{color:var(--amber)}
.activity-chip{display:inline-flex;align-items:center;gap:6px;padding:2px 8px;border-radius:999px;border:1px solid;font-size:10px;font-weight:700;letter-spacing:.06em}
.activity-chip.PRODUCTIVE{color:var(--emerald);border-color:rgba(0,232,122,.35);background:rgba(0,232,122,.08)}
.activity-chip.IDLE{color:var(--amber);border-color:rgba(255,179,64,.35);background:rgba(255,179,64,.08)}
.activity-chip.CHECK{color:var(--coral);border-color:rgba(255,77,106,.35);background:rgba(255,77,106,.08)}
.exec-logs{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.log-box{background:var(--ink);border:1px solid var(--edge);border-radius:var(--r);overflow:hidden}
.log-head{padding:7px 9px;background:var(--lift);border-bottom:1px solid var(--edge);font-size:10px;color:var(--ghost);text-transform:uppercase;letter-spacing:.07em}
.log-scroll{max-height:220px;overflow:auto;padding:9px}
.log-scroll::-webkit-scrollbar{width:3px}.log-scroll::-webkit-scrollbar-thumb{background:var(--dim)}
.log-line{font-size:10px;line-height:1.45;color:var(--ink-text);font-family:var(--mono);white-space:pre-wrap;word-break:break-word;border-bottom:1px solid rgba(255,255,255,.03);padding:2px 0}
.log-line.err{color:var(--coral);background:rgba(255,77,106,.08);border-left:2px solid rgba(255,77,106,.65);padding-left:6px}
.log-line.warn{color:var(--amber);background:rgba(255,179,64,.07);border-left:2px solid rgba(255,179,64,.55);padding-left:6px}
.log-line.ok{color:var(--emerald)}
.log-line.action{color:var(--aqua);background:rgba(0,212,255,.06);border-left:2px solid rgba(0,212,255,.5);padding-left:6px}
.log-line.contract{color:var(--lavender);background:rgba(155,127,255,.08);border-left:2px solid rgba(155,127,255,.55);padding-left:6px}
.log-line.meta{color:var(--ghost)}
.log-line:last-child{border-bottom:none}
.log-empty{font-size:10px;color:var(--ghost)}
.t-tab.on-g{background:var(--emerald);color:var(--ink);border-color:var(--emerald);font-weight:700}
.sev-row{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0 10px}
.sev-chip{font-size:10px;border:1px solid var(--edge);border-radius:999px;padding:2px 8px;background:var(--lift);color:var(--ghost)}
.sev-chip.err{color:var(--coral);border-color:rgba(255,77,106,.35);background:rgba(255,77,106,.08)}
.sev-chip.warn{color:var(--amber);border-color:rgba(255,179,64,.35);background:rgba(255,179,64,.08)}
.sev-chip.action{color:var(--aqua);border-color:rgba(0,212,255,.35);background:rgba(0,212,255,.08)}
.sev-chip.contract{color:var(--lavender);border-color:rgba(155,127,255,.35);background:rgba(155,127,255,.08)}
.insight-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.insight-tile{background:var(--lift);border:1px solid var(--edge);border-radius:var(--r);padding:10px}
.insight-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}
.insight-role{font-family:var(--sans);font-weight:700;color:#fff;font-size:13px}
.insight-score{font-size:11px;font-weight:700;padding:2px 8px;border-radius:999px;border:1px solid}
.insight-score.STRONG{color:var(--emerald);border-color:rgba(0,232,122,.35);background:rgba(0,232,122,.08)}
.insight-score.MEDIUM{color:var(--amber);border-color:rgba(255,179,64,.35);background:rgba(255,179,64,.08)}
.insight-score.WEAK{color:var(--coral);border-color:rgba(255,77,106,.35);background:rgba(255,77,106,.08)}
.insight-meta{font-size:10px;color:var(--ghost);margin-bottom:6px}
.insight-line{font-size:10px;color:var(--ink-text);line-height:1.5;margin-bottom:4px}
.dev-state-badge{display:inline-flex;align-items:center;gap:6px;padding:2px 8px;border-radius:999px;border:1px solid;font-size:10px;font-weight:700;letter-spacing:.05em;text-transform:uppercase}
.dev-state-badge.STALLED{color:var(--coral);border-color:rgba(255,77,106,.38);background:rgba(255,77,106,.10)}
.dev-state-badge.RECOVERING{color:var(--amber);border-color:rgba(255,179,64,.38);background:rgba(255,179,64,.10)}
.dev-state-badge.DELIVERING{color:var(--emerald);border-color:rgba(0,232,122,.35);background:rgba(0,232,122,.10)}
.insight-issues{font-size:10px;color:var(--coral);line-height:1.45}
.insight-events{font-size:10px;color:var(--ghost);line-height:1.45;margin-top:6px;max-height:80px;overflow:auto}
.diag-list{display:flex;flex-direction:column;gap:7px}
.diag-item{background:var(--lift);border:1px solid var(--edge);border-radius:var(--r);padding:8px 10px}
.diag-item.critical{border-left:3px solid var(--coral);background:rgba(255,77,106,.08)}
.diag-item.high{border-left:3px solid var(--amber);background:rgba(255,179,64,.08)}
.diag-item.ok{border-left:3px solid var(--emerald);background:rgba(0,232,122,.08)}
.diag-title{font-family:var(--sans);font-size:12px;font-weight:700;color:#fff}
.diag-meta{font-size:10px;color:var(--ghost);margin-top:2px}
.diag-sample{font-size:10px;color:var(--ink-text);line-height:1.45;margin-top:4px;max-height:38px;overflow:auto}
.iter-issues{display:flex;flex-direction:column;gap:7px;max-height:260px;overflow:auto;padding-right:2px}
.issue-row{background:var(--lift);border:1px solid var(--edge);border-radius:var(--r);padding:8px 10px}
.issue-row.critical{border-left:3px solid var(--coral);background:rgba(255,77,106,.10)}
.issue-row.error{border-left:3px solid var(--coral);background:rgba(255,77,106,.08)}
.issue-row.warn{border-left:3px solid var(--amber);background:rgba(255,179,64,.08)}
.issue-row.info{border-left:3px solid var(--ghost);background:rgba(125,150,170,.06)}
.issue-head{display:flex;align-items:center;justify-content:space-between;gap:10px}
.issue-role{font-family:var(--sans);font-size:12px;font-weight:700;color:#fff}
.issue-sev{font-size:10px;padding:2px 8px;border-radius:999px;border:1px solid var(--edge2);text-transform:uppercase}
.issue-sev.critical,.issue-sev.error{color:var(--coral);border-color:rgba(255,77,106,.4)}
.issue-sev.warn{color:var(--amber);border-color:rgba(255,179,64,.4)}
.issue-sev.info{color:var(--ghost)}
.issue-meta{font-size:10px;color:var(--ghost);margin-top:3px}
.issue-text{font-size:10px;color:var(--ink-text);line-height:1.45;margin-top:4px;word-break:break-word}
.issue-role-group{border:1px solid var(--edge);border-radius:var(--r);padding:8px;background:rgba(8,21,35,.55)}
.issue-role-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;font-size:11px;color:#fff;font-family:var(--sans);font-weight:700}
.agent-issue-chip{margin-top:6px;font-size:10px;line-height:1.35;padding:4px 7px;border-radius:8px;border:1px solid var(--edge2);background:rgba(125,150,170,.08);color:var(--ghost)}
.agent-issue-chip.warn{border-color:rgba(255,179,64,.45);background:rgba(255,179,64,.12);color:var(--amber)}
.agent-issue-chip.error,.agent-issue-chip.critical{border-color:rgba(255,77,106,.45);background:rgba(255,77,106,.12);color:var(--coral)}
.agent-issue-chip.info{border-color:var(--edge2);background:rgba(125,150,170,.08);color:var(--ghost)}
.insight-issue-report{font-size:10px;line-height:1.45;margin-top:4px}
.insight-issue-report.bad{color:var(--coral)}
.insight-issue-report.good{color:var(--emerald)}
@media(max-width:1000px){.insight-grid{grid-template-columns:1fr}}
@media(max-width:1280px){.exec-logs{grid-template-columns:1fr 1fr}}
@media(max-width:980px){.exec-logs{grid-template-columns:1fr}}
.spin-sm{display:inline-block;width:10px;height:10px;border:2px solid rgba(255,255,255,.1);border-top-color:var(--aqua);border-radius:50%;animation:sp .5s linear infinite;vertical-align:middle}
@keyframes sp{to{transform:rotate(360deg)}}
.fade{animation:fadeUp .25s ease}
@keyframes fadeUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
</style>
</head>
<body>
<header>
  <div class="hd-brand">
    <div class="hd-orb"></div>
    <div><div class="hd-title">FC Ops Monitor</div><div class="hd-sub">Finance Copilot · Orchestration</div></div>
  </div>
  <div class="hd-sep"></div>
  <div class="status-capsule err" id="health-capsule">
    <span class="status-dot live"></span><span id="health-txt">—</span>
  </div>
  <div class="hd-spacer"></div>
  <div class="hd-meta">
    <span id="hd-ts">—</span>
    <button class="hd-btn" onclick="doRefresh()"><span id="ri">⟳</span> Refresh</button>
    <a class="hd-btn" href="/planner-debug" target="_blank">Planner Debug</a>
    <span id="cd" style="min-width:60px;text-align:right">auto 12s</span>
  </div>
</header>
<div class="page" id="page">
  <div class="span2" style="display:flex;align-items:center;justify-content:center;height:60vh;color:var(--ghost);flex-direction:column;gap:12px">
    <span class="spin-sm" style="width:20px;height:20px;border-width:3px"></span>
    <span style="font-family:DM Sans,sans-serif;font-size:13px">Chargement…</span>
  </div>
</div>
<script>
let D=null,T=null,E=null,L=null,LC=null,I=null,X=null,F=null,R=null,IS=null,G=null,P=null,A=null,TA=null,DM=null,API_ERRORS=[],cdr=12,iv=null,tickRole='planner',contractRole='planner',execRole='planner',logRole='planner',logKind='runner';
async function fetchJson(url, fallback={}, timeoutMs=6000){
  const ctrl=new AbortController();
  const tid=setTimeout(()=>ctrl.abort(), timeoutMs);
  try{
    const r=await fetch(url,{cache:'no-store',signal:ctrl.signal});
    if(!r.ok)return {ok:false,data:fallback,error:`http_${r.status}`,url};
    return {ok:true,data:await r.json(),error:'',url};
  }catch(err){
    const kind=(err&&err.name==='AbortError')?'timeout':'network';
    return {ok:false,data:fallback,error:kind,url};
  }finally{
    clearTimeout(tid);
  }
}
async function load(){
  const[s,t,e,l,lc,i,x,f,r,is,p,g,a,ta,dm]=await Promise.all([
    fetchJson('/api/status',{}),
    fetchJson('/api/ticks/all?n=20',{}),
    fetchJson('/api/execution/all?tick_n=40&runner_n=90',{}),
    fetchJson(`/api/log-view?role=${encodeURIComponent(logRole)}&kind=${encodeURIComponent(logKind)}&n=220`,{}),
    fetchJson('/api/log-catalog',{}),
    fetchJson('/api/agent-insights',{}),
    fetchJson('/api/execution-insights/all',{}),
    fetchJson('/api/error-feed?n=140',{}),
    fetchJson('/api/issues/feed?n=160&window_min=240',{}),
    fetchJson('/api/issues/summary?window_min=60',{}),
    fetchJson('/api/dev-parent',{}),
    fetchJson('/api/runtime-diagnostics',{}),
    fetchJson('/api/agent-activity?window=6&limit=300',{}),
    fetchJson('/api/tasks/active?window=6&limit=120',{}),
    fetchJson('/api/dependencies/map?limit=300',{})
  ]);
  API_ERRORS=[s,t,e,l,lc,i,x,f,r,is,p,g,a,ta,dm].filter(r=>!r.ok).map(r=>`${r.url}:${r.error}`);

  const statusOk = !!(s.ok && s.data && s.data.queue && s.data.workboard && s.data.agents);
  if(statusOk){
    D=s.data;
    D.__status_unavailable=false;
  }else if(!D){
    D={health:'UNKNOWN',queue:null,workboard:null,agents:{},rate_limits:[],kpi:{},runtime_freshness:{seconds:-1,state:'stale'},sources:{},doctor:{status:'unknown',meta:{}},planner_evidence_quality_score:0,queue_workboard_integrity:{status:'unknown',mismatch_count:0,oldest_mismatch_age_s:-1,queue_only:[],workboard_only:[],state_mismatch:[]},po_scrum_master:{name:'po_scrum_master',mode:'scheduled_advisory',active:false,last_run:'',last_run_age_min:-1,last_report_age_min:-1,lock_skip_streak:0,last_messages_posted:0},agent_messages:{open:0,open_count:0,delivered:0,delivered_count:0,actioned:0,actioned_count:0,closed:0,closed_count:0,delivered_recent:0,actioned_recent:0,closed_recent:0,expired:0,expired_count:0,posted:0,posted_count:0,pending_by_role:{},open_by_role:{},last_message_id_by_role:{},latest_action_status_by_role:{}},__status_unavailable:true};
  }else{
    D.__status_unavailable=true;
  }
  if(t.ok)T=t.data;
  if(e.ok)E=e.data;
  if(l.ok)L=l.data;
  if(lc.ok)LC=lc.data;
  if(i.ok)I=i.data;
  if(x.ok)X=x.data;
  if(f.ok)F=f.data;
  if(r.ok)R=r.data;
  if(is.ok)IS=is.data;
  P=p.ok ? p.data : {};
  if(g.ok)G=g.data;
  A=a.ok ? a.data : {};
  TA=ta.ok ? ta.data : {};
  DM=dm.ok ? dm.data : {};
}
function esc(v){return String(v||'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;')}
function shortPath(v, max=92){
  const s=String(v||'');
  if(!s)return'—';
  if(s.length<=max)return s;
  return `…${s.slice(-(max-1))}`;
}
function classifyLineClient(line){
  const t=String(line||'');
  const u=t.toUpperCase();
  if(/ASK QUESTIONS, EDIT FILES, OR RUN COMMANDS\.|BE SPECIFIC FOR THE BEST RESULTS\.|\/HELP FOR MORE INFORMATION\.|INSTALLED VIA HOMEBREW|USING:\s*1 QWEN\.MD FILE/.test(u))return'meta';
  if(/^\(ESC TO CANCEL/.test(u))return'meta';
  if(/CODER-MODEL|SANDBOX \(|NO SANDBOX/.test(u))return'meta';
  if(/[⠁-⣿]/.test(t))return'meta';
  if(/\brc=(1|2|124|13|22|43)\b/.test(t))return'err';
  if(/TRACEBACK|EXCEPTION|ERROR:|MODULE NOT FOUND|SYNTAX ERROR|UNEXPECTED EOF/.test(u))return'err';
  if(/\[BLOCKED\]|VERDICT:\s*BLOCKED|STATUS:\s*BLOCKED/.test(u))return'err';
  const blockerMatch=u.match(/BLOCKER_ID:\s*([A-Z0-9_\-?]+)/);
  if(blockerMatch&&blockerMatch[1]&&!['NONE','NO_BLOCKER','?'].includes(blockerMatch[1]))return'err';
  if(/\[BACKOFF\]|RATE_LIMIT|\[SKIP\]|GO_WITH_CAUTION|WARN|WARNING/.test(u))return'warn';
  if(/\[ACTION\]/.test(u))return'action';
  if(/\[CONTRACT\]/.test(u))return'contract';
  if(/VERDICT:\s*(PASS|GO)|STATUS:\s*(COMPLETE|OK)|TEST_RESULT=PASS/.test(u))return'ok';
  if(/\[(START|END|TICK|MODEL|CONFIG|MODEL_EFFECTIVE)\]|PRIMARY_PROMPT_(BEGIN|END)|FINAL_OUTPUT/.test(u))return'meta';
  return'normal';
}
function isRateLimited(v,s,b,d){
  const V=(v||'').toUpperCase(),S=(s||'').toUpperCase(),B=(b||'NONE').toUpperCase(),D=(d||'').toUpperCase();
  return B.startsWith('AGENT_RATE_LIMIT_')||S==='RATE_LIMIT_SKIP'||S==='RATE_LIMIT_BACKOFF'||D==='RATE_LIMIT_BACKOFF'||(V==='WAIT'&&S==='RATE_LIMIT_SKIP');
}
function isSoftPlannerSignal(role,agent,blocker,delta){
  if(role!=='planner')return false;
  if(agent&&agent.soft_blocker)return true;
  const req=String((agent&&agent.planner_action_required)||'').toLowerCase();
  if(['claim_ready','create_or_claim','dependency_regroup','runtime_recovery'].includes(req))return true;
  const b=String(blocker||'').toUpperCase();
  const d=String(delta||'').toUpperCase();
  if(['HANDOFF_TO_MISSING','PLANNER_BATCH_ID_INVALID','MODE_ANALYSE_NO_EDITS','CONTRACT_GUARD_BLOCK'].includes(b))return true;
  if(['READY_ITEM_AVAILABLE_RUNTIME_CONTEXT','PLANNER_PROGRESS_REQUIRED','DEPENDENCY_POLICY_ENFORCEMENT_REQUIRED'].includes(d))return true;
  return false;
}
function _canonicalMonitorRole(role){
  return role==='po_scrum_master' ? 'scrum_master' : role;
}
function _agentForRole(role){
  const agents=(D&&D.agents)||{};
  if(role==='scrum_master') return agents.scrum_master||agents.po_scrum_master||{};
  return agents[role]||{};
}
function monitorRoles(){
  const po=(D&&D.po_scrum_master)||{};
  const poHasSignal = !!(po.active || (Number.isFinite(po.last_run_age_min) && po.last_run_age_min >= 0) || po.last_run);
  const advisoryRoles = [];
  const scrumCatalog = LC&&LC.catalog&&LC.catalog.scrum_master;
  const scrumHasLogs = !!(scrumCatalog && Object.values(scrumCatalog).some(v=>v&&v.exists));
  if(poHasSignal || scrumHasLogs) advisoryRoles.push('scrum_master');
  const entriesRaw=Object.entries((D&&D.agents)||{}).filter(([r])=>!!r);
  const entries=entriesRaw.map(([r,a])=>[_canonicalMonitorRole(r),a]);
  const fromStatus=entries
    .filter(([,a])=>{
      const delta=String((a&&a.delta)||'').toUpperCase();
      const blocker=String((a&&a.blocker)||'').toUpperCase();
      const age=(a&&a.tick_age_min);
      const hasRecentTickAge = Number.isFinite(age) && age >= 0 && age <= 240;
      const hasDelta = delta && delta !== '?' && delta !== 'NO_DELTA';
      const hasBlocker = blocker && blocker !== 'NONE' && blocker !== '?';
      return hasRecentTickAge || hasDelta || hasBlocker;
    })
    .map(([r])=>r);
  if(fromStatus.length){
    const preferred=['planner','dev','admin'];
    const forceCore = preferred.filter(r=>entries.some(([name])=>name===r));
    const ordered=[
      ...forceCore.filter(r=>fromStatus.includes(r)),
      ...forceCore.filter(r=>!fromStatus.includes(r)),
      ...fromStatus.filter(r=>!preferred.includes(r)),
      ...advisoryRoles.filter(r=>!fromStatus.includes(r)),
    ];
    return [...new Set(ordered)];
  }
  const fallback=['planner','dev','admin'];
  if(advisoryRoles.length) fallback.push(...advisoryRoles.filter(r=>!fallback.includes(r)));
  return [...new Set(fallback)];
}
function ensureRole(selected, roles){
  if(roles.includes(selected))return selected;
  if(roles.includes('planner'))return 'planner';
  return roles[0]||'planner';
}
function vc(v,s,b,d,role,agent){
  const V=(v||'').toUpperCase(),B=(b||'NONE').toUpperCase();
  if(isRateLimited(v,s,b,d))return'WAIT';
  if(B!=='NONE'&&B)return isSoftPlannerSignal(role,agent,b,d)?'WAIT':'BLOCKED';
  if(V==='GO'||V==='PASS')return V;
  if(V==='WAIT'||(s||'').toUpperCase()==='WAIT')return'WAIT';
  if(V==='BLOCKED')return'BLOCKED';
  if(V==='READY')return'READY';
  return'MUTED';
}
function vcIcon(v){return{GO:'✦',PASS:'✦',WAIT:'◎',READY:'◎',BLOCKED:'⚠',MUTED:'·'}[v]||'·'}
function sparkHtml(role){
  const list=(T&&T[role])||[];
  const items=[...list].reverse().slice(0,16);
  while(items.length<16)items.unshift(null);
  return items.map(t=>{
    if(!t)return'<div class="spark-bar empty"></div>';
    const cls=t.rc===0?'ok':(t.type!=='END'?'skip':'err');
    const h=t.rc===0?18:(t.type==='BACKOFF'?12:9);
    return`<div class="spark-bar ${cls}" style="height:${h}px"></div>`;
  }).join('');
}
function tickRowsHtml(role){
  const list=(T&&T[role])||[];
  if(!list.length)return'<div style="color:var(--ghost);padding:10px;font-size:11px">Aucun tick</div>';
  return list.map(t=>{
    const ok=t.rc===0,sk=t.type!=='END';
    const rcc=ok?'ok':sk?'skip':'err';
    const icon=ok?'✔':(t.type==='BACKOFF'?'↺':'✘');
    return`<div class="t-row"><span class="t-ts">${t.ts}</span><span class="t-type ${t.type}">${t.type}</span><span style="color:var(--ghost)">${t.agent}</span><span class="t-rc ${rcc}">${icon}</span></div>`;
  }).join('');
}
function contractBodyHtml(role){
  const a=_agentForRole(role);
  const xi=(X&&X[role])||{};
  const cs=xi.contract_status||{};
  const verdict=a.verdict||cs.verdict||'MUTED';
  const statusVal=a.status||cs.status||'';
  const blocker=a.blocker||cs.blocker_id||'NONE';
  const delta=a.delta||cs.delta||'';
  const nextVal=a.next||cs.next||'';
  const rl=isRateLimited(verdict,statusVal,blocker,delta);
  const softPlannerAction = isSoftPlannerSignal(role,a,blocker,delta);
  const v=vc(verdict,statusVal,blocker,delta,role,a);
  return[
    ['VERDICT',verdict,v==='GO'||v==='PASS'?'c-ok':v==='BLOCKED'?'c-err':'c-muted'],
    ['STATUS',statusVal,v==='BLOCKED'?'c-err':'c-muted'],
    ['BLOCKER',rl?'NONE':blocker,(!rl&&blocker&&blocker!=='NONE')?(softPlannerAction?'c-warn':'c-err'):'c-muted'],
    ['ACTION_REQUIRED',(role==='planner'&&String(a.planner_action_required||'').toLowerCase()&&String(a.planner_action_required||'').toLowerCase()!=='none')?String(a.planner_action_required||'').toLowerCase():'none',(role==='planner'&&String(a.planner_action_required||'').toLowerCase()&&String(a.planner_action_required||'').toLowerCase()!=='none')?'c-warn':'c-muted'],
    ['DELTA',delta,'c-muted'],
    ['NEXT',(nextVal||'').slice(0,160),'c-muted'],
  ].map(([k,val,cls])=>`<div><span class="c-key">${k}:</span>&nbsp;<span class="${cls}">${val||'?'}</span></div>`).join('');
}
function latestExec(role){
  return (E&&E[role])||{tick_tail:[],runner_tail:[],events_tail:[],last_ts:'',last_rc:null,last_agent:'',last_start:'',last_end:''};
}
function isNoiseLine(line){
  const t=String(line||'').trim();
  if(!t)return true;
  const u=t.toUpperCase();
  if(/ASK QUESTIONS, EDIT FILES, OR RUN COMMANDS\.|BE SPECIFIC FOR THE BEST RESULTS\.|\/HELP FOR MORE INFORMATION\.|INSTALLED VIA HOMEBREW|USING:\s*1 QWEN\.MD FILE/.test(u))return true;
  if(/^\(ESC TO CANCEL/.test(u))return true;
  if(/CODER-MODEL|SANDBOX \(|NO SANDBOX/.test(u))return true;
  if(/[⠁-⣿]/.test(t))return true;
  if(t.startsWith('...~//analyse-financiere'))return true;
  return false;
}
function logLinesHtml(lines, entries=null){
  const rendered=[];
  if(entries && entries.length){
    const sevMap={error:'err',warn:'warn',action:'action',contract:'contract',ok:'ok',meta:'meta',normal:'normal'};
    for(const e of entries){
      const ln=String(e.line||'');
      const cls = sevMap[String(e.severity||'').toLowerCase()] || classifyLineClient(ln);
      if(isNoiseLine(ln) && !['err','warn','action','contract'].includes(cls))continue;
      rendered.push(`<div class="log-line ${cls}">${esc(ln)}</div>`);
    }
  }else{
    if(!lines||!lines.length)return '<div class="log-empty">Aucune ligne récente</div>';
    for(const l of lines){
      const cls=classifyLineClient(l);
      if(isNoiseLine(l) && !['err','warn','action','contract'].includes(cls))continue;
      rendered.push(`<div class="log-line ${cls}">${esc(l)}</div>`);
    }
  }
  if(!rendered.length)return '<div class="log-empty">Aucune ligne utile (bruit UI filtré)</div>';
  return rendered.join('');
}
function execMetaHtml(role){
  const x=latestExec(role);
  const xi=(X&&X[role])||{};
  const sev=xi.severity_counts||{};
  const ev=xi.event_counts||{};
  const activity=xi.activity||'CHECK';
  const quality=xi.quality||'WEAK';
  const taskUpdate=xi.task_update||'unknown';
  const rc=x.last_rc;
  const rcTxt=rc==null?'?':String(rc);
  const rcCls=rc==null?'':(rc===0?'ok':'err');
  return `
    <div class="exec-pill"><div class="exec-pill-label">Dernier timestamp</div><div class="exec-pill-value">${esc(x.last_ts||'—')}</div></div>
    <div class="exec-pill"><div class="exec-pill-label">Retour / agent</div><div class="exec-pill-value ${rcCls}">rc=${esc(rcTxt)} · ${esc(x.last_agent||'?')}</div></div>
    <div class="exec-pill"><div class="exec-pill-label">Dernier marqueur</div><div class="exec-pill-value">${esc(x.last_end||x.last_start||'—')}</div></div>
    <div class="exec-pill"><div class="exec-pill-label">Activité / qualité</div><div class="exec-pill-value"><span class="activity-chip ${esc(activity)}">${esc(activity)}</span> · ${esc(quality)} · ${esc(taskUpdate)}</div></div>
    <div class="exec-pill"><div class="exec-pill-label">Errors · Warn · Actions</div><div class="exec-pill-value">E:${sev.error||0} · W:${sev.warn||0} · A:${sev.action||0} · Events:${(ev.action||0)+(ev.warn||0)+(ev.error||0)}</div></div>
  `;
}
function logCatalogFor(role, kind){
  const c=LC&&LC.catalog&&LC.catalog[role]&&LC.catalog[role][kind];
  return c||null;
}
function logRoleTabsHtml(){
  const roles=monitorRoles();
  return roles.map(r=>`<button class="t-tab${r===logRole?' on':''}" onclick="setLogRole('${r}')">${r}</button>`).join('');
}
function logKindTabsHtml(){
  const kinds=['tick','cron','runner','events','contract'];
  return kinds.map(k=>{
    const c=logCatalogFor(logRole,k);
    const on=k===logKind?' on-g':'';
    const badge = c && c.exists ? '●' : '○';
    return `<button class="t-tab${on}" onclick="setLogKind('${k}')">${badge} ${k}</button>`;
  }).join('');
}
function logViewerHtml(){
  const lines=(L&&L.lines)||[];
  const entries=(L&&L.entries)||[];
  const counts=(L&&L.severity_counts)||{};
  const meta=logCatalogFor(logRole,logKind);
  const path = (L&&L.path) || (meta&&meta.path) || '—';
  const exists = (L&&typeof L.exists==='boolean') ? L.exists : !!(meta&&meta.exists);
  const sev = `
    <div class="sev-row">
      <span class="sev-chip err">error ${counts.error||0}</span>
      <span class="sev-chip warn">warn ${counts.warn||0}</span>
      <span class="sev-chip action">action ${counts.action||0}</span>
      <span class="sev-chip contract">contract ${counts.contract||0}</span>
      <span class="sev-chip">ok ${counts.ok||0}</span>
      <span class="sev-chip">meta ${counts.meta||0}</span>
    </div>`;
  return `
    <div class="tab-bar" id="log-role-tabs">${logRoleTabsHtml()}</div>
    <div class="tab-bar" id="log-kind-tabs">${logKindTabsHtml()}</div>
    ${sev}
    <div class="log-box">
      <div class="log-head">log-view · ${esc(logRole)} · ${esc(logKind)} · ${exists?'available':'missing'}</div>
      <div class="log-scroll">${logLinesHtml(lines,entries)}</div>
    </div>
    <div class="link-row">
      <a class="ext-link" href="/api/log-view?role=${encodeURIComponent(logRole)}&kind=${encodeURIComponent(logKind)}&n=220" target="_blank">⬡ Log JSON</a>
      <a class="ext-link" href="/api/log-catalog" target="_blank">⬡ Catalog</a>
      <span class="ext-link" style="pointer-events:none;opacity:.75">📄 ${esc(path)}</span>
    </div>
  `;
}
function insightsHtml(){
  const agents=(I&&I.agents)||{};
  const exi=(X||{});
  const parent=P||{};
  const roles=monitorRoles();
  return `<div class="insight-grid">${
    roles.map(r=>{
      const a=agents[r]||{};
      const x=exi[r]||{};
      const score=(x.quality_score==null?(a.quality_score==null?'?':a.quality_score):x.quality_score);
      const q=(x.quality||a.quality||'WEAK');
      const e=a.evidence||{};
      const issues=(x.issues&&x.issues.length?x.issues:(a.issues||[]));
      const issueCount=Number(a.issue_count||0);
      const issueSeverity=String(a.issue_severity||'none').toLowerCase();
      const issueCodes=String(a.reported_issues||'none');
      const issueReportOk=!!a.issue_reporting_ok;
      const issueReportErrors=(a.issue_reporting_errors||[]);
      const interesting=(x.interesting_events||[]).slice(-3).map(ev=>`[${ev.ts||''}] ${ev.event||''} ${ev.detail||''}`).join('\n');
      const evc=x.event_counts||{};
      const svc=x.severity_counts||{};
      const activity=x.activity||'CHECK';
      const taskUpdate=x.task_update||a.task_update||'?';
      const isDev=r==='dev';
      const devAuto=(a.dev_autonomy||{});
      const parentState=String((devAuto.coaching_state||a.coaching_state||parent.coaching_state||'RECOVERING')).toUpperCase();
      const parentLine=isDev&&((parent&&Object.keys(parent).length)||Object.keys(devAuto).length)
        ? `<div class="insight-line"><strong>dev_parent:</strong> <span class="dev-state-badge ${esc(parentState)}">${esc(parentState)}</span> · quality=${esc(parent.quality||'?')} ${esc(parent.quality_score||'?')} · channels_missing_24h=${esc(devAuto.channels_missing_streak_24h??a.channels_missing_streak_24h??parent.channels_missing_streak_24h??0)} · none_signal_24h=${esc(devAuto.none_no_signal_streak_24h??a.none_signal_streak_24h??parent.none_signal_streak_24h??0)} · guard_blocks_24h=${esc(devAuto.contract_guard_block_count_24h??a.contract_guard_block_count_24h??parent.contract_guard_block_count_24h??0)} · delivery_actions_24h=${esc(devAuto.delivery_actions_24h??a.delivery_actions_24h??parent.delivery_actions_24h??0)} · enforced_24h=${esc(devAuto.enforced_delivery_count_24h??a.enforced_delivery_count_24h??parent.enforced_delivery_count_24h??0)} · issue_ok_rate_24h=${esc(devAuto.issue_reporting_ok_rate_24h??a.issue_reporting_ok_rate_24h??parent.issue_reporting_ok_rate_24h??100)}%</div>`
        : '';
      const issueReportLine=issueReportOk
        ? `<div class="insight-issue-report good"><strong>issue_report:</strong> ${esc(issueCodes)} · count=${esc(issueCount)} · sev=${esc(issueSeverity)}</div>`
        : `<div class="insight-issue-report bad"><strong>issue_report:</strong> missing/invalid · count=${esc(issueCount)} · sev=${esc(issueSeverity)} · errors=${esc((issueReportErrors||[]).join(',')||'unknown')}</div>`;
      return `<div class="insight-tile">
        <div class="insight-head">
          <span class="insight-role">${r}</span>
          <span class="insight-score ${q}">${q} ${score}</span>
        </div>
        <div class="insight-meta">activity=${esc(activity)} · task_update=${esc(taskUpdate)} · run_note_words=${esc(x.run_note_words||a.run_note_words||0)}</div>
        <div class="insight-line"><strong>next:</strong> ${esc((x.contract_status&&x.contract_status.next)||(a.contract&&a.contract.NEXT)||'?').slice(0,140)}</div>
        <div class="insight-line"><strong>action:</strong> ${esc(a.last_action_line||'—').slice(0,170)}</div>
        <div class="insight-line"><strong>root_cause:</strong> ${esc(e.root_cause||'—').slice(0,120)}</div>
        <div class="insight-line"><strong>verify:</strong> ${esc(e.verify||'—').slice(0,120)}</div>
        ${parentLine}
        <div class="insight-line"><strong>signals:</strong> E:${svc.error||0} W:${svc.warn||0} A:${svc.action||0} · events A:${evc.action||0} W:${evc.warn||0} E:${evc.error||0}</div>
        ${issueReportLine}
        <div class="insight-issues">${issues.length?`issues: ${esc(issues.join(', '))}`:'issues: none'}</div>
        <div class="insight-events">${interesting?esc(interesting):'Aucun événement marquant récent'}</div>
      </div>`;
    }).join('')
  }</div>`;
}
function activityFeedHtml(){
  const timeline=((A&&A.timeline)||[]).slice(0,24);
  if(!timeline.length){
    return '<div class="log-empty">Aucune activité récente consolidée</div>';
  }
  return `<div class="iter-issues">${
    timeline.map(ev=>{
      const role=String(ev.role||'unknown');
      const action=String(ev.action||'NOOP');
      const task=String(ev.task_id||ev.batch_id||'');
      const reason=String(ev.reason_code||'');
      const ts=String(ev.ts||'');
      const artifact=(Array.isArray(ev.artifact_refs)&&ev.artifact_refs.length)?String(ev.artifact_refs[0]||''):'';
      const sev=(action==='BLOCKED')?'error':(action==='NOOP'?'info':'warn');
      return `<div class="issue-row ${sev}">
        <div class="issue-head"><span class="issue-role">${esc(role)} → ${esc(action)}</span><span class="issue-sev ${sev}">${esc(ts.slice(11,19)||'--:--:--')}</span></div>
        <div class="issue-meta">${esc(task||'task: none')} ${reason?`· ${esc(reason)}`:''}</div>
        ${artifact?`<div class="issue-text">artifact: ${esc(artifact)}</div>`:''}
      </div>`;
    }).join('')
  }</div>`;
}
function taskInspectorHtml(){
  const items=((TA&&TA.items)||[]).slice(0,18);
  if(!items.length){
    return '<div class="log-empty">Aucune tâche active détaillée</div>';
  }
  return `<div class="iter-issues">${
    items.map(t=>{
      const state=String(t.state||'UNKNOWN');
      const sev=state==='IN_PROGRESS'?'warn':(state==='WAITING_DEP'?'error':'info');
      const stalled=Boolean(t.stalled);
      const progress=Math.max(0,Math.min(100,Number(t.progress_pct||0)));
      return `<div class="issue-row ${sev}">
        <div class="issue-head"><span class="issue-role">${esc(t.task_id||'')}</span><span class="issue-sev ${sev}">${esc(state)}</span></div>
        <div class="issue-meta">owner=${esc(t.owner||'?')} · progress=${progress}% · step=${esc(t.current_step||'—')}</div>
        <div class="progress-track" style="margin-top:6px"><div class="progress-fill" style="width:${progress}%"></div></div>
        ${t.artifact_output?`<div class="issue-text">artifact: ${esc(t.artifact_output)}</div>`:''}
        ${stalled?`<div class="issue-text" style="color:var(--coral)">stalled: ${esc(t.stalled_reason||'unknown')}</div>`:''}
      </div>`;
    }).join('')
  }</div>`;
}
function dependencyMapHtml(){
  const summary=(DM&&DM.summary)||{};
  const bottlenecks=((DM&&DM.bottlenecks)||[]).slice(0,5);
  const explanations=((DM&&DM.explanations)||[]).slice(0,5);
  if(!bottlenecks.length){
    return `<div class="queue-sync ok"><strong>dependency graph</strong> · nodes=${summary.nodes||0} · edges=${summary.edges||0} · bottlenecks=0</div>`;
  }
  return `<div>
    <div class="queue-sync warn" style="margin-bottom:8px"><strong>dependency graph</strong> · nodes=${summary.nodes||0} · edges=${summary.edges||0} · waiting_dep=${summary.waiting_dep_tasks||0}</div>
    <div class="iter-issues">${
      bottlenecks.map((b,idx)=>`<div class="issue-row warn">
        <div class="issue-head"><span class="issue-role">${idx+1}. ${esc(b.task_id||'unknown')}</span><span class="issue-sev warn">${esc(String(b.blocked_count||0))} blocked</span></div>
        <div class="issue-meta">oldest_wait=${esc(String(b.oldest_blocked_minutes??'-1'))} min</div>
        <div class="issue-text">${esc(explanations[idx]||'')}</div>
      </div>`).join('')
    }</div>
  </div>`;
}
function errorFeedHtml(){
  const items=(F&&F.items)||[];
  if(!items.length)return '<div class="log-empty">Aucune alerte récente.</div>';
  return items.slice(0,60).map(it=>{
    const cls=it.severity==='error'?'err':'warn';
    return `<div class="log-line ${cls}">[${esc(it.ts||'?')}] [${esc(it.role)}:${esc(it.kind)}] ${esc(it.line||'')}</div>`;
  }).join('');
}
function runtimeDiagnosticsHtml(){
  const Dg=G||{};
  const findings=(Dg.top_findings)||[];
  const s=(Dg.signals)||{};
  const permRecent=s.permission_errors_recent||0;
  const permHist=s.permission_errors_historical||0;
  const tshapeActive = s.tshape_takeover_active ? 'yes' : 'no';
  const tshapeTarget = s.tshape_takeover_target_role || 'none';
  const tshapeAge = (s.tshape_takeover_age_min==null || s.tshape_takeover_age_min<0) ? 'na' : `${s.tshape_takeover_age_min}m`;
  const devState = s.dev_coaching_state || 'unknown';
  const devStreak = Number(s.dev_none_no_signal_streak_24h||0);
  const devActions = Number(s.dev_delivery_actions_24h||0);
  const hdr=`perm_recent=${permRecent} · perm_hist=${permHist} · blocked=${(s.health_last_blocked_roles||[]).join(',')||'none'} · resume_max_gap=${s.resume_max_gap_s||0}s · admin_rc124=${s.admin_timeout_events_recent||0} · planner_guard=${s.planner_guard_blocked?'yes':'no'} · tshape=${tshapeActive}:${tshapeTarget}:${tshapeAge} · dev=${devState}:streak${devStreak}:act${devActions}`;
  const rows=findings.length?findings.map(f=>`
    <div class="diag-item ${esc(f.severity||'high')}">
      <div class="diag-title">${esc(f.title||'Finding')}</div>
      <div class="diag-meta">${esc(f.detail||'')}</div>
      <div class="diag-sample">${esc((f.sample||'').slice(0,220))}</div>
    </div>`).join(''):'<div class="diag-item ok"><div class="diag-title">No findings</div></div>';
  return `<div class="diag-meta" style="margin-bottom:8px">${esc(hdr)}</div><div class="diag-list">${rows}</div>`;
}
function issueSevClass(sev){
  const s=String(sev||'INFO').toUpperCase();
  if(s==='CRITICAL')return 'critical';
  if(s==='ERROR')return 'error';
  if(s==='WARN')return 'warn';
  if(s==='HIGH')return 'error';
  if(s==='MEDIUM')return 'warn';
  if(s==='LOW')return 'info';
  return 'info';
}
function truncIssues(v,max=90){
  const s=String(v||'none');
  if(s.length<=max)return s;
  return `${s.slice(0,max-1)}…`;
}
function issueRoleStats(role){
  const byRole=(D&&D.issues_recent_by_role)||{};
  const count=Number(byRole[role]||0);
  const fromStatus=(D&&D.last_issue_by_role&&D.last_issue_by_role[role])||{};
  let code=String(fromStatus.code||'none');
  let age=(fromStatus&&Number.isFinite(fromStatus.age_min))?fromStatus.age_min:-1;
  let sev=String(fromStatus.max_severity||'INFO').toUpperCase();
  const items=(R&&R.items)||[];
  if((!code||code==='none') && items.length){
    const hit=items.find(x=>String(x.role||'')===role && String(x.issue_status||'none')==='has_issues');
    if(hit){
      const codes=(hit.issue_codes||[]);
      if(Array.isArray(codes)&&codes.length)code=String(codes[0]);
      sev=String(hit.max_severity||sev||'INFO').toUpperCase();
      if(age<0){
        const ts=Date.parse(String(hit.ts_utc||''));
        if(Number.isFinite(ts))age=Math.max(0,Math.floor((Date.now()-ts)/60000));
      }
    }
  }
  return {count,code:code||'none',age,sev};
}
function msgStatusClass(status){
  const s=String(status||'none').toLowerCase();
  if(s==='done')return'msg-done';
  if(s==='blocked')return'msg-blocked';
  if(s==='deferred')return'msg-deferred';
  return'';
}
function iterationIssuesHtml(){
  const issueSummary=IS||{};
  const rows=(R&&R.items)||[];
  const sevTotals=(issueSummary.totals_by_severity)||{};
  const open=Number((sevTotals.WARN||0)+(sevTotals.ERROR||0)+(sevTotals.CRITICAL||0));
  const critical=Number(issueSummary.critical_open_count||0);
  const missing=(issueSummary.issue_publication_gap_roles||[]);
  const missingTxt=Array.isArray(missing)&&missing.length?missing.join(', '):'none';
  const head=`<div class="diag-meta" style="margin-bottom:8px">open=${open} · warn=${sevTotals.WARN||0} · error=${sevTotals.ERROR||0} · critical=${critical} · gap=${esc(missingTxt)}</div>`;
  if(!rows.length){
    return `${head}<div class="log-empty">Aucun report d'issue récent (ou source indisponible).</div>`;
  }
  const roles=monitorRoles();
  const groupHtml=roles.map(role=>{
    const roleRows=rows.filter(row=>String(row.role||'')===role && String(row.issue_status||'none')==='has_issues').slice(0,3);
    const roleHead=`<div class="issue-role-head"><span>${esc(role)}</span><a class="ext-link" href="/api/issues/feed?role=${encodeURIComponent(role)}&window_min=240&n=200" target="_blank">⬡ drilldown</a></div>`;
    if(!roleRows.length){
      return `<div class="issue-role-group">${roleHead}<div class="log-empty">none</div></div>`;
    }
    const rowsHtml=roleRows.map(row=>{
      const sev=issueSevClass(row.max_severity||'INFO');
      const rowCls=sev;
      const sevLabel=String(row.max_severity||'INFO').toUpperCase();
      const issues=Array.isArray(row.issue_codes)&&row.issue_codes.length?row.issue_codes.join(','):'none';
      return `<div class="issue-row ${rowCls}">
      <div class="issue-head">
        <span class="issue-role">${esc(row.role||'?')}</span>
        <span class="issue-sev ${rowCls}">${esc(sevLabel)}</span>
      </div>
      <div class="issue-meta">${esc(row.ts_utc||'?')} · tick=${esc(row.tick_id||'unknown')} · count=${esc(row.issue_count||0)} · rc=${esc(row.rc_final)}</div>
      <div class="issue-text">codes=${esc(truncIssues(issues))} · source=${esc(row.source||'')}</div>
      <div class="issue-text">next=${esc(truncIssues(row.next_action||'none',110))}</div>
    </div>`;
    }).join('');
    return `<div class="issue-role-group">${roleHead}${rowsHtml}</div>`;
  }).join('');
  return `${head}<div class="iter-issues">${groupHtml}</div>`;
}
function render(){
  if(!D)return;
  const statusUnavailable = !!D.__status_unavailable || !D.queue || !D.workboard;
  const health=(statusUnavailable?'UNKNOWN':(D.health||'DEGRADED'));
  const queue=D.queue||{total:null,closed:null,active:[],state_counts:{},mismatch_count:0,mismatches:[]};
  const workboard=D.workboard||{total:null,done:null,ready:null,in_progress:null,ready_tasks:[],in_progress_tasks:[]};
  const agents=D.agents||{};
  const rl=D.rate_limits||[];
  const kpi=D.kpi||{};
  const activitySummary=D.activity_summary||{};
  const activityBundle=A||{};
  const systemSummary=(activityBundle.system_summary)||{};
  const src=D.sources||{};
  const doctor=(D&&D.doctor)||{};
  const po=(D&&D.po_scrum_master)||{};
  const msgBus=(D&&D.agent_messages)||{};
  document.getElementById('hd-ts').textContent=new Date().toLocaleTimeString('fr-FR');
  const hc=document.getElementById('health-capsule');
  hc.className='status-capsule '+(statusUnavailable?'warn':(health==='OK'?'ok':health==='STALE'?'warn':'err'));
  document.getElementById('health-txt').textContent=health;
  const qDisplayTotal=(typeof queue.display_total==='number' && queue.display_total>0)?queue.display_total:queue.total;
  const qDisplayClosed=(typeof queue.display_closed==='number')?queue.display_closed:queue.closed;
  const pct=(typeof qDisplayTotal==='number' && qDisplayTotal>0 && typeof qDisplayClosed==='number')?Math.round(qDisplayClosed/qDisplayTotal*100):0;
  const hcls=statusUnavailable?'warn':(health==='OK'?'ok':health==='STALE'?'warn':'err');
  const alertsHtml=(rl||[]).map(r=>`<div class="alert-banner span2 fade"><span style="font-size:16px">⚠</span><div><strong>${r.model.toUpperCase()} RATE-LIMIT</strong> — ${r.remaining_s}s (~${Math.ceil(r.remaining_s/60)}min)</div></div>`).join('');
  const apiErrHtml = statusUnavailable
    ? `<div class="alert-banner span2 fade"><span style="font-size:16px">⚠</span><div><strong>Data source indisponible</strong> — affichage partiel (errors: ${esc((API_ERRORS||[]).slice(0,4).join(' | ')||'status fetch failed')})</div></div>`
    : '';
  const qsc=(queue.state_counts)||{};
  const readyPlannerDisplay = Number.isFinite(Number(queue.ready_planner_count)) ? Number(queue.ready_planner_count) : ((qsc.READY||0)+(qsc.READY_PLANNER||0));
  const readyDevDisplay = Number.isFinite(Number(queue.ready_dev_count)) ? Number(queue.ready_dev_count) : (qsc.READY_DEV||0);
  const readyTotalDisplay = Number.isFinite(Number(queue.ready)) ? Number(queue.ready) : (readyPlannerDisplay + readyDevDisplay);
  const readyDevSource = queue.ready_dev_source || 'queue_state';
  const queueStatesHtml = [
    `<span class="state-chip ready">READY ${readyTotalDisplay}</span>`,
    `<span class="state-chip ready">READY_DEV ${readyDevDisplay} (${readyDevSource==='workboard_runtime'?'workboard':'queue'})</span>`,
    `<span class="state-chip progress">IN_PROGRESS ${qsc.IN_PROGRESS||0}</span>`,
    `<span class="state-chip wait">WAITING_DEP ${qsc.WAITING_DEP||0}</span>`,
    `<span class="state-chip done">DONE/CLOSED ${qDisplayClosed ?? '—'}</span>`
  ].join('');
  const mismatchItems=(queue.mismatches||[]);
  const mismatchHtml = statusUnavailable
    ? `<div class="queue-sync warn"><strong>Queue/workboard indisponible</strong><br>Impossible de confirmer la cohérence temps réel.</div>`
    : mismatchItems.length
    ? `<div class="queue-sync err"><strong>Mismatch ${queue.mismatch_count||mismatchItems.length}</strong><br>${mismatchItems.map(m=>`${esc(m.batch)} · ${esc(m.issue)}`).join('<br>')}</div>`
    : `<div class="queue-sync ok">Queue/workboard sync OK</div>`;
  const batchRows=((queue.display_batches&&queue.display_batches.length)?queue.display_batches:(queue.active||[]));
  const qRows=batchRows.map(i=>`<div class="queue-row ${i.state}"><span class="queue-id">${i.id}</span><span class="queue-badge ${i.state}">${(i.state==='READY' || i.state==='READY_PLANNER')?'▶ READY_PLANNER':i.state==='READY_DEV'?'▶ READY_DEV':i.state==='IN_PROGRESS'?'⟳ IN PROG':i.state==='CLOSED'?'■ CLOSED':'◌ WAITING'}</span></div>`).join('')+`<div class="queue-row CLOSED"><span class="queue-id" style="color:var(--dim)">■ ${qDisplayClosed ?? '—'} clos / ${qDisplayTotal ?? '—'}</span></div>`;
  const rf=(D&&D.runtime_freshness)||{};
  const freshnessClass = rf.state==='fresh'?'ok':(rf.state==='warm'?'warn':'err');
  const freshnessText = (rf.seconds>=0 && !statusUnavailable)?`${rf.state||'unknown'} · ${rf.seconds}s`:'unknown';
  const roles=monitorRoles();
  tickRole=ensureRole(tickRole,roles);
  contractRole=ensureRole(contractRole,roles);
  execRole=ensureRole(execRole,roles);
  logRole=ensureRole(logRole,roles);
  const tileRoles=roles.length ? roles : ['planner','dev','admin'];
  const pa=(D&&D.planner_autonomy)||{};
  const ts=(D&&D.dispatcher_tshape)||{};
  const poRunAge=(Number.isFinite(po.last_run_age_min) && po.last_run_age_min>=0)?`${po.last_run_age_min}m`:'never';
  const poReportAge=(Number.isFinite(po.last_report_age_min) && po.last_report_age_min>=0)?`${po.last_report_age_min}m`:'na';
  const poActiveTxt=po.active?'1':'0';
  const poStatus=esc(po.status||'UNKNOWN');
  const poVerdict=esc(po.verdict||'UNKNOWN');
  const poLockSkip=Number.isFinite(Number(po.lock_skip_streak))?Number(po.lock_skip_streak):0;
  const doctorStatus=esc(String(doctor.status||'unknown').toUpperCase());
  const doctorDuration=(doctor&&doctor.meta&&Number.isFinite(doctor.meta.duration_ms))?`${doctor.meta.duration_ms}ms`:'na';
  const doctorChecks=(doctor&&doctor.checks&&typeof doctor.checks==='object')?doctor.checks:{};
  const doctorFailures=Object.entries(doctorChecks)
    .filter(([_,v])=>String((v&&v.status)||'unknown').toLowerCase()!=='ok')
    .map(([k,v])=>`${k}:${String((v&&v.status)||'unknown').toUpperCase()}`)
    .slice(0,3)
    .join(', ') || 'none';
  const poRecentMsgs=(Array.isArray(po.recent_messages)?po.recent_messages:[]).slice(0,3).map(m=>{
    const id=esc(m.id||'?');
    const pr=esc((m.priority||'normal').toUpperCase());
    const tg=Array.isArray(m.targets)?m.targets.join(','):'';
    return `${id} · ${pr} · ${esc(tg)}`;
  }).join('<br>') || 'none';
  const poTickTail=Array.isArray(po.tick_tail)?po.tick_tail:[];
  const poRunnerTail=Array.isArray(po.runner_tail)?po.runner_tail:[];
  const poEventsTail=Array.isArray(po.events_tail)?po.events_tail:[];
  const plannerReqTop=String((agents.planner&&agents.planner.planner_action_required)||'').toLowerCase();
  const paBadge=(plannerReqTop && plannerReqTop!=='none')
    ? `<span class="planner-action-chip">ACTION REQUIRED · ${esc(plannerReqTop)}</span>`
    : '';
  const tsBadge=(ts&&ts.active)
    ? `<span class="planner-action-chip">TAKEOVER ACTIVE · ${esc(ts.target_role||'unknown')}</span>`
    : '';
  const agentTiles=tileRoles.map(role=>{
    const a=_agentForRole(role);
    const xi=(X&&X[role])||{};
    const contractStatus=xi.contract_status||{};
    const verdict=a.verdict||contractStatus.verdict||'MUTED';
    const statusVal=a.status||contractStatus.status||'';
    const blocker=a.blocker||contractStatus.blocker_id||'NONE';
    const delta=a.delta||contractStatus.delta||'';
    const nextVal=a.next||contractStatus.next||'';
    const rl=isRateLimited(verdict,statusVal,blocker,delta);
    const softPlannerAction = isSoftPlannerSignal(role,a,blocker,delta);
    const v=vc(verdict,statusVal,blocker,delta,role,a);
    const bl=(!rl&&blocker&&blocker!=='NONE')?`<div class="agent-blocker${softPlannerAction?' soft':''}"><span>${softPlannerAction?'◎':'▲'}</span>${esc(blocker)}</div>`:'';
    const plannerReqLabel = String(a.planner_action_required||'').toLowerCase();
    const plannerReq = (role==='planner' && plannerReqLabel && plannerReqLabel!=='none')
      ? `<div class="agent-action-required">ACTION REQUIRED · ${esc(plannerReqLabel)}</div>`
      : '';
    const plannerQualityMissing = (role==='planner' && Array.isArray(a.quality_missing_fields))
      ? a.quality_missing_fields.filter(x=>String(x||'').trim()).length
      : 0;
    const plannerQualityBadge = (role==='planner' && plannerQualityMissing>0)
      ? `<div class="agent-action-required">QUALITY INCOMPLETE · ${plannerQualityMissing}</div>`
      : '';
    const adminTakeoverReq = (role==='admin' && Boolean(a.tshape_active))
      ? `<div class="agent-action-required">TAKEOVER ACTIVE · ${esc(a.tshape_target_role||'unknown')}</div>`
      : '';
    const scrumActionsSent = (role==='scrum_master') ? Number(a.actions_sent_60m||0) : 0;
    const scrumActionBadge = (role==='scrum_master' && scrumActionsSent>0)
      ? `<div class="agent-action-required msg-deferred">SCRUM ACTION ${scrumActionsSent}${a.last_action_target?` · ${esc(a.last_action_target)}`:''}${a.last_action_message_id?` · ${esc(a.last_action_message_id)}`:''}</div>`
      : '';
    const actionReq = plannerReq || adminTakeoverReq;
    const age=a.tick_age_min!=null?`${a.tick_age_min}m ago`:(xi.last_ts?esc(xi.last_ts):'?');
    const schedule=a.schedule||'—';
    const nextTick=(a.next_tick_at&&a.next_tick_min!=null)?`${a.next_tick_at} · ~${a.next_tick_min}min`:'—';
    const issueStat=issueRoleStats(role);
    const issueCls=issueSevClass(issueStat.sev);
    const issueAge=(Number.isFinite(issueStat.age) && issueStat.age>=0)?`${issueStat.age}m`:'na';
    const issueMeta=`issues_60m=${issueStat.count} · last=${issueStat.code||'none'} · age=${issueAge}`;
    const issueChip=issueStat.count>0
      ? `<div class="agent-issue-chip ${issueCls}">${esc(issueMeta)}</div>`
      : `<div class="agent-issue-chip info">${esc(issueMeta)}</div>`;
    const pendingMsgCount=Number(a.pending_messages_count||0);
    const lastMsgActionStatus=String(a.last_message_action_status||'none').toLowerCase();
    const msgStatusCls=msgStatusClass(lastMsgActionStatus);
    const msgStatusTxt=(lastMsgActionStatus && lastMsgActionStatus!=='none')?` · ${lastMsgActionStatus}`:'';
    const msgBadge=pendingMsgCount>0
      ? `<div class="agent-action-required ${msgStatusCls}">MSG ${pendingMsgCount}${a.last_message_id?` · ${esc(a.last_message_id)}`:''}${msgStatusTxt}</div>`
      : '';
    return`<div class="agent-tile fade" onclick="setContract('${role}')"><div class="agent-stripe ${v}"></div><div class="agent-inner"><div class="agent-header"><div class="agent-name-wrap"><span style="font-size:18px">${vcIcon(v)}</span><div><div class="agent-name">${role}</div><div class="agent-sched">${schedule}</div></div></div><div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px"><span class="vc ${v}">${v}</span><span class="age-chip">${age}</span></div></div><div class="agent-delta">${esc(delta)||'—'}</div>${issueChip}${msgBadge}${scrumActionBadge}${plannerQualityBadge}${actionReq}${bl}<div class="agent-next">${esc(nextVal).slice(0,120)}</div><div class="spark">${sparkHtml(role)}</div><div class="agent-footer"><span class="next-lbl">Prochain tick</span><span class="next-time">${nextTick}</span></div></div></div>`;
  }).join('');
  const wbHtml=[...(workboard.in_progress_tasks||[]).map(t=>`<div class="task-chip IN_PROGRESS" title="${t.title}"><span>⟳</span><strong>${t.id}</strong><span class="task-chip-role">${t.role}</span></div>`),
    ...(workboard.ready_tasks||[]).map(t=>`<div class="task-chip ${String((t&&t.state)||'READY').toUpperCase()==='READY_DEV'?'READY_DEV':'READY'}" title="${t.title}"><span>▶</span><strong>${t.id}</strong><span class="task-chip-role">${t.role}</span></div>`)].join('')||'<span style="color:var(--ghost);font-size:11px">Aucune tâche active</span>';
  const tickTabs=roles.map(r=>`<button class="t-tab${r===tickRole?' on':''}" onclick="setTick('${r}')">${r}</button>`).join('');
  const ctabs=roles.map(r=>`<button class="t-tab${r===contractRole?' on-v':''}" onclick="setContract('${r}')">${r}</button>`).join('');
  const etabs=roles.map(r=>`<button class="t-tab${r===execRole?' on-g':''}" onclick="setExec('${r}')">${r}</button>`).join('');
  const ex=latestExec(execRole);
  const plannerExecLinks = execRole==='planner'
    ? `<a class="ext-link" href="/api/planner/log-bundle" target="_blank">⬡ Planner bundle</a><a class="ext-link" href="/api/planner/timeline?n=120" target="_blank">⬡ Planner timeline</a>`
    : '';
  const plannerContractLinks = contractRole==='planner'
    ? `<a class="ext-link" href="/api/planner/log-bundle" target="_blank">⬡ Planner bundle</a><a class="ext-link" href="/api/planner/timeline?n=120" target="_blank">⬡ Planner timeline</a>`
    : '';
  document.getElementById('page').innerHTML=`
    ${apiErrHtml}
    ${alertsHtml}
    <div class="col-left">
      <div class="panel fade"><div class="panel-head"><span class="panel-label">Santé</span><div class="status-capsule ${hcls}" style="padding:3px 9px;font-size:10px"><span class="status-dot${health==='OK'?' live':''}"></span>${health}</div></div>
        <div class="health-hero"><div class="health-ring-wrap"><div class="health-ring ${hcls}"><div class="health-ring-inner"><div class="health-pct">${pct}</div><div class="health-pct-label">%</div></div></div></div><div class="health-status-word ${hcls}">${health}</div><div class="health-ts">${new Date().toLocaleTimeString('fr-FR')}</div></div>
        <div class="stat4"><div class="stat-tile g"><div class="stat-n g">${workboard.done ?? '—'}</div><div class="stat-lbl">DONE</div></div><div class="stat-tile b"><div class="stat-n b">${workboard.ready ?? '—'}</div><div class="stat-lbl">READY</div></div><div class="stat-tile y"><div class="stat-n y">${kpi.done_24h??'—'}</div><div class="stat-lbl">24h</div></div><div class="stat-tile v"><div class="stat-n v">${kpi.proofs??'—'}</div><div class="stat-lbl">PROOFS</div></div></div></div>
      <div class="panel fade"><div class="panel-head"><span class="panel-label">Batches</span><span style="font-size:10px;color:var(--ghost)">${qDisplayClosed ?? '—'}/${qDisplayTotal ?? '—'}</span></div><div class="panel-body"><div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div><div class="queue-states">${queueStatesHtml}</div><div class="queue-list">${qRows}</div>${mismatchHtml}</div></div>
      <div class="panel fade"><div class="panel-head"><span class="panel-label">Vélocité</span><span style="font-size:10px;color:var(--ghost)">${kpi.ts??''}</span></div><div class="stat4"><div class="stat-tile g"><div class="stat-n g">${kpi.done_total??'—'}</div><div class="stat-lbl">Total</div></div><div class="stat-tile y"><div class="stat-n y">${kpi.done_24h??'—'}</div><div class="stat-lbl">24h</div></div><div class="stat-tile"><div class="stat-n">${kpi.done_7d??'—'}</div><div class="stat-lbl">7 jours</div></div><div class="stat-tile b"><div class="stat-n b">${kpi.proofs??'—'}</div><div class="stat-lbl">Proofs</div></div></div></div>
    </div>
	    <div class="col-right">
    <div class="panel fade"><div class="panel-head"><span class="panel-label">Agents</span><span style="font-size:10px;color:var(--ghost)">cliquer → contrat ${paBadge} ${tsBadge}</span></div><div class="panel-body"><div class="agents-row">${agentTiles}</div></div></div>
	      <div class="panel fade"><div class="panel-head"><span class="panel-label">Workboard actif</span><span style="font-size:10px;color:var(--ghost)">${workboard.total ?? '—'} tâches · ${workboard.done ?? '—'} done</span></div><div class="panel-body"><div class="task-grid">${wbHtml}</div><div class="queue-sync ${freshnessClass}" style="margin-top:10px"><strong>Runtime freshness</strong> · ${freshnessText}</div><div class="queue-sync warn" style="margin-top:8px"><strong>Planner autonomy</strong> · idle=${pa.ready_idle_streak??0} · low_score=${pa.low_score_streak??0} · runway_no_batch=${pa.runway_no_batch_streak??0} · autofix24h=${pa.autofix_count_24h??0}</div><div class="queue-sync warn" style="margin-top:8px"><strong>T-shape admin</strong> · active=${ts.active?'1':'0'} · target=${esc(ts.target_role||'none')} · blocker=${esc(ts.reason_blocker||'NONE')}</div><div class="queue-sync ${doctorStatus==='OK'?'ok':'warn'}" style="margin-top:8px"><strong>Doctor</strong> · status=${doctorStatus} · runtime=${doctorDuration}</div><div class="queue-sync ${doctorFailures==='none'?'ok':'warn'}" style="margin-top:8px"><strong>Doctor checks</strong> · ${esc(doctorFailures)}</div><div class="queue-sync ${Number(activitySummary.events_last_1h||0)>0?'ok':'warn'}" style="margin-top:8px"><strong>Activity summary</strong> · 1h=${activitySummary.events_last_1h||0} · 6h=${activitySummary.events_last_6h||0} · progressed_1h=${activitySummary.tasks_progressed_last_1h||0} · bottleneck=${esc(activitySummary.current_bottleneck||'none')}</div><div class="queue-sync" style="margin-top:8px"><strong>System summary</strong> · next=${esc(systemSummary.recommended_next_action||'monitor')} · changed15m=${(systemSummary.what_changed_last_15m||[]).length||0}</div><div style="margin-top:8px;font-size:10px;color:var(--ghost);line-height:1.5"><strong>sources:</strong><br>queue=${esc(shortPath(src.queue||''))}<br>workboard=${esc(shortPath(src.workboard||''))}</div></div></div>
	      <div class="panel fade"><div class="panel-head"><span class="panel-label">Agent Activity Feed</span><span style="font-size:10px;color:var(--ghost)">window=${esc(String((A&&A.window_hours)||6))}h · timeline=${(A&&A.timeline&&A.timeline.length)||0}</span></div><div class="panel-body"><div class="queue-sync ok"><strong>Throughput</strong> · completed_1h=${(A&&A.throughput&&A.throughput.tasks_completed_last_hour)||0} · artifacts_1h=${(A&&A.throughput&&A.throughput.artifacts_generated_last_hour)||0} · rate=${(A&&A.throughput&&A.throughput.delivery_rate)||0}</div><div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:8px"><div class="log-box"><div class="log-head">Timeline</div><div class="log-scroll">${activityFeedHtml()}</div></div><div class="log-box"><div class="log-head">Task Inspector</div><div class="log-scroll">${taskInspectorHtml()}</div></div><div class="log-box"><div class="log-head">Dependency Map</div><div class="log-scroll">${dependencyMapHtml()}</div></div></div><div class="link-row"><a class="ext-link" href="/api/agent-activity?window=6&limit=300" target="_blank">⬡ Agent activity JSON</a><a class="ext-link" href="/api/tasks/active?window=6&limit=120" target="_blank">⬡ Tasks active JSON</a><a class="ext-link" href="/api/dependencies/map?limit=300" target="_blank">⬡ Dependencies JSON</a></div></div></div>
	      <div class="panel fade"><div class="panel-head"><span class="panel-label">PO Scrum Master (Advisory)</span><span style="font-size:10px;color:var(--ghost)">scheduled/5m · active=${poActiveTxt}</span></div><div class="panel-body"><div class="queue-sync ${po.active?'warn':'ok'}"><strong>run_age</strong> ${poRunAge} · <strong>report_age</strong> ${poReportAge} · <strong>status</strong> ${poStatus} · <strong>verdict</strong> ${poVerdict} · <strong>lock_skip_streak</strong> <span class="${poLockSkip>3?'err':'ok'}">${poLockSkip}</span></div><div class="queue-sync warn" style="margin-top:8px"><strong>message bus</strong> · open=${msgBus.open??0} · delivered_recent=${msgBus.delivered_recent??0} · actioned_recent=${msgBus.actioned_recent??0} · closed_recent=${msgBus.closed_recent??0}</div><div class="queue-sync" style="margin-top:8px"><strong>recent_messages</strong><br>${poRecentMsgs}</div><div class="exec-logs" style="margin-top:8px"><div class="log-box"><div class="log-head">fc-ticks (scrum_master.tick.log)</div><div class="log-scroll">${logLinesHtml(poTickTail)}</div></div><div class="log-box"><div class="log-head">role-runner (scrum_master.live.log)</div><div class="log-scroll">${logLinesHtml(poRunnerTail)}</div></div><div class="log-box"><div class="log-head">runner-events (scrum_master.events.log)</div><div class="log-scroll">${logLinesHtml(poEventsTail)}</div></div></div><div class="link-row"><a class="ext-link" href="/api/ticks/scrum_master" target="_blank">⬡ Ticks</a><a class="ext-link" href="/api/logs/scrum_master" target="_blank">⬡ Logs</a><a class="ext-link" href="/api/logs/scrum_master/events" target="_blank">⬡ Events</a><a class="ext-link" href="/api/log-view?role=scrum_master&kind=runner&n=220" target="_blank">⬡ Log JSON</a></div><div style="margin-top:8px;font-size:10px;color:var(--ghost);line-height:1.5"><strong>report:</strong> ${esc(shortPath(po.last_report_path||''))}</div></div></div>
		      <div class="panel fade"><div class="panel-head"><span class="panel-label">Exécution récente</span><span style="color:var(--emerald);font-size:11px;font-weight:600">${execRole}</span></div><div class="panel-body"><div class="tab-bar" id="exec-tabs">${etabs}</div><div class="exec-meta">${execMetaHtml(execRole)}</div><div class="exec-logs"><div class="log-box"><div class="log-head">fc-ticks (${execRole}.tick.log)</div><div class="log-scroll">${logLinesHtml(ex.tick_tail)}</div></div><div class="log-box"><div class="log-head">role-runner (${execRole}.live.log)</div><div class="log-scroll">${logLinesHtml(ex.runner_tail)}</div></div><div class="log-box"><div class="log-head">runner-events (${execRole}.events.log)</div><div class="log-scroll">${logLinesHtml(ex.events_tail)}</div></div></div><div class="link-row"><a class="ext-link" href="/api/execution/${execRole}" target="_blank">⬡ Execution JSON</a><a class="ext-link" href="/api/logs/${execRole}" target="_blank">⬡ Runner logs</a><a class="ext-link" href="/api/logs/${execRole}/events" target="_blank">⬡ Runner events</a><a class="ext-link" href="/api/ticks/${execRole}" target="_blank">⬡ Ticks</a>${plannerExecLinks}</div></div></div>
		      <div class="panel fade"><div class="panel-head"><span class="panel-label">Execution Truth Matrix</span><span style="color:var(--amber);font-size:11px;font-weight:600">activité réelle · qualité · signaux</span></div><div class="panel-body">${insightsHtml()}</div></div>
		      <div class="panel fade"><div class="panel-head"><span class="panel-label">Execution Issues Feed</span><span style="color:var(--coral);font-size:11px;font-weight:600">open ${((IS&&IS.totals_by_severity)?((IS.totals_by_severity.WARN||0)+(IS.totals_by_severity.ERROR||0)+(IS.totals_by_severity.CRITICAL||0)):0)} · critical ${(IS&&IS.critical_open_count)||0}</span></div><div class="panel-body">${iterationIssuesHtml()}</div></div>
		      <div class="panel fade"><div class="panel-head"><span class="panel-label">Logs agents</span><span style="color:var(--aqua);font-size:11px;font-weight:600">${logRole} · ${logKind}</span></div><div class="panel-body">${logViewerHtml()}</div></div>
		      <div class="panel fade"><div class="panel-head"><span class="panel-label">Diagnostic Rapide Runtime</span><span style="color:var(--amber);font-size:11px;font-weight:600">root causes auto</span></div><div class="panel-body">${runtimeDiagnosticsHtml()}</div></div>
		      <div class="panel fade"><div class="panel-head"><span class="panel-label">Error Feed Global</span><span style="color:var(--coral);font-size:11px;font-weight:600">${(F&&F.count)||0} événements</span></div><div class="panel-body"><div class="log-box"><div class="log-head">Dernières erreurs/warnings (tous agents)</div><div class="log-scroll">${errorFeedHtml()}</div></div></div></div>
		      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
	        <div class="panel fade"><div class="panel-head"><span class="panel-label">Ticks</span></div><div class="panel-body"><div class="tab-bar" id="tick-tabs">${tickTabs}</div><div class="tick-scroll" id="tick-content">${tickRowsHtml(tickRole)}</div></div></div>
	        <div class="panel fade"><div class="panel-head"><span class="panel-label">Contrat</span><span style="color:var(--lavender);font-size:11px;font-weight:600">${contractRole}</span></div><div class="panel-body"><div class="tab-bar" id="contract-tabs">${ctabs}</div><div class="contract-block" id="contract-content">${contractBodyHtml(contractRole)}</div><div class="link-row"><a class="ext-link" href="/api/contract/${contractRole}" target="_blank">⬡ JSON</a><a class="ext-link" href="/api/logs/${contractRole}" target="_blank">⬡ Logs</a><a class="ext-link" href="/api/logs/${contractRole}/events" target="_blank">⬡ Events</a><a class="ext-link" href="/api/ticks/${contractRole}" target="_blank">⬡ Ticks</a><a class="ext-link" href="/api/workboard" target="_blank">⬡ Workboard</a>${plannerContractLinks}</div></div></div>
	      </div>
	    </div>`;
}
function setTick(r){tickRole=r;const el=document.getElementById('tick-content');const tabs=document.querySelectorAll('#tick-tabs .t-tab');if(el)el.innerHTML=tickRowsHtml(r);tabs.forEach(t=>t.classList.toggle('on',t.textContent.trim()===r));}
function setContract(r){contractRole=r;render();}
function setExec(r){execRole=r;render();}
async function setLogRole(r){logRole=r;await doRefresh();}
async function setLogKind(k){logKind=k;await doRefresh();}
async function doRefresh(){cdr=12;const ri=document.getElementById('ri');if(ri)ri.innerHTML='<span class="spin-sm"></span>';await load();render();if(ri)ri.textContent='⟳';}
function startCd(){clearInterval(iv);iv=setInterval(async()=>{cdr--;const el=document.getElementById('cd');const ts=document.getElementById('hd-ts');if(ts)ts.textContent=new Date().toLocaleTimeString('fr-FR');if(cdr<=0){cdr=12;await load();render();}if(el)el.textContent=`auto ${cdr}s`;},1000);}
doRefresh().then(startCd);
</script>
</body>
</html>"""

PLANNER_DEBUG_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FC Planner Debug</title>
<style>
*{box-sizing:border-box} body{margin:0;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;background:#060b11;color:#c9dae8}
.wrap{max-width:1440px;margin:0 auto;padding:16px}
.top{display:flex;gap:10px;align-items:center;justify-content:space-between;margin-bottom:12px}
.title{font-size:18px;font-weight:700;color:#fff}
.actions{display:flex;gap:8px;align-items:center}
.btn{display:inline-flex;align-items:center;gap:6px;padding:6px 10px;border:1px solid #274159;border-radius:8px;color:#9fd4ff;text-decoration:none;background:#0e1824}
.btn:hover{border-color:#37b7ff}
.cd{font-size:11px;color:#7ea2bd}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.card{background:#0c1520;border:1px solid #1d2f41;border-radius:10px;overflow:hidden}
.head{padding:9px 12px;background:#101c2a;border-bottom:1px solid #1d2f41;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:#7ea2bd}
.body{padding:12px}
.kpi{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
.pill{padding:8px;border:1px solid #223447;border-radius:8px;background:#0b121c}
.lbl{font-size:10px;color:#7191ab;text-transform:uppercase}
.val{font-size:17px;color:#fff;font-weight:700}
.ok{color:#00e58a}.warn{color:#ffc24f}.err{color:#ff5d75}
.list{margin:0;padding-left:18px;line-height:1.5}
.table{width:100%;border-collapse:collapse;font-size:11px}
.table th,.table td{border-bottom:1px solid #1a2a39;padding:6px 6px;text-align:left;vertical-align:top}
.table th{color:#7ea2bd;font-weight:600}
.mono{white-space:pre-wrap;word-break:break-word;background:#070e16;border:1px solid #1a2a39;border-radius:8px;padding:10px;max-height:300px;overflow:auto;font-size:11px;line-height:1.45}
.span2{grid-column:1/-1}
@media(max-width:980px){.grid{grid-template-columns:1fr}.kpi{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div class="title">Planner Debug</div>
    <div class="actions">
      <a class="btn" href="/">← Dashboard</a>
      <a class="btn" href="/api/planner/log-bundle" target="_blank">Bundle JSON</a>
      <button class="btn" onclick="refreshNow()">⟳ Refresh</button>
      <span id="cd" class="cd">auto 15s</span>
    </div>
  </div>
  <div id="app" class="grid">
    <div class="card span2"><div class="body">Chargement…</div></div>
  </div>
</div>
<script>
let cdr=15, iv=null;
function esc(v){return String(v||'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;')}
function scoreCls(s){if(s>=85)return'ok';if(s>=70)return'warn';return'err'}
function lines(arr, empty='(empty)'){if(!arr||!arr.length)return empty;return arr.map(x=>String(x)).join('\n')}
function normTs(v){return v||'—'}
function auditRows(events){
  if(!events||!events.length) return '<tr><td colspan="8">Aucun event audit</td></tr>';
  return events.slice().reverse().slice(0,25).map(e=>`<tr>
    <td>${esc(normTs(e.ts_utc))}</td>
    <td>${esc(e.source||'')}</td>
    <td>${esc(e.task_update||'')}</td>
    <td>${esc(e.delta||'')}</td>
    <td>${esc(e.guardian_score)}</td>
    <td>${esc(e.guardian_level||'')}</td>
    <td>${esc(e.blocker_id||'')}</td>
    <td>${esc(e.next_action_unique||'')}</td>
  </tr>`).join('');
}
function render(bundle,status){
  const g=bundle.guardian_latest||{};
  const issues=(g.issues||[]);
  const recos=(g.recommendations||[]);
  const streaks=(g.streaks||{});
  const score=Number(g.score||0);
  const scls=scoreCls(score);
  const health=(status&&status.health)||'—';
  const app=document.getElementById('app');
  app.innerHTML=`
    <div class="card span2"><div class="head">Guardian Snapshot</div><div class="body">
      <div class="kpi">
        <div class="pill"><div class="lbl">Health</div><div class="val">${esc(health)}</div></div>
        <div class="pill"><div class="lbl">Score</div><div class="val ${scls}">${esc(g.score)}</div></div>
        <div class="pill"><div class="lbl">Level</div><div class="val">${esc(g.level||'')}</div></div>
        <div class="pill"><div class="lbl">Updated</div><div class="val" style="font-size:12px">${esc(normTs(g.ts_utc))}</div></div>
        <div class="pill"><div class="lbl">Ready Idle Streak</div><div class="val">${esc(streaks.ready_idle_streak)}</div></div>
        <div class="pill"><div class="lbl">Low Score Streak</div><div class="val">${esc(streaks.low_score_streak)}</div></div>
        <div class="pill"><div class="lbl">Runway No Batch</div><div class="val">${esc(streaks.runway_no_batch_streak)}</div></div>
        <div class="pill"><div class="lbl">Source</div><div class="val" style="font-size:12px">${esc(g.source||'')}</div></div>
      </div>
    </div></div>

    <div class="card"><div class="head">Issues</div><div class="body"><ul class="list">${issues.length?issues.map(i=>`<li>${esc(i)}</li>`).join(''):'<li>none</li>'}</ul></div></div>
    <div class="card"><div class="head">Recommendations</div><div class="body"><ul class="list">${recos.length?recos.map(i=>`<li>${esc(i)}</li>`).join(''):'<li>none</li>'}</ul></div></div>

    <div class="card span2"><div class="head">Planner Audit (Latest 25)</div><div class="body">
      <table class="table">
        <thead><tr><th>ts</th><th>source</th><th>task_update</th><th>delta</th><th>score</th><th>level</th><th>blocker</th><th>next_action</th></tr></thead>
        <tbody>${auditRows(bundle.audit_events||[])}</tbody>
      </table>
    </div></div>

    <div class="card"><div class="head">Planner Timeline</div><div class="body"><div class="mono">${esc(lines(bundle.timeline||[]))}</div></div></div>
    <div class="card"><div class="head">Runner Events</div><div class="body"><div class="mono">${esc(lines(bundle.runner_events||[]))}</div></div></div>
  `;
}
async function load(){
  const [bundle,status]=await Promise.all([
    fetch('/api/planner/log-bundle?n=120').then(r=>r.json()),
    fetch('/api/status').then(r=>r.json())
  ]);
  render(bundle,status);
}
async function refreshNow(){cdr=15;await load();}
function startCd(){
  clearInterval(iv);
  iv=setInterval(async()=>{
    cdr--;
    const el=document.getElementById('cd');
    if(el)el.textContent=`auto ${cdr}s`;
    if(cdr<=0){cdr=15;await load();}
  },1000);
}
refreshNow().then(startCd);
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(
        HTML,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

@app.get("/planner-debug", response_class=HTMLResponse)
def planner_debug_page():
    return HTMLResponse(
        PLANNER_DEBUG_HTML,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

if __name__=="__main__":
    print("\u2705  Monitor : http://localhost:7779")
    uvicorn.run(app, host="0.0.0.0", port=7779, log_level="warning")
