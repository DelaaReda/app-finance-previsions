"""
Copilot endpoints expected by the frontend.
Implements minimal, never-empty endpoints backed by existing services when possible.
 - POST /api/copilot/ask
 - GET  /api/copilot/history
 - GET  /api/copilot/context
 - GET  /api/copilot/start
 - POST /api/copilot/reports
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from datetime import datetime, timezone
from annotated_types import Ge, Gt
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from typing_extensions import Annotated

try:
    from api.templates.judge_like_endpoint import (
        append_source_tag,
        compute_singleflight,
        response_cache_get,
        response_cache_set,
        stable_cache_key,
    )
except Exception:  # pragma: no cover
    try:
        from src.api.templates.judge_like_endpoint import (  # type: ignore
            append_source_tag,
            compute_singleflight,
            response_cache_get,
            response_cache_set,
            stable_cache_key,
        )
    except Exception:  # pragma: no cover
        append_source_tag = None  # type: ignore
        compute_singleflight = None  # type: ignore
        response_cache_get = None  # type: ignore
        response_cache_set = None  # type: ignore
        stable_cache_key = None  # type: ignore

try:
    from domains.copilot.application.context_service import ContextService
except Exception:  # pragma: no cover
    try:
        from services.context_service import ContextService  # type: ignore
    except Exception:
        ContextService = None  # type: ignore

try:
    from domains.copilot.application import copilot_service
except Exception:  # pragma: no cover
    try:
        from services import copilot_service  # type: ignore
    except Exception:
        from src.services import copilot_service  # type: ignore

try:
    from storage import io as storage_io
except Exception:  # pragma: no cover
    storage_io = None  # type: ignore


router = APIRouter(tags=["copilot"])
COPILOT_START_CACHE_TTL_SECONDS = max(
    0, int(os.getenv("COPILOT_START_CACHE_TTL_SECONDS", "30") or "30")
)
COPILOT_START_CACHE_MAX_ENTRIES = max(
    1, int(os.getenv("COPILOT_START_CACHE_MAX_ENTRIES", "32") or "32")
)
_COPILOT_START_CACHE: Dict[str, Dict[str, Any]] = {}
_COPILOT_START_INFLIGHT: Dict[str, asyncio.Task] = {}
_COPILOT_START_INFLIGHT_LOCK = asyncio.Lock()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _cache_now_epoch() -> float:
    return datetime.now(timezone.utc).timestamp()


def _normalize_string_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    token = str(value or "").strip()
    return [token] if token else []


def _normalize_memo_why(payload: Dict[str, Any]) -> List[str]:
    why = payload.get("why")
    if isinstance(why, list):
        normalized = [str(item).strip() for item in why if str(item).strip()]
        if normalized:
            return normalized
    if isinstance(why, str) and why.strip():
        return [why.strip()]

    reasoning = payload.get("reasoning")
    if isinstance(reasoning, list):
        normalized = [str(item).strip() for item in reasoning if str(item).strip()]
        if normalized:
            return normalized
    if isinstance(reasoning, str) and reasoning.strip():
        return [reasoning.strip()]

    answer = str(payload.get("answer") or "").strip()
    return [answer] if answer else []


def _normalize_memo_risks(payload: Dict[str, Any]) -> List[str]:
    risks = payload.get("risks")
    if isinstance(risks, list):
        normalized = [str(item).strip() for item in risks if str(item).strip()]
        if normalized:
            return normalized
    if isinstance(risks, str) and risks.strip():
        return [risks.strip()]

    risk = payload.get("risk")
    if isinstance(risk, dict):
        items: List[str] = []
        level = str(risk.get("level") or payload.get("risk_level") or "").strip()
        caveat = str(risk.get("caveat") or payload.get("risk_caveat") or "").strip()
        if level:
            items.append(level)
        if caveat:
            items.append(caveat)
        if items:
            return items

    risk_caveat = str(payload.get("risk_caveat") or "").strip()
    return [risk_caveat] if risk_caveat else []


def _normalize_memo_sources(payload: Dict[str, Any]) -> List[Any]:
    sources = payload.get("sources")
    if isinstance(sources, list) and sources:
        return list(sources)
    source = payload.get("source")
    if isinstance(source, list) and source:
        return list(source)
    token = str(source or "").strip()
    return [token] if token else []


def _normalize_ask_payload(payload: Any) -> Dict[str, Any]:
    return copilot_service.normalize_ask_payload_contract(payload)


def _normalized_action_target(
    target: str,
    kind: str,
    namespace: Optional[str],
) -> Optional[str]:
    if not namespace:
        return None

    namespace_slug = str(namespace).strip().strip("/")
    namespace_path = f"/{namespace_slug}"
    if not namespace_path or namespace_path == "/":
        return None

    normalized_kind = str(kind or "").strip().lower()
    normalized_target = str(target or "").strip().lower()
    if not normalized_target:
        if normalized_kind == "ask":
            return f"{namespace_path}/ask"
        if normalized_kind == "open":
            return namespace_path
        return None

    if not normalized_target.startswith("/"):
        normalized_target = f"/{normalized_target}"

    if normalized_target.startswith(f"{namespace_path}/") or normalized_target in {
        namespace_path,
        f"{namespace_path}/",
    }:
        return target.strip()

    if normalized_target in {"/copilot", "copilot", "/copilot/", "copilot/"}:
        if normalized_kind == "ask":
            return f"{namespace_path}/ask"
        return namespace_path

    if normalized_target.startswith("/copilot/") or normalized_target.startswith("copilot/"):
        normalized = normalized_target.lstrip("/")
        tail = normalized[len("copilot/") :].strip("/")
        if not tail:
            if normalized_kind == "ask":
                return f"{namespace_path}/ask"
            if normalized_kind == "open":
                return namespace_path
            return None
        if tail == "ask":
            return f"{namespace_path}/ask"
        if normalized_kind in {"ask", "open"}:
            return f"{namespace_path}/{tail}"
        return None

    if normalized_kind == "ask" and normalized_target in {"/copilot/ask", "copilot/ask"}:
        return f"{namespace_path}/ask"

    if normalized_kind == "open" and normalized_target in {"/copilot", "copilot", "/copilot/", "copilot/"}:
        return namespace_path

    return None


def _rewrite_namespace_targets(payload: Any, namespace: Optional[str]) -> Any:
    if namespace is None:
        return payload

    if not isinstance(payload, dict):
        return payload

    rewritten: Dict[str, Any] = dict(payload)
    for key in ("ask", "open"):
        items = rewritten.get(key)
        if not isinstance(items, list):
            continue
        updated_items = []
        for item in items:
            if not isinstance(item, dict):
                updated_items.append(item)
                continue

            resolved_kind = str(item.get("kind") or key)
            target = item.get("target")
            mapped = _normalized_action_target(
                str(target if target is not None else ""),
                resolved_kind,
                namespace,
            )
            if mapped:
                item = dict(item)
                item["target"] = mapped
            updated_items.append(item)
        rewritten[key] = updated_items
    return rewritten


def _rewrite_namespace_entry_points(payload: Any, namespace: Optional[str]) -> Any:
    if namespace is None:
        return payload

    if not isinstance(payload, list):
        return payload

    rewritten: List[Any] = []
    for item in payload:
        if not isinstance(item, dict):
            rewritten.append(item)
            continue

        resolved_kind = str(item.get("kind") or "").strip().lower()
        target = item.get("target")
        mapped = _normalized_action_target(
            str(target if target is not None else ""),
            resolved_kind,
            namespace,
        )
        if not mapped:
            rewritten.append(item)
            continue

        updated = dict(item)
        updated["target"] = mapped
        rewritten.append(updated)

    return rewritten


def _normalize_scope(
    tickers: Optional[List[str]],
) -> Optional[Dict[str, List[str]]]:
    normalized: List[str] = []
    for item in tickers or []:
        for raw_token in str(item or "").split(","):
            ticker = raw_token.strip().upper()
            if ticker and ticker not in normalized:
                normalized.append(ticker)
    return {"tickers": normalized} if normalized else None


def _build_start_response(
    start_payload: Optional[Dict[str, Any]],
    *,
    scope: Optional[Dict[str, List[str]]] = None,
    note: Optional[str] = None,
    context_influence: Optional[Dict[str, Any]] = None,
    portfolio_context: Optional[Dict[str, Any]] = None,
    regime_detection: Optional[Dict[str, Any]] = None,
    allocation_drift_alerts: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    resolved_start = dict(start_payload) if isinstance(start_payload, dict) else {}
    brief_of_day = (
        dict(resolved_start.get("brief_of_day"))
        if isinstance(resolved_start.get("brief_of_day"), dict)
        else {}
    )
    resolved_scope_tickers = [
        str(ticker).strip().upper()
        for ticker in ((scope or {}).get("tickers") or [])
        if str(ticker).strip()
    ]
    resolved_scope_tickers = list(dict.fromkeys(resolved_scope_tickers))
    ask_items = [
        dict(item) for item in resolved_start.get("ask", []) if isinstance(item, dict)
    ]
    open_items = [
        dict(item) for item in resolved_start.get("open", []) if isinstance(item, dict)
    ]

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
    generated_at = (
        str(brief_of_day.get("freshness") or brief_of_day.get("generated_at") or "").strip()
        or _utc_now_iso()
    )
    if isinstance(allocation_drift_alerts, dict) and allocation_drift_alerts:
        brief_of_day = dict(brief_of_day)
        brief_of_day["allocation_drift_alerts"] = dict(allocation_drift_alerts)
    source = brief_of_day.get("sources")
    if not isinstance(source, list):
        source = brief_of_day.get("source")
    normalized_source = [
        str(item).strip()
        for item in (source if isinstance(source, list) else [])
        if str(item).strip()
    ]
    if "copilot_start_route" not in normalized_source:
        normalized_source.append("copilot_start_route")

    payload: Dict[str, Any] = {
        "brief_of_day": brief_of_day,
        "ask": ask_items,
        "open": open_items,
        "generated_at": generated_at,
        "freshness": generated_at,
        "source": normalized_source or ["copilot_start_route"],
        "sources": normalized_source or ["copilot_start_route"],
        "filters_applied": {"tickers": list(resolved_scope_tickers)},
        "stats": {
            "ask_count": len(ask_items),
            "open_count": len(open_items),
        },
        "warnings": [],
    }
    if note:
        payload["note"] = note
    if resolved_scope_tickers:
        payload["scope_tickers"] = list(resolved_scope_tickers)
    if isinstance(context_influence, dict) and context_influence:
        payload["context_influence"] = dict(context_influence)
    if isinstance(portfolio_context, dict) and portfolio_context:
        payload["portfolio_context"] = dict(portfolio_context)
    if isinstance(regime_detection, dict) and regime_detection:
        payload["regime_detection"] = dict(regime_detection)
    if isinstance(allocation_drift_alerts, dict) and allocation_drift_alerts:
        payload["allocation_drift_alerts"] = dict(allocation_drift_alerts)
    return payload


def _brief_signature_from_payload(payload: Optional[Dict[str, Any]]) -> str:
    if not isinstance(payload, dict):
        return "brief_missing"

    sanitized: Dict[str, Any] = {}
    for key in (
        "summary",
        "market_sentiment",
        "top_signals",
        "top_risks",
        "macro_signals",
        "sector_rotation",
        "source",
        "sources",
        "event_timing",
    ):
        if key in payload and payload[key] is not None:
            sanitized[key] = payload[key]

    if not sanitized:
        return "brief_missing"

    return hashlib.sha1(
        json.dumps(sanitized, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:12]


def _copilot_start_cache_key(
    *,
    tickers: Optional[List[str]],
    namespace: Optional[str],
) -> Optional[str]:
    try:
        if hasattr(copilot_service, "_load_daily_brief_payload"):
            daily_payload = copilot_service._load_daily_brief_payload()
            payload_signature = _brief_signature_from_payload(daily_payload)
        elif storage_io is not None:
            snapshot = storage_io.load_json("brief_daily")
            if not isinstance(snapshot, dict):
                snapshot = storage_io.load_json("brief_weekly")
            if isinstance(snapshot, dict):
                raw_payload = snapshot.get("data") if isinstance(snapshot.get("data"), dict) else snapshot
                raw_snapshot = raw_payload.get("daily") if isinstance(raw_payload, dict) and isinstance(raw_payload.get("daily"), dict) else raw_payload
                payload_signature = _brief_signature_from_payload(raw_snapshot)
            else:
                payload_signature = "brief_fallback"
        else:
            payload_signature = "storage_missing"
    except Exception as exc:  # pragma: no cover
        payload_signature = f"brief_error:{type(exc).__name__}"

    if not callable(stable_cache_key):
        return None
    return stable_cache_key(
        "copilot_start_v1",
        {
            "brief_signature": payload_signature,
            "tickers": list(tickers or []),
            "namespace": str(namespace or "").strip(),
        },
    )


def _copilot_start_cached_payload(
    cache_key: Optional[str],
) -> Optional[Dict[str, Any]]:
    if not cache_key:
        return None
    if not callable(response_cache_get):
        cached = _COPILOT_START_CACHE.get(cache_key)
        if not isinstance(cached, dict):
            return None
        payload = cached.get("payload")
        stored_at = float(cached.get("stored_at") or 0.0)
        age_seconds = max(0.0, _cache_now_epoch() - stored_at) if stored_at else 0.0
        if COPILOT_START_CACHE_TTL_SECONDS > 0 and age_seconds > COPILOT_START_CACHE_TTL_SECONDS:
            _COPILOT_START_CACHE.pop(cache_key, None)
            return None
        if not isinstance(payload, dict):
            return None
        response = dict(payload)
        response["cache"] = {
            "hit": True,
            "age_seconds": age_seconds,
            "ttl_seconds": COPILOT_START_CACHE_TTL_SECONDS,
        }
        source = response.get("source") if isinstance(response.get("source"), list) else []
        response["source"] = list(source) if source else ["copilot_start_route"]
        if "copilot_start_cache_hit" not in response["source"]:
            response["source"].append("copilot_start_cache_hit")
        return response
    return response_cache_get(
        _COPILOT_START_CACHE,
        cache_key,
        ttl_seconds=COPILOT_START_CACHE_TTL_SECONDS,
        hit_source_tag="copilot_start_cache_hit",
        default_source="copilot_start_route",
    )


def _copilot_start_store_payload(
    cache_key: Optional[str],
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    response = dict(payload)
    cache_meta = response.get("cache") if isinstance(response.get("cache"), dict) else {}
    cache_meta.update({"hit": False, "age_seconds": 0.0, "ttl_seconds": COPILOT_START_CACHE_TTL_SECONDS})
    response["cache"] = cache_meta
    if callable(append_source_tag):
        append_source_tag(response, "copilot_start_route", default_source="copilot_start_route")
    elif not isinstance(response.get("source"), list):
        response["source"] = ["copilot_start_route"]
    if cache_key and callable(response_cache_set):
        response_cache_set(
            _COPILOT_START_CACHE,
            cache_key,
            response,
            max_entries=COPILOT_START_CACHE_MAX_ENTRIES,
        )
    elif cache_key:
        cached_payload = dict(response)
        _COPILOT_START_CACHE[cache_key] = {
            "payload": cached_payload,
            "stored_at": _cache_now_epoch(),
        }
        while len(_COPILOT_START_CACHE) > COPILOT_START_CACHE_MAX_ENTRIES:
            oldest_key = next(iter(_COPILOT_START_CACHE))
            if oldest_key == cache_key and len(_COPILOT_START_CACHE) == 1:
                break
            _COPILOT_START_CACHE.pop(oldest_key, None)
    return response


async def _copilot_start_compute_singleflight(
    cache_key: str,
    compute_fn,
):
    if callable(compute_singleflight):
        return await compute_singleflight(
            _COPILOT_START_INFLIGHT,
            _COPILOT_START_INFLIGHT_LOCK,
            cache_key,
            compute_fn,
        )

    async with _COPILOT_START_INFLIGHT_LOCK:
        inflight_task = _COPILOT_START_INFLIGHT.get(cache_key)
        if inflight_task is None:
            inflight_task = asyncio.create_task(compute_fn())
            _COPILOT_START_INFLIGHT[cache_key] = inflight_task
            created = True
        else:
            created = False

    try:
        payload = await inflight_task
        return payload, created
    finally:
        if created:
            async with _COPILOT_START_INFLIGHT_LOCK:
                current_task = _COPILOT_START_INFLIGHT.get(cache_key)
                if current_task is inflight_task:
                    _COPILOT_START_INFLIGHT.pop(cache_key, None)


def _resolve_effective_scope(
    requested_scope: Optional[Dict[str, List[str]]],
    payload: Optional[Dict[str, Any]],
) -> Optional[Dict[str, List[str]]]:
    payload_scope = (
        _normalize_scope(payload.get("scope_tickers"))
        if isinstance(payload, dict)
        else None
    )
    return payload_scope or requested_scope


class CopilotAskRequest(BaseModel):
    question: str
    context_years: Optional[int] = 5
    scope: Optional[Dict[str, Any]] = None
    tickers: Optional[List[str]] = None
    max_sources: Optional[int] = 5
    conversation_id: Optional[str] = None  # BATCH-73-DEV-02: Follow-up support


def _build_ask_fallback_payload(
    req: CopilotAskRequest,
    *,
    error: Exception,
) -> Dict[str, Any]:
    fallback_payload = {
        "question": req.question,
        "answer": "Copilot ask is temporarily unavailable.",
        "action": "hold",
        "verdict": "hold",
        "horizon": "1w",
        "why": [
            "The copilot ask endpoint hit an internal error and returned a safety fallback.",
        ],
        "risk": {
            "level": "high",
            "caveat": "Retry after the copilot ask dependency recovers.",
        },
        "risk_level": "high",
        "risk_caveat": "Retry after the copilot ask dependency recovers.",
        "sources": [],
        "citations": [],
        "confidence": 0.0,
        "generated_at": _utc_now_iso(),
        "sources_count": 0,
        "quality_status": "error",
        "requirements_met": {
            "min_sources_2": False,
            "quality_threshold": False,
        },
        "source": ["copilot_ask_route", "copilot_ask_fallback"],
        "note": "Copilot ask service temporarily unavailable.",
        "error": str(error),
    }
    if req.tickers:
        fallback_payload["tickers"] = list(req.tickers)
    return _normalize_ask_payload(fallback_payload)


def _log_ask_response_decision(
    req: CopilotAskRequest,
    normalized: Dict[str, Any],
    conversation_id: Optional[str] = None,
) -> None:
    """
    Log copilot decision to immutable journal.

    BATCH-73-DEV-03: Links decisions to conversation threads when conversation_id is provided.
    This enables tracking decision history within conversation context.
    """
    from domains.copilot.application.decision_journal import log_copilot_decision

    verdict_raw = str(normalized.get("verdict") or normalized.get("action") or "hold").lower()
    verdict = "buy" if any(t in verdict_raw for t in ["buy", "achat", "long", "accumuler", "acheter"]) else \
              "sell" if any(t in verdict_raw for t in ["sell", "vendre", "short", "alléger", "sortir"]) else \
              "hold" if any(t in verdict_raw for t in ["hold", "maintenir", "conserver", "wait"]) else "hold"

    confidence = float(normalized.get("confidence") or 0.5)
    horizon = str(normalized.get("horizon") or "1w").lower()
    reasoning = normalized.get("why", [])
    if isinstance(reasoning, list) and reasoning:
        reasoning = reasoning[0]
    elif not isinstance(reasoning, str):
        reasoning = ""
    risk_level = str((normalized.get("risk") or {}).get("level") or normalized.get("risk_level") or "medium").lower()
    sources = normalized.get("sources") or normalized.get("citations") or []

    # BATCH-73-DEV-03: Include conversation_id in metadata for decision-conversation linking
    metadata = {"scope": req.scope, "context_years": req.context_years}
    if conversation_id:
        metadata["conversation_id"] = conversation_id

    log_copilot_decision(
        question=req.question,
        answer=str(normalized.get("answer") or ""),
        verdict=verdict,
        confidence=confidence,
        tickers=req.tickers,
        horizon=horizon if horizon in ("1d", "1w", "1m") else "1w",
        reasoning=reasoning,
        risk_level=risk_level if risk_level in ("low", "medium", "high", "critical") else "medium",
        sources=sources if isinstance(sources, list) else [],
        model="copilot_ask_route",
        metadata=metadata,
    )


@router.post("/copilot/ask")
async def copilot_ask(req: CopilotAskRequest):
    """
    Ask copilot a question.
    
    BATCH-73-DEV-02: Added conversation_id for follow-up questions.
    When conversation_id is provided:
    - User question is appended to conversation history
    - Assistant response is also appended
    - Follow-up context (tickers, recent messages) is injected
    """
    from domains.copilot.application.conversation_history import (
        append_message,
        get_follow_up_context,
    )

    conversation_id = req.conversation_id
    follow_up_context = None

    # BATCH-73-DEV-02: Get follow-up context if conversation_id provided
    if conversation_id:
        try:
            ctx_result = get_follow_up_context(conversation_id=conversation_id, max_history=5)
            if ctx_result.get("status") == "ok":
                follow_up_context = ctx_result
                # Enrich tickers from conversation context if not explicitly provided
                if not req.tickers and ctx_result.get("context", {}).get("tickers"):
                    req.tickers = ctx_result["context"]["tickers"]
        except Exception:
            # Non-blocking: conversation context failure should not break ask
            pass

    try:
        payload = await copilot_service.build_ask_payload(
            question=req.question,
            context_years=req.context_years,
            scope=req.scope,
            tickers=req.tickers,
            max_sources=req.max_sources,
        )
        normalized = _normalize_ask_payload(payload)

        # BATCH-73-DEV-03: Auto-log decision to journal with conversation_id linkage
        try:
            _log_ask_response_decision(req, normalized, conversation_id=conversation_id)
        except Exception as log_exc:
            pass

        # BATCH-73-DEV-02: Log conversation messages if conversation_id provided
        conversation_response_data = None
        if conversation_id:
            try:
                # Log user question
                append_message(
                    conversation_id=conversation_id,
                    role="user",
                    content=req.question,
                    metadata={"tickers": req.tickers, "scope": req.scope},
                )
                # Log assistant response
                append_result = append_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=normalized.get("answer", ""),
                    metadata={
                        "verdict": normalized.get("verdict"),
                        "confidence": normalized.get("confidence"),
                        "horizon": normalized.get("horizon"),
                        "tickers": req.tickers,
                    },
                )
                conversation_response_data = {
                    "conversation_id": conversation_id,
                    "message_id": append_result.get("message_id"),
                    "message_count": append_result.get("message_count"),
                }
            except Exception:
                # Non-blocking: conversation logging failure should not break response
                pass

        result = {"ok": True, "data": normalized}
        
        # BATCH-73-DEV-02: Include conversation metadata in response
        if conversation_response_data:
            result["data"]["conversation"] = conversation_response_data
        if follow_up_context:
            result["data"]["follow_up_context"] = {
                "conversation_id": conversation_id,
                "tickers": follow_up_context.get("context", {}).get("tickers"),
                "portfolio_id": follow_up_context.get("context", {}).get("portfolio_id"),
                "last_verdict": follow_up_context.get("last_verdict"),
                "last_confidence": follow_up_context.get("last_confidence"),
            }
        
        return result
        
    except Exception as exc:
        fallback_payload = _build_ask_fallback_payload(req, error=exc)
        try:
            _log_ask_response_decision(req, fallback_payload, conversation_id=conversation_id)
        except Exception:
            pass
        
        # BATCH-73-DEV-02: Still try to log error to conversation if available
        if conversation_id:
            try:
                append_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=f"Error: {str(exc)}",
                    metadata={"error": True},
                )
            except Exception:
                pass
        
        result = {"ok": True, "data": fallback_payload}
        if conversation_id:
            result["data"]["conversation"] = {"conversation_id": conversation_id, "error_logged": True}
        return result


@router.get("/copilot/history")
async def copilot_history(limit: int = 20):
    return {"ok": True, "data": copilot_service.build_history_payload(limit=limit)}


@router.get("/copilot/context")
async def copilot_context(
    tickers: Optional[List[str]] = Query(None, description="Starter scope tickers"),
    namespace: Optional[str] = None,
):
    scope = _normalize_scope(tickers)

    try:
        payload = await copilot_service.build_context_payload(
            context_service_cls=ContextService,
            scope=scope,
        )
        if isinstance(payload, dict):
            entry_points = payload.get("entry_points")
            start_payload = payload.get("copilot_start")
            if isinstance(start_payload, dict) or isinstance(entry_points, list):
                payload = dict(payload)
            if isinstance(entry_points, list):
                payload["entry_points"] = _rewrite_namespace_entry_points(
                    entry_points,
                    namespace,
                )
            if isinstance(start_payload, dict):
                payload["copilot_start"] = _rewrite_namespace_targets(start_payload, namespace)
        if isinstance(payload, dict) and payload.get("regime") == "fallback":
            payload.setdefault("note", "Market context service temporarily unavailable.")
        return {"ok": True, "data": payload}
    except Exception:
        daily_brief = copilot_service._load_daily_brief_payload()
        entry_points = copilot_service._build_copilot_entry_points(scope, daily_brief)
        build_start_payload = getattr(
            copilot_service,
            "_build_copilot_start_payload",
            None,
        ) or getattr(copilot_service, "_legacy_copilot_start_payload", None)

        fallback: Dict[str, Any] = {
            "note": "Market context service temporarily unavailable.",
            "daily_brief": daily_brief,
            "entry_points": _rewrite_namespace_entry_points(entry_points, namespace),
        }
        if isinstance(scope, dict) and scope.get("tickers"):
            fallback["scope_tickers"] = list(scope.get("tickers") or [])
        if callable(build_start_payload):
            fallback["copilot_start"] = build_start_payload(
                daily_brief=daily_brief,
                entry_points=entry_points,
                scope=scope,
            )
            fallback["copilot_start"] = _rewrite_namespace_targets(
                fallback["copilot_start"],
                namespace,
            )
        return {"ok": True, "data": fallback}


@router.get("/copilot/start")
async def copilot_start(
    tickers: Optional[List[str]] = Query(None, description="Starter scope tickers"),
    namespace: Optional[str] = None,
    debug: bool = Query(False, description="Bypass route cache and return fresh payload"),
):
    scope = _normalize_scope(tickers)
    normalized_tickers = list((scope or {}).get("tickers") or [])
    cache_key = _copilot_start_cache_key(
        tickers=normalized_tickers,
        namespace=namespace,
    )

    if not debug:
        cached_payload = _copilot_start_cached_payload(cache_key)
        if isinstance(cached_payload, dict):
            return {"ok": True, "data": cached_payload}

    async def _compute_payload() -> Dict[str, Any]:
        try:
            payload = await copilot_service.build_context_payload(
                context_service_cls=ContextService,
                scope=scope,
            )
            effective_scope = _resolve_effective_scope(scope, payload)
            start_payload = (
                payload.get("copilot_start")
                if isinstance(payload, dict)
                else None
            )
            if isinstance(start_payload, dict):
                start_payload = _rewrite_namespace_targets(start_payload, namespace)
            note = None
            if isinstance(payload, dict) and payload.get("regime") == "fallback":
                note = "Market context service temporarily unavailable."

            if not isinstance(start_payload, dict) or not start_payload:
                start_payload = (
                    copilot_service._build_copilot_start_payload(
                        daily_brief=payload.get("daily_brief") if isinstance(payload, dict) else None,
                        entry_points=payload.get("entry_points") if isinstance(payload, dict) else None,
                        scope=effective_scope,
                    )
                    if isinstance(payload, dict)
                    else None
                )
                start_payload = _rewrite_namespace_targets(start_payload, namespace)

            return _build_start_response(
                start_payload,
                scope=effective_scope,
                note=note,
                context_influence=payload.get("context_influence") if isinstance(payload, dict) else None,
                portfolio_context=payload.get("portfolio_context") if isinstance(payload, dict) else None,
                regime_detection=payload.get("regime_detection") if isinstance(payload, dict) else None,
                allocation_drift_alerts=payload.get("allocation_drift_alerts") if isinstance(payload, dict) else None,
            )
        except Exception:
            daily_brief = copilot_service._load_daily_brief_payload()
            entry_points = copilot_service._build_copilot_entry_points(scope, daily_brief)
            build_start_payload = getattr(
                copilot_service,
                "_build_copilot_start_payload",
                None,
            ) or getattr(copilot_service, "_legacy_copilot_start_payload", None)

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
            fallback_start = _rewrite_namespace_targets(fallback_start, namespace)
            fallback_payload = {
                "context_influence": None,
                "portfolio_context": None,
                "regime_detection": None,
                "allocation_drift_alerts": None,
            }

            return _build_start_response(
                fallback_start,
                scope=scope,
                note="Market context service temporarily unavailable.",
                context_influence=fallback_payload.get("context_influence"),
                portfolio_context=fallback_payload.get("portfolio_context"),
                regime_detection=fallback_payload.get("regime_detection"),
                allocation_drift_alerts=fallback_payload.get("allocation_drift_alerts"),
            )

    if debug or not cache_key:
        return {"ok": True, "data": _copilot_start_store_payload(None if debug else cache_key, await _compute_payload())}

    payload, _ = await _copilot_start_compute_singleflight(cache_key, _compute_payload)
    cached_payload = _copilot_start_cached_payload(cache_key)
    if isinstance(cached_payload, dict):
        return {"ok": True, "data": cached_payload}
    return {"ok": True, "data": _copilot_start_store_payload(cache_key, payload)}


@router.get("/personal-finance/start")
async def personal_finance_start(
    tickers: Optional[List[str]] = Query(None, description="Starter scope tickers"),
):
    """Alias entrypoint for the personal finance copilot starter."""
    return await copilot_start(tickers=tickers, namespace="personal-finance")


@router.get("/personal-finance/context")
async def personal_finance_context(
    tickers: Optional[List[str]] = Query(None, description="Starter scope tickers"),
):
    """Alias entrypoint for the personal finance context view."""
    return await copilot_context(tickers=tickers, namespace="personal-finance")


@router.post("/personal-finance/ask")
async def personal_finance_ask(req: CopilotAskRequest):
    """Alias ask endpoint for the personal finance copilot."""
    return await copilot_ask(req)


class CopilotReportRequest(BaseModel):
    prompt: str
    filters: Optional[Dict[str, Any]] = None


@router.post("/copilot/reports")
async def copilot_reports(req: CopilotReportRequest):
    return {
        "ok": True,
        "data": copilot_service.build_report_payload(
            prompt=req.prompt,
            filters=req.filters,
        ),
    }


# Decision Journal Routes (BATCH-13-DEV-02)


class CopilotDecisionLogRequest(BaseModel):
    question: str
    answer: str
    verdict: str
    confidence: float
    tickers: Optional[List[str]] = None
    horizon: Optional[str] = "1d"
    reasoning: Optional[str] = None
    risk_level: Optional[str] = "medium"
    model: Optional[str] = None


@router.post("/copilot/decision-journal/log")
async def copilot_decision_journal_log(req: CopilotDecisionLogRequest):
    """Log one copilot decision to immutable journal."""
    from domains.copilot.application.decision_journal import log_copilot_decision

    result = log_copilot_decision(
        question=req.question,
        answer=req.answer,
        verdict=req.verdict,
        confidence=req.confidence,
        tickers=req.tickers,
        horizon=req.horizon or "1d",
        reasoning=req.reasoning,
        risk_level=req.risk_level or "medium",
        model=req.model or "unknown",
    )
    return {"ok": result.get("status") == "recorded", "data": result}


class CopilotOutcomeFeedbackRequest(BaseModel):
    decision_id: str
    horizon: str
    status: str
    actual_return: Optional[float] = None
    predicted_return: Optional[float] = None
    notes: Optional[str] = None


class CopilotPaperTradeExecuteRequest(BaseModel):
    decision_id: str
    ticker: str
    side: str
    quantity: Annotated[float, Gt(0)]
    reference_price: Annotated[float, Gt(0)]
    fee_bps: Annotated[float, Ge(0)] = 0.0
    slippage_bps: Annotated[float, Ge(0)] = 0.0
    market_price: Optional[Annotated[float, Gt(0)]] = None
    executed_at: Optional[str] = None
    notes: Optional[str] = None


@router.post("/copilot/decision-journal/outcomes")
async def copilot_decision_outcome_feedback(req: CopilotOutcomeFeedbackRequest):
    """Record outcome feedback for a decision."""
    from domains.copilot.application.decision_journal import record_outcome_feedback

    result = record_outcome_feedback(
        decision_id=req.decision_id,
        horizon=req.horizon,
        status=req.status,
        actual_return=req.actual_return,
        predicted_return=req.predicted_return,
        notes=req.notes,
    )
    return {"ok": result.get("status") == "recorded", "data": result}


@router.post("/copilot/paper-trades/execute")
async def copilot_paper_trade_execute(req: CopilotPaperTradeExecuteRequest):
    """Execute and journal one paper trade with fill assumptions."""
    from domains.copilot.application.decision_journal import execute_paper_trade

    result = execute_paper_trade(
        decision_id=req.decision_id,
        ticker=req.ticker,
        side=req.side,
        quantity=req.quantity,
        reference_price=req.reference_price,
        fee_bps=req.fee_bps or 0.0,
        slippage_bps=req.slippage_bps or 0.0,
        market_price=req.market_price,
        executed_at=req.executed_at,
        notes=req.notes,
    )
    return {"ok": result.get("status") == "recorded", "data": result}


@router.get("/copilot/decision-journal")
async def copilot_decision_journal_get(
    limit: int = Query(default=50, ge=1, le=500),
    tickers: Optional[List[str]] = Query(None, description="Filter by tickers"),
    horizon: Optional[str] = Query(None, description="Filter by horizon (1d/1w/1m)"),
    verdict: Optional[str] = Query(None, description="Filter by verdict (buy/sell/hold)"),
):
    """Retrieve decision journal entries."""
    from domains.copilot.application.decision_journal import get_decision_journal

    result = get_decision_journal(
        limit=limit,
        tickers=tickers,
        horizon=horizon,
        verdict=verdict,
    )
    return {"ok": True, "data": result}


@router.get("/copilot/decision-journal/outcomes")
async def copilot_outcome_feedback_get(
    decision_id: Optional[str] = Query(None, description="Filter by decision_id"),
    horizon: Optional[str] = Query(None, description="Filter by horizon"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(default=200, ge=1, le=5000),
):
    """Retrieve outcome feedback records."""
    from domains.copilot.application.decision_journal import get_outcome_feedback

    result = get_outcome_feedback(
        decision_id=decision_id,
        horizon=horizon,
        status=status,
        limit=limit,
    )
    return {"ok": True, "data": result}


@router.get("/copilot/decision-journal/metrics")
async def copilot_decision_journal_metrics():
    """Compute hit rate and calibration metrics."""
    from domains.copilot.application.decision_journal import compute_metrics

    result = compute_metrics()
    return {"ok": True, "data": result}


# Conversation History Routes (BATCH-73-DEV-02)


class CopilotConversationCreateRequest(BaseModel):
    first_question: str
    tickers: Optional[List[str]] = None
    scope: Optional[Dict[str, Any]] = None
    portfolio_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@router.post("/copilot/conversation/create")
async def copilot_conversation_create(req: CopilotConversationCreateRequest):
    """
    Create a new conversation thread.
    
    Returns conversation_id for follow-up questions.
    """
    from domains.copilot.application.conversation_history import create_conversation

    result = create_conversation(
        first_question=req.first_question,
        tickers=req.tickers,
        scope=req.scope,
        portfolio_id=req.portfolio_id,
        metadata=req.metadata,
    )
    return {"ok": result.get("status") == "created", "data": result}


@router.get("/copilot/conversation/{conversation_id}")
async def copilot_conversation_get(
    conversation_id: str,
    limit: Optional[int] = Query(None, description="Max messages to return"),
):
    """
    Retrieve a conversation thread by ID.
    
    Returns messages, context, and metadata.
    """
    from domains.copilot.application.conversation_history import get_conversation

    result = get_conversation(conversation_id=conversation_id, limit=limit)
    return {"ok": result.get("status") == "ok", "data": result}


@router.get("/copilot/conversations")
async def copilot_conversations_list(
    limit: int = Query(default=20, ge=1, le=100),
    tickers: Optional[List[str]] = Query(None, description="Filter by tickers"),
    portfolio_id: Optional[str] = Query(None, description="Filter by portfolio"),
):
    """
    List conversation threads.
    
    Returns summaries sorted by updated_at desc.
    """
    from domains.copilot.application.conversation_history import list_conversations

    result = list_conversations(limit=limit, tickers=tickers, portfolio_id=portfolio_id)
    return {"ok": True, "data": result}


@router.delete("/copilot/conversation/{conversation_id}")
async def copilot_conversation_delete(conversation_id: str):
    """
    Delete a conversation thread.
    """
    from domains.copilot.application.conversation_history import delete_conversation

    result = delete_conversation(conversation_id=conversation_id)
    return {"ok": result.get("status") == "deleted", "data": result}


@router.get("/copilot/conversation/{conversation_id}/followup")
async def copilot_conversation_followup_context(
    conversation_id: str,
    max_history: int = Query(default=5, ge=1, le=20),
):
    """
    Get context for follow-up question.
    
    Returns recent messages and inherited context (tickers, portfolio).
    """
    from domains.copilot.application.conversation_history import get_follow_up_context

    result = get_follow_up_context(conversation_id=conversation_id, max_history=max_history)
    return {"ok": result.get("status") == "ok", "data": result}


# Personal Finance Conversation Aliases (BATCH-73-DEV-02)


@router.post("/personal-finance/conversation/create")
async def personal_finance_conversation_create(req: CopilotConversationCreateRequest):
    """Alias for personal finance namespace."""
    return await copilot_conversation_create(req)


@router.get("/personal-finance/conversation/{conversation_id}")
async def personal_finance_conversation_get(conversation_id: str, limit: Optional[int] = None):
    """Alias for personal finance namespace."""
    return await copilot_conversation_get(conversation_id, limit)


@router.get("/personal-finance/conversations")
async def personal_finance_conversations_list(
    limit: int = 20,
    tickers: Optional[List[str]] = None,
    portfolio_id: Optional[str] = None,
):
    """Alias for personal finance namespace."""
    return await copilot_conversations_list(limit, tickers, portfolio_id)
