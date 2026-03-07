from __future__ import annotations

import asyncio
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domains.market_data.api import dashboard as dashboard_route


def test_portfolio_summary_nominal_exposes_stable_metadata(monkeypatch):
    monkeypatch.setattr(
        dashboard_route,
        "build_portfolio_summary",
        lambda: {
            "portfolio_value": 123.45,
            "generated_at": "2026-03-07T16:54:00Z",
            "source": ["dashboard_ui_service"],
        },
    )

    payload = asyncio.run(dashboard_route.get_portfolio_summary())

    assert payload["ok"] is True
    assert payload["status"] == "ok"
    assert payload["error"] is None
    assert payload["freshness"] == "2026-03-07T16:54:00Z"
    assert payload["data"]["status"] == "ok"
    assert payload["data"]["error"] is None
    assert payload["data"]["freshness"] == "2026-03-07T16:54:00Z"


def test_portfolio_summary_fallback_exposes_stable_metadata(monkeypatch):
    def fail_summary():
        raise RuntimeError("dashboard summary failed")

    monkeypatch.setattr(dashboard_route, "build_portfolio_summary", fail_summary)

    payload = asyncio.run(dashboard_route.get_portfolio_summary())

    assert payload["ok"] is True
    assert payload["status"] == "degraded"
    assert "dashboard summary failed" in str(payload["error"])
    assert payload["freshness"] == payload["data"]["freshness"]
    assert payload["data"]["status"] == "degraded"
    assert "dashboard summary failed" in str(payload["data"]["error"])
    assert payload["data"]["portfolio_value"] is None
