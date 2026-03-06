#!/usr/bin/env python3
"""Legacy adapter job to generate and persist judge quality snapshots.

This job bridges legacy launcher/scripts with the new domain implementation
(`services.judge_quality`) while preserving the historical job contract:

    run_judge_quality_report(horizon_days=5, min_samples=20)
"""
from __future__ import annotations

from datetime import datetime, timezone
import argparse
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from services.judge_quality import build_judge_quality_report  # type: ignore
except Exception:  # pragma: no cover
    try:
        from domains.judge.application.judge_quality import (  # type: ignore
            build_judge_quality_report,
        )
    except Exception:  # pragma: no cover
        build_judge_quality_report = None  # type: ignore

try:
    from storage.io import save_json  # type: ignore
except Exception:  # pragma: no cover
    from storage.base import save_json  # type: ignore


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _build_fallback_report(horizon_days: int, min_samples: int) -> Dict[str, Any]:
    now_iso = _utc_now_iso()
    return {
        "as_of": now_iso,
        "horizon_days": int(horizon_days),
        "window_days": [30, 60, 90],
        "min_samples": int(min_samples),
        "coverage": {
            "total_rows": 0,
            "with_timestamp": 0,
            "with_price_series": 0,
            "with_entry_price": 0,
            "with_exit_price": 0,
            "evaluated_rows": 0,
            "evaluated_tickers": [],
        },
        "overall": {
            "n": 0,
            "hit_rate": None,
            "avg_confidence": None,
            "brier": None,
            "mae_expected_return": None,
            "baseline_hit_rate": None,
            "edge_vs_baseline": None,
            "calibration_error": None,
            "sample_status": "insufficient",
            "calibration_buckets": [],
        },
        "windows": {},
        "recommendation": {
            "status": "unavailable",
            "message": "Judge quality service unavailable; fallback report generated.",
        },
        "generated_by_fallback": True,
        "generated_at": now_iso,
    }


def _persist_report(report: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(report)
    now_iso = _utc_now_iso()
    payload.setdefault("as_of", now_iso)
    payload.setdefault("generated_at", now_iso)
    payload["job_execution_time"] = now_iso
    payload["job_type"] = "judge_quality_report"

    save_json(
        "judge_quality",
        payload,
        source=["job:judge_quality_report", "domains.judge.application.judge_quality"],
    )
    return payload


def run_judge_quality_report(
    *,
    horizon_days: int = 5,
    min_samples: int = 20,
    baseline_lookback_days: int = 5,
) -> Optional[Dict[str, Any]]:
    """Generate and persist judge quality report."""
    if not build_judge_quality_report:
        logger.warning("Judge quality service import unavailable, writing fallback payload.")
        fallback = _build_fallback_report(horizon_days=horizon_days, min_samples=min_samples)
        return _persist_report(fallback)

    try:
        report = build_judge_quality_report(
            horizon_days=int(horizon_days),
            min_samples=int(min_samples),
            baseline_lookback_days=int(baseline_lookback_days),
        )
        if not isinstance(report, dict) or not report:
            logger.warning("Judge quality service returned empty payload, writing fallback.")
            report = _build_fallback_report(horizon_days=horizon_days, min_samples=min_samples)
        payload = _persist_report(report)
        logger.info(
            "Judge quality report generated (horizon_days=%s, min_samples=%s, n=%s).",
            horizon_days,
            min_samples,
            (payload.get("overall") or {}).get("n"),
        )
        return payload
    except Exception as exc:
        logger.exception("Judge quality report failed, writing fallback: %s", exc)
        fallback = _build_fallback_report(horizon_days=horizon_days, min_samples=min_samples)
        fallback["error"] = str(exc)
        return _persist_report(fallback)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate judge quality report snapshot")
    parser.add_argument("--horizon-days", type=int, default=5)
    parser.add_argument("--min-samples", type=int, default=20)
    parser.add_argument("--baseline-lookback-days", type=int, default=5)
    args = parser.parse_args()

    payload = run_judge_quality_report(
        horizon_days=args.horizon_days,
        min_samples=args.min_samples,
        baseline_lookback_days=args.baseline_lookback_days,
    )
    if not isinstance(payload, dict) or not payload:
        return 1
    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    raise SystemExit(main())
