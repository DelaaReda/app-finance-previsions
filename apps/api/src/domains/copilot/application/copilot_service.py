"""Reusable business logic for Copilot endpoints."""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import re
from datetime import datetime, timezone
from importlib import import_module
from typing import Any, Callable, Dict, List, Optional

try:
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover
    class BaseModel:  # type: ignore
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        def model_dump(self, **_kwargs):
            return dict(self.__dict__)

        def dict(self, **_kwargs):
            return dict(self.__dict__)

    def Field(default=None, **_kwargs):  # type: ignore
        return default

try:
    from storage import io as storage_io
except Exception:  # pragma: no cover
    storage_io = None  # type: ignore

try:
    from services.service_standard import coerce_confidence, ensure_decision_contract  # type: ignore
except Exception:  # pragma: no cover
    try:
        from platform.legacy.services.service_standard import (  # type: ignore
            coerce_confidence,
            ensure_decision_contract,
        )
    except Exception:  # pragma: no cover
        coerce_confidence = None  # type: ignore
        ensure_decision_contract = None  # type: ignore

# BATCH-84-DEV-03: Live market data for brief enhancement
try:
    from platform.legacy.core.market_data import get_price_history, get_fundamentals
except Exception:  # pragma: no cover
    get_price_history = None  # type: ignore
    get_fundamentals = None  # type: ignore

try:
    from packages.contracts.copilot_v1 import CopilotStartPayload as SharedCopilotStartPayload
except Exception:  # pragma: no cover
    SharedCopilotStartPayload = BaseModel  # type: ignore[misc,assignment]


def utc_now_iso() -> str:
    """Return canonical UTC ISO timestamp without service bridge dependencies."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_tickers(tickers: Optional[List[str]]) -> List[str]:
    return sorted(
        {
            str(item).strip().upper()
            for item in (tickers or [])
            if str(item).strip()
        }
    )


def _build_sources_from_chunks(context_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sources: List[Dict[str, Any]] = []
    for chunk in context_chunks:
        meta = chunk.get("meta") if isinstance(chunk.get("meta"), dict) else {}
        text = str(chunk.get("text") or "")
        sources.append(
            {
                "type": meta.get("type", "context"),
                "url": meta.get("url", ""),
                "date": meta.get("date", ""),
                "ticker": meta.get("ticker", ""),
                "excerpt": text[:200] + "..." if len(text) > 200 else text,
                "id": chunk.get("id", ""),
            }
        )
    return sources


def _safe_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _coerce_verdict(raw_verdict: Optional[str]) -> str:
    text = _safe_text(raw_verdict).lower()
    if any(token in text for token in ["buy", "achat", "long", "accumuler", "acheter"]):
        return "buy"
    if any(token in text for token in ["sell", "vendre", "short", "alléger", "sortir"]):
        return "sell"
    if any(token in text for token in ["hold", "maintenir", "conserver", "wait"]):
        return "hold"
    return "hold"


def _normalize_risk_level(raw_level: Any, fallback: str = "medium") -> str:
    value = _safe_text(raw_level).lower()
    if value in {"low", "medium", "high", "critical"}:
        return value
    if value in {"faible", "bas"}:
        return "low"
    if value in {"modere", "modéré", "moyen"}:
        return "medium"
    if value in {"eleve", "élevé"}:
        return "high"
    return fallback


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _normalize_confidence_value(value: Any, default: float) -> float:
    if callable(coerce_confidence):
        return float(coerce_confidence(value, default=default))

    confidence = _to_float(value, default)
    if confidence > 1.0:
        confidence = confidence / 100.0 if confidence <= 100.0 else 1.0
    return min(1.0, max(0.0, float(confidence)))


def _resolve_payload_confidence(
    *,
    parsed_payload: Optional[Dict[str, Any]],
    llm_response: Dict[str, Any],
    has_min_sources: bool,
    has_quality_model: bool,
) -> float:
    default_confidence = 0.8 if (has_min_sources and has_quality_model) else 0.4
    payload = parsed_payload if isinstance(parsed_payload, dict) else {}

    raw_confidence = None
    for key in ("confidence", "confidence_score", "confidence_pct", "probability"):
        if payload.get(key) is not None:
            raw_confidence = payload.get(key)
            break

    if raw_confidence is None:
        raw_confidence = llm_response.get("confidence")

    resolved_confidence = _normalize_confidence_value(raw_confidence, default_confidence)
    if not has_min_sources or not has_quality_model:
        return min(resolved_confidence, 0.45)
    return resolved_confidence


def _model_dump_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(exclude_none=True)
        if isinstance(dumped, dict):
            return dumped
    return {}


def _collect_fallback_context(scope: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Build local context fallback payload from snapshot files when market service fails."""
    normalized_tickers = _normalize_tickers(scope.get("tickers") if isinstance(scope, dict) else [])
    generated_at = utc_now_iso()
    payload = {
        "regime": "fallback",
        "confidence": 0.35,
        "key_drivers": [],
        "characteristics": {
            "volatility": "inconnu",
            "sentiment": "neutral",
            "trend": "inconnu",
            "momentum": "inconnu",
            "risk_level": "inconnu",
        },
        "recommended_layout": {"primary_widgets": ["CopilotFallbackWidget"]},
        "metadata": {
            "generated_at": generated_at,
            "sources": ["forecasts_snapshot", "news_snapshot", "copilot_service_fallback"],
        },
        "forecast_signals": [],
        "news_signals": [],
    }

    try:
        from storage.io import load_json
    except Exception:
        payload["key_drivers"].append("Aucune source snapshot locale disponible")
        return payload

    forecast_rows = []
    forecasts_payload = load_json("forecasts") or {}
    if isinstance(forecasts_payload, dict):
        forecast_rows.extend(forecasts_payload.get("rows", []) or [])
        forecast_rows.extend((forecasts_payload.get("data") or {}).get("rows", []) or [])

    for row in forecast_rows[:20]:
        if not isinstance(row, dict):
            continue
        row_ticker = str(row.get("ticker") or row.get("symbol") or "").upper().strip()
        if normalized_tickers and row_ticker and row_ticker not in normalized_tickers:
            continue
        confidence = _to_float(row.get("confidence"), 0.0)
        forecast_signals = {
            "ticker": row_ticker or "UNKNOWN",
            "forecast": row.get("forecast"),
            "forecast_30d": row.get("forecast_next_30d_pct") if row.get("forecast_next_30d_pct") is not None else row.get("forecast_next30d"),
            "confidence": confidence,
            "source": row.get("source", "forecast_snapshot"),
            "direction": row.get("direction"),
        }
        payload["forecast_signals"].append(forecast_signals)
        if confidence > payload["confidence"]:
            payload["confidence"] = confidence

    news_rows = []
    news_payload = load_json("news_feed") or {}
    if isinstance(news_payload, dict):
        news_rows.extend(news_payload.get("articles", []) or [])
        news_rows.extend((news_payload.get("data") or {}).get("articles", []) or [])

    for article in news_rows:
        if not isinstance(article, dict):
            continue
        article_tickers = _normalize_tickers(article.get("tickers") or [])
        if normalized_tickers and not set(normalized_tickers).intersection(article_tickers):
            continue
        headline = _safe_text(article.get("headline") or article.get("title"), "")
        if not headline:
            continue
        payload["news_signals"].append({
            "headline": headline[:160],
            "ticker": article_tickers[0] if article_tickers else "MARKET",
            "sentiment": _safe_text(article.get("sentiment"), "neutral"),
            "impact": _safe_text(article.get("impact"), "unknown"),
            "impact_score": _to_float(article.get("impact_score"), 0.0),
            "source": _safe_text(article.get("source"), "news_snapshot"),
        })
        if len(payload["news_signals"]) >= 8:
            break

    if payload["forecast_signals"]:
        payload["key_drivers"].append("Forecasts snapshot chargées localement")
    if payload["news_signals"]:
        payload["key_drivers"].append("News snapshot chargées localement")
    if not payload["key_drivers"]:
        payload["key_drivers"].append("Contexte marché partiel, données locales indisponibles")

    if normalized_tickers:
        payload["scope_tickers"] = normalized_tickers

    payload["confidence"] = min(1.0, max(0.0, float(payload["confidence"])))
    return payload


def _trim_words(text: Any, *, limit: int = 200) -> str:
    words = _safe_text(text).split()
    if not words:
        return ""
    return " ".join(words[:limit])


def _normalize_source_list(value: Any, fallback: str) -> List[str]:
    if isinstance(value, list):
        items = [_safe_text(item) for item in value if _safe_text(item)]
        if items:
            return items
    item = _safe_text(value)
    if item:
        return [item]
    return [fallback]


def _normalize_string_list(value: Any) -> List[str]:
    if isinstance(value, list):
        items: List[str] = []
        for item in value:
            token = _safe_text(item)
            if token:
                items.append(token)
        return items

    token = _safe_text(value)
    return [token] if token else []


def _brief_topic_label(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("ticker", "label", "name", "title", "sector", "theme", "value"):
            token = _safe_text(value.get(key))
            if token:
                return token
        return ""
    return _safe_text(value)


def _build_starter_question(
    scope: Optional[Dict[str, Any]] = None,
    daily_brief: Optional[Dict[str, Any]] = None,
) -> str:
    scope_tickers = _normalize_tickers(scope.get("tickers") if isinstance(scope, dict) else [])
    if scope_tickers:
        return f"Que dois-je surveiller aujourd'hui sur {', '.join(scope_tickers[:3])} ?"

    brief = daily_brief if isinstance(daily_brief, dict) else {}
    for key in ("top_risks", "top_signals", "top_opportunities"):
        for item in brief.get(key) or []:
            topic = _brief_topic_label(item)
            if topic:
                return f"Quel est l'impact de {topic} sur ma journée de trading ?"

    return "Que dois-je surveiller aujourd'hui ?"


def _normalize_brief_event_timing(brief: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    event_timing = brief.get("event_timing") if isinstance(brief.get("event_timing"), dict) else {}
    raw_events = event_timing.get("events") if isinstance(event_timing.get("events"), list) else []
    if not raw_events:
        raw_events = brief.get("key_events") if isinstance(brief.get("key_events"), list) else []

    events: List[Dict[str, Any]] = []
    for index, item in enumerate(raw_events):
        row = item if isinstance(item, dict) else {"label": item}
        label = _safe_text(
            row.get("event_type")
            or row.get("label")
            or row.get("title")
            or row.get("name")
            or row.get("event")
            or row.get("ticker")
            or row.get("stock"),
        )
        if not label:
            continue
        normalized_row = {
            "event_type": label,
            "dominant_horizon": _safe_text(
                row.get("dominant_horizon") or row.get("window") or row.get("horizon"),
                "24h" if index == 0 else "48h",
            ),
            "interpretation": _safe_text(
                row.get("interpretation") or row.get("summary") or row.get("thesis"),
                f"{label} is inside the near-term event window.",
            ),
        }
        if row.get("impact_score") is not None:
            normalized_row["impact_score"] = _to_float(row.get("impact_score"), 0.0)
        events.append(normalized_row)
        if len(events) >= 2:
            break

    if not events:
        return None

    summary = _safe_text(event_timing.get("summary"))
    if not summary:
        summary = "Critical events are clustered into the next 48h."
    sources = _normalize_source_list(
        event_timing.get("source") or event_timing.get("sources") or brief.get("source") or brief.get("sources"),
        "brief_daily_snapshot",
    )
    freshness = _safe_text(
        event_timing.get("freshness") or brief.get("freshness") or brief.get("generated_at"),
        utc_now_iso(),
    )
    return {
        "summary": summary,
        "events": events,
        "freshness": freshness,
        "source": sources,
        "sources": sources,
    }


def _normalize_memo_horizon(payload: Dict[str, Any]) -> str:
    memo_payload = payload.get("memo") if isinstance(payload.get("memo"), dict) else {}
    return _safe_text(
        memo_payload.get("horizon") or payload.get("horizon") or payload.get("time_horizon"),
        "1w",
    )


def _normalize_memo_why(payload: Dict[str, Any]) -> List[str]:
    memo_payload = payload.get("memo") if isinstance(payload.get("memo"), dict) else {}

    for candidate in (
        memo_payload.get("why"),
        payload.get("why"),
        payload.get("reasoning"),
    ):
        items = _normalize_string_list(candidate)
        if items:
            return items

    answer = _safe_text(memo_payload.get("answer") or payload.get("answer"))
    return [answer] if answer else []


def _has_explicit_insufficient_evidence(items: List[str]) -> bool:
    haystack = " ".join(str(item).lower() for item in items)
    return any(
        token in haystack
        for token in (
            "insufficient",
            "insuffisant",
            "insuffisante",
            "insuffisantes",
            "moins de 2",
            "fewer than 2",
        )
    )


def _normalize_memo_risks(
    payload: Dict[str, Any],
    *,
    insufficient_evidence: bool = False,
) -> List[str]:
    memo_payload = payload.get("memo") if isinstance(payload.get("memo"), dict) else {}

    for candidate in (
        memo_payload.get("risks"),
        payload.get("risks"),
    ):
        items = _normalize_string_list(candidate)
        if items:
            risks = items
            break
    else:
        risks = []

    if not risks:
        risk_payload = memo_payload.get("risk") if isinstance(memo_payload.get("risk"), dict) else {}
        if not risk_payload and isinstance(payload.get("risk"), dict):
            risk_payload = dict(payload.get("risk") or {})

        if risk_payload:
            level = _safe_text(risk_payload.get("level") or payload.get("risk_level"))
            caveat = _safe_text(risk_payload.get("caveat") or payload.get("risk_caveat"))
            if level:
                risks.append(level)
            if caveat:
                risks.append(caveat)
        else:
            risks = _normalize_string_list(payload.get("risk"))

    if not risks:
        risks = _normalize_string_list(payload.get("risk_caveat"))

    event_timing = payload.get("event_timing") if isinstance(payload.get("event_timing"), dict) else {}
    event_timing_summary = _safe_text(event_timing.get("summary"))
    if event_timing_summary:
        existing = {str(item).strip().lower() for item in risks if str(item).strip()}
        if event_timing_summary.lower() not in existing:
            risks.append(event_timing_summary)

    if insufficient_evidence and not _has_explicit_insufficient_evidence(risks):
        risks = ["Sources insuffisantes (moins de 2).", *risks] if risks else [
            "Sources insuffisantes (moins de 2)."
        ]

    return risks


def _normalize_memo_sources(payload: Dict[str, Any]) -> List[Any]:
    memo_payload = payload.get("memo") if isinstance(payload.get("memo"), dict) else {}

    for candidate in (
        memo_payload.get("sources"),
        payload.get("sources"),
    ):
        if isinstance(candidate, list) and candidate:
            return list(candidate)

    for candidate in (
        memo_payload.get("source"),
        payload.get("source"),
    ):
        if isinstance(candidate, list) and candidate:
            return list(candidate)

        token = _safe_text(candidate)
        if token:
            return [token]

    return []


def _is_insufficient_evidence(payload: Dict[str, Any], *, sources: List[Any]) -> bool:
    quality_status = _safe_text(payload.get("quality_status")).lower()
    if quality_status == "insufficient_sources":
        return True
    if quality_status == "error":
        return False

    requirements = payload.get("requirements_met") if isinstance(payload.get("requirements_met"), dict) else {}
    if requirements.get("min_sources_2") is False:
        return True

    try:
        if payload.get("sources_count") is not None:
            return int(payload.get("sources_count")) < 2
    except Exception:
        pass

    return len(sources) < 2


def normalize_ask_payload_contract(payload: Any) -> Dict[str, Any]:
    normalized = dict(payload) if isinstance(payload, dict) else {}
    memo_payload = normalized.get("memo") if isinstance(normalized.get("memo"), dict) else {}

    freshness = _safe_text(
        memo_payload.get("freshness") or normalized.get("freshness") or normalized.get("generated_at"),
        "",
    )
    if not freshness:
        freshness = utc_now_iso()
    normalized.setdefault("generated_at", freshness)
    normalized["freshness"] = freshness

    sources = _normalize_memo_sources(normalized)
    insufficient_evidence = _is_insufficient_evidence(normalized, sources=sources)
    why = _normalize_memo_why(normalized)
    if not why and insufficient_evidence:
        why = ["Sources insuffisantes pour une recommandation fiable."]

    risks = _normalize_memo_risks(
        normalized,
        insufficient_evidence=insufficient_evidence,
    )
    verdict = _safe_text(
        memo_payload.get("verdict") or normalized.get("verdict") or normalized.get("action"),
        "hold",
    ).lower()
    horizon = _normalize_memo_horizon(normalized)
    confidence = memo_payload.get("confidence") if memo_payload.get("confidence") is not None else normalized.get("confidence")
    next_steps = _normalize_string_list(memo_payload.get("next_steps"))
    if not next_steps:
        next_steps = _normalize_string_list(normalized.get("next_steps"))
    invalidation = _normalize_string_list(memo_payload.get("invalidation"))
    if not invalidation:
        invalidation = _normalize_string_list(normalized.get("invalidation"))

    memo: Dict[str, Any] = {
        "verdict": verdict,
        "horizon": horizon,
        "why": why,
        "risks": risks,
        "confidence": confidence,
        "freshness": freshness,
        "sources": sources,
    }
    if next_steps:
        memo["next_steps"] = next_steps
    if invalidation:
        memo["invalidation"] = invalidation

    normalized["memo"] = memo
    normalized["verdict"] = _safe_text(normalized.get("verdict"), verdict).lower() or verdict
    normalized["action"] = _safe_text(normalized.get("action"), normalized["verdict"]).lower() or normalized["verdict"]
    normalized["horizon"] = horizon
    normalized["why"] = why
    normalized["risks"] = risks
    normalized["sources"] = sources
    normalized["confidence"] = confidence
    if next_steps:
        normalized["next_steps"] = next_steps
    if invalidation:
        normalized["invalidation"] = invalidation

    return normalized


def _extract_saved_portfolio_state(
    portfolio_payload: Dict[str, Any],
    risk_payload: Dict[str, Any],
) -> Dict[str, Any]:
    risk_portfolio = risk_payload.get("portfolio") if isinstance(risk_payload.get("portfolio"), dict) else {}
    state = risk_portfolio.get("state") if isinstance(risk_portfolio.get("state"), dict) else {}
    if state:
        return {
            field_name: state[field_name]
            for field_name in ("horizon", "conviction", "risk_tolerance")
            if state.get(field_name) is not None
        }

    metadata = portfolio_payload.get("metadata") if isinstance(portfolio_payload.get("metadata"), dict) else {}
    return {
        field_name: metadata[field_name]
        for field_name in ("horizon", "conviction", "risk_tolerance")
        if metadata.get(field_name) is not None
    }


def _resolve_saved_portfolio_context(scope: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    resolved_scope = dict(scope or {}) if isinstance(scope, dict) else {}
    requested_portfolio_id = _safe_text(
        resolved_scope.get("portfolio_id") or resolved_scope.get("portfolioId"),
        "",
    )

    portfolio_module = None
    for module_path in (
        "domains.market_data.application.portfolio_service",
        "services.portfolio_service",
    ):
        try:
            portfolio_module = import_module(module_path)
            break
        except Exception:
            continue
    if portfolio_module is None:
        return None

    get_portfolio_service = getattr(portfolio_module, "get_portfolio_service", None)
    if not callable(get_portfolio_service):
        return None

    try:
        service = get_portfolio_service()
    except Exception:
        return None

    try:
        portfolio = None
        if requested_portfolio_id and callable(getattr(service, "get_portfolio", None)):
            portfolio = service.get_portfolio(requested_portfolio_id)
        if portfolio is None and callable(getattr(service, "list_portfolios", None)):
            portfolios = service.list_portfolios() or []
            portfolio = portfolios[0] if portfolios else None
    except Exception:
        return None

    portfolio_payload = _model_dump_dict(portfolio)
    tickers = _normalize_tickers(portfolio_payload.get("tickers"))
    portfolio_id = _safe_text(portfolio_payload.get("id"), requested_portfolio_id)
    if not portfolio_id or not tickers:
        return None

    weights: Dict[str, float] = {}
    weight_warnings: List[str] = []
    resolve_portfolio_weights = getattr(portfolio_module, "_resolve_portfolio_weights", None)
    if callable(resolve_portfolio_weights):
        try:
            weights, _, weight_warnings = resolve_portfolio_weights(
                tickers,
                portfolio_payload.get("metadata"),
            )
        except Exception:
            weights = {}
            weight_warnings = []

    risk_payload: Dict[str, Any] = {}
    get_risk_profile = getattr(service, "get_risk_profile", None)
    should_load_live_risk = bool(
        requested_portfolio_id or resolved_scope.get("include_live_risk_profile")
    )
    if callable(get_risk_profile) and should_load_live_risk:
        try:
            risk_payload = _model_dump_dict(get_risk_profile(portfolio_id))
        except Exception:
            risk_payload = {}

    portfolio_context = {
        "portfolio": {
            "id": portfolio_id,
            "name": _safe_text(portfolio_payload.get("name"), "Saved portfolio"),
            "tickers": tickers,
            "tickers_count": len(tickers),
            "state": _extract_saved_portfolio_state(portfolio_payload, risk_payload),
        },
        "risk_profile": _safe_text(risk_payload.get("risk_profile"), ""),
        "risk_level": _safe_text(
            risk_payload.get("risk_level")
            or (risk_payload.get("risk") or {}).get("level"),
            "",
        ),
        "benchmark": _safe_text(risk_payload.get("benchmark"), ""),
        "why": risk_payload.get("why") if isinstance(risk_payload.get("why"), list) else [],
        "warnings": (
            (risk_payload.get("warnings") if isinstance(risk_payload.get("warnings"), list) else [])
            + weight_warnings
        ),
        "weights": (
            risk_payload.get("weights")
            if isinstance(risk_payload.get("weights"), dict) and risk_payload.get("weights")
            else weights
        ),
        "confidence": risk_payload.get("confidence"),
        "freshness": _safe_text(risk_payload.get("generated_at"), ""),
        "source": _normalize_source_list(
            risk_payload.get("source"),
            "copilot_saved_portfolio",
        ),
    }
    if "copilot_saved_portfolio" not in portfolio_context["source"]:
        portfolio_context["source"].append("copilot_saved_portfolio")
    return portfolio_context


def _resolve_scope_with_saved_portfolio(
    scope: Optional[Dict[str, Any]] = None,
    *,
    tickers: Optional[List[str]] = None,
) -> tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    resolved_scope = dict(scope or {}) if isinstance(scope, dict) else {}
    normalized_tickers = _normalize_tickers(
        tickers if tickers is not None else resolved_scope.get("tickers")
    )
    requested_portfolio_id = _safe_text(
        resolved_scope.get("portfolio_id") or resolved_scope.get("portfolioId"),
        "",
    )

    saved_portfolio_context = (
        _resolve_saved_portfolio_context(resolved_scope)
        if (requested_portfolio_id or not normalized_tickers)
        else None
    )

    effective_tickers = list(normalized_tickers)
    if not effective_tickers and saved_portfolio_context:
        effective_tickers = _normalize_tickers(
            (saved_portfolio_context.get("portfolio") or {}).get("tickers")
        )

    if effective_tickers:
        resolved_scope["tickers"] = effective_tickers
    else:
        resolved_scope.pop("tickers", None)

    return resolved_scope, saved_portfolio_context


def _build_context_influence(
    *,
    requested_scope: Optional[Dict[str, Any]] = None,
    requested_tickers: Optional[List[str]] = None,
    resolved_scope: Optional[Dict[str, Any]] = None,
    saved_portfolio_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    explicit_tickers = _normalize_tickers(
        requested_tickers
        if requested_tickers is not None
        else (requested_scope.get("tickers") if isinstance(requested_scope, dict) else [])
    )
    effective_tickers = _normalize_tickers(
        resolved_scope.get("tickers") if isinstance(resolved_scope, dict) else []
    )
    portfolio = (
        saved_portfolio_context.get("portfolio")
        if isinstance(saved_portfolio_context, dict) and isinstance(saved_portfolio_context.get("portfolio"), dict)
        else {}
    )

    source = "market_default"
    if explicit_tickers:
        source = "explicit_tickers"
    elif saved_portfolio_context:
        source = "saved_portfolio_default"

    influence: Dict[str, Any] = {
        "mode": "portfolio_aware" if saved_portfolio_context else "market_wide",
        "portfolio_applied": bool(saved_portfolio_context),
        "source": source,
        "requested_tickers": explicit_tickers,
        "effective_tickers": effective_tickers,
    }
    portfolio_id = _safe_text(portfolio.get("id"), "")
    if portfolio_id:
        influence["portfolio_id"] = portfolio_id
    portfolio_state = portfolio.get("state") if isinstance(portfolio.get("state"), dict) else {}
    if portfolio_state:
        influence["portfolio_state"] = {
            field_name: portfolio_state[field_name]
            for field_name in ("horizon", "conviction", "risk_tolerance")
            if portfolio_state.get(field_name) is not None
        }
    return influence


def _normalize_weight_percent_map(raw_weights: Any) -> Dict[str, float]:
    if not isinstance(raw_weights, dict):
        return {}

    normalized: Dict[str, float] = {}
    numeric_values: List[float] = []
    for raw_key, raw_value in raw_weights.items():
        key = _safe_text(raw_key).upper()
        if not key:
            continue
        try:
            value = float(raw_value)
        except Exception:
            continue
        if value < 0:
            continue
        normalized[key] = value
        numeric_values.append(value)

    if not normalized:
        return {}

    scale = 100.0 if sum(numeric_values) <= 1.5 else 1.0
    return {
        key: round(value * scale, 2)
        for key, value in normalized.items()
    }


def _extract_drift_threshold_pct(guardrails: Any) -> Optional[float]:
    if not isinstance(guardrails, list):
        return None

    for item in guardrails:
        text = _safe_text(item).lower()
        if "drift" not in text:
            continue
        match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
        if match:
            try:
                return float(match.group(1))
            except Exception:
                return None
    return None


def _extract_concentration_threshold_pct(guardrails: Any) -> Optional[float]:
    if not isinstance(guardrails, list):
        return None

    for item in guardrails:
        text = _safe_text(item).lower()
        if "concentration" not in text:
            continue
        match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
        if match:
            try:
                return float(match.group(1))
            except Exception:
                return None
    return None


def _build_regime_detection_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    confidence = float(payload.get("confidence") or 0.0)
    key_drivers = payload.get("key_drivers") if isinstance(payload.get("key_drivers"), list) else []
    return {
        "label": _safe_text(payload.get("regime"), "NORMAL"),
        "confidence": round(confidence, 2),
        "confidence_pct": round(confidence * 100.0, 1),
        "threshold_reason": _safe_text(key_drivers[0], "Balanced market conditions") if key_drivers else "Balanced market conditions",
        "source": _normalize_source_list(
            metadata.get("sources"),
            "copilot_context_regime_detection",
        ),
        "generated_at": _safe_text(metadata.get("generated_at"), utc_now_iso()),
    }


def _build_allocation_drift_alerts(
    *,
    playbook_context: Optional[Dict[str, Any]] = None,
    saved_portfolio_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    playbook_context = playbook_context if isinstance(playbook_context, dict) else {}
    saved_portfolio_context = saved_portfolio_context if isinstance(saved_portfolio_context, dict) else {}

    guardrails = playbook_context.get("guardrails") if isinstance(playbook_context.get("guardrails"), list) else []
    weights = _normalize_weight_percent_map(saved_portfolio_context.get("weights"))
    if not weights:
        return {
            "active": False,
            "alerts": [],
            "warning": "saved_portfolio_weights_unavailable",
        }

    alerts: List[Dict[str, Any]] = []
    concentration_threshold = _extract_concentration_threshold_pct(guardrails)
    if concentration_threshold is not None:
        symbol, weight_pct = max(weights.items(), key=lambda item: item[1])
        if weight_pct > concentration_threshold:
            alerts.append(
                {
                    "id": "largest_position_concentration",
                    "severity": "high" if weight_pct - concentration_threshold >= 5 else "medium",
                    "basis": "position_weight_proxy",
                    "symbol": symbol,
                    "current_weight_pct": round(weight_pct, 2),
                    "threshold_pct": round(concentration_threshold, 2),
                    "reason": (
                        f"{symbol} is {weight_pct:.2f}% of saved weights, above the "
                        f"{concentration_threshold:.2f}% playbook concentration proxy. "
                        "Sector exposure details were unavailable, so this alert uses "
                        "position weight as a guardrail proxy."
                    ),
                }
            )

    drift_threshold = _extract_drift_threshold_pct(guardrails)
    if drift_threshold is not None and len(weights) > 1:
        equal_weight_pct = round(100.0 / len(weights), 2)
        symbol, weight_pct = max(
            weights.items(),
            key=lambda item: abs(item[1] - equal_weight_pct),
        )
        drift_pct = round(abs(weight_pct - equal_weight_pct), 2)
        if drift_pct > drift_threshold:
            alerts.append(
                {
                    "id": "equal_weight_rebalance_watch",
                    "severity": "medium",
                    "symbol": symbol,
                    "current_weight_pct": round(weight_pct, 2),
                    "reference_weight_pct": equal_weight_pct,
                    "threshold_pct": round(drift_threshold, 2),
                    "reason": (
                        f"{symbol} deviates {drift_pct:.2f} pts from an equal-weight "
                        f"baseline, above the {drift_threshold:.2f}% rebalance guardrail."
                    ),
                }
            )

    return {
        "active": bool(alerts),
        "alerts": alerts,
        "weights_analyzed": weights,
        "guardrails": guardrails,
    }


def _format_saved_portfolio_prompt(portfolio_context: Optional[Dict[str, Any]]) -> str:
    if not isinstance(portfolio_context, dict):
        return ""

    portfolio = portfolio_context.get("portfolio") if isinstance(portfolio_context.get("portfolio"), dict) else {}
    tickers = _normalize_tickers(portfolio.get("tickers"))
    if not tickers:
        return ""

    state = portfolio.get("state") if isinstance(portfolio.get("state"), dict) else {}
    lines = [
        "=== Contexte portefeuille sauvegarde ===",
        f"Portefeuille: {_safe_text(portfolio.get('name'), 'Saved portfolio')}",
        f"Tickers suivis: {', '.join(tickers)}",
    ]
    if state:
        horizon = _safe_text(state.get("horizon"), "")
        conviction = _safe_text(state.get("conviction"), "")
        risk_tolerance = _safe_text(state.get("risk_tolerance"), "")
        if horizon:
            lines.append(f"Horizon: {horizon}")
        if conviction:
            lines.append(f"Conviction: {conviction}")
        if risk_tolerance:
            lines.append(f"Tolerance au risque: {risk_tolerance}")

    risk_profile = _safe_text(portfolio_context.get("risk_profile"), "")
    risk_level = _safe_text(portfolio_context.get("risk_level"), "")
    if risk_profile:
        lines.append(f"Profil de risque: {risk_profile}")
    if risk_level:
        lines.append(f"Niveau de risque: {risk_level}")

    why = portfolio_context.get("why") if isinstance(portfolio_context.get("why"), list) else []
    if why:
        lines.append("Signaux clefs: " + " | ".join(_safe_text(item) for item in why[:3] if _safe_text(item)))

    warnings = portfolio_context.get("warnings") if isinstance(portfolio_context.get("warnings"), list) else []
    if warnings:
        lines.append("Avertissements: " + " | ".join(_safe_text(item) for item in warnings[:2] if _safe_text(item)))

    return "\n".join(lines)


def _brief_signal_label(item: Any, fallback: str) -> str:
    if not isinstance(item, dict):
        return _safe_text(item, fallback)
    topic = _safe_text(item.get("name") or item.get("topic"), fallback)
    value = _safe_text(item.get("value") or item.get("state"), "n/a")
    signal = _safe_text(item.get("signal") or item.get("direction"), "")
    if signal:
        return f"{topic}={value} ({signal})"
    return f"{topic}={value}"


def _brief_list_values(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    values: List[str] = []
    for item in value:
        label = _safe_text(item.get("sector") if isinstance(item, dict) else item)
        if label:
            values.append(label)
    return values


def _build_copilot_llm_messages(question: str, context_chunks: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    context_text = "\n\n".join(
        [
            f"[{index + 1}] {chunk['text']}\n"
            f"Source: {chunk['meta'].get('url', 'N/A')} | Date: {chunk['meta'].get('date', 'N/A')}"
            for index, chunk in enumerate(context_chunks[:10])
        ]
    )
    system_prompt = (
        "Tu es un copilot financier personnel. Ton role: aider l'utilisateur "
        "a prendre des decisions d'investissement rapides et claires.\n\n"
        "Regles:\n"
        "- Reponds en 3-5 phrases maximum, orientees action\n"
        "- Commence toujours par: HOLD / BUY / SELL / REDUIRE / AUGMENTER selon le contexte\n"
        "- Cite tes sources avec [numero] quand pertinent\n"
        "- Si les donnees manquent, dis-le en 1 phrase et donne quand meme une direction probable\n"
        "- Pas de disclaimers juridiques, l'utilisateur sait que c'est une aide et non un conseil officiel\n"
        "- Utilise les chiffres disponibles (%, prix, tendances)"
    )
    user_prompt = (
        "Contexte (sources de données):\n"
        f"{context_text}\n\n"
        f"Question: {question}\n\n"
        "Réponse (avec citations [1], [2], etc.):"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _extract_llm_citations(answer: str, context_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cited_indices = {
        int(match.group(1)) - 1
        for match in re.finditer(r"\[(\d+)\]", answer or "")
    }
    citations: List[Dict[str, Any]] = []
    for index in cited_indices:
        if index < 0 or index >= len(context_chunks):
            continue
        chunk = context_chunks[index]
        meta = chunk.get("meta") if isinstance(chunk.get("meta"), dict) else {}
        citations.append(
            {
                "index": index + 1,
                "type": meta.get("type", "context"),
                "url": meta.get("url", ""),
                "date": meta.get("date", ""),
                "excerpt": (chunk.get("text") or "")[:200] + "...",
            }
        )
    return citations


def _default_ask_llm(
    *,
    question: str,
    context_chunks: List[Dict[str, Any]],
    max_tokens: int = 1000,
) -> Dict[str, Any]:
    messages = _build_copilot_llm_messages(question, context_chunks)
    primary_error = ""

    try:
        judge_g4f_client = import_module("domains.judge.application.g4f_client")
        llm_res = judge_g4f_client.call_llm(
            messages=messages,
            mode=os.getenv("LLM_RAG_MODE") or os.getenv("LLM_MODEL_MODE"),
            timeout=max(20, int(os.getenv("G4F_TIMEOUT_SECONDS", "60") or "60")),
            category_preference="forecast",
        )
        if isinstance(llm_res, dict) and llm_res.get("ok"):
            answer = str(llm_res.get("answer") or "").strip()
            return {
                "answer": answer,
                "citations": _extract_llm_citations(answer, context_chunks),
                "model": llm_res.get("model") or "judge_g4f_client",
                "tokens": 0,
            }
        primary_error = str((llm_res or {}).get("error") or "judge_stack_llm_failed")
    except Exception as exc:
        primary_error = str(exc)

    try:
        legacy_ask_llm = import_module("research.llm_client").ask_llm
        fallback = legacy_ask_llm(
            question=question,
            context_chunks=context_chunks,
            max_tokens=max_tokens,
        )
        if isinstance(fallback, dict):
            if primary_error and not fallback.get("error"):
                fallback["error"] = primary_error
            return fallback
    except Exception as fallback_exc:
        primary_error = f"{primary_error}; {fallback_exc}" if primary_error else str(fallback_exc)

    return {
        "answer": "",
        "citations": [],
        "model": "unconfigured",
        "tokens": 0,
        "error": primary_error or "copilot_llm_unavailable",
    }


async def _invoke_ask_llm_with_timeout(
    ask_llm_fn: Any,
    *,
    question: str,
    context_chunks: List[Dict[str, Any]],
    max_tokens: int,
) -> Dict[str, Any]:
    timeout_seconds = max(
        0.01,
        float(os.getenv("COPILOT_ASK_LLM_TIMEOUT_SECONDS", "8") or "8"),
    )
    kwargs = {
        "question": question,
        "context_chunks": context_chunks,
        "max_tokens": max_tokens,
    }

    try:
        if inspect.iscoroutinefunction(ask_llm_fn):
            return await asyncio.wait_for(ask_llm_fn(**kwargs), timeout=timeout_seconds)

        if inspect.isfunction(ask_llm_fn) or inspect.ismethod(ask_llm_fn) or callable(ask_llm_fn):
            return await asyncio.wait_for(
                asyncio.to_thread(ask_llm_fn, **kwargs),
                timeout=timeout_seconds,
            )

        result = ask_llm_fn(**kwargs)
        if inspect.isawaitable(result):
            return await asyncio.wait_for(result, timeout=timeout_seconds)
        return result
    except asyncio.TimeoutError as exc:
        raise TimeoutError(
            f"copilot ask llm timed out after {timeout_seconds:.2f}s"
        ) from exc


# ==================== BATCH-84-DEV-03: Live Market Data Enhancement ====================

def _fetch_live_market_indicators() -> Dict[str, Any]:
    """
    Fetch live market indicators for brief enhancement.
    
    Returns dict with:
    - vix: Current VIX level (fear gauge)
    - spy_change: S&P 500 daily change %
    - qqq_change: NASDAQ 100 daily change %
    - market_status: 'open'/'closed' based on timestamp
    - fetched_at: ISO timestamp
    
    BATCH-84-DEV-03: Enhances brief with live data instead of snapshot-only.
    """
    generated_at = utc_now_iso()
    fallback = {
        "vix": None,
        "spy_change": None,
        "qqq_change": None,
        "market_status": "unknown",
        "fetched_at": generated_at,
        "source": "live_market_data",
        "degraded": True,
        "degraded_reason": "Live data fetch failed - using cached brief only",
    }

    live_market_enabled = str(
        __import__("os").getenv("FC_COPILOT_LIVE_MARKET_DATA", "1")
    ).strip().lower() in {"1", "true", "yes", "on"}
    if not live_market_enabled:
        fallback["degraded_reason"] = "Live data disabled - using snapshot brief only"
        return fallback
    
    if get_price_history is None:
        return fallback
    
    try:
        # Fetch VIX (volatility index)
        vix_value = None
        try:
            vix_df = get_price_history("^VIX", interval="1d")
            if vix_df is not None and not vix_df.empty and "Close" in vix_df.columns:
                vix_value = float(vix_df["Close"].iloc[-1])
        except Exception:
            pass
        
        # Fetch SPY (S&P 500 ETF) daily change
        spy_change = None
        try:
            spy_df = get_price_history("SPY", interval="1d")
            if spy_df is not None and not spy_df.empty and "Close" in spy_df.columns:
                closes = spy_df["Close"].dropna()
                if len(closes) >= 2:
                    spy_change = ((closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2]) * 100
        except Exception:
            pass
        
        # Fetch QQQ (NASDAQ 100 ETF) daily change
        qqq_change = None
        try:
            qqq_df = get_price_history("QQQ", interval="1d")
            if qqq_df is not None and not qqq_df.empty and "Close" in qqq_df.columns:
                closes = qqq_df["Close"].dropna()
                if len(closes) >= 2:
                    qqq_change = ((closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2]) * 100
        except Exception:
            pass
        
        # Determine market status (simplified - assumes weekday 9:30-16:00 ET)
        market_status = "unknown"
        try:
            now = datetime.now(timezone.utc)
            # Rough NY timezone check (UTC-5 or UTC-4)
            et_hour = (now.hour - 5) % 24  # Approximate ET hour
            if now.weekday() < 5 and 9 <= et_hour < 16:
                market_status = "open"
            else:
                market_status = "closed"
        except Exception:
            pass
        
        # Build result - only include successfully fetched values
        result = {
            "vix": vix_value,
            "spy_change": round(spy_change, 2) if spy_change is not None else None,
            "qqq_change": round(qqq_change, 2) if qqq_change is not None else None,
            "market_status": market_status,
            "fetched_at": generated_at,
            "source": "live_market_data",
        }
        
        # Mark as degraded if we couldn't fetch anything
        if all(v is None for v in [vix_value, spy_change, qqq_change]):
            result["degraded"] = True
            result["degraded_reason"] = "Live data partially unavailable"
        else:
            result["degraded"] = False
            
        return result
        
    except Exception as e:
        fallback["error"] = str(e)
        return fallback


def _enhance_brief_with_live_data(brief: Dict[str, Any], live_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhance brief payload with live market indicators.
    
    BATCH-84-DEV-03: Adds live market context to snapshot-based brief.
    """
    if not isinstance(brief, dict):
        return brief
    
    enhanced = dict(brief)
    
    # Add live market indicators
    if isinstance(live_data, dict) and live_data:
        enhanced["live_market_data"] = live_data
        
        # Enhance summary with live context if available
        current_summary = brief.get("summary", "")
        vix = live_data.get("vix")
        spy_change = live_data.get("spy_change")
        
        if vix is not None or spy_change is not None:
            live_context_parts = []
            if vix is not None:
                vix_level = "élevé" if vix > 20 else "bas" if vix < 15 else "normal"
                live_context_parts.append(f"VIX={vix:.1f} ({vix_level})")
            if spy_change is not None:
                spy_direction = "haussier" if spy_change > 0.5 else "baissier" if spy_change < -0.5 else "stable"
                live_context_parts.append(f"S&P 500 {spy_direction} ({spy_change:+.2f}%)")
            
            if live_context_parts and current_summary:
                # Prepend live context to summary
                enhanced["summary"] = f"[Live: {', '.join(live_context_parts)}] {current_summary}"
    
    return enhanced


def _load_daily_brief_payload() -> Dict[str, Any]:
    """
    Load daily brief from snapshot and enhance with live market data.
    
    BATCH-84-DEV-03: Adds live VIX, SPY, QQQ data to snapshot-based brief.
    """
    generated_at = utc_now_iso()
    fallback_payload = {
        "summary": "No daily brief available yet.",
        "market_sentiment": "UNKNOWN",
        "top_signals": [],
        "top_risks": [],
        "macro_signals": [],
        "sector_rotation": {"top": [], "bottom": []},
        "generated_at": generated_at,
        "freshness": generated_at,
        "source": ["brief_daily_fallback"],
    }

    if storage_io is None:
        return fallback_payload

    snapshot = storage_io.load_json("brief_daily") or storage_io.load_json("brief_weekly")
    if not isinstance(snapshot, dict) or not snapshot:
        return fallback_payload

    raw_payload = snapshot.get("data") if isinstance(snapshot.get("data"), dict) else snapshot
    brief = raw_payload.get("daily") if isinstance(raw_payload, dict) and isinstance(raw_payload.get("daily"), dict) else raw_payload
    if not isinstance(brief, dict) or not brief:
        return fallback_payload

    normalized = dict(brief)
    normalized["summary"] = _trim_words(normalized.get("summary"), limit=200) or fallback_payload["summary"]
    normalized["market_sentiment"] = _safe_text(
        normalized.get("market_sentiment") or normalized.get("sentiment"),
        fallback_payload["market_sentiment"],
    )

    macro_signals = normalized.get("macro_signals", normalized.get("macro", []))
    normalized["macro_signals"] = macro_signals if isinstance(macro_signals, list) else []

    sector_rotation = normalized.get("sector_rotation")
    if not isinstance(sector_rotation, dict):
        sector_rotation = {"top": [], "bottom": []}
    sector_rotation.setdefault("top", [])
    sector_rotation.setdefault("bottom", [])
    normalized["sector_rotation"] = sector_rotation

    normalized["generated_at"] = _safe_text(normalized.get("generated_at"), generated_at)
    normalized["freshness"] = _safe_text(
        normalized.get("freshness") or normalized.get("generated_at"),
        normalized["generated_at"],
    )
    normalized["source"] = _normalize_source_list(
        normalized.get("source") or normalized.get("sources"),
        "brief_daily_snapshot",
    )
    normalized["event_timing"] = _normalize_brief_event_timing(normalized)
    
    # BATCH-84-DEV-03: Enhance with live market data
    try:
        live_data = _fetch_live_market_indicators()
        if live_data and not live_data.get("degraded", True):
            normalized = _enhance_brief_with_live_data(normalized, live_data)
    except Exception:
        # Silently continue with snapshot-only brief if live data fails
        pass
    
    return normalized


def _build_copilot_entry_points(
    scope: Optional[Dict[str, Any]] = None,
    daily_brief: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    scope_tickers = _normalize_tickers(scope.get("tickers") if isinstance(scope, dict) else [])
    return [
        {
            "id": "brief_of_day",
            "kind": "open",
            "label": "Brief du jour",
            "target": "/brief/daily",
        },
        {
            "id": "ask_copilot",
            "kind": "ask",
            "label": "Poser une question",
            "target": "/copilot/ask",
            "prefill": {
                "question": _build_starter_question(scope, daily_brief),
                "tickers": scope_tickers,
            },
        },
        {
            "id": "open_copilot",
            "kind": "open",
            "label": "Ouvrir Copilot",
            "target": "/copilot",
        },
    ]


def _with_scope_tickers(
    copilot_start: Dict[str, Any],
    *,
    scope: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    scope_tickers = _normalize_tickers(scope.get("tickers") if isinstance(scope, dict) else [])
    if not scope_tickers:
        return copilot_start

    normalized = dict(copilot_start)
    ask_items = normalized.get("ask")
    open_items = normalized.get("open")
    enriched_ask_items, enriched_open_items = _enrich_scope_start_actions(
        ask_items if isinstance(ask_items, list) else [],
        open_items if isinstance(open_items, list) else [],
        scope_tickers=scope_tickers,
    )
    normalized["ask"] = enriched_ask_items
    normalized["open"] = enriched_open_items
    return normalized


def _enrich_scope_start_actions(
    ask_items: List[Dict[str, Any]],
    open_items: List[Dict[str, Any]],
    *,
    scope_tickers: Optional[List[str]] = None,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    normalized_scope_tickers = _normalize_tickers(scope_tickers)

    enriched_ask_items: List[Dict[str, Any]] = []
    for item in ask_items:
        if not isinstance(item, dict):
            continue
        enriched = dict(item)
        prefill = enriched.get("prefill") if isinstance(enriched.get("prefill"), dict) else {}
        prompt = _safe_text(prefill.get("question") or enriched.get("prompt") or enriched.get("question"))
        if normalized_scope_tickers:
            prefill.setdefault("tickers", list(normalized_scope_tickers))
        if prompt:
            prefill.setdefault("question", prompt)
        enriched["prefill"] = prefill
        enriched_ask_items.append(enriched)

    enriched_open_items = [dict(item) for item in open_items if isinstance(item, dict)]
    if not normalized_scope_tickers:
        return enriched_ask_items, enriched_open_items

    existing_targets = {
        _safe_text(item.get("target")).lower()
        for item in enriched_open_items
        if _safe_text(item.get("target"))
    }
    derived_open_items: List[Dict[str, Any]] = []
    for ticker in normalized_scope_tickers[:2]:
        target = f"ticker:{ticker}"
        if target.lower() in existing_targets:
            continue
        derived_open_items.append(
            {
                "id": f"open_{ticker.lower()}",
                "kind": "open",
                "label": f"Open {ticker} deep dive",
                "target": target,
            }
        )
        existing_targets.add(target.lower())

    return enriched_ask_items, derived_open_items + enriched_open_items


def _legacy_copilot_start_payload(
    *,
    daily_brief: Optional[Dict[str, Any]] = None,
    entry_points: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    resolved_brief = dict(daily_brief) if isinstance(daily_brief, dict) else {}
    ask: List[Dict[str, Any]] = []
    open_items: List[Dict[str, Any]] = []

    for item in entry_points or []:
        if not isinstance(item, dict):
            continue
        normalized = dict(item)
        target = _safe_text(normalized.get("target")).lower()
        kind = _safe_text(normalized.get("kind")).lower()
        if kind == "ask" or target == "/copilot/ask":
            ask.append(normalized)
            continue
        if kind == "open" or target:
            open_items.append(normalized)

    return {
        "brief_of_day": resolved_brief,
        "ask": ask,
        "open": open_items,
    }


def _build_copilot_start_payload(
    *,
    daily_brief: Optional[Dict[str, Any]] = None,
    entry_points: Optional[List[Dict[str, Any]]] = None,
    scope: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    resolved_brief = dict(daily_brief) if isinstance(daily_brief, dict) else {}
    legacy_payload = _legacy_copilot_start_payload(
        daily_brief=resolved_brief,
        entry_points=entry_points,
    )
    context_timestamp = _safe_text(
        resolved_brief.get("freshness") or resolved_brief.get("generated_at"),
        utc_now_iso(),
    )

    for module_path in (
        "domains.judge.application.intelligence_service",
        "services.intelligence_service",
    ):
        try:
            module = import_module(module_path)
            build_fn = getattr(module, "_build_copilot_start_payload", None)
            if callable(build_fn):
                payload = build_fn(resolved_brief, context_timestamp=context_timestamp)
                if isinstance(payload, dict) and payload:
                    normalized = dict(payload)
                    brief_of_day = normalized.get("brief_of_day") if isinstance(normalized.get("brief_of_day"), dict) else {}
                    if brief_of_day:
                        event_timing = _normalize_brief_event_timing(resolved_brief)
                        if event_timing and not isinstance(brief_of_day.get("event_timing"), dict):
                            brief_of_day = dict(brief_of_day)
                            brief_of_day["event_timing"] = event_timing
                            normalized["brief_of_day"] = brief_of_day
                    if isinstance(legacy_payload.get("brief_of_day"), dict) and not normalized.get("brief_of_day"):
                        normalized["brief_of_day"] = dict(legacy_payload.get("brief_of_day") or {})
                    return _with_scope_tickers(normalized, scope=scope)
        except Exception:
            continue

    return _with_scope_tickers(legacy_payload, scope=scope)


class CopilotStartPayloadContract(SharedCopilotStartPayload):
    pass


def _contract_dump(model: BaseModel) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_none=True)  # type: ignore[attr-defined]
    if hasattr(model, "dict"):
        return model.dict(exclude_none=True)  # type: ignore[attr-defined]
    return dict(getattr(model, "__dict__", {}))


def _pick_ranked_action(
    ranked_action: Any,
    ask_items: List[Dict[str, Any]],
    open_items: List[Dict[str, Any]],
    *,
    scope_tickers: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    normalized_scope_tickers = _normalize_tickers(scope_tickers)
    if normalized_scope_tickers:
        preferred_targets = {
            f"ticker:{ticker.lower()}"
            for ticker in normalized_scope_tickers
        }
        for item in open_items:
            if not isinstance(item, dict):
                continue
            target = _safe_text(item.get("target")).lower()
            if target in preferred_targets:
                return dict(item)

    if isinstance(ranked_action, dict) and ranked_action.get("id") and ranked_action.get("target"):
        return dict(ranked_action)

    for item in ask_items + open_items:
        if not isinstance(item, dict):
            continue
        if not item.get("id") or not item.get("target"):
            continue
        return dict(item)
    return None


def _resolve_start_effective_scope(
    requested_scope: Optional[Dict[str, Any]],
    payload: Optional[Dict[str, Any]],
) -> Optional[Dict[str, List[str]]]:
    payload_scope = (
        _normalize_tickers(payload.get("scope_tickers"))
        if isinstance(payload, dict)
        else []
    )
    if payload_scope:
        return {"tickers": payload_scope}
    requested_tickers: List[str] = []
    for item in (requested_scope.get("tickers") if isinstance(requested_scope, dict) else []) or []:
        token = _safe_text(item).upper()
        if token and token not in requested_tickers:
            requested_tickers.append(token)
    return {"tickers": requested_tickers} if requested_tickers else None


def build_copilot_start_response(
    start_payload: Optional[Dict[str, Any]],
    *,
    scope: Optional[Dict[str, Any]] = None,
    note: Optional[str] = None,
    context_influence: Optional[Dict[str, Any]] = None,
    portfolio_context: Optional[Dict[str, Any]] = None,
    regime_detection: Optional[Dict[str, Any]] = None,
    allocation_drift_alerts: Optional[Dict[str, Any]] = None,
    fallback_used: Optional[str] = None,
) -> Dict[str, Any]:
    resolved_start = dict(start_payload) if isinstance(start_payload, dict) else {}
    brief_of_day = (
        dict(resolved_start.get("brief_of_day"))
        if isinstance(resolved_start.get("brief_of_day"), dict)
        else {}
    )
    resolved_scope_tickers: List[str] = []
    for item in (scope.get("tickers") if isinstance(scope, dict) else []) or []:
        token = _safe_text(item).upper()
        if token and token not in resolved_scope_tickers:
            resolved_scope_tickers.append(token)
    ask_items = [
        dict(item) for item in resolved_start.get("ask", []) if isinstance(item, dict)
    ]
    open_items = [
        dict(item) for item in resolved_start.get("open", []) if isinstance(item, dict)
    ]
    ask_items, open_items = _enrich_scope_start_actions(
        ask_items,
        open_items,
        scope_tickers=resolved_scope_tickers,
    )

    if not ask_items:
        ask_items = [
            {
                "id": "ask_copilot",
                "kind": "ask",
                "label": "Ask a question",
                "target": "/copilot/ask",
                "prefill": {
                    "question": "What's moving today?",
                    "tickers": list(resolved_scope_tickers),
                },
            }
        ]

    if not open_items:
        open_items = [
            {
                "id": "open_copilot",
                "kind": "open",
                "label": "Open Copilot",
                "target": "/copilot",
            }
        ]

    ranked_action = _pick_ranked_action(
        resolved_start.get("ranked_action"),
        ask_items,
        open_items,
        scope_tickers=resolved_scope_tickers,
    )

    generated_at = (
        _safe_text(brief_of_day.get("freshness") or brief_of_day.get("generated_at"))
        or utc_now_iso()
    )
    if isinstance(allocation_drift_alerts, dict) and allocation_drift_alerts:
        brief_of_day = dict(brief_of_day)
        brief_of_day["allocation_drift_alerts"] = dict(allocation_drift_alerts)

    source = brief_of_day.get("sources")
    if not isinstance(source, list):
        source = brief_of_day.get("source")
    normalized_source = [
        _safe_text(item)
        for item in (source if isinstance(source, list) else [])
        if _safe_text(item)
    ]
    if "copilot_start_route" not in normalized_source:
        normalized_source.append("copilot_start_route")

    warnings: List[str] = []
    if note:
        warnings.append(note)

    contract = CopilotStartPayloadContract(
        brief_of_day=brief_of_day,
        ranked_action=ranked_action,
        ask=ask_items,
        open=open_items,
        generated_at=generated_at,
        freshness=generated_at,
        source=normalized_source or ["copilot_start_route"],
        sources=normalized_source or ["copilot_start_route"],
        filters_applied={"tickers": list(resolved_scope_tickers)},
        stats={
            "ask_count": len(ask_items),
            "open_count": len(open_items),
        },
        warnings=warnings,
        note=note,
        scope_tickers=list(resolved_scope_tickers) if resolved_scope_tickers else None,
        context_influence=dict(context_influence) if isinstance(context_influence, dict) and context_influence else None,
        portfolio_context=dict(portfolio_context) if isinstance(portfolio_context, dict) and portfolio_context else None,
        regime_detection=dict(regime_detection) if isinstance(regime_detection, dict) and regime_detection else None,
        allocation_drift_alerts=(
            dict(allocation_drift_alerts)
            if isinstance(allocation_drift_alerts, dict) and allocation_drift_alerts
            else None
        ),
        fallback_used=fallback_used,
    )
    return _contract_dump(contract)


async def build_copilot_start_endpoint_payload(
    *,
    context_service_cls: Optional[Any] = None,
    scope: Optional[Dict[str, Any]] = None,
    namespace: Optional[str] = None,
    namespace_rewriter: Optional[Callable[[Any, Optional[str]], Any]] = None,
) -> Dict[str, Any]:
    fallback_note = "Market context service temporarily unavailable."

    def _rewrite_namespace(payload: Any) -> Any:
        if callable(namespace_rewriter):
            return namespace_rewriter(payload, namespace)
        return payload

    try:
        payload = await build_context_payload(
            context_service_cls=context_service_cls,
            scope=scope,
        )
        effective_scope = _resolve_start_effective_scope(scope, payload)
        start_payload = (
            payload.get("copilot_start")
            if isinstance(payload, dict)
            else None
        )
        start_payload = _rewrite_namespace(start_payload)

        fallback_used = None
        note = None
        if isinstance(payload, dict) and payload.get("regime") == "fallback":
            note = fallback_note
            fallback_used = "market_context_fallback"

        if not isinstance(start_payload, dict) or not start_payload:
            start_payload = _build_copilot_start_payload(
                daily_brief=payload.get("daily_brief") if isinstance(payload, dict) else None,
                entry_points=payload.get("entry_points") if isinstance(payload, dict) else None,
                scope=effective_scope,
            )
            start_payload = _rewrite_namespace(start_payload)
            if not fallback_used:
                fallback_used = "copilot_start_rebuilt"

        return build_copilot_start_response(
            start_payload,
            scope=effective_scope,
            note=note,
            context_influence=payload.get("context_influence") if isinstance(payload, dict) else None,
            portfolio_context=payload.get("portfolio_context") if isinstance(payload, dict) else None,
            regime_detection=payload.get("regime_detection") if isinstance(payload, dict) else None,
            allocation_drift_alerts=payload.get("allocation_drift_alerts") if isinstance(payload, dict) else None,
            fallback_used=fallback_used,
        )
    except Exception:
        daily_brief = _load_daily_brief_payload()
        entry_points = _build_copilot_entry_points(scope, daily_brief)
        module_globals = globals()
        build_start_payload = module_globals.get(
            "_build_copilot_start_payload"
        ) or module_globals.get("_legacy_copilot_start_payload")

        if callable(build_start_payload):
            fallback_start = build_start_payload(
                daily_brief=daily_brief,
                entry_points=entry_points,
                scope=scope,
            )
        else:
            fallback_start = {
                "brief_of_day": daily_brief,
                "ask": [],
                "open": [],
            }
        fallback_start = _rewrite_namespace(fallback_start)
        return build_copilot_start_response(
            fallback_start,
            scope=scope,
            note=fallback_note,
            context_influence=None,
            portfolio_context=None,
            regime_detection=None,
            allocation_drift_alerts=None,
            fallback_used="copilot_context_exception",
        )


def _extract_bullets(text: str) -> List[str]:
    cleaned = []
    for line in _safe_text(text).splitlines():
        item = re.sub(r"^\s*[-*•]\s*", "", line).strip()
        if len(item) >= 8:
            cleaned.append(item)
    return cleaned[:3]


def _extract_reasoning(raw_answer: Any, fallback_count: int = 3) -> List[str]:
    if isinstance(raw_answer, list):
        items = [str(item).strip() for item in raw_answer if str(item).strip()]
        return items[:fallback_count]

    if not isinstance(raw_answer, str):
        return []

    bullets = _extract_bullets(raw_answer)
    if len(bullets) >= fallback_count:
        return bullets

    sentences = [segment.strip() for segment in re.split(r"(?<=[.!?])\s+", raw_answer) if segment.strip()]
    for segment in sentences:
        if len(segment) >= 12 and segment not in bullets:
            bullets.append(segment)
        if len(bullets) >= fallback_count:
            break
    return bullets[:fallback_count]


def _extract_json_from_text(raw: str) -> Optional[Dict[str, Any]]:
    text = _safe_text(raw)
    if not text:
        return None

    if text.startswith("{") and text.endswith("}"):
        try:
            value = json.loads(text)
            if isinstance(value, dict):
                return value
        except Exception:
            pass

    fenced_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, flags=re.IGNORECASE)
    if fenced_match:
        try:
            value = json.loads(fenced_match.group(1))
            if isinstance(value, dict):
                return value
        except Exception:
            pass

    start = text.find("{")
    if start >= 0:
        tail = text[start:]
        try:
            value = json.loads(tail)
            if isinstance(value, dict):
                return value
        except Exception:
            pass

    return None


def _derive_risk_level(
    *,
    parsed_payload: Optional[Dict[str, Any]],
    market_context_payload: Dict[str, Any],
    confidence: float,
) -> str:
    parsed_payload = parsed_payload if isinstance(parsed_payload, dict) else {}

    parsed_risk_level = parsed_payload.get("risk_level")
    if parsed_risk_level is None and isinstance(parsed_payload.get("risk"), dict):
        parsed_risk_level = (parsed_payload.get("risk") or {}).get("level")
    if parsed_risk_level is None and not isinstance(parsed_payload.get("risk"), dict):
        parsed_risk_level = parsed_payload.get("risk")
    if parsed_risk_level is not None:
        return _normalize_risk_level(parsed_risk_level)

    characteristics = market_context_payload.get("characteristics")
    if isinstance(characteristics, dict):
        ctx_risk_level = characteristics.get("risk_level")
        if _safe_text(ctx_risk_level):
            return _normalize_risk_level(ctx_risk_level)

    if confidence >= 0.75:
        return "low"
    if confidence >= 0.45:
        return "medium"
    return "high"


def _resolve_context_service_class(context_service_cls: Optional[Any] = None) -> Optional[Any]:
    if context_service_cls is not None:
        return context_service_cls

    for path in (
        "domains.copilot.application.context_service",
        "services.context_service",  # legacy bridge fallback
    ):
        try:
            module = import_module(path)
            service_cls = getattr(module, "ContextService", None)
            if service_cls is not None:
                return service_cls
        except Exception:
            continue
    return None


def _format_market_context_prompt(context_payload: Dict[str, Any]) -> str:
    if not isinstance(context_payload, dict):
        return ""

    regime = _safe_text(context_payload.get("regime"), "inconnu")
    confidence = float(context_payload.get("confidence") or 0.0)
    key_drivers = context_payload.get("key_drivers") or []
    if not isinstance(key_drivers, list):
        key_drivers = []

    characs = context_payload.get("characteristics") or {}
    if not isinstance(characs, dict):
        characs = {}

    layout = context_payload.get("recommended_layout") or {}
    if not isinstance(layout, dict):
        layout = {}

    metadata = context_payload.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    forecast_signals = context_payload.get("forecast_signals", [])
    news_signals = context_payload.get("news_signals", [])
    if not isinstance(forecast_signals, list):
        forecast_signals = []
    if not isinstance(news_signals, list):
        news_signals = []
    forecast_values = [
        "{ticker}:{direction}:{confidence}".format(
            ticker=_safe_text(item.get("ticker")),
            direction=_safe_text(item.get("direction"), "inconnu"),
            confidence=round(_to_float(item.get("confidence"), 0.0), 2),
        )
        for item in forecast_signals[:3]
        if isinstance(item, dict)
    ]
    news_values = [
        _safe_text(item.get("headline"), "aucune")
        for item in news_signals[:3]
        if isinstance(item, dict)
    ]

    return (
        "Contexte marché auto (copilot):\n"
        f"- regime={regime}, confiance={round(confidence, 2)}\n"
        f"- drivers={', '.join(_safe_text(x) for x in key_drivers[:5])}\n"
        f"- caractéristiques={', '.join(f'{k}:{_safe_text(v)}' for k, v in characs.items())}\n"
        f"- layout_recommandé={', '.join(_safe_text(x) for x in layout.get('primary_widgets', [])[:3])}\n"
        f"- sources={', '.join(metadata.get('sources') if isinstance(metadata.get('sources'), list) else ['unknown'])}\n"
        f"- scope_tickers={', '.join(context_payload.get('scope_tickers', [])) or 'none'}\n"
        f"- forecast_signaux={', '.join(forecast_values)}\n"
        f"- news_signaux={', '.join(news_values)}\n"
    )


def _build_context_chunk_from_payload(context_payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "text": _safe_text(_format_market_context_prompt(context_payload), "Contexte marché indisponible"),
        "meta": {
            "type": "market_context",
            "url": "backend://copilot/market-context",
            "date": context_payload.get("metadata", {}).get("generated_at", utc_now_iso()),
            "source": "copilot-service",
        },
        "id": "market_context_chunk",
    }


async def _load_event_timing_payload(limit: int = 3) -> Dict[str, Any]:
    try:
        module = import_module("domains.judge.application.judge_endpoint_service")
        build_fn = getattr(module, "get_judge_event_impact_horizon_matrix_payload", None)
        if not callable(build_fn):
            return {}
        response = await build_fn(event_type=None, limit=max(1, int(limit)))
        data = response.get("data") if isinstance(response, dict) else {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _build_event_timing_note(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return None

    rows = payload.get("matrix")
    if not isinstance(rows, list) or not rows:
        return None

    critical_events: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        horizons = row.get("horizons") if isinstance(row.get("horizons"), dict) else {}
        one_week = horizons.get("1w") if isinstance(horizons.get("1w"), dict) else {}
        impact_score = _to_float(one_week.get("impact_score"), 0.0)
        if impact_score < 0.6:
            continue
        critical_events.append(
            {
                "event_type": _safe_text(row.get("event_type"), "event"),
                "dominant_horizon": _safe_text(row.get("dominant_horizon"), "1w"),
                "impact_score": round(impact_score, 4),
                "interpretation": _safe_text(row.get("interpretation")),
            }
        )
        if len(critical_events) >= 2:
            break

    if not critical_events:
        return None

    labels = ", ".join(
        f"{item['event_type']} ({item['dominant_horizon']})"
        for item in critical_events
    )
    normalized_source = ["copilot_event_timing", *(_normalize_string_list(payload.get("source")) or [])]
    return {
        "summary": f"Timing risk elevated around {labels}.",
        "events": critical_events,
        "freshness": _safe_text(payload.get("freshness") or payload.get("generated_at"), utc_now_iso()),
        "source": normalized_source,
        "sources": normalized_source,
    }



def _fetch_live_market_context() -> str:
    """Fetches live market data (forecasts, brief, news) and formats as context string.
    Returns empty string if backend not reachable - never raises."""
    try:
        parts = []

        # 1. Brief du jour
        try:
            brief = _load_daily_brief_payload()
            summary = _safe_text(brief.get("summary"))
            sentiment = _safe_text(brief.get("market_sentiment") or brief.get("sentiment"), "UNKNOWN")
            if summary:
                parts.append(f"=== MARCHE AUJOURD'HUI ===\nSentiment: {sentiment}\n{summary[:300]}")
            macro = brief.get("macro_signals", [])
            if macro:
                macro_str = " | ".join(_brief_signal_label(m, "macro") for m in macro[:4])
                parts.append(f"Macro: {macro_str}")
            sectors = brief.get("sector_rotation", {})
            top = sectors.get("top", [])
            bot = sectors.get("bottom", [])
            if top or bot:
                top_labels = _brief_list_values(top)[:3]
                bottom_labels = _brief_list_values(bot)[:3]
                parts.append(
                    f"Secteurs forts: {', '.join(top_labels)} | Faibles: {', '.join(bottom_labels)}"
                )
        except Exception:
            pass

        # 2. Top forecasts (confiance > 60%) depuis snapshots locaux.
        try:
            forecasts_payload = {}
            if storage_io is not None:
                forecasts_payload = storage_io.load_json("forecasts") or storage_io.load_json("forecast") or {}

            rows = []
            if isinstance(forecasts_payload, dict):
                if isinstance(forecasts_payload.get("rows"), list):
                    rows = forecasts_payload.get("rows") or []
                elif isinstance(forecasts_payload.get("data"), dict) and isinstance(forecasts_payload["data"].get("rows"), list):
                    rows = forecasts_payload["data"].get("rows") or []
            strong = [r for r in rows if r.get("confidence", 0) > 0.60][:6]
            if strong:
                fc_lines = [f"{r['ticker']} -> {r['direction'].upper()} ({r['confidence']:.0%})" for r in strong]
                parts.append("=== FORECASTS FORTS ===\n" + " | ".join(fc_lines))
        except Exception:
            pass

        # 3. News récentes (3 dernières) depuis snapshots locaux.
        try:
            news_payload = {}
            if storage_io is not None:
                news_payload = storage_io.load_json("news_feed") or {}

            articles = []
            if isinstance(news_payload, dict):
                if isinstance(news_payload.get("articles"), list):
                    articles = news_payload.get("articles") or []
                elif isinstance(news_payload.get("data"), dict):
                    nested = news_payload.get("data") or {}
                    if isinstance(nested.get("articles"), list):
                        articles = nested.get("articles") or []
                    elif isinstance(nested.get("items"), list):
                        articles = nested.get("items") or []
            if articles:
                news_lines = []
                for a in articles[:3]:
                    headline = a.get("headline", a.get("title", ""))[:100]
                    sentiment = a.get("sentiment", "")
                    impact = a.get("impact", "")
                    if headline:
                        news_lines.append(f"• {headline} [{sentiment}/{impact}]")
                if news_lines:
                    parts.append("=== NEWS RECENTES ===\n" + "\n".join(news_lines))
        except Exception:
            pass

        return "\n\n".join(parts)
    except Exception:
        return ""


def _finalize_ask_payload(payload: Dict[str, Any], *, default_source: str = "copilot.ask") -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return payload

    freshness = _safe_text(payload.get("freshness") or payload.get("generated_at"), "")
    if not freshness:
        freshness = utc_now_iso()
        payload.setdefault("generated_at", freshness)
    payload.setdefault("freshness", freshness)

    risk_obj = payload.get("risk") if isinstance(payload.get("risk"), dict) else {}
    risk_level = payload.get("risk_level") or risk_obj.get("level")
    risk_caveat = payload.get("risk_caveat") or risk_obj.get("caveat")

    if callable(ensure_decision_contract):
        ensure_decision_contract(
            payload,
            default_source=default_source,
            verdict=payload.get("verdict") or payload.get("action"),
            confidence=payload.get("confidence"),
            why=payload.get("why") or payload.get("reasoning"),
            risk_level=risk_level,
            risk_caveat=risk_caveat,
            freshness=freshness,
        )
    else:
        payload.setdefault("risk_flag", str(risk_level or "").lower() in {"high", "critical"})
        payload.setdefault("source", [default_source])

    return normalize_ask_payload_contract(payload)

async def build_ask_payload(
    *,
    question: str,
    scope: Optional[Dict[str, Any]] = None,
    tickers: Optional[List[str]] = None,
    max_sources: Optional[int] = 5,
    context_years: Optional[int] = None,
    rag_store_cls: Optional[Any] = None,
    ask_llm_fn: Optional[Any] = None,
    context_service_cls: Optional[Any] = None,
) -> Dict[str, Any]:
    """Build copilot answer payload from RAG + LLM.

    Returns a never-empty payload.
    """
    try:
        if rag_store_cls is None:
            rag_store_cls = import_module("research.rag_store").RAGStore
        if ask_llm_fn is None:
            ask_llm_fn = _default_ask_llm
        if context_service_cls is None:
            context_service_cls = _resolve_context_service_class()
    except Exception as import_exc:
        return _finalize_ask_payload({
            "answer": f"Copilot unavailable: {import_exc}",
            "action": "hold",
            "verdict": "hold",
            "why": ["Copilot indisponible, fallback de sécurité activé."],
            "risk": {"level": "high", "caveat": "Service copilot indisponible."},
            "risk_level": "high",
            "sources": [],
            "citations": [],
            "model": "unconfigured",
            "confidence": 0.0,
            "generated_at": utc_now_iso(),
            "sources_count": 0,
            "quality_status": "error",
            "requirements_met": {"min_sources_2": False, "quality_threshold": False},
            "error": str(import_exc),
        })

    try:
        rag_store = rag_store_cls()
        resolved_scope, saved_portfolio_context = _resolve_scope_with_saved_portfolio(
            scope,
            tickers=tickers,
        )
        if context_years is not None:
            resolved_scope.setdefault("context_years", int(context_years))

        market_context = await build_context_payload(context_service_cls=context_service_cls, scope=resolved_scope)
        market_context_payload = market_context if isinstance(market_context, dict) else {}

        top_k = max(1, min(int(max_sources or 5), 20))
        context_chunks = rag_store.search(resolved_scope, top_k=top_k)
        if not context_chunks and market_context_payload:
            context_chunks = [_build_context_chunk_from_payload(market_context_payload)]

        if not context_chunks:
            return _finalize_ask_payload({
                "answer": (
                    "Je n'ai pas trouvé d'informations pertinentes pour répondre à votre "
                    f"question: '{question}'."
                ),
                "action": "hold",
                "verdict": "hold",
                "why": ["Aucune source contextuelle disponible pour une recommandation fiable."],
                "risk": {"level": "high", "caveat": "Aucune source trouvée dans la mémoire."},
                "risk_level": "high",
                "sources": [],
                "citations": [],
                "model": "rag_empty",
                "confidence": 0.3,
                "generated_at": utc_now_iso(),
                "warning": "Aucune source trouvée dans la mémoire",
                "sources_count": 0,
                "quality_status": "insufficient_sources",
                "requirements_met": {
                    "min_sources_2": False,
                    "quality_threshold": False,
                },
            })

        # Injecter le contexte marché live (forecasts + brief + news)
        live_ctx = _fetch_live_market_context()
        context_prompt = _format_market_context_prompt(market_context_payload)
        portfolio_prompt = _format_saved_portfolio_prompt(saved_portfolio_context)
        combined_context = "\n\n".join(filter(None, [live_ctx, context_prompt, portfolio_prompt]))

        if combined_context:
            question_for_llm = (
                f"{question}\n\n"
                f"--- Contexte marché en temps réel ---\n{combined_context}\n"
                "---\n"
                "Donne une recommandation claire (HOLD/BUY/SELL/REDUIRE/AUGMENTER) avec 3 points de raisonnement max."
            )
        else:
            question_for_llm = question

        llm_response = await _invoke_ask_llm_with_timeout(
            ask_llm_fn,
            question=question_for_llm,
            context_chunks=context_chunks,
            max_tokens=1000,
        )
        sources = _build_sources_from_chunks(context_chunks)
        model_name = str(llm_response.get("model") or "unknown")
        has_min_sources = len(sources) >= 2
        has_quality_model = model_name not in {"unconfigured", "fallback", "rag_empty", "error"}
        quality_status = (
            "sufficient_sources" if (has_min_sources and has_quality_model) else "insufficient_sources"
        )

        parsed = _extract_json_from_text(str(llm_response.get("answer") or ""))
        parsed_payload = parsed if isinstance(parsed, dict) else {}
        confidence = _resolve_payload_confidence(
            parsed_payload=parsed_payload or None,
            llm_response=llm_response,
            has_min_sources=has_min_sources,
            has_quality_model=has_quality_model,
        )
        parsed_answer = _safe_text(parsed_payload.get("answer"), "")
        parsed_reasoning_source = parsed_payload.get("why")
        if parsed_reasoning_source is None:
            parsed_reasoning_source = parsed_payload.get("reasoning", "")
        parsed_reasoning = _extract_reasoning(parsed_reasoning_source) if parsed_payload else []
        parsed_action = _coerce_verdict(_safe_text(parsed_payload.get("action") or parsed_payload.get("verdict")))
        parsed_horizon = parsed_payload.get("horizon") or parsed_payload.get("time_horizon")
        parsed_risks = parsed_payload.get("risks")
        parsed_next_steps = parsed_payload.get("next_steps")
        parsed_invalidation = parsed_payload.get("invalidation")
        parsed_risk = parsed_payload.get("risk") if isinstance(parsed_payload.get("risk"), dict) else {}
        parsed_risk_caveat = _safe_text(
            parsed_payload.get("risk_caveat") or parsed_risk.get("caveat"),
            "",
        )
        event_timing = _build_event_timing_note(await _load_event_timing_payload())

        raw_answer = str(llm_response.get("answer") or "").strip()
        answer_seed = parsed_answer or raw_answer
        reasoning = parsed_reasoning or _extract_reasoning(answer_seed)
        action = parsed_action or _coerce_verdict(answer_seed)
        if parsed_answer:
            final_answer = parsed_answer
        elif reasoning:
            final_answer = " ".join(reasoning)
        else:
            final_answer = raw_answer

        risk_fragments = []
        if parsed_risk_caveat:
            risk_fragments.append(parsed_risk_caveat)
        if event_timing:
            risk_fragments.append(event_timing["summary"])
        if not has_min_sources:
            risk_fragments.append("Sources insuffisantes (moins de 2).")
        if not has_quality_model:
            risk_fragments.append("Modèle de réponse fallback.")
        if market_context_payload and float(market_context_payload.get("confidence") or 0.0) < 0.45:
            risk_fragments.append("Confiance marché faible.")
        risk_caveat = " ".join(risk_fragments) or "Contexte marché et sources disponibles."
        risk_level = _derive_risk_level(
            parsed_payload=parsed_payload or None,
            market_context_payload=market_context_payload,
            confidence=confidence,
        )

        response_payload = {
            "question": question,
            "answer": final_answer,
            "action": action,
            "verdict": action,
            "horizon": parsed_horizon,
            "reasoning": reasoning,
            "why": parsed_payload.get("why") or reasoning,
            "risks": parsed_risks,
            "next_steps": parsed_next_steps,
            "invalidation": parsed_invalidation,
            "risk": {"level": risk_level, "caveat": risk_caveat},
            "risk_level": risk_level,
            "risk_caveat": risk_caveat,
            "sources": sources,
            "citations": llm_response.get("citations", []),
            "model": model_name,
            "confidence": confidence,
            "generated_at": utc_now_iso(),
            "sources_count": len(sources),
            "quality_status": quality_status,
            "requirements_met": {
                "min_sources_2": has_min_sources,
                "quality_threshold": has_quality_model,
            },
            "context_influence": _build_context_influence(
                requested_scope=scope,
                requested_tickers=tickers,
                resolved_scope=resolved_scope,
                saved_portfolio_context=saved_portfolio_context,
            ),
        }
        if event_timing:
            response_payload["event_timing"] = event_timing
        if saved_portfolio_context:
            response_payload["portfolio_context"] = saved_portfolio_context
        return _finalize_ask_payload(response_payload)
    except Exception as exc:
        return _finalize_ask_payload({
            "question": question,
            "answer": f"Désolé, une erreur s'est produite lors du traitement: {exc}",
            "action": "hold",
            "verdict": "hold",
            "horizon": "1w",
            "why": ["Erreur interne copilot, recommandation conservatrice appliquée."],
            "risk": {"level": "high", "caveat": "Erreur interne copilot."},
            "risk_level": "high",
            "sources": [],
            "citations": [],
            "model": "error",
            "confidence": 0.0,
            "generated_at": utc_now_iso(),
            "sources_count": 0,
            "quality_status": "error",
            "requirements_met": {"min_sources_2": False, "quality_threshold": False},
            "error": str(exc),
        })


def build_history_payload(*, limit: int) -> Dict[str, Any]:
    """Never-empty history payload (no mock data)."""
    return {
        "conversations": [],
        "count": 0,
        "limit": int(limit),
        "source": ["copilot_service", "history_not_persisted"],
    }


async def build_context_payload(context_service_cls: Optional[Any] = None, scope: Optional[Dict[str, Any]] = None) -> Any:
    """Returns current context when available, or a never-empty fallback."""
    resolved_scope, saved_portfolio_context = _resolve_scope_with_saved_portfolio(
        scope
    )
    payload: Dict[str, Any]
    try:
        cls = _resolve_context_service_class(context_service_cls)
        if cls is not None:
            candidate = await cls().get_current_market_context()
            if isinstance(candidate, dict) and candidate:
                payload = dict(candidate)
            else:
                payload = _collect_fallback_context(resolved_scope)
        else:
            payload = _collect_fallback_context(resolved_scope)
    except Exception:
        payload = _collect_fallback_context(resolved_scope)

    if isinstance(resolved_scope, dict) and resolved_scope.get("tickers"):
        payload["scope_tickers"] = _normalize_tickers(resolved_scope.get("tickers"))
    if saved_portfolio_context:
        payload["portfolio_context"] = saved_portfolio_context
    payload["context_influence"] = _build_context_influence(
        requested_scope=scope,
        resolved_scope=resolved_scope,
        saved_portfolio_context=saved_portfolio_context,
    )
    
    # Enrich with strategy playbook (BATCH-15-DEV-02)
    # Extract regime and risk profile from context for playbook resolution
    regime = payload.get("regime", "NORMAL").lower()
    risk_profile = "moderate"  # Default; could be extended to support user profiles
    
    try:
        from ..application.playbook_resolver import get_playbook_resolver
        resolver = get_playbook_resolver()
        playbook = resolver.resolve(regime=regime, risk_profile=risk_profile)
        payload["playbook_id"] = playbook.id
        payload["playbook_context"] = {
            "name": playbook.name,
            "description": playbook.description,
            "regime": playbook.regime.value,
            "risk_profile": playbook.risk_profile.value,
            "guardrails": playbook.guardrails[:2],
        }
    except Exception as e:
        # Non-blocking: playbook enrichment is optional
        payload["playbook_id"] = None
        payload["playbook_warning"] = f"Playbook resolution unavailable: {str(e)}"

    payload["regime_detection"] = _build_regime_detection_payload(payload)
    payload["allocation_drift_alerts"] = _build_allocation_drift_alerts(
        playbook_context=payload.get("playbook_context"),
        saved_portfolio_context=saved_portfolio_context,
    )
    
    payload["daily_brief"] = _load_daily_brief_payload()
    payload["entry_points"] = _build_copilot_entry_points(
        resolved_scope,
        payload.get("daily_brief"),
    )
    payload["copilot_start"] = _build_copilot_start_payload(
        daily_brief=payload.get("daily_brief"),
        entry_points=payload.get("entry_points"),
        scope=resolved_scope,
    )
    return payload


def build_report_payload(*, prompt: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a report request payload."""
    return {
        "id": f"rpt_{int(datetime.utcnow().timestamp())}",
        "prompt": prompt,
        "filters": filters or {},
        "created_at": utc_now_iso(),
        "status": "queued",
    }
