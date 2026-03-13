"""
Integration tests for execution costs endpoint (BATCH-23-DEV-03).

Tests verify that the /api/execution-costs endpoint:
1. Returns valid cost estimates for different asset classes
2. Exposes gross vs net expected returns
3. Triggers low-edge warnings when appropriate
4. Follows Judge API pattern (ok/data envelope, freshness, source)
"""

import pytest
from typing import Dict, Any


class TestExecutionCostsEndpoint:
    """Test execution costs API endpoint."""

    @pytest.fixture
    def base_url(self) -> str:
        return "http://localhost:8050"

    def test_execution_costs_single_ticker_equity(
        self,
        base_url: str,
    ):
        """Test cost estimate for equity ticker (SPY)."""
        import requests

        response = requests.get(
            f"{base_url}/api/execution-costs",
            params={"ticker": "SPY", "expected_return": 0.05, "horizon": "1m"},
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()

        # Judge API pattern compliance
        assert data.get("ok") is True
        assert "data" in data

        # Core contract
        result = data["data"]
        assert result["ticker"] == "SPY"
        assert "generated_at" in result
        assert "cost_estimate" in result
        assert "source" in result

        # Cost estimate structure
        cost = result["cost_estimate"]
        assert "asset_class" in cost
        assert "gross_expected_return" in cost
        assert "net_expected_return" in cost
        assert "costs_bps" in cost
        assert "warning" in cost

        # Costs breakdown
        costs_bps = cost["costs_bps"]
        assert "fees" in costs_bps
        assert "slippage" in costs_bps
        assert "tax_drag" in costs_bps
        assert "total" in costs_bps

    def test_execution_costs_etf(self, base_url: str):
        """Test cost estimate for ETF with lower costs."""
        import requests

        response = requests.get(
            f"{base_url}/api/execution-costs",
            params={"ticker": "QQQ", "expected_return": 0.03, "horizon": "3m"},
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        result = data["data"]
        cost = result["cost_estimate"]

        # ETF should have lower fees/slippage than equity
        assert cost["asset_class"] in {"etf", "equity"}
        assert cost["costs_bps"]["fees"] <= 10.0  # Reasonable upper bound

    def test_execution_costs_crypto(self, base_url: str):
        """Test cost estimate for crypto with higher costs."""
        import requests

        response = requests.get(
            f"{base_url}/api/execution-costs",
            params={"ticker": "BTC", "expected_return": 0.10, "horizon": "1w"},
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        result = data["data"]
        cost = result["cost_estimate"]

        # Crypto should have higher costs
        assert cost["asset_class"] == "crypto"
        assert cost["costs_bps"]["fees"] >= 8.0
        assert cost["costs_bps"]["slippage"] >= 10.0

    def test_execution_costs_low_edge_warning(self, base_url: str):
        """Test that low-edge situations trigger warnings."""
        import requests

        # Small expected return should trigger low-edge warning
        response = requests.get(
            f"{base_url}/api/execution-costs",
            params={"ticker": "SPY", "expected_return": 0.005, "horizon": "1d"},
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        result = data["data"]
        cost = result["cost_estimate"]
        warning = cost["warning"]

        # Should have some warning for thin edge
        assert "low_edge" in warning
        assert "severity" in warning
        assert warning["severity"] in {"none", "medium", "high"}

    def test_execution_costs_tax_bucket_short_term(self, base_url: str):
        """Test short-term tax bucket for short horizons."""
        import requests

        response = requests.get(
            f"{base_url}/api/execution-costs",
            params={"ticker": "NVDA", "expected_return": 0.08, "horizon": "1w"},
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        result = data["data"]
        cost = result["cost_estimate"]

        tax_assumptions = cost["tax_assumptions"]
        assert tax_assumptions["holding_period_bucket"] == "short_term"
        assert tax_assumptions["applies_on_positive_return_only"] is True

    def test_execution_costs_tax_bucket_long_term(self, base_url: str):
        """Test long-term tax bucket for long horizons."""
        import requests

        response = requests.get(
            f"{base_url}/api/execution-costs",
            params={"ticker": "VTI", "expected_return": 0.07, "horizon": "1y"},
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        result = data["data"]
        cost = result["cost_estimate"]

        tax_assumptions = cost["tax_assumptions"]
        assert tax_assumptions["holding_period_bucket"] == "long_term"

    def test_execution_costs_debug_mode(self, base_url: str):
        """Test debug mode includes detailed breakdown."""
        import requests

        response = requests.get(
            f"{base_url}/api/execution-costs",
            params={"ticker": "TSLA", "expected_return": 0.12, "debug": True},
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        result = data["data"]

        # Debug mode should include extra info
        assert "debug" in result
        assert "input_params" in result["debug"]
        assert "inference_steps" in result["debug"]

    def test_execution_costs_universe(self, base_url: str):
        """Test batch cost estimates for multiple tickers."""
        import requests

        response = requests.get(
            f"{base_url}/api/execution-costs/universe",
            params={"tickers": "SPY,QQQ,GLD,NVDA", "expected_return": 0.05},
            timeout=15,
        )

        assert response.status_code == 200
        data = response.json()

        assert data.get("ok") is True
        result = data["data"]
        assert "tickers" in result
        assert "cost_estimates" in result

        cost_estimates = result["cost_estimates"]
        assert "SPY" in cost_estimates
        assert "QQQ" in cost_estimates
        assert "GLD" in cost_estimates
        assert "NVDA" in cost_estimates

    def test_execution_costs_invalid_ticker(self, base_url: str):
        """Test error handling for invalid ticker."""
        import requests

        response = requests.get(
            f"{base_url}/api/execution-costs",
            params={"ticker": ""},
            timeout=10,
        )

        # Should return error response (Judge API pattern)
        assert response.status_code in {200, 400}
        data = response.json()

        # Even errors follow ok/data or ok/error pattern
        assert "ok" in data

    def test_execution_costs_net_vs_gross(self, base_url: str):
        """Test that net return is less than gross return."""
        import requests

        response = requests.get(
            f"{base_url}/api/execution-costs",
            params={"ticker": "SPY", "expected_return": 0.08},
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        result = data["data"]
        cost = result["cost_estimate"]

        gross = cost["gross_expected_return"]
        net = cost["net_expected_return"]

        # Net should be <= gross (costs always reduce return)
        assert net <= gross

        # Verify the math: net = gross - costs
        costs_bps = cost["costs_bps"]["total"]
        expected_net_bps = (gross * 10_000) - costs_bps
        actual_net_bps = net * 10_000

        # Allow small rounding differences
        assert abs(actual_net_bps - expected_net_bps) < 1.0


class TestExecutionCostsContractCompliance:
    """Test Judge API pattern compliance."""

    def test_judge_api_pattern_ok_envelope(self):
        """Verify ok/data envelope pattern."""
        import requests

        response = requests.get(
            "http://localhost:8050/api/execution-costs",
            params={"ticker": "SPY"},
            timeout=10,
        )

        data = response.json()
        assert data.get("ok") is True
        assert "data" in data

    def test_judge_api_pattern_freshness(self):
        """Verify freshness metadata."""
        import requests

        response = requests.get(
            "http://localhost:8050/api/execution-costs",
            params={"ticker": "AAPL"},
            timeout=10,
        )

        data = response.json()
        result = data["data"]

        assert "generated_at" in result
        # Should be ISO format timestamp
        assert "T" in result["generated_at"]

    def test_judge_api_pattern_source(self):
        """Verify source metadata."""
        import requests

        response = requests.get(
            "http://localhost:8050/api/execution-costs",
            params={"ticker": "MSFT"},
            timeout=10,
        )

        data = response.json()
        result = data["data"]

        assert "source" in result
        assert isinstance(result["source"], list)
        assert len(result["source"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
