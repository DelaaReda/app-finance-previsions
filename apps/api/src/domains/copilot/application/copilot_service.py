"""Reusable business logic for Copilot endpoints."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from importlib import import_module
from typing import Any, Dict, List, Optional

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


def _load_daily_brief_payload() -> Dict[str, Any]:
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

    try:
        from storage.io import load_json
    except Exception:
        return fallback_payload

    snapshot = load_json("brief_daily") or load_json("brief_weekly")
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
    return normalized


def _build_copilot_entry_points(scope: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
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
                "question": "Que dois-je surveiller aujourd'hui ?",
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
    if not isinstance(ask_items, list):
        return normalized

    enriched_items: List[Dict[str, Any]] = []
    for item in ask_items:
        if not isinstance(item, dict):
            continue
        enriched = dict(item)
        prefill = enriched.get("prefill") if isinstance(enriched.get("prefill"), dict) else {}
        prompt = _safe_text(prefill.get("question") or enriched.get("prompt") or enriched.get("question"))
        prefill.setdefault("tickers", scope_tickers)
        if prompt:
            prefill.setdefault("question", prompt)
        enriched["prefill"] = prefill
        enriched_items.append(enriched)

    normalized["ask"] = enriched_items
    return normalized


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
                    if isinstance(legacy_payload.get("brief_of_day"), dict) and not normalized.get("brief_of_day"):
                        normalized["brief_of_day"] = dict(legacy_payload.get("brief_of_day") or {})
                    return _with_scope_tickers(normalized, scope=scope)
        except Exception:
            continue

    return _with_scope_tickers(legacy_payload, scope=scope)


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



def _fetch_live_market_context() -> str:
    """Fetches live market data (forecasts, brief, news) and formats as context string.
    Returns empty string if backend not reachable - never raises."""
    try:
        import urllib.request as _ur
        import json as _json
        import urllib.error

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

        # 2. Top forecasts (confiance > 60%)
        try:
            with _ur.urlopen("http://localhost:8050/api/forecasts?limit=10", timeout=3) as r:
                fc_data = _json.load(r).get("data", {})
            rows = fc_data.get("rows", [])
            strong = [r for r in rows if r.get("confidence", 0) > 0.60][:6]
            if strong:
                fc_lines = [f"{r['ticker']} -> {r['direction'].upper()} ({r['confidence']:.0%})" for r in strong]
                parts.append("=== FORECASTS FORTS ===\n" + " | ".join(fc_lines))
        except Exception:
            pass

        # 3. News récentes (3 dernières)
        try:
            with _ur.urlopen("http://localhost:8050/api/news/feed?limit=3", timeout=3) as r:
                news_data = _json.load(r).get("data", {})
            articles = news_data.get("articles", news_data.get("items", []))
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

    return payload

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
        resolved_scope = dict(scope or {})
        normalized_tickers = _normalize_tickers(tickers)
        if normalized_tickers:
            resolved_scope["tickers"] = normalized_tickers
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
        combined_context = "\n\n".join(filter(None, [live_ctx, context_prompt]))

        if combined_context:
            question_for_llm = (
                f"{question}\n\n"
                f"--- Contexte marché en temps réel ---\n{combined_context}\n"
                "---\n"
                "Donne une recommandation claire (HOLD/BUY/SELL/REDUIRE/AUGMENTER) avec 3 points de raisonnement max."
            )
        else:
            question_for_llm = question

        llm_response = ask_llm_fn(
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
        confidence = _resolve_payload_confidence(
            parsed_payload=parsed if isinstance(parsed, dict) else None,
            llm_response=llm_response,
            has_min_sources=has_min_sources,
            has_quality_model=has_quality_model,
        )
        parsed_answer = _safe_text((parsed or {}).get("answer") if isinstance(parsed, dict) else "")
        parsed_reasoning = _extract_reasoning((parsed or {}).get("reasoning", "")) if isinstance(parsed, dict) else []
        parsed_action = _coerce_verdict(_safe_text((parsed or {}).get("action") or (parsed or {}).get("verdict")))
        final_answer = parsed_answer or str(llm_response.get("answer") or "").strip()

        reasoning = parsed_reasoning or _extract_reasoning(final_answer)
        action = parsed_action or _coerce_verdict(final_answer)

        risk_fragments = []
        if not has_min_sources:
            risk_fragments.append("Sources insuffisantes (moins de 2).")
        if not has_quality_model:
            risk_fragments.append("Modèle de réponse fallback.")
        if market_context_payload and float(market_context_payload.get("confidence") or 0.0) < 0.45:
            risk_fragments.append("Confiance marché faible.")
        risk_caveat = " ".join(risk_fragments) or "Contexte marché et sources disponibles."
        risk_level = _derive_risk_level(
            parsed_payload=parsed if isinstance(parsed, dict) else None,
            market_context_payload=market_context_payload,
            confidence=confidence,
        )

        return _finalize_ask_payload({
            "question": question,
            "answer": final_answer,
            "action": action,
            "verdict": action,
            "reasoning": reasoning,
            "why": reasoning,
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
        })
    except Exception as exc:
        return _finalize_ask_payload({
            "answer": f"Désolé, une erreur s'est produite lors du traitement: {exc}",
            "action": "hold",
            "verdict": "hold",
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
    payload: Dict[str, Any]
    try:
        cls = _resolve_context_service_class(context_service_cls)
        if cls is not None:
            candidate = await cls().get_current_market_context()
            if isinstance(candidate, dict) and candidate:
                payload = dict(candidate)
            else:
                payload = _collect_fallback_context(scope)
        else:
            payload = _collect_fallback_context(scope)
    except Exception:
        payload = _collect_fallback_context(scope)

    if isinstance(scope, dict) and scope.get("tickers"):
        payload["scope_tickers"] = _normalize_tickers(scope.get("tickers"))
    payload["daily_brief"] = _load_daily_brief_payload()
    payload["entry_points"] = _build_copilot_entry_points(scope)
    payload["copilot_start"] = _build_copilot_start_payload(
        daily_brief=payload.get("daily_brief"),
        entry_points=payload.get("entry_points"),
        scope=scope,
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
