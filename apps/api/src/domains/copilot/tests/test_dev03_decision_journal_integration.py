"""
BATCH-73-DEV-03: Decision Journal Integration with Conversation Context

Verifies that copilot ask endpoint auto-logs decisions to the decision journal.
BATCH-73-DEV-03: Adds conversation_id linkage for decision-conversation tracking.

Minimal vertical slice test for delivery proof.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from domains.copilot.api.copilot import router


def _create_test_app():
    """Create FastAPI app with copilot router."""
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return app


def _client() -> TestClient:
    """Create test client."""
    return TestClient(_create_test_app())


class TestDecisionJournalIntegrationInAsk:
    """Tests that /api/copilot/ask auto-logs decisions to journal."""

    @patch('domains.copilot.application.decision_journal.log_copilot_decision')
    @patch('domains.copilot.application.copilot_service.build_ask_payload')
    def test_ask_auto_logs_decision(self, mock_build_ask, mock_log_decision):
        """Test that asking a question auto-logs to decision journal."""
        # Mock the ask payload response
        mock_build_ask.return_value = {
            "question": "Should I buy AAPL?",
            "answer": "Yes, AAPL looks strong with earnings coming up.",
            "verdict": "buy",
            "action": "buy",
            "horizon": "1w",
            "confidence": 0.75,
            "why": ["Strong earnings expected", "Technical breakout"],
            "risks": ["Earnings miss", "Market volatility"],
            "risk": {"level": "medium", "caveat": "Watch earnings date"},
            "sources": [{"type": "news", "url": "https://example.com"}],
            "tickers": ["AAPL"],
        }

        # Mock the decision journal response
        mock_log_decision.return_value = {
            "status": "recorded",
            "decision_id": "dev03test123",
            "recorded_at": "2026-03-22T12:00:00Z",
        }

        client = _client()
        response = client.post(
            "/api/copilot/ask",
            json={
                "question": "Should I buy AAPL?",
                "tickers": ["AAPL"],
                "max_sources": 5,
            },
        )

        # Verify ask endpoint still works
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["verdict"] == "buy"

        # Verify decision journal was called
        mock_log_decision.assert_called_once()
        call_kwargs = mock_log_decision.call_args[1]

        # Verify correct data was logged
        assert call_kwargs["question"] == "Should I buy AAPL?"
        assert call_kwargs["verdict"] == "buy"
        assert call_kwargs["confidence"] == 0.75
        assert call_kwargs["horizon"] == "1w"
        assert call_kwargs["tickers"] == ["AAPL"]
        assert call_kwargs["reasoning"] == "Strong earnings expected"
        assert call_kwargs["risk_level"] == "medium"
        assert len(call_kwargs["sources"]) == 1
        assert call_kwargs["model"] == "copilot_ask_route"

    @patch('domains.copilot.application.decision_journal.log_copilot_decision')
    @patch('domains.copilot.application.copilot_service.build_ask_payload')
    def test_ask_logs_decision_with_defaults(self, mock_build_ask, mock_log_decision):
        """Test that missing fields use sensible defaults."""
        mock_build_ask.return_value = {
            "question": "What about TSLA?",
            "answer": "Wait for better entry.",
            "verdict": "hold",
        }

        mock_log_decision.return_value = {
            "status": "recorded",
            "decision_id": "dev03test456",
        }

        client = _client()
        response = client.post(
            "/api/copilot/ask",
            json={"question": "What about TSLA?"},
        )

        assert response.status_code == 200

        # Verify defaults were applied
        mock_log_decision.assert_called_once()
        call_kwargs = mock_log_decision.call_args[1]
        assert call_kwargs["verdict"] == "hold"
        assert call_kwargs["confidence"] == 0.5  # Default
        assert call_kwargs["horizon"] == "1w"  # Default
        assert call_kwargs["risk_level"] == "medium"  # Default
        assert call_kwargs["tickers"] is None

    @patch('domains.copilot.application.decision_journal.log_copilot_decision')
    @patch('domains.copilot.application.copilot_service.build_ask_payload')
    def test_ask_continues_on_log_failure(self, mock_build_ask, mock_log_decision):
        """Test that ask still returns response even if logging fails."""
        mock_build_ask.return_value = {
            "question": "NVDA outlook?",
            "answer": "Positive.",
            "verdict": "buy",
            "confidence": 0.8,
        }

        # Simulate logging failure
        mock_log_decision.side_effect = Exception("Storage unavailable")

        client = _client()
        response = client.post(
            "/api/copilot/ask",
            json={"question": "NVDA outlook?", "tickers": ["NVDA"]},
        )

        # Ask should still succeed
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["verdict"] == "buy"

        # Log was attempted
        mock_log_decision.assert_called_once()

    @patch('domains.copilot.application.decision_journal.log_copilot_decision')
    @patch('domains.copilot.application.copilot_service.build_ask_payload')
    def test_ask_logs_hold_verdict_correctly(self, mock_build_ask, mock_log_decision):
        """Test that hold verdicts are logged correctly."""
        mock_build_ask.return_value = {
            "question": "Should I sell MSFT?",
            "answer": "Hold for now.",
            "verdict": "hold",
            "horizon": "1m",
            "confidence": 0.6,
            "risk_level": "low",
        }

        mock_log_decision.return_value = {"status": "recorded"}

        client = _client()
        response = client.post(
            "/api/copilot/ask",
            json={
                "question": "Should I sell MSFT?",
                "tickers": ["MSFT"],
                "max_sources": 3,
            },
        )

        assert response.status_code == 200

        call_kwargs = mock_log_decision.call_args[1]
        assert call_kwargs["verdict"] == "hold"
        assert call_kwargs["horizon"] == "1m"
        assert call_kwargs["risk_level"] == "low"
        assert call_kwargs["tickers"] == ["MSFT"]


class TestDecisionJournalIntegrationEdgeCases:
    """Edge cases for decision journal integration."""

    @patch('domains.copilot.application.decision_journal.log_copilot_decision')
    @patch('domains.copilot.application.copilot_service.build_ask_payload')
    def test_ask_fallback_response_is_also_logged(self, mock_build_ask, mock_log_decision):
        """Test that fallback answers are journaled when the ask service fails."""
        mock_build_ask.side_effect = RuntimeError("upstream unavailable")
        mock_log_decision.return_value = {"status": "recorded"}

        client = _client()
        response = client.post(
            "/api/copilot/ask",
            json={"question": "Should I buy AAPL?", "tickers": ["AAPL"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["verdict"] == "hold"
        assert data["data"]["quality_status"] == "error"

        mock_log_decision.assert_called_once()
        call_kwargs = mock_log_decision.call_args[1]
        assert call_kwargs["question"] == "Should I buy AAPL?"
        assert call_kwargs["verdict"] == "hold"
        assert call_kwargs["confidence"] == 0.5
        assert call_kwargs["tickers"] == ["AAPL"]
        assert call_kwargs["horizon"] == "1w"
        assert call_kwargs["risk_level"] == "high"

    @patch('domains.copilot.application.decision_journal.log_copilot_decision')
    @patch('domains.copilot.application.copilot_service.build_ask_payload')
    def test_ask_with_verdict_variations(self, mock_build_ask, mock_log_decision):
        """Test various verdict formats are normalized."""
        test_cases = [
            ("BUY", "buy"),
            ("Sell", "sell"),
            ("HOLD", "hold"),
            ("Accumuler", "buy"),  # French
            ("Vendre", "sell"),
        ]

        for input_verdict, expected_verdict in test_cases:
            mock_build_ask.return_value = {
                "question": "Test?",
                "answer": "Test answer.",
                "verdict": input_verdict,
            }
            mock_log_decision.return_value = {"status": "recorded"}

            client = _client()
            response = client.post("/api/copilot/ask", json={"question": "Test?"})

            assert response.status_code == 200
            call_kwargs = mock_log_decision.call_args[1]
            assert call_kwargs["verdict"] == expected_verdict, f"Failed for {input_verdict}"

    @patch('domains.copilot.application.decision_journal.log_copilot_decision')
    @patch('domains.copilot.application.copilot_service.build_ask_payload')
    def test_ask_with_horizon_normalization(self, mock_build_ask, mock_log_decision):
        """Test that invalid horizons default to 1w."""
        test_horizons = [
            ("1d", "1d"),
            ("1w", "1w"),
            ("1m", "1m"),
            ("invalid", "1w"),  # Should default
            ("", "1w"),
            (None, "1w"),
        ]

        for input_horizon, expected_horizon in test_horizons:
            payload = {
                "question": "Test?",
                "answer": "Test.",
                "verdict": "hold",
            }
            if input_horizon is not None:
                payload["horizon"] = input_horizon

            mock_build_ask.return_value = payload
            mock_log_decision.return_value = {"status": "recorded"}

            client = _client()
            response = client.post("/api/copilot/ask", json={"question": "Test?"})

            assert response.status_code == 200
            call_kwargs = mock_log_decision.call_args[1]
            assert call_kwargs["horizon"] == expected_horizon, f"Failed for {input_horizon}"


class TestDecisionJournalConversationLinkage:
    """BATCH-73-DEV-03: Tests for conversation_id linkage in decision journal."""

    @patch('domains.copilot.application.decision_journal.log_copilot_decision')
    @patch('domains.copilot.application.copilot_service.build_ask_payload')
    def test_ask_with_conversation_id_links_decision(self, mock_build_ask, mock_log_decision):
        """Test that asking with conversation_id stores it in decision metadata."""
        mock_build_ask.return_value = {
            "question": "Should I buy more NVDA?",
            "answer": "Yes, add to position.",
            "verdict": "buy",
            "confidence": 0.8,
        }

        mock_log_decision.return_value = {"status": "recorded"}

        client = _client()
        response = client.post(
            "/api/copilot/ask",
            json={
                "question": "Should I buy more NVDA?",
                "tickers": ["NVDA"],
                "conversation_id": "conv_test123",
            },
        )

        assert response.status_code == 200

        # Verify conversation_id was passed to decision journal
        mock_log_decision.assert_called_once()
        call_kwargs = mock_log_decision.call_args[1]
        assert call_kwargs["metadata"]["conversation_id"] == "conv_test123"
        assert call_kwargs["metadata"]["scope"] is None
        assert call_kwargs["question"] == "Should I buy more NVDA?"

    @patch('domains.copilot.application.decision_journal.log_copilot_decision')
    @patch('domains.copilot.application.copilot_service.build_ask_payload')
    def test_ask_without_conversation_id_has_no_linkage(self, mock_build_ask, mock_log_decision):
        """Test that asking without conversation_id doesn't include it in metadata."""
        mock_build_ask.return_value = {
            "question": "First question?",
            "answer": "Answer.",
            "verdict": "hold",
        }

        mock_log_decision.return_value = {"status": "recorded"}

        client = _client()
        response = client.post(
            "/api/copilot/ask",
            json={"question": "First question?"},
        )

        assert response.status_code == 200

        call_kwargs = mock_log_decision.call_args[1]
        assert "conversation_id" not in call_kwargs["metadata"]
        assert call_kwargs["metadata"]["scope"] is None

    @patch('domains.copilot.application.decision_journal.log_copilot_decision')
    @patch('domains.copilot.application.copilot_service.build_ask_payload')
    def test_ask_with_conversation_and_scope(self, mock_build_ask, mock_log_decision):
        """Test that both scope and conversation_id are preserved in metadata."""
        mock_build_ask.return_value = {
            "question": "Portfolio check?",
            "answer": "Rebalance tech.",
            "verdict": "sell",
            "confidence": 0.7,
        }

        mock_log_decision.return_value = {"status": "recorded"}

        client = _client()
        response = client.post(
            "/api/copilot/ask",
            json={
                "question": "Portfolio check?",
                "tickers": ["AAPL", "MSFT"],
                "conversation_id": "conv_portfolio456",
                "scope": {"portfolio_id": "port_123"},
            },
        )

        assert response.status_code == 200

        call_kwargs = mock_log_decision.call_args[1]
        assert call_kwargs["metadata"]["conversation_id"] == "conv_portfolio456"
        assert call_kwargs["metadata"]["scope"] == {"portfolio_id": "port_123"}
        assert call_kwargs["tickers"] == ["AAPL", "MSFT"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
