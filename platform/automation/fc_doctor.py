#!/usr/bin/env python3
"""Finance Copilot doctor (JSON).

Exit codes:
- 0: ok
- 1: degraded
- 2: error
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from orchestrator_paths import (
    load_runtime_state,
    resolve_orchestrator_read_path,
    runtime_state_root,
)


@dataclass
class CheckResult:
    status: str
    detail: dict[str, Any]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _probe_blocked_message(raw: object) -> bool:
    token = str(raw or "").strip().lower()
    if not token:
        return False
    blocked_markers = (
        "permission denied",
        "operation not permitted",
        "temporarily unavailable",
        "sandbox",
    )
    return any(marker in token for marker in blocked_markers)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return None


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
    config = _read_json(_runner_config_path(root))
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


ROLE_MAP_FILE = Path("docs/orchestrator-ops/parallel-role-cron-map.json")
BASELINE_ADMIN_JOBS = (
    "adminapp-codex-sync-10m",
    "admin-agents-supervisor-15m",
)
BASELINE_UTILITY_JOBS = (
    "stale-sweep-autoheal-7m",
    "dg-alert-15m",
)
BASELINE_ADVISORY_JOBS = (
    "po-scrum-master-advisory-5m",
    "po_scrum_master-advisory-5m",
    "scrum-master-operational-5m",
    "scrum_master-operational-5m",
)


def _planner_only_mode(root: Path) -> bool:
    state = load_runtime_state(root)
    execution_mode = str(state.get("execution_mode", "") or "").strip()
    operator_mode = str(state.get("operator_mode", "") or "").strip()
    if execution_mode == "planner_experimental":
        return True
    if operator_mode == "planner-only":
        return True
    enabled, cron_planner_only = _planner_orchestrator_flags(root)
    return enabled and cron_planner_only


def _expected_core_roles(root: Path) -> tuple[str, ...]:
    if _planner_only_mode(root):
        return ("planner",)
    return ("planner", "dev", "admin")


def _expected_tmux_sessions(root: Path) -> list[str]:
    return [f"codex_{role}_cron" for role in _expected_core_roles(root)]


def _quarantine_job_names(root: Path) -> list[str]:
    names: list[str] = []
    role_map = _read_json(root / ROLE_MAP_FILE)
    if isinstance(role_map, dict):
        for row in role_map.get("roles", []):
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or row.get("role") or "").strip()
            if name:
                names.append(name)
    if not names:
        names.extend(
            [
                "planner-tmux-loop",
                "analyst-tmux-loop",
                "architect-tmux-loop",
                "backend-engineer-tmux-loop",
                "frontend-engineer-tmux-loop",
                "data-analyst-tmux-loop",
                "infra-engineer-tmux-loop",
                "integrator-tmux-loop",
                "dev-tmux-loop",
                "tester-tmux-loop",
                "qa-tmux-loop",
                "clawsentinel",
            ]
        )
    names.extend(BASELINE_ADMIN_JOBS)
    names.extend(BASELINE_UTILITY_JOBS)
    names.extend(BASELINE_ADVISORY_JOBS)
    return list(dict.fromkeys(name for name in names if name))


def _openclaw_cron_jobs() -> list[dict[str, Any]]:
    for cmd in (
        ["openclaw", "cron", "list", "--all", "--json"],
        ["openclaw", "cron", "list", "--json"],
    ):
        try:
            cp = subprocess.run(cmd, text=True, capture_output=True, check=False, timeout=5)
        except Exception:
            continue
        if cp.returncode != 0:
            continue
        try:
            payload = json.loads(cp.stdout or "{}")
        except Exception:
            continue
        if isinstance(payload, dict):
            jobs = payload.get("jobs", [])
            if isinstance(jobs, list):
                return [job for job in jobs if isinstance(job, dict)]
        if isinstance(payload, list):
            return [job for job in payload if isinstance(job, dict)]
    return []


def _quarantined_jobs(root: Path) -> list[str]:
    if not _planner_only_mode(root):
        return []
    expected_names = set(_quarantine_job_names(root))
    out: list[str] = []
    for job in _openclaw_cron_jobs():
        name = str(job.get("name", "") or "").strip()
        if not name or name not in expected_names:
            continue
        if not bool(job.get("enabled", False)):
            out.append(name)
    return sorted(set(out))


def _runtime_state_detail(root: Path) -> dict[str, Any]:
    state = load_runtime_state(root)
    lifecycle = str(state.get("lifecycle", "running")).strip().lower() or "running"
    if lifecycle == "maintenance":
        lifecycle = "paused"
    return {
        "lifecycle": lifecycle,
        "reason": str(state.get("reason", "inferred") or "inferred").strip() or "inferred",
        "operator_mode": str(state.get("operator_mode", "") or "").strip(),
        "execution_mode": str(state.get("execution_mode", "") or "").strip(),
        "source": str(state.get("source", "inferred") or "inferred").strip() or "inferred",
        "updated_at": str(state.get("updated_at", "") or "").strip(),
        "state_file": str(state.get("path", "") or (runtime_state_root(root) / "runtime-state.json")),
    }


def _state_age_minutes(updated_at: object) -> int | None:
    token = str(updated_at or "").strip()
    if not token:
        return None
    try:
        if token.endswith("Z"):
            token = token[:-1] + "+00:00"
        dt = datetime.fromisoformat(token)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    age_min = (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 60.0
    return int(age_min) if age_min >= 0 else 0


def check_workspace_root(root: Path) -> CheckResult:
    exists = root.exists()
    writable = os.access(root, os.W_OK) if exists else False
    status = "ok" if exists and writable else "error"
    return CheckResult(
        status=status,
        detail={
            "canonical": str(root),
            "exists": exists,
            "writable": writable,
        },
    )


def check_scheduler_authority(root: Path) -> CheckResult:
    runtime_state = _runtime_state_detail(root)
    cron_has_vm_resume_guard = False
    cron_rc = 0
    cron_err = ""
    try:
        cp = subprocess.run(
            ["crontab", "-l"],
            text=True,
            capture_output=True,
            check=False,
            timeout=4,
        )
        cron_rc = cp.returncode
        cron_err = (cp.stderr or "").strip()
        if cp.returncode == 0:
            for line in cp.stdout.splitlines():
                token = line.strip()
                if not token or token.startswith("#"):
                    continue
                if "vm_resume_guard.sh" in token:
                    cron_has_vm_resume_guard = True
                    break
    except Exception as exc:
        cron_rc = 2
        cron_err = str(exc)
    cron_probe_blocked = _probe_blocked_message(cron_err)

    runtime_state_age_min = _state_age_minutes(runtime_state.get("updated_at"))
    runtime_state_fallback_ok = (
        cron_probe_blocked
        and str(runtime_state.get("execution_mode", "") or "").strip() != ""
        and (runtime_state_age_min is None or runtime_state_age_min <= 1440)
    )
    if runtime_state_fallback_ok:
        return CheckResult(
            status="ok",
            detail={
                "policy_target": "cron_only",
                "cron_has_vm_resume_guard": False,
                "cron_rc": cron_rc,
                "cron_stderr": cron_err[:200],
                "timer_enabled": False,
                "timer_active": False,
                "timer_probe": "probe_blocked",
                "scheduler_policy": "probe_blocked_runtime_state_fallback",
                "runtime_state_execution_mode": runtime_state.get("execution_mode", ""),
                "runtime_state_updated_at": runtime_state.get("updated_at", ""),
                "runtime_state_age_min": runtime_state_age_min,
            },
        )

    timer_enabled = False
    timer_active = False
    timer_probe = "systemctl_unavailable"
    if subprocess.run(["which", "systemctl"], capture_output=True, text=True, check=False).returncode == 0:
        env_ok = subprocess.run(
            ["systemctl", "--user", "show-environment"],
            capture_output=True,
            text=True,
            check=False,
            timeout=4,
        )
        if env_ok.returncode == 0:
            enabled_cp = subprocess.run(
                ["systemctl", "--user", "is-enabled", "vm-resume-guard.timer"],
                capture_output=True,
                text=True,
                check=False,
                timeout=4,
            )
            active_cp = subprocess.run(
                ["systemctl", "--user", "is-active", "vm-resume-guard.timer"],
                capture_output=True,
                text=True,
                check=False,
                timeout=4,
            )
            timer_probe = f"enabled={enabled_cp.stdout.strip() or enabled_cp.stderr.strip() or 'unknown'};" \
                         f"active={active_cp.stdout.strip() or active_cp.stderr.strip() or 'unknown'}"
            timer_enabled = enabled_cp.returncode == 0 and enabled_cp.stdout.strip() == "enabled"
            timer_active = active_cp.returncode == 0 and active_cp.stdout.strip() == "active"
        else:
            timer_probe = "systemd_user_unavailable"

    if cron_has_vm_resume_guard and timer_enabled:
        status = "degraded"
        policy = "dual_authority_detected"
    elif cron_has_vm_resume_guard and not timer_enabled:
        status = "ok"
        policy = "cron_only"
    elif (not cron_has_vm_resume_guard) and timer_enabled:
        status = "degraded"
        policy = "systemd_only_policy_violation"
    else:
        status = "error"
        policy = "no_scheduler_detected"

    return CheckResult(
        status=status,
        detail={
            "policy_target": "cron_only",
            "cron_has_vm_resume_guard": cron_has_vm_resume_guard,
            "cron_rc": cron_rc,
            "cron_stderr": cron_err[:200],
            "timer_enabled": timer_enabled,
            "timer_active": timer_active,
            "timer_probe": timer_probe,
            "scheduler_policy": policy,
        },
    )


def _read_recent_tick(root: Path, role: str, max_age_min: int = 90) -> dict[str, Any]:
    path = root / "logs-codex-runs" / "fc-ticks" / f"{role}.tick.log"
    if not path.exists():
        return {"path": str(path), "exists": False, "recent": False, "last_ts": "", "age_min": None}
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return {"path": str(path), "exists": True, "recent": False, "last_ts": "", "age_min": None}
    ts_pattern = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z)?)")
    last_ts = ""
    last_age_min: int | None = None
    for raw in reversed(lines[-400:]):
        if not any(marker in raw for marker in ("[START]", "[END]", "[SKIP]", "[BACKOFF]")):
            continue
        match = ts_pattern.search(raw)
        if not match:
            continue
        last_ts = match.group(1)
        last_age_min = _state_age_minutes(last_ts)
        break
    recent = last_age_min is not None and last_age_min <= max_age_min
    return {
        "path": str(path),
        "exists": True,
        "recent": recent,
        "last_ts": last_ts,
        "age_min": last_age_min,
    }


def _read_recent_planner_dispatch(root: Path, max_age_min: int = 90) -> dict[str, Any]:
    path = resolve_orchestrator_read_path(root, "planner-subagents-registry.json")
    data = _read_json(path)
    if not isinstance(data, dict):
        return {
            "path": str(path),
            "exists": path.exists(),
            "recent": False,
            "last_ts": "",
            "age_min": None,
            "active_count": 0,
        }
    subagents = data.get("subagents", [])
    if not isinstance(subagents, list):
        subagents = []
    latest_ts = str(data.get("updated_at", "") or "").strip()
    for item in subagents:
        if not isinstance(item, dict):
            continue
        for key in ("last_update_at", "merged_at", "created_at"):
            token = str(item.get(key, "") or "").strip()
            if token and (not latest_ts or (_state_age_minutes(token) or 10**9) < (_state_age_minutes(latest_ts) or 10**9)):
                latest_ts = token
                break
    age_min = _state_age_minutes(latest_ts)
    active_count = sum(1 for item in subagents if isinstance(item, dict) and str(item.get("status", "")).strip().lower() == "running")
    recent = age_min is not None and age_min <= max_age_min and (active_count > 0 or bool(subagents))
    return {
        "path": str(path),
        "exists": path.exists(),
        "recent": recent,
        "last_ts": latest_ts,
        "age_min": age_min,
        "active_count": active_count,
    }


def check_sessions(root: Path) -> CheckResult:
    runtime_state = _runtime_state_detail(root)
    runtime_paused = runtime_state.get("lifecycle") == "paused"
    cmd = ["tmux", "list-sessions", "-F", "#{session_name}"]
    sessions: list[str] = []
    rc = 0
    err = ""
    try:
        cp = subprocess.run(cmd, text=True, capture_output=True, check=False, timeout=4)
        rc = cp.returncode
        sessions = [line.strip() for line in cp.stdout.splitlines() if line.strip()]
        err = (cp.stderr or "").strip()
    except Exception as exc:
        rc = 2
        err = str(exc)
    expected = _expected_core_roles(root)
    expected_sessions = _expected_tmux_sessions(root)
    expected_session_set = set(expected_sessions)
    orphans = [name for name in sessions if name.startswith("codex_") and name not in expected_session_set]
    quarantined_jobs = _quarantined_jobs(root)
    probe_blocked = _probe_blocked_message(err)
    if probe_blocked and not runtime_paused:
        tick_fallback = {role: _read_recent_tick(root, role) for role in expected}
        planner_dispatch_fallback = _read_recent_planner_dispatch(root) if expected == ("planner",) else {}
        missing: list[str] = []
        found_by_role: dict[str, str] = {}
        for role, item in tick_fallback.items():
            if bool(item.get("recent")):
                found_by_role[role] = f"recent_tick:{item.get('last_ts', '')}"
                continue
            if role == "planner" and bool(planner_dispatch_fallback.get("recent")):
                found_by_role[role] = f"planner_dispatch:{planner_dispatch_fallback.get('last_ts', '')}"
                continue
            missing.append(role)
        status = "ok" if not missing else "degraded"
        return CheckResult(
            status=status,
            detail={
                "rc": rc,
                "sessions": sessions[:60],
                "expected": expected_sessions,
                "expected_sessions": expected_sessions,
                "expected_core": list(expected),
                "missing_core": missing,
                "missing_core_raw": list(expected),
                "found_core": found_by_role,
                "orphans": orphans[:60],
                "quarantined_jobs": quarantined_jobs[:60],
                "scheduler_inventory_mode": "quarantine" if _planner_only_mode(root) else "legacy_compatible",
                "execution_mode": "planner_experimental" if expected == ("planner",) else "parallel_roles",
                "runtime_lifecycle": runtime_state.get("lifecycle", "running"),
                "advisory_optional": "scrum_master",
                "stderr": err[:300],
                "probe_blocked": True,
                "fallback_source": "fc_ticks",
                "tick_fallback": tick_fallback,
                "planner_dispatch_fallback": planner_dispatch_fallback,
            },
        )
    found_by_role: dict[str, str] = {}
    for role in expected:
        for name in sessions:
            token = name.lower()
            if token == role or f"_{role}_" in token or token.endswith(f"_{role}") or token.startswith(f"{role}_"):
                found_by_role[role] = name
                break
    missing = [name for name in expected if name not in found_by_role]
    raw_missing = list(missing)
    if runtime_paused:
        missing = []
    matched_sessions = set(found_by_role.values())
    orphans = [name for name in sessions if name not in matched_sessions and name not in expected_session_set]
    status = "ok" if (runtime_paused or (rc == 0 and not missing)) else "degraded"
    return CheckResult(
        status=status,
        detail={
            "rc": rc,
            "sessions": sessions[:60],
            "expected": expected_sessions,
            "expected_sessions": expected_sessions,
            "expected_core": list(expected),
            "missing_core": missing,
            "missing_core_raw": raw_missing,
            "found_core": found_by_role,
            "orphans": orphans[:60],
            "quarantined_jobs": quarantined_jobs[:60],
            "scheduler_inventory_mode": "quarantine" if _planner_only_mode(root) else "legacy_compatible",
            "execution_mode": "planner_experimental" if expected == ("planner",) else "parallel_roles",
            "runtime_lifecycle": runtime_state.get("lifecycle", "running"),
            "advisory_optional": "scrum_master",
            "stderr": err[:300],
        },
    )


def _stale_lock_entries(path: Path, ttl_seconds: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    stale: list[dict[str, Any]] = []
    now = time.time()
    for p in sorted(path.glob("*.meta")):
        age = int(max(0, now - p.stat().st_mtime))
        if age > ttl_seconds:
            stale.append({"file": str(p), "age_s": age})
    return stale


def check_locks(root: Path, state_dir: Path) -> CheckResult:
    lock_dir = Path("/tmp/fc-agent-locks")
    stale_tick = _stale_lock_entries(lock_dir, ttl_seconds=900)
    stale_state = _stale_lock_entries(state_dir, ttl_seconds=900)
    status = "ok" if not stale_tick and not stale_state else "degraded"
    return CheckResult(
        status=status,
        detail={
            "tick_lock_dir": str(lock_dir),
            "state_dir": str(state_dir),
            "stale_tick_locks": stale_tick[:40],
            "stale_state_locks": stale_state[:40],
            "stale_total": len(stale_tick) + len(stale_state),
        },
    )


def _count_states(items: list[dict], key: str = "state") -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        token = str(item.get(key, "")).strip().upper() or "UNKNOWN"
        counts[token] = counts.get(token, 0) + 1
    return counts


def _normalize_batch_state(token: str) -> str:
    state = str(token or "").strip().upper()
    if state == "CLOSED":
        return "DONE"
    if state in {"READY_PLANNER", "READY_DEV"}:
        return "READY"
    return state or "UNKNOWN"


def _derive_stream_state(states: set[str]) -> str:
    # Priority order mirrors orchestration execution semantics.
    if "IN_PROGRESS" in states:
        return "IN_PROGRESS"
    if "READY_DEV" in states or "READY" in states:
        return "READY"
    if "WAITING_DEP" in states:
        return "WAITING_DEP"
    if "DONE" in states:
        return "DONE"
    if "CLOSED" in states:
        return "DONE"
    if states:
        return sorted(states)[0]
    return "UNKNOWN"


def _batch_prefix(task_id: str) -> str:
    raw = str(task_id or "").strip()
    m = re.match(r"^(BATCH-\d{2})\b", raw)
    if m:
        return m.group(1)
    parts = raw.split("-")
    if len(parts) >= 2 and parts[0] == "BATCH":
        return "-".join(parts[:2])
    return ""


def _states_equivalent(queue_state: str, workboard_state: str) -> bool:
    q = _normalize_batch_state(queue_state)
    w = _normalize_batch_state(workboard_state)
    if q == w:
        return True
    # Queue keeps long-horizon backlog as PLANNED while workboard exposes blocked lanes as WAITING_DEP.
    if q == "PLANNED" and w in {"WAITING_DEP", "BACKLOG"}:
        return True
    # Transitional state: stream is active, next task already READY but not yet claimed.
    if q == "IN_PROGRESS" and w == "READY":
        return True
    if q == "READY" and w == "IN_PROGRESS":
        return True
    return False


def check_queue_workboard(root: Path) -> CheckResult:
    queue_file = resolve_orchestrator_read_path(root, "priority-queue.json")
    workboard_file = resolve_orchestrator_read_path(root, "parallel-workstreams.json")
    queue_obj = _read_json(queue_file) or {}
    wb_obj = _read_json(workboard_file) or {}
    queue_items = queue_obj.get("items", []) if isinstance(queue_obj, dict) else []
    wb_tasks = wb_obj.get("tasks", []) if isinstance(wb_obj, dict) else []
    queue_states = _count_states(queue_items, "state")
    wb_states = _count_states(wb_tasks, "state")

    mismatch: list[str] = []
    queue_batches: dict[str, str] = {}
    queue_items_by_id: dict[str, dict] = {}
    for item in queue_items:
        if not isinstance(item, dict):
            continue
        bid = str(item.get("id", "")).strip()
        if not bid:
            continue
        queue_batches[bid] = _normalize_batch_state(item.get("state", ""))
        queue_items_by_id[bid] = item
    task_batches_raw: dict[str, set[str]] = {}
    task_rows_by_stream: dict[str, list[dict]] = {}
    for task in wb_tasks:
        if not isinstance(task, dict):
            continue
        stream = str(task.get("stream_id", "")).strip() or _batch_prefix(task.get("id", ""))
        if not stream:
            continue
        state = _normalize_batch_state(task.get("state", ""))
        task_batches_raw.setdefault(stream, set()).add(state)
        task_rows_by_stream.setdefault(stream, []).append(task)
    task_batches = {stream: _derive_stream_state(states) for stream, states in task_batches_raw.items()}

    queue_only: list[str] = []
    workboard_only: list[str] = []
    state_mismatch: list[str] = []
    mismatch_age_candidates: list[int] = []

    def _parse_iso_epoch(raw: str) -> int | None:
        text = str(raw or "").strip()
        if not text:
            return None
        try:
            return int(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp())
        except Exception:
            return None

    def _register_age_candidates(batch_id: str) -> None:
        q_item = queue_items_by_id.get(batch_id, {})
        q_epoch = _parse_iso_epoch(str(q_item.get("updated_at", "")).strip() or str(q_item.get("created_at", "")).strip())
        if q_epoch is not None:
            mismatch_age_candidates.append(q_epoch)
        for row in task_rows_by_stream.get(batch_id, []):
            t_epoch = _parse_iso_epoch(str(row.get("updated_at", "")).strip() or str(row.get("created_at", "")).strip())
            if t_epoch is not None:
                mismatch_age_candidates.append(t_epoch)

    for batch_id, queue_state in queue_batches.items():
        wb_state = task_batches.get(batch_id)
        if wb_state is None:
            if queue_state not in {"WAITING_DEP", "PLANNED", "READY_FOR_PARALLEL_DISPATCH"}:
                mismatch.append(f"{batch_id}:queue={queue_state}:workboard=MISSING")
                queue_only.append(batch_id)
                _register_age_candidates(batch_id)
            continue
        if not _states_equivalent(queue_state, wb_state):
            mismatch.append(f"{batch_id}:queue={queue_state}:workboard={wb_state}")
            state_mismatch.append(batch_id)
            _register_age_candidates(batch_id)

    for stream_id in task_batches.keys():
        if stream_id not in queue_batches:
            workboard_only.append(stream_id)
            mismatch.append(f"{stream_id}:queue=MISSING:workboard={task_batches.get(stream_id, 'UNKNOWN')}")
            _register_age_candidates(stream_id)

    oldest_mismatch_age_s = -1
    if mismatch_age_candidates:
        now_epoch = int(datetime.now(timezone.utc).timestamp())
        oldest_epoch = min(mismatch_age_candidates)
        oldest_mismatch_age_s = max(0, now_epoch - oldest_epoch)

    mismatch_count = len(queue_only) + len(workboard_only) + len(state_mismatch)

    status = "ok"
    if not queue_file.exists() or not workboard_file.exists():
        status = "error"
    elif mismatch_count > 0:
        status = "degraded"
    return CheckResult(
        status=status,
        detail={
            "queue_file": str(queue_file),
            "workboard_file": str(workboard_file),
            "queue_exists": queue_file.exists(),
            "workboard_exists": workboard_file.exists(),
            "queue_total": len(queue_items),
            "workboard_total": len(wb_tasks),
            "queue_states": queue_states,
            "workboard_states": wb_states,
            "mismatch_count": mismatch_count,
            "queue_only": queue_only[:80],
            "workboard_only": workboard_only[:80],
            "state_mismatch": state_mismatch[:80],
            "oldest_mismatch_age_s": oldest_mismatch_age_s,
            "mismatch": mismatch[:60],
        },
    )


def _probe_json(url: str, timeout_s: float) -> tuple[bool, int, str]:
    req = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            status = int(getattr(resp, "status", 0) or 0)
            body = resp.read(256).decode("utf-8", errors="ignore")
            return status == 200, status, body[:200]
    except Exception as exc:
        return False, 0, str(exc)[:200]


def _port_from_base(url: str) -> int:
    parsed = urlparse(url)
    if parsed.port is not None:
        return int(parsed.port)
    if parsed.scheme == "https":
        return 443
    return 80


def _listening_ports() -> set[int]:
    try:
        cp = subprocess.run(
            ["ss", "-ltn"],
            text=True,
            capture_output=True,
            check=False,
            timeout=3,
        )
    except Exception:
        return set()
    if cp.returncode != 0 and not (cp.stdout or "").strip():
        return set()
    ports: set[int] = set()
    for raw in (cp.stdout or "").splitlines():
        line = raw.strip()
        if not line or "LISTEN" not in line:
            continue
        match = re.search(r":(\d+)\s", line)
        if not match:
            continue
        try:
            ports.add(int(match.group(1)))
        except Exception:
            continue
    return ports


def check_providers(root: Path, api_base: str, monitor_base: str, state_dir: Path) -> CheckResult:
    ok_api, api_status, api_body = _probe_json(f"{api_base.rstrip('/')}/api/health", timeout_s=2.5)
    # Avoid recursive self-probe deadlocks: /api/status runs doctor_snapshot.
    ok_monitor, mon_status, mon_body = _probe_json(f"{monitor_base.rstrip('/')}/", timeout_s=2.5)
    listening_ports = _listening_ports()
    api_port = _port_from_base(api_base)
    monitor_port = _port_from_base(monitor_base)
    api_listener_ok = api_port in listening_ports
    monitor_listener_ok = monitor_port in listening_ports
    api_probe_blocked = _probe_blocked_message(api_body)
    monitor_probe_blocked = _probe_blocked_message(mon_body)
    api_ok_effective = ok_api or (api_probe_blocked and api_listener_ok)
    monitor_ok_effective = ok_monitor or (monitor_probe_blocked and monitor_listener_ok)
    cache_files = [
        state_dir / "codex.rate_limit_gate_cache",
        state_dir / "qwen.rate_limit_gate_cache",
    ]
    caches = [{"path": str(p), "exists": p.exists()} for p in cache_files]
    status = "ok" if api_ok_effective and monitor_ok_effective else "degraded"
    return CheckResult(
        status=status,
        detail={
            "api_base": api_base,
            "monitor_base": monitor_base,
            "api_health_ok": ok_api,
            "api_reachable_effective": api_ok_effective,
            "api_status": api_status,
            "api_probe": api_body,
            "api_probe_blocked": api_probe_blocked,
            "api_listener_ok": api_listener_ok,
            "monitor_status_ok": ok_monitor,
            "monitor_reachable_effective": monitor_ok_effective,
            "monitor_status_code": mon_status,
            "monitor_probe": mon_body,
            "monitor_probe_blocked": monitor_probe_blocked,
            "monitor_listener_ok": monitor_listener_ok,
            "rate_limit_caches": caches,
        },
    )


def _load_product_priority_guard(root: Path):
    module_path = root / "platform" / "automation" / "product_priority_guard.py"
    if not module_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("fc_product_priority_guard_doctor", module_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_planner_dispatch_metrics(root: Path):
    module_path = root / "platform" / "automation" / "planner_dispatch_metrics.py"
    if not module_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("fc_planner_dispatch_metrics_doctor", module_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_product_value(root: Path, api_base: str) -> CheckResult:
    module = _load_product_priority_guard(root)
    if module is None or not hasattr(module, "build_product_value_metrics"):
        return CheckResult(status="error", detail={"error": "product_priority_guard_missing"})
    try:
        metrics = module.build_product_value_metrics(root, api_base_url=api_base, timeout_s=0.6)
    except Exception as exc:
        return CheckResult(status="error", detail={"error": str(exc)})
    guard = metrics.get("priority_guard", {}) if isinstance(metrics, dict) else {}
    copilot = metrics.get("copilot", {}) if isinstance(metrics, dict) else {}
    forecasts = metrics.get("forecasts", {}) if isinstance(metrics, dict) else {}
    status = "ok"
    if guard.get("status") == "blocked":
        status = "degraded"
    return CheckResult(
        status=status,
        detail={
            "guard_status": guard.get("status", "unknown"),
            "p0_broken": bool(guard.get("p0_broken", False)),
            "blocked_reasons": guard.get("blocked_reasons", []),
            "allow_orchestration_autobatch": bool(guard.get("allow_orchestration_autobatch", True)),
            "copilot_status": copilot.get("status", "unknown"),
            "forecasts_status": forecasts.get("status", "unknown"),
            "metrics": metrics,
        },
    )


def check_delivery_integrity(root: Path) -> CheckResult:
    module = _load_product_priority_guard(root)
    if module is None or not hasattr(module, "build_delivery_integrity_metrics"):
        return CheckResult(status="error", detail={"error": "product_priority_guard_missing"})
    try:
        metrics = module.build_delivery_integrity_metrics(root, window_hours=24)
    except Exception as exc:
        return CheckResult(status="error", detail={"error": str(exc)})
    status = "ok" if str(metrics.get("status", "unknown")) == "ok" else "degraded"
    return CheckResult(status=status, detail=metrics)


def check_delivery_future_integrity(root: Path) -> CheckResult:
    module = _load_product_priority_guard(root)
    if module is None or not hasattr(module, "build_delivery_control_metrics"):
        return CheckResult(status="error", detail={"error": "product_priority_guard_missing"})
    try:
        metrics = module.build_delivery_control_metrics(root, window_hours=24)
    except Exception as exc:
        return CheckResult(status="error", detail={"error": str(exc)})
    status = "ok" if str(metrics.get("future_status", "unknown")) == "ok" else "degraded"
    return CheckResult(status=status, detail=metrics.get("future_delivery_integrity", metrics))


def check_browser_proof_pipeline(root: Path) -> CheckResult:
    module = _load_product_priority_guard(root)
    if module is None or not hasattr(module, "build_delivery_control_metrics"):
        return CheckResult(status="error", detail={"error": "product_priority_guard_missing"})
    try:
        metrics = module.build_delivery_control_metrics(root, window_hours=24)
    except Exception as exc:
        return CheckResult(status="error", detail={"error": str(exc)})
    detail = metrics.get("browser_proof_pipeline", {}) if isinstance(metrics, dict) else {}
    status = "ok" if str(detail.get("status", "unknown")) == "ok" else "degraded"
    return CheckResult(status=status, detail=detail)


def check_suspicious_completions(root: Path) -> CheckResult:
    module = _load_product_priority_guard(root)
    if module is None or not hasattr(module, "build_delivery_control_metrics"):
        return CheckResult(status="error", detail={"error": "product_priority_guard_missing"})
    try:
        metrics = module.build_delivery_control_metrics(root, window_hours=24)
    except Exception as exc:
        return CheckResult(status="error", detail={"error": str(exc)})
    detail = metrics.get("suspicious_completions", {}) if isinstance(metrics, dict) else {}
    status = "ok" if int(detail.get("count", 0) or 0) == 0 else "degraded"
    return CheckResult(status=status, detail=detail)


def check_qa_review_pipeline(root: Path) -> CheckResult:
    module = _load_product_priority_guard(root)
    if module is None or not hasattr(module, "build_delivery_control_metrics"):
        return CheckResult(status="error", detail={"error": "product_priority_guard_missing"})
    try:
        metrics = module.build_delivery_control_metrics(root, window_hours=24)
    except Exception as exc:
        return CheckResult(status="error", detail={"error": str(exc)})
    detail = metrics.get("qa_review_pipeline", {}) if isinstance(metrics, dict) else {}
    status = "ok" if str(detail.get("status", "unknown")) == "ok" else "degraded"
    return CheckResult(status=status, detail=detail)


def check_capability_stall_recovery(root: Path) -> CheckResult:
    module = _load_product_priority_guard(root)
    if module is None or not hasattr(module, "build_delivery_control_metrics"):
        return CheckResult(status="error", detail={"error": "product_priority_guard_missing"})
    try:
        metrics = module.build_delivery_control_metrics(root, window_hours=24)
    except Exception as exc:
        return CheckResult(status="error", detail={"error": str(exc)})
    detail = metrics.get("capability_stall_summary", {}) if isinstance(metrics, dict) else {}
    items = detail.get("items", []) if isinstance(detail, dict) else []
    transient = bool(items) and all(
        isinstance(item, dict)
        and not bool(item.get("takeover_required"))
        and not bool(item.get("recovery_required"))
        and int(item.get("timeout_streak", 0) or 0) <= 1
        and int(item.get("dev_no_progress_streak", 0) or 0) <= 1
        and int(item.get("dev_orphaned_streak", 0) or 0) == 0
        and int(item.get("invalid_result_streak", 0) or 0) == 0
        for item in items
    )
    recovering = bool(items) and all(
        bool(item.get("takeover_required")) or bool(item.get("recovery_required"))
        for item in items
        if isinstance(item, dict)
    )
    status = "ok" if int(detail.get("count", 0) or 0) == 0 or recovering or transient else "degraded"
    if isinstance(detail, dict) and (recovering or transient):
        detail = dict(detail)
        detail["recovery_mode"] = (
            "planner_takeover_or_capability_recovery_active"
            if recovering
            else "transient_capability_requeue_active"
        )
    return CheckResult(status=status, detail=detail)


def check_historical_delivery_debt(root: Path) -> CheckResult:
    module = _load_product_priority_guard(root)
    if module is None or not hasattr(module, "build_delivery_control_metrics"):
        return CheckResult(status="error", detail={"error": "product_priority_guard_missing"})
    try:
        metrics = module.build_delivery_control_metrics(root, window_hours=24)
    except Exception as exc:
        return CheckResult(status="error", detail={"error": str(exc)})
    detail = metrics.get("historical_debt", {}) if isinstance(metrics, dict) else {}
    status = "ok"
    if isinstance(detail, dict):
        detail = dict(detail)
        detail["advisory"] = int(detail.get("count", 0) or 0) > 0
    return CheckResult(status=status, detail=detail)


def check_planner_dispatch(root: Path) -> CheckResult:
    module = _load_planner_dispatch_metrics(root)
    if module is None or not hasattr(module, "build_planner_dispatch_metrics"):
        return CheckResult(status="error", detail={"error": "planner_dispatch_metrics_missing"})
    try:
        metrics = module.build_planner_dispatch_metrics(root, recent_limit=12)
    except Exception as exc:
        return CheckResult(status="error", detail={"error": str(exc)})
    status = "ok" if str(metrics.get("status", "unknown")) == "ok" else "degraded"
    return CheckResult(status=status, detail=metrics)


def check_capability_result_integrity(root: Path) -> CheckResult:
    module = _load_planner_dispatch_metrics(root)
    if module is None or not hasattr(module, "build_planner_dispatch_metrics"):
        return CheckResult(status="error", detail={"error": "planner_dispatch_metrics_missing"})
    try:
        metrics = module.build_planner_dispatch_metrics(root, recent_limit=12)
    except Exception as exc:
        return CheckResult(status="error", detail={"error": str(exc)})
    invalid_count = int(metrics.get("recent_invalid_result_count", 0) or 0)
    timeout_count = int(metrics.get("recent_timeout_like_count", 0) or 0)
    no_progress_count = int(metrics.get("dev_no_progress_count", 0) or 0)
    orphaned_count = int(metrics.get("dev_orphaned_count", 0) or 0)
    recovering = bool(metrics.get("recovering"))
    status = "ok"
    if (invalid_count > 0 or orphaned_count > 0) and not recovering:
        status = "degraded"
    detail = {
        "recent_invalid_result_count": invalid_count,
        "recent_timeout_like_count": timeout_count,
        "dev_no_progress_count": no_progress_count,
        "dev_orphaned_count": orphaned_count,
        "recovering": recovering,
        "latest_failure_mode": metrics.get("latest_failure_mode", "unknown"),
    }
    return CheckResult(status=status, detail=detail)


def check_dev_execution_model(root: Path) -> CheckResult:
    module = _load_planner_dispatch_metrics(root)
    if module is None or not hasattr(module, "build_planner_dispatch_metrics"):
        return CheckResult(status="error", detail={"error": "planner_dispatch_metrics_missing"})
    try:
        metrics = module.build_planner_dispatch_metrics(root, recent_limit=12)
    except Exception as exc:
        return CheckResult(status="error", detail={"error": str(exc)})
    detail = {
        "long_running_dev_count": int(metrics.get("long_running_dev_count", 0) or 0),
        "dev_no_progress_count": int(metrics.get("dev_no_progress_count", 0) or 0),
        "dev_orphaned_count": int(metrics.get("dev_orphaned_count", 0) or 0),
        "dev_invalid_result_count": int(metrics.get("dev_invalid_result_count", 0) or 0),
    }
    status = "ok" if detail["dev_orphaned_count"] == 0 else "degraded"
    return CheckResult(status=status, detail=detail)


def check_dev_progress_integrity(root: Path) -> CheckResult:
    module = _load_planner_dispatch_metrics(root)
    if module is None or not hasattr(module, "build_planner_dispatch_metrics"):
        return CheckResult(status="error", detail={"error": "planner_dispatch_metrics_missing"})
    try:
        metrics = module.build_planner_dispatch_metrics(root, recent_limit=12)
    except Exception as exc:
        return CheckResult(status="error", detail={"error": str(exc)})
    no_progress_count = int(metrics.get("dev_no_progress_count", 0) or 0)
    recovering = bool(metrics.get("recovering"))
    detail = {
        "dev_no_progress_count": no_progress_count,
        "long_running_dev_count": int(metrics.get("long_running_dev_count", 0) or 0),
        "recovering": recovering,
    }
    status = "ok" if no_progress_count == 0 or recovering else "degraded"
    return CheckResult(status=status, detail=detail)


def check_dev_orphan_recovery(root: Path) -> CheckResult:
    module = _load_planner_dispatch_metrics(root)
    if module is None or not hasattr(module, "build_planner_dispatch_metrics"):
        return CheckResult(status="error", detail={"error": "planner_dispatch_metrics_missing"})
    try:
        metrics = module.build_planner_dispatch_metrics(root, recent_limit=12)
    except Exception as exc:
        return CheckResult(status="error", detail={"error": str(exc)})
    orphaned_count = int(metrics.get("dev_orphaned_count", 0) or 0)
    recovering = bool(metrics.get("recovering"))
    detail = {
        "dev_orphaned_count": orphaned_count,
        "recovering": recovering,
    }
    status = "ok" if orphaned_count == 0 or recovering else "degraded"
    return CheckResult(status=status, detail=detail)


def check_planner_takeover_recovery(root: Path) -> CheckResult:
    module = _load_product_priority_guard(root)
    if module is None or not hasattr(module, "build_delivery_control_metrics"):
        return CheckResult(status="error", detail={"error": "product_priority_guard_missing"})
    try:
        metrics = module.build_delivery_control_metrics(root, window_hours=24)
    except Exception as exc:
        return CheckResult(status="error", detail={"error": str(exc)})
    detail = metrics.get("capability_stall_summary", {}) if isinstance(metrics, dict) else {}
    items = detail.get("items", []) if isinstance(detail, dict) else []
    takeover_items = [
        item for item in items
        if isinstance(item, dict) and (bool(item.get("takeover_required")) or bool(item.get("recovery_required")))
    ]
    transient = bool(items) and all(
        isinstance(item, dict)
        and not bool(item.get("takeover_required"))
        and not bool(item.get("recovery_required"))
        and int(item.get("timeout_streak", 0) or 0) <= 1
        and int(item.get("dev_no_progress_streak", 0) or 0) <= 1
        and int(item.get("dev_orphaned_streak", 0) or 0) == 0
        and int(item.get("invalid_result_streak", 0) or 0) == 0
        for item in items
    )
    status = "ok" if not items or len(takeover_items) == len(items) or transient else "degraded"
    if isinstance(detail, dict):
        detail = dict(detail)
        detail["takeover_or_recovery_items"] = len(takeover_items)
        if transient:
            detail["recovery_mode"] = "transient_capability_requeue_active"
    return CheckResult(status=status, detail=detail)


def build_payload(root: Path, api_base: str, monitor_base: str) -> tuple[dict[str, Any], int]:
    start = time.time()
    state_dir = Path(os.environ.get("FC_ROLE_STATE_DIR", str(Path.home() / ".openclaw/cron/role-state"))).expanduser()
    runtime_state = _runtime_state_detail(root)
    checks = {
        "workspace_root": check_workspace_root(root),
        "runtime_state": CheckResult(status="ok", detail=runtime_state),
        "scheduler_authority": check_scheduler_authority(root),
        "sessions": check_sessions(root),
        "locks": check_locks(root, state_dir),
        "queue_workboard": check_queue_workboard(root),
        "providers": check_providers(root, api_base=api_base, monitor_base=monitor_base, state_dir=state_dir),
        "product_value": check_product_value(root, api_base=api_base),
        "delivery_integrity": check_delivery_integrity(root),
        "delivery_future_integrity": check_delivery_future_integrity(root),
        "browser_proof_pipeline": check_browser_proof_pipeline(root),
        "suspicious_completions": check_suspicious_completions(root),
        "qa_review_pipeline": check_qa_review_pipeline(root),
        "dev_execution_model": check_dev_execution_model(root),
        "dev_progress_integrity": check_dev_progress_integrity(root),
        "dev_orphan_recovery": check_dev_orphan_recovery(root),
        "capability_stall_recovery": check_capability_stall_recovery(root),
        "capability_result_integrity": check_capability_result_integrity(root),
        "planner_takeover_recovery": check_planner_takeover_recovery(root),
        "historical_delivery_debt": check_historical_delivery_debt(root),
        "planner_dispatch": check_planner_dispatch(root),
    }
    runtime_paused = runtime_state.get("lifecycle") == "paused"
    advisory_checks = {"planner_dispatch", "delivery_integrity", "historical_delivery_debt"}
    effective_checks = {
        name: check
        for name, check in checks.items()
        if name not in advisory_checks and not (runtime_paused and name in {"scheduler_authority", "sessions"})
    }
    statuses = [check.status for check in effective_checks.values()]
    if "error" in statuses:
        status = "error"
        code = 2
    elif "degraded" in statuses:
        status = "degraded"
        code = 1
    else:
        status = "ok"
        code = 0
    payload = {
        "status": status,
        "generated_at": now_iso(),
        "checks": {name: {"status": cr.status, **cr.detail} for name, cr in checks.items()},
        "meta": {
            "schema_version": "doctor.v1",
            "duration_ms": int((time.time() - start) * 1000),
        },
    }
    return payload, code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Finance Copilot doctor.")
    parser.add_argument("--root", default="")
    parser.add_argument("--api-base-url", default=os.environ.get("FC_API_BASE_URL", "http://127.0.0.1:8050"))
    parser.add_argument("--monitor-base-url", default=os.environ.get("FC_MONITOR_BASE_URL", "http://127.0.0.1:7779"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser().resolve() if args.root else Path(__file__).resolve().parents[2]
    payload, code = build_payload(root, api_base=args.api_base_url, monitor_base=args.monitor_base_url)
    if args.json:
        print(json.dumps(payload, ensure_ascii=True))
    else:
        print(json.dumps(payload, ensure_ascii=True, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
