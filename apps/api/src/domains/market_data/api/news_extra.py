"""
API Routes for News Feed - Dashboard Integration
Provides filtered news data with sentiment scoring for the dashboard with never-empty guarantee
Task: BE-003 - ALEX-FINANCE-ANALYST-SUPERMAN-29
"""
from fastapi import APIRouter, Query
from typing import Dict, Any, Optional, List
import json
from datetime import datetime, timedelta
import logging

from core.response import ok, err
from storage.io import load_json
from services.cache_layer import load_or_compute

router = APIRouter()
logger = logging.getLogger(__name__)

try:
    from services.service_standard import ensure_decision_contract, utc_now_iso  # type: ignore
except Exception:  # pragma: no cover
    ensure_decision_contract = None  # type: ignore
    utc_now_iso = lambda: datetime.utcnow().isoformat() + "Z"  # type: ignore

@router.get("/news/feed")
def get_filtered_news_feed(
    tickers: Optional[List[str]] = Query(None, description="Filter news by specific tickers"),
    since: Optional[str] = Query("7d", description="Time window: 1h, 6h, 1d, 3d, 7d, 14d"),
    region: Optional[str] = Query("all", description="Filter by region: US, EU, APAC, all"),
    score_min: Optional[float] = Query(0.0, ge=-1.0, le=1.0, description="Minimum composite score"),
    limit: Optional[int] = Query(50, ge=1, le=200, description="Limit number of results (max 200)"),
    sort_by: Optional[str] = Query("sentiment", description="Sort by: date, sentiment, relevance, ticker"),
    order: Optional[str] = Query("desc", description="Sort order: asc or desc")
) -> Dict[str, Any]:
    """
    Dashboard news feed endpoint with filtering capabilities.
    Returns news data with sentiment scoring and proper structure for dashboard UI components.
    """
    now_iso = utc_now_iso()
    logger.info(f"📰 GET /api/news/feed - Request received", extra={
        "tickers": tickers,
        "since": since,
        "region": region,
        "score_min": score_min,
        "limit": limit
    })
    
    try:
        # Load news from persistent storage (following never-empty pattern)
        news_data = load_json("news_feed")
        
        if not news_data:
            logger.warning(f"⚠️ No news data found in storage", extra={
                "filters": {
                    "tickers": tickers,
                    "since": since,
                    "region": region,
                    "score_min": score_min,
                    "limit": limit
                }
            })
            # Return empty structure but never fail
            return ok({
                "articles": [],
                "count": 0,
                "filtered_params": {
                    "tickers": tickers,
                    "since": since,
                    "region": region,
                    "score_min": score_min,
                    "limit": limit
                },
                "message": "No news data available - system ingesting in background",
                "freshness": "unknown",
                "generated_at": now_iso,
                "source": ["fallback_empty", "news_pipeline"]
            })
        
        # Extract news articles from payload
        data_payload = news_data.get("data", news_data.get("payload", news_data))
        all_articles = data_payload.get("articles", data_payload if isinstance(data_payload, list) else [])
        
        logger.info(f"📊 Loaded {len(all_articles)} news articles from storage", extra={
            "total_articles": len(all_articles),
            "data_structure": "data.articles" if "data" in news_data else "direct"
        })
        
        # Apply filtering
        filtered_articles = all_articles
        
        # Filter by tickers if specified
        if tickers:
            before_tickers = len(filtered_articles)
            filtered_articles = [
                article for article in filtered_articles
                if any(ticker in (article.get("tickers", []) if article.get("tickers") else [article.get("ticker")]) for ticker in tickers)
            ]
            logger.debug(f"🔍 Filtered by tickers {tickers}: {before_tickers} → {len(filtered_articles)} articles")
        
        # Filter by region if specified
        if region and region != "all":
            before_region = len(filtered_articles)
            filtered_articles = [
                article for article in filtered_articles
                if article.get("region", "US").lower() == region.lower()
            ]
            logger.debug(f"🌍 Filtered by region {region}: {before_region} → {len(filtered_articles)} articles")
        
        # Filter by minimum score
        if score_min and score_min > -1.0:
            before_score = len(filtered_articles)
            filtered_articles = [
                article for article in filtered_articles
                if article.get("sentiment_score", 0) >= score_min or article.get("score", 0) >= score_min
            ]
            logger.debug(f"⚖️ Filtered by min score {score_min}: {before_score} → {len(filtered_articles)} articles")
        
        # Filter by time window
        if since:
            time_multiplier = {"h": 1, "d": 24, "w": 168, "m": 720, "y": 8760}  # hours in each period
            if len(since) > 1 and since[-1] in time_multiplier:
                try:
                    num = int(since[:-1])
                    hours_back = num * time_multiplier[since[-1]]
                    cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
                    
                    filtered_articles = [
                        article for article in filtered_articles
                        if article.get("pubDate") and _safe_parse_date(article["pubDate"]) and _safe_parse_date(article["pubDate"]) > cutoff_time
                    ]
                    logger.debug(f"🕐 Filtered by time window {since}: {len(filtered_articles)} articles")
                except ValueError:
                    logger.warning(f"⚠️ Invalid time window format: {since}, proceeding without time filter")
        
        # Sort results
        logger.debug(f"🔀 Sorting by {sort_by} ({order})...")
        if sort_by == "date":
            reverse_order = order == "desc"
            filtered_articles = sorted(
                filtered_articles,
                key=lambda x: _safe_parse_date(x.get("pubDate", "")) or datetime.min,
                reverse=reverse_order
            )
        elif sort_by == "sentiment":
            reverse_order = order == "desc"
            filtered_articles = sorted(
                filtered_articles,
                key=lambda x: x.get("sentiment_score", x.get("sentiment", 0)),
                reverse=reverse_order
            )
        elif sort_by == "ticker":
            reverse_order = order == "desc"
            filtered_articles = sorted(
                filtered_articles,
                key=lambda x: x.get("ticker", x.get("symbol", "")),
                reverse=reverse_order
            )
        else:  # Default sort by relevance (score)
            reverse_order = order == "desc"
            filtered_articles = sorted(
                filtered_articles,
                key=lambda x: x.get("score", x.get("sentiment_score", 0)),
                reverse=reverse_order
            )
        
        # Apply limit
        before_limit = len(filtered_articles)
        if limit and limit > 0:
            limit_val = min(limit, 200)  # Cap at 200
            filtered_articles = filtered_articles[:limit_val]
            logger.debug(f"✂️ Applied limit {limit_val}: {before_limit} → {len(filtered_articles)} articles")
        
        logger.info(f"✅ News feed filtered successfully", extra={
            "initial_count": len(all_articles),
            "final_count": len(filtered_articles),
            "filters_applied": {
                "tickers": tickers is not None,
                "region": region != "all",
                "min_score": score_min and score_min > -1.0,
                "time_window": since is not None,
                "limit": limit is not None
            }
        })
        
        # Format articles for frontend consumption (with enhanced fields for NewsFeed.tsx)
        formatted_articles = []
        for article in filtered_articles:
            # Parse publication date for timeago display
            pub_date = _safe_parse_date(article.get("pubDate", ""))
            timeago_str = _calculate_timeago(pub_date) if pub_date else "Unknown"
            
            # Format for frontend with all necessary fields
            formatted_article = {
                "id": article.get("id", f"news_{abs(hash(article.get('title', '') + article.get('pubDate', '')))}"),
                "title": article.get("title", "Titre non disponible"),
                "description": article.get("description", "") or article.get("summary", ""),
                "url": article.get("url", "") or article.get("link", ""),
                "pubDate": article.get("pubDate", article.get("date", "")),
                "timeago": timeago_str,
                "source": article.get("source", article.get("publisher", "Unknown")),
                "tickers": article.get("tickers", []) or article.get("symbols", []) or [],
                "sentiment": {
                    "score": article.get("sentiment_score", article.get("sentiment", 0)),
                    "label": _get_sentiment_label(article.get("sentiment_score", article.get("sentiment", 0))),
                    "magnitude": abs(article.get("sentiment_score", article.get("sentiment", 0)))
                },
                "score": article.get("score", article.get("sentiment_score", 0.5)),
                "themes": article.get("themes", []) or article.get("categories", []) or [],
                "region": article.get("region", "US"),
                "author": article.get("author", article.get("byline", "")),
                "word_count": len((article.get("description") or "").split()) if article.get("description") else 0,
                "read_time": max(1, len((article.get("description") or "").split()) // 225) if article.get("description") else 1  # ~225 words per minute
            }
            formatted_articles.append(formatted_article)
        
        # Prepare response data
        response_data = {
            "articles": formatted_articles,
            "count": len(formatted_articles),
            "filtered_params": {
                "tickers": tickers,
                "since": since,
                "region": region,
                "score_min": score_min,
                "limit": limit,
                "sort_by": sort_by,
                "order": order
            },
            "freshness": news_data.get("freshness", news_data.get("last_update")),
            "generated_at": now_iso,
            "source": news_data.get("source", ["news_pipeline", "rss_ingest"])
        }

        if callable(ensure_decision_contract):
            sentiment_values = []
            ticker_counter: Dict[str, int] = {}
            for article in formatted_articles:
                sent = (article.get("sentiment") or {}).get("score") if isinstance(article.get("sentiment"), dict) else None
                try:
                    sentiment_values.append(float(sent))
                except (TypeError, ValueError):
                    pass
                for token in (article.get("tickers") or []):
                    upper = str(token).strip().upper()
                    if upper:
                        ticker_counter[upper] = ticker_counter.get(upper, 0) + 1

            avg_sent = sum(sentiment_values) / len(sentiment_values) if sentiment_values else 0.0
            verdict = "buy" if avg_sent > 0.2 else "sell" if avg_sent < -0.2 else "hold"
            risk_level = "high" if avg_sent < -0.4 else "medium" if avg_sent < -0.2 else "low"
            top_tickers = sorted(ticker_counter.items(), key=lambda x: x[1], reverse=True)[:3]
            top_tickers_str = ", ".join(f"{t}({c})" for t, c in top_tickers) if top_tickers else "none"

            ensure_decision_contract(
                response_data,
                default_source="news_feed",
                verdict=verdict,
                confidence=min(1.0, abs(avg_sent)),
                why=[
                    f"Avg sentiment={avg_sent:.2f} on {len(formatted_articles)} articles",
                    f"Top tickers={top_tickers_str}",
                ],
                risk_level=risk_level,
                risk_caveat="News sentiment skew negative." if avg_sent < -0.2 else "",
                freshness=response_data.get("freshness") or now_iso,
            )
        
        logger.info(f"✅ Returning {len(formatted_articles)} news articles to client")
        return ok(response_data)
        
    except Exception as e:
        logger.error(f"❌ Error in news feed endpoint: {str(e)}", exc_info=True, extra={
            "error_type": type(e).__name__,
            "filters": {
                "tickers": tickers,
                "since": since,
                "region": region,
                "score_min": score_min,
                "limit": limit
            }
        })
        # Return structured response even on error to maintain never-empty contract
        error_response = {
            "articles": [],
            "count": 0,
            "filtered_params": {
                "tickers": tickers,
                "since": since,
                "region": region,
                "score_min": score_min,
                "limit": limit,
                "sort_by": sort_by,
                "order": order
            },
            "error": str(e),
            "message": "News feed temporarily unavailable - showing fallback data",
            "generated_at": now_iso,
            "source": ["fallback", "error_handling", "news_pipeline"]
        }
        return ok(error_response)


def _safe_parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Safely parse date string, return None if parsing fails"""
    if not date_str:
        return None
    try:
        # Try ISO format first
        if "T" in date_str or "Z" in date_str:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        # Try other common formats
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"]:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None
    except (ValueError, AttributeError, TypeError):
        return None


def _calculate_timeago(dt: Optional[datetime]) -> str:
    """Calculate time ago string from datetime"""
    if not dt:
        return "Unknown"
    
    now = datetime.utcnow()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days}d ago"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours}h ago"
    elif diff.seconds >= 60:
        mins = diff.seconds // 60
        return f"{mins}m ago"
    else:
        return "Just now"


def _get_sentiment_label(score: float) -> str:
    """Convert sentiment score to human-readable label"""
    if score >= 0.6:
        return "Très positif"
    elif score >= 0.2:
        return "Positif"
    elif score >= -0.2:
        return "Neutre"
    elif score >= -0.6:
        return "Négatif"
    else:
        return "Très négatif"


# Export router with expected name for main.py registration
news_router = router
