"""
Test Playbook Resolver Enrichment - BATCH-15-DEV-02

Tests that the playbook resolver correctly enriches recommendations
with playbook_id and conflict warnings.
"""
import pytest
import sys
from pathlib import Path

# Add src to path for imports
SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from typing import Dict, Any, Optional

from domains.copilot.domain.playbook import (
    Playbook,
    PlaybookAction,
    MarketRegime,
    RiskProfile,
    get_default_playbook_library,
)
from domains.copilot.application.playbook_resolver import (
    PlaybookResolver,
    get_playbook_resolver,
    resolve_playbook_for_context,
)


class TestPlaybookResolver:
    """Test playbook resolution logic."""

    def test_resolve_exact_match(self):
        """Test resolving playbook with exact regime and risk profile match."""
        resolver = PlaybookResolver()
        playbook = resolver.resolve(regime="bull_market", risk_profile="moderate")
        
        assert playbook.id == "bull_moderate_001"
        assert playbook.regime == MarketRegime.BULL_MARKET
        assert playbook.risk_profile == RiskProfile.MODERATE

    def test_resolve_fallback_to_moderate(self):
        """Test fallback to moderate profile when exact match not found."""
        resolver = PlaybookResolver()
        playbook = resolver.resolve(regime="bull_market", risk_profile="aggressive")
        
        # Should find bull_aggressive_001 if it exists, otherwise fallback
        assert playbook is not None
        assert playbook.regime == MarketRegime.BULL_MARKET

    def test_resolve_final_fallback(self):
        """Test final fallback to normal_moderate_001."""
        resolver = PlaybookResolver()
        playbook = resolver.resolve(regime="unknown_regime", risk_profile="unknown")
        
        assert playbook.id == "normal_moderate_001"

    def test_detect_conflict_via_signal(self):
        """Test conflict detection via conflict_signals."""
        resolver = PlaybookResolver()
        playbook = resolver.resolve(regime="bull_market", risk_profile="moderate")
        
        # Bull market playbook has conflict_signals like "bearish_divergence"
        has_conflict, reason = resolver.detect_conflict(
            playbook=playbook,
            signal_direction="bullish",
            signal_asset="equities",
        )
        
        # Should detect conflict because bullish signal + bearish_divergence in conflict_signals
        assert has_conflict is True
        assert reason is not None
        assert "bearish_divergence" in reason

    def test_no_conflict_aligned_signal(self):
        """Test no conflict when signal aligns with playbook."""
        resolver = PlaybookResolver()
        playbook = resolver.resolve(regime="bull_market", risk_profile="moderate")
        
        # Use neutral signal which doesn't trigger conflict_signals
        has_conflict, reason = resolver.detect_conflict(
            playbook=playbook,
            signal_direction="neutral",
            signal_asset="equities",
        )
        
        # Neutral signal doesn't trigger conflict for bull market playbook
        assert has_conflict is False
        assert reason is None

    def test_detect_action_contradiction(self):
        """Test contradiction detection between playbook action and signal."""
        resolver = PlaybookResolver()
        playbook = resolver.resolve(regime="bear_market", risk_profile="conservative")
        
        # Bear market playbook recommends "reduce" equities
        # A bullish signal for equities would contradict
        has_conflict, reason = resolver.detect_conflict(
            playbook=playbook,
            signal_direction="bullish",
            signal_asset="equities",
        )
        
        # Should detect contradiction: bullish signal vs reduce action
        assert has_conflict is True
        assert "contradicts" in reason.lower()

    def test_enrich_recommendation_adds_playbook_id(self):
        """Test that enrichment adds playbook_id to recommendation."""
        resolver = PlaybookResolver()
        recommendation = {
            "direction": "bullish",
            "asset_class": "equities",
            "confidence": 0.75,
        }
        
        enriched = resolver.enrich_recommendation(
            recommendation=recommendation,
            regime="bull_market",
            risk_profile="moderate",
        )
        
        assert "playbook_id" in enriched
        assert enriched["playbook_id"] == "bull_moderate_001"

    def test_enrich_recommendation_adds_conflict_warning(self):
        """Test that enrichment adds conflict_warning structure."""
        resolver = PlaybookResolver()
        recommendation = {
            "direction": "bullish",
            "asset_class": "equities",
        }
        
        enriched = resolver.enrich_recommendation(
            recommendation=recommendation,
            regime="bull_market",
            risk_profile="moderate",
        )
        
        assert "conflict_warning" in enriched
        assert isinstance(enriched["conflict_warning"], dict)
        assert "detected" in enriched["conflict_warning"]

    def test_enrich_recommendation_adds_playbook_context(self):
        """Test that enrichment adds playbook_context summary."""
        resolver = PlaybookResolver()
        recommendation = {
            "direction": "neutral",
            "asset_class": "bonds",
        }
        
        enriched = resolver.enrich_recommendation(
            recommendation=recommendation,
            regime="normal",
            risk_profile="moderate",
        )
        
        assert "playbook_context" in enriched
        assert "name" in enriched["playbook_context"]
        assert "description" in enriched["playbook_context"]
        assert "guardrails" in enriched["playbook_context"]


class TestPlaybookResolverSingleton:
    """Test singleton pattern for playbook resolver."""

    def test_get_playbook_resolver_returns_singleton(self):
        """Test that get_playbook_resolver returns same instance."""
        resolver1 = get_playbook_resolver()
        resolver2 = get_playbook_resolver()
        
        assert resolver1 is resolver2

    def test_resolve_playbook_for_context(self):
        """Test convenience function resolve_playbook_for_context."""
        playbook_dict = resolve_playbook_for_context(
            regime="bull_market",
            risk_profile="moderate",
        )
        
        assert isinstance(playbook_dict, dict)
        assert playbook_dict["id"] == "bull_moderate_001"
        assert playbook_dict["regime"] == "bull_market"
        assert playbook_dict["risk_profile"] == "moderate"


class TestPlaybookToDict:
    """Test Playbook.to_dict() serialization."""

    def test_playbook_to_dict_format(self):
        """Test playbook serialization matches API response format."""
        playbook = Playbook(
            id="test_001",
            name="Test Playbook",
            regime=MarketRegime.NORMAL,
            risk_profile=RiskProfile.MODERATE,
            description="Test description",
            actions=[
                PlaybookAction(
                    action_type="hold",
                    asset_class="equities",
                    conviction=0.6,
                    rationale="Test rationale",
                    risk_note="Test risk note",
                )
            ],
            guardrails=["Test guardrail 1", "Test guardrail 2"],
            conflict_signals=["test_conflict_signal"],
        )
        
        result = playbook.to_dict()
        
        assert result["id"] == "test_001"
        assert result["name"] == "Test Playbook"
        assert result["regime"] == "normal"
        assert result["risk_profile"] == "moderate"
        assert result["description"] == "Test description"
        assert len(result["actions"]) == 1
        assert result["actions"][0]["action_type"] == "hold"
        assert result["actions"][0]["conviction"] == 0.6
        assert result["actions"][0]["rationale"] == "Test rationale"
        assert result["actions"][0]["risk_note"] == "Test risk note"
        assert len(result["guardrails"]) == 2
        assert len(result["conflict_signals"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
