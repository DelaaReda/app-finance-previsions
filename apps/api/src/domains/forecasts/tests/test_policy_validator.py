"""
Policy Validator Service Tests - BATCH-20-DEV-02

Tests for personal policy guardrails enforcement.
Ensures policy-violating recommendations are properly downgraded.

Author: DEV-02
Task: BATCH-20-DEV-02
"""

import pytest
from typing import Dict, Any

from domains.forecasts.application.policy_validator_service import (
    PolicyValidatorService,
    PolicyViolationSeverity,
    get_policy_validator
)


@pytest.fixture
def validator():
    """Create a fresh policy validator instance."""
    return PolicyValidatorService()


@pytest.fixture
def sample_recommendation():
    """Sample BUY recommendation for testing."""
    return {
        "ticker": "AAPL",
        "action": "BUY",
        "sector": "Technology",
        "risk_score": 0.45,
        "position_size_pct": 15.0,
        "esg_score": 0.72,
        "region": "US"
    }


class TestPolicyValidatorBasics:
    """Basic policy validator functionality tests."""

    def test_validator_initialization(self, validator):
        """Test validator can be initialized."""
        assert validator is not None
        assert hasattr(validator, 'validate_recommendation')

    def test_list_policy_types(self, validator):
        """Test listing available policy types."""
        policy_types = validator.list_policy_types()
        assert isinstance(policy_types, list)
        assert len(policy_types) > 0
        assert "sector_exclusion" in policy_types
        assert "risk_concentration" in policy_types
        assert "position_size_limit" in policy_types
        assert "esg_minimum" in policy_types
        assert "geographic_restriction" in policy_types

    def test_get_policy_template_sector_exclusion(self, validator):
        """Test getting sector exclusion policy template."""
        template = validator.get_policy_template("sector_exclusion")
        assert template["type"] == "sector_exclusion"
        assert "excluded_sectors" in template
        assert template["enabled"] is True

    def test_get_policy_template_risk_concentration(self, validator):
        """Test getting risk concentration policy template."""
        template = validator.get_policy_template("risk_concentration")
        assert template["type"] == "risk_concentration"
        assert "max_risk_score" in template
        assert template["max_risk_score"] == 0.7

    def test_get_unknown_policy_template(self, validator):
        """Test getting unknown policy type returns generic template."""
        template = validator.get_policy_template("unknown_type")
        assert template["type"] == "unknown_type"
        assert template["enabled"] is True


class TestSectorExclusionPolicy:
    """Tests for sector exclusion policy enforcement."""

    def test_no_violation_clean_sector(self, validator, sample_recommendation):
        """Test recommendation with allowed sector passes."""
        policies = [
            {
                "type": "sector_exclusion",
                "enabled": True,
                "excluded_sectors": ["tobacco", "weapons", "fossil_fuels"]
            }
        ]
        
        result = validator.validate_recommendation(sample_recommendation, policies)
        
        assert result["ticker"] == "AAPL"
        assert result["original_action"] == "BUY"
        assert result["validated_action"] == "BUY"
        assert result["violations"] == []
        assert result["violation_badge"] is None
        assert "policy_version" in result

    def test_violation_excluded_sector_blocks_buy(self, validator, sample_recommendation):
        """Test BUY recommendation blocked when sector is excluded."""
        tobacco_recommendation = {
            **sample_recommendation,
            "ticker": "MO",
            "sector": "Tobacco",
            "action": "BUY"
        }
        
        policies = [
            {
                "type": "sector_exclusion",
                "enabled": True,
                "excluded_sectors": ["tobacco", "weapons"]
            }
        ]
        
        result = validator.validate_recommendation(tobacco_recommendation, policies)
        
        assert result["original_action"] == "BUY"
        assert result["validated_action"] == "HOLD"  # Downgraded!
        assert len(result["violations"]) == 1
        assert result["violations"][0]["severity"] == PolicyViolationSeverity.BLOCKING.value
        assert result["violation_badge"] is not None
        assert result["violation_badge"]["severity"] == "critical"

    def test_case_insensitive_sector_match(self, validator, sample_recommendation):
        """Test sector matching is case-insensitive."""
        weapons_recommendation = {
            **sample_recommendation,
            "ticker": "LMT",
            "sector": "Defense & Weapons",
            "action": "BUY"
        }
        
        policies = [
            {
                "type": "sector_exclusion",
                "enabled": True,
                "excluded_sectors": ["weapons"]
            }
        ]
        
        result = validator.validate_recommendation(weapons_recommendation, policies)
        
        assert result["validated_action"] == "HOLD"
        assert len(result["violations"]) == 1

    def test_disabled_policy_ignored(self, validator, sample_recommendation):
        """Test disabled policy is not enforced."""
        policies = [
            {
                "type": "sector_exclusion",
                "enabled": False,  # Disabled
                "excluded_sectors": ["Technology"]
            }
        ]
        
        result = validator.validate_recommendation(sample_recommendation, policies)
        
        assert result["validated_action"] == "BUY"
        assert result["violations"] == []


class TestRiskConcentrationPolicy:
    """Tests for risk concentration limit enforcement."""

    def test_risk_below_threshold(self, validator, sample_recommendation):
        """Test recommendation with acceptable risk passes."""
        policies = [
            {
                "type": "risk_concentration",
                "enabled": True,
                "max_risk_score": 0.7
            }
        ]
        
        result = validator.validate_recommendation(sample_recommendation, policies)
        
        assert result["validated_action"] == "BUY"
        assert result["violations"] == []

    def test_risk_exceeds_threshold_warning(self, validator, sample_recommendation):
        """Test high risk triggers warning but not blocking."""
        high_risk_recommendation = {
            **sample_recommendation,
            "ticker": "TSLA",
            "risk_score": 0.85,
            "action": "BUY"
        }
        
        policies = [
            {
                "type": "risk_concentration",
                "enabled": True,
                "max_risk_score": 0.7
            }
        ]
        
        result = validator.validate_recommendation(high_risk_recommendation, policies)
        
        # Risk violation is WARNING, not BLOCKING
        assert result["validated_action"] == "BUY"  # Not downgraded
        assert len(result["violations"]) == 1
        assert result["violations"][0]["severity"] == PolicyViolationSeverity.WARNING.value
        assert result["violation_badge"]["severity"] == "warning"


class TestPositionSizeLimit:
    """Tests for position size limit enforcement."""

    def test_position_size_within_limit(self, validator, sample_recommendation):
        """Test recommendation within position limit passes."""
        policies = [
            {
                "type": "position_size_limit",
                "enabled": True,
                "max_position_percentage": 20.0
            }
        ]
        
        result = validator.validate_recommendation(sample_recommendation, policies)
        
        assert result["validated_action"] == "BUY"
        assert result["violations"] == []

    def test_position_size_exceeds_limit_blocks_buy(self, validator, sample_recommendation):
        """Test oversized position blocks BUY."""
        oversized_recommendation = {
            **sample_recommendation,
            "ticker": "NVDA",
            "position_size_pct": 35.0,
            "action": "BUY"
        }
        
        policies = [
            {
                "type": "position_size_limit",
                "enabled": True,
                "max_position_percentage": 20.0
            }
        ]
        
        result = validator.validate_recommendation(oversized_recommendation, policies)
        
        assert result["original_action"] == "BUY"
        assert result["validated_action"] == "HOLD"
        assert len(result["violations"]) == 1
        assert result["violations"][0]["severity"] == PolicyViolationSeverity.BLOCKING.value


class TestESGMinimumPolicy:
    """Tests for ESG minimum score enforcement."""

    def test_esg_above_minimum(self, validator, sample_recommendation):
        """Test recommendation with good ESG score passes."""
        policies = [
            {
                "type": "esg_minimum",
                "enabled": True,
                "min_esg_score": 0.6
            }
        ]
        
        result = validator.validate_recommendation(sample_recommendation, policies)
        
        assert result["validated_action"] == "BUY"
        assert result["violations"] == []

    def test_esg_below_minimum_blocks_buy(self, validator, sample_recommendation):
        """Test low ESG score blocks BUY."""
        low_esg_recommendation = {
            **sample_recommendation,
            "ticker": "XOM",
            "esg_score": 0.35,
            "action": "BUY"
        }
        
        policies = [
            {
                "type": "esg_minimum",
                "enabled": True,
                "min_esg_score": 0.6
            }
        ]
        
        result = validator.validate_recommendation(low_esg_recommendation, policies)
        
        assert result["original_action"] == "BUY"
        assert result["validated_action"] == "HOLD"
        assert len(result["violations"]) == 1
        assert result["violations"][0]["severity"] == PolicyViolationSeverity.BLOCKING.value

    def test_esg_missing_score_no_violation(self, validator, sample_recommendation):
        """Test missing ESG score doesn't trigger violation."""
        no_esg_recommendation = {
            **sample_recommendation,
            "esg_score": None
        }
        
        policies = [
            {
                "type": "esg_minimum",
                "enabled": True,
                "min_esg_score": 0.6
            }
        ]
        
        result = validator.validate_recommendation(no_esg_recommendation, policies)
        
        assert result["validated_action"] == "BUY"
        assert result["violations"] == []


class TestGeographicRestriction:
    """Tests for geographic restriction enforcement."""

    def test_region_allowed(self, validator, sample_recommendation):
        """Test recommendation from allowed region passes."""
        policies = [
            {
                "type": "geographic_restriction",
                "enabled": True,
                "allowed_regions": ["US", "EU", "developed_markets"]
            }
        ]
        
        result = validator.validate_recommendation(sample_recommendation, policies)
        
        assert result["validated_action"] == "BUY"
        assert result["violations"] == []

    def test_region_restricted_warning(self, validator, sample_recommendation):
        """Test recommendation from restricted region triggers warning."""
        emerging_market_recommendation = {
            **sample_recommendation,
            "ticker": "BABA",
            "region": "China"
        }
        
        policies = [
            {
                "type": "geographic_restriction",
                "enabled": True,
                "allowed_regions": ["US", "EU"]
            }
        ]
        
        result = validator.validate_recommendation(emerging_market_recommendation, policies)
        
        # Geographic restriction is WARNING, not BLOCKING
        assert result["validated_action"] == "BUY"
        assert len(result["violations"]) == 1
        assert result["violations"][0]["severity"] == PolicyViolationSeverity.WARNING.value


class TestMultiplePolicies:
    """Tests for multiple policy enforcement."""

    def test_multiple_violations(self, validator):
        """Test recommendation violating multiple policies."""
        bad_recommendation = {
            "ticker": "TOBACCO_CN",
            "action": "BUY",
            "sector": "Tobacco",
            "risk_score": 0.9,
            "position_size_pct": 50.0,
            "esg_score": 0.2,
            "region": "China"
        }
        
        policies = [
            {
                "type": "sector_exclusion",
                "enabled": True,
                "excluded_sectors": ["tobacco"]
            },
            {
                "type": "risk_concentration",
                "enabled": True,
                "max_risk_score": 0.7
            },
            {
                "type": "position_size_limit",
                "enabled": True,
                "max_position_percentage": 20.0
            },
            {
                "type": "esg_minimum",
                "enabled": True,
                "min_esg_score": 0.6
            }
        ]
        
        result = validator.validate_recommendation(bad_recommendation, policies)
        
        assert result["original_action"] == "BUY"
        assert result["validated_action"] == "HOLD"
        assert len(result["violations"]) >= 3  # At least 3 blocking violations
        assert len(result["violation_badge"]["violations"]) >= 3

    def test_hold_action_not_downgraded(self, validator, sample_recommendation):
        """Test HOLD recommendation stays HOLD even with violations."""
        hold_recommendation = {
            **sample_recommendation,
            "action": "HOLD",
            "sector": "Tobacco"
        }
        
        policies = [
            {
                "type": "sector_exclusion",
                "enabled": True,
                "excluded_sectors": ["tobacco"]
            }
        ]
        
        result = validator.validate_recommendation(hold_recommendation, policies)
        
        # HOLD doesn't get downgraded further
        assert result["original_action"] == "HOLD"
        assert result["validated_action"] == "HOLD"
        # Violations still recorded for UI badge
        assert len(result["violations"]) == 1


class TestPolicyVersioning:
    """Tests for policy versioning and audit trail."""

    def test_policy_version_timestamp(self, validator, sample_recommendation):
        """Test policy version timestamp is present."""
        policies = []
        
        result = validator.validate_recommendation(sample_recommendation, policies)
        
        assert "policy_version" in result
        assert "validated_at" in result
        # ISO 8601 format
        assert "T" in result["policy_version"]
        assert result["policy_version"].endswith("Z")

    def test_violation_badge_includes_policy_version(self, validator):
        """Test violation badge includes policy version for audit."""
        bad_recommendation = {
            "ticker": "BAD",
            "action": "BUY",
            "sector": "Tobacco"
        }
        
        policies = [
            {
                "type": "sector_exclusion",
                "enabled": True,
                "excluded_sectors": ["tobacco"]
            }
        ]
        
        result = validator.validate_recommendation(bad_recommendation, policies)
        
        assert result["violation_badge"] is not None
        assert "policy_version" in result["violation_badge"]

    def test_policy_version_reuses_explicit_policy_revision(self, validator, sample_recommendation):
        """Test validation returns the stored policy revision when provided."""
        policies = [
            {
                "type": "sector_exclusion",
                "enabled": True,
                "excluded_sectors": ["tobacco"],
                "policy_version": "2026-03-11T09:00:00Z",
            }
        ]

        result = validator.validate_recommendation(sample_recommendation, policies)

        assert result["policy_version"] == "2026-03-11T09:00:00Z"
        assert result["validated_at"] == "2026-03-11T09:00:00Z"

    def test_policy_version_falls_back_to_updated_at(self, validator, sample_recommendation):
        """Test policy metadata timestamp is used when no explicit version exists."""
        policies = [
            {
                "type": "risk_concentration",
                "enabled": True,
                "max_risk_score": 0.7,
                "updated_at": "2026-03-11T10:15:00Z",
            }
        ]

        result = validator.validate_recommendation(sample_recommendation, policies)

        assert result["policy_version"] == "2026-03-11T10:15:00Z"
        assert result["validated_at"] == "2026-03-11T10:15:00Z"


class TestSingleton:
    """Tests for singleton pattern."""

    def test_get_policy_validator_singleton(self):
        """Test get_policy_validator returns singleton instance."""
        validator1 = get_policy_validator()
        validator2 = get_policy_validator()
        assert validator1 is validator2


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_policies_list(self, validator, sample_recommendation):
        """Test validation with empty policies list."""
        result = validator.validate_recommendation(sample_recommendation, [])
        
        assert result["validated_action"] == "BUY"
        assert result["violations"] == []
        assert result["violation_badge"] is None

    def test_recommendation_missing_ticker(self, validator):
        """Test validation with missing ticker."""
        recommendation = {
            "action": "BUY",
            "sector": "Technology"
        }
        
        result = validator.validate_recommendation(recommendation, [])
        
        assert result["ticker"] == "UNKNOWN"
        assert result["validated_action"] == "BUY"

    def test_recommendation_missing_action(self, validator):
        """Test validation with missing action defaults to HOLD."""
        recommendation = {
            "ticker": "AAPL",
            "sector": "Technology"
        }
        
        result = validator.validate_recommendation(recommendation, [])
        
        assert result["original_action"] == "HOLD"
        assert result["validated_action"] == "HOLD"

    def test_recommendation_missing_optional_fields(self, validator):
        """Test validation with missing optional fields."""
        minimal_recommendation = {
            "ticker": "AAPL",
            "action": "BUY"
        }
        
        policies = [
            {
                "type": "sector_exclusion",
                "enabled": True,
                "excluded_sectors": ["tobacco"]
            }
        ]
        
        result = validator.validate_recommendation(minimal_recommendation, policies)
        
        assert result["validated_action"] == "BUY"
        assert result["violations"] == []
