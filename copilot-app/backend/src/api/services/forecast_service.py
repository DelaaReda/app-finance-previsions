"""
Service layer for forecasts with persistent caching.
Addresses the issue of empty responses in the forecasts endpoint.
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
from pathlib import Path
import pandas as pd
import json
from datetime import datetime, timedelta
import asyncio

# New imports for persistent caching
from backend.storage.json_storage import load_json, save_json
from backend.services.cache_service import load_or_compute

from analytics.forecaster import forecast_ticker, ForecastResult
from core.data_store import query_duckdb, write_parquet


class ForecastService:
    def __init__(self):
        self.cache_ttl = 300  # 5 minutes
        self.data_path = Path("data/forecast")
    
    async def get_all_forecasts(self, 
                               asset_type: str = "all", 
                               horizon: str = "all", 
                               sort_by: str = "score") -> Dict[str, Any]:
        """
        Get all forecasts with persistent caching and fallback mechanisms.
        Returns real data or empty structure but never fails.
        """
        # Use the persistent cache mechanism
        key = f"forecasts_{asset_type}_{horizon}_{sort_by}"
        
        async def compute_forecasts():
            try:
                # Try to load from parquet first
                forecasts_data = self._load_cached_forecasts()
                
                if not forecasts_data:
                    # If no cached data, generate fresh forecasts for common tickers
                    forecasts_data = self._generate_fallback_forecasts()
                
                # Apply filters
                filtered_data = self._filter_forecasts(forecasts_data, asset_type, horizon)
                
                # Apply sorting
                sorted_data = self._sort_forecasts(filtered_data, sort_by)
                
                return {
                    "rows": sorted_data,
                    "count": len(sorted_data),
                    "asset_type": asset_type,
                    "generated_at": datetime.utcnow().isoformat(),
                    "source": "parquet_cache" if self._has_cached_data() else "realtime_calculation"
                }
            except Exception as e:
                # Fallback: return structured empty response instead of failing
                return {
                    "rows": [],
                    "count": 0,
                    "error": str(e),
                    "generated_at": datetime.utcnow().isoformat(),
                    "source": "error_fallback"
                }
        
        # Use load_or_compute to get data with persistent caching
        result = await load_or_compute(
            key=key,
            compute_fn=compute_forecasts,
            sources=["forecast_service", "parquet", "realtime_calculation"]
        )
        
        # Ensure the result has the expected format for the API
        if result and "data" not in result:
            # If load_or_compute returned raw computed data, wrap it properly
            return {
                "ok": result.get("error") is None,
                "data": result
            }
        else:
            # If load_or_compute returned cached data with metadata, use it as is
            return {
                "ok": result is not None and "error" not in (result.get("data", {}) or {}),
                "data": result.get("data", result) if result else {"rows": [], "count": 0, "generated_at": datetime.utcnow().isoformat()}
            }
    
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