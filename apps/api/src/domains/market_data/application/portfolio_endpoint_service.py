"""Reusable service entrypoints for portfolio API routes."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

try:
    from services.service_standard import (  # type: ignore
        append_source_tag,
        ensure_decision_contract,
        service_response_with_metadata,
        utc_now_iso,
    )
except Exception:  # pragma: no cover
    from platform.legacy.services.service_standard import (  # type: ignore
        append_source_tag,
        ensure_decision_contract,
        service_response_with_metadata,
        utc_now_iso,
    )


PortfolioServiceGetter = Callable[[], Any]


def _filters_applied(
    *,
    portfolio_id: str,
    benchmark: str,
    start_date: Optional[str],
    end_date: Optional[str],
) -> Dict[str, Any]:
    return {
        "portfolio_id": portfolio_id,
        "benchmark": benchmark,
        "start_date": start_date,
        "end_date": end_date,
    }


def _serialize_profile(profile: Any) -> Dict[str, Any]:
    if isinstance(profile, dict):
        return dict(profile)

    model_dump = getattr(profile, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return dumped

    raise TypeError("Portfolio risk profile must serialize to a dict payload.")


def _normalize_source_tags(payload: Dict[str, Any]) -> list[str]:
    source = payload.get("source")
    if isinstance(source, list):
        return [str(item).strip() for item in source if str(item).strip()]
    return []


def _resolve_risk_profile_degradation(payload: Dict[str, Any]) -> tuple[Optional[str], str]:
    source_tags = _normalize_source_tags(payload)

    if "portfolio_risk_profile_service_fallback" in source_tags:
        return "service_fallback", "degraded"
    if "portfolio_risk_profile_fallback" in source_tags:
        return "metrics_unavailable", "degraded"
    if "portfolio_risk_profile_composition_only" in source_tags:
        return "composition_only", "degraded"
    return None, "ok"


def _fallback_payload(
    *,
    portfolio_id: str,
    benchmark: str,
    start_date: Optional[str],
    end_date: Optional[str],
    error: Exception,
) -> Dict[str, Any]:
    now_iso = utc_now_iso()
    payload = {
        "portfolio": {
            "id": portfolio_id,
            "name": "",
            "description": "",
            "tickers": [],
            "tickers_count": 0,
            "updated_at": None,
            "state": {},
        },
        "benchmark": benchmark,
        "weights": {},
        "metrics": {},
        "risk_profile": "balanced",
        "risk_level": "medium",
        "risk": {
            "level": "medium",
            "caveat": "Portfolio risk profile unavailable; returned service fallback.",
        },
        "why": [
            "The portfolio risk service failed before live metrics could be assembled."
        ],
        "warnings": [
            "Portfolio risk profile unavailable; returned a never-empty fallback payload."
        ],
        "filters_applied": _filters_applied(
            portfolio_id=portfolio_id,
            benchmark=benchmark,
            start_date=start_date,
            end_date=end_date,
        ),
        "stats": {
            "tickers_count": 0,
            "equal_weight_assumption": True,
            "weights_source": "unavailable",
            "has_live_metrics": False,
            "non_null_metrics": 0,
        },
        "confidence": 0.35,
        "generated_at": now_iso,
        "last_update": now_iso,
        "fallback_used": "service_fallback",
        "source": [
            "portfolio_risk_profile_service",
            "portfolio_risk_profile_service_fallback",
        ],
        "error": str(error),
        "message": "Portfolio risk profile unavailable; fallback returned.",
    }
    ensure_decision_contract(
        payload,
        default_source="portfolio_risk_profile_service",
        verdict=payload.get("verdict"),
        confidence=payload.get("confidence"),
        why=payload.get("why"),
        risk_level=payload.get("risk_level"),
        risk_caveat=payload.get("risk", {}).get("caveat"),
        freshness=now_iso,
    )
    return service_response_with_metadata(
        payload,
        default_source="portfolio_risk_profile_service",
        freshness=now_iso,
        status="degraded",
        error=str(error),
    )


def get_portfolio_risk_profile_payload(
    *,
    portfolio_id: str,
    benchmark: str,
    start_date: Optional[str],
    end_date: Optional[str],
    get_portfolio_service_fn: PortfolioServiceGetter,
) -> Optional[Dict[str, Any]]:
    """Build a stable portfolio risk-profile response envelope for the route."""
    try:
        service = get_portfolio_service_fn()
        risk_profile = service.get_risk_profile(
            portfolio_id,
            benchmark=benchmark,
            start_date=start_date,
            end_date=end_date,
        )
        if risk_profile is None:
            return None

        payload = _serialize_profile(risk_profile)
        payload.setdefault(
            "filters_applied",
            _filters_applied(
                portfolio_id=portfolio_id,
                benchmark=benchmark,
                start_date=start_date,
                end_date=end_date,
            ),
        )
        payload.setdefault("stats", {})
        payload.setdefault("warnings", [])
        payload.setdefault("generated_at", utc_now_iso())
        payload.setdefault(
            "last_update",
            payload.get("freshness") or payload.get("generated_at"),
        )

        append_source_tag(
            payload,
            "portfolio_risk_profile_service",
            default_source="portfolio_risk_profile_service",
        )
        ensure_decision_contract(
            payload,
            default_source="portfolio_risk_profile_service",
            verdict=payload.get("verdict"),
            confidence=payload.get("confidence"),
            why=payload.get("why"),
            risk_level=payload.get("risk_level")
            or (
                payload.get("risk", {}).get("level")
                if isinstance(payload.get("risk"), dict)
                else None
            ),
            risk_caveat=(
                payload.get("risk", {}).get("caveat")
                if isinstance(payload.get("risk"), dict)
                else None
            ),
            freshness=payload.get("generated_at"),
        )
        fallback_used, response_status = _resolve_risk_profile_degradation(payload)
        if fallback_used and not payload.get("fallback_used"):
            payload["fallback_used"] = fallback_used
        return service_response_with_metadata(
            payload,
            default_source="portfolio_risk_profile_service",
            freshness=payload.get("generated_at"),
            status=response_status,
            error=payload.get("error"),
        )
    except Exception as exc:
        return _fallback_payload(
            portfolio_id=portfolio_id,
            benchmark=benchmark,
            start_date=start_date,
            end_date=end_date,
            error=exc,
        )
