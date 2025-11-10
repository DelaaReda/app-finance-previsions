"""
Core Data Access Utilities for Finance Copilot
Task: FC-ARCH-UTILS-001 - Factorisation des utilitaires communs
Author: MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7
"""
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from datetime import datetime, timedelta
import sys
import json
import pandas as pd
from enum import Enum


def ensure_array(v: Union[List, str, Dict, None]) -> List:
    """
    Ensure a value is always returned as an array.
    Implements never-empty principle by returning [] instead of None/list.
    
    Args:
        v: Value to convert to array (can be any type)
        
    Returns:
        List: Original value if it's an array, else converted to single-element array or empty array
    """
    if v is None:
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        # If it's a string, treat as single element or split if it looks like CSV
        if ',' in v and len(v.split(',')) > 1:
            return [x.strip() for x in v.split(',') if x.strip()]
        return [v]
    if isinstance(v, dict):
        # If it's a dict, return as single element in array
        return [v]
    # For any other type, return as single element in array
    return [v]


def nn(v: Union[Any, None], fb: Any = 0) -> Any:
    """
    Not-Null utility - returns fallback value if input is null/undefined.
    Implements safe access pattern for optional values.
    
    Args:
        v: Value that may be None
        fb: Fallback value to return if v is None (default: 0)
        
    Returns:
        Value v if not null, otherwise fallback fb
    """
    return fb if v is None or (isinstance(v, str) and v == "") or (isinstance(v, float) and v != v) else v


def has_items(v: Union[List, str, Dict, None]) -> bool:
    """
    Check if a value has items (non-empty).
    
    Args:
        v: Value to check
        
    Returns:
        Boolean indicating if value contains items
    """
    if v is None:
        return False
    if isinstance(v, list):
        return len(v) > 0
    if isinstance(v, str):
        return len(v.strip()) > 0
    if isinstance(v, dict):
        return len(v.keys()) > 0
    return True


def safe_get(obj: Optional[Dict], key: str, default: Any = None) -> Any:
    """
    Safe property access with fallback.
    
    Args:
        obj: Object to extract property from
        key: Property name to extract
        default: Default value if property doesn't exist
        
    Returns:
        Property value if exists, otherwise default
    """
    if obj is None or not isinstance(obj, dict):
        return default
    return obj.get(key, default)


def parse_csv_list(value: Union[str, List[str], None]) -> List[str]:
    """
    Parse CSV-formatted string or return list as-is.
    
    Args:
        value: String in format "item1,item2,item3" or list of strings
        
    Returns:
        List of strings
    """
    if value is None:
        return []
    
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    
    if isinstance(value, str):
        if ',' in value:
            return [item.strip() for item in value.split(',') if item.strip()]
        else:
            # If no comma, treat as single value
            return [value.strip()] if value.strip() else []
    
    return []


def latest_partition_under(base_path: str, pattern: str = "dt=*") -> Optional[str]:
    """
    Get latest partition under a base path (typically dt=YYYYMMDD format).
    Used for finding latest data in partitioned directories.
    
    Args:
        base_path: Base directory to search in
        pattern: Pattern of partitions (default: "dt=*")
        
    Returns:
        Name of latest partition directory or None if none found
    """
    try:
        p = Path(base_path)
        if not p.exists():
            return None
        
        # Get all directories matching the pattern
        partitions = [part.name for part in p.glob(pattern) if part.is_dir()]
        
        if not partitions:
            return None
        
        # Sort partitions to get the latest one (assuming format dt=20251106)
        # Extract date part and sort
        def extract_date(part_name: str) -> str:
            # Format is dt=YYYYMMDD, extract the date part
            if '=' in part_name:
                return part_name.split('=')[1]
            return part_name
        
        # Sort by date - get latest
        sorted_parts = sorted(partitions, key=extract_date, reverse=True)
        return sorted_parts[0] if sorted_parts else None
        
    except Exception as e:
        print(f"Error finding latest partition: {e}")
        return None


def load_equity_final(ticker: str, horizon: str = "1d", base_path: Optional[str] = None) -> Optional[Dict]:
    """
    Load final equity data for a specific ticker and horizon.
    Looks for data in partitioned format: base_path/dt=*/equity/final.parquet
    
    Args:
        ticker: Stock ticker symbol
        horizon: Forecast horizon (1d, 1w, 1m, etc.) 
        base_path: Base data directory (defaults to backend/data)
        
    Returns:
        Equity final data or None if not found
    """
    try:
        if base_path is None:
            # Default to backend data directory
            backend_root = Path(__file__).resolve().parents[2]  # From src/core/data_access.py to backend/
            base_path = str(backend_root / "data")
        
        base_p = Path(base_path)
        
        # Find latest partition
        latest_part = latest_partition_under(str(base_p))
        if latest_part is None:
            return None
        
        # Look for equity final data in the partition
        equity_final_path = base_p / latest_part / "equity" / "final.parquet"
        
        if not equity_final_path.exists():
            # Alternative location
            equity_final_path = base_p / latest_part / "forecast" / "final.parquet"
            
            if not equity_final_path.exists():
                return None
        
        # Load the parquet file into a dataframe
        try:
            df = pd.read_parquet(equity_final_path)
            
            # Filter for the specific ticker if available in DataFrame
            if 'ticker' in df.columns:
                filtered_df = df[df['ticker'].str.upper() == ticker.upper()].head(1)  # Get first match
                if not filtered_df.empty:
                    # Convert to dict format expected by frontend
                    row = filtered_df.iloc[0].to_dict()
                    return {
                        "data": row,
                        "count": 1,
                        "found_ticker": ticker,
                        "partition": latest_part,
                        "loaded_at": datetime.utcnow().isoformat() + "Z"
                    }
            elif 'symbol' in df.columns:
                filtered_df = df[df['symbol'].str.upper() == ticker.upper()].head(1)  # Get first match
                if not filtered_df.empty:
                    row = filtered_df.iloc[0].to_dict()
                    return {
                        "data": row,
                        "count": 1,
                        "found_ticker": ticker,
                        "partition": latest_part,
                        "loaded_at": datetime.utcnow().isoformat() + "Z"
                    }
            else:
                # If no ticker column found, return first few rows
                if not df.empty:
                    rows = df.head(10).to_dict('records')
                    return {
                        "data": rows,
                        "count": len(rows),
                        "partition": latest_part,
                        "loaded_at": datetime.utcnow().isoformat() + "Z"
                    }
            
            return None
        except Exception as e:
            print(f"Error loading parquet file: {e}")
            return None
            
    except Exception as e:
        print(f"Error loading equity final: {e}")
        return None


def load_macro_forecast_rows(limit: int = 200) -> Dict[str, Any]:
    """
    Load macro forecast rows with standardized return format.
    Implements never-empty principle by providing fallback structure.
    
    Args:
        limit: Maximum number of rows to return (default: 200)
        
    Returns:
        Dictionary with rows and metadata in standardized format
    """
    try:
        from backend.src.utils.file_loader import load_json
        
        # Load macro forecast data
        macro_data = load_json("macro_forecasts")
        
        if macro_data and "rows" in macro_data:
            rows = macro_data["rows"]
            # Apply limit
            limited_rows = rows[:limit]
            return {
                "rows": limited_rows,
                "count": len(limited_rows),
                "limit": limit,
                "source": macro_data.get("source", ["load_macro_forecast_rows"]),
                "generated_at": macro_data.get("generated_at", datetime.utcnow().isoformat() + "Z")
            }
        elif macro_data and isinstance(macro_data, list):
            # If data is directly a list of rows
            limited_rows = macro_data[:limit]
            return {
                "rows": limited_rows,
                "count": len(limited_rows),
                "limit": limit,
                "source": ["load_macro_forecast_rows", "direct_list"],
                "generated_at": datetime.utcnow().isoformat() + "Z"
            }
        else:
            # Return fallback structure to maintain never-empty contract
            return {
                "rows": [],
                "count": 0,
                "limit": limit,
                "source": ["load_macro_forecast_rows", "fallback_empty"],
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "message": "No macro forecast data available - using fallback to maintain never-empty contract"
            }
    except Exception as e:
        print(f"Error in load_macro_forecast_rows: {e}")
        # Return fallback structure to maintain never-empty contract
        return {
            "rows": [],
            "count": 0,
            "limit": limit,
            "source": ["load_macro_forecast_rows", "error_fallback"],
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "error": str(e),
            "message": "Error loading macro forecast rows but fallback returned to maintain never-empty contract"
        }


def load_news_for_ticker(ticker: str, limit: int = 50, since_days: int = 7) -> Dict[str, Any]:
    """
    Load news articles for a specific ticker with time filter.
    
    Args:
        ticker: Stock ticker to filter news for
        limit: Maximum number of articles to return
        since_days: Number of days back to include news
        
    Returns:
        Dictionary with news articles and metadata
    """
    try:
        from backend.src.utils.file_loader import load_json
        
        # Load news data
        news_data = load_json("news_feed")
        
        ticker_upper = ticker.upper()
        
        if news_data:
            articles = news_data.get("articles", news_data.get("rows", []))
            
            # Filter articles by ticker and date range
            filtered_articles = []
            cutoff_date = datetime.utcnow() - timedelta(days=since_days)
            
            for article in articles:
                # Check if ticker is mentioned in the article
                article_tickers = ensure_array(article.get("tickers", []))
                
                # Look for ticker mention in various fields
                if ticker_upper in [t.upper() for t in article_tickers]:
                    # Check date if available
                    pub_date_str = article.get("pubDate") or article.get("published_at") or article.get("date")
                    if pub_date_str:
                        try:
                            pub_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                            if pub_date >= cutoff_date:
                                filtered_articles.append(article)
                        except:
                            # If date parsing fails, include anyway (safety fallback)
                            filtered_articles.append(article)
                    else:
                        # If no date, include anyway (safety fallback)
                        filtered_articles.append(article)
                
                # Also check if ticker is mentioned in title/description
                title = article.get("title", "").upper()
                desc = article.get("description", "").upper()
                
                if ticker.upper() in title or ticker.upper() in desc:
                    # Check date if available
                    pub_date_str = article.get("pubDate") or article.get("published_at") or article.get("date")
                    if pub_date_str:
                        try:
                            pub_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                            if pub_date >= cutoff_date:
                                filtered_articles.append(article)
                        except:
                            filtered_articles.append(article)
                    else:
                        filtered_articles.append(article)
            
            # Apply limit
            limited_articles = filtered_articles[:limit]
            
            return {
                "articles": limited_articles,
                "count": len(limited_articles),
                "limit": limit,
                "ticker": ticker,
                "since_days": since_days,
                "source": ["load_news_for_ticker"],
                "generated_at": datetime.utcnow().isoformat() + "Z"
            }
        else:
            # Return fallback structure to maintain never-empty contract
            return {
                "articles": [],
                "count": 0,
                "limit": limit,
                "ticker": ticker,
                "since_days": since_days,
                "source": ["load_news_for_ticker", "fallback_empty"],
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "message": "No news data available for ticker - using fallback to maintain never-empty contract"
            }
    except Exception as e:
        print(f"Error in load_news_for_ticker: {e}")
        return {
            "articles": [],
            "count": 0,
            "limit": limit,
            "ticker": ticker,
            "since_days": since_days,
            "source": ["load_news_for_ticker", "error_fallback"],
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "error": str(e),
            "message": "Error loading news for ticker but fallback returned to maintain never-empty contract"
        }


def calculate_portfolio_metrics(positions: List[Dict[str, Any]], prices_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Calculate portfolio metrics from positions with optional current prices.
    
    Args:
        positions: List of positions with 'ticker', 'quantity', 'avg_price', etc.
        prices_data: Optional current prices data to calculate current value and PnL
        
    Returns:
        Portfolio metrics including value, returns, risk measures
    """
    try:
        total_cost = 0
        total_current_value = 0
        positions_with_pnl = []
        
        for pos in positions:
            ticker = pos.get('ticker', '').upper()
            quantity = pos.get('quantity', 0)
            avg_price = pos.get('avg_price', 0)
            
            cost_basis = quantity * avg_price
            total_cost += cost_basis
            
            # Get current price if available
            current_price = None
            if prices_data and isinstance(prices_data, dict):
                if ticker in prices_data:
                    current_price = prices_data[ticker]
                elif 'rows' in prices_data or 'data' in prices_data:
                    # If prices_data has rows or data structure
                    data_list = prices_data.get('rows', prices_data.get('data', []))
                    for item in ensure_array(data_list):
                        if item.get('ticker', '').upper() == ticker.upper():
                            current_price = item.get('current_price', item.get('price', None))
                            break
            
            current_value = 0
            pnl = 0
            pnl_pct = 0
            
            if current_price is not None:
                current_value = quantity * current_price
                total_current_value += current_value
                pnl = current_value - cost_basis
                pnl_pct = (pnl / cost_basis) * 100 if cost_basis != 0 else 0
            else:
                # Use avg_price as current price for calculation if unavailable
                current_value = quantity * avg_price
                total_current_value += current_value
                pnl = 0  # No PnL if no current price
                pnl_pct = 0
            
            # Calculate position weight
            weight = (current_value / total_current_value) if total_current_value > 0 else 0
            
            pos_with_metrics = {
                **pos,
                "current_price": current_price,
                "current_value": current_value,
                "cost_basis": cost_basis,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "weight": weight
            }
            positions_with_pnl.append(pos_with_metrics)
        
        # Calculate portfolio-level metrics
        pnl_total = total_current_value - total_cost
        pnl_total_pct = (pnl_total / total_cost) * 100 if total_cost != 0 else 0
        
        return {
            "positions": positions_with_pnl,
            "total_cost": total_cost,
            "total_current_value": total_current_value,
            "total_pnl": pnl_total,
            "total_pnl_pct": pnl_total_pct,
            "count_positions": len(positions_with_pnl),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source": ["calculate_portfolio_metrics"]
        }
    except Exception as e:
        print(f"Error in portfolio metrics calculation: {e}")
        return {
            "positions": [],
            "total_cost": 0,
            "total_current_value": 0,
            "total_pnl": 0,
            "total_pnl_pct": 0,
            "count_positions": 0,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source": ["calculate_portfolio_metrics", "error_fallback"],
            "error": str(e),
            "message": "Error calculating portfolio metrics but fallback returned to maintain never-empty contract"
        }