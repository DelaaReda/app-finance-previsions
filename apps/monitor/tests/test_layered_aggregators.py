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
        summary_blocker_roles=[],
    )
    assert health == "DEGRADED"
