#!/usr/bin/env python3
"""
Generate and persist judge quality report.

Usage:
  PYTHONPATH=src:. python jobs/judge_quality_report.py --horizon-days 5 --min-samples 20
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict


backend_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_root))
sys.path.insert(0, str(backend_root / "src"))

from storage.io import load_json, save_json  # noqa: E402
from src.services.judge_quality import build_judge_quality_report  # noqa: E402
from src.services.judge_quality_tracking import build_tracking_payload  # noqa: E402
try:
    from core.sentry_runtime import install_global_excepthook, init_sentry, set_job_context, capture_exception  # noqa: E402
except Exception:  # pragma: no cover
    def install_global_excepthook(job_name: str) -> bool:
        return False

    def init_sentry(component: str) -> bool:
        return False

    def set_job_context(job_name: str, **context: Any) -> None:
        return None

    def capture_exception(exc: BaseException, *, job_name: str | None = None, context: Dict[str, Any] | None = None) -> None:
        return None


def run_judge_quality_report(
    *,
    horizon_days: int = 5,
    min_samples: int = 20,
) -> Dict[str, Any]:
    init_sentry("judge_quality_report")
    set_job_context("judge_quality_report", horizon_days=horizon_days, min_samples=min_samples)
    report = build_judge_quality_report(
        horizon_days=horizon_days,
        min_samples=min_samples,
    )
    save_json(
        "judge_quality",
        report,
        source=["job:judge_quality_report", "judge_metrics"],
    )
    tracking_payload = build_tracking_payload(
        existing=load_json("judge_quality_tracking"),
        report=report,
    )
    save_json(
        "judge_quality_tracking",
        tracking_payload,
        source=["job:judge_quality_report", "judge_metrics_tracking"],
    )
    return report


def main() -> int:
    init_sentry("judge_quality_report")
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon-days", type=int, default=5)
    parser.add_argument("--min-samples", type=int, default=20)
    args = parser.parse_args()

    try:
        report = run_judge_quality_report(
            horizon_days=max(1, int(args.horizon_days)),
            min_samples=max(1, int(args.min_samples)),
        )
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except Exception as exc:
        capture_exception(
            exc,
            job_name="judge_quality_report",
            context={
                "horizon_days": int(args.horizon_days),
                "min_samples": int(args.min_samples),
            },
        )
        raise


if __name__ == "__main__":
    install_global_excepthook("judge_quality_report")
    raise SystemExit(main())
