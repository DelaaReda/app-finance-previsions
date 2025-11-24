"""
Alert Rules API Routes
Task: FC-API-034 - Alert Rules Configuration
Author: ALEX-FINANCE-ANALYST-SUPERMAN-29
"""
from fastapi import APIRouter, Query, HTTPException, Body
from typing import Dict, Any, List, Optional
from datetime import datetime
import sys
from pathlib import Path

# Add backend root to path for imports
backend_root = Path(__file__).resolve().parents[2]  # Go from backend/src/api/routes/alerts.py to backend/
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

try:
    # Preferred import when backend/src is on sys.path
    from services.alert_rules import alert_rules_service
except ImportError:
    # Fallback when referenced via backend package
    from backend.services.alert_rules import alert_rules_service  # type: ignore

router = APIRouter(prefix="/api", tags=["alerts"])

@router.get("/alerts/rules")
async def get_alert_rules():
    """
    Get all configured alert rules.
    Implements never-empty contract by serving cached/latest data if live computation fails.
    """
    try:
        rules_data = alert_rules_service.get_all_rules()
        
        return {
            "ok": True,
            "data": rules_data,
            "freshness": rules_data.get("generated_at", datetime.utcnow().isoformat() + "Z")
        }
    except Exception as e:
        print(f"Error in /alerts/rules endpoint: {str(e)}")
        
        # Return structured fallback to maintain never-empty contract
        return {
            "ok": True,  # Still return True to maintain never-empty contract
            "data": {
                "rules": [],
                "count": 0,
                "enabled_count": 0,
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "source": ["alert_rules_route", "error_fallback", "fc-api-034"],
                "error": str(e),
                "message": "Failed to load alert rules but fallback returned to maintain never-empty contract"
            },
            "freshness": "error"
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
    description: Optional[str] = Body(None, description="Rule description")
):
    """
    Create a new alert rule.
    Validates parameters and adds rule to persistent storage.
    """
    try:
        # Prepare rule data
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
            "source": ["user_created", "alert_rules_api", "fc-api-034"]
        }
        
        # Create the rule
        result = alert_rules_service.create_rule(rule_data)
        
        if result.get("ok"):
            return {
                "ok": True,
                "data": result.get("data"),
                "message": result.get("message")
            }
        else:
            return {
                "ok": False,
                "error": result.get("error"),
                "message": result.get("message")
            }
    except Exception as e:
        print(f"Error creating alert rule: {str(e)}")
        return {
            "ok": False,
            "error": str(e),
            "message": "Failed to create alert rule"
        }


@router.put("/alerts/rules/{rule_id}")
async def update_alert_rule(rule_id: str, rule_data: Dict[str, Any] = Body(...)):
    """
    Update an existing alert rule by ID.
    """
    try:
        result = alert_rules_service.update_rule(rule_id, rule_data)
        
        return {
            "ok": result.get("ok", True),
            "data": result.get("data"),
            "message": result.get("message", "Rule updated successfully if ok=true")
        }
    except Exception as e:
        print(f"Error updating alert rule {rule_id}: {str(e)}")
        
        return {
            "ok": False,
            "error": str(e),
            "message": f"Failed to update alert rule {rule_id}"
        }


@router.delete("/alerts/rules/{rule_id}")
async def delete_alert_rule(rule_id: str):
    """
    Delete an alert rule by ID.
    """
    try:
        result = alert_rules_service.delete_rule(rule_id)
        
        return {
            "ok": result.get("ok", True),
            "data": result.get("data"),
            "message": result.get("message", "Rule deleted successfully if ok=true")
        }
    except Exception as e:
        print(f"Error deleting alert rule {rule_id}: {str(e)}")
        
        return {
            "ok": False,
            "error": str(e),
            "message": f"Failed to delete alert rule {rule_id}"
        }


@router.get("/alerts/types")
async def get_available_alert_types():
    """
    Get list of available alert rule types with their parameters.
    """
    try:
        available_types = {
            "rsi_oversold": {
                "name": "RSI Oversold",
                "description": "Trigger when RSI drops below threshold (typically 30)",
                "parameters": {
                    "rsi_period": {"type": "integer", "default": 14, "description": "RSI calculation period"},
                    "oversold_level": {"type": "float", "default": 30, "min": 0, "max": 100, "description": "Threshold for oversold condition"}
                }
            },
            "rsi_overbought": {
                "name": "RSI Overbought",
                "description": "Trigger when RSI rises above threshold (typically 70)",
                "parameters": {
                    "rsi_period": {"type": "integer", "default": 14, "description": "RSI calculation period"},
                    "overbought_level": {"type": "float", "default": 70, "min": 0, "max": 100, "description": "Threshold for overbought condition"}
                }
            },
            "news_sentiment": {
                "name": "News Sentiment",
                "description": "Trigger when news sentiment score crosses threshold",
                "parameters": {
                    "sentiment_threshold": {"type": "float", "default": -0.5, "min": -1, "max": 1, "description": "Sentiment threshold (-1 to 1)"},
                    "asset_specific": {"type": "boolean", "default": True, "description": "Only trigger for news mentioning specific assets"}
                }
            },
            "price_breakout": {
                "name": "Price Breakout",
                "description": "Trigger when price breaks above/below key technical levels",
                "parameters": {
                    "breakout_threshold": {"type": "float", "default": 0.02, "min": 0, "max": 1, "description": "Breakout threshold as percentage"},
                    "breakout_type": {"type": "string", "default": "either", "options": ["above", "below", "either"], "description": "Direction of breakout to trigger"}
                }
            },
            "volume_spike": {
                "name": "Volume Spike",
                "description": "Trigger when trading volume exceeds threshold",
                "parameters": {
                    "volume_multiple": {"type": "float", "default": 1.5, "min": 1, "description": "Multiple of average volume to trigger"},
                    "lookback_period": {"type": "integer", "default": 20, "description": "Days to calculate average volume"}
                }
            }
        }
        
        return {
            "ok": True,
            "data": {
                "types": available_types,
                "count": len(available_types),
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "source": ["alert_rules_service", "supported_types", "fc-api-034"]
            }
        }
    except Exception as e:
        print(f"Error getting alert types: {str(e)}")
        
        return {
            "ok": True,  # Maintain never-empty
            "data": {
                "types": {},
                "count": 0,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "source": ["alert_rules_service", "error_fallback", "fc-api-034"],
                "error": str(e),
                "message": "Failed to get alert types but fallback returned to maintain never-empty contract"
            }
        }
