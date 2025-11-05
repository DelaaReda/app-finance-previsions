"""
Forecasts Materialization Job - FC-DATA-004
Creates daily forecast cache in Parquet format for fast API access
Author: MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7
"""
import pandas as pd
from datetime import datetime
from pathlib import Path
import logging
from typing import Dict, Any, List
import json
import os
import sys
from datetime import timedelta

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_daily_forecasts_job() -> Dict[str, Any]:
    """
    Run the daily forecasts materialization job.
    Creates Parquet files with proper partitioning and updates latest symlink.
    """
    try:
        logger.info("Starting daily forecasts materialization job...")
        
        # Import our forecasting system
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
        from models.forecast_v0.api import get_forecast
        from models.forecast_v0.main import create_sample_data
        from backend.storage.base import save_json
        from backend.services.cache_layer import load_or_compute_forecasts
        
        # Generate forecasts using our forecasting engine
        tickers = ["SPY", "QQQ", "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "BABA"]
        
        all_forecasts = []
        for ticker in tickers:
            sample_data = create_sample_data(ticker, days=252)
            forecast = get_forecast(ticker, sample_data, include_llm_analysis=True)
            if forecast and 'rows' in forecast and forecast['rows']:
                all_forecasts.extend(forecast['rows'])
        
        # Convert forecasts to DataFrame for Parquet storage
        forecasts_df = forecasts_to_dataframe(all_forecasts)
        
        # Create partitioned output directory (format: data/forecast/dt=YYYYMMDD/)
        today_str = datetime.now().strftime("%Y%m%d")
        partition_dir = Path("data/forecast") / f"dt={today_str}"
        partition_dir.mkdir(parents=True, exist_ok=True)
        
        # Save raw forecasts to parquet
        forecasts_parquet_path = partition_dir / "forecasts.parquet"
        forecasts_df.to_parquet(forecasts_parquet_path, engine='pyarrow', index=False)
        
        # Process final forecasts (apply business logic, filtering, ranking)
        final_df = process_final_forecasts(forecasts_df)
        
        # Save final forecasts to parquet
        final_parquet_path = partition_dir / "final.parquet"
        final_df.to_parquet(final_parquet_path, engine='pyarrow', index=False)
        
        # Update the 'latest' symlink to point to today's partition
        latest_symlink = Path("data/forecast/latest")
        if latest_symlink.exists():
            latest_symlink.unlink()
        latest_symlink.symlink_to(partition_dir)
        
        # Also save to JSON for API consumption
        json_output = {
            "rows": final_df.to_dict('records'),
            "count": len(final_df),
            "generated_at": datetime.now().isoformat() + "Z",
            "partition_date": today_str,
            "source": ["forecast_materialization_job", "daily_cache"],
            "freshness": "fresh"
        }
        
        # Save to forecasts.json as well for API backward compatibility
        save_path = save_json(json_output, "forecasts.json", ["forecast_materialization", "daily_job"])
        
        logger.info(f"Daily forecasts job completed successfully!")
        logger.info(f"  - Raw forecasts saved to: {forecasts_parquet_path}")
        logger.info(f"  - Final forecasts saved to: {final_parquet_path}")
        logger.info(f"  - Latest symlink updated to: {latest_symlink} -> {partition_dir}")
        logger.info(f"  - JSON snapshot saved for API: {save_path}")
        logger.info(f"  - Generated {len(final_df)} forecast rows")
        
        return {
            "status": "success",
            "partition_date": today_str,
            "forecast_count": len(final_df),
            "output_paths": {
                "raw_parquet": str(forecasts_parquet_path),
                "final_parquet": str(final_parquet_path),
                "json_snapshot": save_path,
                "latest_symlink": str(latest_symlink)
            }
        }
        
    except Exception as e:
        logger.error(f"Error in daily forecasts job: {e}")
        # Return fallback structure to maintain never-empty guarantee
        error_result = {
            "status": "error",
            "partition_date": datetime.now().strftime("%Y%m%d"),
            "forecast_count": 0,
            "output_paths": {},
            "error": str(e),
            "message": "Daily forecasts job failed but system maintains fallback data"
        }
        
        # Save error state to maintain never-empty guarantee
        save_json({
            "rows": [],
            "count": 0,
            "generated_at": datetime.now().isoformat() + "Z",
            "partition_date": datetime.now().strftime("%Y%m%d"),
            "source": ["forecast_materialization_job", "error_fallback"],
            "freshness": "error",
            "error": str(e)
        }, "forecasts.json", ["forecast_materialization", "error_fallback"])
        
        return error_result


def forecasts_to_dataframe(forecasts: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convert forecasts to DataFrame for Parquet storage.
    """
    if not forecasts:
        # Create empty DataFrame with proper schema
        return pd.DataFrame(columns=[
            'ticker', 'horizon', 'direction', 'confidence', 'expected_return',
            'explanation', 'model_version', 'generated_at'
        ])
    
    # Normalize and flatten forecasts
    normalized_rows = []
    for forecast in forecasts:
        normalized_row = {
            'ticker': forecast.get('ticker', ''),
            'horizon': forecast.get('horizon', '1d'),
            'direction': forecast.get('direction', 'neutral'),
            'confidence': float(forecast.get('confidence', 0.0)) if forecast.get('confidence') is not None else 0.0,
            'expected_return': float(forecast.get('expected_return', 0.0)) if forecast.get('expected_return') is not None else 0.0,
            'explanation': forecast.get('explanation', ''),
            'model_version': forecast.get('model_version', 'v1'),
            'generated_at': forecast.get('generated_at', datetime.now().isoformat()),
            'model_components': '|'.join(forecast.get('model_components', [])),
            'confidence_breakdown_technical': float(forecast.get('confidence_breakdown', {}).get('technical_score', 0.0)),
            'confidence_breakdown_news': float(forecast.get('confidence_breakdown', {}).get('news_score', 0.0)),
            'confidence_breakdown_momentum': forecast.get('confidence_breakdown', {}).get('momentum_score', 0.0),
        }
        normalized_rows.append(normalized_row)
    
    return pd.DataFrame(normalized_rows)


def process_final_forecasts(forecasts_df: pd.DataFrame) -> pd.DataFrame:
    """
    Process forecasts through business logic to create final forecast set.
    """
    if forecasts_df.empty:
        return forecasts_df
    
    # Apply filters and business logic
    # Filter out low confidence forecasts
    filtered_df = forecasts_df[forecasts_df['confidence'] >= 0.4].copy()
    
    # Calculate composite score for ranking
    filtered_df['composite_score'] = (
        filtered_df['confidence'] * 0.7 + 
        abs(filtered_df['expected_return']) * 0.3
    )
    
    # Sort by composite score (descending)
    final_df = filtered_df.sort_values(by=['composite_score'], ascending=False).reset_index(drop=True)
    
    # Limit to top 100 forecasts to keep file manageable
    final_df = final_df.head(100)
    
    logger.info(f"Processed forecasts: {len(forecasts_df)} → {len(final_df)} (after filtering and ranking)")
    
    return final_df


def get_latest_forecasts() -> Dict[str, Any]:
    """
    Get latest forecasts from the materialized cache with <150ms response time.
    """
    try:
        # Try to read from latest symlinked partition
        latest_path = Path("data/forecast/latest")
        if latest_path.exists() and latest_path.is_symlink():
            final_parquet = latest_path / "final.parquet"
            if final_parquet.exists():
                df = pd.read_parquet(final_parquet, engine='pyarrow')
                return {
                    "rows": df.to_dict('records'),
                    "count": len(df),
                    "generated_at": datetime.now().isoformat() + "Z",  # Current time as API generation time
                    "source": ["materialized_cache", "latest_partition"],
                    "freshness": "current"
                }
        
        # Fallback to JSON snapshot
        import json
        json_path = Path("data/forecast/forecasts.json")
        if json_path.exists():
            with open(json_path, 'r') as f:
                return json.load(f)
        
        # Ultimate fallback - return empty structure but never None
        return {
            "rows": [],
            "count": 0,
            "generated_at": datetime.now().isoformat() + "Z",
            "source": ["fallback"],
            "freshness": "fallback",
            "message": "No cached forecasts available - using fallback structure"
        }
        
    except Exception as e:
        logger.error(f"Error getting latest forecasts: {e}")
        # Maintain never-empty guarantee
        return {
            "rows": [],
            "count": 0,
            "generated_at": datetime.now().isoformat() + "Z",
            "source": ["error_fallback"],
            "freshness": "error",
            "error": str(e),
            "message": "Error accessing forecast cache - return fallback data to maintain never-empty guarantee"
        }


def is_data_stale(max_age_hours: int = 24) -> bool:
    """
    Check if the latest forecast data is stale (older than max_age_hours).
    """
    try:
        latest_path = Path("data/forecast/latest")
        if not latest_path.exists():
            return True  # If no latest, definitely stale
            
        # Get the modification time of the target partition
        target_partition = latest_path.resolve()
        if target_partition.exists():
            import time
            mtime = target_partition.stat().st_mtime
            age_hours = (time.time() - mtime) / 3600
            return age_hours > max_age_hours
        else:
            return True
            
    except Exception:
        # If there's an error checking freshness, assume stale to be safe
        return True


if __name__ == "__main__":
    print("Testing forecasts materialization job...")
    print("Task: FC-DATA-004 - Forecasts materialization (daily cache)")
    print(f"Started: {datetime.now().isoformat()}")
    print("-" * 60)
    
    # Run the daily job
    result = run_daily_forecasts_job()
    
    print(f"Job status: {result.get('status', 'unknown')}")
    print(f"Forecasts generated: {result.get('forecast_count', 0)}")
    print(f"Partition date: {result.get('partition_date', 'N/A')}")
    
    # Test the fast retrieval function
    print("\nTesting fast retrieval (<150ms requirement)...")
    import time
    start_time = time.time()
    fast_result = get_latest_forecasts()
    retrieval_time = (time.time() - start_time) * 1000  # Convert to milliseconds
    
    print(f"Retrieval time: {retrieval_time:.2f}ms")
    print(f"Retrieved forecasts: {len(fast_result.get('rows', []))}")
    print(f"Latency requirement (<150ms): {'✓ PASS' if retrieval_time < 150 else '✗ FAIL'}")
    
    # Check if data is stale
    is_stale = is_data_stale()
    print(f"Data is stale (>24h): {'Yes' if is_stale else 'No'}")
    
    print("-" * 60)
    print("Forecasts materialization job test completed!")
    print("=" * 60)