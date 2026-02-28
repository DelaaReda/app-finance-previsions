"""
News Sentiment job.
Builds per-ticker sentiment aggregates from the latest ingested news feed.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

try:
    from core.sentry_runtime import install_global_excepthook, init_sentry, set_job_context, capture_exception
except Exception:  # pragma: no cover
    def install_global_excepthook(job_name: str) -> bool:
        return False

    def init_sentry(component: str) -> bool:
        return False

    def set_job_context(job_name: str, **context: Any) -> None:
        return None

    def capture_exception(exc: BaseException, *, job_name: str | None = None, context: Dict[str, Any] | None = None) -> None:
        return None

try:
    from storage.io import load_json, save_json
except Exception:  # pragma: no cover
    load_json = None
    save_json = None

from core.ticker_normalization import normalize_ticker


SENTIMENT_TO_SCORE = {
    "positive": 1.0,
    "neutral": 0.0,
    "negative": -1.0,
}


def _extract_articles() -> List[Dict[str, Any]]:
    if load_json is None:
        return []
    payload = load_json("news_feed") or load_json("news_feed.json") or {}
    if not isinstance(payload, dict):
        return []
    articles = payload.get("articles")
    if isinstance(articles, list):
        return [a for a in articles if isinstance(a, dict)]
    nested = payload.get("data", {})
    if isinstance(nested, dict) and isinstance(nested.get("articles"), list):
        return [a for a in nested["articles"] if isinstance(a, dict)]
    return []


def run_news_sentiment_analysis(filters: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Aggregate sentiment by ticker from the latest ingested news file.
    """
    logger.info("Starting news sentiment aggregation job...")
    init_sentry("news_sentiment")

    requested_tickers = []
    if filters and isinstance(filters.get("tickers"), list):
        requested_tickers = [
            t
            for t in (normalize_ticker(str(raw)) for raw in filters.get("tickers", []))
            if t
        ]
    requested_ticker_set = set(requested_tickers)
    set_job_context("news_sentiment", requested_ticker_count=len(requested_tickers))

    try:
        articles = _extract_articles()
        if not articles:
            logger.warning("No articles found in news_feed. Writing empty sentiment snapshot.")
            result = {
                "status": "completed",
                "sentiment_records": 0,
                "tickers_analyzed": [],
                "sentiment_data": [],
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": ["job:news_sentiment", "news_feed_empty"],
            }
            if save_json is not None:
                save_json("news_sentiment", result, source=["job:news_sentiment", "news_feed_empty"])
            return result

        # Build ticker aggregates from article-level labels/scores.
        agg: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "ticker": "",
                "article_count": 0,
                "positive_articles": 0,
                "negative_articles": 0,
                "neutral_articles": 0,
                "sentiment_sum": 0.0,
            }
        )

        for article in articles:
            tickers = article.get("tickers") or []
            if requested_ticker_set:
                tickers = [t for t in tickers if normalize_ticker(str(t)) in requested_ticker_set]
            if not tickers:
                continue
            sentiment_label = str(article.get("sentiment", "neutral")).lower()
            score = article.get("score")
            if isinstance(score, (int, float)):
                # Map legacy 0-100 score to [-1, 1].
                sentiment_value = max(-1.0, min(1.0, (float(score) - 50.0) / 50.0))
            else:
                sentiment_value = SENTIMENT_TO_SCORE.get(sentiment_label, 0.0)

            for raw_ticker in tickers:
                ticker = normalize_ticker(str(raw_ticker))
                if not ticker:
                    continue
                item = agg[ticker]
                item["ticker"] = ticker
                item["article_count"] += 1
                item["sentiment_sum"] += float(sentiment_value)
                if sentiment_value > 0.15:
                    item["positive_articles"] += 1
                elif sentiment_value < -0.15:
                    item["negative_articles"] += 1
                else:
                    item["neutral_articles"] += 1

        sentiment_data: List[Dict[str, Any]] = []
        for ticker, item in sorted(agg.items(), key=lambda kv: kv[0]):
            article_count = int(item["article_count"])
            if article_count <= 0:
                continue
            sentiment_score = float(item["sentiment_sum"]) / article_count
            sentiment_data.append(
                {
                    "ticker": ticker,
                    "sentiment_score": round(sentiment_score, 4),
                    "article_count": article_count,
                    "positive_articles": int(item["positive_articles"]),
                    "negative_articles": int(item["negative_articles"]),
                    "neutral_articles": int(item["neutral_articles"]),
                    "news_impact_score": round(min(1.0, abs(sentiment_score) * (1.0 + article_count / 20.0)), 4),
                    "volatility_adjustment": round(min(0.15, abs(sentiment_score) * 0.08), 4),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "source": ["news_feed", "ticker_sentiment_aggregate"],
                }
            )

        result = {
            "status": "completed",
            "sentiment_records": len(sentiment_data),
            "tickers_analyzed": [row["ticker"] for row in sentiment_data],
            "sentiment_data": sentiment_data,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": ["job:news_sentiment", "news_feed"],
        }

        if save_json is not None:
            save_json("news_sentiment", result, source=["job:news_sentiment", "news_feed"])

        logger.info("News sentiment job completed: %d tickers", len(sentiment_data))
        return result
    except Exception as exc:
        logger.error("News sentiment job failed: %s", exc, exc_info=True)
        capture_exception(exc, job_name="news_sentiment", context={"stage": "aggregate"})
        return {
            "status": "failed",
            "sentiment_records": 0,
            "tickers_analyzed": [],
            "sentiment_data": [],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(exc),
        }


if __name__ == "__main__":
    install_global_excepthook("news_sentiment")
    result = run_news_sentiment_analysis()
    print(result)
