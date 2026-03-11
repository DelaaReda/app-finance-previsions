from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from domains.copilot.api import copilot as copilot_route


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(copilot_route.router, prefix="/api")
    return TestClient(app)


def test_copilot_ask_route_exposes_structured_memo_contract(monkeypatch):
    async def fake_build_ask_payload(**_kwargs):
        return {
            "answer": "Buy NVDA on 1w momentum with event risk controls.",
            "action": "buy",
            "horizon": "1w",
            "confidence": 0.71,
            "reasoning": [
                "Momentum remains strong",
                "Market context is supportive",
            ],
            "risk": {
                "level": "medium",
                "caveat": "CPI could invalidate the setup",
            },
            "freshness": "2026-03-10T10:00:00Z",
            "generated_at": "2026-03-10T10:00:00Z",
            "next_steps": [
                "Wait for the CPI print before sizing up",
                "Review the position after earnings revisions",
            ],
            "invalidation": [
                "Break below 20D moving average",
            ],
            "sources": [
                {"type": "news", "url": "https://example.com/nvda", "ticker": "NVDA"},
            ],
            "sources_count": 2,
            "quality_status": "sufficient_sources",
            "requirements_met": {"min_sources_2": True, "quality_threshold": True},
        }

    monkeypatch.setattr(copilot_route.copilot_service, "build_ask_payload", fake_build_ask_payload)

    client = _client()
    response = client.post(
        "/api/copilot/ask",
        json={"question": "Donne-moi un memo sur NVDA", "tickers": ["NVDA"], "max_sources": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True

    data = payload["data"]
    memo = data.get("memo")

    assert isinstance(memo, dict)
    assert memo["verdict"] == "buy"
    assert memo["horizon"] == "1w"
    assert memo["why"] == [
        "Momentum remains strong",
        "Market context is supportive",
    ]
    assert memo["risks"] == [
        "medium",
        "CPI could invalidate the setup",
    ]
    assert memo["confidence"] == 0.71
    assert memo["freshness"] == "2026-03-10T10:00:00Z"
    assert memo["sources"] == [
        {"type": "news", "url": "https://example.com/nvda", "ticker": "NVDA"},
    ]
    assert memo["next_steps"] == [
        "Wait for the CPI print before sizing up",
        "Review the position after earnings revisions",
    ]
    assert memo["invalidation"] == [
        "Break below 20D moving average",
    ]

    # Legacy compatibility remains available for current consumers.
    assert data["answer"] == "Buy NVDA on 1w momentum with event risk controls."
    assert data["action"] == "buy"
    assert data["verdict"] == "buy"
    assert data["why"] == memo["why"]
    assert data["risks"] == memo["risks"]
    assert data["next_steps"] == memo["next_steps"]
    assert data["invalidation"] == memo["invalidation"]


def test_copilot_ask_route_keeps_insufficient_evidence_explicit(monkeypatch):
    async def fake_build_ask_payload(**_kwargs):
        return {
            "answer": "Signal partiel sur AAPL.",
            "action": "hold",
            "confidence": 0.45,
            "reasoning": [
                "Une seule source contextuelle est disponible.",
            ],
            "risk_caveat": "Sources insuffisantes (moins de 2).",
            "freshness": "2026-03-10T11:00:00Z",
            "generated_at": "2026-03-10T11:00:00Z",
            "sources": [
                {"type": "market_context", "ticker": "AAPL"},
            ],
            "sources_count": 1,
            "quality_status": "insufficient_sources",
            "requirements_met": {"min_sources_2": False, "quality_threshold": True},
        }

    monkeypatch.setattr(copilot_route.copilot_service, "build_ask_payload", fake_build_ask_payload)

    client = _client()
    response = client.post(
        "/api/copilot/ask",
        json={"question": "Donne-moi un memo sur AAPL", "tickers": ["AAPL"], "max_sources": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True

    data = payload["data"]
    memo = data["memo"]

    assert memo["verdict"] == "hold"
    assert memo["horizon"] == "1w"
    assert memo["why"] == ["Une seule source contextuelle est disponible."]
    assert memo["risks"] == ["Sources insuffisantes (moins de 2)."]
    assert memo["confidence"] == 0.45
    assert memo["freshness"] == "2026-03-10T11:00:00Z"
    assert memo["sources"] == [{"type": "market_context", "ticker": "AAPL"}]

    assert data["quality_status"] == "insufficient_sources"
    assert data["requirements_met"]["min_sources_2"] is False


def test_copilot_ask_route_preserves_portfolio_context_markers(monkeypatch):
    async def fake_build_ask_payload(**_kwargs):
        return {
            "answer": "Focus the memo on the saved core holdings.",
            "action": "hold",
            "confidence": 0.63,
            "reasoning": ["Saved holdings are concentrated in quality mega-cap tech."],
            "freshness": "2026-03-10T12:00:00Z",
            "generated_at": "2026-03-10T12:00:00Z",
            "sources": [{"type": "portfolio_state", "label": "saved_portfolio"}],
            "quality_status": "sufficient_sources",
            "requirements_met": {"min_sources_2": True, "quality_threshold": True},
            "context_influence": {
                "mode": "portfolio_aware",
                "portfolio_applied": True,
                "source": "saved_portfolio_default",
                "requested_tickers": [],
                "effective_tickers": ["AAPL", "MSFT"],
                "portfolio_id": "portfolio-123",
            },
            "portfolio_context": {
                "portfolio": {
                    "id": "portfolio-123",
                    "name": "Core",
                    "tickers": ["AAPL", "MSFT"],
                    "state": {
                        "horizon": "1y",
                        "conviction": "high",
                        "risk_tolerance": "moderate",
                    },
                },
                "risk_profile": "balanced",
                "risk_level": "medium",
            },
        }

    monkeypatch.setattr(copilot_route.copilot_service, "build_ask_payload", fake_build_ask_payload)

    client = _client()
    response = client.post(
        "/api/copilot/ask",
        json={"question": "How does my saved portfolio change today's memo?", "max_sources": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True

    data = payload["data"]
    assert data["context_influence"] == {
        "mode": "portfolio_aware",
        "portfolio_applied": True,
        "source": "saved_portfolio_default",
        "requested_tickers": [],
        "effective_tickers": ["AAPL", "MSFT"],
        "portfolio_id": "portfolio-123",
    }
    assert data["portfolio_context"]["portfolio"]["id"] == "portfolio-123"
    assert data["portfolio_context"]["portfolio"]["state"] == {
        "horizon": "1y",
        "conviction": "high",
        "risk_tolerance": "moderate",
    }
    assert data["memo"]["why"] == ["Saved holdings are concentrated in quality mega-cap tech."]


def test_copilot_ask_route_keeps_market_wide_context_explicit_when_no_saved_portfolio_applies(monkeypatch):
    async def fake_build_ask_payload(**_kwargs):
        return {
            "answer": "No saved portfolio was applied, so this stays market-wide.",
            "action": "watch",
            "confidence": 0.52,
            "reasoning": ["No saved scope or explicit tickers were available."],
            "freshness": "2026-03-10T12:05:00Z",
            "generated_at": "2026-03-10T12:05:00Z",
            "sources": [{"type": "market_context", "label": "brief_daily"}],
            "quality_status": "sufficient_sources",
            "requirements_met": {"min_sources_2": True, "quality_threshold": True},
            "context_influence": {
                "mode": "market_wide",
                "portfolio_applied": False,
                "source": "market_context_only",
                "requested_tickers": [],
                "effective_tickers": [],
            },
        }

    monkeypatch.setattr(copilot_route.copilot_service, "build_ask_payload", fake_build_ask_payload)

    client = _client()
    response = client.post(
        "/api/copilot/ask",
        json={"question": "What matters if I have no saved portfolio?", "max_sources": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True

    data = payload["data"]
    assert data["context_influence"] == {
        "mode": "market_wide",
        "portfolio_applied": False,
        "source": "market_context_only",
        "requested_tickers": [],
        "effective_tickers": [],
    }
    assert "portfolio_context" not in data
    assert data["memo"]["why"] == ["No saved scope or explicit tickers were available."]


def test_copilot_start_route_propagates_context_influence_and_portfolio_context(monkeypatch):
    async def fake_build_context_payload(**_kwargs):
        return {
            "scope_tickers": ["AAPL", "MSFT"],
            "context_influence": {
                "mode": "portfolio_aware",
                "portfolio_applied": True,
                "source": "saved_portfolio_default",
                "requested_tickers": [],
                "effective_tickers": ["AAPL", "MSFT"],
                "portfolio_id": "portfolio-123",
                "portfolio_state": {
                    "horizon": "1y",
                    "conviction": "high",
                    "risk_tolerance": "moderate",
                },
            },
            "portfolio_context": {
                "portfolio": {
                    "id": "portfolio-123",
                    "name": "Core",
                    "tickers": ["AAPL", "MSFT"],
                    "state": {
                        "horizon": "1y",
                        "conviction": "high",
                        "risk_tolerance": "moderate",
                    },
                },
                "risk_profile": "balanced",
                "risk_level": "medium",
            },
            "copilot_start": {
                "brief_of_day": {
                    "summary": "Portfolio brief ready.",
                    "generated_at": "2026-03-10T10:00:00Z",
                    "freshness": "2026-03-10T10:00:00Z",
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

    monkeypatch.setattr(copilot_route.copilot_service, "build_context_payload", fake_build_context_payload)

    client = _client()
    response = client.get("/api/copilot/start")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True

    data = payload["data"]
    assert data["scope_tickers"] == ["AAPL", "MSFT"]
    assert data["filters_applied"] == {"tickers": ["AAPL", "MSFT"]}
    assert data["context_influence"] == {
        "mode": "portfolio_aware",
        "portfolio_applied": True,
        "source": "saved_portfolio_default",
        "requested_tickers": [],
        "effective_tickers": ["AAPL", "MSFT"],
        "portfolio_id": "portfolio-123",
        "portfolio_state": {
            "horizon": "1y",
            "conviction": "high",
            "risk_tolerance": "moderate",
        },
    }
    assert data["portfolio_context"]["portfolio"]["id"] == "portfolio-123"
    assert data["portfolio_context"]["portfolio"]["state"] == {
        "horizon": "1y",
        "conviction": "high",
        "risk_tolerance": "moderate",
    }
