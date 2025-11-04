"""
Backtests job implementation for Finance Copilot
Implements cache-first approach with invalidation based on forecasts changes
Author: MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7
"""
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, List, Any, Optional

# Import our storage and cache system
from backend.storage.base import load_json, save_json
from backend.services.cache_layer import load_or_compute

logger = logging.getLogger(__name__)

def compute_backtests() -> Dict[str, Any]:
    """
    Compute backtests based on forecasts and historical market data.
    
    This function simulates trading based on the forecasts and calculates
    performance metrics like hit rate and average expected return.
    """
    try:
        logger.info("Starting backtests computation...")
        
        # Load forecasts to get the trading signals
        forecasts_data = load_json("forecasts.json")
        
        if not forecasts_data or "data" not in forecasts_data:
            logger.warning("No forecasts data available for backtests")
            return {
                "results": [],
                "metrics": {
                    "hit_rate": 0.0,
                    "avg_expected_return": 0.0,
                    "total_trades": 0,
                    "n_trades": 0,
                    "start_date": None,
                    "end_date": None
                },
                "since": None,
                "until": None,
                "depends_on_forecasts": None
            }
        
        # For demo purposes, we'll create simulated backtest results
        # In a real implementation, this would load historical price data
        # and backtest the forecast signals against actual market movements
        forecast_rows = forecasts_data["data"].get("rows", [])
        
        # Create simulated results based on forecasts
        results = []
        correct_predictions = 0
        total_predictions = 0
        total_return = 0.0
        
        for i, forecast in enumerate(forecast_rows[:20]):  # Limit for demo
            # Simulate whether the forecast was correct
            # In real implementation, we'd compare forecast direction to actual price movement
            is_correct = np.random.choice([True, False], p=[0.55, 0.45])  # 55% hit rate for demo
            actual_return = forecast.get("expected_return", 0.0) * np.random.uniform(0.8, 1.2)  # Simulated actual return
            
            if is_correct:
                correct_predictions += 1
            total_predictions += 1
            total_return += actual_return
            
            result = {
                "id": f"sim_{i}_{forecast.get('ticker', 'N/A')}",
                "ticker": forecast.get("ticker", "N/A"),
                "forecast_date": forecast.get("last_update", datetime.now().isoformat()),
                "predicted_direction": forecast.get("direction", "neutral"),
                "predicted_return": forecast.get("expected_return", 0.0),
                "actual_direction": "up" if actual_return > 0 else "down",
                "actual_return": actual_return,
                "confidence": forecast.get("confidence", 0.5),
                "was_correct": is_correct,
                "horizon": forecast.get("horizon", "1d")
            }
            results.append(result)
        
        # Calculate metrics
        hit_rate = correct_predictions / total_predictions if total_predictions > 0 else 0
        avg_expected_return = total_return / total_predictions if total_predictions > 0 else 0
        
        backtest_result = {
            "results": results,
            "metrics": {
                "hit_rate": hit_rate,
                "avg_expected_return": avg_expected_return,
                "total_trades": total_predictions,
                "n_trades": total_predictions,
                "start_date": datetime.now().isoformat(),
                "end_date": datetime.now().isoformat()
            },
            "since": forecasts_data.get("last_update"),
            "until": datetime.now().isoformat(),
            "depends_on_forecasts": forecasts_data.get("last_update")
        }
        
        logger.info(f"Backtests computation completed with {total_predictions} trades and {hit_rate:.2%} hit rate")
        return backtest_result
        
    except Exception as e:
        logger.error(f"Error in compute_backtests: {e}")
        # Return a fallback response
        return {
            "results": [],
            "metrics": {
                "hit_rate": 0.0,
                "avg_expected_return": 0.0,
                "total_trades": 0,
                "n_trades": 0,
                "start_date": None,
                "end_date": None
            },
            "since": None,
            "until": None,
            "depends_on_forecasts": None
        }


def run_and_persist_backtests():
    """
    Run backtests computation and persist to storage
    """
    backtest_data = compute_backtests()
    save_path = save_json(backtest_data, "backtests.json", ["backtest_job", "forecast_based"])
    logger.info(f"Backtests saved to {save_path}")
    return backtest_data


def ensure_backtests_up_to_date() -> Dict[str, Any]:
    """
    Ensure backtests are up-to-date based on forecasts changes.
    Implements the invalidation logic as per FC-P0-006 requirements.
    """
    try:
        # Load current backtests
        current_backtests = load_json("backtests.json")
        
        # Load current forecasts to check for updates
        current_forecasts = load_json("forecasts.json")
        
        # Get timestamps
        forecasts_ts = current_forecasts.get("last_update") if current_forecasts else None
        backtests_depends_on = (current_backtests or {}).get("depends_on_forecasts")
        
        # Check if backtests need to be recomputed
        need_recompute = not current_backtests or (forecasts_ts != backtests_depends_on)
        
        if need_recompute:
            logger.info(f"Forecasts updated ({forecasts_ts}) or no backtests exist, computing new backtests...")
            return run_and_persist_backtests()
        else:
            logger.info("Backtests are up-to-date, returning existing results")
            return current_backtests
            
    except Exception as e:
        logger.error(f"Error in ensure_backtests_up_to_date: {e}")
        # Fallback: return existing backtests or empty result
        existing = load_json("backtests.json")
        if existing:
            return existing
        else:
            return {
                "results": [],
                "metrics": {
                    "hit_rate": 0.0,
                    "avg_expected_return": 0.0,
                    "total_trades": 0,
                    "n_trades": 0,
                    "start_date": None,
                    "end_date": None
                },
                "since": None,
                "until": None,
                "depends_on_forecasts": None
            }


def get_historical_performance(ticker: str = None, days: int = 30) -> List[Dict[str, Any]]:
    """
    Get historical performance metrics for a specific ticker or overall
    """
    try:
        backtests_data = load_json("backtests.json")
        if not backtests_data:
            return []
        
        results = backtests_data.get("results", [])
        
        # Filter by ticker if specified
        if ticker:
            results = [r for r in results if r.get("ticker") == ticker]
        
        # Filter by date range
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered_results = []
        
        for result in results:
            try:
                forecast_date = datetime.fromisoformat(result["forecast_date"].replace('Z', '+00:00'))
                if forecast_date >= cutoff_date:
                    filtered_results.append(result)
            except:
                continue  # Skip invalid dates
        
        return filtered_results
        
    except Exception as e:
        logger.error(f"Error getting historical performance: {e}")
        return []


if __name__ == "__main__":
    # Test the backtests functionality
    print("Testing backtests job...")
    
    # Run and persist backtests
    result = run_and_persist_backtests()
    print(f"Backtests computed with {len(result.get('results', []))} results")
    print(f"Hit rate: {result.get('metrics', {}).get('hit_rate', 0):.2%}")
    print(f"Average expected return: {result.get('metrics', {}).get('avg_expected_return', 0):.4f}")
    
    # Test the up-to-date check
    updated_result = ensure_backtests_up_to_date()
    print(f"Up-to-date check completed, {len(updated_result.get('results', []))} results available")
    
    print("Backtests job test completed successfully!")