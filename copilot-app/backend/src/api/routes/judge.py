"""
Judge API Routes - merged version with options + caching
"""
from datetime import datetime, timezone
import json
import logging
import asyncio
import os
from copy import deepcopy
from pathlib import Path
import time
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Query, HTTPException
from statistics import stdev

# Ensure nested event loops don't break g4f client
try:
    import nest_asyncio

    nest_asyncio.apply()
except Exception:
    pass

try:
    from src.core.response import ok, err
except Exception:  # pragma: no cover
    def ok(data):
        return {"ok": True, "data": data}

    def err(msg, code=500):
        return {"ok": False, "error": msg, "code": code}


from storage.io import load_json

try:
    from services.cache_layer import load_or_compute
except ImportError:  # pragma: no cover
    def load_or_compute(key, compute_fn, **_):
        return compute_fn()


# Dynamic working models (OpenRouter/DeepInfra)
try:
    from agents.g4f_model_watcher import ensure_working_models
except Exception:
    ensure_working_models = None

# Optional LLM judge (econ_llm_agent)
try:
    from analytics.econ_llm_agent import EconomicAnalyst, EconomicInput  # type: ignore
except Exception as e:  # pragma: no cover
    EconomicAnalyst = None  # type: ignore
    EconomicInput = None  # type: ignore
    _LLM_IMPORT_ERROR = e
else:
    _LLM_IMPORT_ERROR = None

# Optional ML prior
try:
    from analytics.ml_baseline import ml_predict_next_return
except Exception:
    ml_predict_next_return = None

# Phase adapter (lightweight summaries)
try:
    from analytics.phases_adapter import build_phase_blocks
except Exception:
    build_phase_blocks = None

# Judge pipeline helpers (scoring, payload, validation)
try:
    from services.judge_pipeline import (
        score_news,
        build_payload,
        parse_llm_answer,
        validate_llm_response,
        log_metrics,
    )
except Exception:
    score_news = None
    build_payload = None
    parse_llm_answer = None
    validate_llm_response = None
    log_metrics = None

# Codestral fallback client
try:
    from services.codestral_client import call_codestral  # type: ignore
except Exception:
    call_codestral = None
# Typed verdict builder (Pydantic schemas)
try:
    from services.judge_builder import build_judge_verdict  # type: ignore
except Exception:
    build_judge_verdict = None
# G4F fallback client
try:
    from services.g4f_client import call_g4f  # type: ignore
except Exception:
    call_g4f = None
# Groq (Grok) client (utilisé aussi comme réparateur)
try:
    from services.groq_client import call_groq  # type: ignore
except Exception:
    call_groq = None

logger = logging.getLogger(__name__)

JUDGE_VERSION = "v3"
JUDGE_CACHE_TTL_SECONDS = max(
    0, int(os.getenv("JUDGE_CACHE_TTL_SECONDS", "120") or "120")
)
JUDGE_CACHE_MAX_ENTRIES = max(
    1, int(os.getenv("JUDGE_CACHE_MAX_ENTRIES", "64") or "64")
)
_JUDGE_RESPONSE_CACHE: Dict[str, Dict[str, Any]] = {}

TICKER_NEWS_ALIAS_TERMS: Dict[str, List[str]] = {
    "SPY": ["S&P 500", "SP500", "SPX", "S AND P 500"],
    "QQQ": ["NASDAQ 100", "NASDAQ-100", "NDX"],
    "TSLA": ["TESLA", "ELON MUSK", "MUSK"],
    "AAPL": ["APPLE", "IPHONE"],
    "GOOGL": ["GOOGLE", "ALPHABET"],
    "MSFT": ["MICROSOFT"],
    "AMZN": ["AMAZON"],
    "META": ["META", "FACEBOOK"],
    "NVDA": ["NVIDIA"],
}

router = APIRouter(prefix="/api/judge", tags=["judge"])


def _judge_cache_key(
    *,
    limit: int,
    min_confidence: float,
    ticker: Optional[List[str]],
    sort_by: Optional[str],
    sort_order: Optional[str],
    profile: str,
) -> str:
    tickers = sorted({t.upper() for t in (ticker or [])})
    key_obj = {
        "v": JUDGE_VERSION,
        "limit": int(limit),
        "min_confidence": float(min_confidence),
        "ticker": tickers,
        "sort_by": sort_by or "confidence",
        "sort_order": sort_order or "desc",
        "profile": profile or "equity_1w",
    }
    return json.dumps(key_obj, sort_keys=True, separators=(",", ":"))


def _prune_judge_cache() -> None:
    if len(_JUDGE_RESPONSE_CACHE) <= JUDGE_CACHE_MAX_ENTRIES:
        return
    # Evict oldest entries first.
    old_keys = sorted(
        _JUDGE_RESPONSE_CACHE.keys(),
        key=lambda k: _JUDGE_RESPONSE_CACHE[k].get("ts", 0.0),
    )
    for key in old_keys[: len(_JUDGE_RESPONSE_CACHE) - JUDGE_CACHE_MAX_ENTRIES]:
        _JUDGE_RESPONSE_CACHE.pop(key, None)


def _normalize_ts_str(ts: Any) -> Optional[str]:
    """Normalize timestamp-like values to an ISO string."""
    if ts is None:
        return None
    try:
        if isinstance(ts, str):
            return ts
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
        if hasattr(ts, "isoformat"):
            return ts.isoformat()
    except Exception:
        return None
    return str(ts)


def _compute_price_features(points: List[List[Any]]) -> Dict[str, Any]:
    """Compute multi-horizon price stats from OHLC (ts, close)."""
    if not points:
        return {}
    pts = sorted(points, key=lambda x: x[0])
    closes = [float(p[1]) for p in pts if len(p) >= 2]
    if len(closes) < 2:
        return {}

    def ret(period: int) -> Optional[float]:
        if len(closes) <= period:
            return None
        return (closes[-1] / closes[-period - 1]) - 1.0

    def realized_vol(period: int) -> Optional[float]:
        if len(closes) <= period:
            return None
        rets = []
        for i in range(len(closes) - period, len(closes) - 1):
            if closes[i] != 0:
                rets.append((closes[i + 1] - closes[i]) / closes[i])
        if len(rets) < 2:
            return None
        try:
            return float(stdev(rets))
        except Exception:
            return None

    def max_drawdown(period: int) -> Optional[float]:
        if len(closes) <= period:
            return None
        window = closes[-period - 1 :]
        peak = window[0]
        dd = 0.0
        for c in window[1:]:
            if c > peak:
                peak = c
            dd = min(dd, (c / peak) - 1.0)
        return dd

    price_min_1y = min(closes[-252:]) if len(closes) >= 5 else min(closes)
    price_max_1y = max(closes[-252:]) if len(closes) >= 5 else max(closes)
    last = closes[-1]
    price_vs_high = last / price_max_1y if price_max_1y else None
    price_vs_low = last / price_min_1y if price_min_1y else None

    stats = {
        "ret_1d": ret(1),
        "ret_5d": ret(5),
        "ret_1m": ret(21),
        "ret_3m": ret(63),
        "ret_6m": ret(126),
        "ret_1y": ret(252),
        "vol_1m": realized_vol(21),
        "vol_3m": realized_vol(63),
        "vol_1y": realized_vol(252),
        "max_drawdown_3m": max_drawdown(63),
        "max_drawdown_1y": max_drawdown(252),
        "price_vs_1y_high": price_vs_high,
        "price_vs_1y_low": price_vs_low,
    }

    def trend_state(ret3m: Optional[float]) -> Optional[str]:
        if ret3m is None:
            return None
        if ret3m > 0.05:
            return "up"
        if ret3m < -0.05:
            return "down"
        return "range"

    stats["trend_state_3m"] = trend_state(stats.get("ret_3m"))
    return {k: v for k, v in stats.items() if v is not None}


def _price_profile_from_stats(stats: Dict[str, Any]) -> Dict[str, str]:
    def fmt_pct(x: Optional[float]) -> str:
        if x is None:
            return "n/a"
        return f"{x*100:.1f}%"

    short = f"Ret 5d={fmt_pct(stats.get('ret_5d'))}, ret 1m={fmt_pct(stats.get('ret_1m'))}"
    medium = f"3m={fmt_pct(stats.get('ret_3m'))}, 6m={fmt_pct(stats.get('ret_6m'))}"
    long = f"1y={fmt_pct(stats.get('ret_1y'))}, vs 1y high={fmt_pct(stats.get('price_vs_1y_high') and stats.get('price_vs_1y_high')-1)}"
    return {
        "short_term": short,
        "medium_term": medium,
        "long_term": long,
    }


def _sentiment_windows(news_items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Aggregate sentiment on 24h/3d/7d/30d based on ingested_at."""
    if not news_items:
        return {}
    windows = {
        "24h": 24,
        "3d": 72,
        "7d": 168,
        "30d": 720,
    }
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    out: Dict[str, Dict[str, Any]] = {}
    for label, hours in windows.items():
        pos = neg = neu = 0
        scores: List[float] = []
        for n in news_items:
            ts = n.get("ingested_at") or n.get("ts") or n.get("published_at")
            if not ts:
                continue
            try:
                nts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                continue
            if nts.tzinfo is None:
                nts = nts.replace(tzinfo=timezone.utc)
            delta_h = (now - nts).total_seconds() / 3600.0
            if delta_h > hours:
                continue
            sc = n.get("score") or n.get("sentiment_score") or n.get("sent")
            label_sent = (n.get("sentiment") or "").lower()
            if sc is None:
                if label_sent == "positive":
                    sc = 1.0
                elif label_sent == "negative":
                    sc = -1.0
                elif label_sent == "neutral":
                    sc = 0.0
            try:
                fsc = float(sc)
                scores.append(fsc)
                if fsc > 0:
                    pos += 1
                elif fsc < 0:
                    neg += 1
                else:
                    neu += 1
            except Exception:
                continue
        if scores or pos or neg or neu:
            avg = sum(scores) / len(scores) if scores else None
            out[label] = {
                "avg": avg,
                "count": len(scores) if scores else pos + neg + neu,
                "pos": pos,
                "neg": neg,
                "neu": neu,
            }
    return out


def _sentiment_profile(sent_win: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Derive simple trend/skew from sentiment_windows."""
    w7 = sent_win.get("7d", {}) if isinstance(sent_win, dict) else {}
    w30 = sent_win.get("30d", {}) if isinstance(sent_win, dict) else {}

    def trend():
        a7 = w7.get("avg")
        a30 = w30.get("avg")
        if a7 is None or a30 is None:
            return None
        diff = a7 - a30
        if diff > 5:
            return "improving"
        if diff < -5:
            return "worsening"
        return "stable"

    def skew():
        if not w7.get("count"):
            return None
        pos = w7.get("pos", 0)
        neg = w7.get("neg", 0)
        if pos >= 2 * max(1, neg):
            return "mostly_positive"
        if neg >= 2 * max(1, pos):
            return "mostly_negative"
        return "mixed"

    return {
        "trend_7d_vs_30d": trend(),
        "skew_7d": skew(),
        "summary": f"Flux: {w7.get('count', 0)} news/7j, avg7d={w7.get('avg')}, avg30d={w30.get('avg')}",
    }


def _fundamentals_profile(fund: Dict[str, Any]) -> Dict[str, Any]:
    """Bucket valuation/growth/risk to guide LLM."""
    pe = fund.get("pe") or fund.get("pe_ratio")
    beta = fund.get("beta")
    growth = fund.get("revenueGrowth") or fund.get("revenue_growth")
    margin = fund.get("profitMargins") or fund.get("profit_margin")

    def bucket_pe(v):
        if v is None:
            return None
        if v < 10:
            return "very_cheap"
        if v < 18:
            return "cheap"
        if v < 25:
            return "fair"
        if v < 40:
            return "expensive"
        return "very_expensive"

    def bucket_beta(v):
        if v is None:
            return None
        if v < 0.8:
            return "low_risk"
        if v < 1.2:
            return "normal_risk"
        if v < 1.8:
            return "elevated_risk"
        return "high_risk"

    valuation = bucket_pe(pe)
    beta_label = bucket_beta(beta)
    if growth is not None:
        growth_label = (
            "high_growth" if growth > 0.15 else "moderate_growth" if growth > 0.05 else "low_growth"
        )
    else:
        growth_label = None
    if margin is not None:
        margin_label = (
            "high_margin" if margin > 0.3 else "moderate_margin" if margin > 0.1 else "low_margin"
        )
    else:
        margin_label = None

    if beta_label in ("elevated_risk", "high_risk"):
        risk_profile = "high_beta"
    elif beta_label == "low_risk":
        risk_profile = "defensive"
    else:
        risk_profile = "balanced"

    return {
        "valuation": valuation,
        "growth_label": growth_label,
        "margin_label": margin_label,
        "beta_label": beta_label,
        "risk_profile": risk_profile,
    }


def _macro_profile(macro: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize macro context into buckets."""
    vix = macro.get("vix")
    us10y_delta = macro.get("us10y_delta_1m")
    dxy = macro.get("dxy")
    if vix is None:
        vix_level = None
    elif vix < 15:
        vix_level = "low"
    elif vix < 25:
        vix_level = "normal"
    else:
        vix_level = "high"

    if us10y_delta is None:
        us10y_trend = None
    elif us10y_delta > 0.005:
        us10y_trend = "rising"
    elif us10y_delta < -0.005:
        us10y_trend = "falling"
    else:
        us10y_trend = "stable"

    return {
        "vix_level": vix_level,
        "vix_value": vix,
        "us10y_trend": us10y_trend,
        "dxy_value": dxy,
    }


@router.get("")
async def get_judge_verdicts(
    limit: int = Query(20, ge=1, le=100, description="Limite de résultats (1-100)"),
    min_confidence: float = Query(
        0.3, ge=0.0, le=1.0, description="Confiance minimum pour inclusion (0.0-1.0)"
    ),
    ticker: Optional[List[str]] = Query(
        None, description="Filtre par ticker (plusieurs autorisés)"
    ),
    sort_by: Optional[str] = Query(
        "confidence",
        description="Tri par: confidence, expected_return, score, risk_level, timestamp",
    ),
    sort_order: Optional[str] = Query("desc", description="Ordre de tri: asc, desc"),
    profile: str = Query("equity_1w", description="Judge profile: equity_1w, sector_regime, etc"),
    debug: bool = Query(False, description="Active les traces et le payload LLM dans la réponse"),
):
    """Get LLM judge verdicts for tickers (never-empty, cached). Supports multiple profiles."""
    logger.info(f"🔍 /api/judge called: limit={limit}, profile={profile}, ticker={ticker}")
    try:
        cache_key: Optional[str] = None
        if not debug and JUDGE_CACHE_TTL_SECONDS > 0:
            cache_key = _judge_cache_key(
                limit=limit,
                min_confidence=min_confidence,
                ticker=ticker,
                sort_by=sort_by,
                sort_order=sort_order,
                profile=profile,
            )
            cached_entry = _JUDGE_RESPONSE_CACHE.get(cache_key)
            if cached_entry and isinstance(cached_entry.get("data"), dict):
                age_seconds = time.time() - float(cached_entry.get("ts", 0.0))
                if age_seconds < JUDGE_CACHE_TTL_SECONDS:
                    cached_data = deepcopy(cached_entry["data"])
                    source = cached_data.get("source")
                    if isinstance(source, list):
                        if "judge_cache_hit" not in source:
                            source.append("judge_cache_hit")
                    else:
                        cached_data["source"] = ["judge_route", "judge_cache_hit"]
                    cached_data["cache"] = {
                        "hit": True,
                        "age_seconds": round(age_seconds, 3),
                        "ttl_seconds": JUDGE_CACHE_TTL_SECONDS,
                    }
                    return {
                        "ok": True,
                        "data": cached_data,
                        "freshness": cached_data.get(
                            "generated_at", datetime.utcnow().isoformat() + "Z"
                        ),
                    }
                _JUDGE_RESPONSE_CACHE.pop(cache_key, None)

        async def compute_judge_verdicts():
            logger.info("🔄 compute_judge_verdicts started")
            traces: List[Dict[str, Any]] = []

            def add_trace(event: str, **kwargs):
                if not debug:
                    return
                try:
                    traces.append(
                        {
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                            "event": event,
                            **kwargs,
                        }
                    )
                except Exception:
                    pass

            add_trace("debug_start", limit=limit, profile=profile, ticker=ticker)

            if _LLM_IMPORT_ERROR or not EconomicAnalyst or not EconomicInput:
                logger.error(f"❌ LLM import error: {_LLM_IMPORT_ERROR}")
                raise HTTPException(
                    status_code=500,
                    detail=f"econ_llm_agent unavailable: {_LLM_IMPORT_ERROR}",
                )

            # Base data (forecasts + news + macro/brief snapshot)
            logger.info("📊 Loading data...")
            add_trace("data_load_start")
            forecasts = load_json("forecasts") or {}
            news_feed = load_json("news_feed") or {}
            brief_daily = load_json("brief_daily") or load_json("brief_weekly") or {}

            backend_root = Path(__file__).resolve().parents[3]

            # Raw data for prices/macro (re-used for tech/macro features)
            prices_path = backend_root / "data" / "stocks" / "prices.json"
            macro_path = backend_root / "data" / "macro_series.json"
            ownership_path = backend_root / "data" / "ownership_snapshot.json"
            judge_features_path = backend_root / "data" / "judge_features.json"

            yahoo_cache: Dict[str, Dict[str, Any]] = {}

            # Load judge profile
            prof = None
            try:
                logger.info(f"🎯 Loading profile: {profile}")
                from services.judge_pipeline import load_profile
                prof = load_profile(profile)
                logger.info(
                    "✅ Profile loaded: name=%s horizon=%s focus=%s tickers=%d max_tokens=%s",
                    getattr(prof, "name", profile),
                    getattr(prof, "horizon", None),
                    getattr(prof, "focus", None),
                    len(getattr(prof, "tickers", []) or []),
                    getattr(prof, "max_tokens", None),
                )
            except FileNotFoundError as e:
                logger.warning(f"⚠️ Profile '{profile}' not found: {e}, using default")
                prof = None
            except Exception as e:
                logger.error(f"❌ Failed to load profile '{profile}': {e}", exc_info=True)
                prof = None

            def _load_judge_features():
                try:
                    return json.loads(judge_features_path.read_text()).get("tickers", {})
                except Exception:
                    return {}

            def _load_prices():
                try:
                    return json.loads(prices_path.read_text()).get("tickers", {})
                except Exception:
                    return {}

            def _load_macro():
                try:
                    return json.loads(macro_path.read_text()).get("series", {})
                except Exception:
                    return {}

            def _load_ownership():
                try:
                    return json.loads(ownership_path.read_text())
                except Exception:
                    return {}

            # Counts for debug visibility
            def _forecasts_count():
                rows_local = (
                    forecasts.get("rows")
                    or forecasts.get("data", {}).get("rows", [])
                    or []
                )
                return len(rows_local)

            def _news_count():
                articles_local = (
                    news_feed.get("articles")
                    or news_feed.get("data", {}).get("articles", [])
                    or []
                )
                return len(articles_local)

            add_trace(
                "data_loaded",
                forecasts=_forecasts_count(),
                news_count=_news_count(),
            )

            prices_data = _load_prices()
            macro_series = _load_macro()
            ownership_data = _load_ownership()
            judge_features = _load_judge_features()

            def _yahoo_snapshot(sym: str) -> Dict[str, Any]:
                symu = sym.upper()
                if symu in yahoo_cache:
                    return yahoo_cache[symu]

                if isinstance(ownership_data, dict) and ownership_data.get(symu):
                    yahoo_cache[symu] = ownership_data[symu]
                    return yahoo_cache[symu]

                try:
                    from ingestion.financials_ownership_client import yahoo_snapshot
                except Exception:
                    yahoo_snapshot = None

                if not yahoo_snapshot:
                    return {}

                try:
                    snap = yahoo_snapshot(symu, use_cache=True)
                    if snap:
                        yahoo_cache[symu] = snap
                        return snap
                except Exception:
                    return {}

                return {}

            rows = (
                forecasts.get("rows")
                or forecasts.get("data", {}).get("rows", [])
                or []
            )
            articles = (
                news_feed.get("articles")
                or news_feed.get("data", {}).get("articles", [])
                or []
            )
            rows_sorted = sorted(
                rows, key=lambda r: r.get("confidence", 0), reverse=True
            )

            # Filter by profile tickers if profile is loaded
            if prof and getattr(prof, "tickers", None):
                prof_tickers = {t.upper() for t in (prof.tickers or [])}
                before = len(rows_sorted)
                rows_sorted = [
                    r
                    for r in rows_sorted
                    if (r.get("ticker") or r.get("symbol") or "").upper() in prof_tickers
                ]
                logger.info(
                    "Filtered to %d rows from profile %s (from %d)",
                    len(rows_sorted),
                    getattr(prof, "name", profile),
                    before,
                )
                add_trace(
                    "profile_filter_applied",
                    profile=profile,
                    before=before,
                    after=len(rows_sorted),
                )

            # Filter by explicit ticker query parameter
            if ticker:
                ticker_set = {t.upper() for t in ticker}
                before = len(rows_sorted)
                rows_sorted = [
                    r
                    for r in rows_sorted
                    if (r.get("ticker") or r.get("symbol") or "").upper() in ticker_set
                ]
                logger.info(
                    "Filtered to %d rows from ticker param %s (from %d)",
                    len(rows_sorted),
                    ticker_set,
                    before,
                )
                add_trace(
                    "ticker_filter_applied",
                    tickers=list(ticker_set),
                    before=before,
                    after=len(rows_sorted),
                )

            if not rows_sorted:
                logger.warning("⚠️ No rows left after profile/ticker filtering")
                now_iso = datetime.utcnow().isoformat() + "Z"
                empty_response = {
                    "verdicts": [],
                    "count": 0,
                    "stats": {
                        "total_verdicts": 0,
                        "high_confidence_count": 0,
                        "avg_confidence": 0.0,
                        "generated_at": now_iso,
                    },
                    "filters_applied": {
                        "min_confidence": min_confidence,
                        "tickers": ticker,
                        "sort_by": sort_by,
                        "sort_order": sort_order,
                        "limit": limit,
                    },
                    "generated_at": now_iso,
                    "source": ["judge_route", "forecasts_llm", "empty_after_filter"],
                }
                if debug:
                    empty_response["debug_pipeline"] = traces
                return empty_response

            # Respect limit but add a hard cap for safety
            max_tickers = min(max(limit, 1), 30)
            top_rows = rows_sorted[:max_tickers]
            logger.info(
                "📋 Selected %d top_rows for processing (limit=%d, hard_cap=%d, available=%d)",
                len(top_rows),
                limit,
                max_tickers,
                len(rows_sorted),
            )
            if top_rows:
                logger.info(
                    "   First ticker: %s",
                    top_rows[0].get("ticker") or top_rows[0].get("symbol") or "N/A",
                )
            add_trace(
                "rows_selected",
                total_rows=len(rows),
                after_filters=len(rows_sorted),
                selected=len(top_rows),
                limit=limit,
                hard_cap=max_tickers,
            )

            def _parse_ts(ts_val):
                if not ts_val:
                    return None
                try:
                    dt = datetime.fromisoformat(str(ts_val).replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except Exception:
                    try:
                        dt = datetime.strptime(str(ts_val), "%Y-%m-%d")
                        return dt.replace(tzinfo=timezone.utc)
                    except Exception:
                        return None

            def _score_news_items(
                news_list: List[Dict[str, Any]], cap: int = 5
            ) -> List[Dict[str, Any]]:
                """Rank news by recency then |sentiment|, keep top cap."""
                scored = []
                for n in news_list:
                    ts = (
                        n.get("timestamp")
                        or n.get("ts")
                        or n.get("published_at")
                        or n.get("date")
                    )
                    dt = _parse_ts(ts)
                    ts_num = None
                    try:
                        ts_num = dt.timestamp() if dt else None
                    except Exception:
                        ts_num = None
                    sent = (
                        n.get("sentiment_score")
                        or n.get("sent")
                        or n.get("sentiment")
                    )
                    try:
                        sent_abs = abs(float(sent)) if sent is not None else 0.0
                    except Exception:
                        sent_abs = 0.0
                    normalized = dict(n)
                    if ts:
                        normalized.setdefault("ts", ts)
                    scored.append((ts_num, sent_abs, normalized))
                scored.sort(key=lambda x: ((x[0] or 0.0), x[1]), reverse=True)
                return [x[2] for x in scored[:cap]]

            # Build global context to avoid “données insuffisantes”
            def _market_context():
                total = len(rows)
                bulls = len(
                    [
                        r
                        for r in rows
                        if str(r.get("direction", "")).lower() == "up"
                    ]
                )
                bears = len(
                    [
                        r
                        for r in rows
                        if str(r.get("direction", "")).lower() == "down"
                    ]
                )
                neutrals = total - bulls - bears
                brief = {}
                data = (
                    brief_daily.get("data")
                    if isinstance(brief_daily, dict)
                    else brief_daily
                )
                if isinstance(data, dict):
                    brief = {
                        "summary": data.get("summary") or data.get("title"),
                        "top_signals": data.get("top_signals"),
                        "top_risks": data.get("top_risks"),
                        "market_sentiment": data.get("market_sentiment"),
                    }
                return {
                    "forecasts_total": total,
                    "bullish": bulls,
                    "bearish": bears,
                    "neutral": neutrals,
                    "brief": brief,
                }

            mkt_ctx = _market_context()

            def _news_for(sym: str) -> List[Dict[str, Any]]:
                symu = sym.upper()
                rel = [
                    a
                    for a in articles
                    if symu in (a.get("tickers") or [])
                    or symu in (a.get("symbols") or [])
                ]
                if rel:
                    return _score_news_items(rel, cap=12)

                # Fallback: infer ticker mentions from title/summary for weakly-tagged feeds.
                alias_terms = TICKER_NEWS_ALIAS_TERMS.get(symu, [])
                rel_fallback: List[Dict[str, Any]] = []
                for a in articles:
                    text = f"{a.get('title', '')} {a.get('summary', '')}".upper()
                    if re.search(rf"\b{re.escape(symu)}\b", text):
                        rel_fallback.append(a)
                        continue
                    if any(term in text for term in alias_terms):
                        rel_fallback.append(a)
                rel = rel_fallback
                return _score_news_items(rel, cap=12)

            def _tech_for(sym: str) -> Dict[str, Any]:
                data = prices_data.get(sym) or {}
                pts = data.get("points") or data.get("prices") or []
                if not pts or len(pts) < 5:
                    return {}
                pts = sorted(pts, key=lambda x: x[0])
                closes = [float(p[1]) for p in pts if len(p) >= 2]
                if not closes:
                    return {}

                def sma(window):
                    if len(closes) < window:
                        return None
                    return sum(closes[-window:]) / window

                def vol(window):
                    if len(closes) < window:
                        return None
                    rets = []
                    for i in range(1, window):
                        prev_idx = -window + i - 1
                        curr_idx = -window + i
                        if closes[prev_idx] != 0:
                            rets.append(
                                (closes[curr_idx] - closes[prev_idx])
                                / closes[prev_idx]
                            )
                    if not rets:
                        return None
                    avg = sum(rets) / len(rets)
                    var = sum((r - avg) ** 2 for r in rets) / len(rets)
                    return var**0.5

                def rsi(period=14):
                    if len(closes) <= period:
                        return None
                    gains, losses = 0.0, 0.0
                    for i in range(len(closes) - period, len(closes) - 1):
                        diff = closes[i + 1] - closes[i]
                        if diff > 0:
                            gains += diff
                        else:
                            losses -= diff
                    if gains == 0 and losses == 0:
                        return 50.0
                    if losses == 0:
                        return 100.0
                    rs = gains / max(1e-9, losses)
                    return 100 - (100 / (1 + rs))

                last_close = closes[-1]
                sma20 = sma(20)
                sma50 = sma(50)
                vol20 = vol(20)
                return {
                    "rsi": round(rsi(14), 2) if rsi(14) is not None else None,
                    "sma20_vs_price": round(
                        (sma20 - last_close) / last_close, 4
                    )
                    if sma20
                    else None,
                    "sma50_vs_price": round(
                        (sma50 - last_close) / last_close, 4
                    )
                    if sma50
                    else None,
                    "vol20": round(vol20, 4) if vol20 is not None else None,
                    "volume": data.get("volume"),
                    "last_price": last_close,
                }

            def _macro_snapshot():
                out: Dict[str, Any] = {}

                def _parse_macro_date(val: Any) -> Optional[datetime]:
                    if not val:
                        return None
                    s = str(val)
                    if s.endswith("Z"):
                        s = s[:-1]
                    try:
                        if "T" in s:
                            dt = datetime.fromisoformat(s)
                        else:
                            dt = datetime.fromisoformat(f"{s}T00:00:00")
                    except Exception:
                        return None
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt

                def last_and_delta(key, win: int = 21):
                    series = macro_series.get(key, {}).get("observations") or []
                    if not series:
                        return None, None, None
                    vals: List[float] = []
                    dates: List[Optional[str]] = []
                    for s in series:
                        v = s.get("value")
                        if v is None:
                            continue
                        try:
                            vals.append(float(v))
                            d = s.get("date")
                            dates.append(str(d) if d else None)
                        except (TypeError, ValueError):
                            continue
                    if not vals:
                        return None, None, None
                    last = vals[-1]
                    last_date = dates[-1] if dates else None
                    delta = None
                    if len(vals) > win:
                        prev = vals[-1 - win]
                        if prev not in (None, 0):
                            delta = (last - prev) / prev
                    return last, delta, last_date

                macro_dates: List[str] = []

                out["vix"], out["vix_delta_1m"], vix_date = last_and_delta("VIXCLS", 21)
                out["us10y"], out["us10y_delta_1m"], us10y_date = last_and_delta(
                    "DGS10", 21
                )
                if vix_date:
                    macro_dates.append(vix_date)
                if us10y_date:
                    macro_dates.append(us10y_date)

                cpi_last, cpi_delta, cpi_last_date = last_and_delta("CPIAUCSL", 1)
                out["cpi_last"] = cpi_last
                out["cpi_delta_1m"] = cpi_delta
                out["cpi_last_date"] = cpi_last_date
                if cpi_last_date:
                    macro_dates.append(cpi_last_date)

                # DXY (broad trade-weighted USD) si dispo
                for key in ("DTWEXBGS", "DTWEXAFEGS", "DXY"):
                    val, delta, dxy_date = last_and_delta(key, 21)
                    if val is not None:
                        out["dxy"] = val
                        out["dxy_delta_1m"] = delta
                        out["dxy_series"] = key
                        out["dxy_last_date"] = dxy_date
                        if dxy_date:
                            macro_dates.append(dxy_date)
                        break

                # Commodities (WTI/Brent/Gold) si présents
                wti, wti_delta, wti_date = last_and_delta("DCOILWTICO", 21)
                brent, brent_delta, brent_date = last_and_delta("DCOILBRENTEU", 21)
                gold, gold_delta, gold_date = last_and_delta("GOLDAMGBD228NLBM", 21)
                if wti is not None:
                    out["wti"] = wti
                    out["wti_delta_1m"] = wti_delta
                    out["wti_last_date"] = wti_date
                    if wti_date:
                        macro_dates.append(wti_date)
                if brent is not None:
                    out["brent"] = brent
                    out["brent_delta_1m"] = brent_delta
                    out["brent_last_date"] = brent_date
                    if brent_date:
                        macro_dates.append(brent_date)
                if gold is not None:
                    out["gold"] = gold
                    out["gold_delta_1m"] = gold_delta
                    out["gold_last_date"] = gold_date
                    if gold_date:
                        macro_dates.append(gold_date)

                if macro_dates:
                    latest_dt = max(
                        (d for d in (_parse_macro_date(v) for v in macro_dates) if d is not None),
                        default=None,
                    )
                    out["latest_date"] = latest_dt.date().isoformat() if latest_dt else None
                else:
                    out["latest_date"] = None
                return out

            def _ownership_for(sym: str) -> Dict[str, Any]:
                snap = (
                    ownership_data.get(sym.upper())
                    if isinstance(ownership_data, dict)
                    else None
                )
                if not snap:
                    snap = _yahoo_snapshot(sym)
                if snap and isinstance(snap, dict):
                    return {
                        "sector": snap.get("sector") or snap.get("industry"),
                        "industry": snap.get("industry"),
                        "marketCap": snap.get("marketCap")
                        or snap.get("mktCap"),
                        "pe": snap.get("trailingPE") or snap.get("pe"),
                        "beta": snap.get("beta"),
                        "avgVolume": snap.get("averageVolume")
                        or snap.get("avgVolume"),
                    }
                return {}

            def _judge_feature_for(sym: str) -> Dict[str, Any]:
                return (
                    judge_features.get(sym.upper())
                    if isinstance(judge_features, dict)
                    else {}
                )

            macro_ctx = _macro_snapshot()

            def _brief_text():
                b = mkt_ctx.get("brief") or {}
                parts: List[str] = []
                if b.get("summary"):
                    parts.append(str(b.get("summary")))
                if b.get("top_signals"):
                    sigs = [
                        s.get("ticker") or s.get("name")
                        for s in b["top_signals"]
                        if isinstance(s, dict)
                    ]
                    parts.append(
                        f"top_signals: {', '.join([s for s in sigs if s])}"
                    )
                if b.get("top_risks"):
                    risks = [
                        r.get("name") or r.get("ticker")
                        for r in b["top_risks"]
                        if isinstance(r, dict)
                    ]
                    parts.append(
                        f"top_risks: {', '.join([r for r in risks if r])}"
                    )
                if b.get("market_sentiment"):
                    parts.append(f"sentiment: {b.get('market_sentiment')}")
                return " | ".join(parts)

            def _parse_analysis(answer: str) -> Dict[str, Any]:
                """Parse LLM answer: use external parser if dispo, sinon JSON le plus probable."""
                def _extract_json_block(text: str) -> Optional[str]:
                    """Retourne le plus grand bloc {...} équilibré trouvé dans le texte."""
                    best = None
                    depth = 0
                    start_idx = None
                    for i, ch in enumerate(text):
                        if ch == "{":
                            if depth == 0:
                                start_idx = i
                            depth += 1
                        elif ch == "}":
                            depth = max(0, depth - 1)
                            if depth == 0 and start_idx is not None:
                                cand = text[start_idx : i + 1]
                                if not best or len(cand) > len(best):
                                    best = cand
                                start_idx = None
                    return best

                if not answer:
                    return {}
                # 1) parser dédié si dispo
                if parse_llm_answer:
                    try:
                        parsed = parse_llm_answer(answer)
                        if isinstance(parsed, dict):
                            return parsed
                    except Exception:
                        pass
                # 2) fallback: dernière ligne JSON
                lines = [l.strip() for l in answer.strip().splitlines() if l.strip()]
                if lines:
                    last_line = lines[-1]
                    try:
                        data = json.loads(last_line)
                        if isinstance(data, dict):
                            return data
                    except Exception:
                        pass
                # 3) bloc JSON le plus probable dans tout le texte
                block = _extract_json_block(answer)
                if block:
                    try:
                        data = json.loads(block)
                        if isinstance(data, dict):
                            return data
                    except Exception:
                        pass
                return {}

            # Force dev mode and a stable free OpenRouter stack for judge (fast + fiable en dev)
            os.environ["ECON_AGENT_MODE"] = "dev"
            os.environ["ECON_AGENT_MODELS"] = ",".join([
                "tngtech/deepseek-r1t2-chimera:free",
                "openai/gpt-oss-120b:free",
                "qwen/qwen3-235b-a22b:free",
                "google/gemini-2.0-flash-exp:free",
            ])
            os.environ.pop("ECON_AGENT_DYNAMIC_MODELS", None)
            candidate_models: Optional[List[str]] = None

            agent = EconomicAnalyst(
                model_candidates=candidate_models,
                timeout=120,  # 120s par appel LLM
                retries_per_model=1,
                char_budget=800,
                max_tokens=prof.max_tokens if prof else 1200,  # Use profile max_tokens
            )

            sem = asyncio.Semaphore(3)  # allow limited parallelism

            async def _process_row(r):
                async with sem:
                    sym = (r.get("ticker") or r.get("symbol") or "").upper()
                    if not sym:
                        return None
                    if debug:
                        add_trace("row_start", ticker=sym)

                    t_total = time.perf_counter()
                    met = {
                        "news_ms": None,
                        "payload_ms": None,
                        "ml_prior_ms": None,
                        "llm_ms": None,
                        "parse_ms": None,
                        "total_ms": None,
                        "llm_model": None,
                        "llm_provider": None,
                    }

                    base_conf = float(r.get("confidence", 0.5) or 0.0)
                    expected_return = r.get("expected_return")
                    direction = r.get("direction", "neutral")
                    horizon = r.get("horizon") or "1w"
                    expected_return_ensemble = expected_return
                    expected_return_final = expected_return_ensemble

                    # verdict_text doit exister même si on échoue avant l'appel LLM
                    verdict_text = (
                        f"{sym}: {direction} (conf {base_conf:.2f})"
                    )

                    # ML prior
                    ml_prior = None
                    t_ml = time.perf_counter()
                    if ml_predict_next_return:
                        try:
                            pred, conf_ml = ml_predict_next_return(
                                sym,
                                horizon=(
                                    horizon
                                    if horizon in ("1w", "1m", "1y")
                                    else "1m"
                                ),
                            )
                            ml_prior = {
                                "pred_return": pred,
                                "confidence": conf_ml,
                                "horizon": horizon,
                                "source": "ml_baseline",
                            }
                        except Exception:
                            ml_prior = {"error": "ml_baseline_failed"}
                    if ml_prior is None:
                        ml_prior = {"error": "ml_baseline_unavailable"}
                    met["ml_prior_ms"] = (
                        time.perf_counter() - t_ml
                    ) * 1000.0
                    if debug:
                        add_trace(
                            "ml_prior",
                            ticker=sym,
                            pred=ml_prior.get("pred_return"),
                            conf=ml_prior.get("confidence"),
                            error=ml_prior.get("error"),
                        )

                    # Ensemble expected_return avec ml_prior si disponible
                    try:
                        er_raw = float(expected_return) if expected_return is not None else None
                        er_ml = (
                            float(ml_prior.get("pred_return"))
                            if isinstance(ml_prior, dict)
                            and ml_prior.get("pred_return") is not None
                            else None
                        )
                        w_ml = (
                            float(ml_prior.get("confidence"))
                            if isinstance(ml_prior, dict)
                            and ml_prior.get("confidence") is not None
                            else None
                        )
                        if w_ml is None:
                            w_ml = 0.5
                        w_ml = max(0.0, min(1.0, w_ml))
                        if er_raw is not None and er_ml is not None:
                            expected_return_ensemble = w_ml * er_ml + (1 - w_ml) * er_raw
                        elif er_ml is not None:
                            expected_return_ensemble = er_ml
                        else:
                            expected_return_ensemble = er_raw
                    except Exception:
                        expected_return_ensemble = expected_return
                    expected_return_final = expected_return_ensemble
                    if debug:
                        add_trace(
                            "ensemble",
                            ticker=sym,
                            expected_return_raw=expected_return,
                            ml_prior_pred=ml_prior.get("pred_return") if isinstance(ml_prior, dict) else None,
                            weight_ml=w_ml if "w_ml" in locals() else None,
                            expected_return_ensemble=expected_return_ensemble,
                        )

                    enriched = _judge_feature_for(sym) or {}
                    ownership = _ownership_for(sym)

                    feat = {
                        "ticker": sym,
                        "direction": direction,
                        "expected_return": expected_return,
                        "expected_return_ensemble": expected_return_ensemble,
                        "confidence": base_conf,
                        "horizon": horizon,
                        "model": r.get("model"),
                        "macro_brief": mkt_ctx.get("brief"),
                        "forecasts_bullish": mkt_ctx.get("bullish"),
                        "forecasts_bearish": mkt_ctx.get("bearish"),
                        "forecasts_neutral": mkt_ctx.get("neutral"),
                        "brief_text": _brief_text(),
                        "news_count": len(_news_for(sym)),
                        "tech": {},
                        "macro": macro_ctx,
                        "sector": r.get("sector")
                        or ownership.get("sector")
                        or enriched.get("fundamentals", {}).get("sector"),
                        "industry": ownership.get("industry")
                        or enriched.get("fundamentals", {}).get("industry"),
                        "beta": ownership.get("beta")
                        or enriched.get("fundamentals", {}).get("beta"),
                        "marketCap": ownership.get("marketCap")
                        or enriched.get("fundamentals", {}).get("marketCap"),
                        "pe": ownership.get("pe")
                        or enriched.get("fundamentals", {}).get("pe"),
                        "avgVolume": ownership.get("avgVolume")
                        or enriched.get("fundamentals", {}).get("avgVolume"),
                        "fundamentals": enriched.get("fundamentals", {}),
                        "peer_signals": r.get("peer_signals"),
                        "ml_prior": ml_prior,
                        "ml_prior_pred": ml_prior.get("pred_return")
                        if isinstance(ml_prior, dict)
                        else None,
                        "ml_prior_conf": ml_prior.get("confidence")
                        if isinstance(ml_prior, dict)
                        else None,
                    }

                    # Enrich tech/fund live (with errors as data_needed hints)
                    try:
                        from services.judge_pipeline import (
                            get_tech_enriched,
                            get_fundamental_minimal,
                        )

                        tech_enriched = get_tech_enriched(
                            sym,
                            judge_features
                            if isinstance(judge_features, dict)
                            else {},
                        )
                        if tech_enriched.get("error"):
                            feat.setdefault("data_needed", []).append(
                                tech_enriched["error"]
                            )
                        else:
                            feat["tech"] = tech_enriched
                        fund_enriched = get_fundamental_minimal(sym)
                        if fund_enriched.get("error"):
                            feat.setdefault("data_needed", []).append(
                                fund_enriched["error"]
                            )
                        else:
                            feat["fundamentals_enriched"] = fund_enriched
                    except Exception as e:
                        feat.setdefault("data_needed", []).append(
                            f"enrichment_failed: {e}"
                        )

                    # News selection
                    t_news = time.perf_counter()
                    news_items = _news_for(sym)[:5]  # limiter le volume
                    met["news_ms"] = (
                        time.perf_counter() - t_news
                    ) * 1000.0
                    news_headlines = [
                        {
                            "title": n.get("title") or n.get("headline"),
                            "sent": n.get("sentiment_score")
                            or n.get("sent")
                            or n.get("sentiment"),
                            "ts": _normalize_ts_str(
                                n.get("timestamp")
                                or n.get("ts")
                                or n.get("published_at")
                                or n.get("date")
                            ),
                            "source": n.get("source"),
                            "summary": (
                                n.get("summary")
                                or n.get("description")
                                or (n.get("raw_text") or "")
                            )[:180],
                            "tickers": n.get("tickers")
                            or n.get("symbols")
                            or [],
                        }
                        for n in news_items
                        if n.get("title") or n.get("headline")
                    ]

                    # Price features (multi-horizon) from cached price points
                    price_features = {}
                    price_points = []
                    try:
                        price_points = (
                            prices_data.get(sym, {}).get("points")
                            or prices_data.get(sym, {}).get("prices")
                            or []
                        )
                        price_stats = _compute_price_features(price_points)
                        if price_stats:
                            price_features["price_stats"] = price_stats
                            price_features["price_profile"] = _price_profile_from_stats(price_stats)
                            # Quick-win extras for snapshot-style consumption
                            if price_stats.get("trend_state_3m"):
                                price_features["price_regime"] = price_stats["trend_state_3m"]
                            vol_block = {}
                            if "vol_1m" in price_stats:
                                vol_block["1m"] = price_stats["vol_1m"]
                            if "vol_3m" in price_stats:
                                vol_block["3m"] = price_stats["vol_3m"]
                            if "vol_1y" in price_stats:
                                vol_block["1y"] = price_stats["vol_1y"]
                            if vol_block:
                                price_features["volatility"] = {"realized_vol": vol_block}
                    except Exception:
                        price_features = {}

                    # Sentiment multi-fenêtre + profil
                    sent_windows = _sentiment_windows(news_items)
                    sent_profile = _sentiment_profile(sent_windows) if sent_windows else {}

                    # Fundamentals / macro profiles (heuristiques rapides)
                    fund_profile = _fundamentals_profile(
                        feat.get("fundamentals_enriched", {})
                        or feat.get("fundamentals", {})
                    )
                    macro_prof = _macro_profile(macro_ctx)

                    # Build question using profile template or fallback
                    base_prompt = (
                        "NE RÉPONDS QUE PAR UNE SEULE LIGNE JSON STRICT qui commence par { et se termine par }.\n"
                        "AUCUN TEXTE AVANT ou APRÈS.\n"
                        "Clés attendues : summary, scenarios, risks, impacts, actions, confidence, data_needed, phase_scores, ml_prior.\n"
                        "Exemple de structure : "
                        "{\"summary\": [\"...\", \"...\"], "
                        "\"scenarios\": [{\"name\": \"base\", \"p\": 60}], "
                        "\"risks\": [\"...\"], "
                        "\"impacts\": {\"FX\": [\"...\"], \"rates\": [\"...\"], \"commodities\": [\"...\"], \"equity\": [\"...\"]}, "
                        "\"actions\": [\"...\"], "
                        "\"confidence\": 0.0-1.0, "
                        "\"data_needed\": [\"...\"], "
                        "\"phase_scores\": {\"fundamental\": num, \"technical\": num, \"macro\": num, \"sentiment\": num, \"fusion\": num}, "
                        "\"ml_prior\": {\"pred_return\": num, \"confidence\": num, \"horizon\": \"...\"}}\n"
                        "Utilise les blocs phases (fundamental/technical/macro/sentiment/fusion) et leurs scores, ainsi que price_stats/price_profile, sentiment_windows/sentiment_profile, fundamentals_profile, macro_profile. "
                        "Si une donnée manque, liste-la dans data_needed. "
                        "SI TU NE PEUX PAS DONNER LE JSON, RÉPONDS PAR {\"error\":\"no_json\"}."
                    )
                    if prof and getattr(prof, "prompt_template", None):
                        question = prof.prompt_template.format(ticker=sym) + " " + base_prompt
                    else:
                        question = (
                            f"Verdict structuré pour {sym} (horizon {horizon}). " + base_prompt
                        )

                    phase_blocks: Dict[str, Any] = {}
                    t_phase = time.perf_counter()
                    if build_phase_blocks:
                        phase_features = dict(enriched)
                        phase_features.setdefault(
                            "fundamentals", enriched.get("fundamentals", {})
                        )
                        phase_features.setdefault(
                            "tech", enriched.get("tech") or _tech_for(sym)
                        )
                        phase_blocks = (
                            build_phase_blocks(
                                sym,
                                phase_features,
                                macro_ctx,
                                news_items,
                            )
                            or {}
                        )
                    if debug:
                        duration_ms = (time.perf_counter() - t_phase) * 1000.0
                        add_trace(
                            "phases_built",
                            ticker=sym,
                            duration_ms=duration_ms,
                            phases=list((phase_blocks or {}).keys()),
                        )
                        for pname, pobj in (phase_blocks or {}).items():
                            add_trace(
                                "phase_done",
                                ticker=sym,
                                phase=pname,
                                score=pobj.get("score") if isinstance(pobj, dict) else None,
                            )
                        add_trace(
                            "phases_state",
                            ticker=sym,
                            scores={
                                k: (v.get("score") if isinstance(v, dict) else None)
                                for k, v in (phase_blocks or {}).items()
                            },
                        )
                        add_trace(
                            "phase_inputs",
                            ticker=sym,
                            tech_keys=list((feat.get("tech") or {}).keys()) if isinstance(feat, dict) else None,
                            fund_keys=list((feat.get("fundamentals") or {}).keys()) if isinstance(feat, dict) else None,
                            macro_keys=list((macro_ctx or {}).keys()),
                            news_count=len(news_items),
                        )
                        add_trace(
                            "phase_outputs",
                            ticker=sym,
                            phases_summary={
                                k: {
                                    "score": (v.get("score") if isinstance(v, dict) else None),
                                    "summary_len": len(v.get("summary") or []) if isinstance(v, dict) else None,
                                }
                                for k, v in (phase_blocks or {}).items()
                            },
                        )
                    # Enrichir les phases avec sentiment simple et momentum si absent
                    try:
                        # Sentiment: moyenne simple des scores/labels si score absent
                        sent_block = phase_blocks.get("sentiment") if isinstance(phase_blocks, dict) else None
                        if sent_block is not None and news_items:
                            vals = []
                            pos = neg = neu = 0
                            for n in news_items:
                                sc = n.get("score") or n.get("sentiment_score") or n.get("sent")
                                label = (n.get("sentiment") or "").lower()
                                if sc is None:
                                    if label == "positive":
                                        sc = 1.0
                                    elif label == "negative":
                                        sc = -1.0
                                    elif label == "neutral":
                                        sc = 0.0
                                try:
                                    if sc is not None:
                                        fsc = float(sc)
                                        vals.append(fsc)
                                        if fsc > 0:
                                            pos += 1
                                        elif fsc < 0:
                                            neg += 1
                                        else:
                                            neu += 1
                                except Exception:
                                    pass
                            det = sent_block.setdefault("details", {})
                            det["news_count"] = len(news_items)
                            det["positive"] = pos
                            det["negative"] = neg
                            det["neutral"] = neu
                            if sent_windows:
                                det["windows"] = sent_windows
                            if sent_profile:
                                det["profile"] = sent_profile
                            if news_headlines:
                                det["top_news_highlights"] = [
                                    (n.get("title") or "")[:140]
                                    for n in news_headlines[:5]
                                    if n.get("title")
                                ]
                            if vals:
                                avg = float(sum(vals) / len(vals))
                                det["avg_score"] = avg
                                # Normaliser score 0-1
                                if sent_block.get("score") is None:
                                    sent_block["score"] = avg
                                if sent_block.get("score") and sent_block["score"] > 1:
                                    sent_block["score"] = sent_block["score"] / 100.0
                                if sent_block.get("score") is not None:
                                    try:
                                        sent_block["score"] = max(0.0, min(1.0, float(sent_block["score"])))
                                    except Exception:
                                        pass
                                # Ajouter un mini résumé lisible si absent
                                if not sent_block.get("summary"):
                                    sent_block["summary"] = [
                                        f"{pos}/{len(news_items)} positives, {neg} negatives, {neu} neutres (avg={avg:.2f})"
                                    ]
                        # Momentum/drawdown depuis tech_enriched si manquants
                        tech_block = phase_blocks.get("technical") if isinstance(phase_blocks, dict) else None
                        if tech_block is not None:
                            details = tech_block.setdefault("details", {})
                            tech_src = feat.get("tech") if isinstance(feat, dict) else {}
                            for key in ("momentum_1m", "momentum_3m", "drawdown_3m"):
                                if details.get(key) is None and tech_src.get(key) is not None:
                                    try:
                                        details[key] = float(tech_src[key])
                                    except Exception:
                                        pass
                            if price_features.get("price_stats"):
                                details.setdefault("price_stats", price_features["price_stats"])
                            if price_features.get("price_profile"):
                                tech_block.setdefault("summary", [])
                                tech_block["summary"].append(
                                    " | ".join(price_features["price_profile"].values())
                                )
                        fund_block = phase_blocks.get("fundamental") if isinstance(phase_blocks, dict) else None
                        if fund_block is not None and fund_profile:
                            fund_block.setdefault("details", {}).setdefault("profile", fund_profile)
                        macro_block_phase = phase_blocks.get("macro") if isinstance(phase_blocks, dict) else None
                        if macro_block_phase is not None and macro_prof:
                            macro_block_phase.setdefault("details", {}).setdefault("profile", macro_prof)
                    except Exception:
                        pass

                    # Inject extra feature blocks for LLM context
                    try:
                        if price_features:
                            feat.update(price_features)
                            # Keep a flat alias for price_regime if present
                            if "price_regime" in price_features:
                                feat["price_regime"] = price_features["price_regime"]
                            if "volatility" in price_features:
                                feat["volatility"] = price_features["volatility"]
                        if sent_windows:
                            feat["sentiment_windows"] = sent_windows
                        if sent_profile:
                            feat["sentiment_profile"] = sent_profile
                        # Sentiment score unifié 0-1 pour LLM (utile pour phase_scores)
                        try:
                            avg_sent = None
                            if isinstance(sent_windows, dict):
                                avg_sent = sent_windows.get("7d", {}).get("avg") or sent_windows.get("24h", {}).get("avg")
                            if avg_sent is not None:
                                sent_norm = float(avg_sent)
                                if sent_norm > 1:
                                    sent_norm = sent_norm / 100.0
                                sent_norm = max(0.0, min(1.0, sent_norm))
                                feat["sentiment_score_norm"] = sent_norm
                        except Exception:
                            pass
                        if fund_profile:
                            feat["fundamentals_profile"] = fund_profile
                        if macro_prof:
                            feat["macro_profile"] = macro_prof
                    except Exception:
                        pass

                    payload = {
                        "question": question,
                        "features": {
                            **feat,
                            "macro": macro_ctx,
                            "news_count": len(news_items),
                            "phases": phase_blocks or {},
                            "ml_prior": ml_prior,
                        },
                        "phases": phase_blocks or None,
                        "news": news_items,
                        "attachments": news_headlines or None,
                        "locale": "fr-FR",
                        "meta": {
                            "source": "judge_route",
                            "ticker": sym,
                            "ml_prior": ml_prior,
                            "data_timestamps": {
                                "macro": macro_ctx.get("cpi_last_date"),
                            },
                        },
                    }

                    # Debug: log payload summary (no heavy data) + compact JSON
                    try:
                        logger.info(
                            "judge_llm_request "
                            f"ticker={sym} "
                            f"models={os.environ.get('ECON_AGENT_MODELS')} "
                            f"question_preview={(question or '')[:160]!r} "
                            f"news_count={len(news_items)} "
                            f"attachments={len(news_headlines or [])} "
                            f"phases={list((phase_blocks or {}).keys())} "
                            f"macro_keys={list(macro_ctx.keys())} "
                            f"feature_keys={list(payload.get('features', {}).keys())} "
                            f"ml_prior_pred={ml_prior.get('pred_return') if isinstance(ml_prior, dict) else None} "
                            f"ml_prior_conf={ml_prior.get('confidence') if isinstance(ml_prior, dict) else None}"
                        )
                        logger.warning(
                            "judge_llm_request_payload=%s",
                            json.dumps(
                                {
                                    "ticker": sym,
                                    "question": question,
                                    "features": payload.get("features"),
                                    "phases": phase_blocks,
                                    "news": news_items,
                                    "attachments": news_headlines,
                                    "meta": payload.get("meta"),
                                },
                                default=str,
                            ),
                        )
                    except Exception:
                        pass
                    if debug:
                        add_trace(
                            "payload_ready",
                            ticker=sym,
                            phases=list((phase_blocks or {}).keys()),
                            news=len(news_items),
                        )

                    # Validate payload (Pydantic) before LLM
                    if build_payload:
                        try:
                            t_payload = time.perf_counter()
                            _ = build_payload(
                                ticker=sym,
                                features=payload["features"],
                                macro=macro_ctx,
                                news=news_items,
                                attachments=news_headlines,
                                phases=phase_blocks or {},
                                ml_prior=ml_prior,
                                locale="fr-FR",
                            )
                            met["payload_ms"] = (
                                time.perf_counter() - t_payload
                            ) * 1000.0
                        except Exception as e:
                            # On renvoie quand même un verdict minimal
                            return {
                                "ticker": sym,
                                "verdict": verdict_text,
                                "confidence": base_conf,
                                "expected_return": expected_return,
                                "risk_level": "medium",
                                "reasoning": [
                                    f"payload_validation_error: {e}"
                                ],
                                "analysis": {
                                    "error": "payload_validation_error",
                                    "details": str(e),
                                },
                                "phases": phase_blocks or None,
                                "phase_scores": {
                                    k: (
                                        v.get("score")
                                        if isinstance(v, dict)
                                        else None
                                    )
                                    for k, v in (phase_blocks or {}).items()
                                }
                                or None,
                                "ml_prior": ml_prior,
                                "raw_answer": "",
                                "generated_at": datetime.utcnow().isoformat()
                                + "Z",
                                "model_version": "econ_llm_agent",
                                "source": ["judge_route", "forecasts_llm"],
                            }

                    # Call LLM in a worker thread to avoid nested event-loop issues
                    def _run_agent():
                        ein = EconomicInput(**payload)
                        return agent.analyze(ein)

                    res = {"ok": False, "error": "not_called", "answer": ""}
                    t_llm = time.perf_counter()
                    for attempt_idx in range(2):
                        try:
                            res = await asyncio.wait_for(
                                asyncio.to_thread(_run_agent), timeout=300
                            )
                            break
                        except asyncio.TimeoutError:
                            res = {"ok": False, "error": "timeout", "answer": ""}
                            break
                        except Exception as e:
                            err_msg = f"{type(e).__name__}: {e}"
                            # Retry once if rate limited
                            if "Too Many Requests" in err_msg:
                                alt_key = os.environ.get("OPEN_ROUTER_API_KEY_2")
                                if alt_key and os.environ.get("OPEN_ROUTER_API_KEY") != alt_key:
                                    os.environ["OPEN_ROUTER_API_KEY"] = alt_key
                                    await asyncio.sleep(1.0)
                                    continue
                                if attempt_idx == 0:
                                    await asyncio.sleep(2.0)
                                    continue
                            res = {"ok": False, "error": err_msg, "answer": ""}
                            break
                    met["llm_ms"] = (time.perf_counter() - t_llm) * 1000.0

                    # G4F fallback si OpenRouter échoue
                    if (
                        not res.get("ok")
                        and call_g4f
                        and os.environ.get("G4F_PROVIDER")
                    ):
                        try:
                            messages = [
                                {"role": "system", "content": "Réponds uniquement par un JSON strict sur une seule ligne."},
                                {"role": "user", "content": question},
                                {
                                    "role": "user",
                                    "content": "Contexte (features JSON) : " + json.dumps(payload.get("features", {}), default=str)[:3500],
                                },
                            ]
                            res_g4f = call_g4f(
                                messages=messages,
                                model=os.environ.get("G4F_MODEL"),
                                provider=os.environ.get("G4F_PROVIDER"),
                                timeout=60,
                            )
                            if res_g4f.get("ok"):
                                res = res_g4f
                                try:
                                    logger.warning("g4f_raw_response=%s", json.dumps(res_g4f, default=str)[:2000])
                                except Exception:
                                    pass
                            else:
                                try:
                                    logger.warning("g4f_error=%s", res_g4f.get("error"))
                                except Exception:
                                    pass
                        except Exception as e:
                            res = {"ok": False, "error": f"g4f_failed: {e}", "answer": ""}

                    # Codestral fallback ensuite
                    if (
                        not res.get("ok")
                        and call_codestral
                        and os.environ.get("CODESTRAL_API_KEY")
                    ):
                        try:
                            messages = [
                                {"role": "system", "content": "Réponds uniquement par un JSON strict sur une seule ligne."},
                                {"role": "user", "content": question},
                                {
                                    "role": "user",
                                    "content": "Contexte (features JSON) : " + json.dumps(payload.get("features", {}), default=str)[:3500],
                                },
                            ]
                            res_cd = call_codestral(
                                messages=messages,
                                model="codestral-2508",
                                max_tokens=1200,
                                temperature=0.2,
                            )
                            if res_cd.get("ok"):
                                res = res_cd
                                try:
                                    logger.warning("codestral_raw_response=%s", json.dumps(res_cd, default=str)[:2000])
                                except Exception:
                                    pass
                            else:
                                try:
                                    logger.warning("codestral_error=%s", res_cd.get("error"))
                                except Exception:
                                    pass
                        except Exception as e:
                            res = {"ok": False, "error": f"codestral_failed: {e}", "answer": ""}

                    # Groq fallback si toujours KO
                    if (
                        not res.get("ok")
                        and call_groq
                        and os.environ.get("GROQ_API_KEY")
                    ):
                        try:
                            messages = [
                                {"role": "system", "content": "Réponds uniquement par un JSON strict sur une seule ligne."},
                                {"role": "user", "content": question},
                                {
                                    "role": "user",
                                    "content": "Contexte (features JSON) : " + json.dumps(payload.get("features", {}), default=str)[:3500],
                                },
                            ]
                            res_groq = call_groq(
                                messages=messages,
                                model="qwen/qwen3-32b",
                                max_tokens=1200,
                                temperature=0.2,
                            )
                            if res_groq.get("ok"):
                                res = res_groq
                                try:
                                    logger.warning("groq_raw_response=%s", json.dumps(res_groq, default=str)[:2000])
                                except Exception:
                                    pass
                            else:
                                try:
                                    logger.warning("groq_error=%s", res_groq.get("error"))
                                except Exception:
                                    pass
                        except Exception as e:
                            res = {"ok": False, "error": f"groq_failed: {e}", "answer": ""}

                    try:
                        logger.info(
                            "judge_llm_raw_response "
                            f"ticker={sym} "
                            f"model={res.get('model') if isinstance(res, dict) else None} "
                            f"provider={res.get('provider') if isinstance(res, dict) else None} "
                            f"raw_preview={(res.get('answer') or '') if isinstance(res, dict) else ''!r}"
                        )
                        logger.warning(
                            "judge_llm_raw_response_payload=%s",
                            json.dumps(res, default=str)
                            if isinstance(res, dict)
                            else str(res),
                        )
                    except Exception:
                        pass

                    parsed: Optional[Dict[str, Any]] = None
                    model_used = None
                    full_answer = None
                    fallback_used = None

                    if isinstance(res, dict) and res.get("ok"):
                        full_answer = res.get("answer")
                        verdict_text = full_answer or verdict_text
                        parsed = res.get("parsed")
                        model_used = res.get("model")
                        if (
                            parsed
                            and isinstance(parsed, dict)
                            and parsed.get("confidence") is not None
                        ):
                            base_conf = float(parsed.get("confidence"))
                    else:
                        full_answer = (
                            res.get("answer")
                            if isinstance(res, dict)
                            else None
                        ) or (
                            res.get("error")
                            if isinstance(res, dict)
                            else None
                        ) or verdict_text

                    # Parsing / validation
                    t_parse = time.perf_counter()
                    parsed = (
                        parsed
                        if isinstance(parsed, dict)
                        else _parse_analysis(full_answer or verdict_text)
                    )
                    if not (isinstance(res, dict) and res.get("ok")):
                        # LLM a échoué: garder l'erreur explicite
                        parsed = {
                            "error": res.get("error")
                            if isinstance(res, dict)
                            else "llm_failed",
                            "raw": full_answer or verdict_text,
                        }
                    # Double passe: auditeur JSON pour réparer/valider la structure
                    if (
                        call_groq
                        and isinstance(parsed, dict)
                        and not parsed.get("error")
                        and isinstance(res, dict)
                        and res.get("ok")
                        and full_answer
                    ):
                        audit_prompt = (
                            "Tu es un AUDITEUR JSON. "
                            "On te donne un texte qui doit être un JSON respectant ce schéma strict : "
                            '{"summary":[],"scenarios":[],"risks":[],"impacts":{"FX":[],"rates":[],"commodities":[],"equity":[]},"actions":[],"confidence":0.0,"data_needed":[],"phase_scores":{},"ml_prior":{}}. '
                            "Ne renvoie QUE le JSON réparé. Si tu ne peux pas, renvoie {\"error\":\"invalid_schema\"}."
                        )
                        messages_audit = [
                            {"role": "system", "content": audit_prompt},
                            {"role": "user", "content": full_answer},
                        ]
                        try:
                            res_audit = call_groq(
                                messages=messages_audit,
                                model="qwen/qwen3-32b",
                                max_tokens=400,
                                temperature=0.0,
                            )
                            if res_audit.get("ok") and res_audit.get("answer"):
                                try:
                                    audited = json.loads(res_audit.get("answer", ""))
                                    if isinstance(audited, dict):
                                        parsed = audited
                                except Exception:
                                    pass
                        except Exception:
                            pass
                    if isinstance(parsed, dict):
                        # Normalisation pour Pydantic: phase_scores doit être un dict
                        ps = parsed.get("phase_scores")
                        if isinstance(ps, list):
                            parsed["phase_scores"] = {}
                        elif ps is None:
                            parsed["phase_scores"] = {}
                        # On force ml_prior issu du pipeline (ignore ce que le LLM renvoie éventuellement)
                        if ml_prior:
                            parsed["ml_prior"] = ml_prior
                        if parsed.get("confidence") is None:
                            parsed["confidence"] = base_conf
                        if parsed.get("error") is None:
                            if phase_blocks:
                                parsed.setdefault(
                                    "phase_scores",
                                    {
                                        k: (
                                            v.get("score")
                                            if isinstance(v, dict)
                                            else None
                                        )
                                        for k, v in phase_blocks.items()
                                    },
                                )
                            if ml_prior:
                                parsed["ml_prior"] = ml_prior
                            try:
                                if validate_llm_response:
                                    parsed = validate_llm_response(parsed)
                                    # Revenir à un dict pour éviter les parsed_ok=False
                                    if hasattr(parsed, "model_dump"):
                                        parsed = parsed.model_dump()
                            except Exception as e:
                                parsed = {
                                    "error": f"llm_validation_error: {e}",
                                    "raw": full_answer or verdict_text,
                                }

                        # Harmoniser la confiance finale avec ce que le LLM fournit
                        if isinstance(parsed, dict) and parsed.get("confidence") is not None:
                            try:
                                base_conf = float(parsed.get("confidence"))
                            except Exception:
                                pass
                        else:
                            # Tentative de réparation via Groq (qwen3-32b) si JSON invalide
                            if call_groq and parsed.get("error"):
                                repair_prompt = (
                                    "Tu es un réparateur JSON. "
                                    "On te donne un texte qui devait être un JSON valide selon ce schéma : "
                                    "{\"summary\":[],\"scenarios\":[],\"risks\":[],\"impacts\":{},\"actions\":[],\"confidence\":0.0,\"data_needed\":[],\"phase_scores\":{},\"ml_prior\":{}}. "
                                    "Renvoie UNIQUEMENT un JSON valide qui suit ce schéma, sans texte autour. "
                                    "Si une clé manque, mets une valeur par défaut appropriée."
                                )
                                messages_repair = [
                                    {"role": "system", "content": repair_prompt},
                                    {"role": "user", "content": full_answer or verdict_text or ""},
                                ]
                                try:
                                    res_repair = call_groq(
                                        messages=messages_repair,
                                        model="qwen/qwen3-32b",
                                        max_tokens=600,
                                        temperature=0.0,
                                    )
                                    if res_repair.get("ok"):
                                        repaired = res_repair.get("answer", "")
                                        try:
                                            repaired_parsed = json.loads(repaired)
                                            if isinstance(repaired_parsed, dict):
                                                parsed = repaired_parsed
                                                # phase_scores par défaut
                                                if isinstance(parsed.get("phase_scores"), list):
                                                    parsed["phase_scores"] = {}
                                                if parsed.get("phase_scores") is None:
                                                    parsed["phase_scores"] = {}
                                                if ml_prior:
                                                    parsed["ml_prior"] = ml_prior
                                                if parsed.get("confidence") is None:
                                                    parsed["confidence"] = base_conf
                                                try:
                                                    parsed = (
                                                        validate_llm_response(parsed)
                                                        if validate_llm_response
                                                        else parsed
                                                    )
                                                except Exception as e3:
                                                    parsed = {
                                                        "error": f"llm_validation_error_repair: {e3}",
                                                        "raw": repaired,
                                                    }
                                                logger.warning("repair_llm_used=groq_qwen3_32b")
                                            else:
                                                parsed = {
                                                    "error": "repair_return_not_dict",
                                                    "raw": repaired,
                                                }
                                        except Exception as e2:
                                            parsed = {
                                                "error": f"repair_json_error: {e2}",
                                                "raw": repaired,
                                            }
                                except Exception as e:
                                    parsed = {
                                        "error": f"repair_call_failed: {e}",
                                        "raw": full_answer or verdict_text,
                                    }
                    else:
                        parsed = {
                            "error": "json_parse_failed",
                            "raw": full_answer or verdict_text,
                        }
                    met["parse_ms"] = (
                        time.perf_counter() - t_parse
                    ) * 1000.0

                    # Ajustement return_adjust (LLM) sur l'ensemble
                    expected_return_final = expected_return_ensemble
                    if isinstance(parsed, dict):
                        ra = parsed.get("return_adjust")
                        try:
                            if ra is not None:
                                ra = float(ra)
                                ra = max(min(ra, 0.03), -0.03)  # clamp ±3%
                                if expected_return_final is None and expected_return is not None:
                                    expected_return_final = expected_return
                                if expected_return_final is not None:
                                    expected_return_final = expected_return_final + ra
                        except Exception:
                            pass

                    logger.debug(
                        "judge_llm_call",
                        extra={
                            "ticker": sym,
                            "model": model_used,
                            "provider": res.get("provider") if isinstance(res, dict) else None,
                            "answer_len": len(full_answer or ""),
                            "parsed_keys": list(parsed.keys()) if isinstance(parsed, dict) else None,
                            "parsed_conf": parsed.get("confidence") if isinstance(parsed, dict) else None,
                            "parse_error": parsed.get("error") if isinstance(parsed, dict) else None,
                            "expected_return_raw": expected_return,
                            "expected_return_ensemble": expected_return_ensemble,
                            "expected_return_final": expected_return_final,
                        },
                    )

                    # Default if parsed vide
                    if not parsed or (
                        isinstance(parsed, dict)
                        and parsed.get("error") == "json_parse_failed"
                    ):
                        fallback_used = "simple_verdict_from_forecast"
                        fallback_news = _news_for(sym)
                        news_titles = [
                            n.get("title")
                            for n in fallback_news[:3]
                            if n.get("title")
                        ]
                        parsed = {
                            "summary": [verdict_text],
                            "scenarios": [
                                {
                                    "name": "base",
                                    "p": 0.55,
                                    "direction": direction,
                                },
                                {
                                    "name": "alt",
                                    "p": 0.25,
                                    "direction": "flat",
                                },
                                {
                                    "name": "risk",
                                    "p": 0.2,
                                    "direction": "opposite",
                                },
                            ],
                            "risks": news_titles or ["news sensitivity"],
                            "impacts": {
                                "equity": [f"{sym} {direction}"],
                                "rates": [],
                                "FX": [],
                                "commodities": [],
                            },
                            "actions": [
                                f"Surveiller {sym}, expected_return={expected_return}",
                                "Réviser si news négatives",
                            ],
                            "confidence": base_conf,
                        }

                    if debug:
                        conf_final_dbg = base_conf
                        if isinstance(parsed, dict) and parsed.get("confidence") is not None:
                            try:
                                conf_final_dbg = float(parsed.get("confidence"))
                            except Exception:
                                pass
                        add_trace(
                            "llm_call",
                            ticker=sym,
                            ok=isinstance(res, dict) and res.get("ok"),
                            model=model_used,
                            provider=res.get("provider") if isinstance(res, dict) else None,
                            parsed_ok=isinstance(parsed, dict) and not parsed.get("error"),
                            fallback=fallback_used,
                            llm_ms=met.get("llm_ms"),
                            confidence=conf_final_dbg,
                        )

                    met["total_ms"] = (
                        time.perf_counter() - t_total
                    ) * 1000.0

                    if log_metrics:
                        try:
                            provider = (
                                res.get("provider_raw")
                                or res.get("provider")
                                if isinstance(res, dict)
                                else None
                            )
                            # Consolider la confiance finale à partir du parsing LLM si dispo
                            conf_final_metric = base_conf
                            if isinstance(parsed, dict) and parsed.get("confidence") is not None:
                                try:
                                    conf_final_metric = float(parsed.get("confidence"))
                                except Exception:
                                    pass
                            log_metrics(
                                "judge_metrics",
                                ticker=sym,
                                news_ms=met.get("news_ms"),
                                payload_ms=met.get("payload_ms"),
                                ml_prior_ms=met.get("ml_prior_ms"),
                                llm_ms=met.get("llm_ms"),
                                parse_ms=met.get("parse_ms"),
                                total_ms=met.get("total_ms"),
                                llm_model=model_used,
                                llm_provider=provider,
                            )
                        except Exception:
                            pass
                    if debug:
                        conf_final_dbg2 = base_conf
                        if isinstance(parsed, dict) and parsed.get("confidence") is not None:
                            try:
                                conf_final_dbg2 = float(parsed.get("confidence"))
                            except Exception:
                                pass
                        add_trace(
                            "row_done",
                            ticker=sym,
                            total_ms=met.get("total_ms"),
                            confidence=conf_final_dbg2,
                            expected_return=expected_return_final,
                        )

                    conf_final = base_conf
                    if isinstance(parsed, dict) and parsed.get("confidence") is not None:
                        try:
                            conf_final = float(parsed.get("confidence"))
                        except Exception:
                            pass

                    # Normaliser les scénarios et dériver un niveau de risque simple
                    def _normalize_scenarios(sc_list: Any) -> List[Dict[str, Any]]:
                        out = []
                        if not isinstance(sc_list, list):
                            return out
                        for sc in sc_list:
                            if not isinstance(sc, dict):
                                continue
                            try:
                                pval = float(sc.get("p"))
                            except Exception:
                                pval = 0.0
                            if pval > 1.0:
                                pval = pval / 100.0
                            out.append(
                                {
                                    "name": sc.get("name"),
                                    "p": pval,
                                    "description": sc.get("description"),
                                }
                            )
                        total = sum(s.get("p", 0.0) for s in out)
                        if total > 0:
                            for s in out:
                                s["p"] = s.get("p", 0.0) / total
                        return out

                    scenarios_norm = _normalize_scenarios(parsed.get("scenarios") if isinstance(parsed, dict) else None)
                    if isinstance(parsed, dict):
                        parsed["scenarios"] = scenarios_norm

                    def _derive_risk_level(sc_list: List[Dict[str, Any]]) -> str:
                        if not sc_list:
                            return "medium"
                        p_bear = max(
                            (s.get("p") or 0.0)
                            for s in sc_list
                            if (s.get("name") or "").lower().startswith("bear")
                        ) if any((s.get("name") or "").lower().startswith("bear") for s in sc_list) else 0.0
                        if p_bear >= 0.35:
                            return "high"
                        if p_bear <= 0.15:
                            return "low"
                        return "medium"

                    derived_risk = _derive_risk_level(scenarios_norm)

                    # Phase scores: distinguer brut (pipeline) vs normalisé (0-1)
                    raw_phase_scores = {
                        k: (v.get("score") if isinstance(v, dict) else None)
                        for k, v in (phase_blocks or {}).items()
                    } or None
                    parsed_phase_scores = (
                        parsed.get("phase_scores") if isinstance(parsed, dict) else None
                    )

                    def _normalize_scores(scores: Dict[str, Any]) -> Dict[str, float]:
                        out: Dict[str, float] = {}
                        for k, v in (scores or {}).items():
                            try:
                                val = float(v)
                                # si >1, on suppose une échelle 0-100
                                if val > 1.0:
                                    val = val / 100.0
                                # clamp 0-1
                                if val < 0:
                                    val = 0.0
                                if val > 1:
                                    val = 1.0
                                out[k] = val
                            except Exception:
                                pass
                        return out

                    norm_phase_scores = None
                    if parsed_phase_scores and isinstance(parsed_phase_scores, dict):
                        norm_phase_scores = _normalize_scores(parsed_phase_scores)
                    elif raw_phase_scores and isinstance(raw_phase_scores, dict):
                        norm_phase_scores = _normalize_scores(raw_phase_scores)

                    # Freshness timestamps
                    latest_news_ts = None
                    try:
                        ts_vals = [
                            _normalize_ts_str(n.get("ts") or n.get("published_at") or n.get("ingested_at"))
                            for n in news_items
                        ]
                        ts_vals = [t for t in ts_vals if t]
                        if ts_vals:
                            latest_news_ts = max(ts_vals)
                    except Exception:
                        latest_news_ts = None

                    price_live_ts = None
                    try:
                        price_live_ts = _normalize_ts_str(feat.get("tech", {}).get("live_ts"))
                    except Exception:
                        price_live_ts = None

                    price_history_ts = None
                    try:
                        if price_points:
                            price_history_ts = _normalize_ts_str(price_points[-1][0])
                    except Exception:
                        price_history_ts = None

                    data_timestamps = {
                        "macro": macro_ctx.get("latest_date") or macro_ctx.get("cpi_last_date"),
                        "macro_latest": macro_ctx.get("latest_date"),
                        "macro_cpi": macro_ctx.get("cpi_last_date"),
                        "price_live": price_live_ts,
                        "price_history": price_history_ts,
                        "news_last": latest_news_ts,
                    }

                    # Alerte fraîcheur macro si trop ancien (>90j)
                    try:
                        macro_ref_date = macro_ctx.get("latest_date") or macro_ctx.get("cpi_last_date")
                        if macro_ref_date:
                            last_macro = datetime.fromisoformat(str(macro_ref_date) + "T00:00:00+00:00")
                            age_days = (datetime.now(timezone.utc) - last_macro).days
                            if age_days > 90:
                                parsed.setdefault("data_needed", []).append(f"macro stale ({age_days}d)")
                    except Exception:
                        pass

                    # Deterministic cleanup of LLM-proposed data_needed.
                    if isinstance(parsed, dict):
                        raw_needed = parsed.get("data_needed")
                        if not isinstance(raw_needed, list):
                            raw_needed = []

                        has_rsi = feat.get("tech", {}).get("rsi") is not None
                        has_news = len(news_items) > 0
                        has_macro = bool(data_timestamps.get("macro"))
                        has_price_live = bool(data_timestamps.get("price_live"))
                        has_price_history = bool(data_timestamps.get("price_history"))

                        cleaned_needed: List[str] = []
                        seen_needed = set()
                        for item in raw_needed:
                            txt = str(item).strip()
                            if not txt:
                                continue
                            low = txt.lower()

                            # Drop asks already satisfied by payload/context.
                            if has_rsi and "rsi" in low:
                                continue
                            if has_news and ("news sentiment" in low or "real-time news sentiment" in low):
                                continue
                            if has_macro and low in {"macro data", "macro indicators", "latest macro data"}:
                                continue
                            if has_price_live and ("real-time price" in low or "prix en temps réel" in low):
                                continue
                            if has_price_history and ("price history" in low or "historique prix" in low):
                                continue

                            key = low
                            if key in seen_needed:
                                continue
                            seen_needed.add(key)
                            cleaned_needed.append(txt)

                        parsed["data_needed"] = cleaned_needed[:8]

                    return {
                        "ticker": sym,
                        "verdict": verdict_text,
                        "confidence": conf_final,
                        "expected_return": expected_return_final,
                        "expected_return_raw": expected_return,
                        "expected_return_ensemble": expected_return_ensemble,
                        "risk_level": derived_risk,
                        "price_regime": price_features.get("price_regime") if isinstance(price_features, dict) else None,
                        "volatility": price_features.get("volatility") if isinstance(price_features, dict) else None,
                        "reasoning": parsed.get("summary")
                        if isinstance(parsed, dict)
                        else None,
                        "analysis": parsed
                        if isinstance(parsed, dict)
                        else {"summary": [verdict_text]},
                        "phases": phase_blocks or None,
                        "phase_scores_raw": raw_phase_scores,
                        "phase_scores": norm_phase_scores or None,
                        "ml_prior": ml_prior,
                        "raw_answer": full_answer or verdict_text,
                        "generated_at": datetime.utcnow().isoformat() + "Z",
                        "model_version": model_used or "econ_llm_agent",
                        "provider": (
                            res.get("provider_raw") or res.get("provider")
                            if isinstance(res, dict)
                            else None
                        ),
                        "source": ["judge_route", "forecasts_llm"],
                        "meta": {
                            "data_timestamps": data_timestamps,
                            "provider": (
                                res.get("provider_raw") or res.get("provider")
                                if isinstance(res, dict)
                                else None
                            ),
                        },
                        **(
                            {
                                "debug_payload": payload,
                                "debug_llm_res": res,
                            }
                            if debug
                            else {}
                        ),
                    }

            tasks = [asyncio.create_task(_process_row(r)) for r in top_rows]
            generated_list = await asyncio.gather(*tasks)
            verdicts = [g for g in generated_list if g]

            # Filtering and stats
            if ticker:
                ticker_list = [t.upper() for t in ticker]
                verdicts = [
                    v
                    for v in verdicts
                    if v.get("ticker", "").upper() in ticker_list
                ]

            confidence_filtered = [
                v
                for v in verdicts
                if v.get("confidence", 0) >= min_confidence
            ]
            # Si filtrage vide mais des erreurs LLM existent, on renvoie quand même pour diagnostic
            if not confidence_filtered and verdicts:
                has_error = any(
                    isinstance(v.get("analysis"), dict) and v["analysis"].get("error")
                    for v in verdicts
                )
                if has_error:
                    confidence_filtered = verdicts

            reverse_sort = sort_order != "asc"

            if sort_by == "confidence":
                confidence_filtered.sort(
                    key=lambda x: x.get("confidence", 0),
                    reverse=reverse_sort,
                )
            elif sort_by == "expected_return":
                confidence_filtered.sort(
                    key=lambda x: x.get("expected_return", 0)
                    or 0.0,
                    reverse=reverse_sort,
                )
            elif sort_by == "score":
                confidence_filtered.sort(
                    key=lambda x: x.get("score", x.get("confidence", 0)),
                    reverse=reverse_sort,
                )
            elif sort_by == "risk_level":
                risk_order = {
                    "low": 0,
                    "medium": 1,
                    "high": 2,
                    "critical": 3,
                }

                def _risk_val(v: Dict[str, Any]) -> int:
                    return risk_order.get(v.get("risk_level", "medium"), 1)

                confidence_filtered.sort(
                    key=_risk_val, reverse=reverse_sort
                )
            elif sort_by == "timestamp":
                confidence_filtered.sort(
                    key=lambda x: x.get("generated_at", ""),
                    reverse=reverse_sort,
                )
            else:
                confidence_filtered.sort(
                    key=lambda x: x.get("confidence", 0),
                    reverse=reverse_sort,
                )

            limited_verdicts = confidence_filtered[:limit]
            total_verdicts = len(verdicts)
            high_conf_count = len(
                [
                    v
                    for v in limited_verdicts
                    if v.get("confidence", 0) >= 0.7
                ]
            )
            avg_confidence = (
                sum(v.get("confidence", 0) for v in limited_verdicts)
                / len(limited_verdicts)
                if limited_verdicts
                else 0.0
            )

            now_iso = datetime.utcnow().isoformat() + "Z"

            response_obj = {
                "verdicts": limited_verdicts,
                "count": len(limited_verdicts),
                "stats": {
                    "total_verdicts": total_verdicts,
                    "high_confidence_count": high_conf_count,
                    "avg_confidence": avg_confidence,
                    "generated_at": now_iso,
                },
                "filters_applied": {
                    "min_confidence": min_confidence,
                    "tickers": ticker,
                    "sort_by": sort_by,
                    "sort_order": sort_order,
                    "limit": limit,
                },
                "generated_at": now_iso,
                "source": ["judge_route", "forecasts_llm"],
            }
            # Optionnel : version typée/canonique des verdicts (Pydantic schemas)
            typed_verdicts = []
            if build_judge_verdict:
                for v in limited_verdicts:
                    try:
                        tv = build_judge_verdict(v, profile=profile)
                        if hasattr(tv, "model_dump"):
                            typed_verdicts.append(tv.model_dump(exclude_none=True))
                        elif hasattr(tv, "dict"):
                            typed_verdicts.append(tv.dict(exclude_none=True))
                    except Exception as e:
                        logger.info("verdict_typed_failed", extra={"error": str(e)})
                        continue

            # On ne garde qu'une seule clé pour la liste finale : verdicts typés si dispo.
            if typed_verdicts:
                response_obj["verdicts"] = typed_verdicts

            if debug:
                response_obj["debug_pipeline"] = traces
                response_obj["verdicts_raw"] = limited_verdicts
            response_obj.pop("verdicts_typed", None)
            return response_obj

        # Ici on pourrait rebrancher load_or_compute si tu veux du cache :
        # verdicts_data = await load_or_compute("judge_verdicts", compute_judge_verdicts)
        verdicts_data = await compute_judge_verdicts()
        if cache_key and isinstance(verdicts_data, dict):
            _JUDGE_RESPONSE_CACHE[cache_key] = {
                "ts": time.time(),
                "data": deepcopy(verdicts_data),
            }
            _prune_judge_cache()

        return {
            "ok": True,
            "data": verdicts_data,
            "freshness": verdicts_data.get(
                "generated_at", datetime.utcnow().isoformat() + "Z"
            ),
        }
    except Exception as e:
        logger.error(f"Critical error in /judge endpoint: {str(e)}")
        now_iso = datetime.utcnow().isoformat() + "Z"
        return {
            "ok": True,
            "data": {
                "verdicts": [],
                "count": 0,
                "stats": {
                    "total_verdicts": 0,
                    "high_confidence_count": 0,
                    "avg_confidence": 0.0,
                    "generated_at": now_iso,
                },
                "filters_applied": {
                    "min_confidence": min_confidence,
                    "tickers": ticker,
                    "sort_by": sort_by,
                    "sort_order": sort_order,
                    "limit": limit,
                },
                "generated_at": now_iso,
                "source": [
                    "judge_route",
                    "critical_error_fallback",
                    "merged",
                ],
                "error": str(e),
                "message": "Judge endpoint failed critically but fallback data returned to maintain never-empty contract",
            },
            "freshness": "error",
        }


# Backward compatibility export
judge_router = router


@router.get("/options")
async def get_judge_options():
    """Options for judge UI (never-empty)."""
    try:
        generated_at = datetime.utcnow().isoformat() + "Z"
        options = {
            "sort_options": [
                {"value": "confidence", "label": "Confiance"},
                {"value": "expected_return", "label": "Retour attendu"},
                {"value": "risk_level", "label": "Niveau de risque"},
                {"value": "timestamp", "label": "Date de génération"},
            ],
            "risk_levels": ["low", "medium", "high", "critical"],
            "confidence_thresholds": [
                {"label": "Toutes", "value": 0.0},
                {"label": "Haute confiance (0.7+)", "value": 0.7},
                {"label": "Très haute confiance (0.8+)", "value": 0.8},
                {"label": "Excellente confiance (0.9+)", "value": 0.9},
            ],
            "generated_at": generated_at,
            "source": ["judge_options_route", "ui_helper_data", "merged"],
        }
        return {"ok": True, "data": options, "freshness": options["generated_at"]}
    except Exception as e:
        now_iso = datetime.utcnow().isoformat() + "Z"
        return {
            "ok": True,
            "data": {
                "sort_options": [
                    {"value": "confidence", "label": "Confiance"},
                    {"value": "expected_return", "label": "Retour attendu"},
                ],
                "risk_levels": ["low", "medium", "high"],
                "confidence_thresholds": [
                    {"label": "Toutes", "value": 0.0},
                    {"label": "Haute confiance (0.7+)", "value": 0.7},
                ],
                "generated_at": now_iso,
                "error": str(e),
                "message": "Judge options endpoint failed but fallback returned to maintain never-empty contract",
            },
            "freshness": "error",
        }
