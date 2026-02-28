"""
Update Monitor Job - Monitor data freshness and update cycles
Part of Finance Copilot Architecture Enhancement Initiative

Implements data freshness monitoring job that checks for stale data and ensures timely updates
"""
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, List
import pandas as pd
import os
from pathlib import Path

logger = logging.getLogger(__name__)

def run_update_monitor_job(filters: Dict = None) -> Dict[str, Any]:
    """
    Main function to run data freshness monitoring job
    Checks for stale data and ensures timely updates across all data sources
    """
    logger.info("Starting update monitor job...")
    
    try:
        # Define data sources to check
        data_sources = [
            {"name": "forecasts", "path": "data/forecasts.json", "max_age_hours": 24},
            {"name": "market_data", "path": "data/market_data.parquet", "max_age_hours": 1}, 
            {"name": "news_sentiment", "path": "data/news_sentiment.json", "max_age_hours": 2},
            {"name": "macro_data", "path": "data/macro.json", "max_age_hours": 6},
            {"name": "leads", "path": "data/leads.json", "max_age_hours": 24}
        ]
        
        freshness_checks = []  # Initialize the variable
        needs_refresh = []
        
        for source in data_sources:
            data_path = Path(source["path"])
            if data_path.exists():
                # Get file modification time
                mod_time = datetime.fromtimestamp(data_path.stat().st_mtime)
                age_hours = (datetime.now() - mod_time).total_seconds() / 3600
                
                is_fresh = age_hours <= source["max_age_hours"]
                
                check_result = {
                    "source": source["name"],
                    "path": str(data_path),
                    "modified_at": mod_time.isoformat(),
                    "age_hours": round(age_hours, 2),
                    "max_age_allowed": source["max_age_hours"],
                    "fresh": is_fresh,
                    "needs_refresh": not is_fresh
                }
                
                if not is_fresh:
                    needs_refresh.append(check_result)
            else:
                check_result = {
                    "source": source["name"],
                    "path": str(data_path),
                    "modified_at": "never",
                    "age_hours": 9999,
                    "max_age_allowed": source["max_age_hours"],
                    "fresh": False,
                    "needs_refresh": True
                }
                needs_refresh.append(check_result)
            
            freshness_checks.append(check_result)
        
        # Generate recommendations
        recommendations = []
        if needs_refresh:
            for item in needs_refresh:
                recommendations.append(f"Run {item['source']}_job to refresh stale data (last update: {item['age_hours']}h ago)")
        
        result = {
            "checks_performed": len(freshness_checks),
            "stale_sources": len(needs_refresh),
            "sources_checked": freshness_checks,
            "requires_action": len(needs_refresh) > 0,
            "recommendations": recommendations,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "completed",
            "source": ["update_monitor", "data_quality", "freshness_checker"]
        }
        
        logger.info(f"✅ Update monitor job completed. Found {len(needs_refresh)} stale data sources.")
        return result
        
    except Exception as e:
        logger.error(f"Update monitor job failed: {str(e)}", exc_info=True)
        return {
            "checks_performed": 0,
            "stale_sources": 0,
            "sources_checked": [],
            "requires_action": False,
            "recommendations": ["Manual check required: " + str(e)],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "failed",
            "error": str(e)
        }