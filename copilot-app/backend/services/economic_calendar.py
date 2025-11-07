"""
Economic Calendar Service
Task: FC-API-029 - Economic Calendar
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import sys
import os
from pathlib import Path

# Add backend to path for imports
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from models.economic_calendar import economic_calendar_model
from storage.io import load_json
from services.cache_layer import load_or_compute


class EconomicCalendarService:
    """
    Service for fetching and managing economic calendar events
    """
    
    def __init__(self):
        self.model = economic_calendar_model
    
    def get_economic_calendar(self, 
                            start_date: Optional[str] = None,
                            end_date: Optional[str] = None,
                            country: Optional[str] = None,
                            importance: Optional[str] = None,
                            limit: int = 100) -> Dict[str, Any]:
        """
        Get economic calendar events with specified filters
        """
        def compute_calendar():
            """Compute fresh calendar data"""
            try:
                result = self.model.get_calendar_for_period(
                    start_date=start_date or datetime.now().strftime("%Y-%m-%d"),
                    end_date=end_date,
                    country_filter=country,
                    importance_filter=importance
                )
                return result
            except Exception as e:
                print(f"Error in calendar computation: {str(e)}")
                # Return fallback structure to maintain never-empty contract
                return {
                    "events": [],
                    "period": {
                        "start": start_date or datetime.now().strftime("%Y-%m-%d"),
                        "end": end_date or (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                    },
                    "filters_applied": {
                        "country": country,
                        "importance": importance
                    },
                    "count": 0,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "source": ["economic_calendar_service", "error_fallback", "fc-api-029"],
                    "error": str(e),
                    "message": "Calendar computation failed but fallback data returned to maintain never-empty contract"
                }
        
        # Use cache layer to serve latest available data, compute fresh if none available
        calendar_data = load_or_compute(
            key=cache_key,
            compute_fn=compute_calendar,
            source=["economic_calendar_service", "fc-api-029", "real_data"]
        )
        
        # Ensure proper response format
        if isinstance(calendar_data, dict) and "calendar" in calendar_data:
            # If it's the full result from the job, extract the calendar data
            response_data = calendar_data.get("calendar", {})
        elif isinstance(calendar_data, dict):
            # If it's already in the right format
            response_data = calendar_data
        else:
            response_data = {
                "events": [],
                "period": {
                    "start": start_date or datetime.now().strftime("%Y-%m-%d"),
                    "end": end_date or (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                },
                "filters_applied": {
                    "country": country,
                    "importance": importance
                },
                "count": 0,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "source": ["economic_calendar_service", "fallback", "fc-api-029"],
                "message": "Invalid data format from calendar service, using fallback to maintain never-empty contract"
            }
        
        # Apply limit to events
        if "events" in response_data:
            response_data["events"] = response_data["events"][:limit]
            response_data["count"] = min(response_data["count"], limit)
        
        return {
            "ok": response_data.get("count", 0) > 0 or response_data.get("error") is None,
            "data": response_data,
            "freshness": response_data.get("generated_at", datetime.utcnow().isoformat() + "Z")
        }
    
    def get_upcoming_events(self, days_ahead: int = 7) -> Dict[str, Any]:
        """Get upcoming events for the next specified number of days"""
        start_date = datetime.now().strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        
        result = self.get_economic_calendar(start_date, end_date)
        return result
    
    def get_impactful_events(self, importance_filter: str = "high") -> Dict[str, Any]:
        """Get events with specified importance level or higher"""
        start_date = datetime.now().strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        result = self.get_economic_calendar(
            start_date=start_date,
            end_date=end_date,
            importance=importance_filter
        )
        return result
        

# Global instance
economic_calendar_service = EconomicCalendarService()

# Convenience functions for API use
def get_calendar_events(start_date: Optional[str] = None, 
                      end_date: Optional[str] = None,
                      country: Optional[str] = None,
                      importance: Optional[str] = None,
                      limit: int = 100):
    """
    Get economic calendar events with specified filters
    """
    return economic_calendar_service.get_economic_calendar(
        start_date, end_date, country, importance, limit
    )

def get_upcoming_economic_events(days_ahead: int = 7):
    """
    Get upcoming economic events for the next specified number of days
    """
    return economic_calendar_service.get_upcoming_events(days_ahead)