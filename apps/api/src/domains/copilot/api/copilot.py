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

from datetime import datetime, timezone
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

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


router = APIRouter(tags=["copilot"])


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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


def _normalize_scope(
    tickers: Optional[List[str]],
) -> Optional[Dict[str, List[str]]]:
    normalized: List[str] = []
    for item in tickers or []:
        ticker = str(item or "").strip().upper()
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
) -> Dict[str, Any]:
    resolved_start = dict(start_payload) if isinstance(start_payload, dict) else {}
    brief_of_day = (
        dict(resolved_start.get("brief_of_day"))
        if isinstance(resolved_start.get("brief_of_day"), dict)
        else {}
    )
    ask_items = [
        dict(item) for item in resolved_start.get("ask", []) if isinstance(item, dict)
    ]
    open_items = [
        dict(item) for item in resolved_start.get("open", []) if isinstance(item, dict)
    ]
    generated_at = (
        str(brief_of_day.get("freshness") or brief_of_day.get("generated_at") or "").strip()
        or _utc_now_iso()
    )
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
        "filters_applied": {"tickers": list((scope or {}).get("tickers") or [])},
        "stats": {
            "ask_count": len(ask_items),
            "open_count": len(open_items),
        },
        "warnings": [],
    }
    if note:
        payload["note"] = note
    if (scope or {}).get("tickers"):
        payload["scope_tickers"] = list((scope or {}).get("tickers") or [])
    if isinstance(context_influence, dict) and context_influence:
        payload["context_influence"] = dict(context_influence)
    if isinstance(portfolio_context, dict) and portfolio_context:
        payload["portfolio_context"] = dict(portfolio_context)
    return payload


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


@router.post("/copilot/ask")
async def copilot_ask(req: CopilotAskRequest):
    payload = await copilot_service.build_ask_payload(
        question=req.question,
        context_years=req.context_years,
        scope=req.scope,
        tickers=req.tickers,
        max_sources=req.max_sources,
    )
    return {"ok": True, "data": _normalize_ask_payload(payload)}


@router.get("/copilot/history")
async def copilot_history(limit: int = 20):
    return {"ok": True, "data": copilot_service.build_history_payload(limit=limit)}


@router.get("/copilot/context")
async def copilot_context(
    tickers: Optional[List[str]] = Query(None, description="Starter scope tickers"),
):
    scope = _normalize_scope(tickers)

    try:
        payload = await copilot_service.build_context_payload(
            context_service_cls=ContextService,
            scope=scope,
        )
        if isinstance(payload, dict) and payload.get("regime") == "fallback":
            payload.setdefault("note", "Market context service temporarily unavailable.")
        return {"ok": True, "data": payload}
    except Exception:
        daily_brief = copilot_service._load_daily_brief_payload()
        entry_points = copilot_service._build_copilot_entry_points(scope)
        build_start_payload = getattr(
            copilot_service,
            "_build_copilot_start_payload",
            None,
        ) or getattr(copilot_service, "_legacy_copilot_start_payload", None)

        fallback: Dict[str, Any] = {
            "note": "Market context service temporarily unavailable.",
            "daily_brief": daily_brief,
            "entry_points": entry_points,
        }
        if isinstance(scope, dict) and scope.get("tickers"):
            fallback["scope_tickers"] = list(scope.get("tickers") or [])
        if callable(build_start_payload):
            fallback["copilot_start"] = build_start_payload(
                daily_brief=daily_brief,
                entry_points=entry_points,
                scope=scope,
            )
        return {"ok": True, "data": fallback}


@router.get("/copilot/start")
async def copilot_start(
    tickers: Optional[List[str]] = Query(None, description="Starter scope tickers"),
):
    scope = _normalize_scope(tickers)

    try:
        payload = await copilot_service.build_context_payload(
            context_service_cls=ContextService,
            scope=scope,
        )
        effective_scope = _resolve_effective_scope(scope, payload)
        note = None
        if isinstance(payload, dict) and payload.get("regime") == "fallback":
            note = "Market context service temporarily unavailable."

        start_payload = payload.get("copilot_start") if isinstance(payload, dict) else None
        if not isinstance(start_payload, dict) or not start_payload:
            start_payload = copilot_service._build_copilot_start_payload(
                daily_brief=payload.get("daily_brief") if isinstance(payload, dict) else None,
                entry_points=payload.get("entry_points") if isinstance(payload, dict) else None,
                scope=effective_scope,
            )
        return {
            "ok": True,
            "data": _build_start_response(
                start_payload,
                scope=effective_scope,
                note=note,
                context_influence=payload.get("context_influence") if isinstance(payload, dict) else None,
                portfolio_context=payload.get("portfolio_context") if isinstance(payload, dict) else None,
            ),
        }
    except Exception:
        daily_brief = copilot_service._load_daily_brief_payload()
        entry_points = copilot_service._build_copilot_entry_points(scope)
        build_start_payload = getattr(
            copilot_service,
            "_build_copilot_start_payload",
            None,
        ) or getattr(copilot_service, "_legacy_copilot_start_payload", None)

        fallback_start: Dict[str, Any]
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

        return {
            "ok": True,
            "data": _build_start_response(
                fallback_start,
                scope=scope,
                note="Market context service temporarily unavailable.",
                context_influence=fallback.get("context_influence"),
                portfolio_context=fallback.get("portfolio_context"),
            ),
        }


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
