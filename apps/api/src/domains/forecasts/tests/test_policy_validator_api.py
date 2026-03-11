"""
Policy Validator API Integration Tests (BATCH-20-DEV-02)

Tests for personal policy guardrails API endpoints:
- GET /forecasts/policy-validator/types
- GET /forecasts/policy-validator/template/{policy_type}
- GET /forecasts/policy-validator/user-policy
- POST /forecasts/policy-validator/user-policy
- POST /forecasts/policy-validator/validate
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from domains.forecasts.api import forecasts as forecasts_route


def _client() -> TestClient:
    """Create test client for forecasts API."""
    app = FastAPI()
    app.include_router(forecasts_route.router)
    return TestClient(app)


def test_list_policy_types():
    """Test listing available policy types."""
    client = _client()
    response = client.get("/forecasts/policy-validator/types")
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "policy_types" in data["data"]
    assert "count" in data["data"]
    assert data["data"]["count"] > 0
    
    policy_types = data["data"]["policy_types"]
    assert "sector_exclusion" in policy_types
    assert "risk_concentration" in policy_types
    assert "position_size_limit" in policy_types
    assert "esg_minimum" in policy_types
    assert "geographic_restriction" in policy_types


def test_get_policy_template_sector_exclusion():
    """Test getting sector exclusion policy template."""
    client = _client()
    response = client.get("/forecasts/policy-validator/template/sector_exclusion")
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "template" in data["data"]
    
    template = data["data"]["template"]
    assert template["type"] == "sector_exclusion"
    assert "excluded_sectors" in template
    assert template["enabled"] is True


def test_get_policy_template_risk_concentration():
    """Test getting risk concentration policy template."""
    client = _client()
    response = client.get("/forecasts/policy-validator/template/risk_concentration")
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    
    template = data["data"]["template"]
    assert template["type"] == "risk_concentration"
    assert "max_risk_score" in template
    assert template["max_risk_score"] == 0.7


def test_get_user_policy_empty():
    """Test getting user policy when none exists."""
    client = _client()
    response = client.get("/forecasts/policy-validator/user-policy")
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "policy" in data["data"]
    assert "has_policy" in data["data"]


def test_save_and_get_user_policy():
    """Test saving and retrieving user policy."""
    client = _client()
    
    # Save policy
    policy_payload = {
        "schema_version": "judge_personal_policy_v1",
        "policy_id": "test_policy",
        "policy_version": "v1",
        "excluded_tickers": ["TSLA", "GME"],
        "blocked_actions": ["sell"],
        "max_risk_level": "medium",
        "custom_rules": [
            {
                "id": "rule_1",
                "type": "sector_exclusion",
                "name": "No Tobacco",
                "enabled": True,
                "config": {"excluded_sectors": ["tobacco"]}
            }
        ]
    }
    
    save_response = client.post(
        "/forecasts/policy-validator/user-policy",
        json={"policy": policy_payload}
    )
    
    assert save_response.status_code == 200
    save_data = save_response.json()
    assert save_data["ok"] is True
    assert "saved_at" in save_data["data"]
    
    # Retrieve policy
    get_response = client.get("/forecasts/policy-validator/user-policy")
    
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["ok"] is True
    assert get_data["data"]["has_policy"] is True
    
    retrieved_policy = get_data["data"]["policy"]
    assert retrieved_policy["policy_id"] == "test_policy"
    assert "TSLA" in retrieved_policy["excluded_tickers"]
    assert "sell" in retrieved_policy["blocked_actions"]
    assert retrieved_policy["max_risk_level"] == "medium"
    assert len(retrieved_policy["custom_rules"]) == 1


def test_validate_recommendation_no_violations():
    """Test validating recommendation with no policy violations."""
    client = _client()
    
    payload = {
        "recommendation": {
            "ticker": "AAPL",
            "action": "BUY",
            "sector": "Technology",
            "risk_score": 0.45,
            "position_size_pct": 10.0,
            "esg_score": 0.75,
            "region": "US"
        },
        "user_policies": [
            {
                "type": "sector_exclusion",
                "enabled": True,
                "excluded_sectors": ["tobacco", "weapons"]
            },
            {
                "type": "risk_concentration",
                "enabled": True,
                "max_risk_score": 0.7
            }
        ]
    }
    
    response = client.post(
        "/forecasts/policy-validator/validate",
        json=payload
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "validation" in data["data"]
    
    validation = data["data"]["validation"]
    assert validation["ticker"] == "AAPL"
    assert validation["original_action"] == "BUY"
    assert validation["validated_action"] == "BUY"
    assert validation["violations"] == []
    assert validation["violation_badge"] is None


def test_validate_recommendation_sector_violation():
    """Test validating recommendation with sector exclusion violation."""
    client = _client()
    
    payload = {
        "recommendation": {
            "ticker": "MO",
            "action": "BUY",
            "sector": "Tobacco",
            "risk_score": 0.3,
            "position_size_pct": 5.0,
            "esg_score": 0.4,
            "region": "US"
        },
        "user_policies": [
            {
                "type": "sector_exclusion",
                "enabled": True,
                "excluded_sectors": ["tobacco", "weapons"]
            }
        ]
    }
    
    response = client.post(
        "/forecasts/policy-validator/validate",
        json=payload
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    
    validation = data["data"]["validation"]
    assert validation["ticker"] == "MO"
    assert validation["original_action"] == "BUY"
    assert validation["validated_action"] == "HOLD"  # Downgraded due to violation
    assert len(validation["violations"]) > 0
    assert validation["violation_badge"] is not None
    assert validation["violation_badge"]["visible"] is True
    assert validation["violation_badge"]["severity"] == "critical"


def test_validate_recommendation_risk_violation():
    """Test validating recommendation with risk concentration violation."""
    client = _client()
    
    payload = {
        "recommendation": {
            "ticker": "TSLA",
            "action": "BUY",
            "sector": "Automotive",
            "risk_score": 0.85,  # High risk
            "position_size_pct": 15.0,
            "esg_score": 0.6,
            "region": "US"
        },
        "user_policies": [
            {
                "type": "risk_concentration",
                "enabled": True,
                "max_risk_score": 0.6  # Conservative limit
            }
        ]
    }
    
    response = client.post(
        "/forecasts/policy-validator/validate",
        json=payload
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    
    validation = data["data"]["validation"]
    assert validation["ticker"] == "TSLA"
    assert validation["violations"] is not None
    assert len(validation["violations"]) > 0
    
    # Check violation details
    risk_violation = next(
        (v for v in validation["violations"] if v["rule_name"] == "risk_concentration"),
        None
    )
    assert risk_violation is not None
    assert "exceeds max" in risk_violation["reason"]


def test_validate_recommendation_multiple_violations():
    """Test validating recommendation with multiple policy violations."""
    client = _client()
    
    payload = {
        "recommendation": {
            "ticker": "GME",
            "action": "BUY",
            "sector": "Retail",
            "risk_score": 0.9,  # Very high risk
            "position_size_pct": 50.0,  # Very large position
            "esg_score": 0.3,  # Low ESG
            "region": "US"
        },
        "user_policies": [
            {
                "type": "risk_concentration",
                "enabled": True,
                "max_risk_score": 0.6
            },
            {
                "type": "position_size_limit",
                "enabled": True,
                "max_position_percentage": 20.0
            },
            {
                "type": "esg_minimum",
                "enabled": True,
                "min_esg_score": 0.5
            }
        ]
    }
    
    response = client.post(
        "/forecasts/policy-validator/validate",
        json=payload
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    
    validation = data["data"]["validation"]
    assert validation["ticker"] == "GME"
    assert validation["validated_action"] == "HOLD"  # Downgraded
    assert len(validation["violations"]) >= 3  # At least 3 violations
    assert validation["violation_badge"]["visible"] is True


def test_validate_recommendation_excluded_ticker():
    """Test validating recommendation for excluded ticker."""
    client = _client()
    
    # Note: ticker_exclusion is handled by judge_endpoint_service, not policy_validator
    # This test verifies the policy validator handles unknown policy types gracefully
    payload = {
        "recommendation": {
            "ticker": "TSLA",
            "action": "BUY",
            "sector": "Automotive",
            "risk_score": 0.5,
            "position_size_pct": 10.0
        },
        "user_policies": [
            {
                "type": "ticker_exclusion",
                "enabled": True,
                "excluded_tickers": ["TSLA", "GME"]
            }
        ]
    }
    
    response = client.post(
        "/forecasts/policy-validator/validate",
        json=payload
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    
    validation = data["data"]["validation"]
    assert validation["ticker"] == "TSLA"
    # ticker_exclusion is not a recognized policy type in policy_validator_service
    # It's handled at the judge endpoint level
    assert validation["validated_action"] == "BUY"  # No downgrade (unknown policy type)


def test_validate_recommendation_error_handling():
    """Test error handling in validation endpoint."""
    client = _client()
    
    # Empty payload
    response = client.post(
        "/forecasts/policy-validator/validate",
        json={}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "validation" in data["data"]
    
    # Should have fallback validation
    validation = data["data"]["validation"]
    assert validation["ticker"] == "UNKNOWN"
    assert validation["violations"] == []


def test_save_invalid_policy_format():
    """Test saving policy with invalid format."""
    client = _client()
    
    # Invalid: not a dict - the API handles this gracefully with error response
    response = client.post(
        "/forecasts/policy-validator/user-policy",
        json={"policy": "invalid_string"}
    )
    
    assert response.status_code == 200
    data = response.json()
    # API returns ok=True but with error field for invalid format
    assert "error" in data["data"] or data["data"].get("ok") is False
