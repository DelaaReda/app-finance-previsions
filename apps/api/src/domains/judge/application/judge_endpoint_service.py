"""Reusable service entrypoints for Judge API endpoints.

Routes stay orchestration-only and delegate payload creation to this module.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, List, Optional

from storage.io import load_json

try:
    from services.judge_quality import build_judge_quality_report  # type: ignore
except Exception:  # pragma: no cover
    build_judge_quality_report = None  # type: ignore

try:
    from services.service_standard import (
        ensure_decision_contract,
        safe_int,
        service_response,
        utc_now_iso,
    )
except Exception:  # pragma: no cover
    from src.services.service_standard import (  # type: ignore
        ensure_decision_contract,
        safe_int,
        service_response,
        utc_now_iso,
    )


JudgeVerdictsComputeFn = Callable[..., Awaitable[Dict[str, Any]]]


def _default_risk_levels() -> List[str]:
    return ["low", "medium", "high", "critical"]


async def get_judge_verdicts_payload(
    *,
    limit: int,
    min_confidence: float,
    ticker: Optional[List[str]],
    sort_by: Any,
    sort_order: Any,
    profile: str,
    debug: bool,
    debug_full: bool,
    x_debug_token: Optional[str],
    compute_verdicts_fn: JudgeVerdictsComputeFn,
) -> Dict[str, Any]:
    """Delegate heavy verdict generation to the provided reusable compute function."""
    response = await compute_verdicts_fn(
        limit=limit,
        min_confidence=min_confidence,
        ticker=ticker,
        sort_by=sort_by,
        sort_order=sort_order,
        profile=profile,
        debug=debug,
        debug_full=debug_full,
        x_debug_token=x_debug_token,
    )
    if not isinstance(response, dict):
        return response

    data = response.get("data")
    if not isinstance(data, dict):
        return response

    verdicts = data.get("verdicts")
    head = verdicts[0] if isinstance(verdicts, list) and verdicts and isinstance(verdicts[0], dict) else {}
    ensure_decision_contract(
        data,
        default_source="judge_endpoint_service",
        verdict=head.get("verdict") or head.get("action"),
        confidence=head.get("confidence"),
        why=head.get("why") or head.get("reasoning"),
        risk_level=head.get("risk_level") or head.get("risk"),
        risk_caveat=head.get("risk_caveat") or head.get("risk_reason"),
        freshness=response.get("freshness") or data.get("generated_at"),
    )
    response.setdefault("freshness", data.get("freshness") or data.get("generated_at"))
    return response


async def get_judge_quality_payload(
    *,
    horizon_days: int,
    min_samples: int,
) -> Dict[str, Any]:
    """Rolling quality metrics for judge/forecast predictive performance."""
    now_iso = utc_now_iso()
    try:
        if not build_judge_quality_report:
            return service_response(
                {
                    "as_of": now_iso,
                    "horizon_days": horizon_days,
                    "min_samples": min_samples,
                    "overall": {"n": 0, "sample_status": "insufficient"},
                    "windows": {},
                    "recommendation": {
                        "status": "unavailable",
                        "message": "Judge quality service unavailable in this runtime.",
                    },
                },
                freshness=now_iso,
            )

        report = build_judge_quality_report(
            horizon_days=horizon_days,
            min_samples=min_samples,
        )
        freshness = report.get("as_of") or now_iso
        return service_response(report, freshness=str(freshness))
    except Exception as exc:
        return service_response(
            {
                "as_of": now_iso,
                "horizon_days": horizon_days,
                "min_samples": min_samples,
                "overall": {"n": 0, "sample_status": "insufficient"},
                "windows": {},
                "recommendation": {
                    "status": "error",
                    "message": "Judge quality computation failed.",
                },
                "error": str(exc),
            },
            freshness="error",
        )


async def get_judge_quality_history_payload(
    *,
    horizon_days: int,
    min_samples: int,
    limit: int,
) -> Dict[str, Any]:
    """Historical quality snapshots for one (horizon, min_samples) scope."""
    now_iso = utc_now_iso()
    try:
        payload = load_json("judge_quality_tracking") or {}
        points = payload.get("points") if isinstance(payload, dict) else []
        points = points if isinstance(points, list) else []

        filtered = [
            point
            for point in points
            if isinstance(point, dict)
            and safe_int(point.get("horizon_days"), -1) == int(horizon_days)
            and safe_int(point.get("min_samples"), -1) == int(min_samples)
        ]
        filtered.sort(key=lambda point: str(point.get("as_of") or ""))
        filtered = filtered[-int(limit) :]
        latest = filtered[-1] if filtered else None

        return service_response(
            {
                "as_of": now_iso,
                "scope": {
                    "horizon_days": int(horizon_days),
                    "min_samples": int(min_samples),
                },
                "count": len(filtered),
                "latest": latest,
                "points": filtered,
            },
            freshness=str((latest or {}).get("as_of", now_iso)),
        )
    except Exception as exc:
        return service_response(
            {
                "as_of": now_iso,
                "scope": {
                    "horizon_days": int(horizon_days),
                    "min_samples": int(min_samples),
                },
                "count": 0,
                "latest": None,
                "points": [],
                "error": str(exc),
                "message": "Judge quality history unavailable; fallback returned.",
            },
            freshness="error",
        )


async def get_judge_options_payload(
    *,
    risk_levels_fn: Optional[Callable[[], List[str]]] = None,
) -> Dict[str, Any]:
    """Options payload for judge UI (never-empty)."""
    now_iso = utc_now_iso()
    try:
        risk_levels = (
            risk_levels_fn() if callable(risk_levels_fn) else _default_risk_levels()
        )
        options = {
            "sort_options": [
                {"value": "confidence", "label": "Confiance"},
                {"value": "expected_return", "label": "Retour attendu"},
                {"value": "risk_level", "label": "Niveau de risque"},
                {"value": "timestamp", "label": "Date de generation"},
            ],
            "risk_levels": risk_levels,
            "confidence_thresholds": [
                {"label": "Toutes", "value": 0.0},
                {"label": "Haute confiance (0.7+)", "value": 0.7},
                {"label": "Tres haute confiance (0.8+)", "value": 0.8},
                {"label": "Excellente confiance (0.9+)", "value": 0.9},
            ],
            "generated_at": now_iso,
            "source": ["judge_options_service", "ui_helper_data", "merged"],
        }
        return service_response(options, freshness=now_iso)
    except Exception as exc:
        return service_response(
            {
                "sort_options": [
                    {"value": "confidence", "label": "Confiance"},
                    {"value": "expected_return", "label": "Retour attendu"},
                ],
                "risk_levels": _default_risk_levels(),
                "confidence_thresholds": [
                    {"label": "Toutes", "value": 0.0},
                    {"label": "Haute confiance (0.7+)", "value": 0.7},
                ],
                "generated_at": now_iso,
                "error": str(exc),
                "message": (
                    "Judge options endpoint failed but fallback returned "
                    "to maintain never-empty contract"
                ),
            },
            freshness="error",
        )


__all__ = [
    "JudgeVerdictsComputeFn",
    "get_judge_verdicts_payload",
    "get_judge_quality_payload",
    "get_judge_quality_history_payload",
    "get_judge_options_payload",
]
