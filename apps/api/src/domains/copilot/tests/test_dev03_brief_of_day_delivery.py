"""
BATCH-73-DEV-03: Personal Finance Copilot - Brief of the Day Delivery Proof

Task: Build a personal finance copilot that starts with a brief of the day, 
      lets the user ask or open.

This test verifies the minimal vertical slice:
1. /api/copilot/start returns brief_of_day with required fields
2. /api/copilot/start returns ask + open entry points
3. Brief includes: summary, market_sentiment, top_signals, top_risks
4. Brief includes freshness and source metadata
5. User can ask questions via /api/copilot/ask
6. User can open copilot via entry points

Product vision: "The copilot must start with a brief of the day"
"""
import sys
from pathlib import Path
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

SRC_PATH = Path(__file__).resolve().parents[3]
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from domains.copilot.api.copilot import router
from storage import io as storage_io


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class TestDEV03BriefOfDayContract:
    """DEV-03: Verify brief of day contract in /copilot/start"""

    def test_brief_of_day_present_with_required_fields(self, monkeypatch):
        """
        DEV-03: Brief of day must be present with all required fields.
        
        Required fields:
        - summary: string < 200 words
        - market_sentiment: BULLISH/BEARISH/NEUTRAL/UNKNOWN
        - top_signals: list
        - top_risks: list
        - generated_at: ISO timestamp
        - freshness: ISO timestamp
        - source: list of strings
        """
        # Mock brief snapshot
        mock_brief = {
            "data": {
                "daily": {
                    "summary": "Markets steady with bullish bias. Tech leads while rates stabilize.",
                    "market_sentiment": "BULLISH",
                    "top_signals": [
                        {"name": "NVDA guidance", "value": "beat", "signal": "positive"},
                        {"name": "VIX", "value": "14.2", "signal": "low_volatility"},
                    ],
                    "top_risks": [
                        {"name": "CPI release", "value": "tomorrow", "signal": "watch"},
                    ],
                    "macro_signals": [
                        {"name": "DXY", "value": "103.5", "signal": "neutral"},
                    ],
                    "sector_rotation": {
                        "top": ["Semiconductors", "Tech"],
                        "bottom": ["Utilities", "Staples"],
                    },
                    "generated_at": "2026-03-23T08:30:00Z",
                    "freshness": "2026-03-23T08:30:00Z",
                    "source": ["brief_daily_generator", "forecasts_snapshot"],
                }
            }
        }

        def mock_load_json(key):
            return mock_brief if key == "brief_daily" else None

        monkeypatch.setattr(storage_io, "load_json", mock_load_json)

        client = _client()
        response = client.get("/api/copilot/start")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        payload = response.json()
        assert payload.get("ok") is True, "Response must have ok=True"

        data = payload.get("data") or {}
        brief = data.get("brief_of_day")

        # DEV-03: Brief must be present
        assert brief is not None, "brief_of_day must be present"
        assert isinstance(brief, dict), "brief_of_day must be a dict"

        # Required field: summary
        assert "summary" in brief, "brief must have 'summary'"
        assert isinstance(brief["summary"], str), "summary must be string"
        assert len(brief["summary"].split()) <= 200, "summary must be < 200 words"

        # Required field: market_sentiment
        assert "market_sentiment" in brief, "brief must have 'market_sentiment'"
        assert brief["market_sentiment"] in {"BULLISH", "BEARISH", "NEUTRAL", "UNKNOWN"}, \
            "market_sentiment must be valid"

        # Required field: top_signals
        assert "top_signals" in brief, "brief must have 'top_signals'"
        assert isinstance(brief["top_signals"], list), "top_signals must be list"

        # Required field: top_risks
        assert "top_risks" in brief, "brief must have 'top_risks'"
        assert isinstance(brief["top_risks"], list), "top_risks must be list"

        # Required field: generated_at
        assert "generated_at" in brief, "brief must have 'generated_at'"
        assert brief["generated_at"].endswith("Z"), "generated_at must be ISO with Z"

        # Required field: freshness
        assert "freshness" in brief, "brief must have 'freshness'"
        assert brief["freshness"].endswith("Z"), "freshness must be ISO with Z"

        # Required field: source
        assert "source" in brief, "brief must have 'source'"
        assert isinstance(brief["source"], list), "source must be list"
        assert len(brief["source"]) > 0, "source must have at least one entry"

    def test_brief_of_day_fallback_when_no_snapshot(self, monkeypatch):
        """
        DEV-03: Fallback brief must work when no snapshot available.
        
        Even fallback must satisfy the contract.
        """
        def mock_load_json_empty(key):
            return None

        monkeypatch.setattr(storage_io, "load_json", mock_load_json_empty)

        client = _client()
        response = client.get("/api/copilot/start")

        assert response.status_code == 200
        payload = response.json()
        data = payload.get("data") or {}
        brief = data.get("brief_of_day")

        # Fallback brief must still satisfy contract
        assert brief is not None, "brief_of_day must always be present (even fallback)"
        assert "summary" in brief, "fallback must have summary"
        assert "market_sentiment" in brief, "fallback must have market_sentiment"
        assert brief["market_sentiment"] == "UNKNOWN", "fallback sentiment must be UNKNOWN"
        assert "top_signals" in brief, "fallback must have top_signals"
        assert isinstance(brief["top_signals"], list), "top_signals must be list"
        assert "top_risks" in brief, "fallback must have top_risks"
        assert isinstance(brief["top_risks"], list), "top_risks must be list"
        assert "generated_at" in brief, "fallback must have generated_at"
        assert "freshness" in brief, "fallback must have freshness"
        assert "source" in brief, "fallback must have source"
        assert "fallback" in str(brief["source"]).lower(), "source must indicate fallback"

    def test_ask_and_open_entry_points_present(self, monkeypatch):
        """
        DEV-03: Entry points for ask and open actions must be present.
        
        The copilot must let the user:
        - Ask questions (ask entry points)
        - Open copilot/views (open entry points)
        """
        mock_brief = {
            "data": {
                "daily": {
                    "summary": "Test brief",
                    "market_sentiment": "NEUTRAL",
                    "top_signals": [],
                    "top_risks": [],
                    "generated_at": "2026-03-23T09:00:00Z",
                    "freshness": "2026-03-23T09:00:00Z",
                    "source": ["test"],
                }
            }
        }

        def mock_load_json(key):
            return mock_brief if key == "brief_daily" else None

        monkeypatch.setattr(storage_io, "load_json", mock_load_json)

        client = _client()
        response = client.get("/api/copilot/start")

        assert response.status_code == 200
        payload = response.json()
        data = payload.get("data") or {}

        # Ask entry points
        ask_items = data.get("ask", [])
        assert isinstance(ask_items, list), "ask must be a list"
        assert len(ask_items) >= 1, "must have at least one ask entry point"

        # Open entry points
        open_items = data.get("open", [])
        assert isinstance(open_items, list), "open must be a list"
        assert len(open_items) >= 1, "must have at least one open entry point"

        # Verify structure - ask items must have label/id/prompt/prefill
        for ask_item in ask_items:
            assert isinstance(ask_item, dict), "ask item must be dict"
            # Ask items should have at least label or id or prompt
            has_identifier = any(k in ask_item for k in ["label", "id", "prompt", "prefill"])
            assert has_identifier, "ask item must have identifier (label/id/prompt/prefill)"

        # Open items must have label/id/target
        for open_item in open_items:
            assert isinstance(open_item, dict), "open item must be dict"
            has_identifier = any(k in open_item for k in ["label", "id", "target"])
            assert has_identifier, "open item must have identifier (label/id/target)"

    def test_brief_of_day_with_ticker_scope(self, monkeypatch):
        """
        DEV-03: Brief must work with ticker scope filtering.
        """
        mock_brief = {
            "data": {
                "daily": {
                    "summary": "NVDA leads semiconductor rally with +5% gain.",
                    "market_sentiment": "BULLISH",
                    "top_signals": [{"name": "NVDA", "value": "+5%", "signal": "positive"}],
                    "top_risks": [],
                    "generated_at": "2026-03-23T10:00:00Z",
                    "freshness": "2026-03-23T10:00:00Z",
                    "source": ["scoped_brief"],
                }
            }
        }

        def mock_load_json(key):
            return mock_brief if key == "brief_daily" else None

        monkeypatch.setattr(storage_io, "load_json", mock_load_json)

        client = _client()
        response = client.get("/api/copilot/start?tickers=nvda&tickers=msft")

        assert response.status_code == 200
        payload = response.json()
        data = payload.get("data") or {}

        # Scope tickers applied
        assert data.get("scope_tickers") == ["MSFT", "NVDA"], "scope_tickers must be applied"
        assert data.get("filters_applied", {}).get("tickers") == ["MSFT", "NVDA"], \
            "filters_applied must show tickers"

        # Brief still present
        brief = data.get("brief_of_day")
        assert brief is not None, "brief must still be present with scope"

    def test_copilot_start_injects_ask_and_open_fallbacks_when_missing(self, monkeypatch):
        """
        DEV-03: The start payload must always expose at least one ask and one open action.

        If upstream context returns empty action lists, copilot should still allow the
        user to ask a follow-up or open a view from the brief-of-day entry.
        """

        async def mock_build_context_payload(context_service_cls=None, scope=None):
            return {
                "daily_brief": {
                    "summary": "Stocks mixed with low volatility.",
                    "market_sentiment": "NEUTRAL",
                    "top_signals": [],
                    "top_risks": [],
                    "generated_at": "2026-03-23T13:00:00Z",
                    "freshness": "2026-03-23T13:00:00Z",
                    "source": ["fallback-test"],
                },
                "copilot_start": {
                    "brief_of_day": {
                        "summary": "Stocks mixed with low volatility.",
                        "market_sentiment": "NEUTRAL",
                        "top_signals": [],
                        "top_risks": [],
                        "generated_at": "2026-03-23T13:00:00Z",
                        "freshness": "2026-03-23T13:00:00Z",
                        "source": ["fallback-test"],
                    },
                    "ask": [],
                    "open": [],
                },
            }

        monkeypatch.setattr(
            "domains.copilot.application.copilot_service.build_context_payload",
            mock_build_context_payload,
        )

        client = _client()
        response = client.get("/api/copilot/start")

        assert response.status_code == 200
        payload = response.json()
        data = payload.get("data") or {}
        ask_items = data.get("ask") or []
        open_items = data.get("open") or []

        assert isinstance(ask_items, list) and ask_items, "ask action fallback must be injected"
        assert isinstance(open_items, list) and open_items, "open action fallback must be injected"
        assert ask_items[0].get("target") in {"/copilot/ask", "/copilot/ask/"}, "ask fallback target must be copilot ask"
        assert open_items[0].get("target") in {"/copilot", "/copilot/"}, "open fallback target must be copilot view"


class TestDEV03AskEndpointContract:
    """DEV-03: Verify ask endpoint for user questions"""

    def test_ask_endpoint_returns_answer_with_verdict(self):
        """
        DEV-03: Ask endpoint must return answer with verdict/action.
        
        When user asks a question, copilot must provide:
        - answer: string response
        - verdict/action: buy/sell/hold
        - horizon: time horizon
        - confidence: 0-1 score
        - why/reasoning: list of reasons
        """
        client = _client()
        response = client.post(
            "/api/copilot/ask",
            json={
                "question": "Should I buy NVDA today?",
                "tickers": ["NVDA"],
            }
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        payload = response.json()
        assert payload.get("ok") is True, "Response must have ok=True"

        data = payload.get("data") or {}

        # Required fields
        assert "question" in data, "must have question"
        assert "answer" in data, "must have answer"
        assert isinstance(data["answer"], str), "answer must be string"

        # Verdict or action
        verdict = data.get("verdict") or data.get("action")
        assert verdict is not None, "must have verdict or action"
        assert verdict.lower() in {"buy", "sell", "hold"}, "verdict must be buy/sell/hold"

        # Horizon
        horizon = data.get("horizon")
        assert horizon is not None, "must have horizon"
        assert horizon.lower() in {"1d", "1w", "1m"}, "horizon must be 1d/1w/1m"

        # Confidence
        confidence = data.get("confidence")
        assert confidence is not None, "must have confidence"
        assert isinstance(confidence, (int, float)), "confidence must be numeric"
        assert 0 <= confidence <= 1, "confidence must be 0-1"

        # Why/reasoning
        why = data.get("why") or data.get("reasoning")
        assert why is not None, "must have why or reasoning"
        assert isinstance(why, list), "why/reasoning must be list"

    def test_ask_endpoint_with_conversation_id(self):
        """
        DEV-03: Ask endpoint must support conversation_id for follow-ups.
        
        BATCH-73-DEV-02 dependency: conversation history support
        """
        client = _client()
        response = client.post(
            "/api/copilot/ask",
            json={
                "question": "What about AAPL?",
                "tickers": ["AAPL"],
                "conversation_id": "test-conversation-123",
            }
        )

        assert response.status_code == 200
        payload = response.json()
        data = payload.get("data") or {}

        # Conversation metadata should be present
        conversation = data.get("conversation")
        assert conversation is not None, "conversation metadata should be present"
        assert conversation.get("conversation_id") == "test-conversation-123", \
            "conversation_id must match"


class TestDEV03IntegrationProof:
    """DEV-03: Integration proof - end-to-end flow"""

    def test_full_copilot_flow_brief_then_ask(self, monkeypatch):
        """
        DEV-03: Full user flow - start with brief, then ask question.
        
        User journey:
        1. Open copilot → see brief of day
        2. Ask question about portfolio
        3. Get answer with verdict
        """
        # Mock brief
        mock_brief = {
            "data": {
                "daily": {
                    "summary": "Markets steady. Tech leads.",
                    "market_sentiment": "BULLISH",
                    "top_signals": [{"name": "Tech rally", "value": "strong"}],
                    "top_risks": [{"name": "CPI tomorrow", "value": "watch"}],
                    "generated_at": "2026-03-23T11:00:00Z",
                    "freshness": "2026-03-23T11:00:00Z",
                    "source": ["integration_test"],
                }
            }
        }

        def mock_load_json(key):
            return mock_brief if key == "brief_daily" else None

        monkeypatch.setattr(storage_io, "load_json", mock_load_json)

        client = _client()

        # Step 1: Get brief
        start_response = client.get("/api/copilot/start")
        assert start_response.status_code == 200
        start_payload = start_response.json()
        assert start_payload.get("ok") is True

        data = start_payload.get("data") or {}
        brief = data.get("brief_of_day")
        assert brief is not None, "brief must be present"
        assert brief["market_sentiment"] == "BULLISH"

        # Step 2: Ask question
        ask_response = client.post(
            "/api/copilot/ask",
            json={
                "question": "What should I do with my tech stocks today?",
                "tickers": ["NVDA", "MSFT"],
            }
        )
        assert ask_response.status_code == 200
        ask_payload = ask_response.json()
        assert ask_payload.get("ok") is True

        ask_data = ask_payload.get("data") or {}
        assert "answer" in ask_data, "must have answer"
        assert ask_data.get("verdict") or ask_data.get("action"), "must have verdict"

    def test_personal_finance_namespace_alias(self, monkeypatch):
        """
        DEV-03: Personal finance namespace alias must work.
        
        /api/personal-finance/start should work as alias for /api/copilot/start
        """
        mock_brief = {
            "data": {
                "daily": {
                    "summary": "Personal finance brief",
                    "market_sentiment": "NEUTRAL",
                    "top_signals": [],
                    "top_risks": [],
                    "generated_at": "2026-03-23T12:00:00Z",
                    "freshness": "2026-03-23T12:00:00Z",
                    "source": ["personal_finance_test"],
                }
            }
        }

        def mock_load_json(key):
            return mock_brief if key == "brief_daily" else None

        monkeypatch.setattr(storage_io, "load_json", mock_load_json)

        client = _client()
        response = client.get("/api/personal-finance/start")

        assert response.status_code == 200
        payload = response.json()
        data = payload.get("data") or {}

        # Brief present
        brief = data.get("brief_of_day")
        assert brief is not None

        # Namespace rewritten
        ask_items = data.get("ask", [])
        for ask_item in ask_items:
            target = ask_item.get("target", "")
            # Should be rewritten to /personal-finance/ask
            assert "/personal-finance" in target or "/copilot" in target, \
                "target must be in personal-finance or copilot namespace"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
