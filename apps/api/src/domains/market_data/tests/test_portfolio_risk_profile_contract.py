from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
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


def test_portfolio_risk_profile_route_delegates_to_endpoint_service(monkeypatch):
    captured = {}
    now_iso = "2026-03-09T06:30:00Z"

    def fake_payload(**kwargs):
        captured.update(kwargs)
        return {
            "ok": True,
            "data": {
                "portfolio": {
                    "id": "portfolio-123",
                    "name": "Core",
                    "description": "",
                    "tickers": ["AAPL"],
                    "tickers_count": 1,
                    "updated_at": now_iso,
                },
                "benchmark": "SPY",
                "weights": {"AAPL": 1.0},
                "metrics": {},
                "risk_profile": "balanced",
                "risk_level": "medium",
                "risk": {"level": "medium", "caveat": ""},
                "why": ["Synthetic response."],
                "warnings": [],
                "filters_applied": {
                    "portfolio_id": "portfolio-123",
                    "benchmark": "SPY",
                    "start_date": None,
                    "end_date": None,
                },
                "stats": {
                    "tickers_count": 1,
                    "equal_weight_assumption": False,
                    "weights_source": "portfolio_metadata",
                    "has_live_metrics": False,
                    "non_null_metrics": 0,
                },
                "confidence": 0.45,
                "generated_at": now_iso,
                "freshness": now_iso,
                "status": "ok",
                "error": None,
                "source": ["portfolio_risk_profile_service"],
                "verdict": "hold",
            },
            "freshness": now_iso,
            "status": "ok",
            "error": None,
        }

    monkeypatch.setattr(portfolios_route, "get_portfolio_risk_profile_payload", fake_payload)

    response = _client().get("/api/portfolios/portfolio-123/risk-profile?benchmark=SPY")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["status"] == "ok"
    assert payload["freshness"] == now_iso
    assert captured["portfolio_id"] == "portfolio-123"
    assert captured["benchmark"] == "SPY"
    assert captured["start_date"] is None
    assert captured["end_date"] is None
    assert callable(captured["get_portfolio_service_fn"])


def test_portfolio_create_and_update_validate_profile_metadata(monkeypatch, tmp_path):
    service = portfolio_app.PortfolioService(
        storage_path=str(tmp_path / "user_portfolios.json")
    )
    monkeypatch.setattr(portfolios_route, "get_portfolio_service", lambda: service)

    create_response = _client().post(
        "/api/portfolios",
        json={
            "name": "Retirement",
            "tickers": ["msft", "aapl"],
            "metadata": {
                "weights": {"msft": 70, "aapl": 30},
                "horizon": "1Y",
                "conviction": "HIGH",
                "risk_tolerance": "moderate",
            },
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()["data"]
    assert created["metadata"] == {
        "weights": {"MSFT": 70.0, "AAPL": 30.0},
        "horizon": "1y",
        "conviction": "high",
        "risk_tolerance": "moderate",
    }

    update_response = _client().put(
        f"/api/portfolios/{created['id']}",
        json={"metadata": {"unknown_flag": True}},
    )

    assert update_response.status_code == 422


def test_portfolio_risk_profile_endpoint_returns_stable_contract(monkeypatch, tmp_path):
    service = portfolio_app.PortfolioService(
        storage_path=str(tmp_path / "user_portfolios.json")
    )
    portfolio = service.create_portfolio(
        name="Core",
        tickers=["MSFT", "AAPL"],
        metadata={
            "weights": {"MSFT": 70, "AAPL": 30},
            "horizon": "1y",
            "conviction": "medium",
            "risk_tolerance": "moderate",
        },
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
    assert payload["status"] == "ok"
    assert payload["error"] is None
    assert payload["freshness"] == data["freshness"]
    assert data["last_update"] == data["freshness"]
    assert data["portfolio"]["id"] == portfolio.id
    assert data["portfolio"]["tickers_count"] == 2
    assert data["portfolio"]["state"] == {
        "horizon": "1y",
        "conviction": "medium",
        "risk_tolerance": "moderate",
    }
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
    assert "portfolio_risk_profile_service" in data["source"]
    assert "metadata_contract_v1" in data["source"]
    assert data["status"] == "ok"
    assert data["error"] is None
    assert any("normalized" in warning.lower() for warning in data["warnings"])


def test_portfolio_risk_profile_surfaces_saved_state_guardrails(
    monkeypatch, tmp_path
):
    service = portfolio_app.PortfolioService(
        storage_path=str(tmp_path / "user_portfolios.json")
    )
    portfolio = service.create_portfolio(
        name="Concentrated Growth",
        tickers=["NVDA", "TSLA"],
        metadata={
            "weights": {"NVDA": 80, "TSLA": 20},
            "horizon": "1m",
            "conviction": "high",
            "risk_tolerance": "conservative",
        },
    )

    class FakePerformanceService:
        def calculate_performance(self, *, tickers, weights, start_date, end_date, benchmark):
            assert tickers == ["NVDA", "TSLA"]
            assert weights == {"NVDA": 0.8, "TSLA": 0.2}
            assert benchmark == "QQQ"
            return (
                perf_app.PortfolioMetrics(
                    total_return=0.22,
                    annualized_return=0.20,
                    volatility=0.36,
                    sharpe_ratio=0.70,
                    max_drawdown=-0.28,
                    win_rate=0.55,
                ),
                perf_app.BenchmarkComparison(
                    benchmark_ticker="QQQ",
                    portfolio_return=0.22,
                    benchmark_return=0.12,
                    outperformance=0.10,
                    correlation=0.88,
                    beta=1.24,
                    alpha=0.05,
                ),
                perf_app.PerformanceTimeSeries(),
            )

    monkeypatch.setattr(portfolios_route, "get_portfolio_service", lambda: service)
    monkeypatch.setattr(
        portfolio_app, "_get_performance_service", lambda: FakePerformanceService()
    )

    response = _client().get(f"/api/portfolios/{portfolio.id}/risk-profile?benchmark=QQQ")

    assert response.status_code == 200
    data = response.json()["data"]

    assert data["risk_profile"] == "high_beta"
    assert data["risk_level"] == "high"
    assert any("saved horizon is 1m" in reason.lower() for reason in data["why"])
    assert any(
        "saved conviction is high" in warning.lower() for warning in data["warnings"]
    )
    assert any(
        "saved risk tolerance is conservative" in warning.lower()
        and "computed profile is high" in warning.lower()
        for warning in data["warnings"]
    )


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
    assert payload["status"] == "degraded"
    assert payload["error"] == "performance backend unavailable"
    assert payload["freshness"] == data["freshness"]
    assert data["last_update"] == data["freshness"]
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
    assert data["status"] == "degraded"
    assert data["error"] == "performance backend unavailable"
    assert "portfolio_risk_profile_service" in data["source"]
    assert "metadata_contract_v1" in data["source"]
    assert any("fallback" in warning.lower() for warning in data["warnings"])
    assert any("unknown tickers" in warning.lower() for warning in data["warnings"])


@pytest.mark.parametrize("weight_field", ["weights", "position_weights"])
def test_portfolio_performance_uses_saved_metadata_weights(
    monkeypatch, tmp_path, weight_field
):
    service = portfolio_app.PortfolioService(
        storage_path=str(tmp_path / "user_portfolios.json")
    )
    portfolio = service.create_portfolio(
        name="Weighted",
        tickers=["MSFT", "AAPL"],
        metadata={weight_field: {"MSFT": 70, "AAPL": 30}},
    )
    captured = {}

    class FakePerformanceService:
        def calculate_performance(
            self, *, tickers, weights, start_date, end_date, benchmark
        ):
            captured.update(
                {
                    "tickers": tickers,
                    "weights": weights,
                    "start_date": start_date,
                    "end_date": end_date,
                    "benchmark": benchmark,
                }
            )
            return (
                perf_app.PortfolioMetrics(
                    total_return=0.12,
                    annualized_return=0.10,
                    volatility=0.18,
                    sharpe_ratio=1.15,
                ),
                perf_app.BenchmarkComparison(
                    benchmark_ticker="SPY",
                    portfolio_return=0.12,
                    benchmark_return=0.09,
                    outperformance=0.03,
                ),
                perf_app.PerformanceTimeSeries(),
            )

    monkeypatch.setattr(
        portfolio_app, "_get_performance_service", lambda: FakePerformanceService()
    )

    performance = service.get_performance(portfolio.id, benchmark="SPY")

    assert performance is not None
    assert captured == {
        "tickers": ["AAPL", "MSFT"],
        "weights": {"AAPL": 0.3, "MSFT": 0.7},
        "start_date": None,
        "end_date": None,
        "benchmark": "SPY",
    }
    assert performance.total_return == 0.12
    assert performance.avg_return == 0.10
    assert performance.vs_benchmark == {
        "benchmark": "SPY",
        "outperformance": 0.03,
    }


@pytest.mark.parametrize("weight_field", ["weights", "position_weights"])
def test_portfolio_performance_timeseries_uses_saved_metadata_weights(
    monkeypatch, tmp_path, weight_field
):
    service = portfolio_app.PortfolioService(
        storage_path=str(tmp_path / "user_portfolios.json")
    )
    portfolio = service.create_portfolio(
        name="Weighted",
        tickers=["MSFT", "AAPL"],
        metadata={weight_field: {"MSFT": 70, "AAPL": 30}},
    )
    captured = []

    class FakePerformanceService:
        def calculate_performance(
            self, *, tickers, weights, start_date, end_date, benchmark
        ):
            captured.append(
                {
                    "tickers": tickers,
                    "weights": weights,
                    "start_date": start_date,
                    "end_date": end_date,
                    "benchmark": benchmark,
                }
            )
            return (
                perf_app.PortfolioMetrics(total_return=0.12),
                perf_app.BenchmarkComparison(
                    benchmark_ticker=benchmark,
                    portfolio_return=0.12,
                    benchmark_return=0.09,
                    outperformance=0.03,
                ),
                perf_app.PerformanceTimeSeries(
                    dates=["2026-03-09"],
                    equity_curve=[1.0],
                    drawdown=[0.0],
                    returns=[0.0],
                ),
            )

    monkeypatch.setattr(portfolios_route, "get_portfolio_service", lambda: service)
    monkeypatch.setattr(
        portfolios_route, "_get_performance_service", lambda: FakePerformanceService()
    )

    response = _client().get(f"/api/portfolios/{portfolio.id}/performance/timeseries")

    assert response.status_code == 200
    assert captured == [
        {
            "tickers": ["AAPL", "MSFT"],
            "weights": {"AAPL": 0.3, "MSFT": 0.7},
            "start_date": None,
            "end_date": None,
            "benchmark": "SPY",
        },
        {
            "tickers": ["SPY"],
            "weights": None,
            "start_date": None,
            "end_date": None,
            "benchmark": "SPY",
        },
    ]
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["portfolio"]["equity_curve"] == [1.0]
    assert payload["data"]["comparison"]["benchmark_ticker"] == "SPY"


def test_portfolio_service_reload_normalizes_legacy_tickers_and_metadata(tmp_path):
    storage_path = tmp_path / "user_portfolios.json"
    storage_path.write_text(
        json.dumps(
            {
                "portfolio-123": {
                    "id": "portfolio-123",
                    "name": "Legacy",
                    "description": "",
                    "tickers": ["msft", " aapl ", "MSFT"],
                    "created_at": "2026-03-09T00:00:00+00:00",
                    "updated_at": "2026-03-09T00:00:00+00:00",
                    "metadata": {
                        "weights": {"msft": 70, "aapl": 30},
                        "horizon": "1Y",
                        "conviction": "HIGH",
                        "risk_tolerance": "balanced",
                        "unknown_flag": True,
                    },
                }
            }
        )
    )

    service = portfolio_app.PortfolioService(storage_path=str(storage_path))

    portfolio = service.get_portfolio("portfolio-123")
    assert portfolio is not None
    assert portfolio.tickers == ["AAPL", "MSFT"]
    assert portfolio.metadata.model_dump(exclude_none=True) == {
        "weights": {"MSFT": 70.0, "AAPL": 30.0},
        "horizon": "1y",
        "conviction": "high",
        "risk_tolerance": "moderate",
    }

    risk_profile = service.get_risk_profile("portfolio-123")
    assert risk_profile is not None
    assert risk_profile.portfolio["tickers"] == ["AAPL", "MSFT"]
    assert risk_profile.portfolio["state"] == {
        "horizon": "1y",
        "conviction": "high",
        "risk_tolerance": "moderate",
    }

    persisted = json.loads(storage_path.read_text())
    assert persisted["portfolio-123"]["tickers"] == ["AAPL", "MSFT"]
    assert persisted["portfolio-123"]["metadata"] == {
        "weights": {"MSFT": 70.0, "AAPL": 30.0},
        "horizon": "1y",
        "conviction": "high",
        "risk_tolerance": "moderate",
    }
