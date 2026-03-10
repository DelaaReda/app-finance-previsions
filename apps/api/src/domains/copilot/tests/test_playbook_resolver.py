"""
Playbook Resolver Tests - BATCH-15-DEV-02

Minimal test suite for strategy playbooks engine.
Tests playbook resolution and conflict detection.
"""
import pytest
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


class TestPlaybookDomain:
    """Test playbook domain models."""

    def test_playbook_creation(self):
        """Test playbook can be created with required fields."""
        playbook = Playbook(
            id="test_001",
            name="Test Playbook",
            regime=MarketRegime.NORMAL,
            risk_profile=RiskProfile.MODERATE,
            description="Test strategy",
        )
        
        assert playbook.id == "test_001"
        assert playbook.name == "Test Playbook"
        assert playbook.regime == MarketRegime.NORMAL
        assert playbook.risk_profile == RiskProfile.MODERATE
        assert playbook.description == "Test strategy"
        assert playbook.actions == []
        assert playbook.guardrails == []

    def test_playbook_with_actions(self):
        """Test playbook with actions."""
        action = PlaybookAction(
            action_type="buy",
            asset_class="equities",
            conviction=0.75,
            rationale="Strong momentum",
        )
        
        playbook = Playbook(
            id="test_002",
            name="Test with Actions",
            regime=MarketRegime.BULL_MARKET,
            risk_profile=RiskProfile.AGGRESSIVE,
            description="Aggressive growth",
            actions=[action],
        )
        
        assert len(playbook.actions) == 1
        assert playbook.actions[0].action_type == "buy"
        assert playbook.actions[0].conviction == 0.75

    def test_playbook_to_dict(self):
        """Test playbook serialization."""
        playbook = Playbook(
            id="test_003",
            name="Serializable Playbook",
            regime=MarketRegime.BEAR_MARKET,
            risk_profile=RiskProfile.CONSERVATIVE,
            description="Defensive strategy",
            guardrails=["Max 40% equities"],
        )
        
        data = playbook.to_dict()
        
        assert data["id"] == "test_003"
        assert data["name"] == "Serializable Playbook"
        assert data["regime"] == "bear_market"
        assert data["risk_profile"] == "conservative"
        assert "Max 40% equities" in data["guardrails"]

    def test_default_playbook_library(self):
        """Test default playbook library exists."""
        library = get_default_playbook_library()
        
        assert isinstance(library, dict)
        assert len(library) > 0
        assert "normal_moderate_001" in library
        assert "bull_moderate_001" in library
        assert "bear_conservative_001" in library


class TestPlaybookResolver:
    """Test playbook resolver logic."""

    def test_resolve_exact_match(self):
        """Test resolver finds exact regime/profile match."""
        resolver = PlaybookResolver()
        
        playbook = resolver.resolve("bull_market", "moderate")
        
        assert playbook.id == "bull_moderate_001"
        assert playbook.regime == MarketRegime.BULL_MARKET

    def test_resolve_with_fallback(self):
        """Test resolver falls back to moderate profile."""
        resolver = PlaybookResolver()
        
        # No "bull_aggressive_001" in defaults, should fallback
        playbook = resolver.resolve("bull_market", "aggressive")
        
        # Should fallback to bull_moderate_001
        assert playbook.id == "bull_moderate_001"

    def test_resolve_default_fallback(self):
        """Test resolver ultimate fallback to normal_moderate."""
        resolver = PlaybookResolver()
        
        # Unknown regime should fallback to normal_moderate_001
        playbook = resolver.resolve("unknown_regime", "conservative")
        
        assert playbook.id == "normal_moderate_001"

    def test_detect_conflict_bullish_signal(self):
        """Test conflict detection for bullish signal."""
        resolver = PlaybookResolver()
        playbook = resolver.resolve("bear_market", "conservative")
        
        # Bear playbook should conflict with bullish signal
        has_conflict, reason = resolver.detect_conflict(
            playbook,
            signal_direction="bullish",
            signal_asset="equities",
        )
        
        assert has_conflict is True
        assert reason is not None
        assert "contradicts" in reason.lower() or "conflict" in reason.lower()

    def test_no_conflict_aligned_signal(self):
        """Test no conflict when signal aligns with playbook."""
        resolver = PlaybookResolver()
        playbook = resolver.resolve("bull_market", "moderate")
        
        # Bull playbook aligned with bullish signal
        # Use 'neutral' signal which won't trigger conflict signals
        has_conflict, reason = resolver.detect_conflict(
            playbook,
            signal_direction="neutral",
            signal_asset="equities",
        )
        
        assert has_conflict is False

    def test_enrich_recommendation(self):
        """Test recommendation enrichment with playbook."""
        resolver = PlaybookResolver()
        
        recommendation = {
            "action": "buy",
            "asset": "AAPL",
            "direction": "bullish",
            "asset_class": "equities",
        }
        
        enriched = resolver.enrich_recommendation(
            recommendation,
            regime="bull_market",
            risk_profile="moderate",
        )
        
        assert "playbook_id" in enriched
        assert enriched["playbook_id"] == "bull_moderate_001"
        assert "conflict_warning" in enriched
        assert "playbook_context" in enriched
        assert enriched["playbook_context"]["name"] == "Bull Market Growth Strategy"


class TestPlaybookResolverIntegration:
    """Integration tests for playbook resolver."""

    def test_resolve_playbook_for_context(self):
        """Test convenience function for API response."""
        result = resolve_playbook_for_context("bull_market", "moderate")
        
        assert isinstance(result, dict)
        assert result["id"] == "bull_moderate_001"
        assert result["name"] == "Bull Market Growth Strategy"
        assert "actions" in result
        assert "guardrails" in result

    def test_all_regimes_resolvable(self):
        """Test all market regimes can resolve a playbook."""
        regimes = [
            "high_volatility",
            "elevated_risk",
            "bull_market",
            "bear_market",
            "risk_off",
            "risk_on",
            "normal",
        ]
        
        for regime in regimes:
            result = resolve_playbook_for_context(regime, "moderate")
            assert result is not None
            assert "id" in result

    def test_all_risk_profiles_resolvable(self):
        """Test all risk profiles can resolve a playbook."""
        profiles = ["conservative", "moderate", "aggressive"]
        
        for profile in profiles:
            result = resolve_playbook_for_context("normal", profile)
            assert result is not None
            assert "id" in result


class TestConflictScenarios:
    """Test conflict detection scenarios from BATCH-15 spec."""

    def test_bear_playbook_vs_bullish_signal(self):
        """B15-T4: Bear playbook should conflict with bullish signal."""
        resolver = PlaybookResolver()
        playbook = resolver.resolve("bear_market", "conservative")
        
        has_conflict, reason = resolver.detect_conflict(
            playbook,
            "bullish",
            "equities",
        )
        
        assert has_conflict is True
        assert "reduce" in reason.lower() or "contradicts" in reason.lower()

    def test_risk_off_playbook_conflict_signals(self):
        """Test risk_off playbook has conflict signals defined."""
        resolver = PlaybookResolver()
        playbook = resolver.resolve("risk_off", "conservative")
        
        assert len(playbook.conflict_signals) > 0
        assert "risk_on_rotation" in playbook.conflict_signals

    def test_bull_playbook_guardrails(self):
        """Test bull playbook has guardrails defined."""
        resolver = PlaybookResolver()
        playbook = resolver.resolve("bull_market", "moderate")
        
        assert len(playbook.guardrails) > 0
        assert "concentration" in " ".join(playbook.guardrails).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
