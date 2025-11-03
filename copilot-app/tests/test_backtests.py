"""
Test Suite specifically for Backtests API endpoint
Created to verify the fixes for the runtime error and backend connectivity issues
"""
import sys
import os
import pytest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client for API testing."""
    app = create_app()
    return TestClient(app)


def test_backtests_endpoint_basic(client):
    """Test backtests endpoint returns correct structure."""
    response = client.get("/api/backtests")
    assert response.status_code == 200
    
    data = response.json()
    assert data["ok"] == True
    assert "data" in data  # Should have the data field from _ok() helper
    
    backtest_data = data["data"]
    # Should have the expected structure for the frontend
    assert "results" in backtest_data
    assert "params" in backtest_data
    assert "generated_at" in backtest_data
    
    # Verify results has the expected fields that the frontend accesses
    results = backtest_data["results"]
    assert "ok" in results
    assert "count_days" in results
    assert "avg_basket_return" in results
    assert "median" in results
    assert "stdev" in results


def test_backtests_endpoint_with_params(client):
    """Test backtests endpoint with query parameters."""
    response = client.get("/api/backtests?horizon=1w&top_n=3&days_back=90")
    assert response.status_code == 200
    
    data = response.json()
    assert data["ok"] == True
    assert "data" in data
    
    backtest_data = data["data"]
    assert "results" in backtest_data
    assert "params" in backtest_data
    assert "generated_at" in backtest_data
    
    # Verify the parameters were passed through correctly
    params = backtest_data["params"]
    assert params["horizon"] == "1w"
    assert params["top_n"] == 3
    assert params["days_back"] == 90


def test_backtests_endpoint_response_structure(client):
    """Test that the backtests response has the structure expected by the frontend."""
    response = client.get("/api/backtests")
    assert response.status_code == 200
    
    data = response.json()
    assert data["ok"] == True
    
    # This is the structure that the frontend BacktestResult interface expects:
    frontend_structure = data["data"]
    assert isinstance(frontend_structure, dict)
    
    # Required fields for the frontend
    assert "results" in frontend_structure
    assert "params" in frontend_structure
    assert "generated_at" in frontend_structure
    
    # Check results structure
    results = frontend_structure["results"]
    assert isinstance(results, dict)
    assert "ok" in results
    assert "count_days" in results
    assert "avg_basket_return" in results
    assert "median" in results
    assert "stdev" in results
    
    # Check params structure
    params = frontend_structure["params"]
    assert isinstance(params, dict)
    assert "horizon" in params
    assert "top_n" in params
    assert "days_back" in params
    
    # Verify data types that the frontend accesses
    assert isinstance(results["count_days"], int) or isinstance(results["count_days"], float)
    assert isinstance(results["avg_basket_return"], (int, float, type(None)))
    assert isinstance(results["median"], (int, float, type(None)))
    assert isinstance(results["stdev"], (int, float, type(None)))
    assert isinstance(params["top_n"], int)
    assert isinstance(params["days_back"], int)
    assert isinstance(params["horizon"], str)
    assert isinstance(frontend_structure["generated_at"], str)


def test_backtests_endpoint_no_crash_on_missing_data(client):
    """Test that backtests endpoint doesn't crash when no data is available."""
    response = client.get("/api/backtests")
    assert response.status_code == 200
    
    data = response.json()
    assert data["ok"] == True
    assert "data" in data
    
    # Even if there's no actual backtest data, the structure should be safe
    # This prevents the runtime crash where data.count_days was accessed directly
    backtest_data = data["data"]
    
    # Verify the structure is always safe to access (no null pointer exceptions)
    assert backtest_data is not None
    assert backtest_data.get("results") is not None
    assert backtest_data.get("params") is not None
    assert backtest_data.get("generated_at") is not None
    
    results = backtest_data["results"]
    assert results is not None
    assert "count_days" in results  # Should always have this field
    assert "avg_basket_return" in results
    assert "median" in results
    assert "stdev" in results


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])