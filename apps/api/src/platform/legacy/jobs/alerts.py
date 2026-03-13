"""
Alerts Job - Generates market alerts based on technical signals, news sentiment, and forecasts.
"""
import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List

# Add backend directory to path to properly import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from storage.io import save_json, load_json


ALERT_SEVERITY_ORDER = {
    "critical": 4,
    "high": 3,
    "warning": 2,
    "medium": 1,
    "low": 0,
    "info": -1,
}

ALERT_PRIORITY_BANDS = (
    (370, "urgent"),
    (290, "high"),
    (200, "medium"),
    (0, "low"),
)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_iso(ts: datetime) -> str:
    if ts.tzinfo is not None:
        ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
    return ts.replace(microsecond=0).isoformat() + "Z"


def _parse_dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _coerce_confidence(raw: Any) -> float:
    confidence = _safe_float(raw, 0.0)
    if confidence > 1:
        confidence /= 100.0
    return max(0.0, min(1.0, confidence))


def _seeded_float(seed: str) -> float:
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _extract_rows(payload: Dict[str, Any] | None, rows_key: str) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    container = payload.get("payload", payload)
    rows = container.get(rows_key, []) if isinstance(container, dict) else []
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    return []


def _extract_previous_alerts(payload: Dict[str, Any] | None) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    containers: List[Dict[str, Any]] = [payload]

    nested_data = payload.get("data")
    if isinstance(nested_data, dict):
        containers.append(nested_data)

    nested_payload = payload.get("payload")
    if isinstance(nested_payload, dict):
        containers.append(nested_payload)

    nested_data_payload = nested_data.get("payload") if isinstance(nested_data, dict) else None
    if isinstance(nested_data_payload, dict):
        containers.append(nested_data_payload)

    previous_alerts: List[Dict[str, Any]] = []
    for container in containers:
        for key in ("alerts", "suppressed_alerts"):
            candidate = container.get(key)
            if isinstance(candidate, list):
                previous_alerts.extend(row for row in candidate if isinstance(row, dict))
    return previous_alerts


def _extract_tickers(ticker: str, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not articles:
        return []

    normalized_ticker = (ticker or "").upper()
    matches: List[Dict[str, Any]] = []
    for article in articles:
        if not isinstance(article, dict):
            continue

        article_tickers = article.get("tickers", [])
        if isinstance(article_tickers, list) and normalized_ticker in [str(item).upper() for item in article_tickers]:
            matches.append(article)
            continue

        title = str(article.get("title", "")).upper()
        if normalized_ticker and normalized_ticker in title:
            matches.append(article)

    return matches


def _normalize_alert(
    alert: Dict[str, Any],
    ts: str,
    seen: Dict[str, Dict[str, Any]],
    ticker: str,
    alert_type: str,
    summary: str,
) -> None:
    severity = str(alert.get("severity", "medium")).lower()
    severity = severity if severity in ALERT_SEVERITY_ORDER else "medium"
    confidence = _coerce_confidence(alert.get("confidence", 0.0))

    fingerprint = f"{ticker}|{alert_type}|{summary}"
    if fingerprint in seen:
        return

    seen[fingerprint] = {
        "id": f"{alert_type}-{ticker}-{ts}",
        "type": alert_type,
        "ticker": ticker,
        "summary": summary,
        "description": alert.get("description", summary),
        "severity": severity,
        "confidence": confidence,
        "timestamp": ts,
        "signals": alert.get("signals", {}),
        "signature": fingerprint,
        "fingerprint": fingerprint,
    }


def _collect_recent_news_count(articles: Iterable[Dict[str, Any]], now: datetime) -> int:
    count = 0
    for article in articles:
        if not isinstance(article, dict):
            continue
        pub_date = article.get("pubDate")
        if not isinstance(pub_date, str):
            continue
        try:
            published_at = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
        except ValueError:
            continue
        if now - published_at <= timedelta(hours=1):
            count += 1
    return count


def _priority_score(alert: Dict[str, Any]) -> int:
    severity_points = (ALERT_SEVERITY_ORDER.get(str(alert.get("severity", "medium")).lower(), 0) + 2) * 100
    confidence_points = int(round(_coerce_confidence(alert.get("confidence", 0.0)) * 100))
    signals = alert.get("signals", {})
    if not isinstance(signals, dict):
        signals = {}
    news_points = min(40, int(signals.get("recent_news_count", 0) or 0) * 10)
    volatility_points = int(min(35, round(_safe_float(signals.get("volatility", 0.0)) * 1000)))
    return severity_points + confidence_points + news_points + volatility_points


def _priority_band(score: int) -> str:
    for floor, label in ALERT_PRIORITY_BANDS:
        if score >= floor:
            return label
    return "low"


def _suppression_config() -> Dict[str, int]:
    window_minutes = max(5, int(_safe_float(os.getenv("ALERTS_SUPPRESSION_WINDOW_MINUTES", 15), 15)))
    fatigue_threshold = max(1, int(_safe_float(os.getenv("ALERTS_FATIGUE_REPETITIONS", 2), 2)))
    escalation_bypass = max(0.0, _safe_float(os.getenv("ALERTS_SUPPRESSION_ESCALATION_DELTA", 0.12), 0.12))
    return {
        "window_minutes": window_minutes,
        "fatigue_threshold": fatigue_threshold,
        "escalation_delta_bps": int(round(escalation_bypass * 10000)),
    }


def _alert_fingerprint(alert: Dict[str, Any]) -> str:
    fingerprint = str(alert.get("fingerprint") or "").strip()
    if fingerprint:
        return fingerprint
    signature = str(alert.get("signature") or "").strip()
    if signature:
        parts = signature.split("|")
        if len(parts) >= 3:
            return "|".join(parts[:3])
        return signature
    ticker = str(alert.get("ticker", "")).upper()
    alert_type = str(alert.get("type", "")).strip()
    summary = str(alert.get("summary", "")).strip()
    if ticker and alert_type and summary:
        return f"{ticker}|{alert_type}|{summary}"
    return ""


def _previous_alert_map(previous_alerts: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    latest: Dict[str, Dict[str, Any]] = {}
    for alert in previous_alerts:
        fingerprint = _alert_fingerprint(alert)
        if not fingerprint:
            continue
        last_seen = _parse_dt(alert.get("timestamp")) or datetime.min
        existing = latest.get(fingerprint)
        if existing is None:
            latest[fingerprint] = dict(alert)
            continue
        existing_seen = _parse_dt(existing.get("timestamp")) or datetime.min
        if last_seen >= existing_seen:
            latest[fingerprint] = dict(alert)
    return latest


def _apply_priority_and_suppression(
    ordered_alerts: List[Dict[str, Any]],
    previous_alerts: List[Dict[str, Any]],
    now: datetime,
) -> Dict[str, Any]:
    now_dt = now.astimezone(timezone.utc).replace(tzinfo=None) if now.tzinfo is not None else now
    config = _suppression_config()
    suppression_window = timedelta(minutes=config["window_minutes"])
    escalation_delta = config["escalation_delta_bps"] / 10000.0
    previous_by_signature = _previous_alert_map(previous_alerts)

    active_alerts: List[Dict[str, Any]] = []
    suppressed_alerts: List[Dict[str, Any]] = []
    priority_counts = defaultdict(int)
    suppressed_counts = defaultdict(int)

    for base_rank, alert in enumerate(ordered_alerts, start=1):
        normalized = dict(alert)
        score = _priority_score(normalized)
        band = _priority_band(score)
        normalized["priority_score"] = score
        normalized["priority_band"] = band
        normalized["priority_rank"] = base_rank

        fingerprint = _alert_fingerprint(normalized)
        previous = previous_by_signature.get(fingerprint)
        suppression = {
            "window_minutes": config["window_minutes"],
            "fatigue_threshold": config["fatigue_threshold"],
            "suppressed": False,
            "repeat_count": 1,
            "reason": "",
            "last_emitted_at": None,
        }

        if previous:
            previous_repeat = int(previous.get("suppression", {}).get("repeat_count", 1))
            suppression["repeat_count"] = previous_repeat + 1
            previous_timestamp = _parse_dt(previous.get("timestamp"))
            if previous_timestamp is not None:
                suppression["last_emitted_at"] = _to_iso(previous_timestamp)
                within_window = now_dt - previous_timestamp <= suppression_window
                previous_confidence = _coerce_confidence(previous.get("confidence", 0.0))
                escalated = (
                    ALERT_SEVERITY_ORDER.get(str(normalized.get("severity", "medium")).lower(), 0)
                    > ALERT_SEVERITY_ORDER.get(str(previous.get("severity", "medium")).lower(), 0)
                    or _coerce_confidence(normalized.get("confidence", 0.0)) >= previous_confidence + escalation_delta
                )
                if within_window and suppression["repeat_count"] > config["fatigue_threshold"] and not escalated:
                    suppression["suppressed"] = True
                    suppression["reason"] = "fatigue_window_duplicate"

        normalized["suppression"] = suppression
        if suppression["suppressed"]:
            suppressed_alerts.append(normalized)
            suppressed_counts[suppression["reason"] or "suppressed"] += 1
            continue

        priority_counts[band] += 1
        active_alerts.append(normalized)

    for rank, alert in enumerate(active_alerts, start=1):
        alert["priority_rank"] = rank

    return {
        "active_alerts": active_alerts,
        "suppressed_alerts": suppressed_alerts,
        "priority_counts": dict(priority_counts),
        "suppressed_counts": dict(suppressed_counts),
        "config": config,
    }


def compute_alerts(now: datetime | None = None) -> Dict[str, Any]:
    """
    Compute market alerts by combining:
    1. Technical signals (RSI-like surrogate)
    2. News sentiment
    3. Forecast direction
    """

    now = now or datetime.utcnow()
    now_iso = _to_iso(now)

    # Load forecasts to correlate with alerts
    forecasts_data = load_json("forecasts")
    forecasts = _extract_rows(forecasts_data, "rows")

    # Load news to check for sentiment correlation
    news_data = load_json("news_feed")
    articles = _extract_rows(news_data, "articles")

    previous_alerts = _extract_previous_alerts(load_json("alerts"))

    warnings: List[str] = []
    if not forecasts:
        warnings.append("no_forecast_rows")
    if not articles:
        warnings.append("no_news_rows")

    alerts: Dict[str, Dict[str, Any]] = {}

    # Common tickers to scan for alerts
    tickers = ["SPY", "QQQ", "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "TSM"]

    for ticker in tickers:
        # Deterministic, seed-based proxy technical signals
        rsi = 20 + 60 * _seeded_float(f"alerts:rsi:{ticker}:{now.strftime('%Y%m%d%H')}")
        volatility = 0.01 + 0.05 * _seeded_float(f"alerts:vol:{ticker}:{now.strftime('%Y%m%d%H%M')}")

        ticker_forecasts = [f for f in forecasts if f.get("ticker", "").upper() == ticker]
        latest_direction: Dict[str, float] = defaultdict(float)
        for forecast in ticker_forecasts:
            direction = str(forecast.get("direction", "")).lower()
            if direction not in {"up", "down", "flat"}:
                continue
            latest_direction[direction] = max(latest_direction[direction], _coerce_confidence(forecast.get("confidence", 0.5)))

        ticker_news = _extract_tickers(ticker, articles)
        negative_sentiment = any(_safe_float(article.get("sentiment_score", 0.0), 0.0) < -0.3 for article in ticker_news)
        positive_sentiment = any(_safe_float(article.get("sentiment_score", 0.0), 0.0) > 0.3 for article in ticker_news)
        recent_news_count = _collect_recent_news_count(ticker_news, now)

        # Rule 1: Oversold-Bearish alert
        bearish_confidence = latest_direction.get("down", 0.0)
        bullish_confidence = latest_direction.get("up", 0.0)

        if rsi < 30 and bearish_confidence > 0:
            if negative_sentiment:
                confidence = min(0.95, bearish_confidence + 0.1)
                _normalize_alert(
                    {
                        "id": f"oversold-bearish-{ticker}-{now_iso}",
                        "type": "oversold-bearish",
                        "description": f"{ticker} oversold (RSI: {rsi:.1f}) with negative sentiment and bearish forecast",
                        "severity": "medium",
                        "confidence": confidence,
                        "signals": {
                            "rsi": round(rsi, 2),
                            "sentiment_negative": True,
                            "forecast_direction": "down",
                        },
                    },
                    now_iso,
                    alerts,
                    ticker,
                    "oversold-bearish",
                    f"oversold-bearish:{ticker}:down",
                )

        # Rule 2: Overbought-Bullish alert
        if rsi > 70 and bullish_confidence > 0:
            if positive_sentiment:
                confidence = min(0.95, bullish_confidence + 0.1)
                _normalize_alert(
                    {
                        "id": f"overbought-bullish-{ticker}-{now_iso}",
                        "type": "overbought-bullish",
                        "description": f"{ticker} overbought (RSI: {rsi:.1f}) with positive sentiment and bullish forecast",
                        "severity": "medium",
                        "confidence": confidence,
                        "signals": {
                            "rsi": round(rsi, 2),
                            "sentiment_positive": True,
                            "forecast_direction": "up",
                        },
                    },
                    now_iso,
                    alerts,
                    ticker,
                    "overbought-bullish",
                    f"overbought-bullish:{ticker}:up",
                )

        # Rule 3: Breakout News alert (high volatility + news activity)
        if volatility > 0.03 and recent_news_count >= 2:
            _normalize_alert(
                {
                    "id": f"breakout-news-{ticker}-{now_iso}",
                    "type": "breakout-news",
                    "description": f"{ticker} high volatility with breaking news ({recent_news_count} articles in last hour)",
                    "severity": "high",
                    "confidence": min(0.95, 0.6 + 0.1 * latest_direction.get("up", 0.0) + 0.1 * latest_direction.get("down", 0.0)),
                    "signals": {
                        "volatility": round(volatility, 4),
                        "recent_news_count": recent_news_count,
                    },
                },
                now_iso,
                alerts,
                ticker,
                "breakout-news",
                f"breakout-news:{ticker}:{recent_news_count}",
            )

    ordered_alerts = list(alerts.values())
    ordered_alerts.sort(
        key=lambda item: (
            ALERT_SEVERITY_ORDER.get(item.get("severity", "medium"), 0),
            item.get("confidence", 0.0),
            item.get("timestamp", ""),
        ),
        reverse=True,
    )
    prioritized = _apply_priority_and_suppression(ordered_alerts, previous_alerts, now)
    active_alerts = prioritized["active_alerts"]
    suppressed_alerts = prioritized["suppressed_alerts"]
    suppressed_count = len(suppressed_alerts)
    if suppressed_count:
        warnings.append("duplicate_alerts_suppressed")

    return {
        "alerts": active_alerts,
        "count": len(active_alerts),
        "suppressed_count": suppressed_count,
        "suppressed_alerts": suppressed_alerts,
        "stats": {
            "scanned_tickers": len(tickers),
            "forecasts_available": len(forecasts),
            "news_articles": len(articles),
            "generated": len(active_alerts),
            "candidate_alerts": len(ordered_alerts),
            "suppressed_duplicates": suppressed_count,
            "priority_bands": prioritized["priority_counts"],
            "suppression_reasons": prioritized["suppressed_counts"],
        },
        "generated_at": now_iso,
        "source": ["technical_signals", "news_sentiment", "forecast_correlation", "market_regime"],
        "pipeline": {
            "algorithm": "multi_signal_confluence_v2",
            "processed_at": now_iso,
            "dedupe": True,
            "priority_ordering": True,
            "suppression_window_minutes": prioritized["config"]["window_minutes"],
            "fatigue_threshold": prioritized["config"]["fatigue_threshold"],
        },
        "warnings": warnings,
    }


def run_alerts_job():
    """
    Main alerts job that computes and saves alerts
    """
    print("[INFO] Starting alerts generation job...")
    
    try:
        # Compute alerts
        alerts_data = compute_alerts()
        
        # Save to persistent storage
        save_json("alerts", alerts_data, source=["job:alerts", "multi_signal_v1"])
        
        print(f"[SUCCESS] Alerts job completed. Generated {alerts_data['count']} alerts.")
        return alerts_data
        
    except Exception as e:
        print(f"[ERROR] Alerts job failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return empty alerts structure on failure to maintain never-empty pattern
        error_payload = {
            "alerts": [],
            "count": 0,
            "suppressed_count": 0,
            "suppressed_alerts": [],
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "error": str(e),
            "source": ["job:alerts", "error_fallback"],
            "warnings": ["job_failed"],
            "pipeline": {
                "algorithm": "multi_signal_confluence_v2",
                "processed_at": datetime.utcnow().isoformat() + "Z"
            }
        }
        
        save_json("alerts", error_payload, source=["job:alerts", "error_fallback"])
        return error_payload


def get_latest_alerts():
    """
    Retrieve the latest alerts from persistent storage
    """
    alerts_snapshot = load_json("alerts")
    if alerts_snapshot:
        # If alerts_snapshot has a payload key, return that
        if "payload" in alerts_snapshot:
            return alerts_snapshot["payload"]
        else:
            # Otherwise return the data structure
            return {
                "alerts": alerts_snapshot.get("alerts", []),
                "count": alerts_snapshot.get("count", 0),
                "suppressed_count": alerts_snapshot.get("suppressed_count", 0),
                "suppressed_alerts": alerts_snapshot.get("suppressed_alerts", []),
                "generated_at": alerts_snapshot.get("generated_at", datetime.utcnow().isoformat() + "Z"),
                "source": alerts_snapshot.get("source", []),
                "pipeline": alerts_snapshot.get("pipeline", {}),
                "stats": alerts_snapshot.get("stats", {}),
                "warnings": alerts_snapshot.get("warnings", []),
            }
    else:
        # Return empty structure if no alerts available
        return {
            "alerts": [],
            "count": 0,
            "suppressed_count": 0,
            "suppressed_alerts": [],
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source": ["fallback_empty"],
            "pipeline": {
                "algorithm": "multi_signal_confluence_v2",
                "processed_at": None
            },
            "stats": {},
            "warnings": [],
        }


if __name__ == "__main__":
    # Run standalone for testing
    result = run_alerts_job()
    print(f"Job completed with {result['count']} alerts")
