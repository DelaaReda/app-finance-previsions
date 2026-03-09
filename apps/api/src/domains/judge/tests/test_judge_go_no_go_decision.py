"""
GO/NO-GO decision logic tests for Judge robustness.

Tests the _judge_go_no_go function that determines whether a verdict
is eligible for display based on confidence, data quality, and health signals.

Decision criteria:
- GO: All signals healthy (llm_ok=True, no parse errors, confidence>=0.5, data_quality>=0.4, sufficient news, <3 data gaps)
- NO_GO: Any red flag detected

Coverage:
1. GO decision when all signals are healthy
2. NO_GO due to LLM provider failure
3. NO_GO due to parse validation failure
4. NO_GO due to low confidence (<0.5)
5. NO_GO due to insufficient data quality (<0.4)
6. NO_GO due to insufficient news count (<10)
7. NO_GO due to multiple data gaps (>=3)
8. NO_GO with multiple reasons (compound failures)
9. Edge case: confidence exactly at threshold (0.50)
10. Edge case: data quality exactly at threshold (0.40)
"""
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domains.judge.api.judge import _judge_go_no_go, JUDGE_NEWS_ITEMS_PER_TICKER


class TestJudgeGoNoGoDecision:
    """Test suite for GO/NO-GO decision logic."""

    def test_go_decision_all_signals_healthy(self):
        """GO when all health signals are green."""
        result = _judge_go_no_go(
            llm_ok=True,
            parsed_error=False,
            confidence=0.75,
            data_quality_score=0.65,
            news_count=15,
            data_needed=["options_flow"],
        )
        assert result["decision"] == "go"
        assert result["eligible"] is True
        assert result["reasons"] == []
        assert result["confidence"] == 0.75
        assert result["data_quality"] == 0.65

    def test_no_go_llm_provider_unhealthy(self):
        """NO_GO when LLM provider is not healthy."""
        result = _judge_go_no_go(
            llm_ok=False,
            parsed_error=False,
            confidence=0.80,
            data_quality_score=0.70,
            news_count=20,
            data_needed=[],
        )
        assert result["decision"] == "no_go"
        assert result["eligible"] is False
        assert "llm_provider_not_healthy" in result["reasons"]
        assert len(result["reasons"]) == 1

    def test_no_go_parse_validation_failed(self):
        """NO_GO when LLM response parsing failed."""
        result = _judge_go_no_go(
            llm_ok=True,
            parsed_error=True,
            confidence=0.70,
            data_quality_score=0.60,
            news_count=15,
            data_needed=[],
        )
        assert result["decision"] == "no_go"
        assert result["eligible"] is False
        assert "llm_payload_validation_failed" in result["reasons"]

    def test_no_go_low_confidence(self):
        """NO_GO when confidence below 0.50 threshold."""
        result = _judge_go_no_go(
            llm_ok=True,
            parsed_error=False,
            confidence=0.45,
            data_quality_score=0.60,
            news_count=15,
            data_needed=[],
        )
        assert result["decision"] == "no_go"
        assert result["eligible"] is False
        assert "low_confidence" in result["reasons"]

    def test_no_go_insufficient_data_quality(self):
        """NO_GO when data quality below 0.40 threshold."""
        result = _judge_go_no_go(
            llm_ok=True,
            parsed_error=False,
            confidence=0.70,
            data_quality_score=0.35,
            news_count=15,
            data_needed=[],
        )
        assert result["decision"] == "no_go"
        assert result["eligible"] is False
        assert "insufficient_data_quality" in result["reasons"]

    def test_no_go_insufficient_news_count(self):
        """NO_GO when news count below threshold (JUDGE_NEWS_ITEMS_PER_TICKER // 2)."""
        threshold = max(5, JUDGE_NEWS_ITEMS_PER_TICKER // 2)
        result = _judge_go_no_go(
            llm_ok=True,
            parsed_error=False,
            confidence=0.70,
            data_quality_score=0.60,
            news_count=threshold - 1,  # One below threshold
            data_needed=[],
        )
        assert result["decision"] == "no_go"
        assert result["eligible"] is False
        assert "insufficient_news" in result["reasons"]

    def test_no_go_multiple_data_gaps(self):
        """NO_GO when 3 or more data gaps detected."""
        result = _judge_go_no_go(
            llm_ok=True,
            parsed_error=False,
            confidence=0.70,
            data_quality_score=0.60,
            news_count=15,
            data_needed=["options_flow", "dark_pool", "insider_trades"],  # 3 gaps
        )
        assert result["decision"] == "no_go"
        assert result["eligible"] is False
        assert "multiple_data_gaps" in result["reasons"]

    def test_no_go_compound_failures(self):
        """NO_GO accumulates all failure reasons."""
        result = _judge_go_no_go(
            llm_ok=False,
            parsed_error=True,
            confidence=0.30,
            data_quality_score=0.20,
            news_count=3,
            data_needed=["a", "b", "c", "d"],  # 4 gaps
        )
        assert result["decision"] == "no_go"
        assert result["eligible"] is False
        assert len(result["reasons"]) == 6
        assert "llm_provider_not_healthy" in result["reasons"]
        assert "llm_payload_validation_failed" in result["reasons"]
        assert "low_confidence" in result["reasons"]
        assert "insufficient_data_quality" in result["reasons"]
        assert "insufficient_news" in result["reasons"]
        assert "multiple_data_gaps" in result["reasons"]

    def test_edge_case_confidence_at_threshold(self):
        """GO when confidence is exactly at 0.50 threshold (boundary inclusive)."""
        result = _judge_go_no_go(
            llm_ok=True,
            parsed_error=False,
            confidence=0.50,
            data_quality_score=0.60,
            news_count=15,
            data_needed=[],
        )
        assert result["decision"] == "go"
        assert result["eligible"] is True
        assert result["reasons"] == []

    def test_edge_case_data_quality_at_threshold(self):
        """GO when data quality is exactly at 0.40 threshold (boundary inclusive)."""
        result = _judge_go_no_go(
            llm_ok=True,
            parsed_error=False,
            confidence=0.60,
            data_quality_score=0.40,
            news_count=15,
            data_needed=[],
        )
        assert result["decision"] == "go"
        assert result["eligible"] is True
        assert result["reasons"] == []

    def test_confidence_clamping(self):
        """Confidence is clamped to [0.0, 1.0] range."""
        result = _judge_go_no_go(
            llm_ok=True,
            parsed_error=False,
            confidence=1.50,  # Invalid > 1.0
            data_quality_score=0.60,
            news_count=15,
            data_needed=[],
        )
        assert result["confidence"] == 1.0

        result = _judge_go_no_go(
            llm_ok=True,
            parsed_error=False,
            confidence=-0.20,  # Invalid < 0.0
            data_quality_score=0.60,
            news_count=15,
            data_needed=[],
        )
        assert result["confidence"] == 0.0

    def test_data_quality_clamping(self):
        """Data quality is clamped to [0.0, 1.0] range."""
        result = _judge_go_no_go(
            llm_ok=True,
            parsed_error=False,
            confidence=0.70,
            data_quality_score=1.80,  # Invalid > 1.0
            news_count=15,
            data_needed=[],
        )
        assert result["data_quality"] == 1.0

        result = _judge_go_no_go(
            llm_ok=True,
            parsed_error=False,
            confidence=0.70,
            data_quality_score=-0.30,  # Invalid < 0.0
            news_count=15,
            data_needed=[],
        )
        assert result["data_quality"] == 0.0

    def test_go_with_minimal_data_gap(self):
        """GO when only 1-2 data gaps (below threshold of 3)."""
        result = _judge_go_no_go(
            llm_ok=True,
            parsed_error=False,
            confidence=0.70,
            data_quality_score=0.60,
            news_count=15,
            data_needed=["options_flow", "dark_pool"],  # 2 gaps - acceptable
        )
        assert result["decision"] == "go"
        assert result["eligible"] is True
        assert result["reasons"] == []

    def test_go_at_news_threshold_boundary(self):
        """GO when news count is exactly at threshold."""
        threshold = max(5, JUDGE_NEWS_ITEMS_PER_TICKER // 2)
        result = _judge_go_no_go(
            llm_ok=True,
            parsed_error=False,
            confidence=0.70,
            data_quality_score=0.60,
            news_count=threshold,  # Exactly at threshold
            data_needed=[],
        )
        assert result["decision"] == "go"
        assert result["eligible"] is True
        assert result["reasons"] == []

    def test_empty_data_needed_list_does_not_trigger_gap(self):
        """Empty data_needed list does not trigger multiple_data_gaps."""
        result = _judge_go_no_go(
            llm_ok=True,
            parsed_error=False,
            confidence=0.70,
            data_quality_score=0.60,
            news_count=15,
            data_needed=[],  # Empty list
        )
        assert result["decision"] == "go"
        assert "multiple_data_gaps" not in result["reasons"]

    def test_none_data_needed_does_not_trigger_gap(self):
        """None data_needed does not trigger multiple_data_gaps."""
        result = _judge_go_no_go(
            llm_ok=True,
            parsed_error=False,
            confidence=0.70,
            data_quality_score=0.60,
            news_count=15,
            data_needed=None,
        )
        assert result["decision"] == "go"
        assert "multiple_data_gaps" not in result["reasons"]


if __name__ == "__main__":
    # Run tests with pytest-style output
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
