"""
HTTP API Route Tests for Copilot Decision Journal + Outcome Feedback Loop (BATCH-13-DEV-03)

Tests the FastAPI HTTP endpoints:
- POST /api/copilot/decision-journal/log
- POST /api/copilot/decision-journal/outcomes
- GET  /api/copilot/decision-journal
- GET  /api/copilot/decision-journal/outcomes
- GET  /api/copilot/decision-journal/metrics

Integration pattern: minimal vertical slice testing HTTP layer + service integration.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Setup paths for imports
SRC_PATH = Path(__file__).resolve().parents[3]
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from domains.copilot.api.copilot import router


def _create_test_app():
    """Create FastAPI app with copilot router."""
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return app


def _client() -> TestClient:
    """Create test client."""
    return TestClient(_create_test_app())


class TestDecisionJournalLogRoute:
    """Tests for POST /api/copilot/decision-journal/log"""

    def test_log_decision_success(self):
        """Test logging a decision via HTTP endpoint."""
        client = _client()

        with patch('domains.copilot.application.decision_journal.log_copilot_decision') as mock_log:
            mock_log.return_value = {
                "status": "recorded",
                "decision_id": "abc123def456",
                "recorded_at": "2026-03-09T12:00:00Z",
                "horizon": "1d",
                "verdict": "buy",
                "confidence": 0.85,
                "tickers": ["AAPL"],
            }

            response = client.post(
                "/api/copilot/decision-journal/log",
                json={
                    "question": "Should I buy AAPL?",
                    "answer": "Yes, AAPL looks strong",
                    "verdict": "buy",
                    "confidence": 0.85,
                    "tickers": ["AAPL"],
                    "horizon": "1d",
                    "reasoning": "Strong earnings expected",
                    "risk_level": "medium",
                    "model": "gpt-4",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert "data" in data
            assert data["data"]["decision_id"] == "abc123def456"
            assert data["data"]["status"] == "recorded"

            # Verify service was called with correct params
            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args[1]
            assert call_kwargs["question"] == "Should I buy AAPL?"
            assert call_kwargs["verdict"] == "buy"
            assert call_kwargs["tickers"] == ["AAPL"]

    def test_log_decision_defaults(self):
        """Test logging with default horizon and risk_level."""
        client = _client()

        with patch('domains.copilot.application.decision_journal.log_copilot_decision') as mock_log:
            mock_log.return_value = {
                "status": "recorded",
                "decision_id": "test123",
                "horizon": "1d",
                "verdict": "hold",
            }

            response = client.post(
                "/api/copilot/decision-journal/log",
                json={
                    "question": "What about TSLA?",
                    "answer": "Hold for now",
                    "verdict": "hold",
                    "confidence": 0.6,
                },
            )

            assert response.status_code == 200
            assert response.json()["ok"] is True

            # Verify defaults were applied
            call_kwargs = mock_log.call_args[1]
            assert call_kwargs["horizon"] == "1d"
            assert call_kwargs["risk_level"] == "medium"
            assert call_kwargs["model"] == "unknown"

    def test_log_decision_missing_fields(self):
        """Test validation rejects missing required fields."""
        client = _client()

        # Missing required 'question'
        response = client.post(
            "/api/copilot/decision-journal/log",
            json={
                "answer": "Some answer",
                "verdict": "buy",
                "confidence": 0.7,
            },
        )

        # FastAPI should reject with 422
        assert response.status_code == 422

    def test_log_decision_verdict_coercion(self):
        """Test that verdicts are normalized by service."""
        client = _client()

        with patch('domains.copilot.application.decision_journal.log_copilot_decision') as mock_log:
            mock_log.return_value = {
                "status": "recorded",
                "decision_id": "test456",
                "verdict": "buy",  # Normalized
            }

            response = client.post(
                "/api/copilot/decision-journal/log",
                json={
                    "question": "Buy AAPL?",
                    "answer": "Yes",
                    "verdict": "BUY",  # Uppercase
                    "confidence": 0.7,
                },
            )

            assert response.status_code == 200
            # Service should normalize
            call_kwargs = mock_log.call_args[1]
            assert call_kwargs["verdict"] == "BUY"  # Passed as-is, service normalizes


class TestOutcomeFeedbackRoute:
    """Tests for POST /api/copilot/decision-journal/outcomes"""

    def test_record_feedback_success(self):
        """Test recording outcome feedback via HTTP."""
        client = _client()

        with patch('domains.copilot.application.decision_journal.record_outcome_feedback') as mock_record:
            mock_record.return_value = {
                "status": "recorded",
                "record_id": "fb123",
                "decision_id": "abc123",
                "horizon": "1d",
                "stored_records": 1,
            }

            response = client.post(
                "/api/copilot/decision-journal/outcomes",
                json={
                    "decision_id": "abc123",
                    "horizon": "1d",
                    "status": "resolved",
                    "actual_return": 0.06,
                    "predicted_return": 0.05,
                    "notes": "Beat expectations",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["data"]["record_id"] == "fb123"

            mock_record.assert_called_once()
            call_kwargs = mock_record.call_args[1]
            assert call_kwargs["decision_id"] == "abc123"
            assert call_kwargs["actual_return"] == 0.06

    def test_record_feedback_minimal(self):
        """Test recording feedback with minimal fields."""
        client = _client()

        with patch('domains.copilot.application.decision_journal.record_outcome_feedback') as mock_record:
            mock_record.return_value = {
                "status": "recorded",
                "record_id": "fb456",
            }

            response = client.post(
                "/api/copilot/decision-journal/outcomes",
                json={
                    "decision_id": "xyz789",
                    "horizon": "1w",
                    "status": "pending",
                },
            )

            assert response.status_code == 200
            assert response.json()["ok"] is True

    def test_record_feedback_missing_required(self):
        """Test validation rejects missing required fields."""
        client = _client()

        # Missing 'decision_id'
        response = client.post(
            "/api/copilot/decision-journal/outcomes",
            json={
                "horizon": "1d",
                "status": "resolved",
            },
        )

        assert response.status_code == 422


class TestPaperTradeExecuteRoute:
    """Tests for POST /api/copilot/paper-trades/execute"""

    def test_execute_paper_trade_success(self):
        client = _client()

        with patch('domains.copilot.application.decision_journal.execute_paper_trade') as mock_execute:
            mock_execute.return_value = {
                "status": "recorded",
                "execution_id": "exec123",
                "decision_id": "abc123",
                "ticker": "AAPL",
                "side": "buy",
                "fill_assumptions": {"assumed_fill_price": 100.25},
                "pnl": {"unrealized": 16.49},
            }

            response = client.post(
                "/api/copilot/paper-trades/execute",
                json={
                    "decision_id": "abc123",
                    "ticker": "AAPL",
                    "side": "buy",
                    "quantity": 10,
                    "reference_price": 100,
                    "fee_bps": 10,
                    "slippage_bps": 25,
                    "market_price": 102,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["data"]["execution_id"] == "exec123"
            call_kwargs = mock_execute.call_args[1]
            assert call_kwargs["decision_id"] == "abc123"
            assert call_kwargs["fee_bps"] == 10

    def test_execute_paper_trade_requires_core_fields(self):
        client = _client()

        response = client.post(
            "/api/copilot/paper-trades/execute",
            json={
                "decision_id": "abc123",
                "ticker": "AAPL",
            },
        )

        assert response.status_code == 422


class TestGetDecisionJournalRoute:
    """Tests for GET /api/copilot/decision-journal"""

    def test_get_journal_empty(self):
        """Test retrieving empty journal."""
        client = _client()

        with patch('domains.copilot.application.decision_journal.get_decision_journal') as mock_get:
            mock_get.return_value = {
                "count": 0,
                "entries": [],
                "source": ["copilot_decision_journal_service"],
            }

            response = client.get("/api/copilot/decision-journal")

            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["data"]["count"] == 0

    def test_get_journal_with_filters(self):
        """Test journal retrieval with query filters."""
        client = _client()

        with patch('domains.copilot.application.decision_journal.get_decision_journal') as mock_get:
            mock_get.return_value = {
                "count": 5,
                "filtered_count": 2,
                "entries": [
                    {"decision_id": "d1", "verdict": "buy", "tickers": ["AAPL"]},
                    {"decision_id": "d2", "verdict": "buy", "tickers": ["AAPL"]},
                ],
            }

            response = client.get(
                "/api/copilot/decision-journal?tickers=AAPL&verdict=buy&horizon=1d&limit=100"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["data"]["filtered_count"] == 2

            # Verify filters passed to service
            mock_get.assert_called_once()
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["tickers"] == ["AAPL"]
            assert call_kwargs["verdict"] == "buy"
            assert call_kwargs["horizon"] == "1d"
            assert call_kwargs["limit"] == 100

    def test_get_journal_default_limit(self):
        """Test default limit is applied."""
        client = _client()

        with patch('domains.copilot.application.decision_journal.get_decision_journal') as mock_get:
            mock_get.return_value = {"count": 50, "entries": []}

            response = client.get("/api/copilot/decision-journal")

            assert response.status_code == 200
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["limit"] == 50  # Default


class TestGetOutcomeFeedbackRoute:
    """Tests for GET /api/copilot/decision-journal/outcomes"""

    def test_get_feedback_empty(self):
        """Test retrieving empty feedback records."""
        client = _client()

        with patch('domains.copilot.application.decision_journal.get_outcome_feedback') as mock_get:
            mock_get.return_value = {
                "count": 0,
                "records": [],
                "source": ["copilot_outcome_feedback_service"],
            }

            response = client.get("/api/copilot/decision-journal/outcomes")

            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["data"]["count"] == 0

    def test_get_feedback_with_filters(self):
        """Test feedback retrieval with query filters."""
        client = _client()

        with patch('domains.copilot.application.decision_journal.get_outcome_feedback') as mock_get:
            mock_get.return_value = {
                "count": 10,
                "filtered_count": 3,
                "records": [{"record_id": "r1"}, {"record_id": "r2"}, {"record_id": "r3"}],
            }

            response = client.get(
                "/api/copilot/decision-journal/outcomes?decision_id=abc123&horizon=1d&status=resolved"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["filtered_count"] == 3

            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["decision_id"] == "abc123"
            assert call_kwargs["horizon"] == "1d"
            assert call_kwargs["status"] == "resolved"


class TestDecisionJournalMetricsRoute:
    """Tests for GET /api/copilot/decision-journal/metrics"""

    def test_get_metrics_empty(self):
        """Test metrics with no feedback data."""
        client = _client()

        with patch('domains.copilot.application.decision_journal.compute_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "metrics": {
                    "1d": {"hit_rate": None, "calibration_error": None, "resolved_count": 0},
                    "1w": {"hit_rate": None, "calibration_error": None, "resolved_count": 0},
                    "1m": {"hit_rate": None, "calibration_error": None, "resolved_count": 0},
                },
                "total_feedback_records": 0,
            }

            response = client.get("/api/copilot/decision-journal/metrics")

            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["data"]["total_feedback_records"] == 0

    def test_get_metrics_with_data(self):
        """Test metrics with feedback data."""
        client = _client()

        with patch('domains.copilot.application.decision_journal.compute_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "metrics": {
                    "1d": {"hit_rate": 0.75, "calibration_error": 0.02, "resolved_count": 10},
                    "1w": {"hit_rate": 0.60, "calibration_error": 0.05, "resolved_count": 5},
                    "1m": {"hit_rate": 0.50, "calibration_error": 0.08, "resolved_count": 2},
                },
                "total_feedback_records": 17,
            }

            response = client.get("/api/copilot/decision-journal/metrics")

            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["data"]["total_feedback_records"] == 17
            assert data["data"]["metrics"]["1d"]["hit_rate"] == 0.75


class TestDecisionJournalEndToEnd:
    """End-to-end tests exercising full HTTP flow."""

    def test_full_loop_log_then_retrieve(self):
        """Test logging a decision and retrieving it."""
        client = _client()

        # Mock the log function
        decision_data = {
            "status": "recorded",
            "decision_id": "e2e12345678",
            "recorded_at": "2026-03-09T12:00:00Z",
            "horizon": "1d",
            "verdict": "buy",
            "confidence": 0.8,
            "tickers": ["TEST"],
        }

        with patch('domains.copilot.application.decision_journal.log_copilot_decision') as mock_log:
            mock_log.return_value = decision_data

            # Log decision
            log_response = client.post(
                "/api/copilot/decision-journal/log",
                json={
                    "question": "Test question",
                    "answer": "Test answer",
                    "verdict": "buy",
                    "confidence": 0.8,
                    "tickers": ["TEST"],
                },
            )

            assert log_response.status_code == 200
            assert log_response.json()["ok"] is True

        # Mock retrieval
        with patch('domains.copilot.application.decision_journal.get_decision_journal') as mock_get:
            mock_get.return_value = {
                "count": 1,
                "entries": [decision_data],
            }

            # Retrieve journal
            get_response = client.get("/api/copilot/decision-journal")

            assert get_response.status_code == 200
            data = get_response.json()
            assert data["ok"] is True
            assert data["data"]["count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
