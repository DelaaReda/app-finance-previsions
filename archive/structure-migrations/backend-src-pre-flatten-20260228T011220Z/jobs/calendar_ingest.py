"""
Economic Calendar Job - Fetch and Process Economic Events
Task: FC-API-029 - Economic Calendar
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, List
from pathlib import Path
import sys

# Add backend to path for imports
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from models.economic_calendar import economic_calendar_model
from storage.io import save_json
from services.cache_layer import load_or_compute


def run_economic_calendar_job():
    """
    Fetch and process economic calendar events, save to persistent storage
    """
    print("Starting economic calendar job...")
    print("Task: FC-API-029 - Economic Calendar")
    
    try:
        # Get upcoming economic events for the next 30 days
        start_date = datetime.now().strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        calendar_data = economic_calendar_model.get_calendar_for_period(
            start_date=start_date,
            end_date=end_date
        )
        
        # Add metadata to the calendar data
        enriched_calendar = {
            "calendar": calendar_data,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "job_type": "economic_calendar_job",
            "task_id": "FC-API-029",
            "data_source": ["fred", "external_economic_calendar", "fc-api-029"],
            "next_refresh_estimate": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")  # Next refresh in 24h
        }
        
        # Save to persistent storage
        save_path = save_json("economic_calendar", enriched_calendar, 
                             source=["economic_calendar_job", "fc-api-029", "calendar_data"])
        
        print(f"Economic calendar job completed successfully.")
        print(f"  Events fetched: {calendar_data['count']}")
        print(f"  Period: {calendar_data['period']['start']} to {calendar_data['period']['end']}")
        print(f"  Data saved to: {save_path}")
        
        return enriched_calendar
        
    except Exception as e:
        print(f"Error in economic calendar job: {str(e)}")
        
        # Fallback: ensure never-empty contract is maintained
        fallback_calendar = {
            "calendar": {
                "events": [],
                "period": {"start": datetime.now().strftime("%Y-%m-%d"), "end": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")},
                "filters_applied": {"country": None, "importance": None},
                "count": 0,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "source": ["economic_calendar_job", "error_fallback", "fc-api-029"]
            },
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "job_type": "economic_calendar_job_fallback",
            "task_id": "FC-API-029",
            "data_source": ["error_fallback"],
            "next_refresh_estimate": (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "error": str(e),
            "message": "Economic calendar job failed but fallback data generated to maintain never-empty contract"
        }
        
        # Still save the fallback data to ensure the API endpoint has something to serve
        try:
            save_json("economic_calendar", fallback_calendar, 
                     source=["economic_calendar_job", "error_fallback", "fc-api-029"])
        except:
            pass  # If even saving fallback fails, just return it
        
        print("Fallback calendar data generated to maintain never-empty contract.")
        return fallback_calendar


def populate_economic_calendar_cache():
    """
    Populate the economic calendar cache with real data - implements never-empty contract
    """
    def compute_calendar():
        """
        Compute fresh economic calendar data
        """
        return run_economic_calendar_job()
    
    # Use the cache layer to serve latest available data, compute fresh if none available
    cached_calendar = load_or_compute(
        key="economic_calendar_cache",
        compute_fn=compute_calendar,
        source=["economic_calendar_cache", "fc-api-029", "never_empty_guarantee"]
    )
    
    return cached_calendar


if __name__ == "__main__":
    print("="*60)
    print("ECONOMIC CALENDAR JOB")
    print("Task: FC-API-029 - Economic Calendar")
    print(f"Started: {datetime.now().isoformat()}")
    print("-"*60)
    
    result = run_economic_calendar_job()
    
    print("-"*60)
    print("ECONOMIC CALENDAR JOB COMPLETED")
    if result and "error" not in result:
        print(f"Status: SUCCESS")
        print(f"Events: {result['calendar']['count']}")
        print(f"Period: {result['calendar']['period']['start']} → {result['calendar']['period']['end']}")
    else:
        print(f"Status: FALLBACK (due to error)")
        if result and "error" in result:
            print(f"Error: {result['error']}")
    
    print(f"Generated: {result['generated_at']}")
    print("="*60)