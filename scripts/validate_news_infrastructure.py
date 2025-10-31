#!/usr/bin/env python3
"""Validation suite for the news lakehouse pipeline."""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd

from ingestion.bronze_pipeline import BronzeIngestionConfig, ingest_bronze_for_date
from ingestion.gold_features_pipeline import GoldConfig, build_daily_features
from ingestion.silver_pipeline import SilverConfig, transform_to_silver


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate news pipeline")
    parser.add_argument("--date", type=str, help="Date partition to validate (YYYY-MM-DD). Default: latest available")
    parser.add_argument("--ingest", action="store_true", help="Run ingestion for the chosen date before validating")
    parser.add_argument("--regions", nargs="+", help="Subset of regions for ingestion")
    return parser.parse_args()


def latest_partition(base: Path) -> date | None:
    if not base.exists():
        return None
    candidates: List[date] = []
    for child in base.iterdir():
        if child.is_dir() and child.name.startswith("dt="):
            try:
                candidates.append(date.fromisoformat(child.name.split("=", 1)[1]))
            except ValueError:
                continue
    return max(candidates) if candidates else None


def validate_bronze(target: date) -> None:
    path = Path("data/news/bronze") / f"dt={target.isoformat()}"
    if not path.exists():
        raise AssertionError(f"Bronze partition missing: {path}")
    files = list(path.glob("*.parquet"))
    if not files:
        raise AssertionError(f"No Parquet files in bronze partition {path}")
    df = pd.read_parquet(files[-1])
    required = {"id", "canonical_url", "source_domain", "published_at"}
    missing = required.difference(df.columns)
    if missing:
        raise AssertionError(f"Bronze partition missing columns: {missing}")


def validate_silver(target: date) -> None:
    path = Path("data/news/silver") / f"dt={target.isoformat()}"
    if not path.exists():
        raise AssertionError(f"Silver partition missing: {path}")
    files = list(path.glob("*.parquet"))
    if not files:
        raise AssertionError(f"No Parquet files in silver partition {path}")
    df = pd.read_parquet(files[-1])
    required = {"tickers", "sentiment", "quality", "hash_text"}
    missing = required.difference(df.columns)
    if missing:
        raise AssertionError(f"Silver partition missing columns: {missing}")
    if df["hash_text"].duplicated().any():
        raise AssertionError("Silver partition contains duplicate hash_text values")


def validate_gold(target: date) -> None:
    path = Path("data/news/gold/features_daily") / f"dt={target.isoformat()}" / "features.parquet"
    if not path.exists():
        raise AssertionError(f"Gold features missing: {path}")
    df = pd.read_parquet(path)
    required = {"ticker", "article_count", "avg_sentiment"}
    missing = required.difference(df.columns)
    if missing:
        raise AssertionError(f"Gold features missing columns: {missing}")


def main() -> int:
    args = parse_args()
    base_bronze = Path("data/news/bronze")
    partition_date: date | None
    if args.date:
        partition_date = date.fromisoformat(args.date)
    else:
        partition_date = latest_partition(base_bronze)
    if partition_date is None:
        partition_date = date.today()

    if args.ingest:
        ingest_bronze_for_date(partition_date, BronzeIngestionConfig(regions=args.regions))
        transform_to_silver(partition_date, SilverConfig())
        build_daily_features(partition_date, GoldConfig())

    validate_bronze(partition_date)
    validate_silver(partition_date)
    validate_gold(partition_date)
    print(f"✅ News pipeline validated for {partition_date}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
