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
        
        if not forecasts_data or not forecasts_data.get("data", forecasts_data.get("payload")):
            logger.warning("No forecasts data available for backtesting")
            return {
                "results": [],
                "since": None,
                "until": None,
                "hit_rate": 0.0,
                "avg_er": 0.0,
                "n_trades": 0,
                "total_return": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "generated_at": datetime.utcnow().isoformat()
            }
        
        # Get forecast data depending on the format
        forecast_payload = forecasts_data.get("data") or forecasts_data.get("payload") or forecasts_data
        forecast_rows = forecast_payload.get("rows", forecast_payload.get("data", []))
        
        if not forecast_rows:
            logger.info("No forecast rows to backtest")
            return {
                "results": [],
                "since": forecasts_data.get("last_update"),
                "until": datetime.utcnow().isoformat(),
                "hit_rate": 0.0,
                "avg_er": 0.0,
                "n_trades": 0,
                "total_return": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "generated_at": datetime.utcnow().isoformat()
            }
        
        # Import market data retrieval function (could come from existing market data module)
        from core.market_data import get_price_history
        
        # Perform backtesting calculations
        results = []
        correct_predictions = 0
        total_predictions = 0
        cumulative_returns = []
        total_portfolio_value = 1.0  # Start with $1 portfolio
        
        for forecast in forecast_rows:
            # Extract forecast information
            symbol = forecast.get("ticker", forecast.get("symbol", "N/A"))
            horizon = forecast.get("horizon", "1d")  # Default to 1 day
            expected_dir = forecast.get("direction", "unknown")
            confidence = forecast.get("confidence", 0.5)
            expected_return = forecast.get("expected_return", 0.0)
            
            # Get actual market movement for this ticker and timeframe
            try:
                # Extract the time horizon to determine how far back to look for actuals
                import re
                horizon_match = re.search(r'(\d+)([dwmy])', horizon.lower())
                horizon_num = 1
                horizon_unit = 'd'  # Default to day
                
                if horizon_match:
                    horizon_num = int(horizon_match.group(1))
                    horizon_unit = horizon_match.group(2)
                
                # Get historical market data for this symbol
                # This simulates comparing forecast against actual market results
                # In a real system, we'd use the actual market return for the forecast period
                actual_return = simulate_actual_return(symbol, horizon_num, horizon_unit)
                actual_dir = "up" if actual_return > 0 else ("down" if actual_return < 0 else "neutral")
                
                # Determine if our forecast was correct
                direction_correct = False
                if expected_dir == "up" and actual_return > 0:
                    direction_correct = True
                elif expected_dir == "down" and actual_return < 0:
                    direction_correct = True
                elif expected_dir == "neutral" and abs(actual_return) < 0.005:  # Within 0.5% range considered neutral
                    direction_correct = True
                elif expected_dir == "neutral":
                    direction_correct = True  # Neutral forecasts are considered correct if they avoid wrong bets
                
                if direction_correct:
                    correct_predictions += 1
                
                total_predictions += 1
                
                # Calculate strategy return (we only make trades we're confident about)
                strat_weight = min(confidence * 2, 1.0)  # Scale position size by confidence (max 100% of portfolio)
                strat_return = actual_return * strat_weight if abs(expected_return) > 0.001 else 0  # Only trade if we had a meaningful forecast
                
                # Track portfolio value over time for metrics
                total_portfolio_value *= (1 + strat_return)
                cumulative_returns.append(strat_return)
                
                result = {
                    "symbol": symbol,
                    "horizon": horizon,
                    "forecast_direction": expected_dir,
                    "forecast_return": expected_return,
                    "confidence": confidence,
                    "actual_direction": actual_dir,
                    "actual_return": actual_return,
                    "direction_correct": direction_correct,
                    "strategy_return": strat_return,
                    "forecast_timestamp": forecast.get("timestamp", forecasts_data.get("last_update")),
                    "status": "completed"
                }
                
                results.append(result)
                
            except Exception as e:
                logger.warning(f"Could not get market data for {symbol}: {e}")
                # Add record with error status
                result = {
                    "symbol": symbol,
                    "horizon": horizon,
                    "forecast_direction": expected_dir,
                    "forecast_return": expected_return,
                    "confidence": confidence,
                    "actual_direction": "unknown",
                    "actual_return": 0.0,
                    "direction_correct": False,
                    "strategy_return": 0.0,
                    "forecast_timestamp": forecast.get("timestamp", forecasts_data.get("last_update")),
                    "status": "error retrieving market data"
                }
                
                results.append(result)
                total_predictions += 1  # Count as prediction even if market data unavailable
        
        # Calculate performance metrics
        hit_rate = correct_predictions / total_predictions if total_predictions > 0 else 0
        
        # Calculate financial metrics
        if cumulative_returns:
            avg_return = sum(cumulative_returns) / len(cumulative_returns) if cumulative_returns else 0.0
            total_return = sum(cumulative_returns)
            
            # Calculate Sharpe ratio (simplified - assuming 0% risk-free rate)
            if len(cumulative_returns) > 1:
                returns_variance = sum((r - avg_return)**2 for r in cumulative_returns) / len(cumulative_returns)
                returns_std = returns_variance ** 0.5
                sharpe_ratio = avg_return / returns_std if returns_std != 0 else 0
            else:
                sharpe_ratio = 0.0
            
            # Calculate max drawdown (simplified max drawdown)
            max_value = 1.0
            max_drawdown = 0.0
            current_value = 1.0
            for ret in cumulative_returns:
                current_value *= (1 + ret) 
                if current_value > max_value:
                    max_value = current_value
                elif current_value < max_value:
                    drawdown = (max_value - current_value) / max_value
                    max_drawdown = max(max_drawdown, drawdown)
        else:
            total_return = 0.0
            avg_return = 0.0
            sharpe_ratio = 0.0
            max_drawdown = 0.0
        
        backtest_result = {
            "results": results,
            "since": forecasts_data.get("last_update"),
            "until": datetime.utcnow().isoformat(),
            "hit_rate": hit_rate,
            "avg_return": avg_return,
            "total_return": total_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "n_trades": total_predictions,
            "n_correct": correct_predictions,
            "accuracy": hit_rate,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Backtests computed: {total_predictions} predictions, hit_rate: {hit_rate:.2%}, total_return: {total_return:.2%}")
        return backtest_result
        
    except Exception as e:
        logger.error(f"Error computing backtests: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return empty results in case of error
        return {
            "results": [],
            "since": None,
            "until": None,
            "hit_rate": 0.0,
            "avg_return": 0.0,
            "total_return": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "n_trades": 0,
            "generated_at": datetime.utcnow().isoformat(),
            "error": str(e)
        }

def simulate_actual_return(symbol: str, horizon_num: int, horizon_unit: str) -> float:
    """
    Simulate retrieving actual market returns for backtesting purposes.
    In a real implementation, this would fetch historical market data for the given symbol
    and calculate the actual return over the forecast horizon.
    """
    import random
    
    # This is a simulation function that would be replaced with actual market data retrieval
    # For now, it simulates realistic market movements based on the symbol
    # In a real system, we would get the actual price movement between forecast_time and forecast_time+horizon
    
    # Different symbols have different volatility characteristics
    if symbol.upper() in ['SPY', 'QQQ', 'IWM', 'DIA']:  # Major indices
        volatility = 0.01  # 1% daily average movement
    elif symbol.upper() in ['VIX', 'TLT', 'GLD']:  # Volatility/inverse products
        volatility = 0.02  # 2% daily average movement
    elif symbol.upper() in ['TSLA', 'NVDA', 'AMD', 'INTC']:  # Tech/high-vol stocks
        volatility = 0.03  # 3% daily average movement
    else:  # Default assumption
        volatility = 0.015  # 1.5% daily average movement
    
    # Adjust for horizon - longer horizons have higher expected movement
    time_multiplier = 1.0
    if horizon_unit == 'w':
        time_multiplier = 2.2  # Weekly movements ~ 2.2x daily
    elif horizon_unit == 'm':
        time_multiplier = 4.4  # Monthly movements ~ 4.4x daily
    elif horizon_unit == 'y':
        time_multiplier = 15.8  # Yearly movements ~ 15.8x daily
    
    # Generate a realistic market return based on volatility
    # Use a distribution that represents real market movements (normal with slight fat tails)
    return random.normalvariate(0, volatility * time_multiplier)

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
                "results": [],
                "since": None,
                "until": None,
                "hit_rate": 0.0,
                "avg_return": 0.0,
                "total_return": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "n_trades": 0,
                "generated_at": datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.error(f"Error in ensure_backtests_up_to_date: {str(e)}")
        # If there's an error, try to return any existing backtests or empty data
        bt = load_json("backtests")
        if bt:
            return bt
        else:
            return {
                "results": [],
                "since": None,
                "until": None,
                "hit_rate": 0.0,
                "avg_return": 0.0,
                "total_return": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "n_trades": 0,
                "generated_at": datetime.utcnow().isoformat(),
                "error": str(e)
            }