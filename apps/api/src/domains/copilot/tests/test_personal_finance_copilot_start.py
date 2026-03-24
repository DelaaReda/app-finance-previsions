"""
BATCH-83-DEV-01: Personal Finance Copilot - Minimal Slice Verification

Test the personal finance copilot start endpoint that delivers:
1. Brief of the day (market summary, sentiment, risks, macro, sectors)
2. Entry points for ask/open actions
3. Portfolio context when available
4. Regime detection

Product vision: "Build a personal finance copilot that starts with a brief of the day"
"""
from typing import Any, Dict, List

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from domains.copilot.api import copilot as copilot_route


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(copilot_route.router, prefix="/api")
    return TestClient(app)


class TestPersonalFinanceCopilotStart:
    """Verify /api/personal-finance/start delivers the brief + ask flow."""

    @pytest.fixture
    def copilot_service_module(self):
        """Import copilot service for unit testing."""
        from domains.copilot.application import copilot_service
        return copilot_service

    def test_personal_finance_start_has_brief_of_day(self, copilot_service_module):
        """Brief of day must be present with required fields."""
        result = copilot_service_module._load_daily_brief_payload()
        
        assert isinstance(result, dict), "Brief must be a dict"
        assert "summary" in result, "Brief must have summary"
        assert "market_sentiment" in result, "Brief must have market_sentiment"
        assert "generated_at" in result, "Brief must have generated_at"
        assert "freshness" in result, "Brief must have freshness"
        assert "source" in result or "sources" in result, "Brief must have source"
        
        # Optional but expected fields
        assert "top_signals" in result or "top_actions" in result, "Brief should have signals/actions"
        assert "top_risks" in result or "main_risks" in result, "Brief should have risks"
        assert "macro_signals" in result, "Brief should have macro signals"
        assert "sector_rotation" in result, "Brief should have sector rotation"

    def test_personal_finance_start_entry_points(self, copilot_service_module):
        """Entry points must include brief, ask, and open actions."""
        entry_points = copilot_service_module._build_copilot_entry_points(scope=None)
        
        assert isinstance(entry_points, list), "Entry points must be a list"
        assert len(entry_points) >= 2, "Must have at least 2 entry points"
        
        # Must have brief of day entry
        brief_entry = next((ep for ep in entry_points if ep.get("id") == "brief_of_day"), None)
        assert brief_entry is not None, "Must have brief_of_day entry point"
        assert brief_entry.get("kind") == "open", "Brief entry must be kind 'open'"
        assert brief_entry.get("label"), "Brief entry must have label"
        assert brief_entry.get("target"), "Brief entry must have target"
        
        # Must have ask entry
        ask_entry = next((ep for ep in entry_points if ep.get("id") == "ask_copilot"), None)
        assert ask_entry is not None, "Must have ask_copilot entry point"
        assert ask_entry.get("kind") == "ask", "Ask entry must be kind 'ask'"
        assert ask_entry.get("prefill", {}).get("question"), "Ask entry must have prefill question"

    def test_copilot_start_payload_structure(self, copilot_service_module):
        """Copilot start payload must have brief + ask + open structure."""
        daily_brief = copilot_service_module._load_daily_brief_payload()
        entry_points = copilot_service_module._build_copilot_entry_points(scope=None)
        
        start_payload = copilot_service_module._build_copilot_start_payload(
            daily_brief=daily_brief,
            entry_points=entry_points,
            scope=None,
        )
        
        assert isinstance(start_payload, dict), "Start payload must be a dict"
        assert "brief_of_day" in start_payload, "Must have brief_of_day"
        assert "ask" in start_payload, "Must have ask items"
        assert "open" in start_payload, "Must have open items"
        
        # Verify brief is integrated (content match, not reference)
        assert start_payload["brief_of_day"]["summary"] == daily_brief["summary"], \
            "Brief summary must be integrated"
        
        # Verify ask/open are separated correctly
        assert isinstance(start_payload["ask"], list), "Ask must be a list"
        assert isinstance(start_payload["open"], list), "Open must be a list"

    def test_scope_tickers_enrichment(self, copilot_service_module):
        """Scope tickers should enrich ask prefill when provided."""
        scope = {"tickers": ["AAPL", "MSFT"]}
        entry_points = copilot_service_module._build_copilot_entry_points(scope=scope)
        
        ask_entry = next((ep for ep in entry_points if ep.get("id") == "ask_copilot"), None)
        assert ask_entry is not None
        
        prefill = ask_entry.get("prefill", {})
        assert "tickers" in prefill, "Prefill must have tickers"
        assert "AAPL" in prefill["tickers"], "Must include AAPL from scope"
        assert "MSFT" in prefill["tickers"], "Must include MSFT from scope"

    def test_investment_memo_contract(self, copilot_service_module):
        """Verify the investment memo output contract from ask endpoint."""
        # Verify the service has the build_ask_payload function
        assert hasattr(copilot_service_module, "build_ask_payload"), \
            "Service must have build_ask_payload"

    def test_namespace_rewrite_for_personal_finance(self, copilot_service_module):
        """Verify namespace rewriting works for personal-finance prefix."""
        from domains.copilot.api.copilot import _rewrite_namespace_targets
        
        payload = {
            "ask": [{"kind": "ask", "target": "/copilot/ask"}],
            "open": [{"kind": "open", "target": "/copilot"}],
        }
        
        rewritten = _rewrite_namespace_targets(payload, namespace="personal-finance")
        
        assert rewritten["ask"][0]["target"] == "/personal-finance/ask", \
            "Ask target must be rewritten to personal-finance namespace"
        assert rewritten["open"][0]["target"] == "/personal-finance", \
            "Open target must be rewritten to personal-finance namespace"


class TestPersonalFinanceCopilotIntegration:
    """Integration tests for the alias routes."""

    def test_personal_finance_start_endpoint_route_contract(self, monkeypatch):
        async def fake_build_context_payload(**_kwargs):
            return {
                "daily_brief": {
                    "summary": "Markets are steady ahead of CPI.",
                    "market_sentiment": "NEUTRAL",
                    "generated_at": "2026-03-14T02:00:00Z",
                    "freshness": "2026-03-14T02:00:00Z",
                    "source": ["personal_finance_start_route_contract"],
                },
                "entry_points": [
                    {"id": "brief_of_day", "kind": "open", "target": "/brief/daily"},
                    {"id": "ask_copilot", "kind": "ask", "target": "/copilot/ask"},
                    {"id": "open_copilot", "kind": "open", "target": "/copilot"},
                ],
                "copilot_start": {
                    "brief_of_day": {
                        "summary": "Markets are steady ahead of CPI.",
                        "market_sentiment": "NEUTRAL",
                        "generated_at": "2026-03-14T02:00:00Z",
                        "freshness": "2026-03-14T02:00:00Z",
                        "source": ["personal_finance_start_route_contract"],
                    },
                    "ask": [{"id": "ask_copilot", "kind": "ask", "target": "/copilot/ask"}],
                    "open": [{"id": "open_copilot", "kind": "open", "target": "/copilot"}],
                },
            }

        monkeypatch.setattr(copilot_route.copilot_service, "build_context_payload", fake_build_context_payload)

        client = _client()
        response = client.get("/api/personal-finance/start?tickers=nvda")

        assert response.status_code == 200
        payload = response.json()
        assert payload.get("ok") is True

        result = payload["data"]
        assert result["brief_of_day"]["summary"] == "Markets are steady ahead of CPI."
        assert result["ask"][0]["target"] == "/personal-finance/ask"
        assert result["open"][0]["target"] == "/personal-finance"
        assert result["scope_tickers"] == ["NVDA"]

    def test_personal_finance_start_splits_comma_delimited_tickers(self, monkeypatch):
        async def fake_build_context_payload(**_kwargs):
            return {
                "daily_brief": {
                    "summary": "Markets are steady ahead of CPI.",
                    "market_sentiment": "NEUTRAL",
                    "generated_at": "2026-03-14T02:00:00Z",
                    "freshness": "2026-03-14T02:00:00Z",
                    "source": ["personal_finance_start_route_contract"],
                },
                "entry_points": [
                    {"id": "brief_of_day", "kind": "open", "target": "/brief/daily"},
                    {"id": "ask_copilot", "kind": "ask", "target": "/copilot/ask"},
                    {"id": "open_copilot", "kind": "open", "target": "/copilot"},
                ],
                "copilot_start": {
                    "brief_of_day": {
                        "summary": "Markets are steady ahead of CPI.",
                        "market_sentiment": "NEUTRAL",
                        "generated_at": "2026-03-14T02:00:00Z",
                        "freshness": "2026-03-14T02:00:00Z",
                        "source": ["personal_finance_start_route_contract"],
                    },
                    "ask": [{"id": "ask_copilot", "kind": "ask", "target": "/copilot/ask"}],
                    "open": [{"id": "open_copilot", "kind": "open", "target": "/copilot"}],
                },
            }

        monkeypatch.setattr(copilot_route.copilot_service, "build_context_payload", fake_build_context_payload)

        client = _client()
        response = client.get("/api/personal-finance/start?tickers=nvda,aapl")

        assert response.status_code == 200
        result = response.json()["data"]
        assert result["scope_tickers"] == ["NVDA", "AAPL"]

    def test_personal_finance_ask_endpoint_route_contract(self, monkeypatch):
        async def fake_build_ask_payload(**_kwargs):
            return {
                "question": "What should I do today?",
                "answer": "Hold AAPL and wait for the event window to clear.",
                "verdict": "hold",
                "horizon": "1w",
                "confidence": 0.58,
                "reasoning": ["Event timing dominates the setup."],
                "sources": [{"type": "news", "ticker": "AAPL"}],
                "generated_at": "2026-03-14T02:05:00Z",
                "freshness": "2026-03-14T02:05:00Z",
                "memo": {
                    "verdict": "hold",
                    "horizon": "1w",
                    "why": ["Event timing dominates the setup."],
                    "risks": ["Sources insuffisantes (moins de 2)."],
                    "confidence": 0.58,
                    "freshness": "2026-03-14T02:05:00Z",
                    "sources": [{"type": "news", "ticker": "AAPL"}],
                },
            }

        monkeypatch.setattr(copilot_route.copilot_service, "build_ask_payload", fake_build_ask_payload)

        client = _client()
        response = client.post(
            "/api/personal-finance/ask",
            json={"question": "What should I do today?", "tickers": ["AAPL"]},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload.get("ok") is True

        memo = payload["data"]
        assert memo["question"] == "What should I do today?"
        assert memo["answer"] == "Hold AAPL and wait for the event window to clear."
        assert memo["verdict"] == "hold"
        assert memo["horizon"] == "1w"
        assert memo["confidence"] == 0.58
        assert memo["sources"] == [{"type": "news", "ticker": "AAPL"}]
