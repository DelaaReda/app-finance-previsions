"""
Dashboard KPIs endpoint
Aggregates forecasts, briefs, news and backtests to expose high level KPIs
used by the adaptive dashboard widgets.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import json
import logging

from fastapi import APIRouter, Query, Response

from core.response import ok
from storage.io import load_json, save_json

logger = logging.getLogger(__name__)

router = APIRouter()

CACHE_KEY = "dashboard/kpis"
CACHE_TTL_SECONDS = 900  # 15 minutes
HIGH_CONF_THRESHOLD = 0.6


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts or not isinstance(ts, str):
        return None
    try:
        if ts.endswith("Z"):
            ts = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        try:
            if value.endswith("Z"):
                value = value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None
    return None


def _extract_payload(snapshot: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not snapshot or not isinstance(snapshot, dict):
        return None
    for key in ("data", "payload", "kpis"):
        value = snapshot.get(key)
        if isinstance(value, dict):
            return value
    return snapshot


def _extract_rows(blob: Any) -> List[Dict[str, Any]]:
    """
    Extract rows from various data structures.
    Handles: direct list, dict with 'rows', dict with 'data.rows', etc.
    """
    if isinstance(blob, list):
        return [item for item in blob if isinstance(item, dict)]
    if isinstance(blob, dict):
        # Try direct 'rows' key first (most common)
        if isinstance(blob.get("rows"), list):
            return [item for item in blob["rows"] if isinstance(item, dict)]
        
        # Try nested structures: data.rows, payload.rows
        candidates = []
        for key in ("data", "payload"):
            value = blob.get(key)
            if value:
                if isinstance(value, list):
                    # data is a list of rows
                    candidates.extend([item for item in value if isinstance(item, dict)])
                elif isinstance(value, dict):
                    # data is a dict, try to extract rows recursively
                    rows = _extract_rows(value)
                    if rows:
                        candidates.extend(rows)
        
        if candidates:
            return candidates
        
        # If no rows found but dict has list-like structure, return empty
        # (to avoid treating metadata dicts as rows)
        return []
    return []


def _ensure_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _load_snapshot(key: str) -> Optional[Dict[str, Any]]:
    data = load_json(key)
    if not data and not key.endswith(".json"):
        data = load_json(f"{key}.json")
    return data


def _recent_articles(articles: List[Dict[str, Any]], window_minutes: int = 60) -> int:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=window_minutes)
    count = 0
    for article in articles:
        ts = _parse_timestamp(article.get("timestamp") or article.get("pubDate"))
        if ts and ts >= cutoff:
            count += 1
    return count


def _avg(values: List[float]) -> float:
    total = 0.0
    count = 0
    for value in values:
        if value is None:
            continue
        total += value
        count += 1
    return total / count if count else 0.0


def _fallback_signals(rows: List[Dict[str, Any]], direction: str) -> List[Dict[str, Any]]:
    direction = direction.lower()
    filtered = []
    for row in rows:
        row_direction = (row.get("direction") or "").lower()
        if direction == "bullish" and row_direction in {"up", "bullish", "buy"}:
            filtered.append(row)
        elif direction == "bearish" and row_direction in {"down", "bearish", "sell"}:
            filtered.append(row)
    filtered.sort(key=lambda r: r.get("confidence", 0) * abs(r.get("expected_return", 0) or 0), reverse=True)
    return filtered[:3]


@router.get("/dashboard/kpis")
def get_dashboard_kpis(
    sectors: Optional[str] = Query(None, description="Filter by sectors (comma-separated)"),
    horizons: Optional[str] = Query(None, description="Filter by horizons (comma-separated)"),
    themes: Optional[str] = Query(None, description="Filter by themes (comma-separated)"),
    tickers: Optional[str] = Query(None, description="Filter by tickers (comma-separated)"),
) -> Dict[str, Any]:
    # When invoked outside FastAPI (tests), Query(...) instances may leak through.
    if not isinstance(tickers, str):
        tickers = None

    now = datetime.utcnow().replace(tzinfo=None)

    cached_snapshot = _load_snapshot(CACHE_KEY)
    cached_payload = _extract_payload(cached_snapshot)
    if cached_payload:
        cached_at = _parse_iso(cached_payload.get("generated_at")) or _parse_iso(
            cached_snapshot.get("freshness")
        )
        if cached_at:
            age_seconds = (now - cached_at.replace(tzinfo=None)).total_seconds()
            if age_seconds < CACHE_TTL_SECONDS:
                logger.info("✅ Serving cached dashboard KPIs (age: %.0fs)", age_seconds)
                return Response(
                    content=json.dumps(ok(cached_payload)),
                    media_type="application/json",
                    headers={
                        "Cache-Control": "public, max-age=300",
                        "ETag": f'"{hash(str(cached_payload))}"',
                    },
                )

    forecasts_snapshot = _load_snapshot("forecasts") or {}
    forecast_rows = _extract_rows(forecasts_snapshot)
    
    # Log for debugging if no rows found
    if not forecast_rows and forecasts_snapshot:
        logger.warning(f"No forecast rows extracted. Snapshot keys: {list(forecasts_snapshot.keys()) if isinstance(forecasts_snapshot, dict) else 'not a dict'}")
        # Try alternative extraction methods
        if isinstance(forecasts_snapshot, dict):
            # Check if rows are directly in the dict
            if "rows" in forecasts_snapshot and isinstance(forecasts_snapshot["rows"], list):
                forecast_rows = [item for item in forecasts_snapshot["rows"] if isinstance(item, dict)]
                logger.info(f"Extracted {len(forecast_rows)} rows from direct 'rows' key")
    
    last_forecast_dt = None
    if isinstance(forecasts_snapshot, dict):
        last_forecast_dt = (
            forecasts_snapshot.get("last_update")
            or forecasts_snapshot.get("generated_at")
            or forecasts_snapshot.get("saved_at")
            or forecasts_snapshot.get("materialized_at")
        )

    ticker_set = {
        row.get("ticker") or row.get("symbol")
        for row in forecast_rows
        if row.get("ticker") or row.get("symbol")
    }
    ticker_set.discard(None)
    horizon_set = {
        row.get("horizon") or row.get("timeframe")
        for row in forecast_rows
        if row.get("horizon") or row.get("timeframe")
    }
    horizon_set.discard(None)

    total_forecasts = len(forecast_rows)
    high_conf_forecasts = sum(1 for row in forecast_rows if (row.get("confidence") or 0) >= HIGH_CONF_THRESHOLD)
    avg_confidence = _avg([row.get("confidence") or 0 for row in forecast_rows])
    
    # Calculate high confidence percentage (for frontend display)
    high_confidence_pct = (high_conf_forecasts / total_forecasts * 100) if total_forecasts > 0 else 0.0
    
    # Debug logging for KPI calculation
    logger.debug(f"📊 KPI Calculation Debug:", extra={
        "total_forecasts": total_forecasts,
        "high_conf_forecasts": high_conf_forecasts,
        "high_confidence_pct": high_confidence_pct,
        "avg_confidence": avg_confidence,
        "threshold": HIGH_CONF_THRESHOLD,
        "sample_confidences": [row.get("confidence", 0) for row in forecast_rows[:5]] if forecast_rows else []
    })
    bullish_signals = sum(
        1 for row in forecast_rows if (row.get("direction") or "").lower() in {"up", "bullish", "buy"}
    )
    bearish_signals = sum(
        1 for row in forecast_rows if (row.get("direction") or "").lower() in {"down", "bearish", "sell"}
    )

    brief_snapshot = _load_snapshot("brief_weekly") or _load_snapshot("brief_daily")
    brief_payload = _extract_payload(brief_snapshot) or {}
    weekly_section = brief_payload.get("weekly") if isinstance(brief_payload, dict) else None
    if not isinstance(weekly_section, dict):
        weekly_section = {}
    top_signals = _ensure_list(weekly_section.get("top_signals") or brief_payload.get("top_signals") or [])
    top_risks = _ensure_list(weekly_section.get("top_risks") or brief_payload.get("top_risks") or [])

    if not top_signals:
        top_signals = _fallback_signals(forecast_rows, "bullish")
    if not top_risks:
        top_risks = _fallback_signals(forecast_rows, "bearish")

    news_snapshot = _load_snapshot("news_feed") or {}
    articles = _ensure_list(news_snapshot.get("articles") or news_snapshot.get("data", {}).get("articles") or [])
    recent_news_count = _recent_articles(articles, window_minutes=60)
    avg_news_score = _avg([article.get("score") for article in articles if isinstance(article, dict)])

    backtests_snapshot = _load_snapshot("backtests") or {}
    backtest_metrics = (
        backtests_snapshot.get("results", {}).get("metrics")
        if isinstance(backtests_snapshot.get("results"), dict)
        else backtests_snapshot.get("metrics", {})
    ) or {}

    backtests_summary = {
        "hit_rate": backtest_metrics.get("hit_rate", 0.0),
        "sharpe_ratio": backtest_metrics.get("sharpe_ratio", 0.0),
        "status": backtests_snapshot.get("results", {}).get("status")
        or backtests_snapshot.get("status")
        or "pending",
    }

    requested_tickers: Optional[set[str]] = None
    if tickers:
        requested_tickers = {ticker.strip().upper() for ticker in tickers.split(",") if ticker.strip()}

    if requested_tickers:
        top_signals = [signal for signal in top_signals if (signal.get("ticker") or "").upper() in requested_tickers]
        top_risks = [risk for risk in top_risks if (risk.get("ticker") or "").upper() in requested_tickers]

    payload = {
        "last_forecast_dt": last_forecast_dt,
        "total_forecasts": total_forecasts,
        "tickers_tracked": len(ticker_set),
        "available_horizons": sorted(h for h in horizon_set if h),
        "top_signals": top_signals[:3],
        "top_risks": top_risks[:3],
        "forecasts": {
            "total": total_forecasts,
            "high_confidence": high_conf_forecasts,
            "high_confidence_pct": round(high_confidence_pct, 2),  # Percentage for frontend
            "avg_confidence": round(avg_confidence, 4),
            "bullish": bullish_signals,
            "bearish": bearish_signals,
        },
        "news": {
            "recent_count": recent_news_count,
            "avg_score": round(avg_news_score, 3) if avg_news_score else 0.0,
            "sources": len({article.get("source") for article in articles if article.get("source")}),
        },
        "backtests": backtests_summary,
        "system": {
            "last_forecast_update": last_forecast_dt,
            "last_news_update": news_snapshot.get("collected_at") or news_snapshot.get("generated_at"),
            "last_brief_update": brief_snapshot.get("last_update") if isinstance(brief_snapshot, dict) else None,
        },
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    try:
        save_json(CACHE_KEY, {"data": payload}, source=["dashboard_api", "kpis"])
    except Exception as exc:
        logger.warning("Unable to cache dashboard KPIs snapshot: %s", exc)

    return Response(
        content=json.dumps(ok(payload)),
        media_type="application/json",
        headers={
            "Cache-Control": "public, max-age=300",
            "ETag": f'"{hash(str(payload))}"',
        },
    )


dashboard_router = router
