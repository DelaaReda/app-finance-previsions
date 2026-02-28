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
from typing import Any, Awaitable, Callable, Dict, List, Optional

from storage.io import load_json

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

_FORECASTS_RESPONSE_CACHE: Dict[str, Dict[str, Any]] = {}
_FORECASTS_INFLIGHT: Dict[str, asyncio.Task] = {}
_FORECASTS_INFLIGHT_LOCK = asyncio.Lock()

RISK_LEVEL_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


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


def _normalize_forecast_row(row: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(row)
    ticker = str(normalized.get("ticker", "")).strip().upper()
    if ticker:
        normalized["ticker"] = ticker

    normalized["confidence"] = _safe_float(normalized.get("confidence", 0.0))
    normalized["score"] = _safe_float(normalized.get("score", 0.0))
    normalized["expected_return"] = _safe_float(
        normalized.get("expected_return", normalized.get("return", 0.0))
    )

    risk = str(normalized.get("risk_level", "medium")).strip().lower() or "medium"
    if risk not in RISK_LEVEL_RANK:
        risk = "medium"
    normalized["risk_level"] = risk
    normalized.setdefault("timestamp", str(normalized.get("generated_at", "")))
    return normalized


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
        "last_update": now_iso,
        "source": source,
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

            rows = [_normalize_forecast_row(row) for row in raw_rows]
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

            if len(paginated_rows) == 0:
                payload["message"] = "No forecasts matched current filters."
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
        rows = [_normalize_forecast_row(row) for row in _safe_rows(forecasts_data)]
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
                if str(row.get("id", "")).strip() == forecast_id
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
    "HIGH_CONFIDENCE_THRESHOLD",
    "_FORECASTS_RESPONSE_CACHE",
    "_FORECASTS_INFLIGHT",
    "_FORECASTS_INFLIGHT_LOCK",
    "get_forecasts_payload",
    "get_forecast_detail_payload",
]
