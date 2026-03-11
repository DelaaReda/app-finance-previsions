"""
Policy Validator Service - Personal Policy Guardrails (BATCH-20)

Validates recommendations against user-defined investment policies.
Ensures policy-violating recommendations never appear as plain BUY signals.

Author: DEV-02
Task: BATCH-20-DEV-02
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class PolicyViolationSeverity(str, Enum):
    """Severity levels for policy violations."""
    BLOCKING = "blocking"  # Hard stop - recommendation must be downgraded/removed
    WARNING = "warning"    # Soft warning - recommendation can proceed with disclosure
    INFO = "info"         # Informational - no action required


class PolicyValidatorService:
    """
    Personal Policy Validator Service
    
    Validates investment recommendations against user-defined policies.
    
    Features:
    - Sector/industry exclusions (e.g., no tobacco, weapons, fossil fuels)
    - Risk concentration limits (e.g., max 20% in single stock)
    - ESG compliance checks
    - Geographic restrictions
    - Position size limits
    
    Policy violations result in recommendation downgrading:
    - "BUY" → "HOLD" or "AVOID" with violation badge
    - Violations are versioned with timestamps for audit trail
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._policy_cache: Dict[str, Any] = {}

    def validate_recommendation(
        self,
        recommendation: Dict[str, Any],
        user_policies: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Validate a single recommendation against user policies.
        
        Args:
            recommendation: Dict with keys: ticker, action, sector, risk_score, etc.
            user_policies: List of user policy definitions
            
        Returns:
            Dict with:
                - original_action: original recommendation action
                - validated_action: action after policy validation
                - violations: list of policy violations found
                - violation_badge: UI badge info if violations exist
                - policy_version: timestamp of policy revision used
        """
        ticker = recommendation.get("ticker", "UNKNOWN")
        original_action = recommendation.get("action", "HOLD")
        sector = recommendation.get("sector", "")
        risk_score = recommendation.get("risk_score", 0.5)
        
        violations: List[Dict[str, Any]] = []
        policy_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        for policy in user_policies:
            if not policy.get("enabled", True):
                continue
                
            violation = self._check_policy(policy, ticker, sector, risk_score, recommendation)
            if violation:
                violations.append(violation)
        
        # Determine if action should be downgraded
        validated_action = original_action
        violation_badge = None
        
        if violations:
            has_blocking = any(
                v.get("severity") == PolicyViolationSeverity.BLOCKING.value 
                for v in violations
            )
            
            if has_blocking and original_action.upper() == "BUY":
                validated_action = "HOLD"
                self.logger.info(f"🛡️ Policy violation blocked BUY → HOLD for {ticker}", extra={
                    "ticker": ticker,
                    "violations_count": len(violations)
                })
            
            # Build violation badge for UI
            violation_badge = {
                "visible": True,
                "severity": "critical" if has_blocking else "warning",
                "message": f"{len(violations)} policy violation(s)",
                "violations": [
                    {
                        "rule": v.get("rule_name"),
                        "reason": v.get("reason"),
                        "severity": v.get("severity")
                    }
                    for v in violations
                ],
                "policy_version": policy_timestamp
            }
        
        return {
            "ticker": ticker,
            "original_action": original_action,
            "validated_action": validated_action,
            "violations": violations,
            "violation_badge": violation_badge,
            "policy_version": policy_timestamp,
            "validated_at": policy_timestamp
        }

    def _check_policy(
        self,
        policy: Dict[str, Any],
        ticker: str,
        sector: str,
        risk_score: float,
        recommendation: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check a single policy rule against a recommendation."""
        policy_type = policy.get("type")
        
        if policy_type == "sector_exclusion":
            return self._check_sector_exclusion(policy, sector, ticker)
        
        elif policy_type == "risk_concentration":
            return self._check_risk_concentration(policy, risk_score, ticker)
        
        elif policy_type == "position_size_limit":
            return self._check_position_size(policy, recommendation, ticker)
        
        elif policy_type == "esg_minimum":
            return self._check_esg_minimum(policy, recommendation, ticker)
        
        elif policy_type == "geographic_restriction":
            return self._check_geographic_restriction(policy, recommendation, ticker)
        
        return None

    def _check_sector_exclusion(
        self,
        policy: Dict[str, Any],
        sector: str,
        ticker: str
    ) -> Optional[Dict[str, Any]]:
        """Check if ticker's sector is excluded."""
        excluded_sectors = policy.get("excluded_sectors", [])
        if not excluded_sectors:
            return None
            
        sector_match = any(
            excluded.lower() in sector.lower() 
            for excluded in excluded_sectors
        )
        
        if sector_match:
            return {
                "rule_name": "sector_exclusion",
                "severity": PolicyViolationSeverity.BLOCKING.value,
                "reason": f"Sector '{sector}' is excluded by policy",
                "ticker": ticker,
                "sector": sector,
                "excluded_sectors": excluded_sectors
            }
        
        return None

    def _check_risk_concentration(
        self,
        policy: Dict[str, Any],
        risk_score: float,
        ticker: str
    ) -> Optional[Dict[str, Any]]:
        """Check if risk score exceeds user's tolerance."""
        max_risk = policy.get("max_risk_score", 1.0)
        
        if risk_score > max_risk:
            return {
                "rule_name": "risk_concentration",
                "severity": PolicyViolationSeverity.WARNING.value,
                "reason": f"Risk score {risk_score:.2f} exceeds max {max_risk:.2f}",
                "ticker": ticker,
                "risk_score": risk_score,
                "max_allowed": max_risk
            }
        
        return None

    def _check_position_size(
        self,
        policy: Dict[str, Any],
        recommendation: Dict[str, Any],
        ticker: str
    ) -> Optional[Dict[str, Any]]:
        """Check if recommended position size exceeds limit."""
        max_position_pct = policy.get("max_position_percentage", 100.0)
        recommended_size = recommendation.get("position_size_pct", 0.0)
        
        if recommended_size > max_position_pct:
            return {
                "rule_name": "position_size_limit",
                "severity": PolicyViolationSeverity.BLOCKING.value,
                "reason": f"Position size {recommended_size:.1f}% exceeds max {max_position_pct:.1f}%",
                "ticker": ticker,
                "recommended_size": recommended_size,
                "max_allowed": max_position_pct
            }
        
        return None

    def _check_esg_minimum(
        self,
        policy: Dict[str, Any],
        recommendation: Dict[str, Any],
        ticker: str
    ) -> Optional[Dict[str, Any]]:
        """Check if ESG score meets minimum threshold."""
        min_esg_score = policy.get("min_esg_score", 0.0)
        esg_score = recommendation.get("esg_score")
        
        if esg_score is not None and esg_score < min_esg_score:
            return {
                "rule_name": "esg_minimum",
                "severity": PolicyViolationSeverity.BLOCKING.value,
                "reason": f"ESG score {esg_score:.2f} below minimum {min_esg_score:.2f}",
                "ticker": ticker,
                "esg_score": esg_score,
                "min_required": min_esg_score
            }
        
        return None

    def _check_geographic_restriction(
        self,
        policy: Dict[str, Any],
        recommendation: Dict[str, Any],
        ticker: str
    ) -> Optional[Dict[str, Any]]:
        """Check if geographic exposure is allowed."""
        allowed_regions = policy.get("allowed_regions", [])
        if not allowed_regions:
            return None
            
        ticker_region = recommendation.get("region", "")
        
        if ticker_region and allowed_regions:
            region_allowed = any(
                allowed.lower() in ticker_region.lower()
                for allowed in allowed_regions
            )
            
            if not region_allowed:
                return {
                    "rule_name": "geographic_restriction",
                    "severity": PolicyViolationSeverity.WARNING.value,
                    "reason": f"Region '{ticker_region}' not in allowed regions",
                    "ticker": ticker,
                    "region": ticker_region,
                    "allowed_regions": allowed_regions
                }
        
        return None

    def get_policy_template(self, policy_type: str) -> Dict[str, Any]:
        """Get a template for creating a new policy."""
        templates = {
            "sector_exclusion": {
                "type": "sector_exclusion",
                "name": "Sector Exclusion Policy",
                "enabled": True,
                "excluded_sectors": ["tobacco", "weapons", "fossil_fuels"],
                "description": "Exclude investments in specific sectors"
            },
            "risk_concentration": {
                "type": "risk_concentration",
                "name": "Risk Concentration Limit",
                "enabled": True,
                "max_risk_score": 0.7,
                "description": "Limit exposure to high-risk assets"
            },
            "position_size_limit": {
                "type": "position_size_limit",
                "name": "Position Size Limit",
                "enabled": True,
                "max_position_percentage": 20.0,
                "description": "Maximum percentage per position"
            },
            "esg_minimum": {
                "type": "esg_minimum",
                "name": "ESG Minimum Score",
                "enabled": True,
                "min_esg_score": 0.6,
                "description": "Minimum ESG rating required"
            },
            "geographic_restriction": {
                "type": "geographic_restriction",
                "name": "Geographic Restriction",
                "enabled": True,
                "allowed_regions": ["US", "EU", "developed_markets"],
                "description": "Restrict investments to specific regions"
            }
        }
        
        return templates.get(policy_type, {
            "type": policy_type,
            "name": f"Custom {policy_type}",
            "enabled": True
        })

    def list_policy_types(self) -> List[str]:
        """List available policy types."""
        return [
            "sector_exclusion",
            "risk_concentration",
            "position_size_limit",
            "esg_minimum",
            "geographic_restriction"
        ]


# Singleton instance
_policy_validator_instance: Optional[PolicyValidatorService] = None


def get_policy_validator() -> PolicyValidatorService:
    """Get or create the policy validator service singleton."""
    global _policy_validator_instance
    if _policy_validator_instance is None:
        _policy_validator_instance = PolicyValidatorService()
    return _policy_validator_instance
