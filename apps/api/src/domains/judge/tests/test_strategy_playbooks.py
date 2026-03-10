"""
Test strategy playbooks builder function.

Minimal test coverage for the _build_strategy_playbook function
to ensure stable contract and decision logic.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports (following existing test patterns)
SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domains.judge.application.judge_endpoint_service import _build_strategy_playbook


class TestBuildStrategyPlaybook:
    """Test the strategy playbook builder."""

    def test_build_playbook_go_decision(self):
        """Test playbook with go decision."""
        verdict = {
            "ticker": "AAPL",
            "horizon": "1w",
            "confidence": 0.75,
            "expected_return": 0.05,
            "risk_level": "medium",
            "go_no_go": {"decision": "go", "reasons": ["Strong momentum", "Positive earnings"]},
            "summary": "Bullish signal detected",
            "actions": ["Buy calls", "Set stop loss at $150"],
        }

        playbook = _build_strategy_playbook(verdict, profile="equity_1w")

        assert playbook["ticker"] == "AAPL"
        assert playbook["horizon"] == "1w"
        assert playbook["profile"] == "equity_1w"
        assert playbook["decision"] == "go"
        assert playbook["confidence"] == 0.75
        assert playbook["expected_return"] == 0.05
        assert playbook["risk_level"] == "medium"
        assert "Strong momentum" in playbook["reasons"]
        assert "Buy calls" in playbook["recommended_actions"]
        assert "playbook_id" in playbook
        assert "AAPL:1w:go:equity_1w" in playbook["playbook_id"]

    def test_build_playbook_no_go_decision(self):
        """Test playbook with no_go decision."""
        verdict = {
            "ticker": "TSLA",
            "horizon": "1m",
            "confidence": 0.65,
            "expected_return": -0.08,
            "risk_level": "high",
            "go_no_go": {"decision": "no_go", "reasons": ["Overvalued", "Competition increasing"]},
            "summary": "Bearish outlook",
            "actions": ["Reduce position", "Hedge with puts"],
        }

        playbook = _build_strategy_playbook(verdict, profile="equity_1m")

        assert playbook["ticker"] == "TSLA"
        assert playbook["decision"] == "no_go"
        assert playbook["risk_level"] == "high"
        # Signal divergence detected: expected_return is negative but confidence is high (0.65)
        # This triggers signal_divergence conflict since signal logic would suggest no_go but confidence is above 0.6
        assert "signal_divergence" in playbook["conflicts"]

    def test_build_playbook_hold_decision(self):
        """Test playbook with hold decision from low confidence."""
        verdict = {
            "ticker": "MSFT",
            "horizon": "1w",
            "confidence": 0.45,
            "expected_return": 0.01,
            "risk_level": "low",
            "go_no_go": {"decision": "", "reasons": []},
        }

        playbook = _build_strategy_playbook(verdict, profile="equity_1w")

        assert playbook["decision"] == "hold"
        assert playbook["confidence"] == 0.45

    def test_build_playbook_confidence_threshold_go(self):
        """Test auto-decision based on confidence threshold."""
        verdict = {
            "ticker": "NVDA",
            "horizon": "1w",
            "confidence": 0.80,
            "expected_return": 0.10,
            "risk_level": "medium",
            "go_no_go": {"decision": "", "reasons": []},
        }

        playbook = _build_strategy_playbook(verdict, profile="equity_1w")

        # High confidence + positive return = go
        assert playbook["decision"] == "go"

    def test_build_playbook_confidence_threshold_no_go(self):
        """Test auto-decision based on low confidence."""
        verdict = {
            "ticker": "AMD",
            "horizon": "1w",
            "confidence": 0.25,
            "expected_return": -0.05,
            "risk_level": "medium",
            "go_no_go": {"decision": "", "reasons": []},
        }

        playbook = _build_strategy_playbook(verdict, profile="equity_1w")

        # Low confidence + negative return = no_go
        assert playbook["decision"] == "no_go"

    def test_build_playbook_conflict_risk_profile(self):
        """Test conflict detection when decision is go but risk is high."""
        verdict = {
            "ticker": "GME",
            "horizon": "1w",
            "confidence": 0.70,
            "expected_return": 0.15,
            "risk_level": "critical",
            "go_no_go": {"decision": "go", "reasons": ["Momentum"]},
        }

        playbook = _build_strategy_playbook(verdict, profile="equity_1w")

        assert playbook["decision"] == "go"
        assert "risk_profile_too_aggressive" in playbook["conflicts"]

    def test_build_playbook_conflict_positive_overridden(self):
        """Test conflict when positive signal is overridden by filters."""
        verdict = {
            "ticker": "SPY",
            "horizon": "1m",
            "confidence": 0.55,
            "expected_return": 0.08,
            "risk_level": "low",
            "go_no_go": {"decision": "no_go", "reasons": ["Market conditions"]},
        }

        playbook = _build_strategy_playbook(verdict, profile="equity_1m")

        assert playbook["decision"] == "no_go"
        assert "positive_signal_overridden_by_filters" in playbook["conflicts"]

    def test_build_playbook_normalize_decision_aliases(self):
        """Test decision normalization from various aliases."""
        test_cases = [
            ("buy", "go"),
            ("long", "go"),
            ("sell", "no_go"),
            ("short", "no_go"),
            ("no-go", "no_go"),
        ]

        for input_decision, expected in test_cases:
            verdict = {
                "ticker": "TEST",
                "horizon": "1w",
                "confidence": 0.60,
                "expected_return": 0.05,
                "go_no_go": {"decision": input_decision, "reasons": []},
            }

            playbook = _build_strategy_playbook(verdict, profile="equity_1w")
            assert playbook["decision"] == expected, f"Failed for {input_decision}"

    def test_build_playbook_evidence_metadata(self):
        """Test evidence metadata extraction."""
        verdict = {
            "ticker": "META",
            "horizon": "1w",
            "confidence": 0.70,
            "expected_return": 0.06,
            "go_no_go": {"decision": "go", "reasons": []},
            "impacts": {"fed_decision": "bullish", "earnings": "beat"},
            "scenarios": [{"type": "bull"}, {"type": "base"}],
            "risks": ["regulation", "competition"],
        }

        playbook = _build_strategy_playbook(verdict, profile="equity_1w")

        assert playbook["evidence"]["scenario_count"] == 2
        assert playbook["evidence"]["risk_count"] == 2
        assert "fed_decision" in playbook["evidence"]["impact_keys"]
        assert "earnings" in playbook["evidence"]["impact_keys"]

    def test_build_playbook_unknown_ticker_fallback(self):
        """Test fallback for missing ticker."""
        verdict = {
            "ticker": None,
            "horizon": "1w",
            "confidence": 0.60,
            "expected_return": 0.03,
            "go_no_go": {"decision": "go", "reasons": []},
        }

        playbook = _build_strategy_playbook(verdict, profile="equity_1w")

        assert playbook["ticker"] == "UNKNOWN"
        assert "UNKNOWN:1w:go:equity_1w" in playbook["playbook_id"]

    def test_build_playbook_summary_fallback(self):
        """Test summary fallback to reasoning."""
        verdict = {
            "ticker": "AAPL",
            "horizon": "1w",
            "confidence": 0.65,
            "expected_return": 0.04,
            "reasoning": "Technical breakout pattern",
            "go_no_go": {"decision": "go", "reasons": []},
        }

        playbook = _build_strategy_playbook(verdict, profile="equity_1w")

        assert len(playbook["summary"]) == 1
        assert "Technical breakout pattern" in playbook["summary"]

    def test_build_playbook_conflict_deduplication(self):
        """Test that duplicate conflicts are removed."""
        verdict = {
            "ticker": "TEST",
            "horizon": "1w",
            "confidence": 0.70,
            "expected_return": 0.10,
            "risk_level": "critical",
            "conflicts": ["risk_profile_too_aggressive", "RISK_PROFILE_TOO_AGGRESSIVE"],
            "go_no_go": {"decision": "go", "reasons": []},
        }

        playbook = _build_strategy_playbook(verdict, profile="equity_1w")

        # Should only have one instance after deduplication
        conflict_count = playbook["conflicts"].count("risk_profile_too_aggressive")
        assert conflict_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
