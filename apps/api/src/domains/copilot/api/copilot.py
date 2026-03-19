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
from annotated_types import Ge, Gt
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from typing_extensions import Annotated

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
    regime_detection: Optional[Dict[str, Any]] = None,
    allocation_drift_alerts: Optional[Dict[str, Any]] = None,
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
    if isinstance(regime_detection, dict) and regime_detection:
        payload["regime_detection"] = dict(regime_detection)
    if isinstance(allocation_drift_alerts, dict) and allocation_drift_alerts:
        payload["allocation_drift_alerts"] = dict(allocation_drift_alerts)
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
    namespace: Optional[str] = None,
):
    scope = _normalize_scope(tickers)

    try:
        payload = await copilot_service.build_context_payload(
            context_service_cls=ContextService,
            scope=scope,
        )
        if isinstance(payload, dict):
            start_payload = payload.get("copilot_start")
            if isinstance(start_payload, dict):
                payload = dict(payload)
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
            fallback["copilot_start"] = _rewrite_namespace_targets(
                fallback["copilot_start"],
                namespace,
            )
        return {"ok": True, "data": fallback}


@router.get("/copilot/start")
async def copilot_start(
    tickers: Optional[List[str]] = Query(None, description="Starter scope tickers"),
    namespace: Optional[str] = None,
):
    scope = _normalize_scope(tickers)

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
        return {
            "ok": True,
            "data": _build_start_response(
                start_payload,
                scope=effective_scope,
                note=note,
                context_influence=payload.get("context_influence") if isinstance(payload, dict) else None,
                portfolio_context=payload.get("portfolio_context") if isinstance(payload, dict) else None,
                regime_detection=payload.get("regime_detection") if isinstance(payload, dict) else None,
                allocation_drift_alerts=payload.get("allocation_drift_alerts") if isinstance(payload, dict) else None,
            ),
        }
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

        return {
            "ok": True,
            "data": _build_start_response(
                fallback_start,
                scope=scope,
                note="Market context service temporarily unavailable.",
                context_influence=fallback_payload.get("context_influence"),
                portfolio_context=fallback_payload.get("portfolio_context"),
                regime_detection=fallback_payload.get("regime_detection"),
                allocation_drift_alerts=fallback_payload.get("allocation_drift_alerts"),
            ),
        }


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
