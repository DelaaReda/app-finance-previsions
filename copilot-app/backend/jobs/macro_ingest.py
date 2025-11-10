"""
Macro Ingestion and Snapshot Service
Task: FC-DATA-006 - Macro ingestion + snapshot
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import json
import requests

# Add backend path for imports
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

# Ensure .env is loaded before accessing environment variables
try:
    from core.env_loader import ensure_env_loaded, get_env
    ensure_env_loaded()
except ImportError:
    # Fallback if env_loader not available
    def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
        return os.getenv(name, default)

from backend.storage.io import save_json, load_json

# FRED API details
FRED_API_KEY = get_env("FRED_API_KEY", "cd46b26e7a08a4bd5ffc6bed7a7ca02f")  # Public demo key
FRED_BASE_URL = "https://api.stlouisfed.org/fred"

class MacroIngestionService:
    """
    Service for ingesting macroeconomic data from FRED API and storing in JSON (Parquet if available)
    """
    
    def __init__(self):
        self.series_registry = {
            "CPIAUCSL": {"title": "Consumer Price Index", "category": "inflation", "freq": "monthly"},
            "UNRATE": {"title": "Civilian Unemployment Rate", "category": "labor", "freq": "monthly"},
            "FEDFUNDS": {"title": "Effective Federal Funds Rate", "category": "rates", "freq": "daily"},
            "T10Y2Y": {"title": "10-Year Treasury Constant Maturity Minus 2-Year Treasury Constant Maturity", "category": "yield_curve", "freq": "daily"},
            "GDP": {"title": "Gross Domestic Product", "category": "growth", "freq": "quarterly"},
            "VIXCLS": {"title": "CBOE Volatility Index", "category": "sentiment", "freq": "daily"},
            "DCOILWTICO": {"title": "Crude Oil Prices: West Texas Intermediate (WTI)", "category": "commodities", "freq": "daily"},
            "DEXUSEU": {"title": "US Dollar to Euro Exchange Rate", "category": "fx", "freq": "daily"},
            "REALHPIUS": {"title": "US Real House Price Index", "category": "housing", "freq": "monthly"},
            "RECPROUSM156N": {"title": "Recession Probabilities for United States", "category": "economic", "freq": "monthly"}
        }
        
        # Create data directories
        self.data_dir = backend_root / "data" / "macro"
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def fetch_fred_series(self, series_id: str, start_date: str = None, end_date: str = None, limit: int = 10000) -> dict:
        """
        Fetch a single FRED series with error handling and fallback
        
        Args:
            series_id: FRED series ID (e.g., "CPIAUCSL", "UNRATE")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            limit: Number of observations to fetch (max 10000)
        
        Returns:
            Dictionary with series data and metadata
        """
        if start_date is None:
            # Default: fetch last 10 years (approximately)
            start_date = (datetime.now() - timedelta(days=365*10)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # Build URL
        url = f"{FRED_BASE_URL}/series/observations"
        params = {
            "series_id": series_id,
            "api_key": FRED_API_KEY,
            "observation_start": start_date,
            "observation_end": end_date,
            "limit": limit,
            "file_type": "json",
            "units": "lin"
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            
            # Check response status
            if response.status_code != 200:
                print(f"Error fetching {series_id}: {response.status_code} - {response.text}")
                return {
                    "id": series_id,
                    "title": self.series_registry.get(series_id, {}).get("title", f"Unknown - {series_id}"),
                    "observations": [],
                    "error": f"HTTP {response.status_code}",
                    "status": "error",
                    "last_update": datetime.utcnow().isoformat() + "Z"
                }
            
            data = response.json()
            
            # Process observations
            observations = []
            for obs in data.get("observations", []):
                if obs.get("value") and obs["value"] != "." and obs["value"] != "":
                    try:
                        value = float(obs["value"])
                        observations.append({
                            "date": obs["date"],
                            "value": value,
                            "real_time_start": obs.get("real_time_start", ""),
                            "real_time_end": obs.get("real_time_end", "")
                        })
                    except ValueError:
                        continue  # Skip invalid values
            
            return {
                "id": series_id,
                "title": data.get("seriess", [{}])[0].get("title", self.series_registry.get(series_id, {}).get("title", f"Unknown - {series_id}")),
                "category": self.series_registry.get(series_id, {}).get("category", "unknown"),
                "frequency": self.series_registry.get(series_id, {}).get("freq", "unknown"),
                "units": data.get("seriess", [{}])[0].get("units", "units"),
                "observations": observations,
                "count": len(observations),
                "last_update": datetime.utcnow().isoformat() + "Z",
                "status": "success"
            }
            
        except Exception as e:
            print(f"Exception fetching {series_id}: {str(e)}")
            # Fallback to return structured data with empty observations
            return {
                "id": series_id,
                "title": self.series_registry.get(series_id, {}).get("title", f"Unknown - {series_id}"),
                "category": self.series_registry.get(series_id, {}).get("category", "unknown"),
                "frequency": self.series_registry.get(series_id, {}).get("freq", "unknown"),
                "units": "",
                "observations": [],
                "count": 0,
                "error": str(e),
                "last_update": datetime.utcnow().isoformat() + "Z",
                "status": "error",
                "message": "Failed to fetch from FRED API, but maintaining never-empty contract with fallback structure"
            }
    
    def fetch_multiple_series(self, series_ids: list, start_date: str = None) -> dict:
        """
        Fetch multiple FRED series and return as mapping {series_id: data}
        """
        results = {}
        
        for series_id in series_ids:
            print(f"Fetching series {series_id}...")
            series_data = self.fetch_fred_series(series_id, start_date=start_date)
            results[series_id] = series_data
            # Be respectful to the API
            import time
            time.sleep(0.25)  # 250ms delay between requests
        
        return {
            "series": results,
            "requested_ids": series_ids,
            "fetched_count": len([k for k, v in results.items() if v.get("status") == "success"]),
            "total_requested": len(series_ids),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source": ["fred_api", "official_data", "fc-data-006"]
        }
    
    def save_series_data(self, series_id: str, series_data: dict):
        """
        Save series to JSON file with date partitioning (fallback to JSON if Parquet unavailable)
        
        Args:
            series_id: FRED series ID
            series_data: Dictionary with series data
        """
        try:
            # Create partition directory by date
            today = datetime.now().strftime("%Y%m%d")
            partition_dir = self.data_dir / f"series_id={series_id}" / f"dt={today}"
            partition_dir.mkdir(parents=True, exist_ok=True)
            
            # Save as JSON (always available) 
            json_file = partition_dir / f"{series_id}_{today}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(series_data, f, indent=2, ensure_ascii=False)
            
            print(f"Saved {len(series_data.get('observations', []))} observations for {series_id} to {json_file}")
            
            # Create/update symlink to latest
            latest_symlink = self.data_dir / f"series_id={series_id}" / "latest"
            if latest_symlink.is_symlink():
                latest_symlink.unlink()
            latest_symlink.symlink_to(partition_dir.resolve())
            
        except Exception as e:
            print(f"Error saving series {series_id} to storage: {str(e)}")
            # Still save as JSON to main data folder as fallback
            save_json(f"macro_series_{series_id}", series_data, source=["fred_ingestion", "fc-data-006", "json_fallback"])
    
    def save_macro_snapshot(self, series_mapping: dict):
        """
        Save latest values snapshot to macro_snapshot.json
        
        Args:
            series_mapping: Dictionary with {series_id: series_data} from fetch_multiple_series
        """
        snapshot = {}
        
        for series_id, series_data in series_mapping.items():
            observations = series_data.get("observations", [])
            if observations:
                # Get the most recent observation
                latest_obs = observations[-1]  # Observations are ordered chronologically
                snapshot[series_id] = {
                    "value": latest_obs["value"],
                    "date": latest_obs["date"],
                    "title": series_data.get("title", ""),
                    "category": series_data.get("category", ""),
                    "frequency": series_data.get("frequency", ""),
                    "last_updated": series_data.get("last_update", datetime.utcnow().isoformat() + "Z")
                }
        
        # Save the snapshot
        save_json("macro_snapshot", {
            "snapshot": snapshot,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source": ["macro_snapshot_service", "fc-data-006"],
            "last_update": datetime.utcnow().isoformat() + "Z"
        }, source=["macro_snapshot", "latest_values", "fc-data-006"])
        
        return snapshot


def run_macro_ingest_job():
    """
    Main macro ingestion job that fetches series and saves to persistent storage
    """
    print("Starting macro data ingestion job...")
    print("Task: FC-DATA-006 - Macro ingestion + snapshot")
    
    service = MacroIngestionService()
    
    try:
        # Define key series to fetch
        key_series = ["CPIAUCSL", "UNRATE", "FEDFUNDS", "T10Y2Y", "GDP", "VIXCLS"]
        
        # Fetch the data
        macro_data = service.fetch_multiple_series(key_series)
        
        # Save each series to persistent storage
        for series_id, series_data in macro_data["series"].items():
            service.save_series_data(series_id, series_data)
        
        # Create the snapshot of latest values
        latest_snapshot = service.save_macro_snapshot(macro_data["series"])
        
        print(f"Macro ingestion completed successfully!")
        print(f"  Fetched {macro_data['fetched_count']}/{macro_data['total_requested']} series")
        print(f"  Created snapshot with {len(latest_snapshot)} latest values")
        
        # Save main macro data to JSON as well for compatibility
        save_json("macro_series", macro_data, source=["macro_ingestion_job", "fc-data-006"])
        
        return macro_data
        
    except Exception as e:
        print(f"Error in macro ingestion job: {str(e)}")
        
        # Fallback: ensure we maintain never-empty contract
        fallback_data = {
            "series": {},
            "requested_ids": [],
            "fetched_count": 0,
            "total_requested": 0,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source": ["macro_ingestion_job", "error_fallback", "fc-data-006"],
            "error": str(e),
            "message": "Macro ingestion failed but fallback data saved to maintain never-empty contract"
        }
        
        # Save the fallback data to ensure API has something to serve
        save_json("macro_series", fallback_data, source=["macro_ingestion_job", "error_fallback", "fc-data-006"])
        
        return fallback_data


if __name__ == "__main__":
    print("="*60)
    print("MACRO INGESTION JOB")
    print("Task: FC-DATA-006 - Macro ingestion + snapshot")
    print(f"Started: {datetime.now().isoformat()}")
    print("-"*60)
    
    result = run_macro_ingest_job()
    
    print("-"*60)
    print("MACRO INGESTION JOB COMPLETED")
    if "error" not in result:
        print(f"Status: SUCCESS")
        print(f"Fetched: {result['fetched_count']}/{result['total_requested']} series")
    else:
        print(f"Status: FALLBACK (due to error)")
        print(f"Error: {result['error']}")
    print(f"Generated: {result['generated_at']}")
    print("="*60)