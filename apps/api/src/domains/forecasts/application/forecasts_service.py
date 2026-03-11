"""Reusable business logic for forecasts endpoints.

Routes should orchestrate only (validation, auth, response mapping) and delegate
all forecast computation/caching logic to this module.
"""

from __future__ import annotations

import asyncio
import heapq
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

from storage.io import load_json, save_json

try:
    from api.templates.judge_like_endpoint import (
        append_source_tag,
        compute_singleflight,
        response_cache_get,
        response_cache_set,
        stable_cache_key,
        utc_now_iso,
    )
except Exception:  # pragma: no cover
    from src.api.templates.judge_like_endpoint import (  # type: ignore
        append_source_tag,
        compute_singleflight,
        response_cache_get,
        response_cache_set,
        stable_cache_key,
        utc_now_iso,
    )

try:
    from services.service_standard import ensure_decision_contract  # type: ignore
except Exception:  # pragma: no cover
    ensure_decision_contract = None  # type: ignore

try:
    from services.prediction_analyzer import prediction_analyzer_service  # type: ignore
except Exception:  # pragma: no cover
    try:
        from domains.forecasts.application.prediction_analyzer import (  # type: ignore
            prediction_analyzer_service,
        )
    except Exception:  # pragma: no cover
        prediction_analyzer_service = None  # type: ignore


logger = logging.getLogger(__name__)

FORECASTS_VERSION = "v2"
FORECASTS_CACHE_TTL_SECONDS = max(
    0, int(os.getenv("FORECASTS_CACHE_TTL_SECONDS", "120") or "120")
)
FORECASTS_CACHE_MAX_ENTRIES = max(
    1, int(os.getenv("FORECASTS_CACHE_MAX_ENTRIES", "128") or "128")
)
HIGH_CONFIDENCE_THRESHOLD = max(
    0.0,
    min(
        1.0,
        float(
            os.getenv("FORECASTS_HIGH_CONFIDENCE_THRESHOLD", "0.6") or "0.6"
        ),
    ),
)
FORECASTS_STALE_SECONDS = max(
    300, int(os.getenv("FORECASTS_STALE_SECONDS", "86400") or "86400")
)
FORECASTS_MIN_CONFIDENCE = max(
    0.0, min(1.0, float(os.getenv("FORECASTS_MIN_CONFIDENCE", "0.01") or "0.01"))
)
FORECASTS_BLOCK_MOCK_NOMINAL = str(
    os.getenv("FORECASTS_BLOCK_MOCK_NOMINAL", "1")
).strip().lower() in {"1", "true", "yes", "on"}

_FORECASTS_RESPONSE_CACHE: Dict[str, Dict[str, Any]] = {}
_FORECASTS_INFLIGHT: Dict[str, asyncio.Task] = {}
_FORECASTS_INFLIGHT_LOCK = asyncio.Lock()
_FORECASTS_SCOREBOARD_RESPONSE_CACHE: Dict[str, Dict[str, Any]] = {}
_FORECASTS_SCOREBOARD_INFLIGHT: Dict[str, asyncio.Task] = {}
_FORECASTS_SCOREBOARD_INFLIGHT_LOCK = asyncio.Lock()

RISK_LEVEL_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}
NOMINAL_REFRESH_MARKERS = ("forecasts_simple", "simple_momentum")
WALK_FORWARD_HIT_RATE_TARGET = 0.52

try:
    from platform.legacy.models.forecast_hybrid_v1 import ForecastHybridV1
except Exception:  # pragma: no cover
    ForecastHybridV1 = None  # type: ignore[misc,assignment]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _normalize_confidence(value: Any, *, default: float = 0.5) -> float:
    confidence = _safe_float(value, default=default)
    if confidence <= 0:
        return max(FORECASTS_MIN_CONFIDENCE, _safe_float(default, default=0.5))
    if confidence > 1.0:
        confidence = confidence / 100.0 if confidence <= 100.0 else 1.0
    return max(0.0, min(1.0, confidence))


def _safe_rows(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = payload.get("rows")
    if isinstance(rows, list):
        return [dict(item) for item in rows if isinstance(item, dict)]
    data = payload.get("data")
    if isinstance(data, dict):
        nested_rows = data.get("rows")
        if isinstance(nested_rows, list):
            return [dict(item) for item in nested_rows if isinstance(item, dict)]
    return []


def _normalize_source(raw_source: Any) -> List[str]:
    if isinstance(raw_source, list):
        out = [str(item).strip() for item in raw_source if str(item).strip()]
        return out or ["forecasts_storage"]
    if isinstance(raw_source, str) and raw_source.strip():
        return [raw_source.strip()]
    return ["forecasts_storage"]


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _contains_mock_marker(values: List[str]) -> bool:
    for value in values:
        marker = str(value).strip().lower()
        if not marker:
            continue
        if "mock" in marker:
            return True
    return False


def _parse_iso_datetime(raw_value: Any) -> Optional[datetime]:
    if raw_value is None:
        return None
    raw = str(raw_value).strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            raw = raw.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(raw)
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _freshness_age_seconds(reference_ts: Any, now_ts: Any) -> float:
    ref_dt = _parse_iso_datetime(reference_ts)
    now_dt = _parse_iso_datetime(now_ts)
    if ref_dt is None or now_dt is None:
        return -1.0
    return max(0.0, (now_dt - ref_dt).total_seconds())


def _freshness_status_from_age(age_seconds: float) -> str:
    if age_seconds < 0:
        return "unknown"
    if age_seconds <= FORECASTS_STALE_SECONDS:
        return "fresh"
    return "stale"


def _normalize_provider_chain(
    *,
    provider_chain: Any,
    provider: Any,
    model: Any,
    source_markers: List[str],
) -> List[str]:
    chain: List[str] = []
    if isinstance(provider_chain, list):
        chain.extend(str(item).strip() for item in provider_chain if str(item).strip())
    provider_v = str(provider).strip()
    model_v = str(model).strip()
    if provider_v:
        chain.append(provider_v)
    if model_v:
        chain.append(model_v)
    chain.extend(str(item).strip() for item in source_markers if str(item).strip())
    # stable de-duplication while preserving first-seen order
    return list(dict.fromkeys(chain))


def _normalize_forecast_row(
    row: Dict[str, Any],
    *,
    snapshot_generated_at: str,
    now_iso: str,
    inherited_source: List[str],
) -> Dict[str, Any]:
    normalized = dict(row)
    ticker = str(normalized.get("ticker", "")).strip().upper()
    if ticker:
        normalized["ticker"] = ticker

    normalized["asset_type"] = str(normalized.get("asset_type", "all") or "all").strip().lower()
    normalized["horizon"] = str(normalized.get("horizon", "all") or "all").strip().lower()

    normalized["confidence"] = _normalize_confidence(
        normalized.get("confidence", 0.0),
        default=0.5,
    )
    normalized["score"] = _safe_float(normalized.get("score", 0.0))
    normalized["expected_return"] = _safe_float(
        normalized.get("expected_return", normalized.get("return", 0.0))
    )

    risk = str(normalized.get("risk_level", "medium")).strip().lower() or "medium"
    if risk not in RISK_LEVEL_RANK:
        risk = "medium"
    normalized["risk_level"] = risk

    timestamp = str(
        normalized.get("timestamp")
        or normalized.get("generated_at")
        or snapshot_generated_at
        or now_iso
    )
    normalized["timestamp"] = timestamp
    normalized["generated_at"] = str(
        normalized.get("generated_at") or timestamp or now_iso
    )

    direction = str(normalized.get("direction", "")).strip().lower()
    if direction not in {"up", "down", "flat"}:
        if normalized["expected_return"] > 0:
            direction = "up"
        elif normalized["expected_return"] < 0:
            direction = "down"
        else:
            direction = "flat"
    normalized["direction"] = direction

    action = str(normalized.get("action", "")).strip().lower()
    if action not in {"buy", "sell", "hold"}:
        action = {"up": "buy", "down": "sell", "flat": "hold"}[direction]
    normalized["action"] = action

    why = str(normalized.get("why", "")).strip()
    if not why:
        summary = normalized.get("summary")
        if isinstance(summary, list):
            why = " ".join(str(item).strip() for item in summary[:2] if str(item).strip())
        elif isinstance(summary, str):
            why = summary.strip()
    if not why:
        explanation = normalized.get("explanation")
        if isinstance(explanation, str):
            why = explanation.strip()
    if not why:
        why = "No rationale provided."
    normalized["why"] = why

    risk_flag_raw = normalized.get("risk_flag")
    if risk_flag_raw is None:
        normalized["risk_flag"] = risk in {"high", "critical"}
    else:
        normalized["risk_flag"] = _safe_bool(risk_flag_raw, default=False)

    row_source = _normalize_source(normalized.get("source"))
    source_markers = [*inherited_source, *row_source]
    normalized["source"] = list(dict.fromkeys(source_markers))

    provider_chain = _normalize_provider_chain(
        provider_chain=normalized.get("provider_chain"),
        provider=normalized.get("provider"),
        model=normalized.get("model") or normalized.get("model_version"),
        source_markers=source_markers,
    )
    normalized["provider_chain"] = provider_chain

    fallback_markers = [*provider_chain, *source_markers]
    fallback_used = _safe_bool(normalized.get("fallback_used"), default=False) or any(
        "fallback" in str(item).lower() or "degraded" in str(item).lower()
        for item in fallback_markers
    )
    normalized["fallback_used"] = bool(fallback_used)

    normalized["latency_ms"] = _safe_float(normalized.get("latency_ms", 0.0))
    freshness_age = _safe_float(
        normalized.get("freshness_age"),
        _freshness_age_seconds(normalized["generated_at"], now_iso),
    )
    normalized["freshness_age"] = float(freshness_age)
    freshness_status = str(normalized.get("freshness_status", "")).strip().lower()
    if freshness_status not in {"fresh", "stale", "unknown"}:
        freshness_status = _freshness_status_from_age(freshness_age)
    normalized["freshness_status"] = freshness_status

    forecast_id = str(
        normalized.get("forecast_id")
        or normalized.get("id")
        or f"{normalized.get('ticker', 'NA')}:{normalized.get('horizon', 'all')}:{normalized['generated_at']}"
    ).strip()
    normalized["forecast_id"] = forecast_id
    normalized["id"] = forecast_id
    return normalized


def _snapshot_markers(
    payload: Dict[str, Any],
    rows: List[Dict[str, Any]],
) -> List[str]:
    markers = [
        *_normalize_source(payload.get("source")),
        *_normalize_source(payload.get("provider_chain")),
    ]
    for row in rows[:25]:
        markers.extend(_normalize_source(row.get("source")))
        model = str(row.get("model") or row.get("model_version") or "").strip()
        if model:
            markers.append(model)
    return list(dict.fromkeys(marker for marker in markers if marker))


def _requires_nominal_refresh(
    payload: Dict[str, Any],
    rows: List[Dict[str, Any]],
    *,
    snapshot_age: float,
) -> bool:
    if snapshot_age < 0 or not rows:
        return True
    if snapshot_age > float(FORECASTS_STALE_SECONDS):
        return True
    markers = [marker.lower() for marker in _snapshot_markers(payload, rows)]
    return any(
        refresh_marker in marker
        for marker in markers
        for refresh_marker in NOMINAL_REFRESH_MARKERS
    )


def _refresh_nominal_snapshot(
    *,
    tickers: List[str],
    now_iso: str,
) -> Optional[Dict[str, Any]]:
    if ForecastHybridV1 is None:
        return None
    try:
        generator = ForecastHybridV1()
        refreshed = generator.run_forecast_job(tickers or None)
        if not isinstance(refreshed, dict):
            return None
        rows = refreshed.get("rows")
        if not isinstance(rows, list) or not rows:
            return None
        payload = dict(refreshed)
        payload["generated_at"] = str(
            payload.get("generated_at")
            or payload.get("last_update")
            or now_iso
        )
        payload["last_update"] = str(
            payload.get("last_update")
            or payload.get("generated_at")
            or now_iso
        )
        payload["freshness"] = str(payload.get("freshness") or payload["generated_at"])
        payload["fallback_used"] = False
        payload["source"] = list(
            dict.fromkeys(
                [
                    *_normalize_source(payload.get("source")),
                    "forecasts_nominal_refresh",
                ]
            )
        )
        payload["provider_chain"] = _normalize_provider_chain(
            provider_chain=payload.get("provider_chain"),
            provider=None,
            model=payload.get("model_version"),
            source_markers=_normalize_source(payload.get("source")),
        )
        save_json("forecasts", payload, source=_normalize_source(payload.get("source")))
        return payload
    except Exception as exc:
        logger.warning("Forecast nominal refresh failed: %s", exc)
        return None


def _build_filter_indexes(
    rows: List[Dict[str, Any]],
) -> Dict[str, Dict[Any, List[Dict[str, Any]]]]:
    by_asset: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_horizon: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_asset_horizon: Dict[tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)

    for row in rows:
        asset = str(row.get("asset_type", "")).lower()
        horizon = str(row.get("horizon", "")).lower()
        by_asset[asset].append(row)
        by_horizon[horizon].append(row)
        by_asset_horizon[(asset, horizon)].append(row)

    return {
        "by_asset": dict(by_asset),
        "by_horizon": dict(by_horizon),
        "by_asset_horizon": dict(by_asset_horizon),
    }


def _select_base_rows(
    rows: List[Dict[str, Any]],
    indexes: Dict[str, Dict[Any, List[Dict[str, Any]]]],
    asset_type: str,
    horizon: str,
) -> List[Dict[str, Any]]:
    asset_type_l = asset_type.lower()
    horizon_l = horizon.lower()

    horizon_alias = {
        "short": {"1d", "1w", "short"},
        "medium": {"1m", "3m", "medium"},
        "long": {"6m", "1y", "long"},
    }
    allowed_horizons = horizon_alias.get(horizon_l, {horizon_l})

    by_asset = indexes.get("by_asset", {})
    by_horizon = indexes.get("by_horizon", {})
    by_asset_horizon = indexes.get("by_asset_horizon", {})

    if asset_type_l == "all" and horizon_l == "all":
        return rows

    if asset_type_l != "all" and horizon_l != "all":
        if len(allowed_horizons) == 1:
            only_hz = next(iter(allowed_horizons))
            return by_asset_horizon.get((asset_type_l, only_hz), [])
        base = by_asset.get(asset_type_l, [])
        return [
            row
            for row in base
            if str(row.get("horizon", "")).lower() in allowed_horizons
        ]

    if asset_type_l != "all":
        return by_asset.get(asset_type_l, [])

    selected: List[Dict[str, Any]] = []
    for hz in allowed_horizons:
        selected.extend(by_horizon.get(hz, []))
    return selected


def _sort_key(row: Dict[str, Any], sort_by: str) -> Any:
    if sort_by == "confidence":
        return _safe_float(row.get("confidence", 0.0))
    if sort_by == "expected_return":
        return _safe_float(row.get("expected_return", 0.0))
    if sort_by == "risk_level":
        return RISK_LEVEL_RANK.get(str(row.get("risk_level", "medium")).lower(), 1)
    if sort_by == "timestamp":
        return str(row.get("timestamp", ""))
    return _safe_float(row.get("score", 0.0))


def _select_page_rows(
    rows: List[Dict[str, Any]],
    sort_by: str,
    sort_order: str,
    limit: int,
    offset: int,
) -> List[Dict[str, Any]]:
    if not rows:
        return []

    reverse_sort = str(sort_order).lower() != "asc"
    sort_key = lambda row: _sort_key(row, sort_by)

    # Dominant UI request shape: offset=0 with a small page.
    # Keep stable tie-order parity with full sorted().
    if offset == 0 and 0 < limit < len(rows) and limit <= 200:
        if reverse_sort:
            top_rows = heapq.nlargest(
                limit,
                enumerate(rows),
                key=lambda item: (sort_key(item[1]), -item[0]),
            )
        else:
            top_rows = heapq.nsmallest(
                limit,
                enumerate(rows),
                key=lambda item: (sort_key(item[1]), item[0]),
            )
        return [row for _, row in top_rows]

    sorted_rows = sorted(rows, key=sort_key, reverse=reverse_sort)
    return sorted_rows[offset : offset + limit]


def _build_forecasts_cache_key(
    *,
    asset_type: str,
    horizon: str,
    tickers: List[str],
    search: Optional[str],
    sort_by: str,
    sort_order: str,
    limit: int,
    offset: int,
) -> str:
    return stable_cache_key(
        f"forecasts_{FORECASTS_VERSION}",
        {
            "asset_type": asset_type,
            "horizon": horizon,
            "tickers": sorted(tickers),
            "search": search or "",
            "sort_by": sort_by,
            "sort_order": sort_order,
            "limit": int(limit),
            "offset": int(offset),
        },
    )


def _base_forecasts_payload(
    *,
    now_iso: str,
    source: List[str],
    filters_applied: Dict[str, Any],
    limit: int,
    offset: int,
) -> Dict[str, Any]:
    return {
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
        "source": source,
        "provider_chain": [],
        "fallback_used": False,
        "latency_ms": 0.0,
        "observability": {
            "provider_chain": [],
            "fallback_used": False,
            "latency_ms": 0.0,
            "freshness_age": -1.0,
        },
        "filters_applied": filters_applied,
        "stats": {
            "total_loaded": 0,
            "filtered_count": 0,
            "returned_count": 0,
            "high_confidence_count": 0,
            "high_confidence_percentage": 0.0,
            "avg_confidence": 0.0,
        },
        "warnings": [],
        "cache": {
            "hit": False,
            "age_seconds": 0.0,
            "ttl_seconds": int(FORECASTS_CACHE_TTL_SECONDS),
        },
    }


def _scoreboard_status(value: float, *, target: Optional[float], comparator: str) -> str:
    if target is None:
        return "unknown"
    if comparator == "gte":
        return "pass" if value >= target else "fail"
    if comparator == "lte":
        return "pass" if value <= target else "fail"
    return "unknown"


def _base_scoreboard_payload(
    *,
    now_iso: str,
    source: List[str],
    filters_applied: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "rows": [],
        "count": 0,
        "generated_at": now_iso,
        "freshness": now_iso,
        "last_update": now_iso,
        "freshness_status": "unknown",
        "freshness_age": -1.0,
        "source": source,
        "filters_applied": filters_applied,
        "stats": {
            "overall_rows": 0,
            "horizon_rows": 0,
            "asset_rows": 0,
            "passing_rows": 0,
            "failing_rows": 0,
        },
        "threshold_summary": {
            "walk_forward_direction_hit_rate": {
                "target": WALK_FORWARD_HIT_RATE_TARGET,
                "comparator": "gte",
            }
        },
        "summary": {},
        "warnings": [],
        "cache": {
            "hit": False,
            "age_seconds": 0.0,
            "ttl_seconds": int(FORECASTS_CACHE_TTL_SECONDS),
        },
    }


async def get_walk_forward_scoreboard_payload(
    *,
    horizon: str,
    debug: bool,
    load_json_fn: Callable[[str], Any] = load_json,
) -> Dict[str, Any]:
    now_iso = utc_now_iso()
    filters_applied = {"horizon": str(horizon or "all").lower()}
    cache_key = stable_cache_key(
        "forecasts_walk_forward_scoreboard_v1",
        filters_applied,
    )

    if not debug and FORECASTS_CACHE_TTL_SECONDS > 0:
        cached = response_cache_get(
            _FORECASTS_SCOREBOARD_RESPONSE_CACHE,
            cache_key,
            ttl_seconds=FORECASTS_CACHE_TTL_SECONDS,
            hit_source_tag="forecasts_scoreboard_cache_hit",
            default_source="forecasts_route",
            copy_mode="deep",
        )
        if cached is not None:
            return cached

    traces: List[Dict[str, Any]] = []

    def add_trace(step: str, **meta: Any) -> None:
        if debug:
            traces.append({"step": step, "ts": utc_now_iso(), **meta})

    async def compute_payload() -> Dict[str, Any]:
        payload = _base_scoreboard_payload(
            now_iso=now_iso,
            source=["forecasts_route", "walk_forward_scoreboard"],
            filters_applied=filters_applied,
        )
        try:
            add_trace("load_snapshot_start")
            report = (
                load_json_fn("prediction_accuracy")
                or load_json_fn("prediction_accuracy.json")
                or {}
            )
            add_trace("load_snapshot_done", has_snapshot=bool(report))
            if not isinstance(report, dict) or not report:
                if prediction_analyzer_service is not None:
                    add_trace("prediction_analyzer_start")
                    report = prediction_analyzer_service.analyze_predictions(
                        horizon=filters_applied["horizon"]
                    )
                    add_trace(
                        "prediction_analyzer_done",
                        total_predictions=(
                            report.get("accuracy_metrics", {}).get("total_predictions", 0)
                            if isinstance(report, dict)
                            else 0
                        ),
                    )
                else:
                    report = {}

            metrics = report.get("accuracy_metrics", {}) if isinstance(report, dict) else {}
            summary = report.get("summary", {}) if isinstance(report, dict) else {}
            by_horizon = report.get("by_horizon", {}) if isinstance(report, dict) else {}
            by_asset = report.get("by_asset", {}) if isinstance(report, dict) else {}
            report_generated_at = str(
                report.get("generated_at")
                or metrics.get("generated_at")
                or now_iso
            )
            freshness_age = _freshness_age_seconds(report_generated_at, now_iso)

            rows: List[Dict[str, Any]] = []
            overall_hit_rate = _safe_float(metrics.get("hit_rate", 0.0))
            rows.append(
                {
                    "metric_key": "walk_forward_direction_hit_rate",
                    "label": "Directional hit rate",
                    "scope": "overall",
                    "value": round(overall_hit_rate, 6),
                    "target": WALK_FORWARD_HIT_RATE_TARGET,
                    "comparator": "gte",
                    "status": _scoreboard_status(
                        overall_hit_rate,
                        target=WALK_FORWARD_HIT_RATE_TARGET,
                        comparator="gte",
                    ),
                    "sample_size": _safe_int(metrics.get("total_predictions", 0)),
                }
            )
            rows.append(
                {
                    "metric_key": "walk_forward_mae",
                    "label": "Mean absolute error",
                    "scope": "overall",
                    "value": round(_safe_float(metrics.get("mae", 0.0)), 6),
                    "target": None,
                    "comparator": "info",
                    "status": "unknown",
                    "sample_size": _safe_int(metrics.get("total_predictions", 0)),
                }
            )

            requested_horizon = filters_applied["horizon"]
            for hz, hz_metrics in sorted(by_horizon.items()):
                if requested_horizon != "all" and str(hz).lower() != requested_horizon:
                    continue
                hit_rate = _safe_float(hz_metrics.get("hit_rate", 0.0))
                rows.append(
                    {
                        "metric_key": "walk_forward_direction_hit_rate",
                        "label": f"Directional hit rate ({hz})",
                        "scope": f"horizon:{hz}",
                        "value": round(hit_rate, 6),
                        "target": WALK_FORWARD_HIT_RATE_TARGET,
                        "comparator": "gte",
                        "status": _scoreboard_status(
                            hit_rate,
                            target=WALK_FORWARD_HIT_RATE_TARGET,
                            comparator="gte",
                        ),
                        "sample_size": _safe_int(hz_metrics.get("count", 0)),
                    }
                )

            asset_items = sorted(
                (
                    (str(asset), asset_metrics)
                    for asset, asset_metrics in by_asset.items()
                    if isinstance(asset_metrics, dict)
                ),
                key=lambda item: (
                    -_safe_int(item[1].get("count", 0)),
                    item[0],
                ),
            )
            for asset, asset_metrics in asset_items[:10]:
                hit_rate = _safe_float(asset_metrics.get("hit_rate", 0.0))
                rows.append(
                    {
                        "metric_key": "walk_forward_direction_hit_rate",
                        "label": f"Directional hit rate ({asset})",
                        "scope": f"asset:{asset}",
                        "value": round(hit_rate, 6),
                        "target": WALK_FORWARD_HIT_RATE_TARGET,
                        "comparator": "gte",
                        "status": _scoreboard_status(
                            hit_rate,
                            target=WALK_FORWARD_HIT_RATE_TARGET,
                            comparator="gte",
                        ),
                        "sample_size": _safe_int(asset_metrics.get("count", 0)),
                    }
                )

            payload.update(
                {
                    "rows": rows,
                    "count": len(rows),
                    "generated_at": now_iso,
                    "freshness": report_generated_at,
                    "last_update": report_generated_at,
                    "freshness_age": freshness_age,
                    "freshness_status": _freshness_status_from_age(freshness_age),
                    "summary": {
                        "hit_rate_percentage": round(
                            _safe_float(summary.get("hit_rate_percentage", overall_hit_rate * 100.0)),
                            3,
                        ),
                        "total_predictions_analyzed": _safe_int(
                            summary.get(
                                "total_predictions_analyzed",
                                metrics.get("total_predictions", 0),
                            )
                        ),
                        "average_confidence": round(
                            _safe_float(
                                summary.get(
                                    "average_confidence",
                                    metrics.get("avg_confidence", 0.0),
                                )
                            ),
                            6,
                        ),
                    },
                    "stats": {
                        "overall_rows": 2,
                        "horizon_rows": sum(
                            1 for row in rows if str(row.get("scope", "")).startswith("horizon:")
                        ),
                        "asset_rows": sum(
                            1 for row in rows if str(row.get("scope", "")).startswith("asset:")
                        ),
                        "passing_rows": sum(1 for row in rows if row.get("status") == "pass"),
                        "failing_rows": sum(1 for row in rows if row.get("status") == "fail"),
                    },
                }
            )
            if not rows:
                payload["message"] = "No walk-forward metrics available."
                payload["warnings"].append("walk_forward_metrics_missing")
            append_source_tag(
                payload,
                "forecasts_scoreboard_live_compute",
                default_source="forecasts_route",
            )
            if debug:
                payload["debug_pipeline"] = traces
            return payload
        except Exception as exc:
            logger.error("Error in walk-forward scoreboard compute: %s", exc, exc_info=True)
            payload["error"] = str(exc)
            payload["message"] = (
                "Walk-forward scoreboard unavailable, returning never-empty fallback."
            )
            payload["warnings"].append("walk_forward_scoreboard_compute_failed")
            payload["source"] = [
                "forecasts_route",
                "walk_forward_scoreboard",
                "critical_error_fallback",
            ]
            if debug:
                add_trace("compute_exception", error=str(exc))
                payload["debug_pipeline"] = traces
            return payload

    payload, is_leader = await compute_singleflight(
        _FORECASTS_SCOREBOARD_INFLIGHT,
        _FORECASTS_SCOREBOARD_INFLIGHT_LOCK,
        cache_key,
        compute_payload,
    )
    if is_leader and not debug and FORECASTS_CACHE_TTL_SECONDS > 0:
        response_cache_set(
            _FORECASTS_SCOREBOARD_RESPONSE_CACHE,
            cache_key,
            payload,
            max_entries=FORECASTS_CACHE_MAX_ENTRIES,
        )
    elif not is_leader:
        append_source_tag(
            payload,
            "forecasts_scoreboard_singleflight_waiter",
            default_source="forecasts_route",
        )
    return payload


async def get_forecasts_payload(
    *,
    asset_type: str,
    horizon: str,
    ticker: Optional[List[str]],
    search: Optional[str],
    sort_by: str,
    sort_order: str,
    limit: int,
    offset: int,
    debug: bool,
    load_json_fn: Callable[[str], Any] = load_json,
) -> Dict[str, Any]:
    now_iso = utc_now_iso()
    normalized_tickers = sorted(
        {str(item).strip().upper() for item in (ticker or []) if str(item).strip()}
    )
    filters_applied = {
        "asset_type": asset_type,
        "horizon": horizon,
        "search": search,
        "sort_by": str(sort_by),
        "sort_order": str(sort_order),
        "tickers": normalized_tickers,
        "limit": int(limit),
        "offset": int(offset),
    }
    cache_key = _build_forecasts_cache_key(
        asset_type=asset_type,
        horizon=horizon,
        tickers=normalized_tickers,
        search=search,
        sort_by=str(sort_by),
        sort_order=str(sort_order),
        limit=limit,
        offset=offset,
    )

    if not debug and FORECASTS_CACHE_TTL_SECONDS > 0:
        cached = response_cache_get(
            _FORECASTS_RESPONSE_CACHE,
            cache_key,
            ttl_seconds=FORECASTS_CACHE_TTL_SECONDS,
            hit_source_tag="forecasts_cache_hit",
            default_source="forecasts_route",
            copy_mode="smart",
        )
        if cached is not None:
            return cached

    traces: List[Dict[str, Any]] = []

    def add_trace(step: str, **meta: Any) -> None:
        if not debug:
            return
        traces.append({"step": step, "ts": utc_now_iso(), **meta})

    async def compute_payload() -> Dict[str, Any]:
        try:
            add_trace("load_snapshot_start")
            forecasts_data = (
                load_json_fn("forecasts") or load_json_fn("forecasts.json") or {}
            )
            if not isinstance(forecasts_data, dict):
                forecasts_data = {}
            raw_rows = _safe_rows(forecasts_data)
            add_trace("load_snapshot_done", loaded_count=len(raw_rows))

            snapshot_generated_at = str(
                forecasts_data.get("generated_at")
                or forecasts_data.get("timestamp")
                or now_iso
            )
            snapshot_last_update = str(
                forecasts_data.get("last_update")
                or forecasts_data.get("generated_at")
                or snapshot_generated_at
            )
            snapshot_source = _normalize_source(forecasts_data.get("source"))
            snapshot_age = _freshness_age_seconds(snapshot_generated_at, now_iso)
            stale_snapshot = snapshot_age > float(FORECASTS_STALE_SECONDS)

            if _requires_nominal_refresh(
                forecasts_data,
                raw_rows,
                snapshot_age=snapshot_age,
            ):
                refresh_tickers = sorted(
                    {
                        str(row.get("ticker", "")).strip().upper()
                        for row in raw_rows
                        if isinstance(row, dict) and str(row.get("ticker", "")).strip()
                    }
                )
                refreshed_payload = _refresh_nominal_snapshot(
                    tickers=refresh_tickers,
                    now_iso=now_iso,
                )
                if refreshed_payload:
                    forecasts_data = refreshed_payload
                    raw_rows = _safe_rows(forecasts_data)
                    snapshot_generated_at = str(
                        forecasts_data.get("generated_at")
                        or forecasts_data.get("timestamp")
                        or now_iso
                    )
                    snapshot_last_update = str(
                        forecasts_data.get("last_update")
                        or forecasts_data.get("generated_at")
                        or snapshot_generated_at
                    )
                    snapshot_source = _normalize_source(forecasts_data.get("source"))
                    snapshot_age = _freshness_age_seconds(snapshot_generated_at, now_iso)
                    stale_snapshot = snapshot_age > float(FORECASTS_STALE_SECONDS)

            mock_detected = _contains_mock_marker(snapshot_source) or any(
                _contains_mock_marker(_normalize_source(row.get("source")))
                for row in raw_rows
                if isinstance(row, dict)
            )
            if mock_detected and FORECASTS_BLOCK_MOCK_NOMINAL and not debug:
                blocked = _base_forecasts_payload(
                    now_iso=now_iso,
                    source=["forecasts_route", *snapshot_source, "mock_blocked_nominal"],
                    filters_applied=filters_applied,
                    limit=limit,
                    offset=offset,
                )
                blocked["freshness"] = snapshot_generated_at
                blocked["last_update"] = snapshot_last_update
                blocked["freshness_age"] = snapshot_age
                blocked["freshness_status"] = _freshness_status_from_age(snapshot_age)
                blocked["fallback_used"] = True
                blocked["provider_chain"] = ["mock_source_blocked"]
                blocked["observability"] = {
                    "provider_chain": ["mock_source_blocked"],
                    "fallback_used": True,
                    "latency_ms": 0.0,
                    "freshness_age": snapshot_age,
                }
                blocked["message"] = (
                    "Nominal forecast path blocked: mock source detected (gate policy)."
                )
                append_source_tag(
                    blocked,
                    "forecasts_mock_gate_blocked",
                    default_source="forecasts_route",
                )
                return blocked

            confidence_issues = [
                row
                for row in raw_rows
                if _safe_float(row.get("confidence", 0.0), default=0.0) <= 0
                or _safe_float(row.get("confidence", 0.0), default=0.0) > 1.0
            ]
            rows = [
                _normalize_forecast_row(
                    row,
                    snapshot_generated_at=snapshot_generated_at,
                    now_iso=now_iso,
                    inherited_source=snapshot_source,
                )
                for row in raw_rows
            ]
            total_loaded = len(rows)
            indexes = _build_filter_indexes(rows)
            add_trace(
                "indexes_built",
                asset_buckets=len(indexes.get("by_asset", {})),
                horizon_buckets=len(indexes.get("by_horizon", {})),
            )

            filtered_rows = _select_base_rows(
                rows,
                indexes,
                asset_type=asset_type,
                horizon=horizon,
            )

            if normalized_tickers:
                ticker_set = set(normalized_tickers)
                filtered_rows = [
                    row
                    for row in filtered_rows
                    if str(row.get("ticker", "")).upper() in ticker_set
                ]

            if search:
                search_l = search.lower()
                filtered_rows = [
                    row
                    for row in filtered_rows
                    if search_l in str(row.get("ticker", "")).lower()
                    or search_l in str(row.get("name", "")).lower()
                    or search_l in str(row.get("model", "")).lower()
                    or search_l in str(row.get("sector", "")).lower()
                ]

            paginated_rows = _select_page_rows(
                filtered_rows,
                sort_by=str(sort_by),
                sort_order=str(sort_order),
                limit=limit,
                offset=offset,
            )

            high_confidence_count = sum(
                1
                for row in filtered_rows
                if _safe_float(row.get("confidence", 0.0))
                >= HIGH_CONFIDENCE_THRESHOLD
            )
            filtered_count = len(filtered_rows)
            avg_confidence = (
                sum(_safe_float(row.get("confidence", 0.0)) for row in filtered_rows)
                / filtered_count
                if filtered_count > 0
                else 0.0
            )
            high_confidence_percentage = (
                float(high_confidence_count * 100.0 / filtered_count)
                if filtered_count > 0
                else 0.0
            )

            payload = _base_forecasts_payload(
                now_iso=now_iso,
                source=["forecasts_route", *snapshot_source],
                filters_applied=filters_applied,
                limit=limit,
                offset=offset,
            )
            payload.update(
                {
                    "rows": paginated_rows,
                    "count": len(paginated_rows),
                    "total": filtered_count,
                    "freshness": snapshot_generated_at,
                    "freshness_age": snapshot_age,
                    "freshness_status": _freshness_status_from_age(
                        snapshot_age
                    ),
                    "last_update": snapshot_last_update,
                    "stats": {
                        "total_loaded": total_loaded,
                        "filtered_count": filtered_count,
                        "returned_count": len(paginated_rows),
                        "high_confidence_count": high_confidence_count,
                        "high_confidence_percentage": round(
                            high_confidence_percentage, 3
                        ),
                        "avg_confidence": round(avg_confidence, 6),
                    },
                }
            )
            provider_chain = sorted(
                {
                    str(item).strip()
                    for row in paginated_rows
                    for item in row.get("provider_chain", [])
                    if str(item).strip()
                }
            )
            avg_latency_ms = (
                sum(_safe_float(row.get("latency_ms", 0.0)) for row in paginated_rows)
                / len(paginated_rows)
                if paginated_rows
                else 0.0
            )
            fallback_used = any(_safe_bool(row.get("fallback_used"), False) for row in paginated_rows)
            payload["provider_chain"] = provider_chain
            payload["fallback_used"] = bool(fallback_used)
            payload["latency_ms"] = round(avg_latency_ms, 3)
            payload["freshness_status"] = _freshness_status_from_age(snapshot_age)
            payload["observability"] = {
                "provider_chain": provider_chain,
                "fallback_used": bool(fallback_used),
                "latency_ms": round(avg_latency_ms, 3),
                "freshness_age": payload.get("freshness_age", -1.0),
            }
            if stale_snapshot:
                payload["fallback_used"] = True
                payload["observability"]["fallback_used"] = True
                payload["warnings"].append(
                    f"Forecast snapshot stale ({snapshot_age:.0f}s > {FORECASTS_STALE_SECONDS}s); results are degraded."
                )
                append_source_tag(
                    payload,
                    "forecasts_stale_data",
                    default_source="forecasts_route",
                )
            if confidence_issues:
                payload["fallback_used"] = True
                payload["observability"]["fallback_used"] = True
                payload["warnings"].append(
                    f"{len(confidence_issues)} rows had invalid confidence and were normalized."
                )

            if len(paginated_rows) == 0:
                payload["message"] = "No forecasts matched current filters."

            if callable(ensure_decision_contract):
                head = paginated_rows[0] if paginated_rows else {}
                ensure_decision_contract(
                    payload,
                    default_source="forecasts_service",
                    verdict=head.get("action") or head.get("verdict"),
                    confidence=head.get("confidence") or payload.get("stats", {}).get("avg_confidence"),
                    why=head.get("why"),
                    risk_level=head.get("risk_level"),
                    risk_caveat=head.get("risk_caveat"),
                    freshness=payload.get("freshness"),
                )

            append_source_tag(
                payload, "forecasts_live_compute", default_source="forecasts_route"
            )
            add_trace(
                "filters_applied",
                total_loaded=total_loaded,
                filtered_count=filtered_count,
                returned_count=len(paginated_rows),
            )
            if debug:
                payload["debug_pipeline"] = traces
            return payload
        except Exception as compute_exc:
            logger.error("Error in forecasts compute: %s", compute_exc, exc_info=True)
            fallback = _base_forecasts_payload(
                now_iso=now_iso,
                source=["forecasts_route", "critical_error_fallback"],
                filters_applied=filters_applied,
                limit=limit,
                offset=offset,
            )
            fallback["error"] = str(compute_exc)
            fallback["message"] = (
                "Forecasts temporarily unavailable, returning empty response per never-empty pattern."
            )
            fallback["fallback_used"] = True
            fallback["provider_chain"] = ["compute_exception_fallback"]
            fallback["observability"] = {
                "provider_chain": ["compute_exception_fallback"],
                "fallback_used": True,
                "latency_ms": 0.0,
                "freshness_age": fallback.get("freshness_age", -1.0),
            }
            if debug:
                add_trace("compute_exception", error=str(compute_exc))
                fallback["debug_pipeline"] = traces
            return fallback

    try:
        if not debug and FORECASTS_CACHE_TTL_SECONDS > 0:
            payload, is_leader = await compute_singleflight(
                _FORECASTS_INFLIGHT,
                _FORECASTS_INFLIGHT_LOCK,
                cache_key,
                compute_payload,
            )
            if is_leader:
                response_cache_set(
                    _FORECASTS_RESPONSE_CACHE,
                    cache_key,
                    payload,
                    max_entries=FORECASTS_CACHE_MAX_ENTRIES,
                )
            else:
                append_source_tag(
                    payload,
                    "forecasts_singleflight_waiter",
                    default_source="forecasts_route",
                )
        else:
            payload = await compute_payload()
        return payload
    except Exception as route_exc:
        logger.error("Error in get_forecasts_payload: %s", route_exc, exc_info=True)
        fallback = _base_forecasts_payload(
            now_iso=now_iso,
            source=["forecasts_route", "critical_route_error_fallback"],
            filters_applied=filters_applied,
            limit=limit,
            offset=offset,
        )
        fallback["error"] = str(route_exc)
        fallback["message"] = (
            "Forecasts route failed critically but fallback data returned to maintain never-empty contract."
        )
        fallback["fallback_used"] = True
        fallback["provider_chain"] = ["route_exception_fallback"]
        fallback["observability"] = {
            "provider_chain": ["route_exception_fallback"],
            "fallback_used": True,
            "latency_ms": 0.0,
            "freshness_age": fallback.get("freshness_age", -1.0),
        }
        if debug:
            fallback["debug_pipeline"] = traces
        return fallback


def get_forecast_detail_payload(
    *,
    forecast_id: str,
    load_json_fn: Callable[[str], Any] = load_json,
) -> Dict[str, Any]:
    now_iso = utc_now_iso()
    source = ["forecasts_route", "forecasts_storage"]
    try:
        forecasts_data = load_json_fn("forecasts") or load_json_fn("forecasts.json") or {}
        if not isinstance(forecasts_data, dict):
            forecasts_data = {}
        rows = [
            _normalize_forecast_row(
                row,
                snapshot_generated_at=str(
                    forecasts_data.get("generated_at")
                    or forecasts_data.get("timestamp")
                    or now_iso
                ),
                now_iso=now_iso,
                inherited_source=_normalize_source(forecasts_data.get("source")),
            )
            for row in _safe_rows(forecasts_data)
        ]
        snapshot_generated_at = str(
            forecasts_data.get("generated_at") or forecasts_data.get("timestamp") or now_iso
        )
        snapshot_last_update = str(
            forecasts_data.get("last_update")
            or forecasts_data.get("generated_at")
            or snapshot_generated_at
        )
        source = ["forecasts_route", *_normalize_source(forecasts_data.get("source"))]

        match = next(
            (
                row
                for row in rows
                if str(row.get("forecast_id", "")).strip() == forecast_id
                or str(row.get("ticker", "")).upper() == forecast_id.upper()
            ),
            None,
        )

        if match is None:
            return {
                "forecast": {},
                "found": False,
                "generated_at": now_iso,
                "freshness": snapshot_generated_at,
                "last_update": snapshot_last_update,
                "source": source,
                "warnings": [],
                "message": f"Forecast {forecast_id} not found.",
            }

        return {
            "forecast": match,
            "found": True,
            "generated_at": now_iso,
            "freshness": snapshot_generated_at,
            "last_update": snapshot_last_update,
            "source": source,
            "warnings": [],
        }
    except Exception as exc:
        logger.error("Error in get_forecast_detail_payload: %s", exc, exc_info=True)
        return {
            "forecast": {},
            "found": False,
            "generated_at": now_iso,
            "freshness": now_iso,
            "last_update": now_iso,
            "source": [*source, "critical_error_fallback"],
            "warnings": [],
            "error": str(exc),
            "message": "Forecast temporarily unavailable, returning empty response per never-empty pattern.",
        }


__all__ = [
    "FORECASTS_CACHE_MAX_ENTRIES",
    "FORECASTS_CACHE_TTL_SECONDS",
    "FORECASTS_STALE_SECONDS",
    "FORECASTS_BLOCK_MOCK_NOMINAL",
    "HIGH_CONFIDENCE_THRESHOLD",
    "_FORECASTS_RESPONSE_CACHE",
    "_FORECASTS_INFLIGHT",
    "_FORECASTS_INFLIGHT_LOCK",
    "get_forecasts_payload",
    "get_forecast_detail_payload",
]
