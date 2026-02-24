from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso_utc(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if isinstance(value, bool):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if isinstance(value, bool):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _point_key(point: Dict[str, Any]) -> Tuple[str, int, int]:
    return (
        str(point.get("date") or ""),
        _safe_int(point.get("horizon_days"), 0),
        _safe_int(point.get("min_samples"), 0),
    )


def build_tracking_point(report: Dict[str, Any]) -> Dict[str, Any]:
    as_of_value = str(report.get("as_of") or _utc_now_iso())
    as_of_dt = _parse_iso_utc(as_of_value) or datetime.now(timezone.utc)
    as_of = as_of_dt.isoformat().replace("+00:00", "Z")
    coverage = report.get("coverage") if isinstance(report.get("coverage"), dict) else {}
    overall = report.get("overall") if isinstance(report.get("overall"), dict) else {}
    recommendation = (
        report.get("recommendation") if isinstance(report.get("recommendation"), dict) else {}
    )

    return {
        "as_of": as_of,
        "date": as_of[:10],
        "horizon_days": _safe_int(report.get("horizon_days"), 5),
        "min_samples": _safe_int(report.get("min_samples"), 20),
        "evaluated_rows": _safe_int(coverage.get("evaluated_rows"), 0),
        "total_rows": _safe_int(coverage.get("total_rows"), 0),
        "with_price_series": _safe_int(coverage.get("with_price_series"), 0),
        "edge_vs_baseline": _safe_float(overall.get("edge_vs_baseline")),
        "hit_rate": _safe_float(overall.get("hit_rate")),
        "brier": _safe_float(overall.get("brier")),
        "calibration_error": _safe_float(overall.get("calibration_error")),
        "sample_status": str(overall.get("sample_status") or "unknown"),
        "recommendation_status": str(recommendation.get("status") or "unknown"),
    }


def _sort_points(points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def _sort_key(point: Dict[str, Any]) -> datetime:
        return _parse_iso_utc(str(point.get("as_of") or "")) or datetime(1970, 1, 1, tzinfo=timezone.utc)

    return sorted(points, key=_sort_key)


def _average(values: List[float | None]) -> float | None:
    nums = [v for v in values if isinstance(v, float)]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 4)


def build_tracking_payload(
    *,
    existing: Dict[str, Any] | None,
    report: Dict[str, Any],
    max_points: int = 730,
) -> Dict[str, Any]:
    max_points = max(1, int(max_points))
    existing_points_raw = (existing or {}).get("points")
    existing_points = existing_points_raw if isinstance(existing_points_raw, list) else []
    points = [p for p in existing_points if isinstance(p, dict)]

    point = build_tracking_point(report)
    point_idx = {_point_key(item): idx for idx, item in enumerate(points)}
    key = _point_key(point)
    if key in point_idx:
        points[point_idx[key]] = point
    else:
        points.append(point)

    points = _sort_points(points)
    if len(points) > max_points:
        points = points[-max_points:]

    scope_points = [
        p
        for p in points
        if _safe_int(p.get("horizon_days"), -1) == point["horizon_days"]
        and _safe_int(p.get("min_samples"), -1) == point["min_samples"]
    ]
    trailing_scope = scope_points[-7:]

    return {
        "as_of": point["as_of"],
        "latest": point,
        "series_scope": {
            "horizon_days": point["horizon_days"],
            "min_samples": point["min_samples"],
        },
        "kpis": {
            "points_total": len(points),
            "points_in_scope": len(scope_points),
            "avg_evaluated_rows_last_7": _average(
                [_safe_float(item.get("evaluated_rows")) for item in trailing_scope]
            ),
            "avg_edge_vs_baseline_last_7": _average(
                [_safe_float(item.get("edge_vs_baseline")) for item in trailing_scope]
            ),
        },
        "points": points,
    }
