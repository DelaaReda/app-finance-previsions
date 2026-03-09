"""
Test Copilot Decision Journal Service (BATCH-13-DEV-02)

Tests for decision logging and outcome feedback loop.
"""

import json
import pytest
import sys
from pathlib import Path
from unittest.mock import patch

# Setup paths for imports
SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domains.copilot.application.decision_journal import (
    log_copilot_decision,
    record_outcome_feedback,
    get_decision_journal,
    get_outcome_feedback,
    compute_metrics,
    _normalize_tickers,
    _coerce_horizon,
    _generate_decision_id,
    DECISION_JOURNAL_STORAGE_KEY,
    DECISION_OUTCOME_FEEDBACK_RECORDS_STORAGE_KEY,
)


class TestNormalizeTickers:
    def test_normalize_empty(self):
        assert _normalize_tickers(None) == []
        assert _normalize_tickers([]) == []

    def test_normalize_duplicates(self):
        assert _normalize_tickers(["AAPL", "aapl", "AAPL"]) == ["AAPL"]

    def test_normalize_sorts(self):
        assert _normalize_tickers(["TSLA", "AAPL", "GOOGL"]) == ["AAPL", "GOOGL", "TSLA"]

    def test_normalize_strips(self):
        assert _normalize_tickers([" AAPL ", "TSLA "]) == ["AAPL", "TSLA"]


class TestCoerceHorizon:
    def test_valid_horizons(self):
        assert _coerce_horizon("1d") == "1d"
        assert _coerce_horizon("1w") == "1w"
        assert _coerce_horizon("1m") == "1m"

    def test_invalid_horizon_defaults(self):
        assert _coerce_horizon("invalid") == "1d"
        assert _coerce_horizon(None) == "1d"
        assert _coerce_horizon("") == "1d"


class TestGenerateDecisionId:
    def test_generates_consistent_id(self):
        id1 = _generate_decision_id("Buy AAPL?", ["AAPL"], "2026-03-09T00:00:00Z")
        id2 = _generate_decision_id("Buy AAPL?", ["AAPL"], "2026-03-09T00:00:00Z")
        assert id1 == id2
        assert len(id1) == 16

    def test_different_questions_different_ids(self):
        id1 = _generate_decision_id("Buy AAPL?", ["AAPL"], "2026-03-09T00:00:00Z")
        id2 = _generate_decision_id("Sell AAPL?", ["AAPL"], "2026-03-09T00:00:00Z")
        assert id1 != id2


class TestLogCopilotDecision:
    @patch('domains.copilot.application.decision_journal._decision_entries_dir')
    @patch('domains.copilot.application.decision_journal.save_json')
    def test_log_decision_success(self, mock_save, mock_entries_dir, tmp_path):
        mock_entries_dir.return_value = tmp_path / "entries"
        mock_entries_dir.return_value.mkdir(parents=True, exist_ok=True)
        mock_save.return_value = tmp_path / "store.json"

        result = log_copilot_decision(
            question="Should I buy AAPL?",
            answer="Yes, AAPL looks strong",
            verdict="buy",
            confidence=0.85,
            tickers=["AAPL"],
            horizon="1d",
            reasoning="Strong earnings expected",
            risk_level="medium",
            model="gpt-4",
        )

        assert result["status"] == "recorded"
        assert "decision_id" in result
        assert result["horizon"] == "1d"
        assert result["verdict"] == "buy"
        assert result["confidence"] == 0.85
        assert result["tickers"] == ["AAPL"]

        # Verify file was created
        entries_dir = mock_entries_dir.return_value
        entry_files = list(entries_dir.glob("*.json"))
        assert len(entry_files) == 1

        # Verify content
        with open(entry_files[0]) as f:
            entry = json.load(f)
        assert entry["verdict"] == "buy"
        assert entry["horizon"] == "1d"
        assert entry["outcome"]["status"] == "pending"

    def test_log_decision_verdict_coercion(self):
        """Test that verdicts are normalized."""
        with patch('domains.copilot.application.decision_journal._decision_entries_dir') as mock_dir:
            with patch('domains.copilot.application.decision_journal.save_json'):
                mock_dir.return_value = Path("/tmp/test_entries")
                mock_dir.return_value.mkdir(parents=True, exist_ok=True)
                
                result = log_copilot_decision(
                    question="Test",
                    answer="Test",
                    verdict="BUY",  # uppercase
                    confidence=0.5,
                )
                assert result["verdict"] == "buy"


class TestRecordOutcomeFeedback:
    @patch('domains.copilot.application.decision_journal._load_outcome_feedback_records')
    @patch('domains.copilot.application.decision_journal._save_outcome_feedback_records')
    def test_record_feedback_success(self, mock_save, mock_load, tmp_path):
        mock_load.return_value = []
        mock_save.return_value = tmp_path / "feedback.json"

        result = record_outcome_feedback(
            decision_id="abc123",
            horizon="1d",
            status="resolved",
            actual_return=0.05,
            predicted_return=0.03,
            notes="Beat expectations",
        )

        assert result["status"] == "recorded"
        assert "record_id" in result
        assert result["decision_id"] == "abc123"
        assert result["horizon"] == "1d"
        assert result["stored_records"] == 1


class TestGetDecisionJournal:
    def test_get_empty_journal(self, tmp_path):
        entries_dir = tmp_path / "entries"
        entries_dir.mkdir(parents=True, exist_ok=True)
        
        with patch('domains.copilot.application.decision_journal._decision_entries_dir') as mock_dir:
            mock_dir.return_value = entries_dir
            
            result = get_decision_journal(limit=50)
            
            assert result["count"] == 0
            assert result["entries"] == []

    def test_get_journal_with_entries(self, tmp_path):
        entries_dir = tmp_path / "entries"
        entries_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test entries
        entry1 = {
            "decision_id": "test1",
            "recorded_at": "2026-03-09T00:00:00Z",
            "verdict": "buy",
            "horizon": "1d",
            "tickers": ["AAPL"],
        }
        entry2 = {
            "decision_id": "test2",
            "recorded_at": "2026-03-09T01:00:00Z",
            "verdict": "sell",
            "horizon": "1w",
            "tickers": ["TSLA"],
        }
        
        with open(entries_dir / "test1.json", 'w') as f:
            json.dump(entry1, f)
        with open(entries_dir / "test2.json", 'w') as f:
            json.dump(entry2, f)
        
        with patch('domains.copilot.application.decision_journal._decision_entries_dir') as mock_dir:
            mock_dir.return_value = entries_dir
            
            result = get_decision_journal(limit=50)
            
            assert result["count"] == 2
            assert len(result["entries"]) == 2
            
            # Test filtering by verdict
            result_buy = get_decision_journal(limit=50, verdict="buy")
            assert result_buy["filtered_count"] == 1
            assert result_buy["entries"][0]["verdict"] == "buy"
            
            # Test filtering by ticker
            result_tsla = get_decision_journal(limit=50, tickers=["TSLA"])
            assert result_tsla["filtered_count"] == 1


class TestGetOutcomeFeedback:
    @patch('domains.copilot.application.decision_journal._load_outcome_feedback_records')
    def test_get_feedback_empty(self, mock_load):
        mock_load.return_value = []
        
        result = get_outcome_feedback(limit=200)
        
        assert result["count"] == 0
        assert result["records"] == []

    @patch('domains.copilot.application.decision_journal._load_outcome_feedback_records')
    def test_get_feedback_with_records(self, mock_load):
        mock_load.return_value = [
            {
                "record_id": "rec1",
                "decision_id": "dec1",
                "horizon": "1d",
                "status": "resolved",
                "recorded_at": "2026-03-09T00:00:00Z",
            },
            {
                "record_id": "rec2",
                "decision_id": "dec2",
                "horizon": "1w",
                "status": "pending",
                "recorded_at": "2026-03-09T01:00:00Z",
            },
        ]
        
        result = get_outcome_feedback(limit=200)
        
        assert result["count"] == 2
        assert len(result["records"]) == 2
        
        # Test filtering by status
        result_resolved = get_outcome_feedback(status="resolved")
        assert result_resolved["filtered_count"] == 1


class TestComputeMetrics:
    @patch('domains.copilot.application.decision_journal._load_outcome_feedback_records')
    def test_compute_metrics_empty(self, mock_load):
        mock_load.return_value = []
        
        result = compute_metrics()
        
        assert "metrics" in result
        assert result["total_feedback_records"] == 0

    @patch('domains.copilot.application.decision_journal._load_outcome_feedback_records')
    def test_compute_metrics_with_data(self, mock_load):
        mock_load.return_value = [
            {
                "decision_id": "dec1",
                "horizon": "1d",
                "status": "resolved",
                "actual_return": 0.05,
                "predicted_return": 0.03,
            },
            {
                "decision_id": "dec2",
                "horizon": "1d",
                "status": "resolved",
                "actual_return": -0.02,
                "predicted_return": 0.01,
            },
        ]
        
        result = compute_metrics()
        
        assert "1d" in result["metrics"]
        metrics_1d = result["metrics"]["1d"]
        assert metrics_1d["resolved_count"] == 2
        # First is hit (both positive), second is miss (different signs)
        assert metrics_1d["hit_rate"] == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
