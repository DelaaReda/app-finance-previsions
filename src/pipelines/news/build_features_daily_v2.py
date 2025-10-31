"""Daily news features v2 skeleton.

Aggregates silver v2 articles into ticker-level metrics with placeholders for
novelty, source impact factors, and topic sensitivity.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterator, List

import pandas as pd

SILVER_DIR = Path("data/news/silver_v2")
GOLD_DIR = Path("data/news/gold/features_daily_v2")


def _iter_silver_partitions(pattern: str) -> Iterator[Path]:
    for path in sorted(SILVER_DIR.glob(f"dt={pattern}/silver.parquet")):
        yield path


def _load(path: Path) -> pd.DataFrame:
    try:
        return pd.read_parquet(path)
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️  could not read {path}: {exc}")
        return pd.DataFrame()


def _explode_tickers(df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict] = []
    for _, row in df.iterrows():
        raw_tickers = row.get("tickers")
        if raw_tickers is None:
            iterable: List[str] = []
        elif isinstance(raw_tickers, (list, tuple)):
            iterable = [str(t) for t in raw_tickers]
        else:
            try:
                iterable = [str(t) for t in list(raw_tickers)]
            except TypeError:
                iterable = [str(raw_tickers)]
        for ticker in iterable:
            rows.append({**row, "ticker": ticker})
    return pd.DataFrame(rows)


def _novelty_ratio(group: pd.DataFrame) -> float:
    if group.empty:
        return 0.0
    dup = group["parent_id"].notna().sum() if "parent_id" in group else 0
    return float(1.0 - dup / max(len(group), 1))


def _sentiment_stats(group: pd.DataFrame) -> Dict[str, float]:
    if "sentiment" not in group:
        return {"mean": 0.0, "pos_share": 0.0, "neg_share": 0.0}
    values = group["sentiment"].apply(lambda s: (s or {}).get("polarity", 0.0))
    hits_pos = (values > 0).sum()
    hits_neg = (values < 0).sum()
    total = max(len(values), 1)
    return {
        "mean": float(values.mean()),
        "pos_share": float(hits_pos / total),
        "neg_share": float(hits_neg / total),
    }


def _tier1_share(group: pd.DataFrame) -> float:
    if "source_tier" not in group or group.empty:
        return 0.0
    return float((group["source_tier"] == "Tier1").sum() / len(group))


def _collect_topics(group: pd.DataFrame) -> List[str]:
    if "topics" not in group or group.empty:
        return []
    counter: Dict[str, int] = defaultdict(int)
    for topics in group["topics"]:
        if not isinstance(topics, (list, tuple)):
            continue
        for topic in topics:
            counter[str(topic)] += 1
    return sorted(counter, key=counter.get, reverse=True)[:5]


def _impact_proxy(group: pd.DataFrame) -> float:
    if "impact_proxy" not in group or group.empty:
        return 0.0
    series = group["impact_proxy"].dropna()
    return float(series.mean()) if not series.empty else 0.0


def build_features_daily_v2(dt_glob: str = "*") -> None:
    partitions = list(_iter_silver_partitions(dt_glob))
    if not partitions:
        print("ℹ️  no silver partitions found")
        return

    frames = [df for path in partitions if not (df := _load(path)).empty]
    if not frames:
        print("⚠️  silver datasets empty")
        return

    silver = pd.concat(frames, ignore_index=True)
    silver["published_at"] = pd.to_datetime(silver["published_at"], utc=True)
    silver["date"] = silver["published_at"].dt.date

    exploded = _explode_tickers(silver)
    if exploded.empty:
        print("⚠️  no tickers found to aggregate")
        return

    results: Dict[str, Dict[str, Dict[str, object]]] = defaultdict(lambda: defaultdict(dict))
    for (date_val, ticker), group in exploded.groupby(["date", "ticker"]):
        stats = _sentiment_stats(group)
        results[str(date_val)][ticker] = {
            "date": pd.to_datetime(date_val),
            "ticker": ticker,
            "news_count": int(len(group)),
            "novelty": _novelty_ratio(group),
            "sent_mean": stats["mean"],
            "sent_pos_share": stats["pos_share"],
            "sent_neg_share": stats["neg_share"],
            "tier1_share": _tier1_share(group),
            "top_topics": _collect_topics(group),
            "intraday_intensity": None,
            "impact_proxy_mean": _impact_proxy(group),
            "source_impact_factor": None,
            "features_version": 2,
        }

    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    for date_str, ticker_map in results.items():
        frame = pd.DataFrame(ticker_map.values())
        target_dir = GOLD_DIR / f"dt={date_str}"
        target_dir.mkdir(parents=True, exist_ok=True)
        out = target_dir / "features.parquet"
        frame.to_parquet(out, index=False)
        print(f"✅ wrote {out}")


if __name__ == "__main__":
    build_features_daily_v2()
