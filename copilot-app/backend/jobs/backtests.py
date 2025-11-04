"""
Backtests job module for calculating model performance based on forecasts.

This module implements cache-first with invalidation based on forecast changes.
"""
from storage.io import load_json, save_json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def compute_backtests():
    """
    Compute backtests by comparing forecast data with actual market results.
    
    This function should:
    1. Load forecast data
    2. Compare with actual market results for the same period
    3. Calculate performance metrics (hit_rate, avg_er, n_trades, etc.)
    """
    try:
        # Load forecast data to compare against market results
        forecasts_data = load_json("forecasts")
        
        if not forecasts_data or not forecasts_data.get("payload"):
            logger.warning("No forecasts data available for backtesting")
            return {
                "results": [],
                "since": None,
                "until": None,
                "hit_rate": 0.0,
                "avg_er": 0.0,
                "n_trades": 0,
                "generated_at": datetime.utcnow().isoformat()
            }
        
        # For now, create a simple mock implementation
        # In a real implementation, this would compare forecast directions with actual price movements
        forecast_rows = forecasts_data["payload"].get("rows", [])
        
        # Perform backtesting calculations
        results = []
        correct_predictions = 0
        total_predictions = 0
        total_error = 0
        
        for forecast in forecast_rows:
            # Mock backtesting logic - in real world, we'd compare with actual market data
            symbol = forecast.get("ticker", forecast.get("symbol", "N/A"))
            horizon = forecast.get("horizon", "N/A")
            expected_dir = forecast.get("direction", "unknown")
            confidence = forecast.get("confidence", 0)
            
            # Mock market result (in real implementation, this would come from historical data)
            # For now, just assume 50% accuracy as a placeholder
            import random
            actual_dir = random.choice(["up", "down"])
            
            if expected_dir != "unknown" and expected_dir == actual_dir:
                correct_predictions += 1
                total_error += abs(forecast.get("expected_return", 0))
            
            total_predictions += 1
            
            result = {
                "symbol": symbol,
                "horizon": horizon,
                "forecast_direction": expected_dir,
                "actual_direction": actual_dir,
                "confidence": confidence,
                "correct": expected_dir != "unknown" and expected_dir == actual_dir,
                "forecast_return": forecast.get("expected_return", 0),
                "actual_return": round(random.uniform(-0.05, 0.05), 4)  # Mock actual return
            }
            results.append(result)
        
        # Calculate metrics
        hit_rate = correct_predictions / total_predictions if total_predictions > 0 else 0
        avg_er = total_error / total_predictions if total_predictions > 0 else 0
        
        backtest_result = {
            "results": results,
            "since": forecasts_data.get("last_update"),
            "until": datetime.utcnow().isoformat(),
            "hit_rate": hit_rate,
            "avg_er": avg_er,
            "n_trades": total_predictions,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Backtests computed: {total_predictions} predictions, hit_rate: {hit_rate:.2%}")
        return backtest_result
        
    except Exception as e:
        logger.error(f"Error computing backtests: {str(e)}")
        # Return empty results in case of error
        return {
            "results": [],
            "since": None,
            "until": None,
            "hit_rate": 0.0,
            "avg_er": 0.0,
            "n_trades": 0,
            "generated_at": datetime.utcnow().isoformat(),
            "error": str(e)
        }

def ensure_backtests_up_to_date():
    """
    Check if backtests need to be recalculated based on forecast updates.
    
    Returns backtests data, recalculating if forecasts have been updated.
    """
    try:
        # Load existing backtests
        bt = load_json("backtests")
        
        # Load current forecasts to check if they're newer
        fc = load_json("forecasts")
        fc_ts = fc.get("last_update") if fc else None
        
        # Check if recalculation is needed
        need_calc = False
        if not bt:
            logger.info("No existing backtests found, need to calculate")
            need_calc = True
        elif fc_ts and bt.get("depends_on_forecasts") != str(fc_ts):
            logger.info(f"Forecasts updated ({fc_ts}) compared to backtests ({bt.get('depends_on_forecasts')}), recalculating")
            need_calc = True
        else:
            logger.info("Backtests are up to date")
        
        if need_calc:
            logger.info("Starting backtests recalculation...")
            data = compute_backtests()
            data["depends_on_forecasts"] = str(fc_ts) if fc_ts else None
            save_json("backtests", data, source=["job:backtests"])
            logger.info("Backtests calculation completed and saved")
        
        # Return the latest backtests (either fresh or from cache)
        result = load_json("backtests")
        if result:
            return result
        else:
            # Return empty structure if no backtests available
            return {
                "payload": {
                    "results": [],
                    "since": None,
                    "until": None,
                    "hit_rate": 0.0,
                    "avg_er": 0.0,
                    "n_trades": 0,
                    "generated_at": datetime.utcnow().isoformat()
                },
                "last_update": None,
                "source": ["job:backtests"],
                "version": 1
            }
    except Exception as e:
        logger.error(f"Error in ensure_backtests_up_to_date: {str(e)}")
        # If there's an error, try to return any existing backtests or empty data
        bt = load_json("backtests")
        if bt:
            return bt
        else:
            return {
                "payload": {
                    "results": [],
                    "since": None,
                    "until": None,
                    "hit_rate": 0.0,
                    "avg_er": 0.0,
                    "n_trades": 0,
                    "generated_at": datetime.utcnow().isoformat(),
                    "error": str(e)
                },
                "last_update": None,
                "source": ["job:backtests", "error_fallback"],
                "version": 1
            }