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

from storage.io import save_json  # noqa: E402
from src.services.judge_quality import build_judge_quality_report  # noqa: E402


def run_judge_quality_report(
    *,
    horizon_days: int = 5,
    min_samples: int = 20,
) -> Dict[str, Any]:
    report = build_judge_quality_report(
        horizon_days=horizon_days,
        min_samples=min_samples,
    )
    save_json(
        "judge_quality",
        report,
        source=["job:judge_quality_report", "judge_metrics"],
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon-days", type=int, default=5)
    parser.add_argument("--min-samples", type=int, default=20)
    args = parser.parse_args()

    report = run_judge_quality_report(
        horizon_days=max(1, int(args.horizon_days)),
        min_samples=max(1, int(args.min_samples)),
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

