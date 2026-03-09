"""
Judge API Routes - merged version with options + caching
"""
from datetime import datetime, timezone
import json
import logging
import asyncio
import os
import re
from copy import deepcopy
from email.utils import parsedate_to_datetime
from pathlib import Path
import time
from typing import Dict, Any, List, Optional, Awaitable, Callable, Literal, Tuple

from fastapi import APIRouter, Query, HTTPException, Header
from pydantic import BaseModel, Field
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
from core.ticker_normalization import normalize_ticker, normalize_tickers

try:
    from services.service_standard import service_response_with_metadata  # type: ignore
except Exception:  # pragma: no cover
    try:
        from platform.legacy.services.service_standard import service_response_with_metadata  # type: ignore
    except Exception:  # pragma: no cover
        def service_response_with_metadata(data, *, default_source, freshness=None, status=None, error=None):
            resolved_error = error if error is not None else data.get("error")
            resolved_status = status or ("degraded" if resolved_error else "ok")
            resolved_freshness = freshness or data.get("freshness") or data.get("generated_at")
            return {
                "ok": True,
                "data": data,
                "freshness": resolved_freshness,
                "status": resolved_status,
                "error": resolved_error,
            }

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
    from domains.judge.application.judge_pipeline import (
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
    from domains.judge.application.judge_builder import build_judge_verdict  # type: ignore
except Exception:
    build_judge_verdict = None
try:
    from schemas.judge import JudgeResponse  # type: ignore
except Exception:
    JudgeResponse = None  # type: ignore
# G4F fallback client
try:
    from domains.judge.application.g4f_client import call_llm, get_ranked_tested_models  # type: ignore
except Exception:
    call_llm = None
    get_ranked_tested_models = None
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
JUDGE_NEWS_ITEMS_PER_TICKER = min(
    30, max(5, int(os.getenv("JUDGE_NEWS_ITEMS_PER_TICKER", "20") or "20"))
)
JUDGE_CHAR_BUDGET = max(
    800, int(os.getenv("JUDGE_CHAR_BUDGET", "1800") or "1800")
)
JUDGE_ALLOW_DEBUG_FULL = str(os.getenv("JUDGE_ALLOW_DEBUG_FULL", "0")).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
JUDGE_DEBUG_ADMIN_TOKEN = str(os.getenv("JUDGE_DEBUG_ADMIN_TOKEN", "") or "").strip()
JUDGE_DEBUG_ANSWER_SNIPPET_CHARS = max(
    200, int(os.getenv("JUDGE_DEBUG_ANSWER_SNIPPET_CHARS", "600") or "600")
)
JUDGE_DEBUG_QUESTION_SNIPPET_CHARS = max(
    100, int(os.getenv("JUDGE_DEBUG_QUESTION_SNIPPET_CHARS", "240") or "240")
)
_JUDGE_RESPONSE_CACHE: Dict[str, Dict[str, Any]] = {}
_JUDGE_INFLIGHT: Dict[str, asyncio.Task] = {}
_JUDGE_INFLIGHT_LOCK = asyncio.Lock()

JudgeSortBy = Literal[
    "confidence",
    "expected_return",
    "score",
    "risk_level",
    "timestamp",
]
JudgeSortOrder = Literal["asc", "desc"]

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


def _normalize_mode(raw_mode: Any) -> str:
    low = str(raw_mode or "").strip().lower()
    if low in {"fastest", "ultrafast", "speed", "speedrun"}:
        return "fastest"
    if low in {"dev", "fast", "test", "testing"}:
        return "dev"
    return "best"


def _resolve_judge_llm_mode() -> str:
    # Backward compatible envs:
    # - legacy: JUDGE_LLM_MODE
    # - canonical: LLM_JUDGE_MODE
    raw_mode = (
        os.getenv("LLM_JUDGE_MODE")
        or os.getenv("JUDGE_LLM_MODE")
        or os.getenv("LLM_MODEL_MODE")
        or "best"
    )
    return _normalize_mode(raw_mode)


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _resolve_debug_full_access(
    *,
    debug: bool,
    debug_full: bool,
    debug_token: Optional[str],
) -> Tuple[bool, Optional[str]]:
    if not (debug and debug_full):
        return False, None
    if not JUDGE_ALLOW_DEBUG_FULL:
        return False, "set JUDGE_ALLOW_DEBUG_FULL=1"
    if JUDGE_DEBUG_ADMIN_TOKEN:
        if str(debug_token or "").strip() != JUDGE_DEBUG_ADMIN_TOKEN:
            return False, "missing_or_invalid_X-Debug-Token"
    return True, None


def _judge_risk_levels() -> List[str]:
    return ["low", "medium", "high", "critical"]


def _resolve_judge_timeouts(llm_mode: str) -> Tuple[int, int, int]:
    mode = _normalize_mode(llm_mode)
    row_timeout_s = max(
        8,
        int(os.getenv("JUDGE_ROW_TIMEOUT_SECONDS", "35") or "35"),
    )

    if mode == "fastest":
        analyze_default = int(
            os.getenv("JUDGE_ANALYZE_TIMEOUT_SECONDS_FASTEST", "10") or "10"
        )
        g4f_default = int(
            os.getenv("JUDGE_G4F_TIMEOUT_SECONDS_FASTEST", "12") or "12"
        )
    elif mode == "dev":
        analyze_default = int(
            os.getenv("JUDGE_ANALYZE_TIMEOUT_SECONDS_DEV", "25") or "25"
        )
        g4f_default = int(
            os.getenv("JUDGE_G4F_TIMEOUT_SECONDS_DEV", "20") or "20"
        )
    else:
        analyze_default = int(
            os.getenv("JUDGE_ANALYZE_TIMEOUT_SECONDS", "45") or "45"
        )
        g4f_default = int(
            os.getenv("JUDGE_G4F_TIMEOUT_SECONDS", "60") or "60"
        )

    # Keep nested LLM timeouts below row timeout budget to avoid guaranteed row_timeout fallbacks.
    analyze_timeout_s = max(6, min(analyze_default, max(8, row_timeout_s - 2)))
    g4f_timeout_s = max(5, min(g4f_default, max(6, row_timeout_s - 1)))
    return row_timeout_s, analyze_timeout_s, g4f_timeout_s


def _judge_cache_key(
    *,
    limit: int,
    min_confidence: float,
    ticker: Optional[List[str]],
    sort_by: Optional[str],
    sort_order: Optional[str],
    profile: str,
) -> str:
    tickers = sorted(normalize_tickers(ticker or []))
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


def _append_source_tag(data: Dict[str, Any], tag: str) -> None:
    source = data.get("source")
    if isinstance(source, list):
        if tag not in source:
            source.append(tag)
        return
    data["source"] = ["judge_route", tag]


def _truncate_str(value: Any, max_chars: int) -> str:
    txt = str(value or "")
    if len(txt) <= max_chars:
        return txt
    return f"{txt[:max_chars]}…"


def _sanitize_debug_payload(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    news = payload.get("news")
    attachments = payload.get("attachments")
    features = payload.get("features")
    return {
        "question_excerpt": _truncate_str(
            payload.get("question"), JUDGE_DEBUG_QUESTION_SNIPPET_CHARS
        ),
        "locale": payload.get("locale"),
        "meta": payload.get("meta") if isinstance(payload.get("meta"), dict) else {},
        "feature_keys": sorted(list(features.keys())) if isinstance(features, dict) else [],
        "news_count": len(news) if isinstance(news, list) else 0,
        "attachment_count": len(attachments) if isinstance(attachments, list) else 0,
    }


def _sanitize_debug_llm_res(res: Any) -> Dict[str, Any]:
    if not isinstance(res, dict):
        return {}
    return {
        "ok": res.get("ok"),
        "provider": res.get("provider_raw") or res.get("provider"),
        "model": res.get("model"),
        "usage": res.get("usage") if isinstance(res.get("usage"), dict) else {},
        "answer_excerpt": _truncate_str(
            res.get("answer"), JUDGE_DEBUG_ANSWER_SNIPPET_CHARS
        ),
    }


def _sanitize_verdict_for_public(
    verdict: Dict[str, Any],
    *,
    keep_raw: bool,
    keep_debug_fields: bool,
) -> Dict[str, Any]:
    public_row = deepcopy(verdict)
    if not keep_raw:
        public_row.pop("raw_answer", None)
    if not keep_debug_fields:
        public_row.pop("debug_payload", None)
        public_row.pop("debug_llm_res", None)
    return public_row


def _judge_go_no_go(
    *,
    llm_ok: bool,
    parsed_error: bool,
    confidence: float,
    data_quality_score: float,
    news_count: int,
    data_needed: Optional[List[str]],
) -> Dict[str, Any]:
    reasons: List[str] = []
    if not llm_ok:
        reasons.append("llm_provider_not_healthy")
    if parsed_error:
        reasons.append("llm_payload_validation_failed")
    if confidence < 0.50:
        reasons.append("low_confidence")
    if data_quality_score < 0.40:
        reasons.append("insufficient_data_quality")
    if news_count < max(5, JUDGE_NEWS_ITEMS_PER_TICKER // 2):
        reasons.append("insufficient_news")
    if isinstance(data_needed, list) and len(data_needed) >= 3:
        reasons.append("multiple_data_gaps")

    decision = "go" if not reasons else "no_go"
    return {
        "decision": decision,
        "eligible": decision == "go",
        "reasons": reasons,
        "confidence": round(max(0.0, min(1.0, float(confidence))), 4),
        "data_quality": round(max(0.0, min(1.0, float(data_quality_score))), 4),
    }


def _build_strategy_playbook(verdict: Dict[str, Any], *, profile: str) -> Dict[str, Any]:
    """Project a Judge verdict into a minimal strategy playbook payload."""
    ticker = normalize_ticker(str(verdict.get("ticker") or "").strip()) or "UNKNOWN"

    def _coerce_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

    def _coerce_text_list(value: Any) -> List[str]:
        if not isinstance(value, list):
            return [str(value).strip()] if str(value).strip() else []
        values: List[str] = []
        seen = set()
        for item in value:
            text = str(item or "").strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            values.append(text)
        return values

    go_no_go = verdict.get("go_no_go") or {}
    decision = str(go_no_go.get("decision") or "").strip().lower() if isinstance(go_no_go, dict) else ""
    if decision in {"go", "buy", "long"}:
        decision = "go"
    elif decision in {"no_go", "sell", "short", "no-go"}:
        decision = "no_go"
    elif not decision:
        confidence = _coerce_float(verdict.get("confidence"), 0.0)
        expected_return = _coerce_float(verdict.get("expected_return"), 0.0)
        if confidence >= 0.6 and expected_return >= 0:
            decision = "go"
        elif confidence <= 0.4 and expected_return <= 0:
            decision = "no_go"
        else:
            decision = "hold"

    summary = verdict.get("summary") or verdict.get("reasoning") or []
    if isinstance(summary, str):
        summary = [summary]
    if not isinstance(summary, list):
        summary = []

    expected_return = _coerce_float(verdict.get("expected_return"), 0.0)
    confidence = _coerce_float(verdict.get("confidence"), 0.0)
    risk_level = str(verdict.get("risk_level") or "medium").strip().lower()
    if risk_level not in {"low", "medium", "high", "critical"}:
        risk_level = "medium"
    horizon = str(verdict.get("horizon") or "1w").strip() or "1w"
    playbook_id = f"{ticker}:{horizon}:{decision}:{profile}"
    reasons = _coerce_text_list((go_no_go or {}).get("reasons", [])) if isinstance(go_no_go, dict) else []

    conflicts: List[str] = []
    if decision == "go" and risk_level in {"high", "critical"}:
        conflicts.append("risk_profile_too_aggressive")
    if decision == "no_go" and expected_return > 0.03:
        conflicts.append("positive_signal_overridden_by_filters")

    return {
        "playbook_id": playbook_id,
        "ticker": ticker,
        "horizon": horizon,
        "profile": profile,
        "decision": decision,
        "confidence": round(confidence, 4),
        "expected_return": round(expected_return, 6),
        "risk_level": risk_level,
        "summary": _coerce_text_list(summary)[:2],
        "recommended_actions": _coerce_text_list(verdict.get("actions") or []),
        "data_needed": _coerce_text_list(verdict.get("data_needed") or []),
        "evidence": {
            "scenario_count": len(verdict.get("scenarios") or []),
            "risk_count": len(verdict.get("risks") or []),
            "impact_keys": sorted((verdict.get("impacts") or {}).keys()),
        },
        "reasons": reasons,
        "conflicts": conflicts,
        "decision_id": verdict.get("decision_id"),
    }


async def _compute_singleflight(
    cache_key: str,
    compute_fn: Callable[[], Awaitable[Dict[str, Any]]],
) -> Tuple[Dict[str, Any], bool]:
    """Compute once per cache_key and let concurrent callers await the same task."""
    is_leader = False
    async with _JUDGE_INFLIGHT_LOCK:
        task = _JUDGE_INFLIGHT.get(cache_key)
        if task is None:
            task = asyncio.create_task(compute_fn())
            _JUDGE_INFLIGHT[cache_key] = task
            is_leader = True
    try:
        result = await task
        return result, is_leader
    finally:
        if is_leader:
            async with _JUDGE_INFLIGHT_LOCK:
                current = _JUDGE_INFLIGHT.get(cache_key)
                if current is task:
                    _JUDGE_INFLIGHT.pop(cache_key, None)


def _normalize_ts_str(ts: Any) -> Optional[str]:
    """Normalize timestamp-like values to an ISO string."""
    if ts is None:
        return None
    try:
        if isinstance(ts, str):
            raw = ts.strip()
            if not raw:
                return None
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except Exception:
                dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
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


async def _legacy_get_judge_verdicts(
    limit: int = Query(20, ge=1, le=100, description="Limite de résultats (1-100)"),
    min_confidence: float = Query(
        0.3, ge=0.0, le=1.0, description="Confiance minimum pour inclusion (0.0-1.0)"
    ),
    ticker: Optional[List[str]] = Query(
        None, description="Filtre par ticker (plusieurs autorisés)"
    ),
    sort_by: JudgeSortBy = Query(
        "confidence",
        description="Tri par: confidence, expected_return, score, risk_level, timestamp",
    ),
    sort_order: JudgeSortOrder = Query("desc", description="Ordre de tri: asc, desc"),
    profile: str = Query("equity_1w", description="Judge profile: equity_1w, sector_regime, etc"),
    debug: bool = Query(False, description="Active les traces et le payload LLM dans la réponse"),
    debug_full: bool = Query(
        False,
        description="Inclut le payload debug complet (reserve admin; necessite JUDGE_ALLOW_DEBUG_FULL=1).",
    ),
    x_debug_token: Optional[str] = Header(
        default=None,
        alias="X-Debug-Token",
        description="Token admin requis pour debug_full si JUDGE_DEBUG_ADMIN_TOKEN est configure.",
    ),
):
    """Get LLM judge verdicts for tickers (never-empty, cached). Supports multiple profiles."""
    logger.info(f"🔍 /api/judge called: limit={limit}, profile={profile}, ticker={ticker}")
    logger.info(
        "judge_debug_flags debug=%r (%s) debug_full=%r (%s)",
        debug,
        type(debug).__name__,
        debug_full,
        type(debug_full).__name__,
    )
    try:
        debug_full_enabled, debug_full_reason = _resolve_debug_full_access(
            debug=debug,
            debug_full=debug_full,
            debug_token=x_debug_token,
        )
        if debug and debug_full and not debug_full_enabled:
            logger.info(
                "judge_debug_full_requested_but_not_allowed reason=%s",
                debug_full_reason or "unknown",
            )
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
                    _append_source_tag(cached_data, "judge_cache_hit")
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
            if debug and debug_full and not debug_full_enabled:
                add_trace("debug_full_denied", reason=debug_full_reason or "unknown")

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
            backtests = load_json("backtests") or {}

            backend_root = Path(__file__).resolve().parents[2]
            allow_yahoo_snapshot = str(
                os.getenv("JUDGE_ALLOW_YAHOO_SNAPSHOT", "0")
            ).strip().lower() in {"1", "true", "yes"}

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

            def _backtest_context() -> Dict[str, Any]:
                """Extract global calibration context from backtests snapshot."""
                bt = backtests if isinstance(backtests, dict) else {}
                cand = bt.get("overall_metrics") if isinstance(bt.get("overall_metrics"), dict) else {}
                if not cand and isinstance(bt.get("results"), dict):
                    cand = bt.get("results") or {}
                hit_rate = None
                n_trades = 0
                generated_at = None
                try:
                    if cand.get("hit_rate") is not None:
                        hit_rate = float(cand.get("hit_rate"))
                        hit_rate = max(0.0, min(1.0, hit_rate))
                except Exception:
                    hit_rate = None
                for key in ("n_trades", "total_trades"):
                    try:
                        if cand.get(key) is not None:
                            n_trades = max(n_trades, int(cand.get(key)))
                    except Exception:
                        pass
                generated_at = (
                    bt.get("generated_at")
                    or bt.get("saved_at")
                    or (cand.get("timestamp") if isinstance(cand, dict) else None)
                )
                return {
                    "hit_rate": hit_rate,
                    "n_trades": n_trades,
                    "generated_at": generated_at,
                }

            add_trace(
                "data_loaded",
                forecasts=_forecasts_count(),
                news_count=_news_count(),
            )
            backtest_ctx = _backtest_context()
            add_trace("backtest_context", **backtest_ctx)

            prices_data = _load_prices()
            macro_series = _load_macro()
            ownership_data = _load_ownership()
            judge_features = _load_judge_features()

            def _yahoo_snapshot(sym: str) -> Dict[str, Any]:
                if not allow_yahoo_snapshot:
                    return {}
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
                prof_tickers = set(normalize_tickers(prof.tickers or []))
                before = len(rows_sorted)
                rows_sorted = [
                    r
                    for r in rows_sorted
                    if normalize_ticker(r.get("ticker") or r.get("symbol") or "") in prof_tickers
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
                ticker_set = set(normalize_tickers(ticker))
                before = len(rows_sorted)
                rows_sorted = [
                    r
                    for r in rows_sorted
                    if normalize_ticker(r.get("ticker") or r.get("symbol") or "") in ticker_set
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
                        "sort_by": str(sort_by),
                        "sort_order": str(sort_order),
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
                        dt = parsedate_to_datetime(str(ts_val))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        return dt
                    except Exception:
                        pass
                    try:
                        dt = datetime.strptime(str(ts_val), "%Y-%m-%d")
                        return dt.replace(tzinfo=timezone.utc)
                    except Exception:
                        return None

            def _score_news_items(
                news_list: List[Dict[str, Any]], cap: int = 30
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
                    return _score_news_items(
                        rel, cap=max(JUDGE_NEWS_ITEMS_PER_TICKER + 5, 25)
                    )

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
                return _score_news_items(
                    rel, cap=max(JUDGE_NEWS_ITEMS_PER_TICKER + 5, 25)
                )

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

            # Candidate models come from tested lists generated/refreshed at startup.
            candidate_models: Optional[List[str]] = None
            model_limit = max(3, int(os.getenv("JUDGE_MODEL_LIMIT", "12") or "12"))
            ranked_models: List[str] = []
            working_models: List[str] = []
            try:
                if get_ranked_tested_models is not None:
                    ranked_models = [
                        m
                        for _, m in get_ranked_tested_models(
                            category_preference="forecast", limit=model_limit
                        )
                        if m
                    ]
            except Exception:
                ranked_models = []
            try:
                if not ranked_models and ensure_working_models is not None:
                    working_models = [
                        m for m in ensure_working_models(limit=model_limit, max_age_hours=6, min_ok=2) if m
                    ]
            except Exception:
                working_models = []

            merged_models: List[str] = []
            seen_models = set()
            for mod in ranked_models + working_models:
                key = str(mod).strip().lower()
                if not key or key in seen_models:
                    continue
                seen_models.add(key)
                merged_models.append(str(mod).strip())
                if len(merged_models) >= model_limit:
                    break
            if merged_models:
                candidate_models = merged_models

            # Optional emergency switch for local debug only.
            if str(os.getenv("JUDGE_FORCE_DEV_MODE", "0")).strip().lower() in {"1", "true", "yes", "on"}:
                os.environ["ECON_AGENT_MODE"] = "dev"
                os.environ["ECON_AGENT_MODELS"] = ",".join(
                    candidate_models
                    or [
                        "tngtech/deepseek-r1t2-chimera:free",
                        "openai/gpt-oss-120b:free",
                        "qwen/qwen3-235b-a22b:free",
                    ]
                )

            judge_llm_mode = _resolve_judge_llm_mode()
            row_timeout_s, judge_timeout_s, judge_g4f_timeout_s = _resolve_judge_timeouts(
                judge_llm_mode
            )
            fastest_skip_agent = (
                judge_llm_mode == "fastest"
                and _env_flag("JUDGE_FASTEST_SKIP_ECON_AGENT", True)
            )
            fastest_disable_paid_fallbacks = (
                judge_llm_mode == "fastest"
                and _env_flag("JUDGE_FASTEST_DISABLE_PAID_FALLBACKS", True)
            )
            fastest_skip_json_repair = (
                judge_llm_mode == "fastest"
                and _env_flag("JUDGE_FASTEST_SKIP_JSON_REPAIR", True)
            )
            allow_paid_fallbacks = not fastest_disable_paid_fallbacks
            agent_timeout_s = max(
                8,
                int(os.getenv("JUDGE_AGENT_TIMEOUT_SECONDS", "120") or "120"),
            )
            if judge_llm_mode == "fastest":
                agent_timeout_s = max(
                    6,
                    int(
                        os.getenv(
                            "JUDGE_AGENT_TIMEOUT_SECONDS_FASTEST",
                            str(judge_timeout_s),
                        )
                        or str(judge_timeout_s)
                    ),
                )

            agent = EconomicAnalyst(
                model_candidates=candidate_models,
                timeout=agent_timeout_s,
                retries_per_model=1,
                char_budget=JUDGE_CHAR_BUDGET,
                max_tokens=prof.max_tokens if prof else 1200,  # Use profile max_tokens
            )
            add_trace(
                "judge_runtime_config",
                llm_mode=judge_llm_mode,
                row_timeout_s=row_timeout_s,
                analyze_timeout_s=judge_timeout_s,
                g4f_timeout_s=judge_g4f_timeout_s,
                fastest_skip_agent=fastest_skip_agent,
                fastest_disable_paid_fallbacks=fastest_disable_paid_fallbacks,
                fastest_skip_json_repair=fastest_skip_json_repair,
                agent_timeout_s=agent_timeout_s,
            )

            sem = asyncio.Semaphore(3)  # allow limited parallelism

            async def _process_row(r):
                async with sem:
                    sym = normalize_ticker(r.get("ticker") or r.get("symbol") or "")
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
                    news_items = _news_for(sym)[:JUDGE_NEWS_ITEMS_PER_TICKER]
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
                    if fastest_skip_agent:
                        res = {
                            "ok": False,
                            "error": "agent_skipped_fastest",
                            "answer": "",
                        }
                    else:
                        agent_attempts = 1 if judge_llm_mode == "fastest" else 2
                        for attempt_idx in range(agent_attempts):
                            try:
                                res = await asyncio.wait_for(
                                    asyncio.to_thread(_run_agent), timeout=judge_timeout_s
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
                        and call_llm
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
                            res_g4f = call_llm(
                                messages=messages,
                                model=os.environ.get("G4F_MODEL"),
                                provider=os.environ.get("G4F_PROVIDER"),
                                mode=judge_llm_mode,
                                timeout=judge_g4f_timeout_s,
                                category_preference="forecast",
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
                        and allow_paid_fallbacks
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
                        and allow_paid_fallbacks
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
                        allow_paid_fallbacks
                        and not fastest_skip_json_repair
                        and call_groq
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
                            if (
                                allow_paid_fallbacks
                                and not fastest_skip_json_repair
                                and call_groq
                                and parsed.get("error")
                            ):
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
                        if p_bear >= 0.55:
                            return "critical"
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

                    def _parse_any_dt(ts_val: Any) -> Optional[datetime]:
                        if not ts_val:
                            return None
                        if isinstance(ts_val, datetime):
                            dt = ts_val
                        else:
                            ts_str = _normalize_ts_str(ts_val)
                            if not ts_str:
                                return None
                            try:
                                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                            except Exception:
                                return None
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        return dt.astimezone(timezone.utc)

                    now_utc = datetime.now(timezone.utc)
                    macro_age_days = None
                    news_age_hours = None
                    price_live_age_hours = None
                    price_history_age_days = None

                    try:
                        macro_ref = data_timestamps.get("macro")
                        if isinstance(macro_ref, str) and "T" not in macro_ref:
                            macro_ref = f"{macro_ref}T00:00:00Z"
                        macro_dt = _parse_any_dt(macro_ref)
                        if macro_dt:
                            macro_age_days = max(0.0, (now_utc - macro_dt).total_seconds() / 86400.0)
                    except Exception:
                        macro_age_days = None
                    try:
                        news_dt = _parse_any_dt(data_timestamps.get("news_last"))
                        if news_dt:
                            news_age_hours = max(0.0, (now_utc - news_dt).total_seconds() / 3600.0)
                    except Exception:
                        news_age_hours = None
                    try:
                        pl_dt = _parse_any_dt(data_timestamps.get("price_live"))
                        if pl_dt:
                            price_live_age_hours = max(0.0, (now_utc - pl_dt).total_seconds() / 3600.0)
                    except Exception:
                        price_live_age_hours = None
                    try:
                        ph_dt = _parse_any_dt(data_timestamps.get("price_history"))
                        if ph_dt:
                            price_history_age_days = max(0.0, (now_utc - ph_dt).total_seconds() / 86400.0)
                    except Exception:
                        price_history_age_days = None

                    def _score_age_hours(age: Optional[float], good: float, warn: float) -> float:
                        if age is None:
                            return 0.0
                        if age <= good:
                            return 1.0
                        if age <= warn:
                            return 0.65
                        return 0.25

                    def _score_age_days(age: Optional[float], good: float, warn: float) -> float:
                        if age is None:
                            return 0.0
                        if age <= good:
                            return 1.0
                        if age <= warn:
                            return 0.65
                        return 0.2

                    news_count = len(news_items)
                    news_coverage_score = min(1.0, news_count / float(max(1, JUDGE_NEWS_ITEMS_PER_TICKER)))
                    news_freshness_score = _score_age_hours(news_age_hours, good=24.0, warn=7 * 24.0)
                    macro_freshness_score = _score_age_days(macro_age_days, good=10.0, warn=45.0)

                    # We tolerate older price history as long as live price is recent.
                    price_live_score = _score_age_hours(price_live_age_hours, good=24.0, warn=96.0)
                    price_hist_score = _score_age_days(price_history_age_days, good=14.0, warn=45.0)
                    price_freshness_score = max(price_live_score, price_hist_score)

                    tech_fields = feat.get("tech", {}) if isinstance(feat.get("tech"), dict) else {}
                    fund_fields = (
                        feat.get("fundamentals_enriched")
                        if isinstance(feat.get("fundamentals_enriched"), dict)
                        else feat.get("fundamentals", {})
                    )
                    tech_ok = sum(
                        1 for k in ("rsi", "sma20", "sma50", "last") if tech_fields.get(k) is not None
                    )
                    fund_ok = sum(
                        1
                        for k in ("marketCap", "pe", "sector", "beta", "avgVolume")
                        if fund_fields.get(k) is not None
                    )
                    structure_score = min(1.0, ((tech_ok / 4.0) + (fund_ok / 5.0)) / 2.0)

                    data_quality_score = (
                        0.25 * news_coverage_score
                        + 0.15 * news_freshness_score
                        + 0.20 * macro_freshness_score
                        + 0.20 * price_freshness_score
                        + 0.20 * structure_score
                    )
                    data_quality_score = max(0.0, min(1.0, float(data_quality_score)))

                    # Confidence calibration from global backtest reliability + data quality.
                    bt_hit = backtest_ctx.get("hit_rate")
                    bt_n = int(backtest_ctx.get("n_trades") or 0)
                    bt_sample_w = max(0.0, min(1.0, bt_n / 120.0))
                    if bt_hit is not None:
                        empirical = (0.5 * (1.0 - bt_sample_w)) + (float(bt_hit) * bt_sample_w)
                    else:
                        empirical = 0.5
                    reliability_multiplier = 1.0 + (empirical - 0.5) * 0.6
                    sample_shrink = 0.8 + 0.2 * bt_sample_w
                    quality_penalty = 0.35 + (0.65 * data_quality_score)

                    conf_calibrated = conf_final * quality_penalty * reliability_multiplier * sample_shrink

                    # Hard safety gates for weak data.
                    if data_quality_score < 0.35:
                        conf_calibrated = min(conf_calibrated, 0.28)
                    if news_count == 0:
                        conf_calibrated = min(conf_calibrated, 0.22)
                    if macro_age_days is not None and macro_age_days > 120:
                        conf_calibrated = min(conf_calibrated, 0.25)
                    if price_live_age_hours is not None and price_live_age_hours > 96:
                        conf_calibrated = min(conf_calibrated, 0.25)

                    conf_final = max(0.05, min(0.95, float(conf_calibrated)))

                    # Enforce minimum risk when data quality is weak.
                    if data_quality_score < 0.2:
                        derived_risk = "high"
                    elif data_quality_score < 0.35 and derived_risk == "low":
                        derived_risk = "medium"

                    if isinstance(parsed, dict):
                        needed = parsed.setdefault("data_needed", [])
                        if not isinstance(needed, list):
                            needed = []
                            parsed["data_needed"] = needed
                        if news_count < max(5, JUDGE_NEWS_ITEMS_PER_TICKER // 2):
                            needed.append("insufficient_news_coverage")
                        if macro_age_days is not None and macro_age_days > 90:
                            needed.append("macro_snapshot_too_old")
                        if price_live_age_hours is not None and price_live_age_hours > 48:
                            needed.append("price_live_snapshot_too_old")

                        # Deduplicate while preserving order
                        seen = set()
                        dedup_needed: List[str] = []
                        for item in needed:
                            sitem = str(item).strip()
                            if not sitem:
                                continue
                            key = sitem.lower()
                            if key in seen:
                                continue
                            seen.add(key)
                            dedup_needed.append(sitem)
                        parsed["data_needed"] = dedup_needed[:10]
                        parsed["data_quality"] = {
                            "score": round(data_quality_score, 4),
                            "components": {
                                "news_coverage": round(news_coverage_score, 4),
                                "news_freshness": round(news_freshness_score, 4),
                                "macro_freshness": round(macro_freshness_score, 4),
                                "price_freshness": round(price_freshness_score, 4),
                                "structure": round(structure_score, 4),
                            },
                            "news_count": news_count,
                            "news_target": JUDGE_NEWS_ITEMS_PER_TICKER,
                        }
                        parsed["confidence_calibration"] = {
                            "base_confidence": round(float(base_conf), 4),
                            "parsed_confidence": round(float(parsed.get("confidence") or base_conf), 4),
                            "quality_penalty": round(float(quality_penalty), 4),
                            "reliability_multiplier": round(float(reliability_multiplier), 4),
                            "sample_shrink": round(float(sample_shrink), 4),
                            "backtest_hit_rate": bt_hit,
                            "backtest_n_trades": bt_n,
                            "final_confidence": round(float(conf_final), 4),
                        }

                    go_no_go = _judge_go_no_go(
                        llm_ok=isinstance(res, dict) and res.get("ok") is True,
                        parsed_error=bool(
                            isinstance(parsed, dict)
                            and parsed.get("error")
                        ),
                        confidence=conf_final,
                        data_quality_score=data_quality_score,
                        news_count=news_count,
                        data_needed=parsed.get("data_needed") if isinstance(parsed, dict) else None,
                    )

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
                        "go_no_go": go_no_go,
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
                            "data_quality_score": round(data_quality_score, 4),
                            "backtest_calibration": {
                                "hit_rate": bt_hit,
                                "n_trades": bt_n,
                                "sample_weight": round(bt_sample_w, 4),
                            },
                            "provider": (
                                res.get("provider_raw") or res.get("provider")
                                if isinstance(res, dict)
                                else None
                            ),
                        },
                        **(
                            {
                                "debug_payload": payload
                                if debug_full_enabled
                                else _sanitize_debug_payload(payload),
                                "debug_llm_res": res
                                if debug_full_enabled
                                else _sanitize_debug_llm_res(res),
                            }
                            if debug
                            else {}
                        ),
                    }

            async def _run_row_with_timeout(row_item: Dict[str, Any]):
                sym = normalize_ticker(
                    row_item.get("ticker") or row_item.get("symbol") or ""
                )
                try:
                    return await asyncio.wait_for(
                        _process_row(row_item), timeout=row_timeout_s
                    )
                except asyncio.TimeoutError:
                    add_trace("row_timeout", ticker=sym, timeout_s=row_timeout_s)
                    expected_ret = row_item.get("pred_return", row_item.get("expected_return", 0.0))
                    try:
                        expected_ret = float(expected_ret or 0.0)
                    except Exception:
                        expected_ret = 0.0
                    try:
                        fallback_conf = float(row_item.get("confidence") or 0.3)
                    except Exception:
                        fallback_conf = 0.3
                    fallback_conf = max(0.0, min(1.0, fallback_conf))
                    return {
                        "ticker": sym or "UNKNOWN",
                        "verdict": "hold",
                        "confidence": fallback_conf,
                        "expected_return": expected_ret,
                        "risk_level": "high",
                        "reasoning": "processing timeout fallback",
                        "analysis": {
                            "summary": ["processing timeout fallback"],
                            "error": "row_timeout",
                        },
                        "generated_at": datetime.utcnow().isoformat() + "Z",
                        "model_version": "judge_timeout_fallback",
                        "source": ["judge_route", "row_timeout_fallback"],
                    }
                except Exception as exc:
                    add_trace(
                        "row_exception",
                        ticker=sym,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                    return None

            tasks = [
                asyncio.create_task(_run_row_with_timeout(r))
                for r in top_rows
            ]
            generated_list = await asyncio.gather(*tasks)
            verdicts = [g for g in generated_list if g]
            row_timeout_count = sum(
                1
                for verdict in verdicts
                if isinstance(verdict.get("analysis"), dict)
                and verdict["analysis"].get("error") == "row_timeout"
            )
            llm_error_count = sum(
                1
                for verdict in verdicts
                if isinstance(verdict.get("analysis"), dict)
                and verdict["analysis"].get("error")
                and verdict["analysis"].get("error") != "row_timeout"
            )

            # Filtering and stats
            if ticker:
                ticker_list = normalize_tickers(ticker)
                verdicts = [
                    v
                    for v in verdicts
                    if normalize_ticker(v.get("ticker", "")) in ticker_list
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
            include_raw_llm = bool(debug and debug_full_enabled)
            public_limited_verdicts = [
                _sanitize_verdict_for_public(
                    v,
                    keep_raw=include_raw_llm,
                    keep_debug_fields=bool(debug),
                )
                for v in limited_verdicts
            ]

            decision_readiness = {
                "go_count": len(
                    [
                        v
                        for v in public_limited_verdicts
                        if isinstance(v.get("go_no_go"), dict)
                        and v["go_no_go"].get("decision") == "go"
                    ]
                ),
                "no_go_count": len(
                    [
                        v
                        for v in public_limited_verdicts
                        if not isinstance(v.get("go_no_go"), dict)
                        or v["go_no_go"].get("decision") != "go"
                    ]
                ),
                "min_confidence": 0.5,
                "min_quality": 0.4,
            }

            response_obj = {
                "verdicts": public_limited_verdicts,
                "count": len(public_limited_verdicts),
                "stats": {
                    "total_verdicts": total_verdicts,
                    "high_confidence_count": high_conf_count,
                    "avg_confidence": avg_confidence,
                    "generated_at": now_iso,
                },
                "decision_readiness": decision_readiness,
                "filters_applied": {
                    "min_confidence": min_confidence,
                    "tickers": ticker,
                    "sort_by": str(sort_by),
                    "sort_order": str(sort_order),
                    "limit": limit,
                },
                "generated_at": now_iso,
                "source": ["judge_route", "forecasts_llm"],
                "runtime": {
                    "llm_mode": judge_llm_mode,
                    "timeouts": {
                        "row_timeout_seconds": row_timeout_s,
                        "analyze_timeout_seconds": judge_timeout_s,
                        "g4f_timeout_seconds": judge_g4f_timeout_s,
                    },
                    "flags": {
                        "fastest_skip_econ_agent": fastest_skip_agent,
                        "fastest_disable_paid_fallbacks": fastest_disable_paid_fallbacks,
                        "fastest_skip_json_repair": fastest_skip_json_repair,
                    },
                    "rows": {
                        "selected": len(top_rows),
                        "processed": len(verdicts),
                        "row_timeout_count": row_timeout_count,
                        "llm_error_count": llm_error_count,
                    },
                },
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

            if typed_verdicts:
                for tv in typed_verdicts:
                    if isinstance(tv, dict):
                        if not include_raw_llm:
                            tv.pop("raw_answer", None)
                        if not debug:
                            tv.pop("debug_payload", None)
                            tv.pop("debug_llm_res", None)

            # On ne garde qu'une seule clé pour la liste finale : verdicts typés si dispo.
            if typed_verdicts:
                response_obj["verdicts"] = typed_verdicts

            if debug:
                response_obj["debug_pipeline"] = traces
                if debug_full_enabled:
                    response_obj["verdicts_raw"] = limited_verdicts
                else:
                    response_obj["verdicts_raw"] = [
                        _sanitize_verdict_for_public(
                            row,
                            keep_raw=False,
                            keep_debug_fields=False,
                        )
                        for row in limited_verdicts
                    ]
            response_obj.pop("verdicts_typed", None)
            return response_obj

        # Ici on pourrait rebrancher load_or_compute si tu veux du cache :
        # verdicts_data = await load_or_compute("judge_verdicts", compute_judge_verdicts)
        cache_leader = False
        singleflight_waiter = False
        if cache_key:
            verdicts_data, cache_leader = await _compute_singleflight(
                cache_key, compute_judge_verdicts
            )
            singleflight_waiter = not cache_leader
        else:
            verdicts_data = await compute_judge_verdicts()

        if cache_key and cache_leader and isinstance(verdicts_data, dict):
            _JUDGE_RESPONSE_CACHE[cache_key] = {
                "ts": time.time(),
                "data": deepcopy(verdicts_data),
            }
            _prune_judge_cache()

        if cache_key and isinstance(verdicts_data, dict):
            cache_meta = verdicts_data.get("cache")
            if not isinstance(cache_meta, dict):
                cache_meta = {}
            cache_meta.update(
                {
                    "hit": False,
                    "age_seconds": 0.0,
                    "ttl_seconds": JUDGE_CACHE_TTL_SECONDS,
                    "singleflight_waiter": bool(singleflight_waiter),
                }
            )
            verdicts_data["cache"] = cache_meta

        if singleflight_waiter and isinstance(verdicts_data, dict):
            verdicts_data = deepcopy(verdicts_data)
            _append_source_tag(verdicts_data, "judge_singleflight_wait")
            cache_meta = verdicts_data.get("cache")
            if not isinstance(cache_meta, dict):
                cache_meta = {}
            cache_meta.update(
                {
                    "hit": False,
                    "singleflight_waiter": True,
                    "ttl_seconds": JUDGE_CACHE_TTL_SECONDS,
                    "age_seconds": 0.0,
                }
            )
            verdicts_data["cache"] = cache_meta

        return service_response_with_metadata(
            verdicts_data,
            default_source="judge_route",
            freshness=verdicts_data.get(
                "generated_at", datetime.utcnow().isoformat() + "Z"
            ),
        )
    except Exception as e:
        logger.error(f"Critical error in /judge endpoint: {str(e)}")
        now_iso = datetime.utcnow().isoformat() + "Z"
        return service_response_with_metadata(
            {
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
                    "sort_by": str(sort_by),
                    "sort_order": str(sort_order),
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
            default_source="judge_route",
            freshness=now_iso,
            status="degraded",
            error=str(e),
        )


# Backward compatibility export
judge_router = router


async def _legacy_get_judge_quality(
    horizon_days: int = Query(
        5, ge=1, le=30, description="Forecast horizon used for realized-return evaluation"
    ),
    min_samples: int = Query(
        20, ge=1, le=500, description="Minimum samples to consider quality assessment reliable"
    ),
):
    """Rolling quality metrics for judge/forecast predictive performance."""
    from services.judge_endpoint_service import get_judge_quality_payload

    return await get_judge_quality_payload(
        horizon_days=horizon_days,
        min_samples=min_samples,
    )


async def _legacy_get_judge_quality_history(
    horizon_days: int = Query(
        5, ge=1, le=30, description="Forecast horizon used for quality snapshots"
    ),
    min_samples: int = Query(
        20, ge=1, le=500, description="Minimum samples used in the quality run"
    ),
    limit: int = Query(90, ge=1, le=1000, description="Maximum number of points returned"),
):
    """Historical snapshots of judge quality metrics for one (horizon, min_samples) scope."""
    from services.judge_endpoint_service import get_judge_quality_history_payload

    return await get_judge_quality_history_payload(
        horizon_days=horizon_days,
        min_samples=min_samples,
        limit=limit,
    )


async def _legacy_get_judge_options():
    """Options for judge UI (never-empty)."""
    from services.judge_endpoint_service import get_judge_options_payload

    return await get_judge_options_payload(risk_levels_fn=_judge_risk_levels)


class JudgeDecisionOutcomeFeedbackRequest(BaseModel):
    decision_id: str = Field(..., description="Judge decision id used in decision journal.")
    horizon: str = Field(..., description="Feedback horizon: 1d, 1w, or 1m.")
    status: Optional[str] = Field(
        default=None,
        description=(
            "Outcome status: pending, in_progress, or resolved. "
            "Defaults to resolved when an outcome or actual_return is provided, otherwise in_progress."
        ),
    )
    outcome: Optional[str] = Field(default=None, description="Outcome label.")
    actual_return: Optional[float] = Field(default=None, description="Observed return.")
    notes: Optional[str] = Field(default=None, description="Optional outcome notes.")
    recorded_at: Optional[str] = Field(default=None, description="Optional UTC ISO timestamp.")


@router.get(
    "",
    response_model=JudgeResponse if JudgeResponse is not None else None,
    response_model_exclude_none=True,
)
async def get_judge_verdicts(
    limit: int = Query(20, ge=1, le=100, description="Limite de résultats (1-100)"),
    min_confidence: float = Query(
        0.3, ge=0.0, le=1.0, description="Confiance minimum pour inclusion (0.0-1.0)"
    ),
    ticker: Optional[List[str]] = Query(
        None, description="Filtre par ticker (plusieurs autorisés)"
    ),
    sort_by: JudgeSortBy = Query(
        "confidence",
        description="Tri par: confidence, expected_return, score, risk_level, timestamp",
    ),
    sort_order: JudgeSortOrder = Query("desc", description="Ordre de tri: asc, desc"),
    profile: str = Query(
        "equity_1w", description="Judge profile: equity_1w, sector_regime, etc"
    ),
    debug: bool = Query(
        False, description="Active les traces et le payload LLM dans la réponse"
    ),
    debug_full: bool = Query(
        False,
        description="Inclut le payload debug complet (reserve admin; necessite JUDGE_ALLOW_DEBUG_FULL=1).",
    ),
    x_debug_token: Optional[str] = Header(
        default=None,
        alias="X-Debug-Token",
        description="Token admin requis pour debug_full si JUDGE_DEBUG_ADMIN_TOKEN est configure.",
    ),
):
    """Judge endpoint orchestrator (business logic delegated to service)."""
    from services.judge_endpoint_service import get_judge_verdicts_payload

    return await get_judge_verdicts_payload(
        limit=limit,
        min_confidence=min_confidence,
        ticker=ticker,
        sort_by=sort_by,
        sort_order=sort_order,
        profile=profile,
        debug=debug,
        debug_full=debug_full,
        x_debug_token=x_debug_token,
        compute_verdicts_fn=_legacy_get_judge_verdicts,
    )


@router.get(
    "/strategy-playbooks",
)
async def get_judge_strategy_playbooks(
    limit: int = Query(20, ge=1, le=100, description="Max playbooks returned (1-100)"),
    min_confidence: float = Query(
        0.3, ge=0.0, le=1.0, description="Confidence minimum for inclusion (0.0-1.0)"
    ),
    ticker: Optional[List[str]] = Query(
        None, description="Filter by ticker before playbook synthesis"
    ),
    sort_by: JudgeSortBy = Query(
        "confidence",
        description="Sort by: confidence, expected_return, score, risk_level, timestamp",
    ),
    sort_order: JudgeSortOrder = Query("desc", description="Sort order: asc, desc"),
    profile: str = Query("equity_1w", description="Judge profile used for underlying verdicts"),
    debug: bool = Query(False, description="Expose debug pipeline in source payload"),
    debug_full: bool = Query(
        False,
        description="Include full debug payloads (admin-gated in upstream verdict path).",
    ),
    x_debug_token: Optional[str] = Header(
        default=None,
        alias="X-Debug-Token",
        description="Token admin requis pour debug_full si JUDGE_DEBUG_ADMIN_TOKEN est configure.",
    ),
):
    """Build strategy playbooks from Judge verdicts using the existing LLM+cache stack."""
    from services.judge_endpoint_service import get_judge_verdicts_payload

    verdict_payload = await get_judge_verdicts_payload(
        limit=limit,
        min_confidence=min_confidence,
        ticker=ticker,
        sort_by=sort_by,
        sort_order=sort_order,
        profile=profile,
        debug=debug,
        debug_full=debug_full,
        x_debug_token=x_debug_token,
        compute_verdicts_fn=_legacy_get_judge_verdicts,
    )

    if not isinstance(verdict_payload, dict):
        return verdict_payload

    data = verdict_payload.get("data") if isinstance(verdict_payload, dict) else {}
    if not isinstance(data, dict):
        data = {}

    verdicts = data.get("verdicts") if isinstance(data, dict) else []
    if not isinstance(verdicts, list):
        verdicts = []

    playbooks = []
    for verdict in verdicts:
        if not isinstance(verdict, dict):
            continue
        playbooks.append(
            _build_strategy_playbook(verdict, profile=profile),
        )

    response_base = deepcopy(data)
    response_base.pop("verdicts", None)
    now_iso = datetime.utcnow().isoformat() + "Z"
    response_data = {
        **response_base,
        "playbooks": playbooks,
        "count": len(playbooks),
        "generated_at": response_base.get("generated_at") or now_iso,
        "source": response_base.get("source") or ["judge_strategy_playbook_route"],
        "filters_applied": {
            "min_confidence": min_confidence,
            "tickers": ticker,
            "sort_by": str(sort_by),
            "sort_order": str(sort_order),
            "limit": limit,
            "profile": profile,
        },
        "stats": {
            "go_count": len([p for p in playbooks if p.get("decision") == "go"]),
            "no_go_count": len([p for p in playbooks if p.get("decision") == "no_go"]),
            "avg_confidence": (
                sum(p.get("confidence", 0.0) for p in playbooks) / len(playbooks)
                if playbooks
                else 0.0
            ),
        },
    }

    if debug:
        response_data["judge_source"] = {
            "data_count": len(verdicts),
            "source": data.get("source"),
            "status": verdict_payload.get("status"),
            "error": verdict_payload.get("error"),
        }
        if isinstance(data.get("debug_pipeline"), list):
            response_data["debug_pipeline"] = data.get("debug_pipeline")
        if isinstance(data.get("verdicts_raw"), list):
            response_data["verdicts_raw"] = data.get("verdicts_raw")
    response_data.setdefault("source", ["judge_strategy_playbook_route"])
    _append_source_tag(response_data, "judge_strategy_playbook_route")

    return service_response_with_metadata(
        response_data,
        default_source="judge_strategy_playbook_route",
        freshness=verdict_payload.get("freshness")
        or data.get("generated_at")
        or now_iso,
        status=verdict_payload.get("status"),
        error=verdict_payload.get("error"),
    )


@router.get("/quality")
async def get_judge_quality(
    horizon_days: int = Query(
        5, ge=1, le=30, description="Forecast horizon used for realized-return evaluation"
    ),
    min_samples: int = Query(
        20, ge=1, le=500, description="Minimum samples to consider quality assessment reliable"
    ),
):
    """Judge quality endpoint orchestrator."""
    from services.judge_endpoint_service import get_judge_quality_payload

    return await get_judge_quality_payload(
        horizon_days=horizon_days,
        min_samples=min_samples,
    )


@router.get("/quality/history")
async def get_judge_quality_history(
    horizon_days: int = Query(
        5, ge=1, le=30, description="Forecast horizon used for quality snapshots"
    ),
    min_samples: int = Query(
        20, ge=1, le=500, description="Minimum samples used in the quality run"
    ),
    limit: int = Query(90, ge=1, le=1000, description="Maximum number of points returned"),
):
    """Judge quality history endpoint orchestrator."""
    from services.judge_endpoint_service import get_judge_quality_history_payload

    return await get_judge_quality_history_payload(
        horizon_days=horizon_days,
        min_samples=min_samples,
        limit=limit,
    )


@router.get("/options")
async def get_judge_options():
    """Judge options endpoint orchestrator."""
    from services.judge_endpoint_service import get_judge_options_payload

    return await get_judge_options_payload(risk_levels_fn=_judge_risk_levels)


@router.get("/decision-journal")
async def get_judge_decision_journal(
    decision_id: Optional[str] = Query(default=None, description="Filter by decision id"),
    profile: Optional[str] = Query(
        default=None,
        description="Filter by profile (default, balanced, sector_regime, ...)",
    ),
    status: Optional[str] = Query(
        default=None,
        description="Filter by latest outcome status (pending/in_progress/resolved)",
    ),
    limit: int = Query(default=200, ge=1, le=5000, description="Max records returned"),
):
    """Decision journal endpoint orchestrator."""
    from services.judge_endpoint_service import get_judge_decision_journal_payload

    return await get_judge_decision_journal_payload(
        decision_id=decision_id,
        profile=profile,
        status_filter=status,
        limit=limit,
    )


@router.post("/decision-journal/outcomes")
async def post_judge_decision_outcome_feedback(
    payload: JudgeDecisionOutcomeFeedbackRequest,
):
    """Record one judge decision outcome event (append-only feedback log)."""
    from services.judge_endpoint_service import append_judge_decision_outcome_feedback

    return await append_judge_decision_outcome_feedback(
        feedback=payload.model_dump()
    )


@router.get("/decision-journal/outcomes")
async def get_judge_decision_outcome_feedback(
    decision_id: Optional[str] = Query(default=None, description="Filter by decision id"),
    horizon: Optional[str] = Query(default=None, description="Filter by horizon"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    limit: int = Query(default=200, ge=1, le=5000, description="Max records returned"),
):
    """Get stored judge decision outcome feedback records."""
    from services.judge_endpoint_service import get_judge_decision_outcome_feedback

    return await get_judge_decision_outcome_feedback(
        decision_id=decision_id,
        horizon=horizon,
        status_filter=status,
        limit=limit,
    )
