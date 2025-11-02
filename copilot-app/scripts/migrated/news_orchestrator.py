#!/usr/bin/env python3
"""Command line orchestrator for the news lakehouse pipeline.

Runs the Bronze → Silver → Gold stages for one or multiple dates.  The script
is idempotent: rerunning a date simply regenerates the Parquet partitions.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ingestion.bronze_pipeline import BronzeIngestionConfig, ingest_bronze_for_date
from ingestion.gold_features_pipeline import GoldConfig, build_daily_features
from ingestion.silver_pipeline import SilverConfig, transform_to_silver
from pipelines.news.build_features_daily_v2 import build_features_daily_v2
from pipelines.news.extract_events_v1 import extract_events_v1
from pipelines.news.to_silver_v2 import to_silver_v2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the news ingestion pipeline")
    parser.add_argument("--date", type=str, help="Single date to process (YYYY-MM-DD)")
    parser.add_argument("--start-date", type=str, help="Start date (inclusive)")
    parser.add_argument("--end-date", type=str, help="End date (inclusive)")
    parser.add_argument("--backfill", type=str, help="Shortcut: 7d, 30d, 1y")
    parser.add_argument("--regions", type=str, nargs="+", help="Regions to ingest (US, CA, FR, DE, INTL, ...)")
    parser.add_argument("--skip-bronze", action="store_true", help="Skip bronze ingestion stage")
    parser.add_argument("--skip-silver", action="store_true", help="Skip silver transform stage")
    parser.add_argument("--skip-gold", action="store_true", help="Skip gold aggregation stage")
    parser.add_argument("--no-html", action="store_true", help="Disable article HTML download")
    parser.add_argument("--per-source", type=int, default=50, help="Max articles per source (default: 50)")
    parser.add_argument("--window-hours", type=int, default=24, help="Bronze fetch window in hours")
    parser.add_argument(
        "--pipeline-version",
        choices=["v1", "v2"],
        default="v2",
        help="Choose between legacy v1 and new lakehouse v2 pipeline",
    )
    parser.add_argument("--skip-events", action="store_true", help="Skip events extraction stage (v2 only)")
    return parser.parse_args()


def _date_range(args: argparse.Namespace) -> List[date]:
    if args.date:
        return [datetime.strptime(args.date, "%Y-%m-%d").date()]
    if args.backfill:
        now = date.today()
        value = int(args.backfill[:-1])
        unit = args.backfill[-1]
        if unit == "d":
            start = now - timedelta(days=value)
        elif unit == "w":
            start = now - timedelta(weeks=value)
        elif unit == "m":
            start = now - timedelta(days=value * 30)
        elif unit == "y":
            start = now - timedelta(days=value * 365)
        else:
            raise ValueError(f"Unsupported backfill window: {args.backfill}")
        return _inclusive_range(start, now)
    if args.start_date and args.end_date:
        start = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        end = datetime.strptime(args.end_date, "%Y-%m-%d").date()
        return _inclusive_range(start, end)
    return [date.today()]


def _inclusive_range(start: date, end: date) -> List[date]:
    if end < start:
        raise ValueError("end-date must be >= start-date")
    days = (end - start).days
    return [start + timedelta(days=i) for i in range(days + 1)]


def main() -> None:
    args = parse_args()
    dates = _date_range(args)

    use_v2 = args.pipeline_version == "v2"

    bronze_config = BronzeIngestionConfig(
        regions=args.regions,
        per_source_limit=args.per_source,
        pull_window_hours=args.window_hours,
        fetch_html=not args.no_html,
    )
    silver_config = SilverConfig() if not use_v2 else None
    gold_config = GoldConfig() if not use_v2 else None

    for target_date in dates:
        print(f"=== Processing {target_date} ===")

        if not args.skip_bronze:
            bronze_path = ingest_bronze_for_date(target_date, bronze_config)
            print(f"[bronze] wrote {bronze_path}")
        else:
            print("[bronze] skipped")

        if use_v2:
            if not args.skip_silver:
                to_silver_v2(target_date.isoformat())
                print("[silver_v2] completed")
            else:
                print("[silver_v2] skipped")

            if not args.skip_gold:
                build_features_daily_v2(target_date.isoformat())
                print("[gold_v2] completed")
            else:
                print("[gold_v2] skipped")

            if not args.skip_events:
                extract_events_v1(target_date.isoformat())
                print("[events_v1] completed")
            else:
                print("[events_v1] skipped")
        else:
            if not args.skip_silver:
                silver_path = transform_to_silver(target_date, silver_config)
                print(f"[silver] wrote {silver_path}")
            else:
                print("[silver] skipped")

            if not args.skip_gold:
                gold_path = build_daily_features(target_date, gold_config)
                print(f"[gold] wrote {gold_path}")
            else:
                print("[gold] skipped")


if __name__ == "__main__":
    main()
