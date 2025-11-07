"""
Market Intelligence & Context Service

Builds the data served to `/api/intelligence/snapshot` and `/api/context/current`
by aggregating existing persisted datasets (forecasts, briefs, news).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional, Tuple

from storage.io import load_json

# ---------- helpers ----------

def _now() -> datetime:
    return datetime.now(timezone.utc)

def _parse_timestamp(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # assume unix epoch seconds
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            return None
    if isinstance(value, str):
        try:
            if value.endswith("Z"):
                value = value.replace("Z", "+00:00")
            return datetime.fromisoformat(value)
        except Exception:
            return None
    return None

def _humanize_age(ts: Optional[datetime]) -> str:
    if not ts:
        return "unknown"
    delta = _now() - ts
    seconds = max(0, int(delta.total_seconds()))
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"

def _safe_rows(payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not payload:
        return []
    if isinstance(payload, list):
        return payload
    if "rows" in payload and isinstance(payload["rows"], list):
        return payload["rows"]
    if "data" in payload and isinstance(payload["data"], list):
        return payload["data"]
    return []

# ---------- loading sources ----------

def _load_forecasts() -> List[Dict[str, Any]]:
    return _safe_rows(load_json("forecasts") or load_json("forecast"))

def _load_brief() -> Dict[str, Any]:
    payload = load_json("brief_daily") or {}
    return payload.get("data") or {}

def _load_news() -> List[Dict[str, Any]]:
    payload = load_json("news_feed") or {}
    articles = payload.get("articles")
    return articles if isinstance(articles, list) else []

# ---------- intelligence builders ----------

@dataclass
class RegimeMetrics:
    regime: str
    confidence: float
    explanation: str

def _classify_regime(rows: List[Dict[str, Any]]) -> RegimeMetrics:
    bullish = []
    bearish = []
    for row in rows:
        er = row.get("expected_return")
        conf = row.get("confidence", 0)
        if er is None or conf is None:
            continue
        weight = max(0.0, float(conf)) * float(er)
        if er > 0:
            bullish.append(weight)
        elif er < 0:
            bearish.append(weight)

    bull_score = sum(bullish)
    bear_score = sum(abs(x) for x in bearish)
    net = bull_score - bear_score
    total = bull_score + bear_score + 1e-6
    confidence = min(1.0, abs(net) / total)

    if net > 0.02:
        regime = "BULL_MARKET"
    elif net < -0.02:
        regime = "BEAR_MARKET"
    elif net > 0.005:
        regime = "RISK_ON"
    elif net < -0.005:
        regime = "RISK_OFF"
    else:
        regime = "NORMAL"

    explanation = (
        f"Bullish pressure {bull_score:+.2f} vs bearish {bear_score:+.2f}. "
        f"Net skew {net:+.2f} ({confidence*100:.0f}% confidence)."
    )
    return RegimeMetrics(regime=regime, confidence=round(confidence, 2), explanation=explanation)

def _select_opportunities(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered = [
        r for r in rows
        if r.get("expected_return") is not None
        and r.get("expected_return", 0) > 0
        and r.get("confidence", 0) >= 0.55
    ]
    filtered.sort(key=lambda r: (r.get("expected_return", 0), r.get("confidence", 0)), reverse=True)
    opportunities = []
    for row in filtered[:3]:
        er = float(row["expected_return"])
        confidence = float(row.get("confidence", 0))
        ticker = row.get("ticker", "N/A")
        horizon = row.get("horizon", "")
        direction = row.get("direction", "").upper()
        reasoning = (
            f"{ticker} {horizon} horizon expects {er*100:+.2f}% ({direction}) "
            f"with {confidence*100:.0f}% confidence."
        )
        opportunities.append({
            "ticker": ticker,
            "reasoning": reasoning,
            "confidence": round(confidence, 3),
        })
    return opportunities

def _severity_from_move(er: float, confidence: float) -> str:
    magnitude = abs(er)
    if magnitude >= 0.02 or confidence >= 0.8:
        return "HIGH"
    if magnitude >= 0.01 or confidence >= 0.6:
        return "MEDIUM"
    return "LOW"

def _select_risks(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered = [
        r for r in rows
        if r.get("expected_return") is not None
        and r.get("expected_return", 0) < 0
        and r.get("confidence", 0) >= 0.55
    ]
    filtered.sort(key=lambda r: (abs(r.get("expected_return", 0)), r.get("confidence", 0)), reverse=True)
    risks = []
    for row in filtered[:3]:
        er = float(row["expected_return"])
        confidence = float(row.get("confidence", 0))
        ticker = row.get("ticker", "N/A")
        horizon = row.get("horizon", "")
        severity = _severity_from_move(er, confidence)
        risks.append({
            "type": ticker.upper(),
            "description": (
                f"{ticker} {horizon} forecast sees {er*100:.2f}% downside "
                f"with {confidence*100:.0f}% confidence."
            ),
            "severity": severity,
        })
    return risks

DRIVER_KEYWORDS = {
    "Fed & Rates": ["fed", "treasury", "yield", "rate", "bond"],
    "AI & Tech": ["ai", "chip", "semiconductor", "nvidia", "apple", "microsoft", "google"],
    "Energy": ["oil", "brent", "gas", "energy", "opec"],
    "Geopolitics": ["war", "conflict", "sanction", "geopolitics"],
    "Consumer": ["consumer", "retail", "spending", "jobs", "employment"],
}

def _extract_news_drivers(news: List[Dict[str, Any]]) -> List[str]:
    scores = {label: 0 for label in DRIVER_KEYWORDS}
    for article in news[:200]:
        title = (article.get("title") or "").lower()
        desc = (article.get("description") or "").lower()
        blob = f"{title} {desc}"
        for label, keywords in DRIVER_KEYWORDS.items():
            if any(word in blob for word in keywords):
                scores[label] += 1
    ranked = sorted(
        [label for label, count in scores.items() if count > 0],
        key=lambda label: scores[label],
        reverse=True,
    )
    return ranked[:3]

def _from_brief_drivers(brief: Dict[str, Any]) -> List[str]:
    drivers = []
    for entry in brief.get("top_signals", [])[:3]:
        ticker = entry.get("ticker")
        score = entry.get("composite_score")
        if ticker and score is not None:
            drivers.append(f"{ticker} signal {score:+.2f}")
    return drivers

def _build_drivers(news: List[Dict[str, Any]], brief: Dict[str, Any]) -> List[str]:
    drivers = _extract_news_drivers(news)
    if len(drivers) < 3:
        drivers.extend(_from_brief_drivers(brief))
    # deduplicate preserving order
    seen = set()
    ordered = []
    for driver in drivers:
        if driver not in seen:
            seen.add(driver)
            ordered.append(driver)
    return ordered[:4]

def _news_sentiment_label(news: List[Dict[str, Any]]) -> Tuple[str, float]:
    # Without sentiment field, approximate using keywords (positive vs negative)
    positive_keywords = ["beat", "growth", "upgrade", "surge", "rise"]
    negative_keywords = ["cut", "downgrade", "crash", "drop", "slump", "war", "sanction"]
    pos = neg = 0
    for article in news[:200]:
        text = (article.get("title") or "").lower()
        if any(word in text for word in positive_keywords):
            pos += 1
        if any(word in text for word in negative_keywords):
            neg += 1
    total = pos + neg
    if total == 0:
        return "neutral", 0.0
    score = (pos - neg) / total
    if score > 0.2:
        label = "bullish"
    elif score < -0.2:
        label = "bearish"
    else:
        label = "neutral"
    return label, score

def _build_summary(opps: List[Dict[str, Any]], risks: List[Dict[str, Any]], sentiment_label: str) -> str:
    if opps:
        tickers = ", ".join(o["ticker"] for o in opps)
        return (
            f"{sentiment_label.capitalize()} tone with opportunities led by {tickers}. "
            "Focus on top bullish setups while monitoring downside alerts."
        )
    if risks:
        tickers = ", ".join(r["type"] for r in risks)
        return (
            f"{sentiment_label.capitalize()} tone with elevated risks on {tickers}. "
            "Defensive posture recommended until signals improve."
        )
    return f"Market tone remains {sentiment_label}; awaiting stronger directional signals."

def _collect_data_freshness(rows: List[Dict[str, Any]], news: List[Dict[str, Any]], brief: Dict[str, Any]) -> Dict[str, str]:
    latest_forecast_ts = None
    for row in rows:
        ts = _parse_timestamp(row.get("calculation_timestamp"))
        if ts and (latest_forecast_ts is None or ts > latest_forecast_ts):
            latest_forecast_ts = ts
    latest_news_ts = None
    for article in news:
        ts = _parse_timestamp(article.get("pubDate") or article.get("timestamp"))
        if ts and (latest_news_ts is None or ts > latest_news_ts):
            latest_news_ts = ts
    brief_ts = _parse_timestamp(brief.get("generated_at") or brief.get("last_update"))
    return {
        "forecasts_age": _humanize_age(latest_forecast_ts),
        "macro_age": _humanize_age(brief_ts),
        "news_age": _humanize_age(latest_news_ts),
    }

# ---------- public builders ----------

def get_market_intelligence_snapshot() -> Dict[str, Any]:
    forecasts = _load_forecasts()
    brief = _load_brief()
    news = _load_news()

    regime_metrics = _classify_regime(forecasts)
    opportunities = _select_opportunities(forecasts)
    risks = _select_risks(forecasts)
    sentiment_label, _ = _news_sentiment_label(news)
    drivers = _build_drivers(news, brief)
    freshness = _collect_data_freshness(forecasts, news, brief)

    summary = _build_summary(opportunities, risks, sentiment_label)

    return {
        "insights": {
            "summary": summary,
            "market_regime": {
                "current": regime_metrics.regime,
                "explanation": regime_metrics.explanation,
            },
            "opportunities": opportunities,
            "risks": risks,
        },
        "data_freshness": freshness,
        "timestamp": _now().isoformat(),
        "drivers": drivers,
        "sources": {
            "forecasts": bool(forecasts),
            "brief": bool(brief),
            "news": bool(news),
        },
    }

def get_market_context_snapshot() -> Dict[str, Any]:
    forecasts = _load_forecasts()
    news = _load_news()
    brief = _load_brief()

    regime_metrics = _classify_regime(forecasts)
    drivers = _build_drivers(news, brief)
    sentiment_label, sentiment_score = _news_sentiment_label(news)

    expected_returns = [float(r.get("expected_return", 0)) for r in forecasts if r.get("expected_return") is not None]
    volatility = "medium"
    if expected_returns:
        dispersion = pstdev(expected_returns)
        if dispersion < 0.01:
            volatility = "low"
        elif dispersion < 0.02:
            volatility = "medium"
        elif dispersion < 0.035:
            volatility = "high"
        else:
            volatility = "extreme"

    net_trend = sum(expected_returns)
    if net_trend > 0.05:
        trend = "up"
    elif net_trend < -0.05:
        trend = "down"
    else:
        trend = "sideways"

    risk_level = "medium"
    if regime_metrics.regime in ("BULL_MARKET", "RISK_ON"):
        risk_level = "low" if volatility in ("low", "medium") else "medium"
    elif regime_metrics.regime in ("BEAR_MARKET", "RISK_OFF"):
        risk_level = "high"

    layout: Dict[str, Any] = {
        "primary_widgets": ["intelligence", "forecasts", "news"],
    }
    if regime_metrics.regime in ("BEAR_MARKET", "RISK_OFF"):
        layout["emphasis"] = "defensive"
        layout["secondary_widgets"] = ["risks", "macro"]
    else:
        layout["emphasis"] = "opportunities"
        layout["secondary_widgets"] = ["opportunities", "volatility"]

    characteristics = {
        "volatility": volatility,
        "sentiment": sentiment_label,
        "trend": trend,
        "momentum": "strong" if abs(net_trend) > 0.08 else "moderate" if abs(net_trend) > 0.03 else "weak",
        "risk_level": risk_level,
    }

    return {
        "regime": regime_metrics.regime,
        "confidence": regime_metrics.confidence,
        "key_drivers": drivers,
        "characteristics": characteristics,
        "recommended_layout": layout,
        "timestamp": _now().isoformat(),
    }
