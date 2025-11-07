"""
Economic Calendar API Route - Endpoints for economic events
Task: FC-API-029 - Economic Calendar
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from fastapi import APIRouter, Query
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from backend.services.cache_layer import load_or_compute
from backend.storage.io import load_json

router = APIRouter(prefix="/api", tags=["macro"])

@router.get("/macro/calendar")
async def economic_calendar(
    start_date: Optional[str] = Query(None, description="Date de début (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    country: Optional[str] = Query(None, description="Filtre par pays (US, EU, JP, etc.)"),
    importance: Optional[str] = Query(None, description="Filtre par importance (low, medium, high)"),
    limit: int = Query(100, ge=1, le=500, description="Limite maximale d'événements à retourner")
):
    """
    Get economic calendar events with impact predictions.
    Implements never-empty contract by serving cached/latest data if live computation fails.
    """
    def compute_economic_calendar():
        """Compute fresh economic calendar data"""
        try:
            # Try to get fresh data from the economic calendar model
            from ..models.economic_calendar import economic_calendar_model
            start = start_date or datetime.now().strftime("%Y-%m-%d")
            result = economic_calendar_model.get_calendar_for_period(
                start_date=start,
                end_date=end_date,
                country_filter=country,
                importance_filter=importance
            )
            return result
        except Exception as e:
            # Fallback to ensure never-empty contract
            print(f"Error in economic calendar computation: {str(e)}")
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
                "source": ["economic_calendar_route", "error_fallback", "fc-api-029"],
                "error": str(e),
                "message": "Economic calendar computation failed, but fallback data returned to maintain never-empty contract"
            }
    
    # Use cache layer to serve latest available data or compute fresh if none available
    calendar_data = load_or_compute(
        key=f"economic_calendar_{start_date or 'current'}_{end_date or 'default'}_{country or 'all'}_{importance or 'all'}",
        compute_fn=compute_economic_calendar,
        source=["economic_calendar_endpoint", "live_calculation", "fc-api-029"]
    )
    
    # Ensure the response structure is correct
    if isinstance(calendar_data, dict) and "calendar" in calendar_data:
        # If it's the full result from the job, extract the calendar data
        response_data = calendar_data["calendar"]
    elif isinstance(calendar_data, dict):
        # If it's already just the calendar data
        response_data = calendar_data
    else:
        # Fallback if response is not a dictionary
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
            "source": ["economic_calendar_route", "fallback", "fc-api-029"],
            "message": "Invalid data format returned from economic calendar service, using fallback to maintain never-empty contract"
        }
    
    # Apply limit to the events
    if "events" in response_data:
        response_data["events"] = response_data["events"][:limit]
        response_data["count"] = min(response_data["count"], limit)
    
    # Return with proper API envelope
    return {
        "ok": True,
        "data": response_data,
        "freshness": response_data.get("generated_at", datetime.utcnow().isoformat() + "Z")
    }


if __name__ == "__main__":
    # This is only for testing the route logic
    print("Route economic calendar loaded successfully")
    print("Provides /api/macro/calendar endpoint")
    print("Task: FC-API-029 - Economic Calendar")