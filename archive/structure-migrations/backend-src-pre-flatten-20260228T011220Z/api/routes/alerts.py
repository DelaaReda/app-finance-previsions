"""
Alerts API Routes
Combines alert rules management with user alert CRUD + live alerts feed.
"""
from fastapi import APIRouter, Query, HTTPException, Body
from typing import Dict, Any, List, Optional
from datetime import datetime
import sys
from pathlib import Path
from pydantic import BaseModel, Field

try:
    from src.core.response import ok, err
except Exception:  # pragma: no cover - defensive fallback
    def ok(data): return {"ok": True, "data": data}
    def err(message, code=500): return {"ok": False, "error": message, "code": code}

# Ensure backend paths
backend_root = Path(__file__).resolve().parents[2]
for p in (backend_root, backend_root / "src"):
    p_str = str(p)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)

try:
    from services.alert_rules import alert_rules_service
except ImportError:  # pragma: no cover
    from src.services.alert_rules import alert_rules_service  # type: ignore

try:
    from services.alerts_service import (
        get_alerts_service,
        Alert,
        AlertCondition,
        AlertType,
        AlertStatus,
    )
except ImportError:  # pragma: no cover
    get_alerts_service = None  # type: ignore
    Alert = AlertCondition = AlertType = AlertStatus = None  # type: ignore

try:
    from services.cache_layer import load_or_compute
except ImportError:  # pragma: no cover
    def load_or_compute(key, compute_fn, **_): return compute_fn()

try:
    from jobs.alerts import get_latest_alerts, run_alerts_job
except Exception:  # pragma: no cover
    get_latest_alerts = lambda: {"alerts": [], "count": 0}
    run_alerts_job = None


router = APIRouter(prefix="/api", tags=["alerts"])


# ------------------- Alert Rules ------------------- #

@router.get("/alerts/rules")
async def get_alert_rules():
    """Get all configured alert rules (never-empty fallback)."""
    try:
        rules_data = alert_rules_service.get_all_rules()
        return {
            "ok": True,
            "data": rules_data,
            "freshness": rules_data.get("generated_at", datetime.utcnow().isoformat() + "Z"),
        }
    except Exception as e:
        return {
            "ok": True,
            "data": {
                "rules": [],
                "count": 0,
                "enabled_count": 0,
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "source": ["alert_rules_route", "error_fallback", "fc-api-034"],
                "error": str(e),
                "message": "Failed to load alert rules but fallback returned to maintain never-empty contract",
            },
            "freshness": "error",
        }


@router.post("/alerts/rules")
async def create_alert_rule(
    name: str = Body(..., description="Rule name"),
    rule_type: str = Body(..., description="Rule type: rsi_oversold, rsi_overbought, news_sentiment, etc."),
    threshold: float = Body(..., description="Threshold value for trigger"),
    assets: List[str] = Body(..., description="List of tickers to monitor"),
    enabled: bool = Body(True, description="Whether the rule is enabled"),
    frequency: str = Body("realtime", description="Alert frequency: realtime, minute, hour, day"),
    priority: int = Body(3, ge=1, le=5, description="Priority level 1-5"),
    parameters: Optional[Dict[str, Any]] = Body(None, description="Additional rule-specific parameters"),
    description: Optional[str] = Body(None, description="Rule description"),
):
    """Create a new alert rule."""
    try:
        rule_data = {
            "name": name,
            "rule_type": rule_type,
            "threshold": threshold,
            "assets": assets,
            "enabled": enabled,
            "frequency": frequency,
            "priority": priority,
            "parameters": parameters or {},
            "description": description or "",
            "source": ["user_created", "alert_rules_api", "fc-api-034"],
        }
        result = alert_rules_service.create_rule(rule_data)
        if result.get("ok"):
            return {"ok": True, "data": result.get("data"), "message": result.get("message")}
        return {"ok": False, "error": result.get("error"), "message": result.get("message")}
    except Exception as e:
        return {"ok": False, "error": str(e), "message": "Failed to create alert rule"}


@router.put("/alerts/rules/{rule_id}")
async def update_alert_rule(rule_id: str, rule_data: Dict[str, Any] = Body(...)):
    """Update an existing alert rule by ID."""
    try:
        result = alert_rules_service.update_rule(rule_id, rule_data)
        return {"ok": result.get("ok", True), "data": result.get("data"), "message": result.get("message", "Rule updated")}
    except Exception as e:
        return {"ok": False, "error": str(e), "message": f"Failed to update alert rule {rule_id}"}


@router.delete("/alerts/rules/{rule_id}")
async def delete_alert_rule(rule_id: str):
    """Delete an alert rule by ID."""
    try:
        result = alert_rules_service.delete_rule(rule_id)
        return {"ok": result.get("ok", True), "data": result.get("data"), "message": result.get("message", "Rule deleted")}
    except Exception as e:
        return {"ok": False, "error": str(e), "message": f"Failed to delete alert rule {rule_id}"}


@router.get("/alerts/types")
async def get_available_alert_types():
    """Get list of available alert rule types with parameters (never-empty)."""
    try:
        available_types = {
            "rsi_oversold": {
                "name": "RSI Oversold",
                "description": "Trigger when RSI drops below threshold (typically 30)",
                "parameters": {
                    "rsi_period": {"type": "integer", "default": 14, "description": "RSI calculation period"},
                    "oversold_level": {"type": "float", "default": 30, "min": 0, "max": 100, "description": "Threshold for oversold condition"},
                },
            },
            "rsi_overbought": {
                "name": "RSI Overbought",
                "description": "Trigger when RSI rises above threshold (typically 70)",
                "parameters": {
                    "rsi_period": {"type": "integer", "default": 14, "description": "RSI calculation period"},
                    "overbought_level": {"type": "float", "default": 70, "min": 0, "max": 100, "description": "Threshold for overbought condition"},
                },
            },
            "news_sentiment": {
                "name": "News Sentiment",
                "description": "Trigger when news sentiment score crosses threshold",
                "parameters": {
                    "sentiment_threshold": {"type": "float", "default": -0.5, "min": -1, "max": 1, "description": "Sentiment threshold (-1 to 1)"},
                    "asset_specific": {"type": "boolean", "default": True, "description": "Only trigger for news mentioning specific assets"},
                },
            },
            "price_breakout": {
                "name": "Price Breakout",
                "description": "Trigger when price breaks above/below key technical levels",
                "parameters": {
                    "breakout_threshold": {"type": "float", "default": 0.02, "min": 0, "max": 1, "description": "Breakout threshold as percentage"},
                    "breakout_type": {"type": "string", "default": "either", "options": ["above", "below", "either"], "description": "Direction of breakout to trigger"},
                },
            },
            "volume_spike": {
                "name": "Volume Spike",
                "description": "Trigger when trading volume exceeds threshold",
                "parameters": {
                    "volume_multiple": {"type": "float", "default": 1.5, "min": 1, "description": "Multiple of average volume to trigger"},
                    "lookback_period": {"type": "integer", "default": 20, "description": "Days to calculate average volume"},
                },
            },
        }
        return {"ok": True, "data": {"types": available_types, "count": len(available_types), "generated_at": datetime.utcnow().isoformat() + "Z", "source": ["alert_rules_service", "supported_types", "fc-api-034"]}}
    except Exception as e:
        return {
            "ok": True,
            "data": {
                "types": {},
                "count": 0,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "source": ["alert_rules_service", "error_fallback", "fc-api-034"],
                "error": str(e),
                "message": "Failed to get alert types but fallback returned to maintain never-empty contract",
            },
        }


# ------------------- User alerts CRUD + feed ------------------- #

class AlertCreateRequest(BaseModel):
    ticker: str = Field(..., description="Ticker symbol", example="AAPL")
    type: AlertType = Field(..., description="Alert type", example="price")
    condition: AlertCondition = Field(..., description="Alert condition")
    message: str = Field(..., description="Alert message", example="AAPL price above $180")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")


class AlertUpdateRequest(BaseModel):
    condition: Optional[AlertCondition] = Field(None, description="New condition")
    message: Optional[str] = Field(None, description="New message")
    status: Optional[AlertStatus] = Field(None, description="New status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="New metadata")


class AlertTestRequest(BaseModel):
    test_value: float = Field(..., description="Value to test against condition")


class AlertSnoozeRequest(BaseModel):
    duration_minutes: int = Field(default=60, ge=1, le=1440, description="Snooze duration in minutes (1-1440)")


@router.get("/alerts")
def alerts():
    """Get market alerts with technical/news/forecast context (cached compute)."""
    try:
        alerts_data = get_latest_alerts() if get_latest_alerts else {"alerts": [], "count": 0}
    except Exception as e:
        alerts_data = {"alerts": [], "count": 0, "error": str(e)}
    if "generated_at" in alerts_data:
        try:
            import datetime as _dt
            gen_time = _dt.datetime.fromisoformat(alerts_data["generated_at"].replace("Z", "+00:00"))
            freshness = "stale" if (_dt.datetime.now(_dt.timezone.utc) - gen_time).total_seconds() > 3600 else "fresh"
        except Exception:
            freshness = "unknown"
        alerts_data["freshness"] = alerts_data.get("freshness", freshness)
    else:
        alerts_data["freshness"] = "fresh"
    # Ensure never-empty contract even if upstream errors
    if not alerts_data.get("alerts"):
        alerts_data.setdefault("alerts", [])
    alerts_data["count"] = len(alerts_data["alerts"])
    alerts_data.pop("error", None)
    alerts_data.pop("message", None)
    return ok(alerts_data)


@router.get("/alerts/user")
def get_user_alerts(
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    status: Optional[AlertStatus] = Query(None, description="Filter by status"),
    type: Optional[AlertType] = Query(None, description="Filter by type"),
):
    """List user-created alerts with optional filters."""
    try:
        service = get_alerts_service() if get_alerts_service else None
        alerts = service.list_alerts(ticker=ticker, status=status, type=type) if service else []
        return ok({"alerts": [alert.model_dump() for alert in alerts], "count": len(alerts)})
    except Exception as e:
        return err(f"Failed to get alerts: {str(e)}", code=500)


@router.post("/alerts")
def create_alert(request: AlertCreateRequest):
    """Create a new alert."""
    try:
        service = get_alerts_service() if get_alerts_service else None
        alert = service.create_alert(
            ticker=request.ticker,
            type=request.type,
            condition=request.condition,
            message=request.message,
            metadata=request.metadata,
        ) if service else None
        return ok(alert.model_dump() if alert else {})
    except Exception as e:
        return err(f"Failed to create alert: {str(e)}", code=500)


@router.get("/alerts/{alert_id}")
def get_alert(alert_id: str):
    """Get a specific alert by ID."""
    try:
        service = get_alerts_service() if get_alerts_service else None
        alert = service.get_alert(alert_id) if service else None
        if not alert:
            return err(f"Alert {alert_id} not found", code=404)
        return ok(alert.model_dump())
    except Exception as e:
        return err(f"Failed to get alert: {str(e)}", code=500)


@router.put("/alerts/{alert_id}")
def update_alert(alert_id: str, request: AlertUpdateRequest):
    """Update an existing alert."""
    try:
        service = get_alerts_service() if get_alerts_service else None
        alert = service.update_alert(
            alert_id=alert_id,
            condition=request.condition,
            message=request.message,
            status=request.status,
            metadata=request.metadata,
        ) if service else None
        if not alert:
            return err(f"Alert {alert_id} not found", code=404)
        return ok(alert.model_dump())
    except Exception as e:
        return err(f"Failed to update alert: {str(e)}", code=500)


@router.delete("/alerts/{alert_id}")
def delete_alert(alert_id: str):
    """Delete an alert."""
    try:
        service = get_alerts_service() if get_alerts_service else None
        deleted = service.delete_alert(alert_id) if service else False
        if not deleted:
            return err(f"Alert {alert_id} not found", code=404)
        return ok({"deleted": True, "id": alert_id})
    except Exception as e:
        return err(f"Failed to delete alert: {str(e)}", code=500)


@router.post("/alerts/{alert_id}/test")
def test_alert(alert_id: str, request: AlertTestRequest):
    """Test if an alert condition would trigger for a value."""
    try:
        service = get_alerts_service() if get_alerts_service else None
        result = service.test_alert(alert_id, request.test_value) if service else {"would_trigger": False}
        if "error" in result:
            return err(result["error"], code=404)
        return ok(result)
    except Exception as e:
        return err(f"Failed to test alert: {str(e)}", code=500)


@router.post("/alerts/{alert_id}/snooze")
def snooze_alert(alert_id: str, request: AlertSnoozeRequest):
    """Snooze an alert for specified duration."""
    try:
        service = get_alerts_service() if get_alerts_service else None
        alert = service.snooze_alert(alert_id, request.duration_minutes) if service else None
        if not alert:
            return err(f"Alert {alert_id} not found", code=404)
        return ok(alert.model_dump())
    except Exception as e:
        return err(f"Failed to snooze alert: {str(e)}", code=500)


@router.get("/alerts/triggered")
def get_triggered_alerts(limit: int = Query(50, le=100, description="Maximum number of alerts")):
    """Get recently triggered alerts."""
    try:
        service = get_alerts_service() if get_alerts_service else None
        triggered = service.get_triggered_alerts(limit=limit) if service else []
        return ok({"alerts": [alert.model_dump() for alert in triggered], "count": len(triggered)})
    except Exception as e:
        return err(f"Failed to get triggered alerts: {str(e)}", code=500)


# Run initial alerts job on import (non-blocking fallback)
if __name__ != "__main__" and run_alerts_job:
    try:
        import os
        if not os.environ.get("TEST_ENV"):
            run_alerts_job()
    except Exception:
        pass
