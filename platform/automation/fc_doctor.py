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
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
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


def _expected_core_roles(root: Path) -> tuple[str, ...]:
    enabled, cron_planner_only = _planner_orchestrator_flags(root)
    if enabled and cron_planner_only:
        return ("planner",)
    return ("planner", "dev", "admin")


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
    status = "ok" if (runtime_paused or (rc == 0 and not missing)) else "degraded"
    return CheckResult(
        status=status,
        detail={
            "rc": rc,
            "sessions": sessions[:60],
            "expected_core": list(expected),
            "missing_core": missing,
            "missing_core_raw": raw_missing,
            "found_core": found_by_role,
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


def check_providers(root: Path, api_base: str, monitor_base: str, state_dir: Path) -> CheckResult:
    ok_api, api_status, api_body = _probe_json(f"{api_base.rstrip('/')}/api/health", timeout_s=2.5)
    # Avoid recursive self-probe deadlocks: /api/status runs doctor_snapshot.
    ok_monitor, mon_status, mon_body = _probe_json(f"{monitor_base.rstrip('/')}/", timeout_s=2.5)
    cache_files = [
        state_dir / "codex.rate_limit_gate_cache",
        state_dir / "qwen.rate_limit_gate_cache",
    ]
    caches = [{"path": str(p), "exists": p.exists()} for p in cache_files]
    status = "ok" if ok_api and ok_monitor else "degraded"
    return CheckResult(
        status=status,
        detail={
            "api_base": api_base,
            "monitor_base": monitor_base,
            "api_health_ok": ok_api,
            "api_status": api_status,
            "api_probe": api_body,
            "monitor_status_ok": ok_monitor,
            "monitor_status_code": mon_status,
            "monitor_probe": mon_body,
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
    }
    runtime_paused = runtime_state.get("lifecycle") == "paused"
    effective_checks = {
        name: check
        for name, check in checks.items()
        if not (runtime_paused and name in {"scheduler_authority", "sessions"})
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
