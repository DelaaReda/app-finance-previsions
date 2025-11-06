"""
Simplified Backtest Engine - Performance Tracking
Task: FC-P2-018 - ML Model Performance Tracking
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any
import statistics

class BacktestEngine:
    """
    Simplified engine for running backtests with performance metrics
    """
    
    def __init__(self):
        self.tracking_data = {
            "models": {},
            "predictions": [],
            "metrics_history": []
        }
    
    def calculate_performance_metrics(self, trades: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate comprehensive performance metrics for backtests
        """
        if not trades or len(trades) == 0:
            return self._get_default_metrics()
        
        # Extract key metrics from trades
        directions_correct = [t.get("direction_correct", False) for t in trades]
        trade_profits = [t.get("trade_profit", 0) for t in trades]
        trade_returns = [t.get("trade_return", 0) for t in trades]
        
        # Hit rate (accuracy of direction predictions)
        hits = sum(1 for dc in directions_correct if dc)
        hit_rate = hits / len(directions_correct) if directions_correct else 0.0
        
        # Win rate (percentage of profitable trades)
        wins = sum(1 for profit in trade_profits if profit > 0)
        win_rate = wins / len(trade_profits) if trade_profits else 0.0
        
        # Average win/loss
        winning_trades = [p for p in trade_profits if p > 0]
        losing_trades = [p for p in trade_profits if p <= 0]
        
        avg_win = sum(winning_trades) / len(winning_trades) if winning_trades else 0.0
        avg_loss = sum(losing_trades) / len(losing_trades) if losing_trades and len(losing_trades) > 0 else 0.0
        
        # Calculate Sharpe ratio (simplified)
        if trade_returns and len(trade_returns) > 1:
            mean_return = sum(trade_returns) / len(trade_returns)
            std_return = statistics.stdev(trade_returns) if len(trade_returns) > 1 else 1.0
            # Risk-free rate = 0.02, but we'll simplify for this calculation
            sharpe_ratio = mean_return / std_return if std_return != 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        # Calculate total return
        final_value = sum(trade_profits) + 100000  # Assuming starting capital
        initial_capital = 100000
        total_return_pct = ((final_value - initial_capital) / initial_capital) * 100 if initial_capital > 0 else 0.0
        
        # Calculate CAGR (simplified - assuming 1 year if we have enough trades)
        total_years = 1.0  # Simplified assumption
        cagr = ((final_value / initial_capital) ** (1 / total_years)) - 1 if initial_capital > 0 else 0.0
        
        # Max drawdown (simplified calculation)
        max_dd = 0.0
        if len(trade_profits) > 0:
            cumulative_profits = [trade_profits[0]]
            for i in range(1, len(trade_profits)):
                cumulative_profits.append(cumulative_profits[-1] + trade_profits[i])
            
            peak = cumulative_profits[0]
            for value in cumulative_profits:
                if value > peak:
                    peak = value
                if peak != 0:
                    drawdown = (peak - value) / peak
                    max_dd = max(max_dd, drawdown)
        
        # Volatility
        volatility = statistics.stdev(trade_returns) if trade_returns and len(trade_returns) > 1 else 0.0
        
        return {
            "hit_rate": round(hit_rate, 4),
            "win_rate": round(win_rate, 4),
            "cagr": round(cagr, 4),
            "max_drawdown": round(max_dd, 4),
            "sharpe_ratio": round(sharpe_ratio, 4),
            "total_return_pct": round(total_return_pct, 4),
            "avg_win": round(avg_win, 4),
            "avg_loss": round(avg_loss, 4),
            "volatility": round(volatility, 4),
            "total_trades": len(trades),
            "total_winning_trades": len(winning_trades),
            "total_losing_trades": len(losing_trades),
            "best_trade": round(max(trade_profits) if trade_profits else 0.0, 4),
            "worst_trade": round(min(trade_profits) if trade_profits else 0.0, 4),
            "final_portfolio_value": round(final_value, 2)
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
    
    def run_backtest(self, forecasts: List[Dict], prices_data: Dict[str, List[Dict]], params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run simplified backtest on forecast data against historical prices
        """
        if params is None:
            params = {}
        
        # Default parameters
        initial_capital = params.get("initial_capital", 100000)
        
        # Create dummy trades based on forecasts if we have them
        trades = []
        for forecast in forecasts:
            # Simple simulation - in real implementation would match forecast date with price data
            trade = {
                "ticker": forecast.get("ticker", "UNKNOWN"),
                "forecast_date": forecast.get("timestamp", datetime.utcnow().isoformat()),
                "forecast_direction": forecast.get("direction", "neutral"),
                "forecast_confidence": forecast.get("confidence", 0.5),
                "trade_profit": forecast.get("simulated_profit", 0.0),  # In a real scenario, would calculate from price movement
                "trade_return": forecast.get("simulated_return", 0.0),
                "direction_correct": forecast.get("direction_correct", False),
                "entry_price": forecast.get("entry_price", 100.0),
                "exit_price": forecast.get("exit_price", 100.0)
            }
            trades.append(trade)
        
        # Calculate performance metrics
        performance_metrics = self.calculate_performance_metrics(trades)
        
        # Prepare results
        results = {
            "trades": trades,
            "metrics": performance_metrics,
            "params": params,
            "start_date": params.get("start_date", (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")),
            "end_date": params.get("end_date", datetime.now().strftime("%Y-%m-%d")),
            "initial_capital": initial_capital,
            "final_capital": performance_metrics.get("final_portfolio_value", initial_capital),
            "total_trades": len(trades),
            "hit_rate": performance_metrics.get("hit_rate", 0.0),
            "cagr": performance_metrics.get("cagr", 0.0),
            "max_drawdown": performance_metrics.get("max_drawdown", 0.0),
            "sharpe_ratio": performance_metrics.get("sharpe_ratio", 0.0),
            "summary": {
                "total_return_pct": performance_metrics.get("total_return_pct", 0.0),
                "total_trades": performance_metrics.get("total_trades", 0),
                "winning_trades": performance_metrics.get("total_winning_trades", 0),
                "losing_trades": performance_metrics.get("total_losing_trades", 0),
                "best_trade": performance_metrics.get("best_trade", 0.0),
                "worst_trade": performance_metrics.get("worst_trade", 0.0),
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "generated_by": "backtest_engine_simplified",
            "version": "1.0.0",
            "status": "success"
        }
        
        return results


# Global instance
backtest_engine = BacktestEngine()

def run_backtest_analysis(forecasts: List[Dict], prices: Dict[str, List[Dict]], params: Dict[str, Any] = None):
    """
    Run backtest analysis with simplified approach
    """
    if params is None:
        params = {}
    
    return backtest_engine.run_backtest(forecasts, prices, params)