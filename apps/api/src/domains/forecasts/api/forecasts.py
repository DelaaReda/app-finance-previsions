"""Forecasts API routes (orchestrator-only).

Business logic lives in `services/forecasts_service.py`.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

try:
    from src.core.response import ok
except Exception:  # pragma: no cover
    def ok(data):
        return {"ok": True, "data": data}

try:
    from platform.edge.contracts import edge_degraded, edge_enabled, edge_ok
    from platform.edge.critical_endpoints import (
        forecasts_degraded as edge_forecasts_degraded,
        forecasts_ok as edge_forecasts_ok,
    )
except Exception:  # pragma: no cover
    edge_ok = lambda data, **_: {"ok": True, "data": data}  # type: ignore
    edge_degraded = (  # type: ignore
        lambda data, code, message, detail=None, **_: {
            "ok": True,
            "status": "degraded",
            "data": data,
            "error": {"code": code, "message": message, "detail": detail},
            "meta": {"source": ["legacy_fallback"], "fallback": True},
        }
    )
    edge_enabled = lambda *_args, **_kwargs: False  # type: ignore
    edge_forecasts_ok = lambda data, **_: {"ok": True, "data": data}  # type: ignore
    edge_forecasts_degraded = lambda data, detail=None, **_: {"ok": True, "data": data}  # type: ignore

from storage.io import load_json
import logging as _logging

try:
    from services.service_standard import ensure_decision_contract, utc_now_iso  # type: ignore
except Exception:  # pragma: no cover
    try:
        from platform.legacy.services.service_standard import (  # type: ignore
            ensure_decision_contract,
            utc_now_iso,
        )
    except Exception:  # pragma: no cover
        ensure_decision_contract = None  # type: ignore
        utc_now_iso = None  # type: ignore

try:
    from schemas.forecasts import (  # type: ignore
        ForecastDetailResponse,
        ForecastSortBy,
        ForecastSortOrder,
        ForecastsResponse,
        WalkForwardScoreboardResponse,
    )
except Exception:  # pragma: no cover
    ForecastsResponse = None  # type: ignore
    ForecastDetailResponse = None  # type: ignore
    WalkForwardScoreboardResponse = None  # type: ignore
    ForecastSortBy = str  # type: ignore
    ForecastSortOrder = str  # type: ignore

try:
    from services import forecasts_service
except Exception:  # pragma: no cover
    from src.services import forecasts_service  # type: ignore

try:
    from domains.forecasts.application.global_signal_mesh_service import (
        build_global_signal_mesh_payload,
        build_insider_behavior_payload,
        build_macro_regime_hierarchy_payload,
        build_policy_change_impact_payload,
    )
except Exception:  # pragma: no cover
    build_global_signal_mesh_payload = None  # type: ignore
    build_insider_behavior_payload = None  # type: ignore
    build_macro_regime_hierarchy_payload = None  # type: ignore
    build_policy_change_impact_payload = None  # type: ignore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/forecasts")
EDGE_FORECASTS_FLAG = "FC_API_EDGE_FORECASTS"


def _now_iso() -> str:
    if callable(utc_now_iso):
        return utc_now_iso()
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _apply_decision_contract(payload: Dict[str, Any], *, route: str) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return payload

    now_iso = payload.get("generated_at") or payload.get("freshness") or _now_iso()
    payload.setdefault("generated_at", now_iso)
    payload.setdefault("freshness", now_iso)
    payload.setdefault("last_update", payload.get("last_update") or now_iso)
    payload.setdefault("source", [route])

    def _sync_payload_provenance() -> None:
        if not isinstance(payload.get("provenance"), dict):
            return
        payload["provenance"] = {
            **payload["provenance"],
            "source": list(payload.get("source") or [route]),
            "fallback_used": bool(payload.get("error")) or bool(payload.get("fallback_used")),
            "sla": {
                **(
                    payload["provenance"].get("sla")
                    if isinstance(payload["provenance"].get("sla"), dict)
                    else {}
                ),
                "updated_at": str(payload.get("last_update") or payload.get("freshness") or now_iso),
            },
        }

    if callable(ensure_decision_contract):
        ensure_decision_contract(
            payload,
            default_source=route,
            verdict="hold",
            confidence=payload.get("avg_confidence") or payload.get("confidence") or 0.45,
            why=["Forecast payload is informational with decision context."],
            risk_level=payload.get("risk_level") or payload.get("risk", {}).get("level") if isinstance(payload.get("risk"), dict) else None,
            freshness=payload.get("freshness"),
        )
        _sync_payload_provenance()
        return payload

    payload.setdefault("verdict", "hold")
    payload.setdefault("confidence", 0.45)
    payload.setdefault("why", ["Forecast payload is informational with decision context."])
    payload.setdefault("risk_level", "medium")
    payload.setdefault("risk", {"level": "medium", "caveat": ""})
    payload.setdefault("risk_flag", payload.get("risk_level") in {"high", "critical"})
    _sync_payload_provenance()
    return payload

# Expose service state for test/backward-compat contract checks.
_FORECASTS_RESPONSE_CACHE = forecasts_service._FORECASTS_RESPONSE_CACHE
_FORECASTS_INFLIGHT = forecasts_service._FORECASTS_INFLIGHT
_FORECASTS_INFLIGHT_LOCK = forecasts_service._FORECASTS_INFLIGHT_LOCK


@router.get(
    "",
    response_model=ForecastsResponse if ForecastsResponse is not None else None,
    response_model_exclude_none=True,
)
async def get_forecasts(
    asset_type: str = Query("all", description="Asset type: equity, commodity, crypto, all"),
    horizon: str = Query("all", description="Horizon: 1w, 1m, 3m, all"),
    ticker: Optional[List[str]] = Query(None, description="Filter by ticker symbols"),
    search: Optional[str] = Query(None, description="Search term"),
    sort_by: ForecastSortBy = Query(  # type: ignore[valid-type]
        "score",
        description="Sort by: score, confidence, expected_return, timestamp, risk_level",
    ),
    sort_order: ForecastSortOrder = Query("desc", description="Sort order (asc/desc)"),  # type: ignore[valid-type]
    limit: int = Query(50, ge=1, le=100, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    debug: bool = Query(False, description="Bypass cache and include debug_pipeline traces."),
):
    try:
        payload = await forecasts_service.get_forecasts_payload(
            asset_type=asset_type,
            horizon=horizon,
            ticker=ticker,
            search=search,
            sort_by=str(sort_by),
            sort_order=str(sort_order),
            limit=limit,
            offset=offset,
            debug=debug,
            load_json_fn=load_json,
        )
        _apply_decision_contract(payload, route="forecasts_route")
        if edge_enabled(EDGE_FORECASTS_FLAG, default=True):
            return edge_forecasts_ok(payload)
        return ok(payload)
    except Exception as route_exc:
        logger.error("Error in get_forecasts route orchestration: %s", route_exc, exc_info=True)
        now_iso = _now_iso()
        # Never-empty route-level fallback.
        fallback_payload = {
            "rows": [],
            "count": 0,
            "total": 0,
            "offset": int(offset),
            "limit": int(limit),
            "generated_at": now_iso,
            "freshness": now_iso,
            "freshness_status": "unknown",
            "freshness_age": -1.0,
            "last_update": now_iso,
            "source": ["forecasts_route", "critical_route_error_fallback"],
            "provider_chain": ["route_exception_fallback"],
            "fallback_used": True,
            "latency_ms": 0.0,
            "observability": {
                "provider_chain": ["route_exception_fallback"],
                "fallback_used": True,
                "latency_ms": 0.0,
                "freshness_age": -1.0,
            },
            "filters_applied": {
                "asset_type": asset_type,
                "horizon": horizon,
                "search": search,
                "sort_by": str(sort_by),
                "sort_order": str(sort_order),
                "tickers": sorted(
                    {
                        str(item).strip().upper()
                        for item in (ticker or [])
                        if str(item).strip()
                    }
                ),
                "limit": int(limit),
                "offset": int(offset),
            },
            "stats": {
                "total_loaded": 0,
                "filtered_count": 0,
                "returned_count": 0,
                "high_confidence_count": 0,
                "high_confidence_percentage": 0.0,
                "avg_confidence": 0.0,
            },
            "warnings": [],
            "cache": {"hit": False, "age_seconds": 0.0, "ttl_seconds": 0},
            "error": str(route_exc),
            "message": "Forecasts route failed critically but returned never-empty fallback.",
        }
        _apply_decision_contract(fallback_payload, route="forecasts_route")
        if edge_enabled(EDGE_FORECASTS_FLAG, default=True):
            return edge_forecasts_degraded(fallback_payload, detail=str(route_exc))
        return ok(fallback_payload)


@router.get(
    "/scoreboard",
    response_model=WalkForwardScoreboardResponse
    if WalkForwardScoreboardResponse is not None
    else None,
    response_model_exclude_none=True,
)
async def get_walk_forward_scoreboard(
    horizon: str = Query(
        "all",
        description="Optional walk-forward horizon filter (all, 1d, 1w, 1m, 3m).",
    ),
    debug: bool = Query(False, description="Bypass cache and include debug_pipeline traces."),
):
    try:
        payload = await forecasts_service.get_walk_forward_scoreboard_payload(
            horizon=horizon,
            debug=debug,
            load_json_fn=load_json,
        )
        _apply_decision_contract(payload, route="forecasts_route")
        if edge_enabled(EDGE_FORECASTS_FLAG, default=True):
            return edge_ok(
                payload,
                source=["forecasts_route", "walk_forward_scoreboard"],
                fallback=bool(payload.get("error")),
            )
        return ok(payload)
    except Exception as route_exc:
        logger.error(
            "Error in get_walk_forward_scoreboard route orchestration: %s",
            route_exc,
            exc_info=True,
        )
        now_iso = _now_iso()
        fallback_payload = {
            "rows": [],
            "count": 0,
            "generated_at": now_iso,
            "freshness": now_iso,
            "last_update": now_iso,
            "updated_at": now_iso,
            "freshness_status": "unknown",
            "freshness_age": -1.0,
            "source": ["forecasts_route", "walk_forward_scoreboard", "critical_route_error_fallback"],
            "filters_applied": {"horizon": str(horizon or "all").lower()},
            "stats": {"overall_rows": 0, "horizon_rows": 0, "asset_rows": 0, "passing_rows": 0, "failing_rows": 0},
            "threshold_summary": {
                "walk_forward_direction_hit_rate": {
                    "target": 0.52,
                    "comparator": "gte",
                    "value": 0.0,
                    "status": "fail",
                    "sample_size": 0,
                    "scope": "overall",
                    "updated_at": now_iso,
                }
            },
            "summary": {},
            "warnings": [],
            "cache": {"hit": False, "age_seconds": 0.0, "ttl_seconds": 0},
            "provenance": {
                "source": ["forecasts_route", "walk_forward_scoreboard", "critical_route_error_fallback"],
                "provider_chain": [],
                "model_version": None,
                "fallback_used": False,
                "sla": {
                    "updated_at": now_iso,
                    "freshness_age_seconds": 0.0,
                    "freshness_status": "fresh",
                    "target_max_age_seconds": 0,
                    "within_target": True,
                },
            },
            "error": str(route_exc),
            "message": "Walk-forward scoreboard route failed critically but returned never-empty fallback.",
        }
        _apply_decision_contract(fallback_payload, route="forecasts_route")
        if edge_enabled(EDGE_FORECASTS_FLAG, default=True):
            return edge_degraded(
                fallback_payload,
                code="walk_forward_scoreboard_unavailable",
                message="Walk-forward scoreboard unavailable, degraded fallback payload returned.",
                detail=str(route_exc),
                source=["forecasts_route", "walk_forward_scoreboard", "critical_route_error_fallback"],
                fallback=True,
            )
        return ok(fallback_payload)


@router.get("/global-signal-mesh")
async def get_global_signal_mesh(
    include_non_nominal: bool = Query(
        False,
        description="Include fallback-only free sources that are not on the nominal runtime path.",
    ),
    debug: bool = Query(False, description="Bypass cache and include debug_pipeline traces."),
):
    try:
        if build_global_signal_mesh_payload is None:
            raise ModuleNotFoundError("domains.forecasts.application.global_signal_mesh_service")
        payload = build_global_signal_mesh_payload(
            include_non_nominal=include_non_nominal,
            debug=debug,
        )
        _apply_decision_contract(payload, route="forecasts_global_signal_mesh")
        return ok(payload)
    except Exception as exc:
        logger.error("Error in get_global_signal_mesh route orchestration: %s", exc, exc_info=True)
        now_iso = _now_iso()
        fallback_payload = {
            "mesh_id": "free_global_signal_mesh",
            "generated_at": now_iso,
            "freshness": now_iso,
            "last_update": now_iso,
            "source": ["forecasts_global_signal_mesh", "critical_route_error_fallback"],
            "filters_applied": {
                "include_non_nominal": bool(include_non_nominal),
            },
            "sources_catalog": [],
            "stats": {
                "source_count": 0,
                "nominal_source_count": 0,
                "layer_counts": {},
                "license_class_counts": {},
            },
            "coverage": {
                "layers": [],
                "nominal_layers": [],
                "free_nominal_path_only": True,
            },
            "warnings": [],
            "provenance": {
                "source": ["forecasts_global_signal_mesh", "critical_route_error_fallback"],
                "fallback_used": True,
                "sla": {
                    "updated_at": now_iso,
                    "freshness_status": "unknown",
                    "freshness_age_seconds": 0.0,
                    "target_max_age_seconds": 0,
                    "within_target": False,
                },
            },
            "cache": {"hit": False, "age_seconds": 0.0, "ttl_seconds": 0},
            "error": str(exc),
            "message": "Global signal mesh unavailable, returning never-empty fallback.",
        }
        _apply_decision_contract(fallback_payload, route="forecasts_global_signal_mesh")
        return ok(fallback_payload)


@router.get("/policy-impact")
async def get_policy_change_impact(
    jurisdiction: str = Query("all", description="Jurisdiction filter: all, US, EU, UK, global."),
    status: str = Query("all", description="Policy status filter: all, proposed, adopted, effective, monitoring."),
    sector: str = Query("all", description="Sector filter: all, financials, technology, energy, healthcare, industrials."),
    limit: int = Query(10, ge=1, le=25, description="Max policy events to return."),
    debug: bool = Query(False, description="Bypass cache and include debug_pipeline traces."),
):
    try:
        if build_policy_change_impact_payload is None:
            raise ModuleNotFoundError("domains.forecasts.application.global_signal_mesh_service")
        payload = build_policy_change_impact_payload(
            jurisdiction=jurisdiction,
            status=status,
            sector=sector,
            limit=limit,
            debug=debug,
        )
        _apply_decision_contract(payload, route="forecasts_policy_change_impact")
        return ok(payload)
    except Exception as exc:
        logger.error("Error in get_policy_change_impact route orchestration: %s", exc, exc_info=True)
        now_iso = _now_iso()
        fallback_payload = {
            "engine_id": "policy_change_impact_v1",
            "generated_at": now_iso,
            "freshness": now_iso,
            "last_update": now_iso,
            "source": ["forecasts_policy_change_impact", "critical_route_error_fallback"],
            "filters_applied": {
                "jurisdiction": jurisdiction,
                "status": status,
                "sector": sector,
                "limit": int(limit),
            },
            "events": [],
            "stats": {
                "policy_article_count": 0,
                "returned_event_count": 0,
                "status_counts": {},
                "jurisdiction_counts": {},
                "sector_counts": {},
            },
            "timeline": {
                "effective_now_count": 0,
                "proposed_count": 0,
                "adopted_count": 0,
            },
            "warnings": [],
            "provenance": {
                "source": ["forecasts_policy_change_impact", "critical_route_error_fallback"],
                "fallback_used": True,
                "sla": {
                    "updated_at": now_iso,
                    "freshness_status": "unknown",
                    "freshness_age_seconds": 0.0,
                    "target_max_age_seconds": 0,
                    "within_target": False,
                },
            },
            "cache": {"hit": False, "age_seconds": 0.0, "ttl_seconds": 0},
            "error": str(exc),
            "message": "Policy impact engine unavailable, returning never-empty fallback.",
        }
        _apply_decision_contract(fallback_payload, route="forecasts_policy_change_impact")
        return ok(fallback_payload)


@router.get("/macro-regime-hierarchy")
async def get_macro_regime_hierarchy(
    country: str = Query("US", description="Country focus for the hierarchy."),
    continent: str = Query("", description="Optional continent override."),
    horizon: str = Query("3m", description="Forecast horizon label."),
    include_non_nominal: bool = Query(
        False,
        description="Include free fallback-only sources outside the nominal runtime path.",
    ),
    debug: bool = Query(False, description="Bypass cache and include debug_pipeline traces."),
):
    try:
        if build_macro_regime_hierarchy_payload is None:
            raise ModuleNotFoundError("domains.forecasts.application.global_signal_mesh_service")
        payload = build_macro_regime_hierarchy_payload(
            country=country,
            continent=continent,
            horizon=horizon,
            include_non_nominal=include_non_nominal,
            debug=debug,
        )
        _apply_decision_contract(payload, route="forecasts_macro_regime_hierarchy")
        return ok(payload)
    except Exception as exc:
        logger.error("Error in get_macro_regime_hierarchy route orchestration: %s", exc, exc_info=True)
        now_iso = _now_iso()
        fallback_payload = {
            "forecast_id": "macro_regime_hierarchy_v1",
            "generated_at": now_iso,
            "freshness": now_iso,
            "last_update": now_iso,
            "source": ["forecasts_macro_regime_hierarchy", "critical_route_error_fallback"],
            "filters_applied": {
                "country": str(country or "US").upper(),
                "continent": str(continent or "").lower(),
                "horizon": str(horizon or "3m").lower(),
                "include_non_nominal": bool(include_non_nominal),
            },
            "levels": [],
            "consistency": {"has_contradictions": False, "pairs": []},
            "narrative": {
                "summary": "Macro regime hierarchy unavailable, returning never-empty fallback.",
                "regime_bias": "unknown",
                "key_risks": [],
                "consistency_call": "unknown",
            },
            "stats": {
                "level_count": 0,
                "news_signal_count": 0,
                "coverage_source_count": 0,
            },
            "warnings": ["macro_regime_hierarchy_unavailable"],
            "provenance": {
                "source": ["forecasts_macro_regime_hierarchy", "critical_route_error_fallback"],
                "llm_used": False,
                "fallback_used": True,
                "sla": {
                    "updated_at": now_iso,
                    "freshness_status": "unknown",
                    "freshness_age_seconds": 0.0,
                    "target_max_age_seconds": 0,
                    "within_target": False,
                },
            },
            "cache": {"hit": False, "age_seconds": 0.0, "ttl_seconds": 0},
            "error": str(exc),
            "message": "Macro regime hierarchy unavailable, returning never-empty fallback.",
        }
        _apply_decision_contract(fallback_payload, route="forecasts_macro_regime_hierarchy")
        return ok(fallback_payload)


@router.get("/insider-behavior")
async def get_insider_behavior(
    tickers: str = Query("", description="Optional comma-separated ticker filter."),
    limit: int = Query(10, ge=1, le=25, description="Max insider signals to return."),
    debug: bool = Query(False, description="Bypass cache and include debug_pipeline traces."),
):
    try:
        if build_insider_behavior_payload is None:
            raise ModuleNotFoundError("domains.forecasts.application.global_signal_mesh_service")
        payload = build_insider_behavior_payload(
            tickers=tickers,
            limit=limit,
            debug=debug,
        )
        _apply_decision_contract(payload, route="forecasts_insider_behavior")
        return ok(payload)
    except Exception as exc:
        logger.error("Error in get_insider_behavior route orchestration: %s", exc, exc_info=True)
        now_iso = _now_iso()
        fallback_payload = {
            "engine_id": "insider_behavior_intelligence_v1",
            "generated_at": now_iso,
            "freshness": now_iso,
            "last_update": now_iso,
            "source": ["forecasts_insider_behavior", "critical_route_error_fallback"],
            "filters_applied": {
                "tickers": [item.strip().upper() for item in tickers.split(",") if item.strip()],
                "limit": limit,
            },
            "signals": [],
            "stats": {
                "snapshot_row_count": 0,
                "returned_signal_count": 0,
                "stance_counts": {},
                "high_uncertainty_count": 0,
            },
            "guardrails": {
                "deterministic_language_allowed": False,
                "policy": "Insider activity is evidence with uncertainty, never a standalone directive.",
            },
            "warnings": [],
            "provenance": {
                "source": ["forecasts_insider_behavior", "critical_route_error_fallback"],
                "fallback_used": True,
                "sla": {
                    "updated_at": now_iso,
                    "freshness_status": "unknown",
                    "freshness_age_seconds": 0.0,
                    "target_max_age_seconds": 0,
                    "within_target": False,
                },
            },
            "cache": {"hit": False, "age_seconds": 0.0, "ttl_seconds": 0},
            "error": str(exc),
            "message": "Insider behavior intelligence unavailable, returning never-empty fallback.",
        }
        _apply_decision_contract(fallback_payload, route="forecasts_insider_behavior")
        return ok(fallback_payload)


@router.get(
    "/{forecast_id}",
    response_model=ForecastDetailResponse if ForecastDetailResponse is not None else None,
    response_model_exclude_none=True,
)
async def get_forecast(forecast_id: str):
    try:
        payload = forecasts_service.get_forecast_detail_payload(
            forecast_id=forecast_id,
            load_json_fn=load_json,
        )
        _apply_decision_contract(payload, route="forecast_detail")
        if edge_enabled(EDGE_FORECASTS_FLAG, default=True):
            return edge_ok(
                payload,
                source=["forecasts_route", "forecast_detail"],
                fallback=not bool(payload.get("found")) if isinstance(payload, dict) else False,
            )
        return ok(payload)
    except Exception as exc:
        logger.error("Error in get_forecast route orchestration: %s", exc, exc_info=True)
        now_iso = _now_iso()
        fallback_payload = {
            "forecast": {},
            "found": False,
            "generated_at": now_iso,
            "freshness": now_iso,
            "last_update": now_iso,
            "updated_at": now_iso,
            "freshness_status": "fresh",
            "freshness_age": 0.0,
            "source": ["forecasts_route", "critical_route_error_fallback"],
            "warnings": [],
            "error": str(exc),
            "message": "Forecast temporarily unavailable, returning empty response per never-empty pattern.",
        }
        fallback_payload["provenance"] = forecasts_service._build_payload_provenance(
            payload=fallback_payload,
            now_iso=now_iso,
        )
        _apply_decision_contract(fallback_payload, route="forecast_detail")
        if edge_enabled(EDGE_FORECASTS_FLAG, default=True):
            return edge_degraded(
                fallback_payload,
                code="forecast_detail_unavailable",
                message="Forecast detail unavailable, degraded fallback payload returned.",
                detail=str(exc),
                source=["forecasts_route", "critical_route_error_fallback"],
                fallback=True,
            )
        return ok(fallback_payload)


forecasts_router = router
