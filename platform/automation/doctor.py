#!/usr/bin/env python3
"""Unified orchestration doctor (stable JSON contract)."""

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

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from orchestrator_paths import load_runtime_state, resolve_orchestrator_read_path

CORE_ROLES = ("planner", "dev", "admin")


@dataclass
class RateLimitState:
    active: bool
    until_epoch: int
    remaining_s: int
    source: str


def _now_iso() -> str:
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
    return CORE_ROLES


def _runtime_state(root: Path) -> dict[str, Any]:
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
        "state_file": str(state.get("path", "") or ""),
    }


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default


def _tmux_sessions() -> list[str]:
    try:
        cp = subprocess.run(
            ["tmux", "list-sessions", "-F", "#{session_name}"],
            text=True,
            capture_output=True,
            check=False,
            timeout=4,
        )
    except Exception:
        return []
    if cp.returncode != 0:
        return []
    return [line.strip() for line in (cp.stdout or "").splitlines() if line.strip()]


def _expected_sessions() -> list[str]:
    return [f"codex_{role}_cron" for role in CORE_ROLES]


def _expected_sessions_for_root(root: Path) -> list[str]:
    return [f"codex_{role}_cron" for role in _expected_core_roles(root)]


def _lock_family_snapshot(state_dir: Path) -> dict[str, Any]:
    now_epoch = int(time.time())
    tick_dir = Path("/tmp/fc-agent-locks")

    def family(patterns: tuple[Path, ...], ttl_s: int) -> dict[str, Any]:
        files: list[Path] = []
        for pattern in patterns:
            files.extend(sorted(pattern.parent.glob(pattern.name)))
        stale: list[dict[str, Any]] = []
        for item in files:
            try:
                age = max(0, now_epoch - int(item.stat().st_mtime))
            except Exception:
                age = 0
            if age > ttl_s:
                stale.append({"path": str(item), "age_s": age})
        return {
            "count": len(files),
            "stale_count": len(stale),
            "stale": stale[:30],
        }

    return {
        "tick": family((tick_dir / "*.meta",), ttl_s=900),
        "run": family((state_dir / "*.run.lock.meta",), ttl_s=900),
        "memory": family((state_dir / "*.memory.lock.meta", state_dir / "*.memory.lock"), ttl_s=1800),
    }


def _queue_workboard_snapshot(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    queue_file = resolve_orchestrator_read_path(root, "priority-queue.json")
    workboard_file = resolve_orchestrator_read_path(root, "parallel-workstreams.json")
    queue_obj = _read_json(queue_file) or {}
    workboard_obj = _read_json(workboard_file) or {}

    queue_items = queue_obj.get("items", []) if isinstance(queue_obj, dict) else []
    wb_tasks = workboard_obj.get("tasks", []) if isinstance(workboard_obj, dict) else []

    queue_by_state: dict[str, int] = {}
    for item in queue_items:
        if not isinstance(item, dict):
            continue
        state = str(item.get("state", "UNKNOWN")).strip().upper() or "UNKNOWN"
        queue_by_state[state] = queue_by_state.get(state, 0) + 1

    wb_by_state: dict[str, int] = {}
    for task in wb_tasks:
        if not isinstance(task, dict):
            continue
        state = str(task.get("state", "UNKNOWN")).strip().upper() or "UNKNOWN"
        wb_by_state[state] = wb_by_state.get(state, 0) + 1

    queue_stream_state: dict[str, str] = {}
    for item in queue_items:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("id", "")).strip()
        if not sid:
            continue
        queue_stream_state[sid] = str(item.get("state", "")).strip().upper()

    wb_stream_states: dict[str, set[str]] = {}
    for task in wb_tasks:
        if not isinstance(task, dict):
            continue
        sid = str(task.get("stream_id", "")).strip()
        if not sid:
            continue
        st = str(task.get("state", "")).strip().upper() or "UNKNOWN"
        wb_stream_states.setdefault(sid, set()).add(st)

    def _norm_state(raw: str) -> str:
        token = str(raw or "").strip().upper()
        if token in {"READY", "READY_PLANNER"}:
            return "READY_PLANNER"
        return token

    def _derive_wb_stream_state(states: set[str]) -> str:
        norm_states = {_norm_state(s) for s in (states or set())}
        if "IN_PROGRESS" in norm_states or "REVIEW" in norm_states:
            return "IN_PROGRESS"
        if "READY_DEV" in norm_states:
            return "READY_DEV"
        if "READY_PLANNER" in norm_states:
            return "READY_PLANNER"
        if "WAITING_DEP" in norm_states:
            return "WAITING_DEP"
        if "PLANNED" in norm_states:
            return "PLANNED"
        if "BLOCKED" in norm_states:
            return "BLOCKED"
        if "DONE" in norm_states or "CLOSED" in norm_states:
            return "DONE"
        return next(iter(norm_states), "UNKNOWN")

    wb_stream_state: dict[str, str] = {sid: _derive_wb_stream_state(states) for sid, states in wb_stream_states.items()}

    mismatches: list[str] = []
    for sid, q_state in queue_stream_state.items():
        wb_state = wb_stream_state.get(sid)
        q_norm = _norm_state(q_state)
        wb_norm = _norm_state(wb_state)
        if wb_norm and wb_norm != q_norm:
            mismatches.append(f"{sid}:queue={q_state}:workboard={wb_state}")

    consistency_flags = {
        "queue_file_exists": queue_file.exists(),
        "workboard_file_exists": workboard_file.exists(),
        "queue_workboard_mismatch": bool(mismatches),
        "queue_ready_no_workboard_ready": queue_by_state.get("READY", 0) > 0 and wb_by_state.get("READY", 0) == 0,
    }

    queue_summary = {
        "source": str(queue_file),
        "exists": queue_file.exists(),
        "total": len(queue_items),
        "states": queue_by_state,
    }
    workboard_summary = {
        "source": str(workboard_file),
        "exists": workboard_file.exists(),
        "total": len(wb_tasks),
        "states": wb_by_state,
    }
    if mismatches:
        consistency_flags["mismatch_samples"] = mismatches[:20]
    return queue_summary, workboard_summary, consistency_flags


def _role_model_map(root: Path) -> dict[str, str]:
    candidates = [
        root / "platform" / "config" / "runner" / "runner_config.v1.yaml",
        root / "platform" / "automation" / "config" / "runner.v1.yaml",
    ]
    for candidate in candidates:
        obj = _read_json(candidate)
        if not isinstance(obj, dict):
            continue
        roles = obj.get("roles")
        if not isinstance(roles, dict):
            continue
        out: dict[str, str] = {}
        for role, payload in roles.items():
            if not isinstance(payload, dict):
                continue
            model = str(payload.get("model", "")).strip()
            if model:
                out[str(role)] = model
        if out:
            return out
    return {}


def _rate_limit_state(cache_file: Path) -> RateLimitState:
    if not cache_file.exists():
        return RateLimitState(False, 0, 0, str(cache_file))

    until_epoch = 0
    try:
        raw = cache_file.read_text(encoding="utf-8", errors="ignore").strip()
        until_epoch = _safe_int(raw.split("|")[0], 0)
    except Exception:
        until_epoch = 0

    remaining = max(0, until_epoch - int(time.time()))
    return RateLimitState(remaining > 0, until_epoch, remaining, str(cache_file))


def _load_product_priority_guard(root: Path):
    module_path = root / "platform" / "automation" / "product_priority_guard.py"
    if not module_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("fc_product_priority_guard_unified_doctor", module_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_payload(root: Path, state_dir: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    runtime_state = _runtime_state(root)

    root_resolved = str(root.resolve())
    root_writable = root.exists() and os.access(root, os.W_OK)
    if not root.exists():
        errors.append("workspace_root_missing")
    elif not root_writable:
        errors.append("workspace_root_not_writable")

    sessions_active = _tmux_sessions()
    sessions_expected = _expected_sessions_for_root(root)
    missing = [name for name in sessions_expected if name not in sessions_active]
    orphans = [name for name in sessions_active if name.startswith("codex_") and name not in sessions_expected]
    if missing and runtime_state.get("lifecycle") != "paused":
        warnings.append(f"missing_core_sessions:{','.join(missing)}")

    locks = _lock_family_snapshot(state_dir)
    for lock_kind in ("tick", "run", "memory"):
        if locks.get(lock_kind, {}).get("stale_count", 0) > 0:
            warnings.append(f"stale_{lock_kind}_locks")

    queue_summary, workboard_summary, consistency_flags = _queue_workboard_snapshot(root)
    if not consistency_flags.get("queue_file_exists"):
        errors.append("queue_file_missing")
    if not consistency_flags.get("workboard_file_exists"):
        errors.append("workboard_file_missing")
    if consistency_flags.get("queue_workboard_mismatch"):
        warnings.append("queue_workboard_mismatch")

    role_model_map = _role_model_map(root)
    codex_rl = _rate_limit_state(state_dir / "codex.rate_limit_gate_cache")
    qwen_rl = _rate_limit_state(state_dir / "qwen.rate_limit_gate_cache")
    if codex_rl.active:
        warnings.append("codex_rate_limit_active")
    if qwen_rl.active:
        warnings.append("qwen_rate_limit_active")

    product_value: dict[str, Any] = {}
    delivery_integrity: dict[str, Any] = {}
    guard_module = _load_product_priority_guard(root)
    if guard_module is not None:
        api_base = os.environ.get("FC_API_BASE_URL", "http://127.0.0.1:8050")
        try:
            product_value = guard_module.build_product_value_metrics(root, api_base_url=api_base, timeout_s=0.6)
            if (product_value.get("priority_guard") or {}).get("status") == "blocked":
                warnings.append("product_priority_guard_blocked")
        except Exception as exc:
            warnings.append("product_priority_guard_error")
            product_value = {"error": str(exc)}
        try:
            delivery_integrity = guard_module.build_delivery_integrity_metrics(root, window_hours=24)
            if str(delivery_integrity.get("status", "ok")) != "ok":
                warnings.append("delivery_integrity_degraded")
        except Exception as exc:
            warnings.append("delivery_integrity_error")
            delivery_integrity = {"error": str(exc)}

    if errors:
        verdict = "BLOCKED"
    else:
        stale_like = []
        if missing and runtime_state.get("lifecycle") != "paused":
            stale_like.append("missing_sessions")
        if consistency_flags.get("queue_workboard_mismatch"):
            stale_like.append("state_mismatch")
        if any(locks.get(k, {}).get("stale_count", 0) > 0 for k in ("tick", "run", "memory")):
            stale_like.append("stale_locks")

        if runtime_state.get("lifecycle") == "paused":
            non_pause_errors = list(errors)
            non_pause_warnings = [item for item in warnings if not item.startswith("missing_core_sessions:")]
            if non_pause_errors:
                verdict = "BLOCKED"
            elif non_pause_warnings:
                verdict = "DEGRADED"
            else:
                verdict = "OK"
        elif codex_rl.active or qwen_rl.active:
            verdict = "DEGRADED"
        elif stale_like:
            verdict = "STALE"
        else:
            verdict = "OK"

    return {
        "timestamp_utc": _now_iso(),
        "workspace": {
            "root_resolved": root_resolved,
            "root_writable": bool(root_writable),
        },
        "runtime_state": runtime_state,
        "sessions": {
            "expected": sessions_expected,
            "active": sessions_active,
            "orphans": orphans,
            "missing": [] if runtime_state.get("lifecycle") == "paused" else missing,
            "missing_raw": missing,
        },
        "locks": locks,
        "orchestrator": {
            "queue_summary": queue_summary,
            "workboard_summary": workboard_summary,
            "consistency_flags": consistency_flags,
        },
        "providers": {
            "role_model_map": role_model_map,
            "rate_limit": {
                "codex": {
                    "active": codex_rl.active,
                    "until_epoch": codex_rl.until_epoch,
                    "remaining_s": codex_rl.remaining_s,
                    "source": codex_rl.source,
                },
                "qwen": {
                    "active": qwen_rl.active,
                    "until_epoch": qwen_rl.until_epoch,
                    "remaining_s": qwen_rl.remaining_s,
                    "source": qwen_rl.source,
                },
            },
        },
        "product_value": product_value,
        "delivery_integrity": delivery_integrity,
        "verdict": verdict,
        "errors": errors,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Unified orchestration doctor")
    parser.add_argument("--root", default="")
    parser.add_argument("--json", action="store_true", default=False)
    parser.add_argument(
        "--state-dir",
        default=os.environ.get("FC_ROLE_STATE_DIR", str(Path.home() / ".openclaw/cron/role-state")),
    )
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser().resolve() if args.root else Path(__file__).resolve().parents[2]
    state_dir = Path(args.state_dir).expanduser().resolve()
    payload = build_payload(root, state_dir)

    if args.json:
        print(json.dumps(payload, ensure_ascii=True))
    else:
        print(json.dumps(payload, ensure_ascii=True, indent=2))

    verdict = str(payload.get("verdict", "BLOCKED")).upper()
    if verdict == "OK":
        return 0
    if verdict == "STALE":
        return 1
    if verdict == "DEGRADED":
        return 2
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
