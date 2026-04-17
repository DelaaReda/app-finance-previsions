from __future__ import annotations

from apps.monitor.src.aggregators import compute_health, ensure_core_agents


def test_ensure_core_agents_never_null():
    agents, incomplete = ensure_core_agents({"planner": {"status": "OK", "verdict": "PASS", "blocker": "NONE", "tick_age_min": 1, "source": "runtime_contract"}})
    assert "dev" in agents
    assert "admin" in agents
    assert "dev" in incomplete
    assert "admin" in incomplete


def test_compute_health_force_degraded():
    health = compute_health(
        force_degraded=True,
        hard_blocked=False,
        has_rate_limits=False,
        has_rate_limited_agents=False,
        has_stale_context=False,
        summary_blocker_roles=[],
    )
    assert health == "DEGRADED"


def test_compute_health_stale_when_context_is_stale():
    health = compute_health(
        force_degraded=False,
        hard_blocked=False,
        has_rate_limits=False,
        has_rate_limited_agents=False,
        has_stale_context=True,
        summary_blocker_roles=[],
    )
    assert health == "STALE"


def test_compute_health_keeps_non_blocking_rate_limits_ok():
    health = compute_health(
        force_degraded=False,
        hard_blocked=False,
        has_rate_limits=True,
        has_rate_limited_agents=False,
        rate_limits_advisory=True,
        has_stale_context=False,
        summary_blocker_roles=[],
    )
    assert health == "OK"
