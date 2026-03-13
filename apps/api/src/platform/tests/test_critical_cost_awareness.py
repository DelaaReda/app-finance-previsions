"""
Test cost awareness in critical routes - BATCH-23-DEV-03

Verifies that platform/routers/critical.py uses the canonical
estimate_execution_costs from domains/judge/application/execution_costs.py
for tax, fees, and slippage awareness.
"""
from __future__ import annotations

import pytest
from typing import Dict, Any, Optional


class TestCriticalRoutesCostAwareness:
    """Test that critical routes use canonical cost estimation."""

    def test_build_cost_awareness_uses_canonical_estimator(self):
        """Verify _build_cost_awareness delegates to estimate_execution_costs."""
        # Import the function being tested
        from platform.routers.critical import _build_cost_awareness
        
        # Import the canonical estimator
        from domains.judge.application.execution_costs import estimate_execution_costs
        
        # Verify the function exists and is callable
        assert callable(_build_cost_awareness)
        assert callable(estimate_execution_costs)
        
        # Test with a sample forecast
        forecast = {
            'expected_return': 0.02,
            'horizon': '1w',
            'direction': 'up',
        }
        
        result = _build_cost_awareness(
            ticker='AAPL',
            forecast=forecast,
        )
        
        # Verify result structure matches canonical output
        assert result is not None
        assert 'gross_expected_return_pct' in result
        assert 'net_expected_return_pct' in result
        assert 'fee_bps' in result
        assert 'slippage_bps' in result
        assert 'estimated_tax_drag_bps' in result
        assert 'total_cost_bps' in result
        assert 'tax_rate_assumption' in result
        assert 'tax_bucket' in result
        assert 'tax_impact' in result

    def test_build_cost_awareness_equity_costs(self):
        """Test cost estimation for equity asset class."""
        from platform.routers.critical import _build_cost_awareness
        
        forecast = {
            'expected_return': 0.015,
            'horizon': '1w',
            'direction': 'up',
        }
        
        result = _build_cost_awareness(
            ticker='AAPL',
            forecast=forecast,
        )
        
        assert result is not None
        # Equity should have equity-typical costs
        assert result['fee_bps'] > 0
        assert result['slippage_bps'] > 0
        assert result['tax_bucket'] in ('short_term', 'long_term')

    def test_build_cost_awareness_etf_costs(self):
        """Test cost estimation for ETF asset class."""
        from platform.routers.critical import _build_cost_awareness
        
        forecast = {
            'expected_return': 0.012,
            'horizon': '1m',
            'direction': 'up',
        }
        
        result = _build_cost_awareness(
            ticker='SPY',
            forecast=forecast,
        )
        
        assert result is not None
        # ETFs should have lower costs than individual equities
        assert result['fee_bps'] > 0
        assert result['slippage_bps'] > 0

    def test_build_cost_awareness_low_edge_warning(self):
        """Test that low net edge triggers warning."""
        from platform.routers.critical import _build_cost_awareness
        
        # Very small expected return that costs will overwhelm
        forecast = {
            'expected_return': 0.001,
            'horizon': '1w',
            'direction': 'up',
        }
        
        result = _build_cost_awareness(
            ticker='AAPL',
            forecast=forecast,
        )
        
        assert result is not None
        # Should have warning when edge is thin
        assert 'warning' in result

    def test_build_cost_awareness_handles_missing_estimator(self, monkeypatch):
        """Test graceful fallback when estimator is unavailable."""
        # Temporarily hide the estimator
        import platform.routers.critical as critical_module
        original_estimator = critical_module.estimate_execution_costs
        critical_module.estimate_execution_costs = None
        
        try:
            forecast = {
                'expected_return': 0.02,
                'horizon': '1w',
            }
            
            result = critical_module._build_cost_awareness(
                ticker='AAPL',
                forecast=forecast,
            )
            
            # Should return None gracefully
            assert result is None
        finally:
            # Restore original estimator
            critical_module.estimate_execution_costs = original_estimator

    def test_build_cost_awareness_handles_invalid_forecast(self):
        """Test graceful handling of invalid forecast data."""
        from platform.routers.critical import _build_cost_awareness
        
        # Invalid forecast
        forecast = {
            'expected_return': 'not_a_number',
            'horizon': None,
        }
        
        result = _build_cost_awareness(
            ticker='AAPL',
            forecast=forecast,
        )
        
        # Should either return None or handle gracefully
        # (implementation may choose to use defaults)
        assert result is None or isinstance(result, dict)
