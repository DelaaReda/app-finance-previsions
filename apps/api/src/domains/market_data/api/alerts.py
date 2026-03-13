"""
Alerts API Routes
Combines alert rules management with user alert CRUD + live alerts feed.
"""
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException, Body
from typing import Dict, Any, List, Literal, Optional
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
for p in (backend_root,):
    p_str = str(p)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)

try:
    from domains.market_data.application.alert_rules import alert_rules_service
except ImportError:  # pragma: no cover
    from src.domains.market_data.application.alert_rules import alert_rules_service  # type: ignore

try:
    from domains.market_data.application.alerts_service import (
        get_alerts_service,
        Alert,
        AlertCondition,
        AlertType,
        AlertStatus,
    )
except ImportError:  # pragma: no cover
    from src.domains.market_data.application.alerts_service import (  # type: ignore
        get_alerts_service,
        Alert,
        AlertCondition,
        AlertType,
        AlertStatus,
    )

try:
    from domains.market_data.application.cache_layer import load_or_compute
except ImportError:  # pragma: no cover
    try:
        from src.domains.market_data.application.cache_layer import load_or_compute  # type: ignore
    except Exception:  # pragma: no cover
        def load_or_compute(key, compute_fn, **_): return compute_fn()

try:
    from platform.legacy.jobs.alerts import get_latest_alerts, run_alerts_job
except Exception:  # pragma: no cover
    try:
        from src.platform.legacy.jobs.alerts import get_latest_alerts, run_alerts_job  # type: ignore
    except Exception:  # pragma: no cover
        get_latest_alerts = lambda: {"alerts": [], "count": 0}
        run_alerts_job = None


router = APIRouter(prefix="/api", tags=["alerts"])

ALERTS_CACHE_TTL_SECONDS = max(
    0, int(os.getenv("ALERTS_ROUTE_CACHE_TTL_SECONDS", "60") or "60")
)
ALERTS_CACHE_MAX_ENTRIES = max(
    1, int(os.getenv("ALERTS_ROUTE_CACHE_MAX_ENTRIES", "32") or "32")
)
ALERT_PRIORITY_BANDS = {"urgent", "high", "medium", "low"}
ALERT_SEVERITY_ORDER = {
    "critical": 5,
    "high": 4,
    "warning": 3,
    "medium": 2,
    "low": 1,
    "info": 0,
}
_ALERTS_RESPONSE_CACHE: Dict[str, Dict[str, Any]] = {}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stable_cache_key(namespace: str, params: Dict[str, Any]) -> str:
    serialized = json.dumps(params, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.md5(serialized.encode("utf-8")).hexdigest()
    return f"{namespace}:{digest}"


def _alerts_cache_get(cache_key: str) -> Optional[Dict[str, Any]]:
    if ALERTS_CACHE_TTL_SECONDS <= 0:
        return None
    cached = _ALERTS_RESPONSE_CACHE.get(cache_key)
    if not isinstance(cached, dict):
        return None
    cached_at = float(cached.get("_cached_at", 0.0) or 0.0)
    age_seconds = max(0, int(time.time() - cached_at))
    if age_seconds > ALERTS_CACHE_TTL_SECONDS:
        _ALERTS_RESPONSE_CACHE.pop(cache_key, None)
        return None

    payload = dict(cached.get("payload") or {})
    payload["cache"] = {
        "hit": True,
        "age_seconds": age_seconds,
        "ttl_seconds": ALERTS_CACHE_TTL_SECONDS,
    }
    payload["source"] = list(payload.get("source") or []) + ["alerts_route_cache_hit"]
    return payload


def _alerts_cache_set(cache_key: str, payload: Dict[str, Any]) -> None:
    if ALERTS_CACHE_TTL_SECONDS <= 0:
        return
    if len(_ALERTS_RESPONSE_CACHE) >= ALERTS_CACHE_MAX_ENTRIES:
        oldest_key = min(
            _ALERTS_RESPONSE_CACHE.items(),
            key=lambda item: float(item[1].get("_cached_at", 0.0) or 0.0),
        )[0]
        _ALERTS_RESPONSE_CACHE.pop(oldest_key, None)
    _ALERTS_RESPONSE_CACHE[cache_key] = {
        "_cached_at": time.time(),
        "payload": dict(payload),
    }


def _parse_generated_at(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _freshness_from_generated_at(value: Any, now_utc: datetime) -> str:
    generated_at = _parse_generated_at(value)
    if generated_at is None:
        return "unknown"
    return "stale" if (now_utc - generated_at).total_seconds() > 3600 else "fresh"


def _sort_alerts(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        [dict(row) for row in rows if isinstance(row, dict)],
        key=lambda item: (
            int(item.get("priority_rank", 9999) or 9999),
            -int(item.get("priority_score", 0) or 0),
            -ALERT_SEVERITY_ORDER.get(str(item.get("severity", "medium")).lower(), 0),
            -float(item.get("confidence", 0.0) or 0.0),
            str(item.get("timestamp", "")),
        ),
    )


def _build_alerts_payload(
    *,
    priority_band: Optional[str],
    include_suppressed: bool,
    limit: int,
    debug: bool,
) -> Dict[str, Any]:
    now_iso = _utc_now_iso()
    now_utc = datetime.now(timezone.utc)
    filters_applied = {
        "priority_band": priority_band,
        "include_suppressed": include_suppressed,
        "limit": limit,
    }
    source = ["alerts_route", "alerts_snapshot"]
    warnings: List[str] = []

    try:
        snapshot = get_latest_alerts() if get_latest_alerts else {"alerts": [], "count": 0}
    except Exception as exc:
        return {
            "alerts": [],
            "count": 0,
            "suppressed_count": 0,
            "suppressed_alerts": [],
            "suppressed_risks": [],
            "generated_at": now_iso,
            "freshness": "error",
            "last_update": now_iso,
            "source": source + ["alerts_route_fallback"],
            "filters_applied": filters_applied,
            "alerting_metadata": {},
            "stats": {
                "total_visible_before_limit": 0,
                "visible_count": 0,
                "suppressed_available": 0,
                "returned_suppressed_count": 0,
                "priority_bands": {},
            },
            "warnings": warnings,
            "cache": {
                "hit": False,
                "age_seconds": 0,
                "ttl_seconds": ALERTS_CACHE_TTL_SECONDS,
            },
            "error": str(exc),
            "message": "Alerts endpoint fallback returned to maintain never-empty contract.",
        }

    alerts_rows = _sort_alerts(snapshot.get("alerts", []))
    suppressed_rows = _sort_alerts(snapshot.get("suppressed_alerts", []))
    if priority_band:
        alerts_rows = [row for row in alerts_rows if str(row.get("priority_band", "")).lower() == priority_band]
        suppressed_rows = [row for row in suppressed_rows if str(row.get("priority_band", "")).lower() == priority_band]

    visible_before_limit = len(alerts_rows)
    alerts_rows = alerts_rows[:limit]
    returned_suppressed = suppressed_rows[:limit] if include_suppressed else []

    if include_suppressed and suppressed_rows:
        warnings.append("suppressed_alerts_included_for_debugging")
    warnings.extend([str(item) for item in snapshot.get("warnings", []) if isinstance(item, str)])

    generated_at = snapshot.get("generated_at") or now_iso
    payload = {
        "alerts": alerts_rows,
        "count": len(alerts_rows),
        "suppressed_count": len(suppressed_rows),
        "suppressed_alerts": returned_suppressed,
        "suppressed_risks": snapshot.get("suppressed_risks") or [],
        "alerting_metadata": snapshot.get("alerting_metadata") or {},
        "generated_at": generated_at,
        "freshness": snapshot.get("freshness") or _freshness_from_generated_at(generated_at, now_utc),
        "last_update": generated_at,
        "source": list(snapshot.get("source") or source) + ["alerts_route_live"],
        "filters_applied": filters_applied,
        "stats": {
            "total_visible_before_limit": visible_before_limit,
            "visible_count": len(alerts_rows),
            "suppressed_available": len(suppressed_rows),
            "returned_suppressed_count": len(returned_suppressed),
            "priority_bands": dict((snapshot.get("stats") or {}).get("priority_bands") or {}),
            "suppression_reasons": dict((snapshot.get("stats") or {}).get("suppression_reasons") or {}),
        },
        "queue": {
            "top_alert_id": alerts_rows[0].get("id") if alerts_rows else None,
            "top_priority_band": alerts_rows[0].get("priority_band") if alerts_rows else None,
            "has_suppressed": bool(suppressed_rows),
        },
        "pipeline": dict(snapshot.get("pipeline") or {}),
        "warnings": warnings,
        "cache": {
            "hit": False,
            "age_seconds": 0,
            "ttl_seconds": ALERTS_CACHE_TTL_SECONDS,
        },
    }

    if debug:
        payload["debug_pipeline"] = [
            "load_latest_alerts_snapshot",
            "sort_by_priority_score_and_rank",
            "filter_priority_band",
            "apply_limit",
        ]
        payload["debug_snapshot_counts"] = {
            "alerts": len(snapshot.get("alerts", []) or []),
            "suppressed_alerts": len(snapshot.get("suppressed_alerts", []) or []),
        }

    return payload


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
def alerts(
    priority_band: Optional[Literal["urgent", "high", "medium", "low"]] = Query(
        None,
        description="Optional priority-band filter for the queue view.",
    ),
    include_suppressed: bool = Query(
        False,
        description="Include suppressed alerts preview for fatigue/debug review.",
    ),
    limit: int = Query(20, ge=1, le=100, description="Maximum visible alerts to return."),
    debug: bool = Query(False, description="Bypass cache and expose debug pipeline metadata."),
):
    """Get market alerts with priority queue metadata and suppression-aware filters."""
    params = {
        "priority_band": priority_band,
        "include_suppressed": include_suppressed,
        "limit": limit,
    }
    cache_key = _stable_cache_key("alerts_route_v2", params)
    if not debug:
        cached = _alerts_cache_get(cache_key)
        if cached is not None:
            return ok(cached)

    payload = _build_alerts_payload(
        priority_band=priority_band,
        include_suppressed=include_suppressed,
        limit=limit,
        debug=debug,
    )
    if not debug:
        _alerts_cache_set(cache_key, payload)
    return ok(payload)


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
