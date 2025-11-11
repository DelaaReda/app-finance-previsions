"""
Market Intelligence & Context Service

Builds the data served to `/api/intelligence/snapshot` and `/api/context/current`
by aggregating existing persisted datasets (forecasts, briefs, news).
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from datetime import datetime, timezone
from statistics import pstdev
from typing import Any, Dict, List, Optional, Tuple

from storage.io import load_json
import logging

logger = logging.getLogger(__name__)

# ---------- paths & helpers ----------

DATA_DIR = Path("data")
CACHE_FILE_INTEL = DATA_DIR / "intelligence_snapshot.json"
CACHE_FILE_CONTEXT = DATA_DIR / "market_context_snapshot.json"

def _read_cache(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def _write_cache(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

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
            dt_obj = datetime.fromisoformat(value)
            return dt_obj if dt_obj.tzinfo else dt_obj.replace(tzinfo=timezone.utc)
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
    if "data" in payload:
        data = payload["data"]
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "rows" in data and isinstance(data["rows"], list):
            return data["rows"]
    return []

# ---------- loading sources ----------

def _load_forecasts() -> List[Dict[str, Any]]:
    logger.debug("📂 Loading forecasts data...")
    data = load_json("forecasts") or load_json("forecast")
    rows = _safe_rows(data)
    logger.debug(f"✅ Loaded {len(rows)} forecast rows")
    return rows

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
    valid_rows = 0
    
    for row in rows:
        # Try multiple field names for expected_return
        er = row.get("expected_return") or row.get("expectedReturn") or row.get("return") or row.get("er")
        # Try multiple field names for confidence
        conf = row.get("confidence") or row.get("conf") or row.get("score") or 0.5
        
        if er is None:
            # Try to infer from direction if available
            direction = row.get("direction", "").upper()
            if direction in ("UP", "BULLISH", "BUY"):
                er = 0.01  # Default positive return
            elif direction in ("DOWN", "BEARISH", "SELL"):
                er = -0.01  # Default negative return
            else:
                continue
        
        if conf is None:
            conf = 0.5  # Default confidence
        
        try:
            er = float(er)
            conf = float(conf)
        except (ValueError, TypeError):
            continue
        
        valid_rows += 1
        weight = max(0.0, conf) * er
        if er > 0:
            bullish.append(weight)
        elif er < 0:
            bearish.append(weight)

    bull_score = sum(bullish) if bullish else 0.0
    bear_score = sum(abs(x) for x in bearish) if bearish else 0.0
    net = bull_score - bear_score
    total = bull_score + bear_score + 1e-6
    confidence = min(1.0, abs(net) / total * 1.5) if total > 1e-6 else 0.0

    # If no valid data, return neutral
    if valid_rows == 0:
        return RegimeMetrics(
            regime="NORMAL",
            confidence=0.0,
            explanation="Insufficient forecast data for regime classification. Market analysis in progress."
        )

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
    filtered = []
    for r in rows:
        # Try multiple field names
        er = r.get("expected_return") or r.get("expectedReturn") or r.get("return") or r.get("er")
        conf = r.get("confidence") or r.get("conf") or r.get("score") or 0.3
        
        # Infer from direction if expected_return is missing
        if er is None:
            direction = r.get("direction", "").upper()
            if direction in ("UP", "BULLISH", "BUY"):
                er = 0.01
            else:
                continue
        
        try:
            er = float(er)
            conf = float(conf)
        except (ValueError, TypeError):
            continue
        
        if er > 0 and conf >= 0.20:  # Lowered threshold from 0.30 to 0.20
            filtered.append({
                **r,
                "expected_return": er,
                "confidence": conf
            })
    
    filtered.sort(key=lambda r: (r.get("expected_return", 0), r.get("confidence", 0)), reverse=True)
    opportunities = []
    for row in filtered[:3]:
        er = float(row.get("expected_return", 0))
        confidence = float(row.get("confidence", 0))
        ticker = row.get("ticker", "N/A")
        horizon = row.get("horizon", "short")  # Default to "short" if missing
        direction = row.get("direction", "").upper() or "UP"
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
    filtered = []
    for r in rows:
        # Try multiple field names
        er = r.get("expected_return") or r.get("expectedReturn") or r.get("return") or r.get("er")
        conf = r.get("confidence") or r.get("conf") or r.get("score") or 0.3
        
        # Infer from direction if expected_return is missing
        if er is None:
            direction = r.get("direction", "").upper()
            if direction in ("DOWN", "BEARISH", "SELL"):
                er = -0.01
            else:
                continue
        
        try:
            er = float(er)
            conf = float(conf)
        except (ValueError, TypeError):
            continue
        
        if er < 0 and conf >= 0.20:  # Lowered threshold from 0.30 to 0.20
            filtered.append({
                **r,
                "expected_return": er,
                "confidence": conf
            })
    
    filtered.sort(key=lambda r: (abs(r.get("expected_return", 0)), r.get("confidence", 0)), reverse=True)
    risks = []
    for row in filtered[:3]:
        er = float(row.get("expected_return", 0))
        confidence = float(row.get("confidence", 0))
        ticker = row.get("ticker", "N/A")
        horizon = row.get("horizon", "short")  # Default to "short" if missing
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

def get_market_intelligence_snapshot(use_cache: bool = True, persist: bool = True) -> Dict[str, Any]:
    import time
    start_time = time.time()
    
    logger.info(f"🧠 get_market_intelligence_snapshot called", extra={
        "use_cache": use_cache,
        "persist": persist
    })
    
    if use_cache:
        logger.debug(f"🔍 Checking cache: {CACHE_FILE_INTEL}")
        cached = _read_cache(CACHE_FILE_INTEL)
        if cached:
            logger.info(f"✅ Using cached intelligence snapshot", extra={
                "cache_file": str(CACHE_FILE_INTEL),
                "timestamp": cached.get("timestamp")
            })
            return cached
        logger.debug(f"⚠️ No cache found, generating new snapshot")

    logger.debug(f"📂 Loading data sources...")
    forecasts = _load_forecasts()
    brief = _load_brief()
    news = _load_news()
    
    logger.info(f"📊 Data loaded", extra={
        "forecasts_count": len(forecasts),
        "brief_keys": list(brief.keys())[:5] if brief else [],
        "news_count": len(news)
    })

    logger.debug(f"🔍 Classifying market regime...")
    regime_metrics = _classify_regime(forecasts)
    logger.info(f"📈 Market regime classified", extra={
        "regime": regime_metrics.regime,
        "confidence": regime_metrics.confidence
    })
    
    logger.debug(f"🔍 Selecting opportunities...")
    opportunities = _select_opportunities(forecasts)
    logger.debug(f"🔍 Selecting risks...")
    risks = _select_risks(forecasts)
    logger.info(f"🎯 Opportunities and risks selected", extra={
        "opportunities_count": len(opportunities),
        "risks_count": len(risks)
    })
    
    logger.debug(f"🔍 Analyzing news sentiment...")
    sentiment_label, _ = _news_sentiment_label(news)
    logger.debug(f"🔍 Building drivers...")
    drivers = _build_drivers(news, brief)
    logger.debug(f"🔍 Collecting data freshness...")
    freshness = _collect_data_freshness(forecasts, news, brief)

    logger.debug(f"🔍 Building summary...")
    summary = _build_summary(opportunities, risks, sentiment_label)

    snapshot = {
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

    if persist:
        _write_cache(CACHE_FILE_INTEL, snapshot)

    return snapshot

def get_market_context_snapshot(use_cache: bool = True, persist: bool = True) -> Dict[str, Any]:
    if use_cache:
        cached = _read_cache(CACHE_FILE_CONTEXT)
        if cached:
            return cached

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

    context = {
        "regime": regime_metrics.regime,
        "confidence": regime_metrics.confidence,
        "key_drivers": drivers,
        "characteristics": characteristics,
        "recommended_layout": layout,
        "timestamp": _now().isoformat(),
    }

    if persist:
        _write_cache(CACHE_FILE_CONTEXT, context)

    return context
