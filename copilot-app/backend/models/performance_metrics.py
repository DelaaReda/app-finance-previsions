"""
Performance Metrics Calculator
Task: FC-API-028 - Multi-Asset Performance Table
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import math
from statistics import mean, stdev
import sys
from pathlib import Path

# Add backend to path for imports
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

class PerformanceMetricsCalculator:
    """
    Calculate performance metrics for multi-assets with benchmark comparison
    """
    
    def __init__(self):
        self.cached_performance = {}
    
    def calculate_returns(self, prices: List[float], period: str = "total") -> List[float]:
        """
        Calculate returns for a series of prices
        
        Args:
            prices: List of prices over time
            period: Time period for calculation ("total", "daily", "weekly", "monthly", "yearly")
        
        Returns:
            List of returns for each period
        """
        if len(prices) < 2:
            return []
        
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] != 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)
            else:
                returns.append(0.0)  # Default return if previous price is zero
        
        return returns
    
    def calculate_periodic_returns(self, prices: List[float], interval: int = 1) -> List[float]:
        """
        Calculate periodic returns (e.g., monthly returns from daily prices)
        
        Args:
            prices: List of prices
            interval: Interval between periods (1 for daily, 21 for monthly, 252 for yearly)
        
        Returns:
            List of periodic returns
        """
        if len(prices) < interval + 1:
            return []
        
        returns = []
        for i in range(interval, len(prices)):
            start_price = prices[i - interval]
            end_price = prices[i]
            if start_price != 0:
                periodic_return = (end_price - start_price) / start_price
                returns.append(periodic_return)
            else:
                returns.append(0.0)
        
        return returns
    
    def calculate_annualized_return(self, returns: List[float], periods_per_year: int = 252) -> float:
        """
        Calculate annualized return from periodic returns
        
        Args:
            returns: List of periodic returns
            periods_per_year: Number of periods per year (252 for daily, 52 for weekly, 12 for monthly)
        
        Returns:
            Annualized return
        """
        if not returns:
            return 0.0
        
        cumulative_return = 1.0
        for ret in returns:
            cumulative_return *= (1 + ret)
        
        if len(returns) == 0:
            return 0.0
        
        # Annualize the return
        years = len(returns) / periods_per_year
        if years > 0:
            annualized_return = cumulative_return ** (1 / years) - 1
        else:
            annualized_return = mean(returns) * periods_per_year
        
        return annualized_return
    
    def calculate_volatility(self, returns: List[float], periods_per_year: int = 252, annualized: bool = True) -> float:
        """
        Calculate volatility (standard deviation) of returns
        
        Args:
            returns: List of periodic returns
            periods_per_year: Number of periods per year for annualization
            annualized: Whether to annualize the volatility
        
        Returns:
            Volatility measure
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        # Calculate standard deviation
        volatility = stdev(returns) if len(returns) > 1 else 0.0
        
        if annualized:
            # Annualize using square root of time scaling
            volatility *= math.sqrt(periods_per_year)
        
        return volatility
    
    def calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.02, periods_per_year: int = 252) -> float:
        """
        Calculate Sharpe ratio (excess return per unit of risk)
        
        Args:
            returns: List of periodic returns
            risk_free_rate: Risk-free rate (annualized)
            periods_per_year: Number of periods per year
        
        Returns:
            Sharpe ratio
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        # Adjust risk-free rate for the period
        period_risk_free_rate = risk_free_rate / periods_per_year
        excess_returns = [ret - period_risk_free_rate for ret in returns]
        
        excess_return = mean(excess_returns) * periods_per_year
        volatility = self.calculate_volatility(returns, periods_per_year, annualized=True)
        
        if volatility != 0:
            sharpe_ratio = excess_return / volatility
        else:
            return 0.0  # Avoid division by zero
        
        return sharpe_ratio
    
    def calculate_maximum_drawdown(self, prices: List[float]) -> float:
        """
        Calculate Maximum Drawdown (peak-to-trough decline)
        
        Args:
            prices: List of prices over time
        
        Returns:
            Maximum drawdown as a negative percentage
        """
        if len(prices) < 2:
            return 0.0
        
        max_price = prices[0]
        max_dd = 0.0
        
        for price in prices:
            if price > max_price:
                max_price = price
            
            if max_price != 0:
                dd = (price - max_price) / max_price
                if dd < max_dd:
                    max_dd = dd
        
        return max_dd
    
    def calculate_beta(self, asset_returns: List[float], benchmark_returns: List[float]) -> float:
        """
        Calculate Beta of an asset relative to a benchmark
        
        Args:
            asset_returns: List of asset returns
            benchmark_returns: List of benchmark returns
        
        Returns:
            Beta coefficient
        """
        if not asset_returns or not benchmark_returns or len(asset_returns) != len(benchmark_returns) or len(asset_returns) < 2:
            return 0.0
        
        n = len(asset_returns)
        
        # Calculate means
        asset_mean = mean(asset_returns)
        benchmark_mean = mean(benchmark_returns)
        
        # Calculate covariance and benchmark variance
        cov_asset_bench = sum((asset_returns[i] - asset_mean) * (benchmark_returns[i] - benchmark_mean) for i in range(n)) / (n - 1)
        var_benchmark = sum((benchmark_returns[i] - benchmark_mean) ** 2 for i in range(n)) / (n - 1)
        
        if var_benchmark == 0:
            return 0.0
        
        beta = cov_asset_bench / var_benchmark
        return float(beta)
    
    def calculate_alpha(self, asset_returns: List[float], benchmark_returns: List[float], risk_free_rate: float = 0.02) -> float:
        """
        Calculate Alpha (excess return over expected return based on Beta)
        
        Args:
            asset_returns: List of asset returns
            benchmark_returns: List of benchmark returns
            risk_free_rate: Risk-free rate
        
        Returns:
            Alpha coefficient
        """
        if not asset_returns or not benchmark_returns or len(asset_returns) != len(benchmark_returns):
            return 0.0
        
        # Calculate annualized returns
        asset_annual_return = self.calculate_annualized_return(asset_returns)
        benchmark_annual_return = self.calculate_annualized_return(benchmark_returns)
        
        # Calculate Beta
        beta = self.calculate_beta(asset_returns, benchmark_returns)
        
        # Calculate expected return based on CAPM
        expected_return = risk_free_rate + beta * (benchmark_annual_return - risk_free_rate)
        
        # Alpha is the difference between actual and expected return
        alpha = asset_annual_return - expected_return
        
        return alpha
    
    def calculate_performance_metrics(self, 
                                    prices: List[float], 
                                    benchmark_prices: Optional[List[float]] = None,
                                    risk_free_rate: float = 0.02) -> Dict[str, float]:
        """
        Calculate comprehensive performance metrics for an asset
        
        Args:
            prices: List of asset prices
            benchmark_prices: Optional list of benchmark prices for comparison
            risk_free_rate: Risk-free rate for calculations
        
        Returns:
            Dictionary of performance metrics
        """
        if not prices or len(prices) < 2:
            return self._get_empty_metrics()
        
        # Calculate returns
        daily_returns = self.calculate_returns(prices)
        annual_return = self.calculate_annualized_return(daily_returns)
        volatility = self.calculate_volatility(daily_returns)
        sharpe_ratio = self.calculate_sharpe_ratio(daily_returns, risk_free_rate)
        max_drawdown = self.calculate_maximum_drawdown(prices)
        
        # Initialize metrics dictionary
        metrics = {
            "annual_return": annual_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "total_return": (prices[-1] - prices[0]) / prices[0] if prices[0] != 0 else 0.0,
            "return_volatility_ratio": annual_return / volatility if volatility != 0 else 0.0,
            "win_rate": len([r for r in daily_returns if r > 0]) / len(daily_returns) if daily_returns else 0.0,
            "avg_positive_return": mean([r for r in daily_returns if r > 0]) if any(r > 0 for r in daily_returns) else 0.0,
            "avg_negative_return": mean([r for r in daily_returns if r < 0]) if any(r < 0 for r in daily_returns) else 0.0,
            "best_day_return": max(daily_returns) if daily_returns else 0.0,
            "worst_day_return": min(daily_returns) if daily_returns else 0.0,
            "days_tracked": len(prices),
            "calmar_ratio": annual_return / abs(max_drawdown) if abs(max_drawdown) > 0 else 0.0
        }
        
        # Add benchmark comparison metrics if benchmark prices provided
        if benchmark_prices and len(benchmark_prices) >= 2:
            benchmark_daily_returns = self.calculate_returns(benchmark_prices)
            
            metrics["beta"] = self.calculate_beta(daily_returns, benchmark_daily_returns)
            metrics["alpha"] = self.calculate_alpha(daily_returns, benchmark_daily_returns, risk_free_rate)
            
            # Calculate outperformance metrics
            benchmark_annual_return = self.calculate_annualized_return(benchmark_daily_returns)
            metrics["outperformance_vs_benchmark"] = annual_return - benchmark_annual_return
        else:
            metrics["beta"] = 0.0
            metrics["alpha"] = 0.0
            metrics["outperformance_vs_benchmark"] = 0.0
        
        # Add generated timestamp
        metrics["generated_at"] = datetime.utcnow().isoformat() + "Z"
        
        return metrics
    
    def calculate_multi_asset_performance(self, 
                                        asset_prices: Dict[str, List[float]], 
                                        benchmark_prices: Optional[List[float]] = None,
                                        risk_free_rate: float = 0.02) -> Dict[str, Any]:
        """
        Calculate performance table for multiple assets
        
        Args:
            asset_prices: Dictionary with asset ticker as key and price list as value
            benchmark_prices: Optional benchmark price series for comparison
            risk_free_rate: Risk-free rate for calculations
        
        Returns:
            Dictionary with performance table and metadata
        """
        performance_table = {}
        
        # Calculate metrics for each asset
        for ticker, prices in asset_prices.items():
            if prices and len(prices) >= 2:
                # Get benchmark prices for this asset if available (same length as asset prices)
                benchmark_subset = None
                if benchmark_prices and len(benchmark_prices) == len(prices):
                    benchmark_subset = benchmark_prices
                elif benchmark_prices:
                    # If lengths don't match, take a subset
                    if len(benchmark_prices) >= len(prices):
                        benchmark_subset = benchmark_prices[-len(prices):]
                    else:
                        # Extend benchmark with last value if needed
                        benchmark_subset = benchmark_prices + [benchmark_prices[-1]] * (len(prices) - len(benchmark_prices))
                
                # Calculate performance metrics for this asset
                metrics = self.calculate_performance_metrics(prices, benchmark_subset, risk_free_rate)
                performance_table[ticker] = metrics
            else:
                # If insufficient prices, return empty metrics
                performance_table[ticker] = self._get_empty_metrics()
        
        # Calculate summary statistics
        summary = {
            "assets_analyzed": list(performance_table.keys()),
            "total_assets": len(performance_table),
            "average_annual_return": mean([perf["annual_return"] for perf in performance_table.values()]) if performance_table else 0.0,
            "average_volatility": mean([perf["volatility"] for perf in performance_table.values()]) if performance_table else 0.0,
            "average_sharpe": mean([perf["sharpe_ratio"] for perf in performance_table.values()]) if performance_table else 0.0,
            "benchmark_used": True if benchmark_prices else False,
            "risk_free_rate_used": risk_free_rate
        }
        
        # Add generated timestamp
        summary["generated_at"] = datetime.utcnow().isoformat() + "Z"
        
        return {
            "performance_table": performance_table,
            "summary": summary,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source": ["performance_calculator", "multi_asset_analysis", "fc-api-028"]
        }
    
    def compare_assets_vs_benchmark(self, 
                                  asset_prices: Dict[str, List[float]], 
                                  benchmark_prices: List[float]) -> Dict[str, Any]:
        """
        Compare assets against benchmark and return performance differentials
        
        Args:
            asset_prices: Dictionary with asset ticker as key and price list as value
            benchmark_prices: Benchmark price series for comparison
        
        Returns:
            Dictionary with asset vs benchmark comparison
        """
        comparison = {}
        
        if not benchmark_prices or len(benchmark_prices) < 2:
            # Return empty comparison if no benchmark
            for ticker in asset_prices.keys():
                comparison[ticker] = {
                    "outperformance": 0.0,
                    "relative_sharpe": 0.0,
                    "relative_volatility": 0.0,
                    "tracking_error": 0.0,
                    "information_ratio": 0.0
                }
            return comparison
        
        # Calculate benchmark metrics
        benchmark_returns = self.calculate_returns(benchmark_prices)
        benchmark_annual_return = self.calculate_annualized_return(benchmark_returns)
        benchmark_volatility = self.calculate_volatility(benchmark_returns)
        
        for ticker, prices in asset_prices.items():
            if prices and len(prices) >= 2:
                # Align price lengths if necessary
                if len(prices) != len(benchmark_prices):
                    min_len = min(len(prices), len(benchmark_prices))
                    asset_subset = prices[-min_len:]
                    bench_subset = benchmark_prices[-min_len:]
                else:
                    asset_subset = prices
                    bench_subset = benchmark_prices
                
                # Calculate asset metrics
                asset_returns = self.calculate_returns(asset_subset)
                asset_annual_return = self.calculate_annualized_return(asset_returns)
                
                # Calculate differential metrics
                outperformance = asset_annual_return - benchmark_annual_return
                relative_sharpe = self.calculate_sharpe_ratio(asset_returns) - self.calculate_sharpe_ratio(benchmark_returns)
                
                asset_volatility = self.calculate_volatility(asset_returns)
                relative_volatility = asset_volatility - benchmark_volatility
                
                # Calculate tracking error (volatility of outperformance)
                if len(asset_returns) == len(benchmark_returns):
                    active_returns = [ar - br for ar, br in zip(asset_returns, benchmark_returns)]
                    tracking_error = self.calculate_volatility(active_returns)
                    
                    # Information ratio
                    info_ratio = outperformance / tracking_error if tracking_error != 0 else 0.0
                else:
                    tracking_error = 0.0
                    info_ratio = 0.0
                
                comparison[ticker] = {
                    "outperformance": outperformance,
                    "relative_sharpe": relative_sharpe,
                    "relative_volatility": relative_volatility,
                    "tracking_error": tracking_error,
                    "information_ratio": info_ratio
                }
            else:
                # Default values if insufficient data
                comparison[ticker] = {
                    "outperformance": 0.0,
                    "relative_sharpe": 0.0,
                    "relative_volatility": 0.0,
                    "tracking_error": 0.0,
                    "information_ratio": 0.0
                }
        
        return comparison
    
    def _get_empty_metrics(self) -> Dict[str, float]:
        """
        Return empty metrics structure to maintain never-empty contract
        """
        return {
            "annual_return": 0.0,
            "volatility": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "total_return": 0.0,
            "return_volatility_ratio": 0.0,
            "win_rate": 0.0,
            "avg_positive_return": 0.0,
            "avg_negative_return": 0.0,
            "best_day_return": 0.0,
            "worst_day_return": 0.0,
            "days_tracked": 0,
            "calmar_ratio": 0.0,
            "beta": 0.0,
            "alpha": 0.0,
            "outperformance_vs_benchmark": 0.0,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "error": "Insufficient price data for performance calculation",
            "message": "Returning empty metrics to maintain never-empty contract"
        }


# Global instance
performance_calculator = PerformanceMetricsCalculator()


def calculate_asset_performance(prices: List[float], 
                              benchmark_prices: Optional[List[float]] = None,
                              risk_free_rate: float = 0.02) -> Dict[str, float]:
    """
    Convenience function to calculate performance metrics for a single asset
    """
    return performance_calculator.calculate_performance_metrics(prices, benchmark_prices, risk_free_rate)


def calculate_multi_asset_performance(asset_prices: Dict[str, List[float]], 
                                   benchmark_prices: Optional[List[float]] = None,
                                   risk_free_rate: float = 0.02) -> Dict[str, Any]:
    """
    Convenience function to calculate performance table for multiple assets
    """
    return performance_calculator.calculate_multi_asset_performance(asset_prices, benchmark_prices, risk_free_rate)


def compare_assets_vs_benchmark(asset_prices: Dict[str, List[float]], 
                              benchmark_prices: List[float]) -> Dict[str, Any]:
    """
    Convenience function to compare assets against benchmark
    """
    return performance_calculator.compare_assets_vs_benchmark(asset_prices, benchmark_prices)