"""
Judge quality service.

Computes rolling quality metrics for forecast/judge outputs using locally cached
forecasts and prices. Designed to stay robust when data is partial.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from storage.io import load_json
from core.ticker_normalization import normalize_ticker


@dataclass
class EvaluatedForecast:
    ticker: str
    ts: datetime
    confidence: float
    expected_return: float
    realized_return: float
    hit: bool
    baseline_hit: Optional[bool]
    horizon_days: int


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        try:
            dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            return None
    else:
        s = str(value).strip()
        if not s:
            return None
        if len(s) == 10 and s.count("-") == 2:
            s = f"{s}T00:00:00Z"
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _direction_sign(direction: Optional[str], expected_return: float) -> int:
    d = (direction or "").strip().lower()
    if d in {"up", "bull", "bullish", "long"}:
        return 1
    if d in {"down", "bear", "bearish", "short"}:
        return -1
    if d in {"flat", "neutral", "hold"}:
        return 0
    if expected_return > 1e-9:
        return 1
    if expected_return < -1e-9:
        return -1
    return 0


def _sign(x: float) -> int:
    if x > 1e-12:
        return 1
    if x < -1e-12:
        return -1
    return 0


def _extract_rows_from_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    rows = payload.get("rows")
    if not isinstance(rows, list):
        rows = (payload.get("data") or {}).get("rows")
    if not isinstance(rows, list):
        return []
    out: List[Dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            out.append(row)
    return out


def _load_forecast_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    current = load_json("forecasts") or {}
    rows.extend(_extract_rows_from_payload(current))

    backend_root = Path(__file__).resolve().parents[2]
    history_dir = backend_root / "data" / "forecast"
    for fp in sorted(history_dir.glob("dt=*/forecasts.json")):
        try:
            payload = json.loads(fp.read_text(encoding="utf-8"))
            rows.extend(_extract_rows_from_payload(payload))
        except Exception:
            continue
    return rows


def _load_prices_points() -> Dict[str, List[Tuple[datetime, float]]]:
    payload = load_json("stocks/prices") or {}
    tickers_block = payload.get("tickers") if isinstance(payload, dict) else {}
    if not isinstance(tickers_block, dict):
        return {}

    out: Dict[str, List[Tuple[datetime, float]]] = {}
    for ticker, block in tickers_block.items():
        if not isinstance(block, dict):
            continue
        points = block.get("points")
        if not isinstance(points, list):
            continue
        parsed: List[Tuple[datetime, float]] = []
        for point in points:
            if not isinstance(point, list) or len(point) < 2:
                continue
            ts = _parse_dt(point[0])
            if ts is None:
                continue
            try:
                px = float(point[1])
            except Exception:
                continue
            if px <= 0:
                continue
            parsed.append((ts, px))
        if parsed:
            parsed.sort(key=lambda x: x[0])
            normalized = normalize_ticker(str(ticker))
            if not normalized:
                continue
            out[normalized] = parsed
    return out


def _bucket_calibration(records: Sequence[EvaluatedForecast]) -> List[Dict[str, Any]]:
    bins = [
        (0.0, 0.3),
        (0.3, 0.5),
        (0.5, 0.7),
        (0.7, 0.85),
        (0.85, 1.01),
    ]
    out: List[Dict[str, Any]] = []
    for lo, hi in bins:
        sub = [r for r in records if lo <= r.confidence < hi]
        if not sub:
            out.append(
                {
                    "bucket": f"[{lo:.2f},{min(1.0, hi):.2f})",
                    "n": 0,
                    "avg_confidence": None,
                    "hit_rate": None,
                    "gap": None,
                }
            )
            continue
        avg_conf = sum(r.confidence for r in sub) / len(sub)
        hit_rate = sum(1.0 for r in sub if r.hit) / len(sub)
        out.append(
            {
                "bucket": f"[{lo:.2f},{min(1.0, hi):.2f})",
                "n": len(sub),
                "avg_confidence": round(avg_conf, 4),
                "hit_rate": round(hit_rate, 4),
                "gap": round(hit_rate - avg_conf, 4),
            }
        )
    return out


def _aggregate_metrics(
    records: Sequence[EvaluatedForecast],
    *,
    min_samples: int,
) -> Dict[str, Any]:
    n = len(records)
    if n == 0:
        return {
            "n": 0,
            "hit_rate": None,
            "avg_confidence": None,
            "brier": None,
            "mae_expected_return": None,
            "baseline_hit_rate": None,
            "edge_vs_baseline": None,
            "calibration_error": None,
            "sample_status": "insufficient",
        }

    hit_rate = sum(1.0 for r in records if r.hit) / n
    avg_conf = sum(r.confidence for r in records) / n
    brier = sum((r.confidence - (1.0 if r.hit else 0.0)) ** 2 for r in records) / n
    mae_er = sum(abs(r.expected_return - r.realized_return) for r in records) / n

    baseline_vals = [r.baseline_hit for r in records if r.baseline_hit is not None]
    baseline_hit_rate: Optional[float] = None
    edge_vs_baseline: Optional[float] = None
    if baseline_vals:
        baseline_hit_rate = sum(1.0 for x in baseline_vals if x) / len(baseline_vals)
        edge_vs_baseline = hit_rate - baseline_hit_rate

    sample_status = "ok" if n >= min_samples else "insufficient"
    return {
        "n": n,
        "hit_rate": round(hit_rate, 4),
        "avg_confidence": round(avg_conf, 4),
        "brier": round(brier, 4),
        "mae_expected_return": round(mae_er, 4),
        "baseline_hit_rate": round(baseline_hit_rate, 4) if baseline_hit_rate is not None else None,
        "edge_vs_baseline": round(edge_vs_baseline, 4) if edge_vs_baseline is not None else None,
        "calibration_error": round(abs(hit_rate - avg_conf), 4),
        "sample_status": sample_status,
    }


def _evaluate_rows(
    rows: Iterable[Dict[str, Any]],
    prices_by_ticker: Dict[str, List[Tuple[datetime, float]]],
    *,
    now_utc: datetime,
    horizon_days: int,
    baseline_lookback_days: int,
) -> Tuple[List[EvaluatedForecast], Dict[str, int]]:
    evaluated: List[EvaluatedForecast] = []
    coverage = {
        "total_rows": 0,
        "with_timestamp": 0,
        "with_price_series": 0,
        "with_entry_price": 0,
        "with_exit_price": 0,
    }

    for row in rows:
        if not isinstance(row, dict):
            continue
        coverage["total_rows"] += 1
        ticker = normalize_ticker(str(row.get("ticker") or row.get("symbol") or ""))
        if not ticker:
            continue

        ts = (
            _parse_dt(row.get("timestamp"))
            or _parse_dt(row.get("ts"))
            or _parse_dt(row.get("generated_at"))
        )
        if ts is None:
            continue
        coverage["with_timestamp"] += 1
        if ts > now_utc:
            continue

        series = prices_by_ticker.get(ticker)
        if not series:
            continue
        coverage["with_price_series"] += 1

        entry_idx: Optional[int] = None
        for idx, (p_ts, _p) in enumerate(series):
            if p_ts >= ts:
                entry_idx = idx
                break
        if entry_idx is None:
            continue
        coverage["with_entry_price"] += 1
        entry_ts, entry_px = series[entry_idx]

        target_ts = entry_ts + timedelta(days=horizon_days)
        exit_idx: Optional[int] = None
        for idx in range(entry_idx + 1, len(series)):
            if series[idx][0] >= target_ts:
                exit_idx = idx
                break
        if exit_idx is None:
            continue
        coverage["with_exit_price"] += 1
        _exit_ts, exit_px = series[exit_idx]
        realized_return = (exit_px / entry_px) - 1.0

        expected_return = _safe_float(row.get("expected_return"), 0.0)
        confidence = _clamp(_safe_float(row.get("confidence"), 0.5), 0.0, 1.0)
        pred_sign = _direction_sign(row.get("direction"), expected_return)
        ret_sign = _sign(realized_return)
        if pred_sign == 0:
            hit = ret_sign == 0
        else:
            hit = pred_sign == ret_sign

        baseline_hit: Optional[bool] = None
        if entry_idx >= baseline_lookback_days:
            prev_px = series[entry_idx - baseline_lookback_days][1]
            baseline_sign = _sign((entry_px / prev_px) - 1.0)
            if baseline_sign != 0:
                baseline_hit = baseline_sign == ret_sign

        evaluated.append(
            EvaluatedForecast(
                ticker=ticker,
                ts=ts,
                confidence=confidence,
                expected_return=expected_return,
                realized_return=realized_return,
                hit=hit,
                baseline_hit=baseline_hit,
                horizon_days=horizon_days,
            )
        )

    return evaluated, coverage


def build_judge_quality_report_from_data(
    *,
    rows: Sequence[Dict[str, Any]],
    prices_by_ticker: Dict[str, List[Tuple[datetime, float]]],
    horizon_days: int = 5,
    window_days: Sequence[int] = (30, 60, 90),
    min_samples: int = 20,
    baseline_lookback_days: int = 5,
    now_utc: Optional[datetime] = None,
) -> Dict[str, Any]:
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)

    evaluated, coverage = _evaluate_rows(
        rows,
        prices_by_ticker,
        now_utc=now,
        horizon_days=max(1, int(horizon_days)),
        baseline_lookback_days=max(1, int(baseline_lookback_days)),
    )
    evaluated.sort(key=lambda r: r.ts)

    windows: Dict[str, Any] = {}
    for wd in window_days:
        wd_i = max(1, int(wd))
        cutoff = now - timedelta(days=wd_i)
        subset = [r for r in evaluated if r.ts >= cutoff]
        windows[f"{wd_i}d"] = {
            **_aggregate_metrics(subset, min_samples=min_samples),
            "calibration_buckets": _bucket_calibration(subset),
        }

    overall = _aggregate_metrics(evaluated, min_samples=min_samples)
    overall["calibration_buckets"] = _bucket_calibration(evaluated)

    recommendation = {
        "status": "insufficient_sample",
        "message": "Not enough evaluated samples to claim predictive edge yet.",
    }
    n = int(overall.get("n") or 0)
    hit_rate = overall.get("hit_rate")
    edge = overall.get("edge_vs_baseline")
    if n >= min_samples and isinstance(hit_rate, float):
        if isinstance(edge, float) and edge < -0.02:
            recommendation = {
                "status": "underperforming_baseline",
                "message": "Judge directional calls are underperforming a simple momentum baseline.",
            }
        elif hit_rate >= 0.56 and (edge is None or edge > 0.0):
            recommendation = {
                "status": "promising",
                "message": "Judge shows early edge, but keep monitoring on larger samples.",
            }
        else:
            recommendation = {
                "status": "neutral",
                "message": "Judge is near baseline. Keep collecting data before trusting high-conviction calls.",
            }

    evaluated_tickers = sorted({r.ticker for r in evaluated})
    return {
        "as_of": now.isoformat().replace("+00:00", "Z"),
        "horizon_days": max(1, int(horizon_days)),
        "window_days": [max(1, int(w)) for w in window_days],
        "min_samples": max(1, int(min_samples)),
        "coverage": {
            **coverage,
            "evaluated_rows": len(evaluated),
            "evaluated_tickers": evaluated_tickers,
        },
        "overall": overall,
        "windows": windows,
        "recommendation": recommendation,
    }


def build_judge_quality_report(
    *,
    horizon_days: int = 5,
    window_days: Sequence[int] = (30, 60, 90),
    min_samples: int = 20,
    baseline_lookback_days: int = 5,
) -> Dict[str, Any]:
    rows = _load_forecast_rows()
    prices = _load_prices_points()
    return build_judge_quality_report_from_data(
        rows=rows,
        prices_by_ticker=prices,
        horizon_days=horizon_days,
        window_days=window_days,
        min_samples=min_samples,
        baseline_lookback_days=baseline_lookback_days,
    )
