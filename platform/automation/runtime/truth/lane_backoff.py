from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator_paths import (
    load_runtime_state,
    persist_runtime_state,
    resolve_orchestrator_read_path,
    write_orchestrator_json,
)


CONTINUOUS_LANES = ("planner", "app-dev", "verifier")
LANE_ALIAS_MAP = {
    "planner": "planner",
    "planner_architect_orchestrator": "planner",
    "vision-architect-tasks-planner": "planner",
    "vision_architect_tasks_planner": "planner",
    "app-dev": "app-dev",
    "app_dev": "app-dev",
    "dev": "app-dev",
    "backend_engineer": "app-dev",
    "frontend_engineer": "app-dev",
    "integrator": "app-dev",
    "data_analyst": "app-dev",
    "verifier": "verifier",
    "qa": "verifier",
    "tester": "verifier",
}
LANE_BACKOFF_THRESHOLD = 3


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_lane_name(role: str) -> str:
    token = str(role or "").strip().replace("_", "-").lower()
    return LANE_ALIAS_MAP.get(token, token)


def _default_root() -> Path:
    return Path.cwd()


def _resolve_root_and_role(root_or_role: Path | str | None, role: str | None) -> tuple[Path, str]:
    if role is None:
        return _default_root(), canonical_lane_name(str(root_or_role or ""))
    return Path(root_or_role) if root_or_role is not None else _default_root(), canonical_lane_name(role)


def lane_backoff_relpath(role: str) -> str:
    return f"lane-backoff/{canonical_lane_name(role)}.json"


def lane_backoff_path(root: Path, role: str) -> Path:
    return resolve_orchestrator_read_path(root, lane_backoff_relpath(role))


def _default_lane_backoff(role: str) -> dict[str, Any]:
    canonical_role = canonical_lane_name(role)
    return {
        "schema_version": "lane_backoff.v1",
        "role": canonical_role,
        "active": False,
        "reason": "none",
        "until": None,
        "trigger_streak": 0,
        "null_tick_streak": 0,
        "armed_at": None,
        "cleared_at": None,
        "cleared_by": None,
        "updated_at": _utc_now(),
    }


def load_lane_backoff(root_or_role: Path | str | None, role: str | None = None) -> dict[str, Any]:
    root, canonical_role = _resolve_root_and_role(root_or_role, role)
    path = lane_backoff_path(root, canonical_role)
    default = _default_lane_backoff(canonical_role)
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return default
    if not isinstance(payload, dict):
        return default
    default.update(payload)
    default["role"] = canonical_role
    default["active"] = bool(default.get("active"))
    default["trigger_streak"] = int(default.get("trigger_streak", 0) or 0)
    default["null_tick_streak"] = int(default.get("null_tick_streak", 0) or 0)
    return default


def persist_lane_backoff(root: Path, role: str, payload: dict[str, Any]) -> Path:
    state = _default_lane_backoff(role)
    if isinstance(payload, dict):
        state.update(payload)
    canonical_role = canonical_lane_name(state.get("role", role))
    state["role"] = canonical_role
    state["active"] = bool(state.get("active"))
    state["trigger_streak"] = int(state.get("trigger_streak", 0) or 0)
    state["null_tick_streak"] = int(state.get("null_tick_streak", 0) or 0)
    state["updated_at"] = _utc_now()
    path = write_orchestrator_json(root, lane_backoff_relpath(canonical_role), state, mirror_docs=False)

    runtime_state = load_runtime_state(root)
    runtime_lane_backoff = runtime_state.get("lane_backoff", {})
    if not isinstance(runtime_lane_backoff, dict):
        runtime_lane_backoff = {}
    runtime_lane_backoff = dict(runtime_lane_backoff)
    runtime_lane_backoff[canonical_role] = dict(state)
    persist_runtime_state(
        root,
        lifecycle=str(runtime_state.get("lifecycle", "running") or "running"),
        reason=str(runtime_state.get("reason", "inferred") or "inferred"),
        execution_mode=str(runtime_state.get("execution_mode", "") or ""),
        operator_mode=str(runtime_state.get("operator_mode", "") or ""),
        source=str(runtime_state.get("source", "lane_backoff") or "lane_backoff"),
        lane_backoff=runtime_lane_backoff,
    )
    return path


def write_lane_backoff(root_or_role: Path | str | None, role_or_payload: str | dict[str, Any], payload: dict[str, Any] | None = None) -> Path:
    if payload is None:
        root = _default_root()
        role = str(root_or_role or "")
        resolved_payload = role_or_payload if isinstance(role_or_payload, dict) else {}
    else:
        root = Path(root_or_role) if root_or_role is not None else _default_root()
        role = str(role_or_payload or "")
        resolved_payload = payload
    return persist_lane_backoff(root, role, resolved_payload)


def clear_lane_backoff(
    root_or_role: Path | str | None,
    role: str | None = None,
    *,
    cleared_by: str = "planner",
    reason: str = "planner_refresh",
) -> dict[str, Any]:
    root, canonical_role = _resolve_root_and_role(root_or_role, role)
    state = load_lane_backoff(root, canonical_role)
    state.update(
        {
            "active": False,
            "reason": str(reason or "planner_refresh").strip() or "planner_refresh",
            "until": None,
            "trigger_streak": 0,
            "null_tick_streak": 0,
            "cleared_at": _utc_now(),
            "cleared_by": str(cleared_by or "planner").strip() or "planner",
        }
    )
    persist_lane_backoff(root, canonical_role, state)
    return state


def is_lane_backoff_active(payload: dict[str, Any]) -> bool:
    if not isinstance(payload, dict) or not bool(payload.get("active")):
        return False
    until_raw = str(payload.get("until") or "").strip()
    if not until_raw:
        return True
    try:
        until_dt = datetime.fromisoformat(until_raw.replace("Z", "+00:00"))
    except Exception:
        return True
    return until_dt > datetime.now(timezone.utc)


def record_lane_tick(
    root: Path,
    role: str,
    *,
    null_tick: bool,
    reason: str,
    threshold: int = LANE_BACKOFF_THRESHOLD,
    activated_by: str = "fc_agent_tick",
) -> dict[str, Any]:
    state = load_lane_backoff(root, role)
    threshold_value = max(1, int(threshold or LANE_BACKOFF_THRESHOLD))
    reason_text = str(reason or "no_canonical_delta").strip() or "no_canonical_delta"
    if not null_tick:
        if not state.get("active"):
            state["null_tick_streak"] = 0
            state["reason"] = "none"
        persist_lane_backoff(root, role, state)
        return state

    streak = int(state.get("null_tick_streak", 0) or 0) + 1
    state["null_tick_streak"] = streak
    if not state.get("active") and streak >= threshold_value:
        state["active"] = True
        state["reason"] = reason_text
        state["trigger_streak"] = streak
        state["armed_at"] = _utc_now()
        state["until"] = None
        state["cleared_at"] = None
        state["cleared_by"] = str(activated_by or "fc_agent_tick").strip() or "fc_agent_tick"
    persist_lane_backoff(root, role, state)
    return state


def load_all_lane_backoffs(root: Path, roles: tuple[str, ...] = CONTINUOUS_LANES) -> dict[str, Any]:
    return {canonical_lane_name(role): load_lane_backoff(root, role) for role in roles}


def load_active_lane_backoffs(root: Path | None = None, roles: tuple[str, ...] = CONTINUOUS_LANES) -> dict[str, Any]:
    effective_root = Path(root) if root is not None else _default_root()
    return {
        role: state
        for role, state in load_all_lane_backoffs(effective_root, roles=roles).items()
        if is_lane_backoff_active(state)
    }
