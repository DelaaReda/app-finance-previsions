"""Silver layer transformation for the news lakehouse pipeline.

Consumes bronze Parquet partitions, cleans the article content, enriches it
with lightweight NLP signals (tickers, topics, sentiment) and publishes the
result as a new partition under ``data/news/silver``.
"""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd

from ingestion.news_schemas import SilverRecord, asdict_recursive
from taxonomy.news_taxonomy import classify_event, tag_geopolitics, tag_sectors

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - fall back to simple stripping
    BeautifulSoup = None  # type: ignore

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    _VADER = SentimentIntensityAnalyzer()
except Exception:  # pragma: no cover
    _VADER = None  # type: ignore

try:
    from langdetect import detect as lang_detect
except Exception:  # pragma: no cover
    def lang_detect(text: str) -> str:
        if text and any(ord(c) > 127 for c in text):
            return "fr"
        return "en"

from core.stock_utils import guess_ticker

LOGGER = logging.getLogger("news.silver")
BRONZE_DIR = Path("data/news/bronze")
SILVER_DIR = Path("data/news/silver")
UPPER_TOKEN = re.compile(r"\\b[A-Z]{2,6}\\b")
TICKER_STOPWORDS = {"THE", "AND", "FOR", "WITH", "THIS", "FROM", "HAVE", "UNITED"}


@dataclass(slots=True)
class SilverConfig:
    bronze_dir: Path = BRONZE_DIR
    silver_dir: Path = SILVER_DIR
    min_chars: int = 240  # drop ultra-short items
    sentiment_positive: float = 0.15
    sentiment_negative: float = -0.15


def _load_bronze_frames(date_partition: Path) -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    for file in sorted(date_partition.glob("*.parquet")):
        if file.name.startswith("news_bronze") or file.name.endswith(".parquet"):
            try:
                frames.append(pd.read_parquet(file))
            except Exception as exc:
                LOGGER.warning("Failed to load bronze file %s: %s", file, exc)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _clean_text(raw_html: Optional[str], fallback_summary: Optional[str]) -> str:
    if raw_html and BeautifulSoup:
        soup = BeautifulSoup(raw_html, "html.parser")
        for script in soup(["script", "style", "noscript"]):
            script.decompose()
        text = " ".join(part.strip() for part in soup.get_text().splitlines() if part.strip())
        if text:
            return text
    return (fallback_summary or "").strip()


def _sentiment_score(text: str) -> float:
    if not text:
        return 0.0
    if _VADER:
        return float(_VADER.polarity_scores(text)["compound"])
    # Fallback: naive polarity from keyword counts
    positive_words = ("beat", "growth", "surge", "record", "improve", "gain", "bullish", "positive")
    negative_words = ("loss", "drop", "decline", "warns", "lawsuit", "fraud", "bearish", "negative")
    text_lower = text.lower()
    pos_hits = sum(text_lower.count(word) for word in positive_words)
    neg_hits = sum(text_lower.count(word) for word in negative_words)
    total = pos_hits + neg_hits
    if total == 0:
        return 0.0
    return (pos_hits - neg_hits) / total


def _quality_score(text: str) -> float:
    length = len(text)
    if length <= 0:
        return 0.0
    if length < 200:
        return 0.3
    if length > 1200:
        return 1.0
    return 0.3 + (length - 200) / 1000 * 0.7


def _extract_tickers(text: str, title: Optional[str]) -> List[str]:
    tokens = set()
    for chunk in (text or "").split():
        chunk = chunk.strip("()[],.;:!?'\"").upper()
        if UPPER_TOKEN.match(chunk) and chunk not in TICKER_STOPWORDS:
            tokens.add(chunk)
    if title:
        for chunk in title.split():
            chunk = chunk.strip("()[],.;:!?'\"").upper()
            if UPPER_TOKEN.match(chunk) and chunk not in TICKER_STOPWORDS:
                tokens.add(chunk)
    tickers: List[str] = []
    for token in sorted(tokens):
        if len(token) <= 1:
            continue
        tickers.append(token)
    # Attempt to enrich with heuristics on company names
    if title:
        guessed = guess_ticker(title)
        if guessed:
            tickers.append(guessed.upper())
    return sorted(set(tickers))


def _dedupe(records: Iterable[SilverRecord]) -> List[SilverRecord]:
    seen: set[str] = set()
    unique: List[SilverRecord] = []
    for record in records:
        if record.hash_text and record.hash_text in seen:
            continue
        if record.hash_text:
            seen.add(record.hash_text)
        unique.append(record)
    return unique


def transform_to_silver(target_date: date, config: SilverConfig | None = None) -> Path:
    config = config or SilverConfig()
    bronze_partition = config.bronze_dir / f"dt={target_date.isoformat()}"
    if not bronze_partition.exists():
        raise FileNotFoundError(f"No bronze partition found at {bronze_partition}")

    df = _load_bronze_frames(bronze_partition)
    if df.empty:
        config.silver_dir.mkdir(parents=True, exist_ok=True)
        empty_path = config.silver_dir / f"dt={target_date.isoformat()}" / "news_silver_empty.parquet"
        empty_path.parent.mkdir(parents=True, exist_ok=True)
        empty_df = pd.DataFrame(columns=list(SilverRecord.__dataclass_fields__.keys()))
        _write_parquet(empty_df, empty_path)
        LOGGER.info("Silver pipeline wrote empty partition for %s", target_date)
        return empty_path

    records: List[SilverRecord] = []
    for row in df.to_dict("records"):
        text = _clean_text(row.get("raw_html"), row.get("summary"))
        if len(text) < config.min_chars:
            continue
        hash_text = hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]
        lang = row.get("lang_detected") or lang_detect(text[:240])
        sentiment = _sentiment_score(text)
        quality = _quality_score(text)
        sectors = tag_sectors(text)
        events = classify_event(text)
        geopolitics = tag_geopolitics(text)
        tickers = _extract_tickers(text, row.get("title"))

        record = SilverRecord(
            id=row.get("id"),
            canonical_url=row.get("canonical_url"),
            source_domain=row.get("source_domain"),
            source_name=row.get("source_name"),
            region=row.get("region"),
            lang=lang,
            published_at=_ensure_datetime(row.get("published_at")),
            crawled_at=_ensure_datetime(row.get("crawled_at")),
            title=row.get("title"),
            summary=row.get("summary"),
            text=text,
            hash_text=hash_text,
            tickers=tickers,
            sectors=sectors,
            events=events,
            geopolitics=geopolitics,
            sentiment=sentiment,
            quality=quality,
        )
        records.append(record)

    deduped = _dedupe(records)

    output_partition = config.silver_dir / f"dt={target_date.isoformat()}"
    output_partition.mkdir(parents=True, exist_ok=True)
    output_path = output_partition / f"news_silver_{datetime.now(timezone.utc).strftime('%H%M%S')}.parquet"

    if deduped:
        df_out = pd.DataFrame(asdict_recursive(record) for record in deduped)
    else:
        df_out = pd.DataFrame(columns=list(SilverRecord.__dataclass_fields__.keys()))

    _write_parquet(df_out, output_path)
    LOGGER.info(
        "Silver pipeline wrote %s/%s enriched articles to %s",
        len(deduped),
        len(records),
        output_path,
    )
    return output_path


def _ensure_datetime(value: Optional[object]) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


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


__all__ = ["SilverConfig", "transform_to_silver"]
