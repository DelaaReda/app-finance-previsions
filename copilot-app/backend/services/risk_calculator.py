"""
Risk Calculator Service
Task: FC-API-031 - Risk Analytics Dashboard
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from typing import Dict, List, Any, Optional
import sys
from pathlib import Path
from datetime import datetime

# Add backend to path for imports
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from backend.models.risk_metrics import RiskMetricsCalculator, get_risk_dashboard_data, calculate_var, calculate_beta
from backend.storage.io import load_json
from backend.services.cache_layer import load_or_compute


class RiskCalculatorService:
    """
    Service for calculating and managing risk analytics
    """
    
    def __init__(self):
        self.calculator = RiskMetricsCalculator()
    
    def get_portfolio_risk_metrics(self, 
                                  tickers: List[str],
                                  weights: Optional[Dict[str, float]] = None,
                                  market_returns: Optional[List[float]] = None) -> Dict[str, Any]:
        """
        Get portfolio risk metrics with caching and fallback
        
        Args:
            tickers: List of tickers to calculate risk metrics for
            weights: Optional weights for portfolio (defaults to equal weighting)
            market_returns: Optional market returns for beta calculation
            
        Returns:
            Portfolio risk metrics with proper API envelope
        """
        def compute_risk_metrics():
            """Compute fresh risk metrics"""
            try:
                return self.calculator.get_risk_dashboard_data(tickers)
            except Exception as e:
                print(f"Error computing risk metrics: {str(e)}")
                
                # Return fallback structure to maintain never-empty contract
                return {
                    "portfolio_metrics": {
                        "assets": tickers,
                        "weights": weights or {},
                        "total_assets": len(tickers),
                        "total_weight": sum(weights.values()) if weights else float(len(tickers)) * (1.0/len(tickers)) if len(tickers) > 0 else 1.0,
                        "var_95": 0.0,
                        "var_99": 0.0,
                        "portfolio_volatility": 0.0,
                        "diversification_ratio": 1.0,
                        "individual": {ticker: {"var_95": 0.0, "volatility": 0.0, "beta": 0.0, "weight": 1.0/len(tickers) if len(tickers) > 0 else 0.0} for ticker in tickers},
                        "correlations": {},
                        "generated_at": datetime.utcnow().isoformat() + "Z",
                        "source": ["risk_calculator_service", "error_fallback", "fc-api-031"]
                    },
                    "individual_risks": [
                        {
                            "ticker": ticker,
                            "var_95": 0.0,
                            "volatility": 0.0,
                            "beta": 0.0,
                            "risk_level": "low"
                        } for ticker in tickers
                    ],
                    "tickers_analyzed": tickers,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "source": ["risk_calculator_service", "error_fallback", "fc-api-031"],
                    "error": str(e),
                    "message": "Risk calculation failed but fallback data generated to maintain never-empty contract"
                }
        
        # Use cache layer to serve latest available data, compute fresh if none available
        risk_key = f"portfolio_risk_{'_'.join(sorted(tickers))}"
        risk_data = load_or_compute(
            key=risk_key,
            compute_fn=compute_risk_metrics,
            source=["risk_calculator_service", "portfolio_metrics", "fc-api-031"]
        )
        
        # Ensure proper response format
        response_data = risk_data if isinstance(risk_data, dict) else {
            "portfolio_metrics": {},
            "individual_risks": [],
            "tickers_analyzed": tickers,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source": ["risk_calculator_service", "empty_fallback", "fc-api-031"],
            "message": "Invalid data format returned from risk calculation, using fallback to maintain never-empty contract"
        }
        
        return {
            "ok": not response_data.get("error") and len(response_data.get("individual_risks", [])) > 0,
            "data": response_data,
            "freshness": response_data.get("generated_at", datetime.utcnow().isoformat() + "Z")
        }
    
    def get_var_analysis(self, 
                        asset_returns: List[float], 
                        confidence: float = 0.95, 
                        method: str = "historical") -> Dict[str, float]:
        """
        Get Value at Risk analysis for a single asset
        
        Args:
            asset_returns: List of returns for the asset
            confidence: Confidence level (0.95 default)
            method: 'historical' or 'parametric' method
            
        Returns:
            VaR analysis results
        """
        try:
            var_result = calculate_var(asset_returns, confidence, method)
            
            return {
                "var": var_result,
                "confidence_level": confidence,
                "method": method,
                "returns_analyzed": len(asset_returns),
                "generated_at": datetime.utcnow().isoformat() + "Z"
            }
        except Exception as e:
            # Return fallback to maintain never-empty contract
            return {
                "var": 0.0,
                "confidence_level": confidence,
                "method": method,
                "returns_analyzed": 0,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "error": str(e),
                "message": "VaR calculation failed but fallback data returned to maintain never-empty contract"
            }
    
    def get_beta_analysis(self, 
                         asset_returns: List[float], 
                         market_returns: List[float]) -> Dict[str, float]:
        """
        Get Beta analysis comparing asset to market
        
        Args:
            asset_returns: List of returns for the asset
            market_returns: List of returns for market benchmark (like SPY)
            
        Returns:
            Beta analysis results
        """
        try:
            beta_result = calculate_beta(asset_returns, market_returns)
            
            return {
                "beta": beta_result,
                "asset_returns_count": len(asset_returns),
                "market_returns_count": len(market_returns),
                "generated_at": datetime.utcnow().isoformat() + "Z"
            }
        except Exception as e:
            # Return fallback to maintain never-empty contract
            return {
                "beta": 0.0,
                "asset_returns_count": len(asset_returns),
                "market_returns_count": len(market_returns),
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "error": str(e),
                "message": "Beta calculation failed but fallback data returned to maintain never-empty contract"
            }


# Global instance
risk_calculator_service = RiskCalculatorService()

# Convenience functions
def get_portfolio_risk(tickers: List[str], weights: Optional[Dict[str, float]] = None, market_returns: Optional[List[float]] = None):
    """
    Get portfolio risk metrics
    """
    return risk_calculator_service.get_portfolio_risk_metrics(tickers, weights, market_returns)

def get_var_for_asset(asset_returns: List[float], confidence: float = 0.95, method: str = "historical"):
    """
    Get VaR for a single asset
    """
    return risk_calculator_service.get_var_analysis(asset_returns, confidence, method)

def get_beta_for_asset(asset_returns: List[float], market_returns: List[float]):
    """
    Get Beta for a single asset
    """
    return risk_calculator_service.get_beta_analysis(asset_returns, market_returns)