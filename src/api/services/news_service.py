# src/api/services/news_service.py
"""News service backed by the lakehouse parquet outputs (v2)."""
from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from api.schemas import (
    NewsArticle,
    NewsFeedData,
    NewsFeedFilters,
    NewsScore,
    SentimentData,
    TraceMetadata,
)
from core.duck import query_parquet

SILVER_PARQUET = "data/news/silver_v2/dt=*/silver.parquet"
FEATURES_PARQUET = "data/news/gold/features_daily_v2/dt=*/features.parquet"

REGION_MAP: Dict[str, List[str]] = {
    "US": ["US"],
    "CA": ["CA"],
    "EU": ["FR", "DE"],
    "INTL": ["INTL", "GEO"],
    "all": [],
}

SOURCE_TIER_SCORE: Dict[str, float] = {
    "Tier1": 1.0,
    "Tier2": 0.7,
    "Tier3": 0.5,
}


def _hash_data(data: Any) -> str:
    content = str(data).encode("utf-8")
    return hashlib.sha256(content).hexdigest()[:32]


def _create_trace(source: str, asof: date, payload: Any) -> TraceMetadata:
    return TraceMetadata(
        created_at=datetime.utcnow(),
        source=source,
        asof_date=asof,
        hash=_hash_data(payload),
    )


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _since_to_timedelta(since: str) -> timedelta:
    mapping = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "1d": timedelta(days=1),
        "3d": timedelta(days=3),
        "7d": timedelta(days=7),
        "14d": timedelta(days=14),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
    }
    return mapping.get(since, timedelta(days=7))


def _ensure_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value
    if isinstance(value, str):
        try:
            dt_value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if dt_value.tzinfo is not None:
            dt_value = dt_value.astimezone(timezone.utc).replace(tzinfo=None)
        return dt_value
    return None


def _compute_score(row: Dict[str, Any], now: datetime, published: datetime) -> NewsScore:
    hours = max((now - published).total_seconds() / 3600.0, 0.0)
    freshness = _clamp(1.0 / (1.0 + hours / 6.0))
    tier = (row.get("source_tier") or "Tier3")
    source_quality = _clamp(SOURCE_TIER_SCORE.get(tier, 0.5))
    relevance_input = row.get("impact_proxy")
    if relevance_input is None:
        relevance_input = row.get("relevance", 0.4)
    relevance = _clamp(relevance_input)
    total = _clamp(0.5 * freshness + 0.3 * source_quality + 0.2 * relevance)
    return NewsScore(
        total=total,
        freshness=freshness,
        source_quality=source_quality,
        relevance=relevance,
    )


def _summarise(row: Dict[str, Any]) -> str:
    summary = row.get("summary") or ""
    if summary:
        return summary
    text = row.get("text") or ""
    return text[:280]


def get_news_feed(
    tickers: Optional[List[str]] = None,
    since: str = "7d",
    score_min: float = 0.0,
    region: str = "all",
    limit: int = 50,
) -> NewsFeedData:
    now = datetime.utcnow()
    start_time = now - _since_to_timedelta(since)
    limit_fetch = max(limit * 5, limit * 2)

    sql = f"""
        SELECT id, title, summary, text, source_domain, source_name, region,
               published_at, tickers, impact_proxy, relevance, source_tier
        FROM read_parquet('{SILVER_PARQUET}')
        WHERE published_at >= ?
        ORDER BY published_at DESC
        LIMIT ?
    """
    try:
        rows = query_parquet(sql, [start_time, limit_fetch])
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️  news feed query failed: {exc}")
        rows = []

    ticker_targets = {t.upper() for t in (tickers or [])}
    region_targets = set(REGION_MAP.get(region, []))
    count_total = 0
    articles: List[NewsArticle] = []

    for row in rows:
        published = _ensure_datetime(row.get("published_at"))
        if published is None:
            continue
        row_region = row.get("region")
        if region_targets and row_region not in region_targets:
            continue
        row_tickers = [str(t).upper() for t in (row.get("tickers") or [])]
        if ticker_targets and not (set(row_tickers) & ticker_targets):
            continue

        score = _compute_score(row, now, published)
        if score.total < score_min:
            continue

        count_total += 1
        if len(articles) >= limit:
            continue

        source_label = row.get("source_name") or row.get("source_domain") or "Unknown"
        article = NewsArticle(
            id=str(row.get("id")),
            title=row.get("title") or "",
            summary=_summarise(row),
            url=row.get("canonical_url") or row.get("url") or "",
            source=source_label,
            published_at=published,
            tickers=row_tickers,
            score=score,
            trace=_create_trace("news_lakehouse_v2", published.date(), row.get("id")),
        )
        articles.append(article)

    filters = NewsFeedFilters(
        tickers=[t.upper() for t in (tickers or [])] or None,
        since=since,
        score_min=score_min,
        region=region,
    )

    feed_trace = _create_trace(
        "news_lakehouse_v2",
        date.today(),
        {"count": len(articles), "total": count_total, "since": since},
    )

    return NewsFeedData(
        articles=articles,
        count=len(articles),
        total=count_total,
        filters=filters,
        trace=feed_trace,
    )


def get_sentiment(limit: int = 100) -> SentimentData:
    start_date = (datetime.utcnow() - timedelta(days=30)).date()
    sql = f"""
        SELECT ticker, avg(sent_mean) AS avg_sentiment
        FROM read_parquet('{FEATURES_PARQUET}')
        WHERE date >= ?
        GROUP BY ticker
        ORDER BY abs(avg_sentiment) DESC
        LIMIT ?
    """
    try:
        rows = query_parquet(sql, [start_date, limit])
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️  sentiment query failed: {exc}")
        rows = []

    sentiment = {
        row["ticker"]: float(row.get("avg_sentiment") or 0.0)
        for row in rows
        if row.get("ticker")
    }

    trace = _create_trace(
        "news_features_v2",
        date.today(),
        {"tickers": list(sentiment.keys())},
    )

    return SentimentData(
        sentiment=sentiment,
        count=len(sentiment),
        trace=trace,
    )
