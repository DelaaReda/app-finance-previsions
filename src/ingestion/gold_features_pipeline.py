"""Gold layer generation for the news lakehouse pipeline.

Aggregates enriched silver articles into ticker-level daily features that can
be queried by analytics notebooks or the API service.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Dict, List

import pandas as pd

from ingestion.news_schemas import GoldDailyFeatures, asdict_recursive

SILVER_DIR = Path("data/news/silver")
GOLD_DIR = Path("data/news/gold/features_daily")


@dataclass(slots=True)
class GoldConfig:
    silver_dir: Path = SILVER_DIR
    gold_dir: Path = GOLD_DIR
    positive_threshold: float = 0.15
    negative_threshold: float = -0.15
    min_articles: int = 1


def build_daily_features(target_date: date, config: GoldConfig | None = None) -> Path:
    config = config or GoldConfig()
    partition = config.silver_dir / f"dt={target_date.isoformat()}"
    if not partition.exists():
        raise FileNotFoundError(f"No silver partition found at {partition}")

    frames: List[pd.DataFrame] = []
    for file in sorted(partition.glob("*.parquet")):
        try:
            frames.append(pd.read_parquet(file))
        except Exception as exc:
            continue
    if not frames:
        return _write_empty(config, target_date)

    df = pd.concat(frames, ignore_index=True)
    if df.empty:
        return _write_empty(config, target_date)

    aggregates: Dict[str, Dict[str, object]] = defaultdict(lambda: {
        "article_count": 0,
        "positive_count": 0,
        "negative_count": 0,
        "neutral_count": 0,
        "sentiment_sum": 0.0,
        "quality_sum": 0.0,
        "sectors": set(),
        "events": set(),
        "geopolitics": set(),
    })

    for row in df.to_dict("records"):
        tickers = _ensure_list(row.get("tickers"))
        if not tickers:
            continue
        sentiment = float(row.get("sentiment") or 0.0)
        quality = float(row.get("quality") or 0.0)
        sectors = _ensure_list(row.get("sectors"))
        events = _ensure_list(row.get("events"))
        geopolitics = _ensure_list(row.get("geopolitics"))

        for ticker in tickers:
            agg = aggregates[ticker]
            agg["article_count"] += 1
            agg["sentiment_sum"] += sentiment
            agg["quality_sum"] += quality
            if sentiment >= config.positive_threshold:
                agg["positive_count"] += 1
            elif sentiment <= config.negative_threshold:
                agg["negative_count"] += 1
            else:
                agg["neutral_count"] += 1
            agg["sectors"].update(sectors)
            agg["events"].update(events)
            agg["geopolitics"].update(geopolitics)

    features: List[GoldDailyFeatures] = []
    for ticker, agg in aggregates.items():
        if agg["article_count"] < config.min_articles:
            continue
        article_count = agg["article_count"]
        avg_sentiment = agg["sentiment_sum"] / article_count if article_count else None
        quality_avg = agg["quality_sum"] / article_count if article_count else None
        features.append(
            GoldDailyFeatures(
                date=target_date,
                ticker=ticker,
                article_count=article_count,
                positive_count=agg["positive_count"],
                negative_count=agg["negative_count"],
                neutral_count=agg["neutral_count"],
                avg_sentiment=avg_sentiment,
                quality_avg=quality_avg,
                sectors=sorted(set(agg["sectors"])),
                events=sorted(set(agg["events"])),
                geopolitics=sorted(set(agg["geopolitics"])),
            )
        )

    output_partition = config.gold_dir / f"dt={target_date.isoformat()}"
    output_partition.mkdir(parents=True, exist_ok=True)
    output_path = output_partition / "features.parquet"
    df_out = pd.DataFrame(asdict_recursive(feature) for feature in features)
    _write_parquet(df_out, output_path)
    return output_path


def _ensure_list(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v]
    if isinstance(value, str):
        if value.startswith("[") and value.endswith("]"):
            try:
                import json

                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(v) for v in parsed if v]
            except Exception:
                pass
        return [value]
    return [str(value)]


def _write_empty(config: GoldConfig, target_date: date) -> Path:
    config.gold_dir.mkdir(parents=True, exist_ok=True)
    empty_path = config.gold_dir / f"dt={target_date.isoformat()}" / "features.parquet"
    empty_path.parent.mkdir(parents=True, exist_ok=True)
    empty_df = pd.DataFrame(columns=list(GoldDailyFeatures.__dataclass_fields__.keys()))
    _write_parquet(empty_df, empty_path)
    return empty_path


def _write_parquet(df: "pd.DataFrame", path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        df.to_parquet(path, index=False)
    except Exception:
        import duckdb

        con = duckdb.connect()
        try:
            con.register("news_df", df)
            con.execute(f"COPY news_df TO '{path}' (FORMAT 'parquet')")
        finally:
            con.unregister("news_df")
            con.close()


__all__ = ["GoldConfig", "build_daily_features"]
