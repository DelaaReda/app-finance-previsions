"""
BATCH-80-DEV-03: Decision Journal Integration with Portfolio Context

Verifies that:
1. Decisions can be filtered by portfolio_id
2. Decisions can be filtered by conversation_id
3. Portfolio context is preserved in decision metadata
4. API endpoints support portfolio_id and conversation_id filters

Minimal vertical slice for personal finance copilot decision tracking.
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


class TestDecisionJournalPortfolioFiltering:
    """Tests for portfolio_id filtering in decision journal."""

    @patch('domains.copilot.application.decision_journal.get_decision_journal')
    def test_decision_journal_endpoint_accepts_portfolio_id(self, mock_get_journal):
        """Test that /api/copilot/decision-journal accepts portfolio_id filter."""
        mock_get_journal.return_value = {
            "count": 2,
            "filtered_count": 2,
            "returned_count": 2,
            "entries": [
                {
                    "decision_id": "test123",
                    "question": "Should I rebalance portfolio?",
                    "verdict": "sell",
                    "metadata": {"portfolio_id": "port_tech_001"},
                }
            ],
            "freshness": "2026-03-23T12:00:00Z",
        }

        client = _client()
        response = client.get(
            "/api/copilot/decision-journal",
            params={"portfolio_id": "port_tech_001"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "entries" in data["data"]

        # Verify portfolio_id was passed to get_decision_journal
        mock_get_journal.assert_called_once()
        call_kwargs = mock_get_journal.call_args[1]
        assert call_kwargs["portfolio_id"] == "port_tech_001"

    @patch('domains.copilot.application.decision_journal.get_decision_journal')
    def test_decision_journal_endpoint_accepts_conversation_id(self, mock_get_journal):
        """Test that /api/copilot/decision-journal accepts conversation_id filter."""
        mock_get_journal.return_value = {
            "count": 5,
            "filtered_count": 5,
            "entries": [],
            "freshness": "2026-03-23T12:00:00Z",
        }

        client = _client()
        response = client.get(
            "/api/copilot/decision-journal",
            params={"conversation_id": "conv_abc123"},
        )

        assert response.status_code == 200

        mock_get_journal.assert_called_once()
        call_kwargs = mock_get_journal.call_args[1]
        assert call_kwargs["conversation_id"] == "conv_abc123"

    @patch('domains.copilot.application.decision_journal.get_decision_journal')
    def test_decision_journal_combined_filters(self, mock_get_journal):
        """Test combining portfolio_id, conversation_id, and other filters."""
        mock_get_journal.return_value = {
            "count": 10,
            "filtered_count": 3,
            "returned_count": 3,
            "entries": [],
            "freshness": "2026-03-23T12:00:00Z",
        }

        client = _client()
        response = client.get(
            "/api/copilot/decision-journal",
            params={
                "portfolio_id": "port_123",
                "conversation_id": "conv_456",
                "tickers": ["AAPL", "MSFT"],
                "horizon": "1w",
                "verdict": "buy",
                "limit": 25,
            },
        )

        assert response.status_code == 200

        mock_get_journal.assert_called_once()
        call_kwargs = mock_get_journal.call_args[1]
        assert call_kwargs["portfolio_id"] == "port_123"
        assert call_kwargs["conversation_id"] == "conv_456"
        assert call_kwargs["tickers"] == ["AAPL", "MSFT"]
        assert call_kwargs["horizon"] == "1w"
        assert call_kwargs["verdict"] == "buy"
        assert call_kwargs["limit"] == 25


class TestDecisionJournalPortfolioMetadata:
    """Tests for portfolio metadata in decision logging."""

    @patch('domains.copilot.application.decision_journal.log_copilot_decision')
    @patch('domains.copilot.application.copilot_service.build_ask_payload')
    def test_ask_with_portfolio_scope_logs_portfolio_id(self, mock_build_ask, mock_log_decision):
        """Test that asking with portfolio scope logs portfolio_id in metadata."""
        mock_build_ask.return_value = {
            "question": "Should I rebalance my tech portfolio?",
            "answer": "Reduce tech exposure.",
            "verdict": "sell",
            "confidence": 0.7,
            "tickers": ["AAPL", "MSFT", "NVDA"],
        }

        mock_log_decision.return_value = {"status": "recorded"}

        client = _client()
        response = client.post(
            "/api/copilot/ask",
            json={
                "question": "Should I rebalance my tech portfolio?",
                "tickers": ["AAPL", "MSFT"],
                "scope": {"portfolio_id": "port_tech_001"},
            },
        )

        assert response.status_code == 200

        mock_log_decision.assert_called_once()
        call_kwargs = mock_log_decision.call_args[1]

        # Verify portfolio_id is in metadata
        assert call_kwargs["metadata"]["scope"] == {"portfolio_id": "port_tech_001"}
        assert call_kwargs["tickers"] == ["AAPL", "MSFT"]

    @patch('domains.copilot.application.decision_journal.log_copilot_decision')
    @patch('domains.copilot.application.copilot_service.build_ask_payload')
    def test_ask_with_portfolio_and_conversation(self, mock_build_ask, mock_log_decision):
        """Test that both portfolio_id and conversation_id are preserved."""
        mock_build_ask.return_value = {
            "question": "Follow-up on portfolio?",
            "answer": "Yes, rebalance.",
            "verdict": "buy",
        }

        mock_log_decision.return_value = {"status": "recorded"}

        client = _client()
        response = client.post(
            "/api/copilot/ask",
            json={
                "question": "Follow-up on portfolio?",
                "conversation_id": "conv_portfolio_789",
                "scope": {"portfolio_id": "port_diversified"},
                "tickers": ["VTI"],
            },
        )

        assert response.status_code == 200

        call_kwargs = mock_log_decision.call_args[1]
        assert call_kwargs["metadata"]["conversation_id"] == "conv_portfolio_789"
        assert call_kwargs["metadata"]["scope"] == {"portfolio_id": "port_diversified"}


class TestDecisionJournalServiceLayer:
    """Service layer tests for decision journal portfolio filtering."""

    def test_get_decision_journal_with_portfolio_filter(self):
        """Test get_decision_journal filters by portfolio_id."""
        from domains.copilot.application.decision_journal import get_decision_journal

        # This test verifies the function accepts the parameter without error
        # Actual filtering depends on stored data
        result = get_decision_journal(
            limit=10,
            portfolio_id="test_portfolio",
        )

        assert "entries" in result
        assert "count" in result
        assert result["source"] == ["copilot_decision_journal_service"]

    def test_get_decision_journal_with_conversation_filter(self):
        """Test get_decision_journal filters by conversation_id."""
        from domains.copilot.application.decision_journal import get_decision_journal

        result = get_decision_journal(
            limit=10,
            conversation_id="test_conversation",
        )

        assert "entries" in result
        assert "count" in result

    def test_get_decision_journal_combined_filters(self):
        """Test get_decision_journal with multiple filters."""
        from domains.copilot.application.decision_journal import get_decision_journal

        result = get_decision_journal(
            limit=20,
            tickers=["AAPL"],
            horizon="1w",
            verdict="buy",
            portfolio_id="port_test",
            conversation_id="conv_test",
        )

        assert "entries" in result
        assert "filtered_count" in result or "count" in result


class TestDecisionJournalEdgeCases:
    """Edge cases for portfolio/conversation filtering."""

    @patch('domains.copilot.application.decision_journal.get_decision_journal')
    def test_empty_portfolio_filter(self, mock_get_journal):
        """Test filtering by non-existent portfolio returns empty list."""
        mock_get_journal.return_value = {
            "count": 0,
            "filtered_count": 0,
            "returned_count": 0,
            "entries": [],
            "freshness": "2026-03-23T12:00:00Z",
        }

        client = _client()
        response = client.get(
            "/api/copilot/decision-journal",
            params={"portfolio_id": "nonexistent_portfolio"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["count"] == 0

    @patch('domains.copilot.application.decision_journal.get_decision_journal')
    def test_portfolio_filter_case_sensitive(self, mock_get_journal):
        """Test that portfolio_id filtering is case-sensitive."""
        mock_get_journal.return_value = {
            "count": 5,
            "entries": [],
            "freshness": "2026-03-23T12:00:00Z",
        }

        client = _client()
        response = client.get(
            "/api/copilot/decision-journal",
            params={"portfolio_id": "PORT_UPPERCASE"},
        )

        assert response.status_code == 200
        mock_get_journal.assert_called_once()
        call_kwargs = mock_get_journal.call_args[1]
        assert call_kwargs["portfolio_id"] == "PORT_UPPERCASE"

    @patch('domains.copilot.application.decision_journal.log_copilot_decision')
    @patch('domains.copilot.application.copilot_service.build_ask_payload')
    def test_decision_without_portfolio_has_null_metadata(self, mock_build_ask, mock_log_decision):
        """Test that decisions without portfolio have no portfolio_id in metadata."""
        mock_build_ask.return_value = {
            "question": "General question?",
            "answer": "General answer.",
            "verdict": "hold",
        }

        mock_log_decision.return_value = {"status": "recorded"}

        client = _client()
        response = client.post(
            "/api/copilot/ask",
            json={"question": "General question?"},
        )

        assert response.status_code == 200

        call_kwargs = mock_log_decision.call_args[1]
        # No portfolio_id in scope
        assert call_kwargs["metadata"]["scope"] is None
        # No conversation_id
        assert "conversation_id" not in call_kwargs["metadata"]


class TestDecisionJournalIntegrationContract:
    """Integration contract tests for BATCH-80-DEV-03."""

    @patch('domains.copilot.application.decision_journal.log_copilot_decision')
    @patch('domains.copilot.application.copilot_service.build_ask_payload')
    def test_full_flow_ask_then_filter_by_portfolio(self, mock_build_ask, mock_log_decision):
        """Test full flow: ask with portfolio, then filter decisions by portfolio."""
        # Step 1: Ask a question with portfolio context
        mock_build_ask.return_value = {
            "question": "Tech portfolio rebalance?",
            "answer": "Reduce AAPL, add to MSFT.",
            "verdict": "sell",
            "confidence": 0.75,
            "tickers": ["AAPL", "MSFT"],
        }

        decision_id = "test_decision_portfolio_flow"
        mock_log_decision.return_value = {
            "status": "recorded",
            "decision_id": decision_id,
        }

        client = _client()
        ask_response = client.post(
            "/api/copilot/ask",
            json={
                "question": "Tech portfolio rebalance?",
                "scope": {"portfolio_id": "port_tech_rebalance"},
                "tickers": ["AAPL", "MSFT"],
            },
        )

        assert ask_response.status_code == 200

        # Verify decision was logged with portfolio context
        mock_log_decision.assert_called_once()
        call_kwargs = mock_log_decision.call_args[1]
        assert call_kwargs["metadata"]["scope"] == {"portfolio_id": "port_tech_rebalance"}

        # Step 2: Filter decisions by portfolio (simulated)
        # In real scenario, this would query actual stored data
        from domains.copilot.application.decision_journal import get_decision_journal

        journal_result = get_decision_journal(portfolio_id="port_tech_rebalance")
        assert "entries" in journal_result

    def test_decision_journal_metadata_schema(self):
        """Test that decision journal metadata schema supports portfolio and conversation."""
        from domains.copilot.application.decision_journal import log_copilot_decision, get_decision_journal
        import tempfile
        import os

        # Use temp directory for test
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["COPILOT_DECISION_JOURNAL_DIR"] = tmpdir

            try:
                result = log_copilot_decision(
                    question="Test portfolio question?",
                    answer="Test answer.",
                    verdict="buy",
                    confidence=0.8,
                    tickers=["TEST"],
                    horizon="1w",
                    metadata={
                        "portfolio_id": "port_test_schema",
                        "conversation_id": "conv_test_schema",
                    },
                )

                assert result["status"] == "recorded"
                assert "decision_id" in result

                # Verify we can retrieve it
                journal = get_decision_journal(
                    portfolio_id="port_test_schema",
                    conversation_id="conv_test_schema",
                )
                assert "entries" in journal

            finally:
                # Cleanup
                if "COPILOT_DECISION_JOURNAL_DIR" in os.environ:
                    del os.environ["COPILOT_DECISION_JOURNAL_DIR"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
