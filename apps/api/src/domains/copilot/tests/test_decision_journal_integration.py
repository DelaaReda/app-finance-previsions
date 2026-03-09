"""
Integration tests for Copilot Decision Journal + Outcome Feedback Loop (BATCH-13-DEV-03)

Verifies end-to-end flow:
1. Log copilot decision
2. Record outcome feedback at 1d/1w/1m horizons
3. Retrieve journal with attached feedback
4. Compute hit rate and calibration metrics

Integration test pattern: minimal vertical slice covering the complete feedback loop.
"""

import json
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

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
    _load_outcome_feedback_records,
    _save_outcome_feedback_records,
    DECISION_JOURNAL_STORAGE_KEY,
    DECISION_OUTCOME_FEEDBACK_RECORDS_STORAGE_KEY,
    FEEDBACK_HORIZONS,
)


class TestDecisionJournalIntegration:
    """End-to-end integration tests for decision journal + outcome feedback loop."""

    @pytest.fixture
    def temp_storage(self, tmp_path):
        """Create temporary storage for decision journal entries."""
        entries_dir = tmp_path / "entries"
        entries_dir.mkdir(parents=True, exist_ok=True)
        
        with patch('domains.copilot.application.decision_journal._decision_entries_dir') as mock_dir:
            mock_dir.return_value = entries_dir
            yield {
                'entries_dir': entries_dir,
                'tmp_path': tmp_path,
            }

    @pytest.fixture
    def mock_feedback_storage(self, tmp_path):
        """Mock outcome feedback storage."""
        feedback_file = tmp_path / "feedback_records.json"
        
        def fake_load():
            if not feedback_file.exists():
                return []
            with open(feedback_file) as f:
                data = json.load(f)
                return data.get("records", [])
        
        def fake_save(records, freshness):
            payload = {
                "schema_version": "copilot_outcome_feedback_v1",
                "record_mode": "append_only",
                "count": len(records),
                "records": records,
                "freshness": freshness,
            }
            with open(feedback_file, 'w') as f:
                json.dump(payload, f, indent=2)
            return feedback_file
        
        with patch('domains.copilot.application.decision_journal._load_outcome_feedback_records', side_effect=fake_load):
            with patch('domains.copilot.application.decision_journal._save_outcome_feedback_records', side_effect=fake_save):
                yield {
                    'feedback_file': feedback_file,
                    'tmp_path': tmp_path,
                }

    def test_full_feedback_loop_1d_horizon(self, temp_storage, mock_feedback_storage):
        """Test complete feedback loop: log decision -> record outcome -> verify metrics."""
        
        # Step 1: Log a copilot decision
        decision_result = log_copilot_decision(
            question="Should I buy AAPL?",
            answer="Yes, AAPL looks strong with expected 5% return",
            verdict="buy",
            confidence=0.75,
            tickers=["AAPL"],
            horizon="1d",
            reasoning="Strong earnings expected, technical breakout",
            risk_level="medium",
            model="gpt-4",
        )
        
        assert decision_result["status"] == "recorded"
        decision_id = decision_result["decision_id"]
        assert len(decision_id) == 16
        
        # Step 2: Verify decision appears in journal
        journal = get_decision_journal(limit=50)
        assert journal["count"] == 1
        assert journal["entries"][0]["decision_id"] == decision_id
        assert journal["entries"][0]["verdict"] == "buy"
        assert journal["entries"][0]["outcome"]["status"] == "pending"
        
        # Step 3: Record outcome feedback (simulating 1 day later)
        feedback_result = record_outcome_feedback(
            decision_id=decision_id,
            horizon="1d",
            status="resolved",
            actual_return=0.06,  # 6% actual return
            predicted_return=0.05,  # Predicted 5%
            notes="Beat expectations on strong earnings",
        )
        
        assert feedback_result["status"] == "recorded"
        assert feedback_result["decision_id"] == decision_id
        assert "record_id" in feedback_result
        
        # Step 4: Verify feedback record exists
        feedback_records = get_outcome_feedback(decision_id=decision_id)
        assert feedback_records["count"] == 1
        assert feedback_records["records"][0]["status"] == "resolved"
        assert feedback_records["records"][0]["actual_return"] == 0.06
        
        # Step 5: Compute metrics - should show hit (same sign)
        metrics = compute_metrics()
        assert metrics["total_feedback_records"] == 1
        assert "1d" in metrics["metrics"]
        
        metrics_1d = metrics["metrics"]["1d"]
        assert metrics_1d["resolved_count"] == 1
        assert metrics_1d["hit_rate"] == 1.0  # Both positive = hit
        assert abs(metrics_1d["calibration_error"] - 0.01) < 0.001  # |0.06 - 0.05|

    def test_feedback_loop_multiple_horizons(self, temp_storage, mock_feedback_storage):
        """Test decisions with multiple horizons (1d, 1w, 1m)."""
        
        # Log decisions with different horizons
        decisions = []
        for horizon in FEEDBACK_HORIZONS:
            result = log_copilot_decision(
                question=f"Test decision for {horizon}",
                answer=f"Test answer for {horizon}",
                verdict="buy",
                confidence=0.7,
                tickers=["TEST"],
                horizon=horizon,
                model="test",
            )
            decisions.append(result)
        
        # Verify all decisions logged
        journal = get_decision_journal(limit=50)
        assert journal["count"] == 3
        
        # Record feedback for each horizon
        for i, horizon in enumerate(FEEDBACK_HORIZONS):
            # Alternate hits and misses
            actual = 0.05 if i % 2 == 0 else -0.03
            predicted = 0.04  # Always predicted positive
            
            record_outcome_feedback(
                decision_id=decisions[i]["decision_id"],
                horizon=horizon,
                status="resolved",
                actual_return=actual,
                predicted_return=predicted,
                notes=f"Test feedback for {horizon}",
            )
        
        # Verify metrics by horizon
        metrics = compute_metrics()
        
        for horizon in FEEDBACK_HORIZONS:
            assert horizon in metrics["metrics"]
            h_metrics = metrics["metrics"][horizon]
            assert h_metrics["resolved_count"] == 1
            assert h_metrics["total_count"] == 1
        
        # Overall: 2 hits (1d, 1m positive), 1 miss (1w negative)
        total_resolved = sum(m["resolved_count"] for m in metrics["metrics"].values())
        assert total_resolved == 3

    def test_feedback_loop_miss_scenario(self, temp_storage, mock_feedback_storage):
        """Test scenario where prediction was wrong (miss)."""
        
        # Log a buy decision
        decision = log_copilot_decision(
            question="Buy TSLA?",
            answer="TSLA will go up 10%",
            verdict="buy",
            confidence=0.9,
            tickers=["TSLA"],
            horizon="1w",
            reasoning="Moon mission",
            model="gpt-4",
        )
        
        # Record outcome: predicted up, actually went down (miss)
        record_outcome_feedback(
            decision_id=decision["decision_id"],
            horizon="1w",
            status="resolved",
            actual_return=-0.15,  # Down 15%
            predicted_return=0.10,  # Predicted up 10%
            notes="Crashed on production issues",
        )
        
        # Verify miss in metrics
        metrics = compute_metrics()
        metrics_1w = metrics["metrics"]["1w"]
        
        assert metrics_1w["resolved_count"] == 1
        assert metrics_1w["hit_rate"] == 0.0  # Different signs = miss
        assert metrics_1w["calibration_error"] == 0.25  # |−0.15 − 0.10|

    def test_filtering_and_retrieval(self, temp_storage, mock_feedback_storage):
        """Test filtering journal by tickers, verdict, horizon."""
        
        # Create diverse set of decisions
        test_data = [
            {"ticker": "AAPL", "verdict": "buy", "horizon": "1d"},
            {"ticker": "TSLA", "verdict": "sell", "horizon": "1w"},
            {"ticker": "GOOGL", "verdict": "hold", "horizon": "1m"},
            {"ticker": "AAPL", "verdict": "sell", "horizon": "1d"},
        ]
        
        for data in test_data:
            log_copilot_decision(
                question=f"Test {data['ticker']} {data['verdict']}",
                answer="Test answer",
                verdict=data["verdict"],
                confidence=0.6,
                tickers=[data["ticker"]],
                horizon=data["horizon"],
                model="test",
            )
        
        # Test ticker filter
        aapl_journal = get_decision_journal(tickers=["AAPL"])
        assert aapl_journal["filtered_count"] == 2
        
        # Test verdict filter
        buy_journal = get_decision_journal(verdict="buy")
        assert buy_journal["filtered_count"] == 1
        
        # Test horizon filter
        horizon_journal = get_decision_journal(horizon="1d")
        assert horizon_journal["filtered_count"] == 2
        
        # Test combined filters
        combined = get_decision_journal(tickers=["AAPL"], verdict="buy")
        assert combined["filtered_count"] == 1

    def test_metrics_with_partial_feedback(self, temp_storage, mock_feedback_storage):
        """Test metrics when only some decisions have feedback."""
        
        # Log 5 decisions
        decision_ids = []
        for i in range(5):
            result = log_copilot_decision(
                question=f"Decision {i}",
                answer="Test",
                verdict="buy",
                confidence=0.7,
                tickers=["TEST"],
                horizon="1d",
                model="test",
            )
            decision_ids.append(result["decision_id"])
        
        # Record feedback for only 2 decisions
        record_outcome_feedback(
            decision_id=decision_ids[0],
            horizon="1d",
            status="resolved",
            actual_return=0.05,
            predicted_return=0.04,
        )
        record_outcome_feedback(
            decision_id=decision_ids[1],
            horizon="1d",
            status="resolved",
            actual_return=-0.02,
            predicted_return=0.03,
        )
        
        # Metrics should only count resolved
        metrics = compute_metrics()
        assert metrics["total_feedback_records"] == 2
        assert metrics["metrics"]["1d"]["resolved_count"] == 2
        # total_count reflects decisions with feedback, not all logged decisions
        assert metrics["metrics"]["1d"]["total_count"] == 2

    def test_append_only_feedback_records(self, temp_storage, mock_feedback_storage):
        """Verify feedback records are append-only (never overwrite)."""
        
        decision = log_copilot_decision(
            question="Test",
            answer="Test",
            verdict="buy",
            confidence=0.7,
            tickers=["TEST"],
            horizon="1d",
            model="test",
        )
        
        # Record multiple feedback entries for same decision
        for i in range(3):
            record_outcome_feedback(
                decision_id=decision["decision_id"],
                horizon="1d",
                status="resolved",
                actual_return=0.01 * (i + 1),
                predicted_return=0.02,
                notes=f"Update {i+1}",
            )
        
        # All records should exist (append-only)
        feedback = get_outcome_feedback(decision_id=decision["decision_id"])
        assert feedback["count"] == 3
        
        # Verify record mode
        assert feedback["record_mode"] == "append_only"


class TestDecisionJournalEdgeCases:
    """Edge cases and error handling."""

    @pytest.fixture
    def temp_storage(self, tmp_path):
        """Create temporary storage."""
        entries_dir = tmp_path / "entries"
        entries_dir.mkdir(parents=True, exist_ok=True)
        
        with patch('domains.copilot.application.decision_journal._decision_entries_dir') as mock_dir:
            mock_dir.return_value = entries_dir
            yield entries_dir

    def test_empty_journal(self, temp_storage):
        """Test retrieving empty journal."""
        journal = get_decision_journal()
        assert journal["count"] == 0
        assert journal["entries"] == []

    def test_invalid_horizon_defaults_to_1d(self, temp_storage, mock_feedback_storage=None):
        """Test that invalid horizon defaults to 1d."""
        if mock_feedback_storage:
            pass  # Use fixture if available
        
        with patch('domains.copilot.application.decision_journal._load_outcome_feedback_records', return_value=[]):
            with patch('domains.copilot.application.decision_journal._save_outcome_feedback_records', return_value=temp_storage / "tmp.json"):
                result = log_copilot_decision(
                    question="Test",
                    answer="Test",
                    verdict="buy",
                    confidence=0.7,
                    horizon="invalid",
                    model="test",
                )
                assert result["horizon"] == "1d"

    def test_verdict_coercion(self, temp_storage):
        """Test verdict normalization."""
        with patch('domains.copilot.application.decision_journal._load_outcome_feedback_records', return_value=[]):
            with patch('domains.copilot.application.decision_journal._save_outcome_feedback_records', return_value=temp_storage / "tmp.json"):
                # Test various verdict formats
                for verdict_input in ["BUY", "Buy", "buy", "SELL", "HOLD"]:
                    result = log_copilot_decision(
                        question="Test",
                        answer="Test",
                        verdict=verdict_input,
                        confidence=0.7,
                        model="test",
                    )
                    assert result["verdict"] in ["buy", "sell", "hold"]

    def test_ticker_deduplication(self, temp_storage):
        """Test ticker normalization and deduplication."""
        with patch('domains.copilot.application.decision_journal._load_outcome_feedback_records', return_value=[]):
            with patch('domains.copilot.application.decision_journal._save_outcome_feedback_records', return_value=temp_storage / "tmp.json"):
                result = log_copilot_decision(
                    question="Test",
                    answer="Test",
                    verdict="buy",
                    confidence=0.7,
                    tickers=["AAPL", "aapl", "AAPL", "  googl  "],
                    model="test",
                )
                assert result["tickers"] == ["AAPL", "GOOGL"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
