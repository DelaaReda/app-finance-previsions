"""
API Routes for Backtests - Finance Copilot System
Serves backtest results comparing forecasts to actual market performance
"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

from core.response import ok, err
from backend.storage.io import load_json, save_json
from backend.services.cache_layer import load_or_compute

router = APIRouter()

@router.get("/backtests")
def get_backtests(
    ticker: Optional[str] = Query(None, description="Filter by specific ticker"),
    horizon: Optional[str] = Query(None, description="Filter by forecast horizon (1d, 1w, 1m)"),
    min_confidence: Optional[float] = Query(0.0, description="Minimum confidence threshold (0.0-1.0)"),
    limit: Optional[int] = Query(None, description="Maximum number of results to return")
) -> Dict[str, Any]:
    """
    Get backtest results comparing forecasts to actual market performance.
    Returns metrics on forecast accuracy including hit rate and expected returns.
    """
    try:
        # Load backtest results from persistent storage
        backtests_data = load_json("backtests")
        
        if not backtests_data:
            # Return empty metrics structure but never fail
            return ok({
                "results": {
                    "hit_rate": 0.0,
                    "avg_er": 0.0,
                    "n_trades": 0,
                    "total_evaluated": 0,
                    "correct_predictions": 0,
                    "start_date": None,
                    "end_date": None,
                    "avg_confidence": 0.0,
                    "success_rate": 0.0,
                    "sample_size": 0,
                    "accuracy": 0.0
                },
                "params": {
                    "ticker_filter": ticker,
                    "horizon_filter": horizon,
                    "min_confidence": min_confidence,
                    "limit": limit
                },
                "freshness": "unknown",
                "generated_at": datetime.utcnow().isoformat(),
                "source": ["fallback_empty"],
                "message": "No backtest data available - forecasts are being evaluated against market data"
            })
        
        # Extract the results from the loaded data
        results = backtests_data.get("results", {})
        
        # Apply filters if specified
        filtered_results = results.copy()
        
        if ticker:
            # Filter by ticker if needed - this would require adjusting the actual backtest results
            # For now, we'll still return overall metrics but indicate the filter
            filtered_results["filtered_by_ticker"] = ticker
            
        if horizon:
            filtered_results["filtered_by_horizon"] = horizon
            
        if min_confidence > 0.0:
            filtered_results["filtered_by_min_confidence"] = min_confidence
            
        # Apply limit if specified
        if limit and "backtest_results" in filtered_results:
            filtered_results["backtest_results"] = filtered_results["backtest_results"][:limit]
        
        return ok({
            "results": filtered_results,
            "params": {
                "ticker_filter": ticker,
                "horizon_filter": horizon,
                "min_confidence": min_confidence,
                "limit": limit
            },
            "freshness": backtests_data.get("freshness", "unknown"),
            "generated_at": datetime.utcnow().isoformat(),
            "source": backtests_data.get("source", ["backtests_job"]),
            "status": "active"
        })
        
    except Exception as e:
        # Return structured error response instead of crashing
        return err(500, f"Error in backtests endpoint: {str(e)}")


@router.get("/backtests/metrics")
def get_backtest_metrics() -> Dict[str, Any]:
    """
    Get high-level backtest metrics overview.
    """
    try:
        backtests_data = load_json("backtests")
        
        if not backtests_data or not backtests_data.get("results"):
            return ok({
                "overall_hit_rate": 0.0,
                "avg_expected_return": 0.0,
                "total_trades_evaluated": 0,
                "accuracy_trend": "unknown",
                "avg_confidence": 0.0,
                "last_update": None,
                "model_performance": {
                    "precision": 0.0,
                    "recall": 0.0,
                    "f1_score": 0.0
                }
            })
        
        results = backtests_data.get("results", {})
        
        return ok({
            "overall_hit_rate": results.get("hit_rate", 0.0),
            "avg_expected_return": results.get("avg_er", 0.0),
            "total_trades_evaluated": results.get("n_trades", 0),
            "accuracy_trend": results.get("trend", "stable"),
            "avg_confidence": results.get("avg_confidence", 0.0),
            "last_update": results.get("generated_at", backtests_data.get("generated_at")),
            "model_performance": {
                "precision": results.get("hit_rate", 0.0),  # Using hit_rate as precision proxy
                "recall": results.get("recall", results.get("hit_rate", 0.0)),
                "f1_score": results.get("f1_score", 0.0),
                "accuracy": results.get("accuracy", 0.0)
            }
        })
    except Exception as e:
        return err(500, f"Error getting backtest metrics: {str(e)}")


@router.get("/backtests/detail/{ticker}")
def get_backtest_detail(ticker: str) -> Dict[str, Any]:
    """
    Get detailed backtest results for a specific ticker.
    """
    try:
        backtests_data = load_json("backtests")
        
        if not backtests_data or not backtests_data.get("results"):
            return ok({
                "ticker": ticker,
                "results": [],
                "summary": {
                    "hit_rate": 0.0,
                    "avg_er": 0.0,
                    "n_trades": 0,
                    "message": f"No backtest data available for {ticker}"
                },
                "freshness": "unknown",
                "generated_at": datetime.utcnow().isoformat()
            })
        
        # In real implementation, this would filter by specific ticker
        # For now, return a summary based on available data
        results = backtests_data.get("results", {})
        
        # Return specific metrics for this ticker (in a real implementation,
        # this would filter the detailed results) 
        ticker_summary = {
            "ticker": ticker,
            "hit_rate": results.get("hit_rate", 0.0),
            "avg_er": results.get("avg_er", 0.0),
            "n_trades": results.get("n_trades", 0),
            "avg_confidence": results.get("avg_confidence", 0.0),
            "total_evaluated": results.get("total_evaluated", 0),
            "correct_predictions": results.get("correct_predictions", 0)
        }
        
        return ok({
            "ticker": ticker,
            "results": [ticker_summary],  # Would have more details in real implementation
            "summary": ticker_summary,
            "freshness": backtests_data.get("freshness", "unknown"),
            "generated_at": datetime.utcnow().isoformat(),
            "source": backtests_data.get("source", ["backtests_job"])
        })
        
    except Exception as e:
        return err(500, f"Error getting details for {ticker}: {str(e)}")


# Pydantic model for backtest parameters
class BacktestRunRequest(BaseModel):
    tickers: Optional[List[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    strategy: Optional[str] = "momentum"
    horizon: Optional[str] = "1d"
    min_confidence: Optional[float] = 0.55
    benchmark: Optional[str] = "SPY"


@router.post("/backtests/run")
def run_backtest(request: BacktestRunRequest) -> Dict[str, Any]:
    """
    Run a backtest with specified parameters.
    This endpoint allows interactive backtesting from the UI with custom parameters.
    """
    try:
        from backend.services.backtest_service import backtest_service
        
        # Run backtest with the specified parameters
        result = backtest_service.run_custom_backtest(
            tickers=request.tickers or ["SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "META"],
            start_date=request.start_date,
            end_date=request.end_date,
            strategy=request.strategy,
            horizon=request.horizon,
            min_confidence=request.min_confidence,
            benchmark=request.benchmark
        )
        
        # Save the result for later retrieval
        job_id = f"backtest_{request.strategy}_{int(datetime.utcnow().timestamp())}"
        save_json(job_id, result, 
                  source=["interactive_backtest", "custom_params"])
        
        return ok({
            "result": result,
            "params": request.dict(),
            "job_id": job_id,
            "status": "completed",
            "generated_at": datetime.utcnow().isoformat(),
            "source": ["backtest_service", "interactive_calculation"]
        })


@router.get("/backtests")
def get_backtests_overview(
    strategy: Optional[str] = Query(None, description="Filter by strategy type (momentum, mean-reversion, etc.)"),
    horizon: Optional[str] = Query(None, description="Filter by forecast horizon (1d, 5d, 1mo, etc.)"),
    min_confidence: Optional[float] = Query(0.0, description="Minimum confidence threshold"),
    benchmark: Optional[str] = Query("SPY", description="Benchmark for comparison")
) -> Dict[str, Any]:
    """
    Get backtests overview with performance metrics and equity curves.
    Main endpoint for the backtests page showing CAGR, maxDD, win rate, equity curve.
    """
    try:
        # Try to load existing backtest results
        backtests_data = load_json("backtests")
        
        if not backtests_data:
            # Return empty structure but never fail
            return ok({
                "results": {
                    "cagr": 0.0,
                    "max_drawdown": 0.0,
                    "win_rate": 0.0,
                    "total_return": 0.0,
                    "sharpe_ratio": 0.0,
                    "volatility": 0.0,
                    "profit_factor": 1.0,
                    "total_trades": 0,
                    "avg_return": 0.0,
                    "best_trade": 0.0,
                    "worst_trade": 0.0,
                    "avg_win": 0.0,
                    "avg_loss": 0.0,
                    "win_loss_ratio": 0.0
                },
                "equity_curve": [],
                "performance_chart": [],  # For frontend charts
                "filtered_params": {
                    "strategy": strategy,
                    "horizon": horizon,
                    "min_confidence": min_confidence,
                    "benchmark": benchmark
                },
                "message": "No backtest data available - system calculating in background",
                "freshness": "unknown",
                "generated_at": datetime.utcnow().isoformat(),
                "source": ["fallback_empty"],
                "status": "waiting_for_data"
            })
        
        # Calculate comprehensive metrics from existing backtests
        comprehensive_results = calculate_comprehensive_metrics(backtests_data, strategy, horizon, min_confidence)
        
        return ok({
            "results": comprehensive_results["metrics"],
            "equity_curve": comprehensive_results["equity_curve"],
            "performance_chart": comprehensive_results["performance_chart"],
            "filtered_params": {
                "strategy": strategy,
                "horizon": horizon,
                "min_confidence": min_confidence,
                "benchmark": benchmark
            },
            "freshness": backtests_data.get("freshness", "unknown"),
            "generated_at": datetime.utcnow().isoformat(),
            "source": backtests_data.get("source", ["backtests_job"]),
            "status": "active"
        })
        
    except Exception as e:
        return ok({
            "results": {
                "cagr": 0.0,
                "max_drawdown": 0.0,
                "win_rate": 0.0,
                "total_return": 0.0,
                "sharpe_ratio": 0.0,
                "volatility": 0.0,
                "profit_factor": 1.0,
                "total_trades": 0,
                "avg_return": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "win_loss_ratio": 0.0
            },
            "equity_curve": [],
            "performance_chart": [],
            "error": str(e),
            "message": "Error calculating backtest metrics",
            "generated_at": datetime.utcnow().isoformat(),
            "source": ["fallback_error"]
        })


def calculate_comprehensive_metrics(backtests_data: Dict, strategy: Optional[str], horizon: Optional[str], min_confidence: float) -> Dict:
    """
    Calculate comprehensive backtest metrics for frontend consumption
    """
    # Extract the results from the backtests data
    results = backtests_data.get("results", {})
    
    # Initialize default values with proper keys
    metrics = {
        "cagr": results.get("cagr", 0.0),
        "max_drawdown": abs(results.get("max_drawdown", 0.0)),  # Ensure positive value for drawdown
        "win_rate": results.get("win_rate", 0.0),
        "total_return": results.get("total_return", 0.0),
        "sharpe_ratio": results.get("sharpe_ratio", 0.0),
        "volatility": results.get("volatility", 0.0),
        "profit_factor": results.get("profit_factor", 1.0),
        "total_trades": results.get("total_trades", 0),
        "avg_return": results.get("avg_return", 0.0),
        "best_trade": results.get("best_trade", 0.0),
        "worst_trade": results.get("worst_trade", 0.0),
        "avg_win": results.get("avg_win", 0.0),
        "avg_loss": results.get("avg_loss", 0.0),
        "win_loss_ratio": results.get("win_loss_ratio", 0.0)
    }
    
    # If we don't have detailed metrics from stored data, calculate basic ones from whatever data is available
    if metrics["cagr"] == 0.0 and "rows" in results:  # Changed from "cagr" to "cagr"
        # Calculate metrics from raw backtest results if they exist
        rows = results.get("rows", [])
        if rows and isinstance(rows, list):
            # Calculate basic metrics from the rows
            successful_trades = [r for r in rows if r.get("outcome") == "win" or r.get("return", 0) > 0]
            losing_trades = [r for r in rows if r.get("outcome") == "loss" or r.get("return", 0) < 0]
            
            if len(rows) > 0:
                metrics["win_rate"] = len(successful_trades) / len(rows)
                metrics["total_trades"] = len(rows)
                
                # Calculate other metrics from the data
                returns = [r.get("return", 0) for r in rows if "return" in r]
                if returns:
                    metrics["avg_return"] = sum(returns) / len(returns)
                    metrics["best_trade"] = max(returns) if returns else 0.0
                    metrics["worst_trade"] = min(returns) if returns else 0.0
                    
                    # Calculate volatility (std dev)
                    avg_ret = metrics["avg_return"]
                    variance = sum((r - avg_ret) ** 2 for r in returns) / len(returns) if returns else 0
                    metrics["volatility"] = variance ** 0.5 if variance > 0 else 0.0
                    
                    # Calculate win/loss ratios
                    wins = [r for r in returns if r > 0]
                    losses = [r for r in returns if r < 0]
                    if len(losses) != 0:
                        metrics["avg_win"] = sum(wins) / len(wins) if wins else 0.0
                        metrics["avg_loss"] = sum(losses) / len(losses) if losses else 0.0
                        metrics["win_loss_ratio"] = abs(metrics["avg_win"] / metrics["avg_loss"]) if abs(metrics["avg_loss"]) != 0 else float('inf')
    
    # Create simple equity curve based on the returns if not available
    equity_curve = []
    if "equity_history" in backtests_data:  # Changed from results to backtests_data
        equity_curve_data = backtests_data["equity_history"]
        if isinstance(equity_curve_data, list):
            equity_curve = equity_curve_data
        elif isinstance(equity_curve_data, dict) and "rows" in equity_curve_data:
            # If it's a structured response, extract the rows
            equity_curve = equity_curve_data["rows"]
    elif "trades" in results:
        # Generate equity curve from trades if available
        trades = results["trades"] if isinstance(results.get("trades"), list) else []
        # Generate simple equity curve from trade returns
        if trades:
            equity_curve = [{"date": t.get("date", ""), "value": t.get("equity", 1.0)} for t in trades if "date" in t and "equity" in t]
    elif "history" in results:
        # Alternative structure for equity history
        history = results["history"] if isinstance(results.get("history"), list) else []
        if history:
            # Convert history to equity curve format expected by frontend
            equity_curve = []
            cumulative_value = 1.0  # Start with $1 (100%)
            for record in history:
                if "return" in record or "pnl" in record or "change" in record:
                    # Calculate cumulative value based on returns
                    ret = record.get("return", record.get("pnl", record.get("change", 0)))
                    cumulative_value *= (1 + ret)
                    equity_curve.append({
                        "date": record.get("date", record.get("timestamp", record.get("time", ""))),
                        "value": cumulative_value
                    })
    
    # Performance chart data (for frontend charts)
    performance_chart = [
        {"metric": "CAGR", "value": metrics["cagr"] * 100, "unit": "%"},
        {"metric": "Max DD", "value": abs(metrics["max_drawdown"]) * 100, "unit": "%"},
        {"metric": "Win Rate", "value": metrics["win_rate"] * 100, "unit": "%"},
        {"metric": "Sharpe", "value": metrics["sharpe_ratio"], "unit": ""},
        {"metric": "Profit Factor", "value": metrics["profit_factor"], "unit": ""}
    ]
    
    return {
        "metrics": metrics,
        "equity_curve": equity_curve,
        "performance_chart": performance_chart
    }


# Endpoint to check backtest status (for async jobs)
@router.get("/backtests/status/{job_id}")
def get_backtest_status(job_id: str) -> Dict[str, Any]:
    """
    Get status of a backtest job.
    """
    try:
        # Try to load the results for the specific job
        job_result = load_json(f"backtest_{job_id}")
        
        if job_result:
            return ok({
                "job_id": job_id,
                "status": "completed",
                "result": job_result,
                "completed_at": datetime.utcnow().isoformat()
            })
        else:
            # Check if it's running or queued
            # For now, return a default response indicating status unknown
            return ok({
                "job_id": job_id,
                "status": "unknown",
                "message": f"Backtest job {job_id} not found or still running",
                "checked_at": datetime.utcnow().isoformat()
            })
            
    except Exception as e:
        return err(500, f"Error checking backtest status: {str(e)}")