"""Reusable service entrypoints for Judge API endpoints.

Routes stay orchestration-only and delegate payload creation to this module.
"""

from __future__ import annotations

from hashlib import sha1
from typing import Any, Awaitable, Callable, Dict, List, Optional

from storage.io import load_json

try:
    from services.judge_quality import build_judge_quality_report  # type: ignore
except Exception:  # pragma: no cover
    build_judge_quality_report = None  # type: ignore

try:
    from services.service_standard import (
        append_source_tag,
        coerce_confidence,
        coerce_verdict,
        ensure_endpoint_metadata,
        ensure_source_list,
        ensure_decision_contract,
        normalize_risk_level,
        safe_int,
        service_response_with_metadata,
        utc_now_iso,
    )
except Exception:  # pragma: no cover
    from src.services.service_standard import (  # type: ignore
        append_source_tag,
        coerce_confidence,
        coerce_verdict,
        ensure_endpoint_metadata,
        ensure_source_list,
        ensure_decision_contract,
        normalize_risk_level,
        safe_int,
        service_response_with_metadata,
        utc_now_iso,
    )


JudgeVerdictsComputeFn = Callable[..., Awaitable[Dict[str, Any]]]


def _default_risk_levels() -> List[str]:
    return ["low", "medium", "high", "critical"]


def _coerce_text_list(*values: Any) -> List[str]:
    items: List[str] = []
    seen = set()
    for value in values:
        if isinstance(value, list):
            for raw_item in value:
                text = str(raw_item or "").strip()
                if not text:
                    continue
                key = text.lower()
                if key in seen:
                    continue
                seen.add(key)
                items.append(text)
            continue
        text = str(value or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append(text)
    return items


def _fallback_horizon(*, profile: str, verdict: Dict[str, Any]) -> str:
    raw_horizon = str(
        verdict.get("horizon")
        or (verdict.get("ml_prior") or {}).get("horizon")
        or ""
    ).strip()
    if raw_horizon:
        return raw_horizon

    profile_text = str(profile or "").strip().lower()
    for candidate in ("1d", "1w", "1m", "3m", "6m", "1y"):
        if candidate in profile_text:
            return candidate
    return "1w"


def _build_journal_entry(
    verdict: Dict[str, Any],
    *,
    profile: str,
    fallback_generated_at: str,
    default_sources: List[str],
) -> Optional[Dict[str, Any]]:
    if not isinstance(verdict, dict):
        return None

    captured_at = str(
        verdict.get("generated_at")
        or (verdict.get("meta") or {}).get("generated_at")
        or fallback_generated_at
        or utc_now_iso()
    ).strip() or utc_now_iso()
    ticker = str(verdict.get("ticker") or "UNKNOWN").strip().upper() or "UNKNOWN"
    action = coerce_verdict(
        verdict.get("verdict") or verdict.get("action") or verdict.get("direction"),
        default="hold",
    )
    confidence = coerce_confidence(verdict.get("confidence"), default=0.5)
    why = _coerce_text_list(
        verdict.get("why"),
        verdict.get("summary"),
        verdict.get("reasoning"),
    ) or ["Decision generated from judge verdict payload."]

    risk_payload = verdict.get("risk") if isinstance(verdict.get("risk"), dict) else {}
    risk_level = normalize_risk_level(
        verdict.get("risk_level") or risk_payload.get("level"),
        default="medium",
    )
    risk_caveat = str(
        risk_payload.get("caveat")
        or verdict.get("risk_caveat")
        or verdict.get("risk_reason")
        or ""
    ).strip()
    sources = ensure_source_list(
        verdict.get("source") or (verdict.get("meta") or {}).get("source") or default_sources,
        default_source="judge_endpoint_service",
    )
    horizon = _fallback_horizon(profile=profile, verdict=verdict)
    decision_basis = "|".join(
        [
            ticker,
            horizon,
            action,
            captured_at,
            str(profile or "").strip().lower() or "default",
        ]
    )
    decision_id = f"judge_{sha1(decision_basis.encode('utf-8')).hexdigest()[:16]}"

    return {
        "decision_id": decision_id,
        "date": captured_at[:10],
        "captured_at": captured_at,
        "ticker": ticker,
        "action": action,
        "confidence": confidence,
        "horizon": horizon,
        "why": why,
        "risk": {
            "level": risk_level,
            "caveat": risk_caveat,
        },
        "sources": sources,
        "profile": str(profile or "").strip() or "default",
    }


def _attach_decision_journal_projection(
    data: Dict[str, Any],
    *,
    profile: str,
    freshness: Optional[str],
) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return data

    verdicts = data.get("verdicts")
    if not isinstance(verdicts, list):
        verdicts = []
        data["verdicts"] = verdicts

    generated_at = str(freshness or data.get("generated_at") or utc_now_iso()).strip() or utc_now_iso()
    default_sources = ensure_source_list(
        data.get("source"),
        default_source="judge_endpoint_service",
    )
    entries: List[Dict[str, Any]] = []
    for verdict in verdicts:
        entry = _build_journal_entry(
            verdict,
            profile=profile,
            fallback_generated_at=generated_at,
            default_sources=default_sources,
        )
        if entry is None:
            continue
        verdict.setdefault("decision_id", entry["decision_id"])
        entries.append(entry)

    data["decision_journal"] = {
        "schema_version": "decision_journal_v1",
        "generated_at": generated_at,
        "count": len(entries),
        "append_only": True,
        "link_field": "decision_id",
        "outcomes_update_mode": "separate_records",
        "feedback_horizons": ["1d", "1w", "1m"],
        "entries": entries,
    }
    append_source_tag(
        data,
        "decision_journal_projection_v1",
        default_source="judge_endpoint_service",
    )
    return data


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
    _attach_decision_journal_projection(
        data,
        profile=profile,
        freshness=response.get("freshness") or data.get("generated_at"),
    )
    ensure_endpoint_metadata(
        data,
        default_source="judge_endpoint_service",
        freshness=response.get("freshness") or data.get("generated_at"),
    )
    return service_response_with_metadata(
        data,
        default_source="judge_endpoint_service",
        freshness=data.get("freshness"),
        status=data.get("status"),
        error=data.get("error"),
    )


async def get_judge_quality_payload(
    *,
    horizon_days: int,
    min_samples: int,
) -> Dict[str, Any]:
    """Rolling quality metrics for judge/forecast predictive performance."""
    now_iso = utc_now_iso()
    try:
        if not build_judge_quality_report:
            return service_response_with_metadata(
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
                default_source="judge_quality_service",
                freshness=now_iso,
            )

        report = build_judge_quality_report(
            horizon_days=horizon_days,
            min_samples=min_samples,
        )
        freshness = report.get("as_of") or now_iso
        return service_response_with_metadata(
            report,
            default_source="judge_quality_service",
            freshness=str(freshness),
        )
    except Exception as exc:
        return service_response_with_metadata(
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
            default_source="judge_quality_service",
            freshness=now_iso,
            status="degraded",
            error=str(exc),
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

        return service_response_with_metadata(
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
            default_source="judge_quality_history_service",
            freshness=str((latest or {}).get("as_of", now_iso)),
        )
    except Exception as exc:
        return service_response_with_metadata(
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
            default_source="judge_quality_history_service",
            freshness=now_iso,
            status="degraded",
            error=str(exc),
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
        return service_response_with_metadata(
            options,
            default_source="judge_options_service",
            freshness=now_iso,
        )
    except Exception as exc:
        return service_response_with_metadata(
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
            default_source="judge_options_service",
            freshness=now_iso,
            status="degraded",
            error=str(exc),
        )


__all__ = [
    "JudgeVerdictsComputeFn",
    "get_judge_verdicts_payload",
    "get_judge_quality_payload",
    "get_judge_quality_history_payload",
    "get_judge_options_payload",
]
