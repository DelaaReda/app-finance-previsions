from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

SRC_PATH = Path(__file__).resolve().parents[3]
ROOT_PATH = Path(__file__).resolve().parents[6]
for candidate in (ROOT_PATH, SRC_PATH):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from domains.copilot.api import copilot as copilot_route


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(copilot_route.router, prefix="/api")
    return TestClient(app)


def test_personal_finance_start_rescues_never_empty_fallback_with_judge_payload(monkeypatch):
    async def fake_build_copilot_start_endpoint_payload(**_kwargs):
        return {
            "brief_of_day": {
                "summary": "No daily brief available yet.",
                "market_sentiment": "UNKNOWN",
                "generated_at": "2026-03-14T02:00:00Z",
                "freshness": "2026-03-14T02:00:00Z",
                "source": ["brief_daily_fallback"],
            },
            "ask": [{"id": "ask_copilot", "kind": "ask", "target": "/personal-finance/ask"}],
            "open": [{"id": "open_copilot", "kind": "open", "target": "/personal-finance"}],
            "generated_at": "2026-03-14T02:00:00Z",
            "freshness": "2026-03-14T02:00:00Z",
            "source": ["copilot_start_route"],
            "filters_applied": {"tickers": ["NVDA"]},
            "stats": {"ask_count": 1, "open_count": 1},
            "warnings": [],
            "fallback_used": "copilot_start_never_empty",
        }

    async def fake_judge_personal_finance_start_payload(*, tickers=None):
        assert tickers == ["NVDA"]
        return {
            "ok": True,
            "data": {
                "brief_of_day": {
                    "summary": "Judge rescue brief for NVDA.",
                    "market_sentiment": "BEARISH",
                    "generated_at": "2026-03-14T03:00:00Z",
                    "freshness": "2026-03-14T03:00:00Z",
                    "source": ["judge_personal_finance_start_service"],
                },
                "ranked_action": {
                    "id": "portfolio_today",
                    "kind": "ask",
                    "label": "Portfolio today?",
                    "target": "/personal-finance/ask",
                },
                "ask": [
                    {
                        "id": "portfolio_today",
                        "kind": "ask",
                        "label": "Portfolio today?",
                        "target": "/personal-finance/ask",
                    }
                ],
                "open": [
                    {
                        "id": "open_copilot",
                        "kind": "open",
                        "label": "Open Copilot",
                        "target": "/personal-finance",
                    }
                ],
                "generated_at": "2026-03-14T03:00:00Z",
                "freshness": "2026-03-14T03:00:00Z",
                "source": ["judge_personal_finance_start_service"],
                "sources": ["judge_personal_finance_start_service"],
                "filters_applied": {"tickers": ["NVDA"]},
                "stats": {"ask_count": 1, "open_count": 1},
                "warnings": [],
            },
        }

    monkeypatch.setattr(
        copilot_route.copilot_service,
        "build_copilot_start_endpoint_payload",
        fake_build_copilot_start_endpoint_payload,
    )
    monkeypatch.setattr(
        copilot_route.import_module("services.judge_endpoint_service"),
        "get_judge_personal_finance_start_payload",
        fake_judge_personal_finance_start_payload,
    )

    client = _client()
    response = client.get("/api/personal-finance/start?tickers=nvda")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["brief_of_day"]["summary"] == "Judge rescue brief for NVDA."
    assert data["ranked_action"]["target"] == "/personal-finance/ask"
    assert data["ask"][0]["target"] == "/personal-finance/ask"
    assert data["open"][0]["target"] == "/personal-finance"
    assert data["cache"]["hit"] is False
    assert "judge_personal_finance_start_service" in (data.get("source") or [])


def test_copilot_start_rescues_never_empty_fallback_with_copilot_targets(monkeypatch):
    async def fake_build_copilot_start_endpoint_payload(**_kwargs):
        return {
            "brief_of_day": {
                "summary": "No daily brief available yet.",
                "market_sentiment": "UNKNOWN",
                "generated_at": "2026-03-14T02:00:00Z",
                "freshness": "2026-03-14T02:00:00Z",
                "source": ["brief_daily_fallback"],
            },
            "ask": [{"id": "ask_copilot", "kind": "ask", "target": "/copilot/ask"}],
            "open": [{"id": "open_copilot", "kind": "open", "target": "/copilot"}],
            "generated_at": "2026-03-14T02:00:00Z",
            "freshness": "2026-03-14T02:00:00Z",
            "source": ["copilot_start_route"],
            "filters_applied": {"tickers": ["NVDA"]},
            "stats": {"ask_count": 1, "open_count": 1},
            "warnings": [],
            "fallback_used": "copilot_start_never_empty",
        }

    async def fake_judge_personal_finance_start_payload(*, tickers=None):
        assert tickers == ["NVDA"]
        return {
            "ok": True,
            "data": {
                "brief_of_day": {
                    "summary": "Judge rescue brief for NVDA.",
                    "market_sentiment": "BEARISH",
                    "generated_at": "2026-03-14T03:00:00Z",
                    "freshness": "2026-03-14T03:00:00Z",
                    "source": ["judge_personal_finance_start_service"],
                },
                "ranked_action": {
                    "id": "portfolio_today",
                    "kind": "ask",
                    "label": "Portfolio today?",
                    "target": "/personal-finance/ask",
                },
                "ask": [
                    {
                        "id": "portfolio_today",
                        "kind": "ask",
                        "label": "Portfolio today?",
                        "target": "/personal-finance/ask",
                    }
                ],
                "open": [
                    {
                        "id": "open_copilot",
                        "kind": "open",
                        "label": "Open Copilot",
                        "target": "/personal-finance",
                    }
                ],
                "generated_at": "2026-03-14T03:00:00Z",
                "freshness": "2026-03-14T03:00:00Z",
                "source": ["judge_personal_finance_start_service"],
                "sources": ["judge_personal_finance_start_service"],
                "filters_applied": {"tickers": ["NVDA"]},
                "stats": {"ask_count": 1, "open_count": 1},
                "warnings": [],
            },
        }

    monkeypatch.setattr(
        copilot_route.copilot_service,
        "build_copilot_start_endpoint_payload",
        fake_build_copilot_start_endpoint_payload,
    )
    monkeypatch.setattr(
        copilot_route.import_module("services.judge_endpoint_service"),
        "get_judge_personal_finance_start_payload",
        fake_judge_personal_finance_start_payload,
    )

    client = _client()
    response = client.get("/api/copilot/start?tickers=nvda")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["brief_of_day"]["summary"] == "Judge rescue brief for NVDA."
    assert data["ranked_action"]["target"] == "/copilot/ask"
    assert data["ask"][0]["target"] == "/copilot/ask"
    assert data["open"][0]["target"] == "/copilot"
    assert data["cache"]["hit"] is False
    assert "judge_personal_finance_start_service" in (data.get("source") or [])
