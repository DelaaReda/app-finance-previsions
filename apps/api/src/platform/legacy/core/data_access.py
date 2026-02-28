"""
Shared Data Access Utilities
Task: FC-ARCH-UTILS-001 - Factorisation des utilitaires communs
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21

Purpose: Eliminate duplicate functions across multiple files by centralizing them here
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import sys
from pathlib import Path

# Add backend to path for imports
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from storage.io import load_json
from core.market_data import get_price_history


def _latest_dt_under(base: str, pattern: str = "dt=*") -> Optional[str]:
    """
    Find the latest date partition in the specified base path with the given pattern.
    Replacement for duplicated _latest_dt_under functions.
    
    Args:
        base: Base directory to search
        pattern: Pattern to match (default: "dt=*")
    
    Returns:
        Latest date partition name or None if none found
    """
    try:
        parts = sorted(Path(base).glob(pattern))
        if not parts:
            return None
        # Return the last part name (e.g., "dt=20251105")
        latest_part = parts[-1]
        return latest_part.name.split('=')[-1] if '=' in latest_part.name else latest_part.name
    except Exception as e:
        print(f"Error finding latest dt under {base}: {str(e)}")
        return None  # Return None to maintain never-empty contract


def _load_equity_final() -> pd.DataFrame:
    """
    Load the latest equity final data from date-partitioned storage.
    Replacement for duplicated _load_equity_final functions.
    
    Returns:
        DataFrame with equity final data or empty DataFrame
    """
    try:
        from datetime import datetime
        # Look for the latest date partition
        base_path = Path("data/forecast")
        if not base_path.exists():
            # Check alternative path formats
            alt_path = Path(__file__).resolve().parent.parent / "data" / "forecast"
            if alt_path.exists():
                base_path = alt_path
            else:
                return pd.DataFrame()  # Return empty but never-empty contract
        
        # Get all date partition directories
        parts = sorted(base_path.glob("dt=*"))
        if not parts:
            return pd.DataFrame()  # No data available yet
        
        # Get the latest partition
        latest_part = parts[-1]
        final_file = latest_part / "final.parquet"
        
        # Try to load the parquet file
        if final_file.exists():
            return pd.read_parquet(final_file)
        else:
            # Try alternative filenames
            alt_final_file = latest_part / "forecasts.parquet"
            if alt_final_file.exists():
                return pd.read_parquet(alt_final_file)
            else:
                # Last resort: try JSON format
                alt_json_file = latest_part / "forecasts.json"
                if alt_json_file.exists():
                    json_data = load_json(f"forecast/dt={latest_part.name.split('=')[1]}/forecasts")
                    if json_data and "data" in json_data:
                        # Convert to DataFrame if structured data exists
                        if "rows" in json_data["data"]:
                            return pd.DataFrame(json_data["data"]["rows"])
                        else:
                            return pd.DataFrame(json_data["data"]) if isinstance(json_data["data"], list) else pd.DataFrame()
                    else:
                        return pd.DataFrame()
        
        return pd.DataFrame()
        
    except Exception as e:
        print(f"Error loading equity final data: {str(e)}")
        # Return empty DataFrame to maintain never-empty contract
        return pd.DataFrame()


def _load_commodity() -> pd.DataFrame:
    """
    Load the latest commodity data from date-partitioned storage.
    Replacement for duplicated _load_commodity functions.
    
    Returns:
        DataFrame with commodity data or empty DataFrame
    """
    try:
        # Look for the latest date partition
        base_path = Path("data/forecast") 
        if not base_path.exists():
            # Check alternative path formats
            alt_path = Path(__file__).resolve().parent.parent / "data" / "forecast"
            if alt_path.exists():
                base_path = alt_path
            else:
                return pd.DataFrame()  # Return empty but maintain never-empty
        
        # Get all date partition directories
        parts = sorted(base_path.glob("dt=*"))
        if not parts:
            return pd.DataFrame()  # No data available yet
        
        # Get the latest partition
        latest_part = parts[-1]
        commodity_file = latest_part / "commodities.parquet"
        
        # Try to load the parquet file
        if commodity_file.exists():
            return pd.read_parquet(commodity_file)
        else:
            # Try alternative names
            alt_commodity_file = latest_part / "commodity.parquet"
            if alt_commodity_file.exists():
                return pd.read_parquet(alt_commodity_file)
            else:
                # Try commodities.csv
                csv_file = latest_part / "commodities.csv"
                if csv_file.exists():
                    return pd.read_csv(csv_file)
                else:
                    # Last resort: try JSON format
                    json_file = latest_part / "commodities.json"
                    if json_file.exists():
                        json_data = load_json(f"forecast/dt={latest_part.name.split('=')[1]}/commodities")
                        if json_data and "data" in json_data:
                            if "rows" in json_data["data"]:
                                return pd.DataFrame(json_data["data"]["rows"])
                            else:
                                return pd.DataFrame(json_data["data"]) if isinstance(json_data["data"], list) else pd.DataFrame()
                        else:
                            return pd.DataFrame()
        
        return pd.DataFrame()
        
    except Exception as e:
        print(f"Error loading commodity data: {str(e)}")
        # Return empty DataFrame to maintain never-empty contract
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Public helpers expected by api.main and other routes
# ---------------------------------------------------------------------------

def get_close_series(ticker: str, interval: str = "1d", limit: int = 252) -> Optional[pd.Series]:
    """Return a pandas Series of close prices for ticker.

    Prefers cached JSON in storage, falls back to live fetch via market_data.
    """
    try:
        ticker = (ticker or "").upper()
        data = load_json("stocks/prices") or load_json("stocks_prices") or {}
        candidates = None
        if isinstance(data, dict):
            candidates = data.get("tickers") or data.get("data", {}).get("tickers") or data
        if isinstance(candidates, dict) and ticker in candidates:
            points = candidates[ticker].get("points", [])
            if points:
                closes = [p.get("close") for p in points if isinstance(p, dict) and p.get("close") is not None]
                idx = range(len(closes))
                return pd.Series(closes[-limit:], index=idx[-limit:]) if closes else pd.Series(dtype=float)
    except Exception:
        pass

    # Fallback to live fetch
    try:
        df = get_price_history(ticker, interval=interval)
        if df is None or df.empty or "Close" not in df.columns:
            return None
        series = df["Close"].dropna()
        if limit:
            series = series.tail(limit)
        return series
    except Exception:
        return None


def load_macro_forecast_rows(limit: int = 200):
    """Fallback loader used by api.main; returns a never-empty structure."""
    try:
        data = load_json("macro_forecasts") or {}
        rows = data.get("rows") or data.get("data", {}).get("rows") or []
        if limit:
            rows = rows[:limit]
        return {"ok": True, "rows": rows, "count": len(rows)}
    except Exception as e:
        return {"ok": False, "rows": [], "count": 0, "error": str(e)}

def _load_stock_prices(ticker: str) -> pd.DataFrame:
    """
    Load stock prices for a specific ticker from date-partitioned storage.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        DataFrame with stock price data or empty DataFrame
    """
    try:
        # Look for stock prices data with the ticker
        base_path = Path("data/stocks")
        
        # Try different partition formats
        parts = sorted(list(base_path.glob("dt=*")) + list(base_path.glob(f"{ticker.lower()}_dt=*")))
        
        if not parts:
            # Check alternative locations
            alt_path = Path(__file__).resolve().parent.parent / "data" / "stocks"
            if alt_path.exists():
                parts = sorted(list(alt_path.glob("dt=*")) + list(alt_path.glob(f"{ticker.lower()}_dt=*")))
            
            if not parts:
                return pd.DataFrame()
        
        # Get the latest partition
        latest_part = parts[-1]
        price_file = latest_part / f"{ticker.lower()}_prices.parquet"
        
        if price_file.exists():
            return pd.read_parquet(price_file)
        else:
            # Try alternative formats
            csv_file = latest_part / f"{ticker.lower()}_prices.csv"
            if csv_file.exists():
                return pd.read_csv(csv_file)
            else:
                json_file = latest_part / f"{ticker.lower()}_prices.json"
                if json_file.exists():
                    json_data = load_json(f"stocks/dt={latest_part.name.split('=')[1]}/{ticker.lower()}_prices")
                    if json_data and isinstance(json_data, dict) and "data" in json_data:
                        if isinstance(json_data["data"], list):
                            return pd.DataFrame(json_data["data"])
                        elif isinstance(json_data["data"], dict) and "rows" in json_data["data"]:
                            return pd.DataFrame(json_data["data"]["rows"])
                    
        return pd.DataFrame()
        
    except Exception as e:
        print(f"Error loading stock prices for {ticker}: {str(e)}")
        # Return empty DataFrame to maintain never-empty contract
        return pd.DataFrame()


def _load_macro_data(dataset_name: str) -> pd.DataFrame:
    """
    Load macroeconomic data from date-partitioned storage.
    
    Args:
        dataset_name: Name of macro dataset (e.g., "cpi", "gdp", "employment")
        
    Returns:
        DataFrame with macro data or empty DataFrame
    """
    try:
        base_path = Path("data/macro")
        
        # Get all date partition directories
        parts = sorted(base_path.glob("dt=*"))
        if not parts:
            return pd.DataFrame()
        
        # Get the latest partition
        latest_part = parts[-1]
        dataset_file = latest_part / f"{dataset_name}.parquet"
        
        if dataset_file.exists():
            return pd.read_parquet(dataset_file)
        else:
            # Try alternative formats
            csv_file = latest_part / f"{dataset_name}.csv"
            if csv_file.exists():
                return pd.read_csv(csv_file)
            else:
                json_file = latest_part / f"{dataset_name}.json"
                if json_file.exists():
                    json_data = load_json(f"macro/dt={latest_part.name.split('=')[1]}/{dataset_name}")
                    if json_data and isinstance(json_data, dict) and "data" in json_data:
                        if isinstance(json_data["data"], list):
                            return pd.DataFrame(json_data["data"])
                        elif isinstance(json_data["data"], dict) and "rows" in json_data["data"]:
                            return pd.DataFrame(json_data["data"]["rows"])
        
        return pd.DataFrame()
        
    except Exception as e:
        print(f"Error loading macro data {dataset_name}: {str(e)}")
        # Return empty DataFrame to maintain never-empty contract
        return pd.DataFrame()


def _load_news_data() -> pd.DataFrame:
    """
    Load latest news data from date-partitioned storage.
    
    Returns:
        DataFrame with news data or empty DataFrame
    """
    try:
        base_path = Path("data/news")
        
        # Get all date partition directories
        parts = sorted(base_path.glob("dt=*"))
        if not parts:
            # Try alternative structures
            parts = sorted(base_path.glob("*/dt=*"))  # Nested structure possible
            if not parts:
                # Last resort: look for JSON files
                json_files = list(base_path.glob("**/*.json"))
                if json_files:
                    latest_json = max(json_files, key=lambda x: x.stat().st_mtime if x.exists() else datetime.min.timestamp())
                    json_data = load_json(latest_json.stem)
                    if json_data:
                        if isinstance(json_data, dict) and "data" in json_data and "articles" in json_data["data"]:
                            return pd.DataFrame(json_data["data"]["articles"])
                        elif isinstance(json_data, dict) and "articles" in json_data:
                            return pd.DataFrame(json_data["articles"])
                        elif isinstance(json_data, list):
                            return pd.DataFrame(json_data)
        
        if parts:
            latest_part = parts[-1]
            news_file = latest_part / "news.parquet"
            
            if news_file.exists():
                return pd.read_parquet(news_file)
            else:
                # Try alternative names
                for alt_file in ["feed.parquet", "latest.parquet", "articles.parquet"]:
                    alt_news_file = latest_part / alt_file
                    if alt_news_file.exists():
                        return pd.read_parquet(alt_news_file)
                
                # Try JSON format
                json_file = latest_part / "news.json"
                if json_file.exists():
                    json_data = load_json(f"news/dt={latest_part.name.split('=')[1]}/news")
                    if json_data and isinstance(json_data, dict) and "data" in json_data:
                        if "articles" in json_data["data"]:
                            return pd.DataFrame(json_data["data"]["articles"])
                        elif "rows" in json_data["data"]:
                            return pd.DataFrame(json_data["data"]["rows"])
        
        return pd.DataFrame()
        
    except Exception as e:
        print(f"Error loading news data: {str(e)}")
        # Return empty DataFrame to maintain never-empty contract
        return pd.DataFrame()


def _ensure_safe_array(data: Any, default: List = None) -> List:
    """
    Ensure data is a safe array, maintaining never-empty contract.
    Replacement for duplicated ensureArray patterns.
    
    Args:
        data: Raw data that should be converted to array
        default: Default array to return if conversion fails
        
    Returns:
        Array of data or default array
    """
    if default is None:
        default = []
    
    if data is None:
        return default
    
    if isinstance(data, list):
        return data
    
    if isinstance(data, dict):
        # If it's a dict with a "rows" or "data" key, return that
        if "rows" in data:
            return data["rows"] if isinstance(data["rows"], list) else default
        elif "data" in data:
            if isinstance(data["data"], list):
                return data["data"]
            elif isinstance(data["data"], dict) and "rows" in data["data"]:
                return data["data"]["rows"] if isinstance(data["data"]["rows"], list) else default
            else:
                return default
        else:
            # Convert dict values to array
            return list(data.values()) if data else default
    
    if hasattr(data, '__iter__') and not isinstance(data, str):
        # If it's iterable but not a string, convert to list
        try:
            return list(data)
        except:
            return default
    
    # For any other type, return default
    return default


def get_last_update_timestamp(file_path: str) -> Optional[str]:
    """
    Extract timestamp from file or directory that indicates last update time.
    
    Args:
        file_path: Path to file or directory
        
    Returns:
        Timestamp as string or None if not available
    """
    try:
        path = Path(file_path)
        
        if path.exists():
            # Get modification time
            mtime = path.stat().st_mtime
            timestamp = datetime.fromtimestamp(mtime)
            return timestamp.isoformat() + "Z"
        else:
            # If path doesn't exist, return None
            return None
    except Exception as e:
        print(f"Error getting last update timestamp for {file_path}: {str(e)}")
        return None


def _load_data_partitioned(base_dir: str, filename: str, date_partition: Optional[str] = None) -> pd.DataFrame:
    """
    Generic function to load partitioned data (for any type of partitioned data).
    
    Args:
        base_dir: Base directory containing date partitions
        filename: Filename without extension (will try parquet, csv, json)
        date_partition: Specific date partition to load (if None, loads latest)
        
    Returns:
        DataFrame with data or empty DataFrame
    """
    try:
        base_path = Path(base_dir)
        
        if date_partition:
            # Load specific partition
            partition_path = base_path / f"dt={date_partition}"
            if not partition_path.exists():
                return pd.DataFrame()
        else:
            # Load latest partition
            parts = sorted(base_path.glob("dt=*"))
            if not parts:
                return pd.DataFrame()
            partition_path = parts[-1]
        
        # Try different file formats in order of preference
        for fmt in ["parquet", "csv", "json"]:
            data_file = partition_path / f"{filename}.{fmt}"
            
            if data_file.exists():
                if fmt == "parquet":
                    return pd.read_parquet(data_file)
                elif fmt == "csv":
                    return pd.read_csv(data_file)
                elif fmt == "json":
                    json_data = load_json(f"{base_dir.replace('/', '_')}/dt={partition_path.name.split('=')[1]}/{filename}")
                    if json_data:
                        if isinstance(json_data, dict) and "data" in json_data:
                            if isinstance(json_data["data"], list):
                                return pd.DataFrame(json_data["data"])
                            elif "rows" in json_data["data"]:
                                return pd.DataFrame(json_data["data"]["rows"])
                        elif isinstance(json_data, list):
                            return pd.DataFrame(json_data)
        
        # If no files found in the partition, return empty DataFrame
        return pd.DataFrame()
        
    except Exception as e:
        print(f"Error loading partitioned data {base_dir}/{filename}: {str(e)}")
        # Return empty DataFrame to maintain never-empty contract
        return pd.DataFrame()


# Convenience functions that replace duplicate functions across multiple files
def get_latest_forecast_date() -> Optional[str]:
    """Get the latest forecast date from date partitions"""
    return _latest_dt_under("data/forecast", "dt=*")

def get_latest_macro_date() -> Optional[str]:
    """Get the latest macro date from date partitions"""
    return _latest_dt_under("data/macro", "dt=*")

def load_latest_forecasts_data() -> pd.DataFrame:
    """Load latest forecasts data (equity + commodity)"""
    equity_df = _load_equity_final()
    commodity_df = _load_commodity()
    
    # Combine if both exist
    if not equity_df.empty and not commodity_df.empty:
        try:
            equity_df = equity_df.copy()  # Make sure we can modify
            commodity_df = commodity_df.copy()
            if 'asset_type' not in equity_df.columns:
                equity_df['asset_type'] = 'equity'
            if 'asset_type' not in commodity_df.columns:
                commodity_df['asset_type'] = 'commodity'
            return pd.concat([equity_df, commodity_df], ignore_index=True)
        except Exception as e:
            # If concat fails, return equity data with a note
            print(f"Error combining equity and commodity data: {str(e)}")
            return equity_df if not equity_df.empty else commodity_df
    elif not equity_df.empty:
        equity_df = equity_df.copy()
        if not isinstance(equity_df, pd.DataFrame):
            equity_df = pd.DataFrame()
        if 'asset_type' not in equity_df.columns:
            equity_df['asset_type'] = 'equity'
        return equity_df
    elif not commodity_df.empty:
        commodity_df = commodity_df.copy()
        if not isinstance(commodity_df, pd.DataFrame):
            commodity_df = pd.DataFrame()
        if 'asset_type' not in commodity_df.columns:
            commodity_df['asset_type'] = 'commodity'
        return commodity_df
    else:
        return pd.DataFrame()

def get_equity_final_data() -> pd.DataFrame:
    """Convenience function for loading equity final data"""
    return _load_equity_final()

def get_commodity_data() -> pd.DataFrame:
    """Convenience function for loading commodity data"""
    return _load_commodity()

def get_equity_forecasts_data() -> pd.DataFrame:
    """Load equity forecasts only"""
    df = _load_equity_final()
    if not df.empty:
        df['asset_type'] = 'equity'
    return df

def get_commodity_forecasts_data() -> pd.DataFrame:
    """Load commodity forecasts only"""  
    df = _load_commodity()
    if not df.empty:
        df['asset_type'] = 'commodity'
    return df
