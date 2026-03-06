from __future__ import annotations

import time

from platform.routers import health


def test_runtime_rate_limit_snapshot_reads_active_cooldowns(tmp_path, monkeypatch):
    now = int(time.time())
    monkeypatch.setenv("FC_ROLE_STATE_DIR", str(tmp_path))
    (tmp_path / "planner.rate_limit_gate_cache").write_text(f"{now+90}|planner throttling")
    (tmp_path / "dev.rate_limit_gate_cache").write_text(f"{now-10}|expired")

    payload = health._runtime_rate_limit_snapshot()

    assert payload["active_count"] == 1
    assert payload["cooldowns"]
    active = payload["active_cooldowns"]
    assert active[0]["actor"] == "planner"
    assert active[0]["reason"] == "planner throttling"
    assert active[0]["active"] is True
