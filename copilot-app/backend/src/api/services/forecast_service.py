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
from backend.storage.io import load_json, save_json
from backend.services.cache_layer import load_or_compute

# Corrected imports for existing modules that might be in the codebase
try:
    from backend.analytics.forecaster import forecast_ticker, ForecastResult
except ImportError:
    # Fallback if module doesn't exist yet
    forecast_ticker = None
    ForecastResult = None

try:
    from backend.core.data_store import query_duckdb, write_parquet
except ImportError:
    # Fallback if module doesn't exist yet
    query_duckdb = None
    write_parquet = None

# Use our newly created ML forecast model
from backend.models.ml_forecast import run_forecast_generation
from backend.models.llm_ranker import llm_ranker


class ForecastService:
    def __init__(self):
        self.cache_ttl = 300  # 5 minutes
        self.data_path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "forecast"
    
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
        result = await load_or_compute(
            key,
            compute_forecasts,
            ["forecast_service", "hybrid_ml_g4f", "realtime_calculation"]
        )
        
        # Prepare the response with freshness info at the top level
        if result and isinstance(result, dict) and "data" in result:
            # This is cached data with metadata, return with freshness info
            api_response = result["data"].copy() if isinstance(result["data"], dict) else {"rows": [], "count": 0}
            api_response["freshness"] = result.get("freshness", "unknown")
            api_response["last_update"] = result.get("last_update")
            api_response["source"] = result.get("source", [])
            
            return {
                "ok": "error" not in (result.get("data", {}) or {}),
                "data": api_response
            }
        else:
            # This is computed data without cache metadata, add basic freshness info
            api_response = result if isinstance(result, dict) else {"rows": [], "count": 0, "generated_at": datetime.utcnow().isoformat()}
            api_response["freshness"] = "fresh"
            api_response["last_update"] = datetime.utcnow().isoformat()
            api_response["source"] = ["realtime_calculation"]
            
            return {
                "ok": "error" not in (result or {}),
                "data": api_response
            }
    
    def _load_hybrid_forecasts(self) -> Dict[str, Any]:
        """
        Load forecasts from the hybrid system's saved file.
        """
        try:
            # Use our job to get the latest forecasts
            from backend.jobs.forecasts import get_latest_forecasts
            return get_latest_forecasts()
        except Exception as e:
            print(f"Error loading hybrid forecasts: {e}")
            pass
        
        return {}
    
    def _generate_hybrid_forecasts(self) -> Dict[str, Any]:
        """
        Generate forecasts using the hybrid system (ML + G4F).
        """
        try:
            # Use our jobs module to run the hybrid forecast job
            from backend.jobs.forecasts import run_forecasts_job
            return run_forecasts_job()
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
        try:
            # Use our ML model to generate forecasts
            from backend.models.ml_forecast import run_forecast_generation
            return run_forecast_generation()
        except Exception as e:
            print(f"Fallback forecast generation failed: {e}")
            # Return minimal structure if all else fails
            return []
    
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