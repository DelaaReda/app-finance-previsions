import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

SRC_PATH = Path(__file__).resolve().parents[3]
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from domains.copilot.api.copilot import router
from domains.copilot.application import copilot_service
from storage import io as storage_io


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


def test_copilot_context_route_passes_scope_tickers_to_service(monkeypatch):
    captured = {}

    async def _fake_build_context_payload(*_args, **kwargs):
        captured["scope"] = kwargs.get("scope")
        return {
            "daily_brief": {
                "summary": "Scoped brief ready.",
                "source": ["copilot_domain_router_test"],
            },
            "entry_points": [],
            "copilot_start": {},
            "scope_tickers": kwargs.get("scope", {}).get("tickers", []),
        }

    monkeypatch.setattr(copilot_service, "build_context_payload", _fake_build_context_payload)

    client = _client()
    response = client.get("/api/copilot/context?tickers=nvda&tickers=msft&tickers=NVDA")

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("ok") is True
    assert captured.get("scope") == {"tickers": ["NVDA", "MSFT"]}
    assert payload.get("data", {}).get("scope_tickers") == ["NVDA", "MSFT"]


def test_copilot_context_route_success_keeps_brief_first_starter_contract(monkeypatch):
    class _FakeContextService:
        async def get_current_market_context(self):
            return {
                "regime": "BULL_MARKET",
                "confidence": 0.72,
                "key_drivers": ["AI leadership remains concentrated."],
                "metadata": {
                    "generated_at": "2026-03-09T10:15:00Z",
                    "sources": ["forecasts", "news"],
                },
            }

    brief_snapshot = {
        "data": {
            "daily": {
                "summary": "Semiconductors continue to lead while rates stay range-bound.",
                "market_sentiment": "BULLISH",
                "top_signals": ["Semiconductors leading"],
                "top_risks": ["Rates repricing"],
                "generated_at": "2026-03-09T10:20:00Z",
                "source": ["copilot_domain_router_test"],
            }
        }
    }

    monkeypatch.setattr(
        storage_io,
        "load_json",
        lambda key: brief_snapshot if key == "brief_daily" else None,
    )
    monkeypatch.setattr(
        copilot_service,
        "_resolve_context_service_class",
        lambda _context_service_cls=None: _FakeContextService,
    )

    client = _client()
    response = client.get("/api/copilot/context?tickers=nvda")

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("ok") is True

    data = payload.get("data") or {}
    assert data.get("scope_tickers") == ["NVDA"]

    daily_brief = data.get("daily_brief") or {}
    assert daily_brief.get("summary") == "Semiconductors continue to lead while rates stay range-bound."
    assert daily_brief.get("market_sentiment") == "BULLISH"
    assert daily_brief.get("source") == ["copilot_domain_router_test"]

    entry_points = data.get("entry_points") or []
    assert [item.get("id") for item in entry_points] == [
        "brief_of_day",
        "ask_copilot",
        "open_copilot",
    ]
    assert entry_points[0].get("target") == "/brief/daily"
    assert entry_points[1].get("prefill", {}).get("tickers") == ["NVDA"]
    assert entry_points[2].get("target") == "/copilot"

    copilot_start = data.get("copilot_start") or {}
    assert copilot_start.get("brief_of_day", {}).get("summary") == daily_brief.get("summary")
    assert [item.get("id") for item in copilot_start.get("ask", [])] == [
        "portfolio_today",
        "market_theme",
        "nvda_memo",
    ]
    assert copilot_start.get("ask", [])[0].get("prefill", {}).get("tickers") == ["NVDA"]
    assert [item.get("target") for item in copilot_start.get("open", [])] == [
        "market",
        "opportunities",
        "copilot",
    ]


def test_copilot_context_route_fallback_keeps_brief_and_entry_points(monkeypatch):
    async def _raise_context_error(*_args, **_kwargs):
        raise RuntimeError("copilot context unavailable")

    fallback_brief = {
        "summary": "No daily brief available yet.",
        "market_sentiment": "UNKNOWN",
        "top_signals": [],
        "top_risks": [],
        "macro_signals": [],
        "sector_rotation": {"top": [], "bottom": []},
        "generated_at": "2026-03-09T06:00:00Z",
        "freshness": "2026-03-09T06:00:00Z",
        "source": ["copilot_daily_brief_fallback"],
    }
    fallback_entry_points = [
        {
            "id": "brief_of_day",
            "kind": "open",
            "label": "Brief du jour",
            "target": "/brief/daily",
        },
        {
            "id": "ask_copilot",
            "kind": "ask",
            "label": "Poser une question",
            "target": "/copilot/ask",
        },
    ]

    monkeypatch.setattr(copilot_service, "build_context_payload", _raise_context_error)
    monkeypatch.setattr(copilot_service, "_load_daily_brief_payload", lambda: dict(fallback_brief))
    monkeypatch.setattr(
        copilot_service,
        "_build_copilot_entry_points",
        lambda scope=None: [dict(item) for item in fallback_entry_points],
    )
    monkeypatch.setattr(
        copilot_service,
        "_build_copilot_start_payload",
        lambda *, daily_brief=None, entry_points=None, scope=None: {
            "brief_of_day": dict(daily_brief or {}),
            "open": [dict(item) for item in entry_points or [] if item.get("kind") == "open"],
            "ask": [dict(item) for item in entry_points or [] if item.get("kind") == "ask"],
        },
    )

    client = _client()
    response = client.get("/api/copilot/context?tickers=spy")

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("ok") is True

    data = payload.get("data") or {}
    assert data.get("note") == "Market context service temporarily unavailable."
    assert data.get("scope_tickers") == ["SPY"]

    daily_brief = data.get("daily_brief") or {}
    assert daily_brief.get("summary") == "No daily brief available yet."
    assert daily_brief.get("source") == ["copilot_daily_brief_fallback"]

    entry_points = data.get("entry_points") or []
    assert [item.get("id") for item in entry_points[:2]] == ["brief_of_day", "ask_copilot"]
    assert [item.get("kind") for item in entry_points[:2]] == ["open", "ask"]

    copilot_start = data.get("copilot_start") or {}
    assert copilot_start.get("brief_of_day", {}).get("summary") == "No daily brief available yet."
    assert [item.get("id") for item in copilot_start.get("open", [])] == ["brief_of_day"]
    assert [item.get("id") for item in copilot_start.get("ask", [])] == ["ask_copilot"]


def test_copilot_start_route_reuses_context_payload(monkeypatch):
    captured = {}

    async def _fake_build_context_payload(*_args, **kwargs):
        captured["scope"] = kwargs.get("scope")
        return {
            "copilot_start": {
                "brief_of_day": {
                    "summary": "Daily brief ready.",
                    "generated_at": "2026-03-09T10:00:00Z",
                    "freshness": "2026-03-09T10:00:00Z",
                    "source": ["copilot_start_test"],
                },
                "ask": [
                    {"id": "portfolio_today", "target": "/copilot/ask"},
                ],
                "open": [
                    {"id": "brief_of_day", "target": "/brief/daily"},
                    {"id": "open_copilot", "target": "/copilot"},
                ],
            },
            "regime_detection": {
                "label": "RISK_ON",
                "confidence": 0.81,
                "threshold_reason": "Breadth improving",
            },
            "allocation_drift_alerts": {
                "active": True,
                "alerts": [
                    {
                        "id": "largest_position_concentration",
                        "symbol": "NVDA",
                        "severity": "high",
                    }
                ],
            },
        }

    monkeypatch.setattr(copilot_service, "build_context_payload", _fake_build_context_payload)

    client = _client()
    response = client.get("/api/copilot/start?tickers=nvda&tickers=msft&tickers=NVDA")

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("ok") is True
    assert captured.get("scope") == {"tickers": ["NVDA", "MSFT"]}

    data = payload.get("data") or {}
    assert data.get("brief_of_day", {}).get("summary") == "Daily brief ready."
    assert [item.get("id") for item in data.get("ask", [])] == ["portfolio_today"]
    assert [item.get("id") for item in data.get("open", [])] == ["brief_of_day", "open_copilot"]
    assert data.get("filters_applied") == {"tickers": ["NVDA", "MSFT"]}
    assert data.get("stats") == {"ask_count": 1, "open_count": 2}
    assert data.get("scope_tickers") == ["NVDA", "MSFT"]
    assert "copilot_start_route" in (data.get("source") or [])
    assert data.get("regime_detection", {}).get("label") == "RISK_ON"
    assert data.get("allocation_drift_alerts", {}).get("active") is True


def test_copilot_start_route_uses_service_resolved_scope_metadata(monkeypatch):
    async def _fake_build_context_payload(*_args, **_kwargs):
        return {
            "scope_tickers": ["AAPL", "MSFT"],
            "copilot_start": {
                "brief_of_day": {
                    "summary": "Portfolio-scoped brief.",
                    "generated_at": "2026-03-09T10:00:00Z",
                    "freshness": "2026-03-09T10:00:00Z",
                    "source": ["copilot_start_test"],
                },
                "ask": [
                    {
                        "id": "portfolio_today",
                        "target": "/copilot/ask",
                        "prefill": {"tickers": ["AAPL", "MSFT"]},
                    },
                ],
                "open": [
                    {"id": "open_copilot", "target": "/copilot"},
                ],
            },
        }

    monkeypatch.setattr(copilot_service, "build_context_payload", _fake_build_context_payload)

    client = _client()
    response = client.get("/api/copilot/start")

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("ok") is True

    data = payload.get("data") or {}
    assert data.get("filters_applied") == {"tickers": ["AAPL", "MSFT"]}
    assert data.get("scope_tickers") == ["AAPL", "MSFT"]
    assert data.get("ask", [])[0].get("prefill", {}).get("tickers") == ["AAPL", "MSFT"]


def test_copilot_start_route_fallback_keeps_brief_and_actions(monkeypatch):
    async def _raise_context_error(*_args, **_kwargs):
        raise RuntimeError("copilot context unavailable")

    fallback_brief = {
        "summary": "No daily brief available yet.",
        "market_sentiment": "UNKNOWN",
        "generated_at": "2026-03-09T06:00:00Z",
        "freshness": "2026-03-09T06:00:00Z",
        "source": ["copilot_daily_brief_fallback"],
    }
    fallback_entry_points = [
        {
            "id": "brief_of_day",
            "kind": "open",
            "label": "Brief du jour",
            "target": "/brief/daily",
        },
        {
            "id": "ask_copilot",
            "kind": "ask",
            "label": "Poser une question",
            "target": "/copilot/ask",
        },
    ]

    monkeypatch.setattr(copilot_service, "build_context_payload", _raise_context_error)
    monkeypatch.setattr(copilot_service, "_load_daily_brief_payload", lambda: dict(fallback_brief))
    monkeypatch.setattr(
        copilot_service,
        "_build_copilot_entry_points",
        lambda scope=None: [dict(item) for item in fallback_entry_points],
    )
    monkeypatch.setattr(
        copilot_service,
        "_build_copilot_start_payload",
        lambda *, daily_brief=None, entry_points=None, scope=None: {
            "brief_of_day": dict(daily_brief or {}),
            "open": [dict(item) for item in entry_points or [] if item.get("kind") == "open"],
            "ask": [dict(item) for item in entry_points or [] if item.get("kind") == "ask"],
        },
    )

    client = _client()
    response = client.get("/api/copilot/start?tickers=spy")

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("ok") is True

    data = payload.get("data") or {}
    assert data.get("note") == "Market context service temporarily unavailable."
    assert data.get("brief_of_day", {}).get("summary") == "No daily brief available yet."
    assert [item.get("id") for item in data.get("open", [])] == ["brief_of_day"]
    assert [item.get("id") for item in data.get("ask", [])] == ["ask_copilot"]
    assert data.get("filters_applied") == {"tickers": ["SPY"]}
    assert data.get("scope_tickers") == ["SPY"]


def test_copilot_start_route_omits_alert_payloads_in_fallback(monkeypatch):
    async def _raise_context_error(*_args, **_kwargs):
        raise RuntimeError("copilot context unavailable")

    monkeypatch.setattr(copilot_service, "build_context_payload", _raise_context_error)
    monkeypatch.setattr(
        copilot_service,
        "_load_daily_brief_payload",
        lambda: {
            "summary": "No daily brief available yet.",
            "market_sentiment": "UNKNOWN",
            "generated_at": "2026-03-09T06:00:00Z",
            "freshness": "2026-03-09T06:00:00Z",
            "source": ["copilot_daily_brief_fallback"],
        },
    )
    monkeypatch.setattr(copilot_service, "_build_copilot_entry_points", lambda scope=None: [])
    monkeypatch.setattr(
        copilot_service,
        "_build_copilot_start_payload",
        lambda *, daily_brief=None, entry_points=None, scope=None: {
            "brief_of_day": dict(daily_brief or {}),
            "open": [],
            "ask": [],
        },
    )

    client = _client()
    response = client.get("/api/copilot/start")

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("ok") is True
    data = payload.get("data") or {}
    assert "regime_detection" not in data
    assert "allocation_drift_alerts" not in data


def test_copilot_context_includes_playbook_enrichment(monkeypatch):
    """Test that context includes playbook_id and playbook_context (BATCH-15-DEV-02)."""
    async def _fake_build_context_payload(*_args, **_kwargs):
        return {
            "regime": "BULL_MARKET",
            "confidence": 0.75,
            "key_drivers": ["Strong momentum"],
            "playbook_id": "bull_moderate_001",
            "playbook_context": {
                "name": "Bull Market Growth Strategy",
                "description": "Participate in upside while maintaining diversification",
                "regime": "bull_market",
                "risk_profile": "moderate",
                "guardrails": [
                    "Avoid concentration >20% in single sector",
                    "Rebalance if equity allocation drifts >5% from target",
                ],
            },
        }

    monkeypatch.setattr(copilot_service, "build_context_payload", _fake_build_context_payload)

    client = _client()
    resp = client.get("/api/copilot/context")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["data"]["playbook_id"] == "bull_moderate_001"
    assert "playbook_context" in data["data"]
    assert data["data"]["playbook_context"]["name"] == "Bull Market Growth Strategy"
