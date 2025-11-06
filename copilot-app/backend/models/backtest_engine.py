"""
Real Backtests with Performance Metrics
Task: FC-BACKTESTS-REAL 
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import statistics
from pathlib import Path
import json

class BacktestEngine:
    """
    Engine for running real backtests with performance metrics
    """
    
    def __init__(self):
        self.performance_metrics = {}
    
    def run_backtest(self, forecasts: List[Dict], prices_data: Dict[str, List[Dict]], params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run backtest on forecast data against historical prices
        
        Args:
            forecasts: List of forecasts with ticker, direction, confidence, timestamp
            prices_data: Historical price data {ticker: [{"date": "...", "close": value}, ...]}
            params: Backtest parameters {horizon, start_date, end_date, initial_capital, etc.}
        
        Returns:
            Backtest results with performance metrics
        """
        if params is None:
            params = {}
        
        # Default parameters
        horizon = params.get("horizon", "1d")  # 1 day, 1 week, 1 month
        start_date = params.get("start_date", (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"))
        end_date = params.get("end_date", datetime.now().strftime("%Y-%m-%d"))
        initial_capital = params.get("initial_capital", 100000)
        rebalance_frequency = params.get("rebalance_frequency", "daily")  # daily, weekly, monthly
        
        # Initialize portfolio
        portfolio_value = initial_capital
        portfolio_history = []
        trades = []
        
        trades = []
        portfolio_value = initial_capital
        portfolio_history = []
        
        # Process forecasts and match with price data
        for forecast in forecasts:
            ticker = forecast.get("ticker", "").upper()
            direction = forecast.get("direction", "").lower()
            confidence = forecast.get("confidence", 0.5)
            forecast_date = forecast.get("timestamp") or forecast.get("forecast_date")
            horizon = forecast.get("horizon", "1d")  # Default to 1 day horizon
            
            if not ticker or not direction or not forecast_date:
                continue
            
            # Get historical price data for the ticker
            ticker_prices = prices_data.get(ticker, [])
            if not ticker_prices:
                continue
            
            # Find the forecast date in price data
            forecast_price_entry = None
            for price_entry in ticker_prices:
                entry_date_str = price_entry.get("date", "")
                if entry_date_str.startswith(forecast_date.split("T")[0]) if "T" in forecast_date else entry_date_str == forecast_date:  # Match date part
                    forecast_price_entry = price_entry
                    break
            
            if not forecast_price_entry:
                continue
            
            # Find the future price based on horizon
            future_price_entry = self._find_future_price(ticker_prices, forecast_date, horizon)
            if not future_price_entry:
                continue
            
            # Execute trade based on forecast
            forecast_price = forecast_price_entry.get("close")
            future_price = future_price_entry.get("close")
            
            if not forecast_price or not future_price:
                continue
            
            # Calculate return based on forecast direction vs actual movement
            actual_direction = "up" if future_price > forecast_price else "down"
            direction_correct = (direction == "up" and actual_direction == "up") or (direction == "down" and actual_direction == "down")
            
            # Calculate trade return (simplified: equal weight allocation)
            trade_size = portfolio_value * confidence * 0.1  # Only use 10% of portfolio based on confidence
            trade_return = (future_price - forecast_price) / forecast_price if forecast_price != 0 else 0.0
            if direction == "down":  # If forecast was down, we short (inverse return)
                trade_return = -trade_return
            
            trade_profit = trade_size * trade_return
            portfolio_value += trade_profit
            
            # Record trade
            trade = {
                "ticker": ticker,
                "forecast_date": forecast_date,
                "forecast_direction": direction,
                "forecast_confidence": confidence,
                "entry_price": forecast_price,
                "exit_price": future_price,
                "exit_date": future_price.get("date"),
                "direction_correct": direction_correct,
                "trade_return": trade_return,
                "trade_profit": trade_profit,
                "portfolio_value": portfolio_value,
                "trade_size": trade_size,
                "horizon_actual": horizon
            }
            trades.append(trade)
            
            # Record portfolio history
            portfolio_history.append({
                "date": future_price.get("date"),
                "value": portfolio_value,
                "trade_count": len(trades)
            })
        
        # Calculate performance metrics
        if len(trades) > 0:
            performance_metrics = self._calculate_performance_metrics(trades, portfolio_history, initial_capital)
        else:
            performance_metrics = self._get_default_metrics()
        
        # Prepare results
        results = {
            "trades": trades,
            "portfolio_history": portfolio_history,
            "metrics": performance_metrics,
            "params": params,
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": initial_capital,
            "final_capital": portfolio_value,
            "total_trades": len(trades),
            "hit_rate": performance_metrics.get("hit_rate", 0),
            "cagr": performance_metrics.get("cagr", 0),
            "max_drawdown": performance_metrics.get("max_drawdown", 0),
            "sharpe_ratio": performance_metrics.get("sharpe_ratio", 0),
            "equity_curve": self._generate_equity_curve(portfolio_history),
            "summary": {
                "total_return_pct": ((portfolio_value - initial_capital) / initial_capital) * 100 if initial_capital > 0 else 0,
                "total_trades": len(trades),
                "winning_trades": sum(1 for t in trades if t["trade_profit"] > 0),
                "losing_trades": sum(1 for t in trades if t["trade_profit"] <= 0),
                "best_trade": max([t["trade_profit"] for t in trades] + [0]),
                "worst_trade": min([t["trade_profit"] for t in trades] + [0]),
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "generated_by": "backtest_engine_v1",
            "version": "1.0.0"
        }
        
        return results
    
    def _find_future_price(self, price_data: List[Dict], start_date: str, horizon: str) -> Optional[Dict]:
        """
        Find the price at a future date based on the horizon from the start date
        """
        try:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00")) if "T" in start_date else datetime.fromisoformat(start_date)
        except ValueError:
            try:
                start_dt = datetime.strptime(start_date.split("T")[0], "%Y-%m-%d")
            except:
                return None  # Invalid date format
        
        # Define horizon periods
        horizon_days = {
            "1d": 1,
            "3d": 3,
            "1w": 7,
            "2w": 14,
            "1m": 30,
            "3m": 90,
            "6m": 180,
            "1y": 365
        }
        
        target_days = horizon_days.get(horizon, 7)  # Default to 1 week
        target_date = start_dt + timedelta(days=target_days)
        
        # Find price entry closest to target date
        for entry in price_data:
            entry_date_str = entry.get("date", "")
            try:
                entry_date = datetime.fromisoformat(entry_date_str.replace("Z", "+00:00")) if "T" in entry_date_str else datetime.strptime(entry_date_str.split("T")[0], "%Y-%m-%d")
                if entry_date >= target_date:  # First date after target
                    return entry
            except:
                continue  # Skip invalid dates
        
        return None
    
    def _calculate_performance_metrics(self, trades: List[Dict], portfolio_history: List[Dict], initial_capital: float) -> Dict[str, float]:
        """
        Calculate comprehensive performance metrics for backtests
        """
        if not trades:
            return self._get_default_metrics()
        
        # Calculate returns
        returns = [trade["trade_return"] for trade in trades]
        profits = [trade["trade_profit"] for trade in trades]
        
        # Hit rate (accuracy of forecast directions)
        hits = sum(1 for trade in trades if trade["direction_correct"])
        hit_rate = hits / len(trades) if len(trades) > 0 else 0.0
        
        # Calculate CAGR (Compound Annual Growth Rate)
        total_return = (portfolio_history[-1]["value"] / initial_capital) - 1 if len(portfolio_history) > 0 else 0
        total_years = 1  # Simplified - actual calculation would use date range
        
        cagr = (portfolio_history[-1]["value"] / initial_capital) ** (1/total_years) - 1 if len(portfolio_history) > 0 and total_years > 0 else 0.0
        
        # Calculate max drawdown
        if portfolio_history:
            peak = initial_capital
            max_dd = 0.0
            for entry in portfolio_history:
                current_value = entry["value"]
                if current_value > peak:
                    peak = current_value
                
                drawdown = (peak - current_value) / peak if peak > 0 else 0.0
                if drawdown > max_dd:
                    max_dd = drawdown
        else:
            max_dd = 0.0
        
        # Calculate Sharpe ratio (simplified with assumed risk free rate)
        risk_free_rate = 0.02  # 2% annual risk-free rate
        excess_returns = [r - (risk_free_rate/len(returns)) for r in returns] if returns else []
        
        mean_excess_return = sum(excess_returns) / len(excess_returns) if excess_returns else 0.0
        std_excess_return = statistics.stdev(excess_returns) if len(excess_returns) > 1 else 0.0
        sharpe_ratio = (mean_excess_return / std_excess_return) * np.sqrt(252) if std_excess_return != 0 else 0.0  # Annualized
        
        # Calculate other metrics
        win_rate = sum(1 for p in profits if p > 0) / len(profits) if profits else 0.0
        avg_win = sum(p for p in profits if p > 0) / sum(1 for p in profits if p > 0) if any(p > 0 for p in profits) else 0.0
        avg_loss = sum(p for p in profits if p <= 0) / sum(1 for p in profits if p <= 0) if any(p <= 0 for p in profits) else 0.0
        
        total_return_pct = ((portfolio_history[-1]["value"] / initial_capital) - 1) * 100 if portfolio_history and initial_capital > 0 else 0.0
        
        return {
            "hit_rate": round(hit_rate, 4),
            "win_rate": round(win_rate, 4),
            "cagr": round(cagr, 4),
            "max_drawdown": round(max_dd, 4),
            "sharpe_ratio": round(sharpe_ratio, 4),
            "total_return_pct": round(total_return_pct, 4),
            "avg_win": round(avg_win, 4),
            "avg_loss": round(avg_loss, 4),
            "volatility": round(statistics.stdev(returns) if returns and len(returns) > 1 else 0.0, 4),
            "total_trades": len(trades),
            "total_winning_trades": sum(1 for p in profits if p > 0),
            "total_losing_trades": sum(1 for p in profits if p <= 0),
            "best_trade": round(max(profits) if profits else 0.0, 4),
            "worst_trade": round(min(profits) if profits else 0.0, 4),
            "final_portfolio_value": round(portfolio_history[-1]["value"] if portfolio_history else initial_capital, 2)
        }
    
    def _get_default_metrics(self) -> Dict[str, float]:
        """
        Return default metrics when no trades are available
        """
        return {
            "hit_rate": 0.0,
            "win_rate": 0.0,
            "cagr": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "total_return_pct": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "volatility": 0.0,
            "total_trades": 0,
            "total_winning_trades": 0,
            "total_losing_trades": 0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
            "final_portfolio_value": 0.0
        }
    
    def _generate_equity_curve(self, portfolio_history: List[Dict]) -> List[Dict[str, Any]]:
        """
        Generate simplified equity curve data for charting
        """
        if not portfolio_history:
            return []
        
        # Return a simplified version with date and normalized value
        initial_value = portfolio_history[0]["value"] if portfolio_history else 100000
        return [{"date": entry["date"], "value": round((entry["value"] / initial_value - 1) * 100, 4)} for entry in portfolio_history]


# Global instance
backtest_engine = BacktestEngine()

def run_backtest_analysis(forecasts: List[Dict], prices: Dict[str, List[Dict]], params: Dict[str, Any] = None):
    """
    Run backtest analysis with real data
    """
    if params is None:
        params = {}
    
    return backtest_engine.run_backtest(forecasts, prices, params)