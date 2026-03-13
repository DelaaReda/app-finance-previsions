"""
BATCH-23-DEV-03: Tax, Fees, and Slippage Awareness - Targeted Test

Verifies that weekly brief signals include cost_awareness fields.
"""
import pytest
import sys
from pathlib import Path

# Add src directory to path for imports
src_path = str(Path(__file__).parent.parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from platform.legacy.jobs.weekly_brief import generate_signal_from_forecast


class TestWeeklyBriefCostAwareness:
    """BATCH-23-DEV-03: Verify cost awareness in brief signals."""

    def test_generate_signal_includes_cost_awareness_fields(self):
        """Signal from forecast should include tax/fee/slippage awareness."""
        forecast = {
            "ticker": "AAPL",
            "direction": "up",
            "confidence": 0.74,
            "expected_return": 0.018,
            "horizon": "1w",
            "reasoning": "Trend remains constructive.",
        }

        signal = generate_signal_from_forecast(forecast)

        # Core signal fields
        assert signal["ticker"] == "AAPL"
        assert signal["type"] == "BULLISH"
        assert signal["confidence"] == 0.74
        assert signal["expected_return"] == 0.018

        # BATCH-23-DEV-03: Cost awareness fields
        assert "cost_awareness" in signal
        cost = signal["cost_awareness"]

        assert "gross_expected_return_pct" in cost
        assert "net_expected_return_pct" in cost
        assert "fee_bps" in cost
        assert "slippage_bps" in cost
        assert "estimated_tax_drag_bps" in cost
        assert "total_cost_bps" in cost
        assert "tax_bucket" in cost
        assert "tax_impact" in cost
        assert "edge_status" in cost

        # Flattened fields for UI convenience
        assert signal["gross_expected_return_pct"] == cost["gross_expected_return_pct"]
        assert signal["net_expected_return_pct"] == cost["net_expected_return_pct"]
        assert signal["fee_bps"] == cost["fee_bps"]
        assert signal["slippage_bps"] == cost["slippage_bps"]

    def test_generate_signal_detects_cost_overwhelm_edge(self):
        """Signal should warn when costs overwhelm small edge."""
        forecast = {
            "ticker": "IEF",
            "direction": "up",
            "confidence": 0.63,
            "expected_return": 0.0011,  # Very small edge
            "horizon": "1w",
            "reasoning": "Defensive ballast.",
        }

        signal = generate_signal_from_forecast(forecast)

        assert "cost_awareness" in signal
        cost = signal["cost_awareness"]

        # Small edge should be flagged
        assert cost.get("warning") == "Costs overwhelm edge"
        assert cost.get("edge_status") == "eroded"
        assert signal["warning"] == "Costs overwhelm edge"
        assert signal["edge_status"] == "eroded"

    def test_generate_signal_handles_missing_import_gracefully(self):
        """Signal generation should not crash if judge_pipeline is unavailable."""
        forecast = {
            "ticker": "TEST",
            "direction": "up",
            "confidence": 0.5,
            "expected_return": 0.01,
            "horizon": "1d",
        }

        # Should not raise even if build_net_edge_assessment is None
        signal = generate_signal_from_forecast(forecast)

        # Core fields must be present
        assert signal["ticker"] == "TEST"
        assert signal["type"] == "BULLISH"
        # cost_awareness may be None if import failed, but signal still valid
        # (graceful degradation)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
