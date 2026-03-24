"""
Regression coverage for the production execution-cost helpers.

BATCH-23 cost awareness depends on the live Judge route helpers for:
- asset class inference
- liquidity bucket inference
- fee/slippage/tax drag estimation
- low-edge warnings
"""

import sys
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domains.judge.api.judge import (  # noqa: E402
    _estimate_execution_costs,
    _infer_execution_asset_class,
    _infer_execution_liquidity_bucket,
)


class TestExecutionAssetClassInference:
    """Test asset class detection from ticker and features."""

    def test_equity_default(self):
        result = _infer_execution_asset_class(
            ticker="AAPL",
            row={},
            features={},
        )
        assert result == "equity"

    def test_etf_by_ticker(self):
        for ticker in ["SPY", "QQQ", "IWM", "TLT", "GLD"]:
            result = _infer_execution_asset_class(
                ticker=ticker,
                row={},
                features={},
            )
            assert result == "etf", f"Expected etf for {ticker}"

    def test_etf_by_fund_type(self):
        result = _infer_execution_asset_class(
            ticker="UNKNOWN",
            row={},
            features={"fundamentals_enriched": {"fundType": "ETF"}},
        )
        assert result == "etf"

    def test_crypto_by_asset_class(self):
        result = _infer_execution_asset_class(
            ticker="BTC",
            row={},
            features={"asset_class": "crypto"},
        )
        assert result == "crypto"


class TestLiquidityBucketInference:
    """Test liquidity bucket detection."""

    def test_liquid_large_cap(self):
        result = _infer_execution_liquidity_bucket(
            ticker="AAPL",
            asset_class="equity",
            features={"marketCap": 50_000_000_000},
            price_features={},
        )
        assert result == "liquid"

    def test_liquid_high_volume(self):
        result = _infer_execution_liquidity_bucket(
            ticker="AAPL",
            asset_class="equity",
            features={"avgVolume": 10_000_000},
            price_features={},
        )
        assert result == "liquid"

    def test_medium_cap(self):
        result = _infer_execution_liquidity_bucket(
            ticker="AAPL",
            asset_class="equity",
            features={"marketCap": 5_000_000_000},
            price_features={},
        )
        assert result == "medium"

    def test_illiquid_small_cap(self):
        result = _infer_execution_liquidity_bucket(
            ticker="AAPL",
            asset_class="equity",
            features={"marketCap": 500_000_000},
            price_features={},
        )
        assert result == "illiquid"

    def test_crypto_liquid(self):
        result = _infer_execution_liquidity_bucket(
            ticker="BTC",
            asset_class="crypto",
            features={"avgVolume": 150_000_000},
            price_features={},
        )
        assert result == "liquid"

    def test_high_volatility_downgrade(self):
        result = _infer_execution_liquidity_bucket(
            ticker="AAPL",
            asset_class="equity",
            features={"marketCap": 50_000_000_000},
            price_features={"price_stats": {"vol_1m": 0.12}},
        )
        assert result == "illiquid"


class TestExecutionCostEstimation:
    """Test cost estimation logic."""

    def test_liquid_equity_costs(self):
        result = _estimate_execution_costs(
            ticker="AAPL",
            expected_return=0.05,
            horizon="1m",
            row={},
            features={"marketCap": 1_000_000_000_000},
            price_features={},
        )
        assert result["asset_class"] == "equity"
        assert result["liquidity_bucket"] == "liquid"
        assert result["gross_expected_return"] == 0.05
        assert result["gross_expected_effect_bps"] == 500.0
        assert result["costs_bps"]["fees"]["base"] == 3.0
        assert result["costs_bps"]["slippage"]["base"] == 8.0

    def test_etf_costs(self):
        result = _estimate_execution_costs(
            ticker="SPY",
            expected_return=0.03,
            horizon="1m",
            row={},
            features={"avgVolume": 100_000_000},
            price_features={},
        )
        assert result["asset_class"] == "etf"
        assert result["liquidity_bucket"] == "liquid"
        assert result["costs_bps"]["fees"]["base"] == 2.0
        assert result["costs_bps"]["slippage"]["base"] == 5.0

    def test_crypto_costs(self):
        result = _estimate_execution_costs(
            ticker="BTC",
            expected_return=0.10,
            horizon="1m",
            row={},
            features={"asset_class": "crypto", "avgVolume": 200_000_000},
            price_features={},
        )
        assert result["asset_class"] == "crypto"
        assert result["liquidity_bucket"] == "liquid"
        assert result["costs_bps"]["fees"]["base"] == 12.0
        assert result["costs_bps"]["slippage"]["base"] == 18.0

    def test_net_return_calculation(self):
        result = _estimate_execution_costs(
            ticker="AAPL",
            expected_return=0.05,
            horizon="1m",
            row={},
            features={"marketCap": 1_000_000_000_000},
            price_features={},
        )
        assert result["net_expected_return"] is not None
        assert abs(result["net_expected_return"] - 0.0389) < 0.001

    def test_long_term_tax_bucket(self):
        result = _estimate_execution_costs(
            ticker="AAPL",
            expected_return=0.10,
            horizon="1y",
            row={},
            features={"marketCap": 1_000_000_000_000},
            price_features={},
        )
        assert result["tax_assumptions"]["holding_period_bucket"] == "long_term"
        assert result["tax_assumptions"]["tax_rate_band"]["base"] == 0.10

    def test_short_term_tax_bucket(self):
        result = _estimate_execution_costs(
            ticker="AAPL",
            expected_return=0.10,
            horizon="3m",
            row={},
            features={"marketCap": 1_000_000_000_000},
            price_features={},
        )
        assert result["tax_assumptions"]["holding_period_bucket"] == "short_term"
        assert result["tax_assumptions"]["tax_rate_band"]["base"] == 0.20


class TestLowEdgeWarning:
    """Test low edge warning logic."""

    def test_no_warning_healthy_edge(self):
        result = _estimate_execution_costs(
            ticker="AAPL",
            expected_return=0.10,
            horizon="1m",
            row={},
            features={"marketCap": 1_000_000_000_000},
            price_features={},
        )
        assert result["warning"]["low_edge"] is False
        assert result["warning"]["severity"] == "none"
        assert result["warning"]["message"] is None

    def test_medium_warning_thin_edge(self):
        result = _estimate_execution_costs(
            ticker="AAPL",
            expected_return=0.005,
            horizon="1m",
            row={},
            features={"marketCap": 1_000_000_000_000, "avgVolume": 10_000_000},
            price_features={},
        )
        assert result["warning"]["low_edge"] is True
        assert result["warning"]["severity"] == "medium"
        assert result["warning"]["message"] is not None
        assert "thin" in result["warning"]["message"].lower()

    def test_high_warning_negative_edge(self):
        result = _estimate_execution_costs(
            ticker="ILLIQUID",
            expected_return=0.003,
            horizon="1m",
            row={},
            features={"marketCap": 100_000_000},
            price_features={},
        )
        assert result["warning"]["low_edge"] is True
        assert result["warning"]["severity"] == "high"
        assert result["warning"]["message"] is not None
        assert "negative" in result["warning"]["message"].lower()

    def test_no_warning_zero_return(self):
        result = _estimate_execution_costs(
            ticker="AAPL",
            expected_return=-0.02,
            horizon="1m",
            row={},
            features={"marketCap": 1_000_000_000_000},
            price_features={},
        )
        assert result["warning"]["low_edge"] is False


class TestCostBreakdown:
    """Test detailed cost breakdown presentation."""

    def test_cost_components(self):
        result = _estimate_execution_costs(
            ticker="AAPL",
            expected_return=0.05,
            horizon="1m",
            row={},
            features={"marketCap": 1_000_000_000_000},
            price_features={},
        )
        costs = result["costs_bps"]
        assert "fees" in costs
        assert "slippage" in costs
        assert "tax_drag" in costs
        assert "total" in costs

        for component in ["fees", "slippage", "tax_drag", "total"]:
            assert "low" in costs[component]
            assert "base" in costs[component]
            assert "high" in costs[component]

    def test_model_version(self):
        result = _estimate_execution_costs(
            ticker="AAPL",
            expected_return=0.05,
            horizon="1m",
            row={},
            features={"marketCap": 1_000_000_000_000},
            price_features={},
        )
        assert result["model_version"] == "judge_execution_costs_v1"
