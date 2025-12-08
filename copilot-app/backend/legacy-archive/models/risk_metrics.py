"""
Risk Metrics Calculator
Task: FC-API-031 - Risk Analytics Dashboard
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import math
from statistics import mean, stdev


class RiskMetricsCalculator:
    """
    Calculate risk metrics for portfolio and individual assets
    """
    
    def __init__(self):
        self.cached_risks = {}
    
    def calculate_var_historical(self, returns: List[float], confidence: float = 0.95) -> float:
        """
        Calculate historical Value at Risk (VaR) at the specified confidence level
        
        Args:
            returns: List of historical returns
            confidence: Confidence level (e.g., 0.95 for 95% VaR)
        
        Returns:
            VaR at specified confidence level
        """
        if not returns or len(returns) == 0:
            return 0.0
        
        # Sort returns in ascending order
        sorted_returns = sorted(returns)
        
        # Calculate the index for the specified confidence level
        index = int((1 - confidence) * len(sorted_returns))
        
        # Ensure index is valid
        if index >= len(sorted_returns):
            index = len(sorted_returns) - 1
        if index < 0:
            index = 0
        
        # VaR is the negative of the specified percentile return
        var = -sorted_returns[index] if sorted_returns else 0.0
        return float(var)
    
    def calculate_var_parametric(self, returns: List[float], confidence: float = 0.95) -> float:
        """
        Calculate parametric (variance-covariance) Value at Risk (VaR)
        
        Args:
            returns: List of historical returns
            confidence: Confidence level (e.g., 0.95 for 95% VaR)
        
        Returns:
            Parametric VaR at specified confidence level
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        # Calculate mean and standard deviation of returns
        mean_return = mean(returns)
        std_dev = stdev(returns) if len(returns) > 1 else 0.0
        
        # Z-score for 95% confidence level (approximately -1.645)
        z_scores = {
            0.90: -1.282,
            0.95: -1.645,
            0.99: -2.326
        }
        
        z_score = z_scores.get(confidence, -1.645)  # Default to 95% if not found
        
        # VaR = mean - (z_score * std_dev)
        var = -(mean_return + (z_score * std_dev))
        return float(var)
    
    def calculate_portfolio_var(self, asset_returns: Dict[str, List[float]], weights: Dict[str, float], confidence: float = 0.95) -> float:
        """
        Calculate portfolio Value at Risk
        
        Args:
            asset_returns: Dictionary with asset name as key and returns as value
            weights: Dictionary with asset name as key and weight in portfolio as value
            confidence: Confidence level for VaR calculation
        
        Returns:
            Portfolio VaR at specified confidence level
        """
        if not asset_returns or not weights:
            return 0.0
        
        # Calculate weighted portfolio returns
        # This is a simplified approach - assumes equal length return series
        portfolio_returns = []
        
        # Get all return series and ensure they have the same length
        if not asset_returns:
            return 0.0
        
        # Calculate portfolio returns based on weights
        asset_names = list(asset_returns.keys())
        series_lengths = [len(asset_returns[name]) for name in asset_names]
        min_length = min(series_lengths) if series_lengths else 0
        
        if min_length == 0:
            return 0.0
        
        # Calculate portfolio return for each period
        for i in range(min_length):
            portfolio_return = 0.0
            total_weight = 0.0
            
            for asset in asset_names:
                if i < len(asset_returns[asset]):
                    weight = weights.get(asset, 0.0)  # Default to 0 if no weight specified
                    asset_return = asset_returns[asset][i]
                    portfolio_return += asset_return * weight
                    total_weight += weight
            
            # Normalize by total weight to handle incomplete weight specification
            if total_weight > 0:
                portfolio_returns.append(portfolio_return / total_weight if total_weight != 1.0 else portfolio_return)
            else:
                portfolio_returns.append(0.0)  # Default to 0 if no weights available
        
        # Calculate VaR from portfolio returns
        return self.calculate_var_historical(portfolio_returns, confidence)
    
    def calculate_beta(self, asset_returns: List[float], market_returns: List[float]) -> float:
        """
        Calculate Beta of an asset relative to the market (SPY)
        
        Args:
            asset_returns: List of returns for the asset
            market_returns: List of returns for the market benchmark
        
        Returns:
            Beta coefficient
        """
        if not asset_returns or not market_returns or len(asset_returns) != len(market_returns) or len(asset_returns) < 2:
            return 0.0
        
        n = len(asset_returns)
        
        # Calculate means
        asset_mean = mean(asset_returns)
        market_mean = mean(market_returns)
        
        # Calculate covariance and market variance
        cov_asset_market = sum((asset_returns[i] - asset_mean) * (market_returns[i] - market_mean) for i in range(n)) / (n - 1)
        var_market = sum((market_returns[i] - market_mean) ** 2 for i in range(n)) / (n - 1)
        
        if var_market == 0:
            return 0.0
        
        beta = cov_asset_market / var_market
        return float(beta)
    
    def calculate_correlation_matrix(self, asset_returns: Dict[str, List[float]]) -> Dict[str, Dict[str, float]]:
        """
        Calculate correlation matrix between assets
        
        Args:
            asset_returns: Dictionary with asset name as key and returns as value
        
        Returns:
            Correlation matrix as nested dictionary
        """
        assets = list(asset_returns.keys())
        n = len(assets)
        
        # Initialize correlation matrix
        correlation_matrix = {}
        for asset1 in assets:
            correlation_matrix[asset1] = {}
            for asset2 in assets:
                correlation_matrix[asset1][asset2] = 0.0
        
        # Calculate correlations
        for i, asset1 in enumerate(assets):
            for j, asset2 in enumerate(assets):
                if i == j:
                    correlation_matrix[asset1][asset2] = 1.0  # Self-correlation is 1
                elif i < j:  # Only calculate each pair once
                    corr = self.calculate_correlation(asset_returns[asset1], asset_returns[asset2])
                    correlation_matrix[asset1][asset2] = corr
                    correlation_matrix[asset2][asset1] = corr  # Correlation matrix is symmetric
        
        return correlation_matrix
    
    def calculate_correlation(self, returns1: List[float], returns2: List[float]) -> float:
        """
        Calculate correlation coefficient between two series of returns
        """
        if not returns1 or not returns2 or len(returns1) != len(returns2) or len(returns1) < 2:
            return 0.0
        
        n = len(returns1)
        
        # Calculate means
        mean1 = mean(returns1)
        mean2 = mean(returns2)
        
        # Calculate standard deviations
        std1 = stdev(returns1) if len(returns1) > 1 else 0.0
        std2 = stdev(returns2) if len(returns2) > 1 else 0.0
        
        if std1 == 0 or std2 == 0:
            return 0.0
        
        # Calculate correlation
        numerator = sum((returns1[i] - mean1) * (returns2[i] - mean2) for i in range(n)) / (n - 1)
        denominator = std1 * std2
        
        if denominator == 0:
            return 0.0
        
        correlation = numerator / denominator
        # Clamp correlation between -1 and 1 to handle floating point errors
        return max(-1.0, min(1.0, float(correlation)))
    
    def calculate_volatility(self, returns: List[float], annualized: bool = True) -> float:
        """
        Calculate volatility (standard deviation) of returns
        
        Args:
            returns: List of returns
            annualized: Whether to annualize the volatility (sqrt(252) for daily returns)
        
        Returns:
            Volatility of the returns
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        # Calculate standard deviation
        vol = stdev(returns)
        
        if annualized:
            # Annualize using trading days (252 days per year is typical for daily returns)
            vol *= math.sqrt(252)
        
        return float(vol)
    
    def _calculate_portfolio_metrics(self, 
                                   asset_returns: Dict[str, List[float]], 
                                   weights: Optional[Dict[str, float]] = None,
                                   market_returns: Optional[List[float]] = None) -> Dict[str, Any]:
        """
        Calculate comprehensive portfolio risk metrics
        
        Args:
            asset_returns: Dictionary of {asset: [returns]}
            weights: Optional weights dictionary, if None assumes equal weighting
            market_returns: Optional market returns for beta calculation
        
        Returns:
            Dictionary with all portfolio risk metrics
        """
        assets = list(asset_returns.keys())
        
        if not assets:
            return self._get_empty_metrics()
        
        # Set default weights if not provided (equal weighting)
        if weights is None:
            weight_value = 1.0 / len(assets)
            weights = {asset: weight_value for asset in assets}
        
        # Initialize portfolio metrics
        portfolio_metrics = {
            "assets": assets,
            "weights": weights,
            "total_assets": len(assets),
            "total_weight": sum(weights.values())
        }
        
        # Calculate portfolio VaR metrics
        portfolio_var_95 = self.calculate_portfolio_var(asset_returns, weights, 0.95)
        portfolio_var_99 = self.calculate_portfolio_var(asset_returns, weights, 0.99)
        
        portfolio_metrics["var_95"] = portfolio_var_95
        portfolio_metrics["var_99"] = portfolio_var_99
        
        # Calculate individual asset metrics
        individual_metrics = {}
        for asset, returns in asset_returns.items():
            weight = weights.get(asset, 0.0)
            
            individual_metrics[asset] = {
                "weight": weight,
                "var_95": self.calculate_var_historical(returns, 0.95),
                "var_99": self.calculate_var_historical(returns, 0.99),
                "volatility": self.calculate_volatility(returns),
                "returns_count": len(returns)
            }
            
            # Calculate Beta if market returns are available
            if market_returns:
                individual_metrics[asset]["beta"] = self.calculate_beta(returns, market_returns)
        
        portfolio_metrics["individual"] = individual_metrics
        
        # Calculate correlation matrix
        correlation_matrix = self.calculate_correlation_matrix(asset_returns)
        portfolio_metrics["correlations"] = correlation_matrix
        
        # Calculate portfolio-level metrics
        portfolio_vols = []
        for asset, returns in asset_returns.items():
            asset_vol = self.calculate_volatility(returns) * weights.get(asset, 0.0)
            portfolio_vols.append(asset_vol)
        
        combined_volatility = sum(portfolio_vols)  # Simplified - ignores correlations
        portfolio_metrics["portfolio_volatility"] = combined_volatility
        portfolio_metrics["diversification_ratio"] = combined_volatility / portfolio_var_95 if portfolio_var_95 != 0 else 1.0
        
        portfolio_metrics["generated_at"] = datetime.utcnow().isoformat() + "Z"
        portfolio_metrics["source"] = ["risk_calculator", "portfolio_analytics", "fc-api-031"]
        
        return portfolio_metrics
    
    def _get_empty_metrics(self) -> Dict[str, Any]:
        """
        Return empty metrics structure to maintain never-empty contract
        """
        return {
            "assets": [],
            "weights": {},
            "total_assets": 0,
            "total_weight": 0.0,
            "var_95": 0.0,
            "var_99": 0.0,
            "portfolio_volatility": 0.0,
            "diversification_ratio": 1.0,
            "individual": {},
            "correlations": {},
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source": ["risk_calculator", "empty_fallback", "fc-api-031"],
            "warning": "No return data available, returning empty metrics structure to maintain never-empty contract"
        }
    
    def get_risk_dashboard_data(self, tickers: List[str]) -> Dict[str, Any]:
        """
        Get risk dashboard data for specified tickers
        
        Args:
            tickers: List of tickers to calculate risk metrics for
            
        Returns:
            Comprehensive risk metrics dashboard data
        """
        try:
            # Generate mock returns based on the tickers
            # In practice, this would load from persisted data or fetch real market data
            mock_returns = {}
            for ticker in tickers:
                # Generate mock returns (would typically come from price history)
                mock_returns[ticker] = self._generate_mock_returns(30)  # 30 days of returns
            
            # Also generate mock market returns (SPY) for beta calculations
            market_returns = self._generate_mock_returns(30, base_value=0.0005)  # Lower volatility for market index
            
            # Calculate comprehensive metrics
            metrics = self._calculate_portfolio_metrics(
                asset_returns=mock_returns,
                weights=None,
                market_returns=market_returns
            )
            
            # Add ticker-specific risk analysis
            risk_signals = []
            for ticker in tickers:
                individual_data = metrics["individual"].get(ticker, {})
                if individual_data:
                    risk_signals.append({
                        "ticker": ticker,
                        "var_95": individual_data.get("var_95", 0.0),
                        "volatility": individual_data.get("volatility", 0.0),
                        "beta": individual_data.get("beta", 0.0),
                        "sharpe_ratio": individual_data.get("sharpe_ratio", 0.0) if "sharpe_ratio" in individual_data else 0.0,
                        "max_drawdown": individual_data.get("max_drawdown", 0.0) if "max_drawdown" in individual_data else 0.0,
                        "risk_level": self._determine_risk_level(
                            individual_data.get("var_95", 0.0),
                            individual_data.get("volatility", 0.0),
                            individual_data.get("beta", 0.0)
                        )
                    })
            
            result = {
                "portfolio_metrics": metrics,
                "individual_risks": risk_signals,
                "tickers_analyzed": tickers,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "source": ["risk_analytics_calculator", "portfolio_dashboard", "fc-api-031"],
                "data_quality": "synthetic_data_for_demo"  # Indicates this is demo data
            }
            
            return result
            
        except Exception as e:
            print(f"Error in risk dashboard calculation: {str(e)}")
            # Return fallback structure to maintain never-empty contract
            return {
                "portfolio_metrics": self._get_empty_metrics(),
                "individual_risks": [],
                "tickers_analyzed": tickers,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "source": ["risk_analytics_calculator", "error_fallback", "fc-api-031"],
                "error": str(e),
                "message": "Risk calculation failed but fallback data returned to maintain never-empty contract"
            }
    
    def _generate_mock_returns(self, n: int, volatility: float = 0.02, base_value: float = 0.001) -> List[float]:
        """
        Generate mock returns for testing/presentation purposes
        In real implementation, this would come from actual price history
        """
        import random
        # Generate somewhat realistic returns with base drift and volatility
        returns = []
        for _ in range(n):
            # Generate return with drift and some randomness
            drift = base_value
            shock = random.uniform(-volatility, volatility)  # Random market shock
            returns.append(drift + shock)
        return returns
    
    def _determine_risk_level(self, var_95: float, volatility: float, beta: float) -> str:
        """
        Determine risk level based on multiple metrics
        """
        # Calculate risk score based on multiple factors
        risk_score = (var_95 * 0.4) + (volatility * 0.4) + (abs(beta - 1) * 0.2)  # Higher beta deviating from 1.0 = more risk
        
        if risk_score > 0.05:
            return "high"  # High risk
        elif risk_score > 0.02:
            return "medium"  # Medium risk
        else:
            return "low"  # Low risk


# Global instance
risk_metrics_calculator = RiskMetricsCalculator()


# Convenience functions
def calculate_portfolio_var(returns: Dict[str, List[float]], weights: Dict[str, float], confidence: float = 0.95) -> float:
    """
    Calculate portfolio VaR
    """
    return risk_metrics_calculator.calculate_portfolio_var(returns, weights, confidence)

def calculate_var(returns: List[float], confidence: float = 0.95, method: str = "historical") -> float:
    """
    Calculate VaR using historical or parametric method
    """
    if method == "historical":
        return risk_metrics_calculator.calculate_var_historical(returns, confidence)
    elif method == "parametric":
        return risk_metrics_calculator.calculate_var_parametric(returns, confidence)
    else:
        return risk_metrics_calculator.calculate_var_historical(returns, confidence)

def calculate_beta(asset_returns: List[float], market_returns: List[float]) -> float:
    """
    Calculate Beta of asset vs market
    """
    return risk_metrics_calculator.calculate_beta(asset_returns, market_returns)

def get_risk_dashboard_data(tickers: List[str]) -> Dict[str, Any]:
    """
    Get comprehensive risk dashboard data
    """
    return risk_metrics_calculator.get_risk_dashboard_data(tickers)