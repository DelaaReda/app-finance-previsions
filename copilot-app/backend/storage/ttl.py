"""
TTL (Time-To-Live) system for cached data
Task: FC-TTL-001 (+100 pts)
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from datetime import datetime, timedelta
from typing import Dict, Optional

# TTL configuration (in seconds)
TTL_CONFIG = {
    "forecasts": 24 * 3600,        # 24h
    "news_feed": 15 * 60,          # 15 min
    "brief_weekly": 7 * 24 * 3600, # 7 days
    "brief_daily": 24 * 3600,      # 24h
    "alerts": 30 * 60,             # 30 min
    "backtests": 30 * 24 * 3600,   # 30 days
}

def is_fresh(data: Dict, data_type: str) -> bool:
    """
    Check if cached data is still fresh based on TTL

    Args:
        data: The cached data dictionary
        data_type: Type of data (e.g., "forecasts", "news_feed")

    Returns:
        True if data is fresh, False if stale or missing freshness info
    """
    if not data or "freshness" not in data:
        return False

    ttl_seconds = TTL_CONFIG.get(data_type)
    if ttl_seconds is None:
        # Unknown data type, assume stale
        return False

    try:
        # Parse ISO timestamp
        freshness_str = data["freshness"]
        if freshness_str.endswith("Z"):
            freshness_str = freshness_str[:-1] + "+00:00"

        freshness_time = datetime.fromisoformat(freshness_str)
        now = datetime.now(freshness_time.tzinfo) if freshness_time.tzinfo else datetime.now()
        age_seconds = (now - freshness_time).total_seconds()

        return age_seconds < ttl_seconds

    except Exception as e:
        print(f"⚠️  Error parsing freshness timestamp: {e}")
        return False

def get_freshness_metadata(data: Dict, data_type: str) -> Dict:
    """
    Get metadata about data freshness

    Returns:
        {
            "is_fresh": bool,
            "age_seconds": float,
            "ttl_seconds": int,
            "expires_at": str (ISO),
            "status": "fresh" | "stale" | "unknown"
        }
    """
    if not data or "freshness" not in data:
        return {
            "is_fresh": False,
            "age_seconds": None,
            "ttl_seconds": TTL_CONFIG.get(data_type),
            "expires_at": None,
            "status": "unknown"
        }

    ttl_seconds = TTL_CONFIG.get(data_type)

    try:
        freshness_str = data["freshness"]
        if freshness_str.endswith("Z"):
            freshness_str = freshness_str[:-1] + "+00:00"

        freshness_time = datetime.fromisoformat(freshness_str)
        now = datetime.now(freshness_time.tzinfo) if freshness_time.tzinfo else datetime.now()
        age_seconds = (now - freshness_time).total_seconds()

        expires_at = freshness_time + timedelta(seconds=ttl_seconds)
        is_fresh_bool = age_seconds < ttl_seconds

        return {
            "is_fresh": is_fresh_bool,
            "age_seconds": age_seconds,
            "ttl_seconds": ttl_seconds,
            "expires_at": expires_at.isoformat(),
            "status": "fresh" if is_fresh_bool else "stale"
        }

    except Exception as e:
        return {
            "is_fresh": False,
            "age_seconds": None,
            "ttl_seconds": ttl_seconds,
            "expires_at": None,
            "status": "error",
            "error": str(e)
        }