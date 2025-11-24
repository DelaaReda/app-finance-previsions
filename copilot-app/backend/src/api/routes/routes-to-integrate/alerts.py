"""
Alerts API Route - Provides market alerts based on technical signals, news, and forecasts
Extended by: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39 (API-ALERTS-001)
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from backend.core.response import ok, err
from backend.services.cache_layer import load_or_compute
from backend.jobs.alerts import get_latest_alerts
from backend.services.alerts_service import (
    get_alerts_service,
    Alert,
    AlertCondition,
    AlertType,
    AlertStatus
)

router = APIRouter()


# Request/Response models
class AlertCreateRequest(BaseModel):
    """Request body for creating an alert"""
    ticker: str = Field(..., description="Ticker symbol", example="AAPL")
    type: AlertType = Field(..., description="Alert type", example="price")
    condition: AlertCondition = Field(..., description="Alert condition")
    message: str = Field(..., description="Alert message", example="AAPL price above $180")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")


class AlertUpdateRequest(BaseModel):
    """Request body for updating an alert"""
    condition: Optional[AlertCondition] = Field(None, description="New condition")
    message: Optional[str] = Field(None, description="New message")
    status: Optional[AlertStatus] = Field(None, description="New status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="New metadata")


class AlertTestRequest(BaseModel):
    """Request body for testing an alert"""
    test_value: float = Field(..., description="Value to test against condition")


class AlertSnoozeRequest(BaseModel):
    """Request body for snoozing an alert"""
    duration_minutes: int = Field(default=60, ge=1, le=1440, description="Snooze duration in minutes (1-1440)")


@router.get("/alerts")
def alerts():
    """
    Get market alerts with technical signals, news sentiment, and forecast correlation.
    
    Returns alerts ordered by confidence (highest first).
    
    Example response structure:
    {
        "ok": true,
        "data": {
            "alerts": [
                {
                    "id": "oversold-bearish-SPY-20251104123456",
                    "type": "oversold-bearish",
                    "ticker": "SPY",
                    "description": "SPY oversold (RSI: 28.5) with negative sentiment and bearish forecast",
                    "severity": "medium",
                    "confidence": 0.85,
                    "timestamp": "2025-11-04T12:34:56.789Z",
                    "signals": {
                        "rsi": 28.5,
                        "sentiment_negative": true,
                        "forecast_direction": "down"
                    }
                }
            ],
            "count": 1,
            "generated_at": "2025-11-04T12:34:56.789Z",
            "source": ["technical_signals", "news_sentiment", "forecast_correlation"],
            "pipeline": {
                "algorithm": "multi_signal_confluence_v1",
                "processed_at": "2025-11-04T12:34:56.789Z"
            }
        }
    }
    """
    # Use the cache layer to get alerts data
    # If cached data exists and is fresh, return it
    # Otherwise, compute fresh alerts and cache them
    alerts_data = get_latest_alerts()
    
    # Add freshness information to response
    if 'generated_at' in alerts_data:
        # Calculate if data is stale (older than 1 hour)
        import datetime
        try:
            gen_time = datetime.datetime.fromisoformat(alerts_data['generated_at'].replace('Z', '+00:00'))
            current_time = datetime.datetime.now(datetime.timezone.utc)
            time_diff = (current_time - gen_time).total_seconds()
            
            alerts_data["freshness"] = "stale" if time_diff > 3600 else "fresh"
        except:
            alerts_data["freshness"] = "unknown"
    else:
        alerts_data["freshness"] = "fresh"
    
    return ok(alerts_data)


# ============================================================================
# USER ALERTS CRUD OPERATIONS (API-ALERTS-001 by ELENA-39)
# ============================================================================

@router.get("/alerts/user")
def get_user_alerts(
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    status: Optional[AlertStatus] = Query(None, description="Filter by status"),
    type: Optional[AlertType] = Query(None, description="Filter by type")
):
    """
    Get user-created alerts with optional filters
    
    **Query Parameters:**
    - `ticker`: Filter by ticker symbol
    - `status`: Filter by status (active, triggered, snoozed, disabled)
    - `type`: Filter by type (price, sentiment, forecast, etc.)
    
    **Returns:**
    ```json
    {
      "ok": true,
      "data": {
        "alerts": [...],
        "count": 10
      }
    }
    ```
    """
    try:
        service = get_alerts_service()
        alerts = service.list_alerts(ticker=ticker, status=status, type=type)
        
        return ok({
            "alerts": [alert.model_dump() for alert in alerts],
            "count": len(alerts)
        })
    except Exception as e:
        return err(f"Failed to get alerts: {str(e)}", code=500)


@router.post("/alerts")
def create_alert(request: AlertCreateRequest):
    """
    Create a new alert
    
    **Request Body:**
    ```json
    {
      "ticker": "AAPL",
      "type": "price",
      "condition": {
        "field": "price",
        "operator": ">",
        "value": 180.0
      },
      "message": "AAPL price above $180"
    }
    ```
    
    **Alert Types:**
    - `price`: Price threshold
    - `sentiment`: Sentiment shift
    - `forecast`: Forecast change
    - `correlation`: Correlation break
    - `regime`: Market regime change
    - `volume`: Volume spike
    - `volatility`: Volatility threshold
    - `technical`: Technical indicator
    
    **Returns:**
    ```json
    {
      "ok": true,
      "data": {
        "id": "...",
        "ticker": "AAPL",
        ...
      }
    }
    ```
    """
    try:
        service = get_alerts_service()
        alert = service.create_alert(
            ticker=request.ticker,
            type=request.type,
            condition=request.condition,
            message=request.message,
            metadata=request.metadata
        )
        
        return ok(alert.model_dump())
    except Exception as e:
        return err(f"Failed to create alert: {str(e)}", code=500)


@router.get("/alerts/{alert_id}")
def get_alert(alert_id: str):
    """
    Get a specific alert by ID
    
    **Returns:**
    ```json
    {
      "ok": true,
      "data": {
        "id": "...",
        "ticker": "AAPL",
        ...
      }
    }
    ```
    """
    try:
        service = get_alerts_service()
        alert = service.get_alert(alert_id)
        
        if not alert:
            return err(f"Alert {alert_id} not found", code=404)
        
        return ok(alert.model_dump())
    except Exception as e:
        return err(f"Failed to get alert: {str(e)}", code=500)


@router.put("/alerts/{alert_id}")
def update_alert(alert_id: str, request: AlertUpdateRequest):
    """
    Update an existing alert
    
    **Request Body (all fields optional):**
    ```json
    {
      "condition": {
        "field": "price",
        "operator": ">",
        "value": 185.0
      },
      "message": "Updated message",
      "status": "active"
    }
    ```
    
    **Returns:**
    ```json
    {
      "ok": true,
      "data": {
        "id": "...",
        ...
      }
    }
    ```
    """
    try:
        service = get_alerts_service()
        alert = service.update_alert(
            alert_id=alert_id,
            condition=request.condition,
            message=request.message,
            status=request.status,
            metadata=request.metadata
        )
        
        if not alert:
            return err(f"Alert {alert_id} not found", code=404)
        
        return ok(alert.model_dump())
    except Exception as e:
        return err(f"Failed to update alert: {str(e)}", code=500)


@router.delete("/alerts/{alert_id}")
def delete_alert(alert_id: str):
    """
    Delete an alert
    
    **Returns:**
    ```json
    {
      "ok": true,
      "data": {
        "deleted": true,
        "id": "..."
      }
    }
    ```
    """
    try:
        service = get_alerts_service()
        deleted = service.delete_alert(alert_id)
        
        if not deleted:
            return err(f"Alert {alert_id} not found", code=404)
        
        return ok({
            "deleted": True,
            "id": alert_id
        })
    except Exception as e:
        return err(f"Failed to delete alert: {str(e)}", code=500)


@router.post("/alerts/{alert_id}/test")
def test_alert(alert_id: str, request: AlertTestRequest):
    """
    Test if alert condition would be met with given value
    
    **Request Body:**
    ```json
    {
      "test_value": 182.5
    }
    ```
    
    **Returns:**
    ```json
    {
      "ok": true,
      "data": {
        "alert_id": "...",
        "ticker": "AAPL",
        "condition": {...},
        "test_value": 182.5,
        "would_trigger": true,
        "message": "..."
      }
    }
    ```
    """
    try:
        service = get_alerts_service()
        result = service.test_alert(alert_id, request.test_value)
        
        if "error" in result:
            return err(result["error"], code=404)
        
        return ok(result)
    except Exception as e:
        return err(f"Failed to test alert: {str(e)}", code=500)


@router.post("/alerts/{alert_id}/snooze")
def snooze_alert(alert_id: str, request: AlertSnoozeRequest):
    """
    Snooze an alert for specified duration
    
    **Request Body:**
    ```json
    {
      "duration_minutes": 120
    }
    ```
    
    **Returns:**
    ```json
    {
      "ok": true,
      "data": {
        "id": "...",
        "status": "snoozed",
        "snoozed_until": "2025-11-06T10:00:00Z"
      }
    }
    ```
    """
    try:
        service = get_alerts_service()
        alert = service.snooze_alert(alert_id, request.duration_minutes)
        
        if not alert:
            return err(f"Alert {alert_id} not found", code=404)
        
        return ok(alert.model_dump())
    except Exception as e:
        return err(f"Failed to snooze alert: {str(e)}", code=500)


@router.get("/alerts/triggered")
def get_triggered_alerts(limit: int = Query(50, le=100, description="Maximum number of alerts")):
    """
    Get recently triggered alerts
    
    **Query Parameters:**
    - `limit`: Maximum number of alerts to return (max 100)
    
    **Returns:**
    ```json
    {
      "ok": true,
      "data": {
        "alerts": [...],
        "count": 15
      }
    }
    ```
    """
    try:
        service = get_alerts_service()
        triggered = service.get_triggered_alerts(limit=limit)
        
        return ok({
            "alerts": [alert.model_dump() for alert in triggered],
            "count": len(triggered)
        })
    except Exception as e:
        return err(f"Failed to get triggered alerts: {str(e)}", code=500)


# ============================================================================
# INITIALIZATION
# ============================================================================

# Run the alert job to generate initial alerts
# This ensures that when the endpoint is first called, there's already data
if __name__ != "__main__":
    # Import and run the job to ensure we have initial data
    from backend.jobs.alerts import run_alerts_job
    import sys
    import os
    # Only run on import if we're not in a test environment
    if not os.environ.get('TEST_ENV'):
        try:
            run_alerts_job()
        except:
            # If job fails to run, that's okay - the endpoint will handle it gracefully
            pass