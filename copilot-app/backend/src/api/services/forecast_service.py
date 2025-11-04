"""
Service layer for forecasts with persistent caching.
Addresses the issue of empty responses in the forecasts endpoint.
Updated to use hybrid ML + G4F system (FC-P1-013).
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
from pathlib import Path
import pandas as pd
import json
from datetime import datetime, timedelta
import asyncio

# New imports for persistent caching
from backend.storage.base import load_json, save_json
from backend.services.cache_layer import load_or_compute

from analytics.forecaster import forecast_ticker, ForecastResult
from core.data_store import query_duckdb, write_parquet
from backend.models.forecast_hybrid_v1 import ForecastHybridV1


class ForecastService:
    def __init__(self):
        self.cache_ttl = 300  # 5 minutes
        self.data_path = Path("data/forecast")
        # Initialize the hybrid forecast system
        self.hybrid_system = ForecastHybridV1()
    
    async def get_all_forecasts(self, 
                               asset_type: str = "all", 
                               horizon: str = "all", 
                               sort_by: str = "score") -> Dict[str, Any]:
        """
        Get all forecasts with persistent caching and fallback mechanisms.
        Updated to use hybrid ML + G4F system (FC-P1-013).
        Returns real data or empty structure but never fails.
        """
        # Use the persistent cache mechanism
        key = f"forecasts_{asset_type}_{horizon}_{sort_by}"
        
        async def compute_forecasts():
            try:
                # Try to load from the hybrid system's saved forecasts first
                forecasts_data = self._load_hybrid_forecasts()
                
                if not forecasts_data or not forecasts_data.get("rows"):
                    # If no hybrid forecast data, execute the hybrid system
                    forecasts_data = self._generate_hybrid_forecasts()
                
                # Apply filters
                filtered_data = self._filter_forecasts(forecasts_data.get("rows", []), asset_type, horizon)
                
                # Apply sorting
                sorted_data = self._sort_forecasts(filtered_data, sort_by)
                
                return {
                    "rows": sorted_data,
                    "count": len(sorted_data),
                    "asset_type": asset_type,
                    "generated_at": forecasts_data.get("last_update", datetime.utcnow().isoformat()),
                    "source": forecasts_data.get("source", ["hybrid_ml_g4f"]),
                    "model_version": forecasts_data.get("model_version", "hybrid_v1")
                }
            except Exception as e:
                # Fallback: return structured empty response instead of failing
                return {
                    "rows": [],
                    "count": 0,
                    "error": str(e),
                    "generated_at": datetime.utcnow().isoformat(),
                    "source": ["hybrid_ml_g4f", "error_fallback"],
                    "model_version": "hybrid_v1"
                }
        
        # Use load_or_compute to get data with persistent caching
        result = load_or_compute(
            key,
            compute_forecasts,
            ["forecast_service", "hybrid_ml_g4f", "realtime_calculation"]
        )
        
        # Extract the actual data from the result
        if result and "data" in result:
            actual_data = result["data"]
        else:
            actual_data = result
            
        # Ensure the result has the expected format for the API
        if actual_data and "error" not in actual_data:
            return {
                "ok": True,
                "data": actual_data
            }
        else:
            # Return empty structure but never fail
            return {
                "ok": False,
                "data": {
                    "rows": [],
                    "count": 0,
                    "generated_at": datetime.utcnow().isoformat(),
                    "source": ["fallback"],
                    "model_version": "hybrid_v1"
                }
            }
    
    def _load_hybrid_forecasts(self) -> Dict[str, Any]:
        """
        Load forecasts from the hybrid system's saved file.
        """
        try:
            # The hybrid system saves to data/forecasts.json
            forecasts_file = Path(__file__).parent.parent.parent / "data" / "forecasts.json"
            
            if forecasts_file.exists():
                with open(forecasts_file, 'r') as f:
                    content = json.load(f)
                
                # Return the data part if it exists
                if "data" in content:
                    return content["data"]
                else:
                    # If the format is different, return as is
                    return content
        except Exception as e:
            print(f"Error loading hybrid forecasts: {e}")
            pass
        
        return {}
    
    def _generate_hybrid_forecasts(self) -> Dict[str, Any]:
        """
        Generate forecasts using the hybrid system (ML + G4F).
        """
        try:
            # Use the hybrid system to generate forecasts for common tickers
            common_tickers = ["SPY", "QQQ", "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "TSM"]
            return self.hybrid_system.run_forecast_job(common_tickers)
        except Exception as e:
            print(f"Error generating hybrid forecasts: {e}")
            return {"rows": [], "last_update": datetime.utcnow().isoformat(), "source": ["hybrid_ml_g4f", "error_fallback"]}
    
    def _load_cached_forecasts(self) -> List[Dict[str, Any]]:
        """Load forecasts from parquet cache."""
        try:
            parts = sorted(self.data_path.glob('dt=*'))
            if parts:
                latest = parts[-1]
                final_path = latest / 'final.parquet'
                if final_path.exists():
                    df = pd.read_parquet(final_path)
                    if not df.empty:
                        # Convert DataFrame to list of dicts
                        return df.to_dict('records')
        except Exception:
            pass
        return []
    
    def _has_cached_data(self) -> bool:
        """Check if we have any cached forecast data."""
        try:
            parts = sorted(self.data_path.glob('dt=*'))
            if parts:
                latest = parts[-1]
                final_path = latest / 'final.parquet'
                return final_path.exists()
        except Exception:
            pass
        return False
    
    def _generate_fallback_forecasts(self) -> List[Dict[str, Any]]:
        """
        Generate forecasts for common tickers as fallback.
        This ensures we never have empty results.
        """
        common_tickers = ["SPY", "QQQ", "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "TSM"]
        horizons = ["1w", "1m", "3m"]
        
        all_forecasts = []
        
        for ticker in common_tickers:
            for horizon in horizons:
                try:
                    # Generate forecast using the existing forecaster
                    forecast_result: ForecastResult = forecast_ticker(ticker, horizon)
                    
                    forecast_dict = {
                        "ticker": ticker,
                        "horizon": horizon,
                        "direction": forecast_result.direction,
                        "confidence": forecast_result.confidence,
                        "expected_return": forecast_result.expected_return,
                        "drivers": forecast_result.drivers,
                        "generated_at": datetime.utcnow().isoformat()
                    }
                    
                    all_forecasts.append(forecast_dict)
                except Exception:
                    # If forecast fails for a ticker, continue with others
                    continue
        
        return all_forecasts
    
    def _filter_forecasts(self, forecasts: List[Dict], asset_type: str, horizon: str) -> List[Dict]:
        """Filter forecasts by asset type and horizon."""
        filtered = forecasts
        
        if asset_type != "all":
            # For now, we only have equity data
            if asset_type == "equity":
                # All tickers in our system are equities
                pass
            # Add other asset types when available
        
        if horizon != "all":
            filtered = [f for f in filtered if f.get("horizon") == horizon]
        
        return filtered
    
    def _sort_forecasts(self, forecasts: List[Dict], sort_by: str) -> List[Dict]:
        """Sort forecasts by the specified criteria."""
        if sort_by == "score":
            # Sort by confidence (or final_score if available)
            return sorted(forecasts, key=lambda x: x.get("confidence", 0), reverse=True)
        elif sort_by == "ticker":
            return sorted(forecasts, key=lambda x: x.get("ticker", ""))
        else:
            # Default: sort by confidence
            return sorted(forecasts, key=lambda x: x.get("confidence", 0), reverse=True)


# Global forecast service instance
forecast_service = ForecastService()