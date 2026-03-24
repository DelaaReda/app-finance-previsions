from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from api.main import create_app
from platform.routers import critical


def _client(monkeypatch) -> TestClient:
    monkeypatch.setenv("FC_API_EDGE_RECOMMENDATIONS", "1")
    app = create_app()
    app.router.on_startup.clear()
    app.router.on_shutdown.clear()
    return TestClient(app)


def test_recommendations_daily_prefers_daily_brief_and_preserves_alerting_context(monkeypatch):
    snapshots = {
        "brief_daily": {
            "data": {
                "daily": {
                    "top_signals": [
                        {
                            "ticker": "NVDA",
                            "confidence": 0.82,
                            "expected_return": 0.034,
                            "horizon": "1d",
                            "reason": "AI demand remains intact.",
                        }
                    ],
                    "top_risks": [
                        {
                            "ticker": "QQQ",
                            "priority": "urgent",
                            "suppression_reason": "",
                        }
                    ],
                    "suppressed_risks": [
                        {
                            "ticker": "SMH",
                            "suppression_reason": "fatigue_window_duplicate",
                            "duplicate_count": 2,
                        }
                    ],
                    "alerting_metadata": {
                        "suppression_window_minutes": 15,
                        "suppressed_risk_count": 1,
                    },
                    "source": ["brief_daily_fixture"],
                }
            }
        },
        "brief_daily.json": None,
        "brief_weekly": {
            "data": {
                "weekly": {
                    "top_signals": [
                        {
                            "ticker": "TLT",
                            "confidence": 0.51,
                            "expected_return": 0.011,
                            "horizon": "1w",
                            "reasoning": "Weekly fallback should not win.",
                        }
                    ],
                    "source": ["brief_weekly_fixture"],
                }
            }
        },
        "brief_weekly.json": None,
    }

    monkeypatch.setattr(
        critical,
        "_load_recommendations_brief_snapshot",
        lambda: (snapshots["brief_daily"]["data"]["daily"], "brief_daily"),
    )
    monkeypatch.setattr(
        critical,
        "_load_market_context_snapshot_fn",
        lambda: lambda: {
            "insights": {
                "market_regime": {"current": "RISK_OFF"},
                "summary": "Risk is concentrated into one catalyst.",
            }
        },
    )

    client = _client(monkeypatch)
    response = client.get("/api/recommendations/daily?limit=1")

    assert response.status_code == 200
    payload = response.json()
    data = payload["data"]

    assert data["recommendations"][0]["ticker"] == "NVDA"
    assert data["recommendations"][0]["reasoning"] == "AI demand remains intact."
    assert data["market_context"]["regime"] == "RISK_OFF"
    assert data["top_risks"] == [
        {
            "ticker": "QQQ",
            "priority": "urgent",
            "suppression_reason": "",
        }
    ]
    assert data["top_risk_items"] == data["top_risks"]
    assert data["suppressed_risks"] == [
        {
            "ticker": "SMH",
            "suppression_reason": "fatigue_window_duplicate",
            "duplicate_count": 2,
        }
    ]
    assert data["alerting_metadata"] == {
        "suppression_window_minutes": 15,
        "suppressed_risk_count": 1,
    }
    assert data["source"] == ["brief_daily_fixture"]


def test_recommendations_daily_keeps_weekly_fallback_contract_when_daily_missing(monkeypatch):
    snapshots = {
        "brief_daily": None,
        "brief_daily.json": None,
        "brief_weekly": {
            "data": {
                "weekly": {
                    "top_signals": [
                        {
                            "ticker": "TLT",
                            "confidence": 0.66,
                            "expected_return": 0.014,
                            "horizon": "1w",
                            "reasoning": "Rates relief keeps the fallback constructive.",
                        }
                    ],
                    "top_risks": [{"ticker": "CPI", "thesis": "Inflation surprise"}],
                    "source": ["brief_weekly_fixture"],
                }
            }
        },
        "brief_weekly.json": None,
    }

    monkeypatch.setattr(
        critical,
        "_load_recommendations_brief_snapshot",
        lambda: (snapshots["brief_weekly"]["data"]["weekly"], "brief_weekly"),
    )
    monkeypatch.setattr(
        critical,
        "_load_market_context_snapshot_fn",
        lambda: lambda: {
            "insights": {
                "market_regime": {"current": "NORMAL"},
                "summary": "Fallback context.",
            }
        },
    )

    client = _client(monkeypatch)
    response = client.get("/api/recommendations/daily?limit=1")

    assert response.status_code == 200
    data = response.json()["data"]

    assert data["recommendations"][0]["ticker"] == "TLT"
    assert data["recommendations"][0]["reasoning"] == "Rates relief keeps the fallback constructive."
    assert data["top_risks"] == [{"ticker": "CPI", "thesis": "Inflation surprise"}]
    assert data["top_risk_items"] == data["top_risks"]
    assert data["suppressed_risks"] == []
    assert data["alerting_metadata"] == {}
    assert data["source"] == ["brief_weekly_fixture"]
