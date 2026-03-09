from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domains.market_data.api import portfolios as portfolios_route
from domains.market_data.application import portfolio_performance_service as perf_app
from domains.market_data.application import portfolio_service as portfolio_app


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(portfolios_route.router)
    return TestClient(app)


def test_portfolio_risk_profile_endpoint_returns_stable_contract(monkeypatch, tmp_path):
    service = portfolio_app.PortfolioService(
        storage_path=str(tmp_path / "user_portfolios.json")
    )
    portfolio = service.create_portfolio(
        name="Core",
        tickers=["MSFT", "AAPL"],
        metadata={"weights": {"MSFT": 70, "AAPL": 30}},
    )

    class FakePerformanceService:
        def calculate_performance(self, *, tickers, weights, start_date, end_date, benchmark):
            assert set(tickers) == {"AAPL", "MSFT"}
            assert weights == {"AAPL": 0.3, "MSFT": 0.7}
            assert benchmark == "SPY"
            return (
                perf_app.PortfolioMetrics(
                    total_return=0.12,
                    annualized_return=0.10,
                    volatility=0.18,
                    sharpe_ratio=1.15,
                    max_drawdown=-0.08,
                    win_rate=0.57,
                    best_day=0.03,
                    worst_day=-0.02,
                ),
                perf_app.BenchmarkComparison(
                    benchmark_ticker="SPY",
                    portfolio_return=0.12,
                    benchmark_return=0.09,
                    outperformance=0.03,
                    correlation=0.81,
                    beta=0.94,
                    alpha=0.02,
                ),
                perf_app.PerformanceTimeSeries(),
            )

    monkeypatch.setattr(portfolios_route, "get_portfolio_service", lambda: service)
    monkeypatch.setattr(
        portfolio_app, "_get_performance_service", lambda: FakePerformanceService()
    )

    response = _client().get(f"/api/portfolios/{portfolio.id}/risk-profile?benchmark=SPY")

    assert response.status_code == 200
    payload = response.json()
    data = payload["data"]

    assert payload["ok"] is True
    assert data["portfolio"]["id"] == portfolio.id
    assert data["portfolio"]["tickers_count"] == 2
    assert data["risk_profile"] == "balanced"
    assert data["risk_level"] == "medium"
    assert data["risk"]["level"] == "medium"
    assert data["stats"]["has_live_metrics"] is True
    assert data["stats"]["equal_weight_assumption"] is False
    assert data["stats"]["weights_source"] == "portfolio_metadata"
    assert data["stats"]["non_null_metrics"] >= 6
    assert data["stats"]["largest_position_ticker"] == "MSFT"
    assert data["stats"]["largest_position_weight"] == 0.7
    assert data["weights"] == {"AAPL": 0.3, "MSFT": 0.7}
    assert sum(data["weights"].values()) == 1.0
    assert data["filters_applied"]["benchmark"] == "SPY"
    assert data["verdict"] == "hold"
    assert data["source"][0] == "portfolio_service"
    assert any("normalized" in warning.lower() for warning in data["warnings"])


def test_portfolio_risk_profile_endpoint_falls_back_without_live_metrics(
    monkeypatch, tmp_path
):
    service = portfolio_app.PortfolioService(
        storage_path=str(tmp_path / "user_portfolios.json")
    )
    portfolio = service.create_portfolio(
        name="Focused",
        tickers=["NVDA"],
        metadata={"weights": {"MSFT": 1.0}},
    )

    class BrokenPerformanceService:
        def calculate_performance(self, *, tickers, weights, start_date, end_date, benchmark):
            raise RuntimeError("performance backend unavailable")

    monkeypatch.setattr(portfolios_route, "get_portfolio_service", lambda: service)
    monkeypatch.setattr(
        portfolio_app, "_get_performance_service", lambda: BrokenPerformanceService()
    )

    response = _client().get(
        f"/api/portfolios/{portfolio.id}/risk-profile?benchmark=QQQ"
    )

    assert response.status_code == 200
    payload = response.json()
    data = payload["data"]

    assert payload["ok"] is True
    assert data["portfolio"]["id"] == portfolio.id
    assert data["filters_applied"]["benchmark"] == "QQQ"
    assert data["stats"]["equal_weight_assumption"] is True
    assert data["stats"]["has_live_metrics"] is False
    assert data["stats"]["weights_source"] == "equal_weight_fallback"
    assert data["error"] == "performance backend unavailable"
    assert "fallback" in " ".join(data["source"])
    assert data["weights"] == {"NVDA": 1.0}
    assert data["metrics"] == {}
    assert data["risk"]["level"] == "medium"
    assert data["risk_profile"] == "balanced"
    assert any("fallback" in warning.lower() for warning in data["warnings"])
    assert any("unknown tickers" in warning.lower() for warning in data["warnings"])
