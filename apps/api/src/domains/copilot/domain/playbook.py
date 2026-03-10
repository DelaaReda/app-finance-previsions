"""
Strategy Playbooks Domain Model - BATCH-15-DEV-02

Playbooks encode investment strategy rules by market regime and risk profile.
Each playbook provides actionable guidance for recommendations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class RiskProfile(str, Enum):
    """Investor risk tolerance profiles."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class MarketRegime(str, Enum):
    """Market regime classifications."""
    HIGH_VOLATILITY = "high_volatility"
    ELEVATED_RISK = "elevated_risk"
    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market"
    RISK_OFF = "risk_off"
    RISK_ON = "risk_on"
    NORMAL = "normal"


@dataclass
class PlaybookAction:
    """An actionable recommendation within a playbook."""
    action_type: str  # "buy", "sell", "hold", "reduce", "increase"
    asset_class: str  # "equities", "bonds", "gold", "cash", etc.
    conviction: float  # 0.0-1.0 confidence in this action
    rationale: str
    risk_note: Optional[str] = None


@dataclass
class Playbook:
    """
    Strategy playbook for a specific regime and risk profile combination.
    
    Attributes:
        id: Unique playbook identifier (e.g., "bull_moderate_001")
        name: Human-readable name
        regime: Market regime this playbook applies to
        risk_profile: Target investor risk profile
        description: Summary of strategy approach
        actions: List of recommended actions
        guardrails: Constraints and rules to follow
        conflict_signals: Signals that would trigger a conflict warning
    """
    id: str
    name: str
    regime: MarketRegime
    risk_profile: RiskProfile
    description: str
    actions: List[PlaybookAction] = field(default_factory=list)
    guardrails: List[str] = field(default_factory=list)
    conflict_signals: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert playbook to dictionary for API response."""
        return {
            "id": self.id,
            "name": self.name,
            "regime": self.regime.value,
            "risk_profile": self.risk_profile.value,
            "description": self.description,
            "actions": [
                {
                    "action_type": a.action_type,
                    "asset_class": a.asset_class,
                    "conviction": a.conviction,
                    "rationale": a.rationale,
                    "risk_note": a.risk_note,
                }
                for a in self.actions
            ],
            "guardrails": self.guardrails,
            "conflict_signals": self.conflict_signals,
            "metadata": self.metadata,
        }


# Default playbooks library - minimal viable set
DEFAULT_PLAYBOOKS: List[Playbook] = [
    Playbook(
        id="bull_moderate_001",
        name="Bull Market Growth Strategy",
        regime=MarketRegime.BULL_MARKET,
        risk_profile=RiskProfile.MODERATE,
        description="Participate in upside while maintaining diversification",
        actions=[
            PlaybookAction(
                action_type="increase",
                asset_class="equities",
                conviction=0.75,
                rationale="Strong momentum and positive sentiment support equity exposure",
            ),
            PlaybookAction(
                action_type="hold",
                asset_class="bonds",
                conviction=0.6,
                rationale="Maintain diversification but reduce duration risk",
            ),
        ],
        guardrails=[
            "Avoid concentration >20% in single sector",
            "Rebalance if equity allocation drifts >5% from target",
        ],
        conflict_signals=["bearish_divergence", "overbought_rsi"],
    ),
    Playbook(
        id="bear_moderate_001",
        name="Bear Market Defensive Strategy",
        regime=MarketRegime.BEAR_MARKET,
        risk_profile=RiskProfile.MODERATE,
        description="Reduce risk while maintaining strategic exposure",
        actions=[
            PlaybookAction(
                action_type="reduce",
                asset_class="equities",
                conviction=0.7,
                rationale="Downside protection in confirmed bear market",
            ),
            PlaybookAction(
                action_type="increase",
                asset_class="bonds",
                conviction=0.65,
                rationale="Flight to quality supports fixed income",
            ),
            PlaybookAction(
                action_type="hold",
                asset_class="cash",
                conviction=0.6,
                rationale="Maintain dry powder for opportunities",
            ),
        ],
        guardrails=[
            "Equity exposure <=60%",
            "Focus on quality and defensive sectors",
            "Avoid leverage",
        ],
        conflict_signals=["bullish_reversal", "oversold_bounce"],
    ),
    Playbook(
        id="bear_conservative_001",
        name="Bear Market Preservation Strategy",
        regime=MarketRegime.BEAR_MARKET,
        risk_profile=RiskProfile.CONSERVATIVE,
        description="Capital preservation with defensive positioning",
        actions=[
            PlaybookAction(
                action_type="reduce",
                asset_class="equities",
                conviction=0.8,
                rationale="Downside protection priority in confirmed bear market",
            ),
            PlaybookAction(
                action_type="increase",
                asset_class="bonds",
                conviction=0.7,
                rationale="Flight to quality supports fixed income allocation",
            ),
            PlaybookAction(
                action_type="hold",
                asset_class="cash",
                conviction=0.65,
                rationale="Maintain dry powder for future opportunities",
            ),
        ],
        guardrails=[
            "Equity exposure <=40%",
            "Focus on defensive sectors (utilities, consumer staples, healthcare)",
            "No leverage or speculative positions",
        ],
        conflict_signals=["bullish_reversal", "oversold_bounce"],
    ),
    Playbook(
        id="risk_off_moderate_001",
        name="Risk-Off Balanced Defense",
        regime=MarketRegime.RISK_OFF,
        risk_profile=RiskProfile.MODERATE,
        description="Defensive positioning with measured risk reduction",
        actions=[
            PlaybookAction(
                action_type="reduce",
                asset_class="equities",
                conviction=0.75,
                rationale="Risk aversion favors reducing equity exposure",
            ),
            PlaybookAction(
                action_type="increase",
                asset_class="gold",
                conviction=0.65,
                rationale="Safe haven demand supports precious metals",
            ),
            PlaybookAction(
                action_type="increase",
                asset_class="bonds",
                conviction=0.7,
                rationale="Treasuries benefit from flight to quality",
            ),
        ],
        guardrails=[
            "Reduce equity exposure to strategic minimum",
            "Avoid high-yield and emerging market debt",
            "Maintain cash buffer (10-20%)",
        ],
        conflict_signals=["risk_on_rotation", "oversold_equities"],
    ),
    Playbook(
        id="risk_off_conservative_001",
        name="Risk-Off Defensive Strategy",
        regime=MarketRegime.RISK_OFF,
        risk_profile=RiskProfile.CONSERVATIVE,
        description="Maximum defense during risk aversion episodes",
        actions=[
            PlaybookAction(
                action_type="reduce",
                asset_class="equities",
                conviction=0.85,
                rationale="Risk aversion favors exiting risk assets",
            ),
            PlaybookAction(
                action_type="increase",
                asset_class="gold",
                conviction=0.7,
                rationale="Safe haven demand supports precious metals",
            ),
            PlaybookAction(
                action_type="increase",
                asset_class="bonds",
                conviction=0.75,
                rationale="Treasuries benefit from flight to quality",
            ),
        ],
        guardrails=[
            "Minimize equity exposure to essential holdings only",
            "Avoid high-yield and emerging market debt",
            "Maintain elevated cash buffer (15-25%)",
        ],
        conflict_signals=["risk_on_rotation", "oversold_equities"],
    ),
    Playbook(
        id="risk_on_moderate_001",
        name="Risk-On Opportunity Strategy",
        regime=MarketRegime.RISK_ON,
        risk_profile=RiskProfile.MODERATE,
        description="Participate in risk appetite with measured exposure",
        actions=[
            PlaybookAction(
                action_type="increase",
                asset_class="equities",
                conviction=0.7,
                rationale="Positive sentiment supports equity exposure",
            ),
            PlaybookAction(
                action_type="increase",
                asset_class="emerging_markets",
                conviction=0.6,
                rationale="Risk-on favors higher beta assets",
            ),
            PlaybookAction(
                action_type="reduce",
                asset_class="cash",
                conviction=0.65,
                rationale="Deploy cash into growth opportunities",
            ),
        ],
        guardrails=[
            "Monitor volatility for regime shift warning",
            "Set stop-losses at 10-12% below entry",
            "Maintain diversification across sectors",
        ],
        conflict_signals=["volatility_spike", "risk_off_flow"],
    ),
    Playbook(
        id="risk_on_aggressive_001",
        name="Risk-On Opportunity Strategy",
        regime=MarketRegime.RISK_ON,
        risk_profile=RiskProfile.AGGRESSIVE,
        description="Maximize participation in risk appetite environment",
        actions=[
            PlaybookAction(
                action_type="increase",
                asset_class="equities",
                conviction=0.8,
                rationale="Positive sentiment and low volatility support risk taking",
            ),
            PlaybookAction(
                action_type="increase",
                asset_class="emerging_markets",
                conviction=0.65,
                rationale="Risk-on favors higher beta emerging markets",
            ),
            PlaybookAction(
                action_type="reduce",
                asset_class="cash",
                conviction=0.7,
                rationale="Deploy cash into growth opportunities",
            ),
        ],
        guardrails=[
            "Monitor volatility for early warning of regime shift",
            "Set stop-losses at 8-10% below entry",
            "Avoid excessive concentration in single trade",
        ],
        conflict_signals=["volatility_spike", "risk_off_flow"],
    ),
    Playbook(
        id="high_volatility_moderate_001",
        name="High Volatility Navigation Strategy",
        regime=MarketRegime.HIGH_VOLATILITY,
        risk_profile=RiskProfile.MODERATE,
        description="Navigate extreme volatility with caution and flexibility",
        actions=[
            PlaybookAction(
                action_type="reduce",
                asset_class="equities",
                conviction=0.65,
                rationale="High volatility favors lower exposure",
            ),
            PlaybookAction(
                action_type="increase",
                asset_class="bonds",
                conviction=0.6,
                rationale="Stability from fixed income allocation",
            ),
            PlaybookAction(
                action_type="hold",
                asset_class="cash",
                conviction=0.7,
                rationale="Maintain flexibility for opportunities",
            ),
        ],
        guardrails=[
            "Avoid large new positions until volatility subsides",
            "Use limit orders and wide stops",
            "Rebalance on volatility normalization",
        ],
        conflict_signals=["volatility_compression", "calm_before_storm"],
    ),
    Playbook(
        id="elevated_risk_moderate_001",
        name="Elevated Risk Caution Strategy",
        regime=MarketRegime.ELEVATED_RISK,
        risk_profile=RiskProfile.MODERATE,
        description="Cautious positioning with selective exposure",
        actions=[
            PlaybookAction(
                action_type="hold",
                asset_class="equities",
                conviction=0.55,
                rationale="Maintain exposure but monitor closely",
            ),
            PlaybookAction(
                action_type="increase",
                asset_class="bonds",
                conviction=0.6,
                rationale="Add defensive ballast",
            ),
            PlaybookAction(
                action_type="hold",
                asset_class="cash",
                conviction=0.65,
                rationale="Reserve for better entry points",
            ),
        ],
        guardrails=[
            "Tighten stop-losses on equity positions",
            "Avoid speculative additions",
            "Review portfolio for hidden risk concentrations",
        ],
        conflict_signals=["risk_escalation", "volatility_breakout"],
    ),
    Playbook(
        id="normal_moderate_001",
        name="Balanced Market Strategy",
        regime=MarketRegime.NORMAL,
        risk_profile=RiskProfile.MODERATE,
        description="Maintain strategic allocation in balanced conditions",
        actions=[
            PlaybookAction(
                action_type="hold",
                asset_class="equities",
                conviction=0.6,
                rationale="No strong signal to deviate from strategic allocation",
            ),
            PlaybookAction(
                action_type="hold",
                asset_class="bonds",
                conviction=0.6,
                rationale="Maintain diversification benefit",
            ),
            PlaybookAction(
                action_type="hold",
                asset_class="cash",
                conviction=0.5,
                rationale="Standard cash buffer for rebalancing",
            ),
        ],
        guardrails=[
            "Rebalance quarterly or on 5% drift",
            "Maintain target allocation ranges",
            "Review for tactical tilts on new signals",
        ],
        conflict_signals=["regime_transition_warning"],
    ),
]


def get_default_playbook_library() -> Dict[str, Playbook]:
    """Return the default playbook library indexed by ID."""
    return {p.id: p for p in DEFAULT_PLAYBOOKS}
