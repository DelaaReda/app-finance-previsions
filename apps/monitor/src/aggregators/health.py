from __future__ import annotations

from typing import Any

CORE_ROLES = ("planner", "dev", "admin", "scrum_master")


def unknown_agent_payload(role: str, source: str = "unknown") -> dict[str, Any]:
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


def ensure_core_agents(
    agents: dict[str, Any],
    *,
    core_roles: tuple[str, ...] | list[str] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    out = dict(agents) if isinstance(agents, dict) else {}
    incomplete: list[str] = []
    required = ("status", "verdict", "blocker", "tick_age_min", "source")
    roles = tuple(core_roles or CORE_ROLES)
    for role in roles:
        agent = out.get(role)
        if not isinstance(agent, dict):
            out[role] = unknown_agent_payload(role)
            incomplete.append(role)
            continue
        if any(field not in agent for field in required):
            incomplete.append(role)
            continue
        status_token = str(agent.get("status", "")).strip().upper()
        verdict_token = str(agent.get("verdict", "")).strip().upper()
        source_token = str(agent.get("source", "")).strip().lower()
        if source_token == "unknown" or status_token in {"UNKNOWN", "?"} or verdict_token in {"UNKNOWN", "?"}:
            incomplete.append(role)
    return out, sorted(set(incomplete))


def compute_health(
    *,
    force_degraded: bool,
    hard_blocked: bool,
    has_rate_limits: bool,
    has_rate_limited_agents: bool,
    rate_limits_advisory: bool = False,
    has_stale_context: bool = False,
    summary_blocker_roles: list[str] | None = None,
    scrum_health_guard: bool = True,
) -> str:
    if force_degraded:
        return "DEGRADED"

    blocker_roles = summary_blocker_roles or []
    only_scrum_blocked = bool(blocker_roles) and set(blocker_roles) == {"scrum_master"}

    if hard_blocked:
        if scrum_health_guard and only_scrum_blocked:
            return "STALE"
        return "DEGRADED"

    if has_rate_limits or has_rate_limited_agents:
        if rate_limits_advisory:
            pass
        else:
            return "STALE"

    if has_stale_context:
        return "STALE"

    return "OK"
