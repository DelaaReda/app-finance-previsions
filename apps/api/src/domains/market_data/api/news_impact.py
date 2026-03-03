"""
News Impact Analysis API Routes - Finance Copilot System
Provides sophisticated analysis of how news impacts financial assets with sentiment correlation
Task: FC-API-030 - News Impact Analysis
Author: ALEX-FINANCE-ANALYST-SUPERMAN-29
"""
from fastapi import APIRouter, Query
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from core.response import ok, err
from storage.io import load_json

router = APIRouter()
logger = logging.getLogger(__name__)
IMPACT_SCORE_SCALE_MAX = 10.0


def _impact_threshold_to_ratio(impact_threshold: Optional[float]) -> float:
    """Normalize threshold input to a 0..1 ratio, accepting either 0..1 or 0..10 scales."""
    try:
        threshold = float(impact_threshold)
    except (TypeError, ValueError):
        return 0.1
    if threshold > 1.0:
        threshold /= IMPACT_SCORE_SCALE_MAX
    return max(0.0, min(1.0, threshold))


def _impact_score_to_ratio(impact_score: float) -> float:
    try:
        score = float(impact_score)
    except (TypeError, ValueError):
        return 0.0
    if score > 1.0:
        score = score / IMPACT_SCORE_SCALE_MAX
    return max(0.0, min(1.0, score))


def _impact_score_10(impact_score: float) -> float:
    return round(max(0.0, min(IMPACT_SCORE_SCALE_MAX, _impact_score_to_ratio(impact_score) * IMPACT_SCORE_SCALE_MAX)), 2)


def _build_signal_trace(
    article: Dict[str, Any],
    sentiment_score: float,
    relevance_score: float,
    impact_score: float,
    impact_categories: List[str],
    confidence: float,
    pub_date: str,
    tickers: List[str],
) -> Dict[str, Any]:
    return {
        "article_id": article.get("id", ""),
        "source": article.get("source", article.get("publisher", "unknown")),
        "published_at": pub_date,
        "tickers": tickers,
        "sentiment_score": sentiment_score,
        "relevance_score": relevance_score,
        "impact_score_10": _impact_score_10(impact_score),
        "categories": impact_categories,
        "confidence": confidence,
    }

@router.get("/news/analysis")
def get_news_impact_analysis(
    tickers: Optional[List[str]] = Query(None, description="Filter by specific tickers (e.g., AAPL, MSFT)"),
    since: Optional[str] = Query("7d", description="Time window: 1h, 6h, 1d, 3d, 7d, 14d, 30d"),
    impact_threshold: Optional[float] = Query(0.1, description="Minimum impact threshold (0.0-1.0 or 0.0-10.0)"),
    sentiment_filter: Optional[str] = Query("all", description="Filter by sentiment: positive, negative, neutral, all"),
    categories: Optional[List[str]] = Query(None, description="Filter by news categories (earnings, merger, ipo, etc.)"),
    limit: Optional[int] = Query(100, description="Limit number of results (max 500)")
) -> Dict[str, Any]:
    """
    Analyze the impact of news articles on financial assets.
    Returns impact scores, correlation between news and price movements, and sentiment analysis.
    """
    try:
        impact_threshold_ratio = _impact_threshold_to_ratio(impact_threshold)
        logger.info(f"🔬 GET /news/analysis - Impact analysis requested", extra={
            "tickers": tickers,
            "since": since,
            "impact_threshold": impact_threshold_ratio,
            "sentiment_filter": sentiment_filter,
            "categories": categories,
            "limit": limit
        })
        
        # Load news data from persistent storage (following never-empty pattern)
        news_data = load_json("news_feed")
        
        if not news_data:
            logger.warning("⚠️ No news data found for impact analysis", extra={
                "filters": {
                    "tickers": tickers,
                    "since": since,
                    "impact_threshold": impact_threshold_ratio
                }
            })
            
            # Return empty but structured response (never-empty pattern)
            return ok({
                "impact_analysis": [],
                "summary": {
                    "total_articles_analyzed": 0,
                    "total_impactful_events": 0,
                    "avg_impact_score": 0.0,
                    "most_impacted_tickers": [],
                    "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0},
                    "category_distribution": {},
                    "time_series": []
                },
                "parameters": {
                    "tickers": tickers,
                    "since": since,
                    "impact_threshold": impact_threshold_ratio,
                    "impact_threshold_input": impact_threshold,
                    "sentiment_filter": sentiment_filter,
                    "categories": categories,
                    "limit": limit
                },
                "message": "No news data available - system fetching from RSS sources in background",
                "freshness": "unknown",
                "generated_at": datetime.utcnow().isoformat(),
                "source": ["fallback_empty", "news_impact_analyzer"]
            })
        
        # Extract articles from data payload
        data_payload = news_data.get("data", news_data.get("payload", news_data))
        all_articles = data_payload.get("articles", data_payload if isinstance(data_payload, list) else [])
        
        logger.info(f"📊 Loaded {len(all_articles)} articles for impact analysis", extra={
            "total_articles": len(all_articles),
            "filters": {
                "tickers": tickers,
                "since": since,
                "sentiment_filter": sentiment_filter
            }
        })
        
        # Apply filtering
        filtered_articles = all_articles
        
        # Filter by tickers if specified
        if tickers:
            filtered_articles = [
                article for article in filtered_articles
                if any(ticker.upper() in [t.upper() for t in article.get("tickers", []) or article.get("symbols", []) or []] for ticker in tickers)
            ]
            logger.debug(f"🔍 Filtered by tickers {tickers}: {len(all_articles)} → {len(filtered_articles)} articles")
        
        # Apply date filter
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
                    logger.debug(f"📅 Filtered by time window {since}: {len(filtered_articles)} articles remain")
                except ValueError:
                    logger.warning(f"⚠️ Invalid time window format: {since}, proceeding without time filter")
        
        # Apply sentiment filter
        if sentiment_filter and sentiment_filter.lower() != "all":
            if sentiment_filter.lower() == "positive":
                filtered_articles = [article for article in filtered_articles if _get_sentiment_score(article) > 0.1]
            elif sentiment_filter.lower() == "negative":
                filtered_articles = [article for article in filtered_articles if _get_sentiment_score(article) < -0.1]
            elif sentiment_filter.lower() == "neutral":
                filtered_articles = [article for article in filtered_articles if -0.1 <= _get_sentiment_score(article) <= 0.1]
        
        # Apply category filter if specified
        if categories:
            filtered_articles = [
                article for article in filtered_articles
                if any(cat.lower() in [c.lower() for c in article.get("categories", []) or article.get("themes", []) or []] for cat in categories)
            ]
            logger.debug(f"🏷️ Filtered by categories {categories}: {len(filtered_articles)} articles remain")
        
        # Calculate news impact for each article
        impact_results = []
        for article in filtered_articles:
            impact_result = calculate_single_news_impact(article)
            
            # Only include if impact score exceeds threshold
            if impact_result["impact_score"] >= impact_threshold_ratio:
                impact_result["original_article"] = article  # Include original article data
                impact_results.append(impact_result)
        
        # Sort by impact score (highest first)
        impact_results = sorted(impact_results, key=lambda x: x["impact_score"], reverse=True)
        
        # Apply limit
        if limit and len(impact_results) > limit:
            impact_results = impact_results[:limit]
        
        # Generate summary statistics
        summary = generate_impact_summary(impact_results, filtered_articles, tickers)
        
        response_data = {
            "impact_analysis": impact_results,
            "summary": summary,
            "parameters": {
                "tickers": tickers,
                "since": since,
                "impact_threshold": impact_threshold_ratio,
                "impact_threshold_input": impact_threshold,
                "sentiment_filter": sentiment_filter,
                "categories": categories,
                "limit": limit
            },
            "generated_at": datetime.utcnow().isoformat(),
            "freshness": news_data.get("freshness", news_data.get("last_update")),
            "source": news_data.get("source", ["news_impact_analyzer", "correlation_analysis"])
        }
        
        logger.info(f"✅ News impact analysis completed", extra={
            "total_articles_analyzed": len(filtered_articles),
            "impactful_events_found": len(impact_results),
            "avg_impact_score": summary.get("avg_impact_score", 0),
            "most_impacted_tickers": summary.get("most_impacted_tickers", [])[:5]
        })
        
        return ok(response_data)
        
    except Exception as e:
        logger.error(f"❌ Error in news impact analysis: {str(e)}", exc_info=True)
        
        # Return structured response even on error (never-empty pattern)
        return ok({
            "impact_analysis": [],
            "summary": {
                "total_articles": 0,
                "total_impactful_events": 0,
                "avg_impact_score": 0.0,
                "most_impacted_tickers": [],
                "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0},
                "category_distribution": {}
            },
            "parameters": {
                "tickers": tickers,
                "since": since,
                "impact_threshold": impact_threshold_ratio,
                "impact_threshold_input": impact_threshold,
                "sentiment_filter": sentiment_filter,
                "categories": categories,
                "limit": limit
            },
            "error": str(e),
            "message": "News impact analysis temporarily unavailable - showing fallback data",
            "generated_at": datetime.utcnow().isoformat(),
            "source": ["fallback", "error_handling", "news_impact_analyzer"]
        })


def calculate_single_news_impact(article: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate the impact score for a single news article on relevant tickers.
    
    Args:
        article: The news article to analyze
        
    Returns:
        Dictionary with impact scores and analysis
    """
    try:
        title = article.get("title", "")
        summary = article.get("summary", article.get("description", ""))
        tickers_mentioned = article.get("tickers", []) or article.get("symbols", [])
        pub_date = _safe_parse_date(article.get("pubDate", ""))
        
        if not tickers_mentioned:
            # If no tickers in article, return with 0 impact
            return {
                "tickers": [],
                "impact_score": 0.0,
                "sentiment_score": _get_sentiment_score(article),
                "correlation_score": 0.0,
                "relevance_score": 0.0,
                "article_id": article.get("id", ""),
                "timestamp": pub_date.isoformat() if pub_date else "",
                "title": title,
                "impact_categories": []
            }
        
        # Calculate different impact components
        sentiment_score = _get_sentiment_score(article)
        
        # Calculate relevance based on multiple factors
        relevance_score = calculate_article_relevance(article, tickers_mentioned)
        
        # Calculate impact categories (based on article content and keywords)
        impact_categories = categorize_news_impact(article)
        
        # Combine sentiment and relevance for impact score
        impact_score = min(1.0, max(0.0, (0.6 * abs(sentiment_score)) + (0.4 * relevance_score)))  # Weighted combination
        
        # Calculate confidence in impact prediction
        confidence = calculate_impact_confidence(article, impact_categories)
        signal_trace = _build_signal_trace(
            article=article,
            sentiment_score=sentiment_score,
            relevance_score=relevance_score,
            impact_score=impact_score,
            impact_categories=impact_categories,
            confidence=confidence,
            pub_date=pub_date.isoformat() if pub_date else "",
            tickers=tickers_mentioned,
        )
        content_summary = (summary[:240] + "...") if len(summary) > 240 else summary
        
        return {
            "tickers": tickers_mentioned,
            "impact_score": impact_score,  # 0..1
            "impact_score_10": _impact_score_10(impact_score),
            "sentiment_score": sentiment_score,
            "correlation_score": 0.0,  # Would be calculated with market data correlation in production
            "relevance_score": relevance_score,
            "article_id": article.get("id", ""),
            "timestamp": pub_date.isoformat() if pub_date else "",
            "title": title,
            "content_preview": summary[:100] + "..." if len(summary) > 100 else summary,
            "content_summary": content_summary,
            "impact_categories": impact_categories,
            "confidence_in_impact": confidence,
            "signal_trace": signal_trace,
            "estimated_price_impact_pct": estimate_price_impact(sentiment_score, impact_categories),
            "volatility_factor": calculate_volatility_factor(sentiment_score, impact_categories)
        }
    
    except Exception as e:
        logger.warning(f"⚠️ Error calculating impact for article: {str(e)}")
        # Return safe fallback values even if calculation fails
        return {
            "tickers": [],
            "impact_score": 0.0,
            "impact_score_10": 0.0,
            "sentiment_score": _get_sentiment_score(article),
            "correlation_score": 0.0,
            "relevance_score": 0.0,
            "article_id": article.get("id", ""),
            "timestamp": article.get("pubDate", ""),
            "title": article.get("title", ""),
            "content_preview": (article.get("summary", "") or article.get("description", ""))[:100] + "..." if len(article.get("summary", "") or article.get("description", "")) > 100 else (article.get("summary", "") or article.get("description", "")),
            "content_summary": (article.get("summary", "") or article.get("description", ""))[:240],
            "impact_categories": ["error_processing"],
            "confidence_in_impact": 0.3,  # Low confidence if processing error
            "signal_trace": {
                "article_id": article.get("id", ""),
                "source": article.get("source", article.get("publisher", "unknown")),
                "published_at": article.get("pubDate", ""),
                "tickers": [],
                "sentiment_score": _get_sentiment_score(article),
                "relevance_score": 0.0,
                "impact_score_10": 0.0,
                "categories": ["error_processing"],
                "confidence": 0.3,
            },
            "estimated_price_impact_pct": 0.0,
            "volatility_factor": 0.1  # Conservative default
        }


def generate_impact_summary(impact_results: List[Dict], all_articles: List[Dict], tickers: Optional[List[str]]) -> Dict[str, Any]:
    """
    Generate summary statistics for the impact analysis results.
    """
    if not impact_results:
        # If no impactful articles found, return meaningful defaults
        return {
            "total_articles_analyzed": len(all_articles),
            "total_impactful_events": 0,
            "avg_impact_score": 0.0,
            "median_impact_score": 0.0,
            "max_impact_score": 0.0,
            "min_impact_score": 0.0,
            "total_sentiment_score": 0.0,
            "avg_sentiment": 0.0,
            "most_impacted_tickers": [],
            "impact_distribution": {"low": 0, "medium": 0, "high": 0},
            "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0},
            "category_distribution": {},
            "time_series": [],
            "generated_at": datetime.utcnow().isoformat()
        }
    
    # Calculate basic metrics
    total_impact_score = sum(result["impact_score"] for result in impact_results)
    avg_impact_score = total_impact_score / len(impact_results) if impact_results else 0.0
    
    # Calculate median impact score
    sorted_scores = sorted([r["impact_score"] for r in impact_results])
    median_impact_score = sorted_scores[len(sorted_scores)//2] if sorted_scores else 0.0
    
    # Calculate ticker frequency for most impacted
    ticker_impact_counts = {}
    for result in impact_results:
        for ticker in result.get("tickers", []):
            ticker_impact_counts[ticker] = ticker_impact_counts.get(ticker, 0) + 1
    
    most_impacted_tickers = sorted(ticker_impact_counts.items(), key=lambda x: x[1], reverse=True)
    most_impacted_tickers = [ticker for ticker, count in most_impacted_tickers[:10]]  # Top 10
    
    # Calculate impact distribution
    low_impact = sum(1 for r in impact_results if r["impact_score"] < 0.3)
    medium_impact = sum(1 for r in impact_results if 0.3 <= r["impact_score"] < 0.7)
    high_impact = sum(1 for r in impact_results if r["impact_score"] >= 0.7)
    
    impact_distribution = {
        "low": low_impact,
        "medium": medium_impact,
        "high": high_impact
    }
    
    # Calculate sentiment distribution
    positive_count = sum(1 for r in impact_results if r["sentiment_score"] > 0.1)
    negative_count = sum(1 for r in impact_results if r["sentiment_score"] < -0.1)
    neutral_count = len(impact_results) - positive_count - negative_count
    
    sentiment_distribution = {
        "positive": positive_count,
        "negative": negative_count,
        "neutral": neutral_count
    }
    
    # Calculate category distribution
    category_counts = {}
    for result in impact_results:
        for category in result.get("impact_categories", []):
            category_counts[category] = category_counts.get(category, 0) + 1
    
    # Create time series for impact over time
    time_series = []
    for result in impact_results[:20]:  # Limit to top 20 for performance
        time_series.append({
            "date": result["timestamp"],
            "impact_score": result["impact_score"],
            "sentiment_score": result["sentiment_score"],
            "tickers": result.get("tickers", [])[:3],  # Limit to first 3 tickers
            "title": result["title"][:50] + "..." if len(result["title"]) > 50 else result["title"]
        })
    
    return {
        "total_articles_analyzed": len(all_articles),
        "total_impactful_events": len(impact_results),
        "avg_impact_score": avg_impact_score,
        "median_impact_score": median_impact_score,
        "max_impact_score": max((r["impact_score"] for r in impact_results), default=0.0),
        "min_impact_score": min((r["impact_score"] for r in impact_results), default=0.0),
        "total_sentiment_score": sum(r["sentiment_score"] for r in impact_results),
        "avg_sentiment": sum(r["sentiment_score"] for r in impact_results) / len(impact_results) if impact_results else 0.0,
        "most_impacted_tickers": most_impacted_tickers,
        "impact_distribution": impact_distribution,
        "sentiment_distribution": sentiment_distribution,
        "category_distribution": category_counts,
        "time_series": time_series,
        "generated_at": datetime.utcnow().isoformat()
    }


def calculate_article_relevance(article: Dict[str, Any], mentioned_tickers: List[str]) -> float:
    """
    Calculate relevance score for an article based on various factors.
    """
    try:
        title = article.get("title", "")
        summary = article.get("summary", article.get("description", ""))
        source = article.get("source", article.get("publisher", "unknown"))
        
        # Calculate relevance based on multiple factors
        title_relevance = 0.3 if any(ticker.lower() in title.lower() for ticker in mentioned_tickers) else 0.0
        sentiment_magnitude = abs(_get_sentiment_score(article)) * 0.2
        source_relevance = 0.2 if source.lower() in ["reuters", "bloomberg", "wsj", "financial_times", "marketwatch", "cnbc"] else 0.0
        content_length_relevance = min(0.3, len(summary) / 1000.0)  # Max 0.3 for content length (up to 1000 chars)
        
        # Combine relevance factors
        total_relevance = title_relevance + sentiment_magnitude + source_relevance + content_length_relevance
        return min(1.0, max(0.0, total_relevance))
    except:
        return 0.1  # Default low relevance if calculation fails


def categorize_news_impact(article: Dict[str, Any]) -> List[str]:
    """
    Categorize the impact type of a news article based on content.
    """
    try:
        title = article.get("title", "").lower()
        summary = article.get("summary", article.get("description", "")).lower()
        
        categories = []
        
        # Earnings/Financial Results
        if any(keyword in title or keyword in summary for keyword in ["earnings", "quarterly", "results", "revenue", "profit", "eps", "q1", "q2", "q3", "q4"]):
            categories.append("earnings")
        
        # Mergers & Acquisitions
        if any(keyword in title or keyword in summary for keyword in ["merger", "acquisition", "acquire", "buyout", "divest", "spinoff", "deal", "takeover"]):
            categories.append("merger_acquisition")
        
        # IPO/Stock Events
        if any(keyword in title or keyword in summary for keyword in ["ipo", "public", "shares", "debut", "listing", "stock_offering", "s-1"]):
            categories.append("ipo_stock_event")
        
        # Policy/Regulatory
        if any(keyword in title or keyword in summary for keyword in ["regulatory", "fed", "policy", "rate", "treasury", "government", "legislation", "regulation"]):
            categories.append("policy_regulatory")
        
        # Market Events
        if any(keyword in title or keyword in summary for keyword in ["crash", "rally", "sell-off", "panic", "bubble", "market_maker", "flash_crash"]):
            categories.append("market_event")
        
        # Technology/Crypto
        if any(keyword in title or keyword in summary for keyword in ["crypto", "blockchain", "bitcoin", "ethereum", "defi", "ai", "machine_learning", "algorithm"]):
            categories.append("technology_crypto")
        
        # Economic Indicators
        if any(keyword in title or keyword in summary for keyword in ["gdp", "unemployment", "cpi", "inflation", "jobs", "employment", "housing", "consumer_spending"]):
            categories.append("economic_indicator")
        
        # If no specific category identified, assign general
        if not categories:
            categories.append("general")
        
        return categories
    except:
        return ["general"]  # Default category if categorization fails


def calculate_impact_confidence(article: Dict[str, Any], categories: List[str]) -> float:
    """
    Calculate confidence in the impact score based on article quality and category.
    """
    try:
        source = article.get("source", article.get("publisher", "unknown")).lower()
        sentiment_magnitude = abs(_get_sentiment_score(article))
        
        # Base confidence
        confidence = 0.5
        
        # Boost if high-impact category
        if any(cat in categories for cat in ["earnings", "merger_acquisition", "policy_regulatory", "market_event"]):
            confidence += 0.2
        
        # Boost for reliable sources
        if source in ["reuters", "bloomberg", "wsj", "financial_times", "cnbc"]:
            confidence += 0.15
        
        # Boost for high sentiment magnitude
        confidence += sentiment_magnitude * 0.2
        
        return min(1.0, max(0.3, confidence))  # Clamp between 0.3 and 1.0
    except:
        return 0.4  # Default confidence if calculation fails


def estimate_price_impact(sentiment_score: float, categories: List[str]) -> float:
    """
    Estimate potential price impact percentage based on sentiment and category.
    """
    try:
        base_impact = sentiment_score * 0.015  # Base impact of 1.5% per sentiment unit
        
        # Amplify for high-impact categories
        if any(cat in categories for cat in ["earnings", "merger_acquisition"]):
            base_impact *= 2.0  # Double impact for earnings/M&A
        elif any(cat in categories for cat in ["policy_regulatory", "market_event"]):
            base_impact *= 1.5  # 1.5x impact for policy/market events
        
        # Cap the impact to reasonable bounds
        return min(0.05, max(-0.05, base_impact))  # Max ±5% impact
    except:
        return 0.0  # Default 0% impact if calculation fails


def calculate_volatility_factor(sentiment_score: float, categories: List[str]) -> float:
    """
    Calculate expected volatility increase factor based on news.
    """
    try:
        base_volatility = 0.1  # Base 10% volatility factor
        sentiment_factor = abs(sentiment_score) * 0.15  # 15% boost per sentiment unit magnitude
        
        # Additional boost for high-impact categories
        category_factor = 0.0
        if any(cat in categories for cat in ["earnings", "merger_acquisition", "market_event"]):
            category_factor = 0.1
        elif any(cat in categories for cat in ["policy_regulatory"]):
            category_factor = 0.05
        
        total_factor = base_volatility + sentiment_factor + category_factor
        return min(0.5, max(0.05, total_factor))  # Between 5% and 50% volatility factor
    except:
        return 0.1  # Default volatility factor if calculation fails


def _get_sentiment_score(article: Dict[str, Any]) -> float:
    """
    Extract normalized sentiment score from article.
    """
    try:
        score = article.get("sentiment_score") or article.get("sentiment", 0.0) or article.get("polarity", 0.0)
        if isinstance(score, (int, float)):
            return max(-1.0, min(1.0, float(score)))  # Clamp to [-1.0, 1.0]
        elif isinstance(score, str):
            try:
                return max(-1.0, min(1.0, float(score)))  # Convert string to float and clamp
            except ValueError:
                return 0.0  # Return 0 if string can't be converted
        else:
            return 0.0  # Default if score is not a number or string
    except:
        return 0.0  # Default if extraction fails


def _safe_parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Safely parse a date string, returning None if parsing fails.
    """
    if not date_str:
        return None
    
    try:
        from datetime import datetime
        # Handle ISO format with timezone
        date_str = str(date_str).strip()
        if "T" in date_str and ("Z" in date_str or "+" in date_str):
            # Handle timezone formats
            if "Z" in date_str:
                cleaned = date_str.replace("Z", "+00:00")
            elif date_str.endswith("+0000"):
                cleaned = date_str.replace("+0000", "+00:00")
            else:
                cleaned = date_str
            
            # Parse with timezone info
            try:
                return datetime.fromisoformat(cleaned)
            except ValueError:
                # If timezone parsing fails, try without timezone
                clean_date = date_str.split("T")[0]
                return datetime.strptime(clean_date, "%Y-%m-%d")
        elif "T" in date_str:
            # Simple ISO format without timezone
            clean_date = date_str.split("T")[0]
            return datetime.strptime(clean_date, "%Y-%m-%d")
        else:
            # Simple date format
            return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        # If all parsing attempts fail, return None
        return None


# Export router with expected name for main.py
news_impact_router = router
