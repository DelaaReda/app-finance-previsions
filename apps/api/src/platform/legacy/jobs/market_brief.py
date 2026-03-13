"""
Market Brief Job Module - Generate comprehensive market briefs.
Creates daily market summaries from cached forecasts, macro data, and news.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import logging
from statistics import mean
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

try:
    from platform.legacy.jobs.alerts import get_alerting_contract_defaults
except Exception:  # pragma: no cover - fallback for older path layouts
    try:
        from src.platform.legacy.jobs.alerts import get_alerting_contract_defaults  # type: ignore
    except Exception:  # pragma: no cover
        def get_alerting_contract_defaults() -> Dict[str, Any]:
            return {
                "suppression_window_minutes": 15,
                "fatigue_threshold": 2,
                "duplicate_suppression_reason": "fatigue_window_duplicate",
                "urgent_bypass_enabled": True,
            }


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert numeric-like values to float safely."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _safe_text(value: Any, default: str = "") -> str:
    """Normalize text values."""
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _extract_rows(snapshot: Dict[str, Any] | None, rows_key: str) -> List[Dict[str, Any]]:
    """Extract row-like payload from common wrapped formats."""
    if not isinstance(snapshot, dict):
        return []

    candidates = []
    data = snapshot.get("data")
    if isinstance(data, dict) and rows_key in data:
        candidates = data.get(rows_key, [])
    elif rows_key in snapshot:
        candidates = snapshot.get(rows_key, [])
    elif isinstance(data, list):
        candidates = data

    if not isinstance(candidates, list):
        return []

    return [row for row in candidates if isinstance(row, dict)]


def _macro_signal(value: float, topic: str) -> Dict[str, Any]:
    """Map numeric score to a macro readability label."""
    if value > 0.35:
        state = "hawkish"
    elif value < -0.35:
        state = "dovish"
    else:
        state = "neutral"

    return {
        "topic": topic,
        "state": state,
        "score": round(value, 3),
        "confidence": min(1.0, round(abs(value), 3) + 0.33),
        "note": f"Signal macro {topic.lower()} dérivé de snapshot." ,
    }


def _build_sector_rotation(forecasts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute top/bottom sectors from forecast expected return by ticker sector."""
    groups = defaultdict(list)
    for row in forecasts:
        sector = _safe_text(row.get("sector"), "Unknown")
        groups[sector].append(_safe_float(row.get("expected_return", 0.0)))

    ranked = []
    for sector, values in groups.items():
        if not values:
            continue
        score = mean(values)
        ranked.append(
            {
                "sector": sector,
                "momentum": round(score, 3),
                "direction": "up" if score >= 0 else "down",
                "size": len(values),
            }
        )

    if not ranked:
        return {
            "top": [],
            "bottom": [],
            "leaders": [],
            "laggards": [],
        }

    ranked.sort(key=lambda item: item["momentum"], reverse=True)
    top = ranked[:3]
    bottom = sorted(ranked, key=lambda item: item["momentum"])[:3]

    return {
        "top": top,
        "bottom": bottom,
        "leaders": [entry["sector"] for entry in top],
        "laggards": [entry["sector"] for entry in bottom],
        "momentum_score": round(mean([abs(item["momentum"]) for item in top + bottom]), 3),
    }


def run_market_brief_job(filters: Dict = None) -> Dict[str, Any]:
    """
    Main function to run market brief generation job.
    """
    logger.info("Starting market brief generation job...")

    try:
        from storage.base import load_forecasts, load_news_feed, load_json, save_json

        forecasts_data = load_forecasts() if callable(load_forecasts) else None
        news_data = load_news_feed() if callable(load_news_feed) else None
        macro_data = load_json("macro_series.json") if callable(load_json) else None

        forecasts = _extract_rows(forecasts_data, "rows")
        news_articles = _extract_rows(news_data, "articles")

        bullish = sorted(
            [row for row in forecasts if _safe_text(row.get("direction")) == "up"],
            key=lambda row: _safe_float(row.get("confidence", 0.5)) * abs(_safe_float(row.get("expected_return", 0.0)),),
            reverse=True,
        )
        bearish = sorted(
            [row for row in forecasts if _safe_text(row.get("direction")) == "down"],
            key=lambda row: _safe_float(row.get("confidence", 0.5)) * abs(_safe_float(row.get("expected_return", 0.0))),
            reverse=True,
        )

        positive_news = [
            article for article in news_articles if _safe_text(article.get("sentiment")).lower() == "positive"
        ]
        negative_news = [
            article for article in news_articles if _safe_text(article.get("sentiment")).lower() == "negative"
        ]

        macro_series = {}
        if isinstance(macro_data, dict):
            macro_series = macro_data.get("series", macro_data.get("data", {})) or {}
        if not isinstance(macro_series, dict):
            macro_series = {}

        fed_score = 0.0
        cpi_score = 0.0
        geo_score = 0.0
        for key, value in macro_series.items():
            key_l = _safe_text(key).lower()
            score = _safe_float(value)
            if "fed" in key_l or "rate" in key_l:
                fed_score += score
            if "cpi" in key_l or "infl" in key_l:
                cpi_score += score
            if "geo" in key_l or "risk" in key_l or "vix" in key_l:
                geo_score += score

        macro_signals = [
            _macro_signal(fed_score, "Fed"),
            _macro_signal(cpi_score, "Inflation"),
            _macro_signal(geo_score, "Géopolitique"),
        ]

        top_signals = []
        for row in bullish[:3]:
            top_signals.append(
                {
                    "ticker": _safe_text(row.get("ticker"), "MARKET"),
                    "signal": "strong_bullish",
                    "confidence": round(_safe_float(row.get("confidence", 0.5)), 3),
                    "horizon": _safe_text(row.get("horizon"), "1d"),
                    "reason": _safe_text(row.get("reasoning", ""), "Bullish signal from model."),
                    "expected_return": round(_safe_float(row.get("expected_return", 0.0)), 3),
                    "source": _safe_text(row.get("model", "forecasts")),
                }
            )

        alerting_contract = get_alerting_contract_defaults()
        suppression_window_minutes = max(
            1,
            int(alerting_contract.get("suppression_window_minutes", 15) or 15),
        )
        duplicate_suppression_reason = str(
            alerting_contract.get("duplicate_suppression_reason") or "fatigue_window_duplicate"
        )
        urgent_bypass_enabled = bool(alerting_contract.get("urgent_bypass_enabled", True))

        top_risks = []
        suppressed_risks = []
        seen_risk_fingerprints = {}
        for row in bearish:
            ticker = _safe_text(row.get("ticker"), "MARKET")
            confidence = _safe_float(row.get("confidence", 0.0))
            expected_return = round(_safe_float(row.get("expected_return", 0.0)), 3)
            horizon = _safe_text(row.get("horizon"), "1d")
            severity = "high" if confidence > 0.7 else "medium"
            priority = "urgent" if severity == "high" and expected_return <= -0.03 else severity
            alert_fingerprint = f"{ticker}:{horizon}:bearish"
            duplicate_count = int(seen_risk_fingerprints.get(alert_fingerprint, 0) or 0)
            urgent_bypass = urgent_bypass_enabled and priority == "urgent" and duplicate_count > 0
            base_risk = {
                "ticker": ticker,
                "risk": "bearish",
                "severity": severity,
                "priority": priority,
                "priority_score": round((confidence * 100.0) + max(0.0, abs(min(expected_return, 0.0)) * 1000.0), 2),
                "probability": round(confidence, 3),
                "impact": _safe_text(row.get("sector", "equity"), "equity"),
                "mitigation": _safe_text(row.get("reasoning", ""), "Revenir au monitorage technique."),
                "expected_return": expected_return,
                "source": _safe_text(row.get("model", "forecasts")),
                "horizon": horizon,
                "alert_fingerprint": alert_fingerprint,
                "suppression_window_minutes": suppression_window_minutes,
            }
            seen_risk_fingerprints[alert_fingerprint] = duplicate_count + 1
            if duplicate_count > 0 and not urgent_bypass:
                suppressed_risks.append(
                    {
                        **base_risk,
                        "suppressed": True,
                        "suppression_reason": duplicate_suppression_reason,
                        "duplicate_count": duplicate_count,
                        "urgent_bypass": False,
                    }
                )
                continue
            top_risks.append(
                {
                    **base_risk,
                    "priority_rank": len(top_risks) + 1,
                    "suppressed": False,
                    "suppression_reason": "",
                    "duplicate_count": duplicate_count,
                    "urgent_bypass": urgent_bypass,
                }
            )
            if len(top_risks) >= 3:
                break

        bullish_count = len(bullish)
        bearish_count = len(bearish)
        if bullish_count > bearish_count * 1.5:
            market_sentiment = "BULLISH"
        elif bearish_count > bullish_count * 1.5:
            market_sentiment = "BEARISH"
        else:
            market_sentiment = "MIXED"

        picks = [item.get("ticker") for item in bullish[:2] if item.get("ticker")]

        sectors = _build_sector_rotation(forecasts)
        summary = (
            f"Daily market brief: {market_sentiment}. "
            f"{bullish_count} opportunités haussières, {bearish_count} risques majeurs. "
            f"{len(positive_news)} top nouvelles positives, {len(negative_news)} négatives. "
            f"Leaders: {', '.join([entry.get('sector', 'N/A') for entry in sectors.get('top', [])]) or 'N/A'}"
        )

        brief_data = {
            "title": "Brief quotidien",
            "period": "daily",
            "summary": summary,
            "market_sentiment": market_sentiment,
            "source": ["market_brief_job"],
            "top_signals": top_signals,
            "top_risks": top_risks,
            "suppressed_risks": suppressed_risks,
            "picks": picks,
            "macro_signals": macro_signals,
            "sector_rotation": sectors,
            "alerting_metadata": {
                **alerting_contract,
                "suppression_window_minutes": suppression_window_minutes,
                "suppressed_risk_count": len(suppressed_risks),
                "priority_model": "severity_plus_expected_return",
            },
        }

        save_json(brief_data, "brief_daily.json", source=["job:market_brief", "forecasts", "news", "macro"])

        result = {
            "brief_generated": True,
            "models_used": ["market_brief_job", "forecasts", "news", "macro_series"],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "completed",
            "brief_data": brief_data,
            "brief_count": len(top_signals),
            "forecasts_analyzed": len(forecasts),
            "news_analyzed": len(news_articles),
            "source": ["market_brief_generator", "forecasts", "news", "macro_series"],
            "summary": brief_data["summary"],
            "market_sentiment": market_sentiment,
        }

        logger.info("✅ Market brief job completed successfully.")
        return result

    except Exception as e:
        logger.error(f"Market brief job failed: {str(e)}", exc_info=True)
        return {
            "brief_generated": False,
            "models_used": [],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "failed",
            "error": str(e)
        }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    result = run_market_brief_job()
    print(f"\n✅ Market brief job completed: {result}")
