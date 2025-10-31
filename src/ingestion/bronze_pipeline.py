"""Bronze layer ingestion for the news lakehouse pipeline."""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import pandas as pd

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore

try:
    from langdetect import detect as lang_detect
except Exception:  # pragma: no cover
    def lang_detect(text: str) -> str:
        if text and any(ord(c) > 127 for c in text):
            return "fr"
        return "en"

from ingestion.news_schemas import BronzeRecord, asdict_recursive

LOGGER = logging.getLogger("news.bronze")
DEFAULT_BASE_DIR = Path("data/news/bronze")


def _canonicalize_url(url: str) -> str:
    if not url:
        return url
    parts = urlparse(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith("utm_")]
    cleaned = parts._replace(
        scheme=parts.scheme.lower() or "https",
        netloc=parts.netloc.lower(),
        query=urlencode(query, doseq=True),
    )
    return urlunparse(cleaned)


def _hash_identity(url: str, title: Optional[str], published: datetime) -> str:
    payload = "|".join(
        [
            _canonicalize_url(url or ""),
            (title or "").strip().lower(),
            published.replace(tzinfo=timezone.utc).isoformat(),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _fetch_html(url: str, timeout: int = 10) -> Optional[str]:
    if not url or requests is None:
        return None
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "FinanceCopilotBot/0.1"})
        if 200 <= resp.status_code < 400:
            return resp.text
    except Exception:
        return None
    return None


@dataclass(slots=True)
class BronzeIngestionConfig:
    base_dir: Path = DEFAULT_BASE_DIR
    regions: Optional[List[str]] = None
    per_source_limit: int = 50
    pull_window_hours: int = 24
    fetch_html: bool = True

    def resolve_sources(self) -> Dict[str, List[str]]:
        from ingestion.finnews import SOURCES

        if not self.regions:
            return SOURCES
        selected: Dict[str, List[str]] = {}
        for region in self.regions:
            feeds = SOURCES.get(region.upper())
            if feeds:
                selected[region.upper()] = feeds
        return selected


def _iter_entries(feed_url: str, window: timedelta, limit: int):
    try:
        import feedparser  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("feedparser is required for news ingestion. pip install feedparser") from exc

    parsed = feedparser.parse(feed_url)
    if not parsed.entries:
        return []
    cutoff = datetime.now(timezone.utc) - window
    yielded = 0
    for entry in parsed.entries:
        published_parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
        if published_parsed:
            published = datetime(*published_parsed[:6], tzinfo=timezone.utc)
        else:
            published = datetime.now(timezone.utc)
        if published < cutoff:
            continue
        yield entry, published
        yielded += 1
        if limit and yielded >= limit:
            break


def ingest_bronze_for_date(target_date: date, config: BronzeIngestionConfig | None = None) -> Path:
    config = config or BronzeIngestionConfig()
    config.base_dir.mkdir(parents=True, exist_ok=True)
    day_dir = config.base_dir / f"dt={target_date.isoformat()}"
    day_dir.mkdir(parents=True, exist_ok=True)

    records: List[BronzeRecord] = []
    window = timedelta(hours=config.pull_window_hours)

    for region, feeds in config.resolve_sources().items():
        for feed_url in feeds:
            for entry, published in _iter_entries(feed_url, window, config.per_source_limit):
                title = getattr(entry, "title", None)
                summary = getattr(entry, "summary", None) or getattr(entry, "description", None)
                link = getattr(entry, "link", None) or getattr(entry, "id", None)
                canonical = _canonicalize_url(link or "")
                if not canonical:
                    continue
                record_id = _hash_identity(canonical, title, published)
                raw_html = _fetch_html(canonical) if config.fetch_html else None

                source_name = None
                source = getattr(entry, "source", None)
                if isinstance(source, dict):
                    source_name = source.get("title")

                records.append(
                    BronzeRecord(
                        id=record_id,
                        url=link or canonical,
                        canonical_url=canonical,
                        source_domain=urlparse(canonical).netloc,
                        source_name=source_name,
                        region=region,
                        lang_detected=lang_detect((title or "") + " " + (summary or "")) if (title or summary) else None,
                        published_at=published,
                        crawled_at=datetime.now(timezone.utc),
                        title=title,
                        summary=summary,
                        raw_html=raw_html,
                        license_hint="rss",
                        paywall=None,
                        status_code=None,
                    )
                )

    output_path = day_dir / f"news_bronze_{datetime.now(timezone.utc).strftime('%H%M%S')}.parquet"
    if not records:
        df = pd.DataFrame(columns=list(BronzeRecord.__dataclass_fields__.keys()))
        _write_parquet(df, output_path)
        LOGGER.info("Bronze ingestion produced no records for %s", target_date)
        return output_path

    df = pd.DataFrame(asdict_recursive(record) for record in records)
    _write_parquet(df, output_path)
    LOGGER.info("Bronze ingestion wrote %s records to %s", len(df), output_path)
    return output_path


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


__all__ = ["BronzeIngestionConfig", "ingest_bronze_for_date"]
