"""
Portfolio Performance Service - Calculate real portfolio metrics
Author: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
Task: API-PORTFOLIO-003 - Performance Analytics Phase 2
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field
import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Try to import yfinance, fallback gracefully if not available
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    logger.warning("yfinance not available - performance calculations will use mock data")
    YFINANCE_AVAILABLE = False


# ============================================================================
# Data Models
# ============================================================================

class PortfolioMetrics(BaseModel):
    """Portfolio performance metrics"""
    total_return: Optional[float] = Field(None, description="Total return (%)")
    annualized_return: Optional[float] = Field(None, description="Annualized return (%)")
    volatility: Optional[float] = Field(None, description="Annualized volatility (%)")
    sharpe_ratio: Optional[float] = Field(None, description="Sharpe ratio")
    max_drawdown: Optional[float] = Field(None, description="Maximum drawdown (%)")
    win_rate: Optional[float] = Field(None, description="Win rate (% positive days)")
    best_day: Optional[float] = Field(None, description="Best daily return (%)")
    worst_day: Optional[float] = Field(None, description="Worst daily return (%)")


class BenchmarkComparison(BaseModel):
    """Benchmark comparison metrics"""
    benchmark_ticker: str
    portfolio_return: Optional[float] = None
    benchmark_return: Optional[float] = None
    outperformance: Optional[float] = None
    correlation: Optional[float] = None
    beta: Optional[float] = None
    alpha: Optional[float] = None


class PerformanceTimeSeries(BaseModel):
    """Time series data for performance visualization"""
    dates: List[str] = Field(default_factory=list)
    equity_curve: List[float] = Field(default_factory=list)
    drawdown: List[float] = Field(default_factory=list)
    returns: List[float] = Field(default_factory=list)


# ============================================================================
# Helper Functions
# ============================================================================

def fetch_price_data(
    tickers: List[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> pd.DataFrame:
    """
    Fetch historical price data for tickers
    
    Args:
        tickers: List of ticker symbols
        start_date: Start date (YYYY-MM-DD), defaults to 1 year ago
        end_date: End date (YYYY-MM-DD), defaults to today
    
    Returns:
        DataFrame with columns: Date, Ticker, Close
    """
    if not YFINANCE_AVAILABLE:
        logger.warning("yfinance not available - returning mock data")
        return pd.DataFrame()
    
    # Default dates
    if end_date is None:
        end_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    if start_date is None:
        start_date = (datetime.now(timezone.utc) - timedelta(days=365)).strftime('%Y-%m-%d')
    
    all_data = []
    
    for ticker in tickers:
        try:
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(start=start_date, end=end_date)
            
            if hist.empty:
                logger.warning(f"No data for {ticker}")
                continue
            
            # Extract close prices
            df = hist[['Close']].reset_index()
            df['Ticker'] = ticker
            df.columns = ['Date', 'Close', 'Ticker']
            
            all_data.append(df)
            
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {str(e)}")
            continue
    
    if not all_data:
        return pd.DataFrame()
    
    # Combine all data
    combined = pd.concat(all_data, ignore_index=True)
    return combined


def calculate_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate daily returns from prices
    
    Args:
        prices: DataFrame with columns: Date, Ticker, Close
    
    Returns:
        DataFrame with columns: Date, Ticker, Return
    """
    if prices.empty:
        return pd.DataFrame()
    
    returns_list = []
    
    for ticker in prices['Ticker'].unique():
        ticker_data = prices[prices['Ticker'] == ticker].sort_values('Date')
        ticker_data['Return'] = ticker_data['Close'].pct_change()
        returns_list.append(ticker_data[['Date', 'Ticker', 'Return']])
    
    combined = pd.concat(returns_list, ignore_index=True)
    return combined.dropna()


def calculate_portfolio_returns(
    returns: pd.DataFrame,
    weights: Optional[Dict[str, float]] = None
) -> pd.Series:
    """
    Calculate portfolio returns (equal-weighted by default)
    
    Args:
        returns: DataFrame with columns: Date, Ticker, Return
        weights: Optional dict of ticker -> weight (must sum to 1.0)
    
    Returns:
        Series with Date index and portfolio returns
    """
    if returns.empty:
        return pd.Series()
    
    # Pivot to wide format (tickers as columns)
    returns_wide = returns.pivot(index='Date', columns='Ticker', values='Return')
    
    if weights is None:
        # Equal weights
        weights = {ticker: 1.0 / len(returns_wide.columns) for ticker in returns_wide.columns}
    
    # Calculate weighted returns
    portfolio_returns = pd.Series(0.0, index=returns_wide.index)
    
    for ticker, weight in weights.items():
        if ticker in returns_wide.columns:
            portfolio_returns += returns_wide[ticker] * weight
    
    return portfolio_returns


def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.02
) -> float:
    """
    Calculate Sharpe ratio
    
    Args:
        returns: Series of returns
        risk_free_rate: Annual risk-free rate (default 2%)
    
    Returns:
        Sharpe ratio
    """
    if returns.empty or returns.std() == 0:
        return 0.0
    
    # Annualize
    excess_return = returns.mean() * 252 - risk_free_rate
    volatility = returns.std() * np.sqrt(252)
    
    return excess_return / volatility if volatility > 0 else 0.0


def calculate_drawdown(equity_curve: pd.Series) -> Tuple[pd.Series, float]:
    """
    Calculate drawdown series and max drawdown
    
    Args:
        equity_curve: Series of cumulative portfolio values
    
    Returns:
        (drawdown_series, max_drawdown)
    """
    if equity_curve.empty:
        return pd.Series(), 0.0
    
    # Calculate running maximum
    running_max = equity_curve.cummax()
    
    # Drawdown = (current - max) / max
    drawdown = (equity_curve - running_max) / running_max
    
    max_drawdown = drawdown.min()
    
    return drawdown, max_drawdown


def calculate_beta_alpha(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
    risk_free_rate: float = 0.02
) -> Tuple[float, float]:
    """
    Calculate portfolio beta and alpha vs benchmark
    
    Args:
        portfolio_returns: Portfolio returns
        benchmark_returns: Benchmark returns
        risk_free_rate: Annual risk-free rate
    
    Returns:
        (beta, alpha)
    """
    if portfolio_returns.empty or benchmark_returns.empty:
        return 0.0, 0.0
    
    # Align indices
    aligned = pd.DataFrame({
        'portfolio': portfolio_returns,
        'benchmark': benchmark_returns
    }).dropna()
    
    if len(aligned) < 2:
        return 0.0, 0.0
    
    # Calculate beta (covariance / variance)
    covariance = aligned['portfolio'].cov(aligned['benchmark'])
    benchmark_variance = aligned['benchmark'].var()
    
    beta = covariance / benchmark_variance if benchmark_variance > 0 else 0.0
    
    # Calculate alpha (CAPM)
    portfolio_annual_return = aligned['portfolio'].mean() * 252
    benchmark_annual_return = aligned['benchmark'].mean() * 252
    
    alpha = portfolio_annual_return - (risk_free_rate + beta * (benchmark_annual_return - risk_free_rate))
    
    return beta, alpha


# ============================================================================
# Main Service Class
# ============================================================================

class PortfolioPerformanceService:
    """Service for calculating portfolio performance metrics"""
    
    def __init__(self):
        self.risk_free_rate = 0.02  # 2% annual
    
    def calculate_performance(
        self,
        tickers: List[str],
        weights: Optional[Dict[str, float]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        benchmark: str = "SPY"
    ) -> Tuple[PortfolioMetrics, BenchmarkComparison, PerformanceTimeSeries]:
        """
        Calculate comprehensive portfolio performance
        
        Args:
            tickers: List of ticker symbols
            weights: Optional ticker weights (equal-weighted if None)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            benchmark: Benchmark ticker (default SPY)
        
        Returns:
            (metrics, benchmark_comparison, timeseries)
        """
        logger.info(f"Calculating performance for {len(tickers)} tickers vs {benchmark}")
        
        # Fetch price data
        prices = fetch_price_data(tickers + [benchmark], start_date, end_date)
        
        if prices.empty:
            logger.warning("No price data available")
            return self._empty_response(benchmark)
        
        # Calculate returns
        returns = calculate_returns(prices)
        
        # Separate portfolio and benchmark returns
        portfolio_tickers = [t for t in tickers if t in returns['Ticker'].unique()]
        benchmark_returns_df = returns[returns['Ticker'] == benchmark]
        portfolio_returns_df = returns[returns['Ticker'].isin(portfolio_tickers)]
        
        if portfolio_returns_df.empty:
            logger.warning("No portfolio returns data")
            return self._empty_response(benchmark)
        
        # Calculate portfolio returns (weighted)
        portfolio_returns = calculate_portfolio_returns(portfolio_returns_df, weights)
        
        # Calculate benchmark returns
        benchmark_returns = benchmark_returns_df.set_index('Date')['Return']
        
        # === PORTFOLIO METRICS ===
        metrics = self._calculate_metrics(portfolio_returns)
        
        # === BENCHMARK COMPARISON ===
        comparison = self._calculate_benchmark_comparison(
            portfolio_returns,
            benchmark_returns,
            benchmark
        )
        
        # === TIME SERIES ===
        timeseries = self._calculate_timeseries(portfolio_returns)
        
        return metrics, comparison, timeseries
    
    def _calculate_metrics(self, returns: pd.Series) -> PortfolioMetrics:
        """Calculate portfolio metrics"""
        if returns.empty:
            return PortfolioMetrics()
        
        # Total return
        total_return = (1 + returns).prod() - 1
        
        # Annualized return
        num_days = len(returns)
        annualized_return = (1 + total_return) ** (252 / num_days) - 1 if num_days > 0 else 0.0
        
        # Volatility (annualized)
        volatility = returns.std() * np.sqrt(252)
        
        # Sharpe ratio
        sharpe = calculate_sharpe_ratio(returns, self.risk_free_rate)
        
        # Equity curve for drawdown
        equity_curve = (1 + returns).cumprod()
        _, max_drawdown = calculate_drawdown(equity_curve)
        
        # Win rate
        win_rate = (returns > 0).sum() / len(returns) if len(returns) > 0 else 0.0
        
        # Best/worst day
        best_day = returns.max()
        worst_day = returns.min()
        
        return PortfolioMetrics(
            total_return=float(total_return),
            annualized_return=float(annualized_return),
            volatility=float(volatility),
            sharpe_ratio=float(sharpe),
            max_drawdown=float(max_drawdown),
            win_rate=float(win_rate),
            best_day=float(best_day),
            worst_day=float(worst_day)
        )
    
    def _calculate_benchmark_comparison(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series,
        benchmark_ticker: str
    ) -> BenchmarkComparison:
        """Calculate benchmark comparison metrics"""
        if portfolio_returns.empty or benchmark_returns.empty:
            return BenchmarkComparison(benchmark_ticker=benchmark_ticker)
        
        # Align returns
        aligned = pd.DataFrame({
            'portfolio': portfolio_returns,
            'benchmark': benchmark_returns
        }).dropna()
        
        if aligned.empty:
            return BenchmarkComparison(benchmark_ticker=benchmark_ticker)
        
        # Total returns
        portfolio_total = (1 + aligned['portfolio']).prod() - 1
        benchmark_total = (1 + aligned['benchmark']).prod() - 1
        outperformance = portfolio_total - benchmark_total
        
        # Correlation
        correlation = aligned['portfolio'].corr(aligned['benchmark'])
        
        # Beta and Alpha
        beta, alpha = calculate_beta_alpha(
            aligned['portfolio'],
            aligned['benchmark'],
            self.risk_free_rate
        )
        
        return BenchmarkComparison(
            benchmark_ticker=benchmark_ticker,
            portfolio_return=float(portfolio_total),
            benchmark_return=float(benchmark_total),
            outperformance=float(outperformance),
            correlation=float(correlation),
            beta=float(beta),
            alpha=float(alpha)
        )
    
    def _calculate_timeseries(self, returns: pd.Series) -> PerformanceTimeSeries:
        """Calculate time series data for charts"""
        if returns.empty:
            return PerformanceTimeSeries()
        
        # Equity curve (normalized to 100)
        equity_curve = (1 + returns).cumprod() * 100
        
        # Drawdown
        drawdown_series, _ = calculate_drawdown(equity_curve)
        
        return PerformanceTimeSeries(
            dates=[d.strftime('%Y-%m-%d') for d in returns.index],
            equity_curve=equity_curve.tolist(),
            drawdown=(drawdown_series * 100).tolist(),  # Convert to percentage
            returns=(returns * 100).tolist()  # Convert to percentage
        )
    
    def _empty_response(
        self,
        benchmark: str
    ) -> Tuple[PortfolioMetrics, BenchmarkComparison, PerformanceTimeSeries]:
        """Return empty response structures"""
        return (
            PortfolioMetrics(),
            BenchmarkComparison(benchmark_ticker=benchmark),
            PerformanceTimeSeries()
        )


# Singleton instance
_performance_service: Optional[PortfolioPerformanceService] = None


def get_performance_service() -> PortfolioPerformanceService:
    """Get or create performance service singleton"""
    global _performance_service
    if _performance_service is None:
        _performance_service = PortfolioPerformanceService()
    return _performance_service
