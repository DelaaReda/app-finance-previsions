"""Silver v2 transformation skeleton.

Reads bronze partitions, applies enrichment hooks, and writes silver v2 schema.
The heavy lifting (readability, NER, sentiment, etc.) can be plugged into the
`TODO` sections without changing the orchestrator contract.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable, Iterator, List

import pandas as pd

BRONZE_DIR = Path("data/news/bronze")
SILVER_DIR = Path("data/news/silver_v2")


def _iter_bronze_partitions(pattern: str) -> Iterator[Path]:
    """Yield bronze parquet files matching dt glob."""
    for path in sorted(BRONZE_DIR.glob(f"dt={pattern}/**/*.parquet")):
        yield path


def _load_partition(path: Path) -> pd.DataFrame:
    try:
        return pd.read_parquet(path)
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️  Failed to read {path}: {exc}")
        return pd.DataFrame()


def _hash_text(text: str, published_at: str, source_domain: str) -> str:
    base = f"{text}|{published_at}|{source_domain}".lower().strip()
    return hashlib.sha1(base.encode()).hexdigest()


def _default_list(length: int) -> List[list]:
    return [[] for _ in range(length)]


def _apply_enrichment(df: pd.DataFrame) -> pd.DataFrame:
    """Placeholder enrichment logic – plug your modules here."""
    if df.empty:
        return df
    df = df.copy()
    df["source_tier"] = df.get("source_tier", "Tier2")
    df["text"] = df.get("text")
    if "text" not in df or df["text"].isna().all():
        df["text"] = df.get("summary", "")
    df["tickers"] = df.get("tickers") if "tickers" in df else _default_list(len(df))
    df["topics"] = df.get("topics") if "topics" in df else _default_list(len(df))
    df["entities"] = df.get("entities") if "entities" in df else _default_list(len(df))
    df["sentiment"] = df.apply(lambda _: {"polarity": 0.0, "subjectivity": 0.0}, axis=1)
    df["quality"] = df.apply(
        lambda _: {"credibility": 0.5, "completeness": 0.5, "noise": 0.5},
        axis=1,
    )
    df["relevance"] = 0.0
    df["impact_proxy"] = 0.0
    df["market_window_ref"] = df.apply(
        lambda _: {
            "t0": pd.NaT,
            "t1d": pd.NaT,
            "t5d": pd.NaT,
            "t20d": pd.NaT,
        },
        axis=1,
    )
    df["hash_text"] = df.apply(
        lambda row: _hash_text(str(row.get("text", "")), str(row.get("published_at")), str(row.get("source_domain"))),
        axis=1,
    )
    df["dedup_key"] = df["hash_text"]
    df["simhash"] = None
    df["parent_id"] = None
    return df


def _persist(df: pd.DataFrame, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    output = target_dir / "silver.parquet"
    df.to_parquet(output, index=False)
    with (target_dir / "metadata.json").open("w", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "row_count": len(df),
                    "columns": sorted(df.columns.tolist()),
                },
                indent=2,
            )
        )
    print(f"✅ wrote {output}")


def to_silver_v2(dt_glob: str = "*") -> None:
    partitions = list(_iter_bronze_partitions(dt_glob))
    if not partitions:
        print("ℹ️  no bronze partitions matched pattern")
        return

    frames: List[pd.DataFrame] = []
    for path in partitions:
        df = _load_partition(path)
        if not df.empty:
            frames.append(df)
    if not frames:
        print("⚠️  bronze partitions had no rows")
        return

    bronze = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["id"])
    silver = _apply_enrichment(bronze)

    for dt_value, group in silver.groupby(pd.to_datetime(silver["published_at"]).dt.strftime("%Y-%m-%d")):
        target = SILVER_DIR / f"dt={dt_value}"
        _persist(group, target)


if __name__ == "__main__":
    to_silver_v2()
