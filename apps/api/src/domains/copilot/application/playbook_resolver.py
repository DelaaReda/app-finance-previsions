"""
Playbook Resolver - BATCH-15-DEV-02

Resolves the appropriate strategy playbook based on:
- Current market regime
- User risk profile
- Signal conflicts detection
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone

from ..domain.playbook import (
    Playbook,
    PlaybookAction,
    MarketRegime,
    RiskProfile,
    get_default_playbook_library,
)

logger = logging.getLogger(__name__)


class PlaybookResolver:
    """
    Resolves strategy playbooks for recommendations.
    
    The resolver maps market regime + risk profile to a specific playbook,
    and detects conflicts between playbook guidance and signal direction.
    """

    def __init__(self, playbook_library: Optional[Dict[str, Playbook]] = None):
        """
        Initialize resolver with playbook library.
        
        Args:
            playbook_library: Optional custom library. Uses defaults if not provided.
        """
        self.library = playbook_library or get_default_playbook_library()
        self.logger = logging.getLogger(__name__)

    def resolve(
        self,
        regime: str,
        risk_profile: str,
    ) -> Playbook:
        """
        Resolve the appropriate playbook for given regime and risk profile.
        
        Args:
            regime: Market regime (e.g., "bull_market", "bear_market", "BULL_MARKET")
            risk_profile: User risk profile (e.g., "moderate", "conservative")
            
        Returns:
            Matching Playbook object
            
        Falls back to normal_moderate_001 if no exact match found.
        """
        # Normalize inputs - handle both underscore and uppercase formats
        regime_normalized = regime.upper().replace("-", "_")
        risk_key = risk_profile.lower()
        
        # Map context service regime names to playbook ID prefix
        # Note: playbook IDs use shortened names (bull not bull_market)
        regime_to_playbook_id = {
            "HIGH_VOLATILITY": "high_volatility",
            "ELEVATED_RISK": "elevated_risk",
            "BULL_MARKET": "bull",
            "BEAR_MARKET": "bear",
            "RISK_OFF": "risk_off",
            "RISK_ON": "risk_on",
            "NORMAL": "normal",
        }
        regime_key = regime_to_playbook_id.get(regime_normalized, regime_normalized.lower())
        
        # Try exact match first
        playbook_id = f"{regime_key}_{risk_key}_001"
        if playbook_id in self.library:
            self.logger.debug(f"Resolved playbook: {playbook_id}")
            return self.library[playbook_id]
        
        # Fallback: try regime with moderate profile
        fallback_id = f"{regime_key}_moderate_001"
        if fallback_id in self.library:
            self.logger.debug(f"Fallback to playbook: {fallback_id}")
            return self.library[fallback_id]
        
        # Final fallback: normal moderate
        default_id = "normal_moderate_001"
        self.logger.warning(
            f"No playbook found for regime={regime}, risk={risk_profile}. "
            f"Using default: {default_id}"
        )
        return self.library[default_id]

    def detect_conflict(
        self,
        playbook: Playbook,
        signal_direction: str,
        signal_asset: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Detect if a signal conflicts with playbook guidance.
        
        Args:
            playbook: The resolved playbook
            signal_direction: Signal direction ("bullish", "bearish", "neutral")
            signal_asset: Asset class the signal relates to
            
        Returns:
            Tuple of (has_conflict, conflict_reason)
        """
        # Check conflict signals
        conflict_map = {
            "bullish": ["bearish_divergence", "overbought_rsi", "risk_off_flow"],
            "bearish": ["bullish_reversal", "oversold_bounce", "risk_on_rotation"],
        }
        
        signal_conflicts = conflict_map.get(signal_direction.lower(), [])
        
        for conflict_signal in playbook.conflict_signals:
            if conflict_signal in signal_conflicts:
                reason = f"Signal {signal_direction} conflicts with playbook warning: {conflict_signal}"
                self.logger.info(f"Conflict detected: {reason}")
                return True, reason
        
        # Check if signal action contradicts playbook action
        playbook_action = self._find_playbook_action(playbook, signal_asset)
        if playbook_action:
            contradiction = self._is_contradictory(
                playbook_action.action_type,
                signal_direction,
            )
            if contradiction:
                reason = (
                    f"Signal {signal_direction} for {signal_asset} contradicts "
                    f"playbook action {playbook_action.action_type}"
                )
                self.logger.info(f"Action contradiction: {reason}")
                return True, reason
        
        return False, None

    def _find_playbook_action(
        self,
        playbook: Playbook,
        asset_class: str,
    ) -> Optional[PlaybookAction]:
        """Find playbook action for a specific asset class."""
        for action in playbook.actions:
            if action.asset_class.lower() == asset_class.lower():
                return action
        return None

    def _is_contradictory(
        self,
        playbook_action: str,
        signal_direction: str,
    ) -> bool:
        """Check if playbook action contradicts signal direction."""
        # Define contradictions
        bullish_actions = {"buy", "increase", "hold"}
        bearish_actions = {"sell", "reduce", "hold"}
        
        signal_lower = signal_direction.lower()
        
        if signal_lower == "bullish":
            # Bullish signal contradicts bearish playbook action
            return playbook_action.lower() in {"sell", "reduce"}
        elif signal_lower == "bearish":
            # Bearish signal contradicts bullish playbook action
            return playbook_action.lower() in {"buy", "increase"}
        
        return False

    def enrich_recommendation(
        self,
        recommendation: Dict[str, Any],
        regime: str,
        risk_profile: str,
    ) -> Dict[str, Any]:
        """
        Enrich a recommendation with playbook context.
        
        Args:
            recommendation: Original recommendation dict
            regime: Current market regime
            risk_profile: User risk profile
            
        Returns:
            Enriched recommendation with playbook_id and conflict warning
        """
        playbook = self.resolve(regime, risk_profile)
        
        # Add playbook ID to recommendation
        enriched = dict(recommendation)
        enriched["playbook_id"] = playbook.id
        
        # Check for conflicts
        signal_direction = recommendation.get("direction", "neutral")
        signal_asset = recommendation.get("asset_class", "equities")
        
        has_conflict, conflict_reason = self.detect_conflict(
            playbook,
            signal_direction,
            signal_asset,
        )
        
        if has_conflict:
            enriched["conflict_warning"] = {
                "detected": True,
                "reason": conflict_reason,
                "playbook_id": playbook.id,
                "playbook_regime": playbook.regime.value,
            }
            self.logger.warning(
                f"Recommendation conflict: {conflict_reason} "
                f"(playbook={playbook.id})"
            )
        else:
            enriched["conflict_warning"] = {
                "detected": False,
            }
        
        # Add playbook summary
        enriched["playbook_context"] = {
            "name": playbook.name,
            "description": playbook.description,
            "guardrails": playbook.guardrails[:2],  # Top 2 guardrails
        }
        
        return enriched


# Singleton instance
_resolver_instance: Optional[PlaybookResolver] = None


def get_playbook_resolver() -> PlaybookResolver:
    """Get singleton instance of PlaybookResolver."""
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = PlaybookResolver()
    return _resolver_instance


def resolve_playbook_for_context(
    regime: str,
    risk_profile: str,
) -> Dict[str, Any]:
    """
    Convenience function to resolve playbook for API response.
    
    Args:
        regime: Market regime string
        risk_profile: Risk profile string
        
    Returns:
        Playbook data as dictionary
    """
    resolver = get_playbook_resolver()
    playbook = resolver.resolve(regime, risk_profile)
    return playbook.to_dict()
