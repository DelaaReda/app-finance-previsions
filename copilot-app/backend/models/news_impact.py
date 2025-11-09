"""
News Impact Analysis Model
Task: FC-API-030 - News Impact Analysis
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import sys
from pathlib import Path
import math
import re


class NewsImpactModel:
    """
    Model for analyzing news impact on asset prices
    """
    
    def __init__(self):
        self.cached_impacts = {}
    
    def _calculate_sentiment_score(self, title: str, content: str = "", source: str = "") -> float:
        """
        Calculate sentiment score from news content
        
        Args:
            title: News title
            content: News content/body
            source: News source
        
        Returns:
            Sentiment score between -1 (negative) and 1 (positive)
        """
        # Basic sentiment analysis using keyword weighting
        # In a real implementation, this would use a trained sentiment model
        text = (title + " " + content).lower()
        
        positive_keywords = [
            'rise', 'gain', 'profit', 'increase', 'up', 'boost', 'positive', 'growth', 
            'outperform', 'upgrade', 'buy', 'strong', 'excellent', 'beat', 'surprise',
            'bullish', 'rally', 'success', 'expansion', 'approval', 'deal',
            'partnership', 'contract', 'acquisition', 'merger', 'dividend', 'return',
            'rebound', 'recovery', 'momentum', 'breakthrough', 'innovation', 'leadership',
            'record', 'high', 'outlook', 'prospect', 'opportunity', 'advantage'
        ]
        
        negative_keywords = [
            'fall', 'loss', 'drop', 'down', 'decline', 'decrease', 'weak', 'negative',
            'miss', 'downgrade', 'sell', 'bearish', 'crash', 'crisis', 'loss', 'failure',
            'scandal', 'lawsuit', 'regulatory', 'ban', 'shutdown', 'bankruptcy', 'fraud',
            'recession', 'volatile', 'risk', 'concern', 'warn', 'cut', 'layoffs',
            'downturn', 'slump', 'struggle', 'pressure', 'challenges', 'uncertainty',
            'volatile', 'disappoint', 'underperform', 'concern', 'problem', 'threat'
        ]
        
        # Count positive and negative words
        pos_count = sum(1 for word in positive_keywords if word in text)
        neg_count = sum(1 for word in negative_keywords if word in text)
        
        # Calculate sentiment score
        total_count = pos_count + neg_count
        if total_count > 0:
            sentiment = (pos_count - neg_count) / total_count
        else:
            # Default to neutral if no sentiment words found
            sentiment = 0.0
        
        # Adjust based on source reliability (hypothetical adjustment)
        if 'bloomberg' in source.lower() or 'reuters' in source.lower() or 'wsj' in source.lower():
            # Major sources might have higher impact
            sentiment = sentiment * 1.1
        elif 'social_media' in source.lower() or 'reddit' in source.lower() or 'twitter' in source.lower():
            # Social media might have different reliability
            sentiment = sentiment * 0.8
        
        # Clamp between -1 and 1
        return max(-1.0, min(1.0, sentiment))
    
    def analyze_news_impact(self, 
                           articles: List[Dict[str, Any]], 
                           price_history: Dict[str, List[Dict[str, Any]]],
                           ticker_mentions: Optional[Dict[str, List[str]]] = None) -> Dict[str, Any]:
        """
        Analyze the impact of news articles on specific assets
        
        Args:
            articles: List of news articles with timestamps
            price_history: Price history for relevant tickers
            ticker_mentions: Mapping of article IDs to relevant tickers
        
        Returns:
            Analysis results with impact scores
        """
        impact_analysis = {
            "articles_analyzed": len(articles),
            "impacts": {},
            "summary_by_ticker": {},
            "total_mentions": 0,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source": ["news_impact_model", "impact_analysis", "fc-api-030"]
        }
        
        if not articles:
            impact_analysis["message"] = "No articles provided for impact analysis"
            return impact_analysis
        
        # Create ticker mentions mapping if not provided
        if ticker_mentions is None:
            ticker_mentions = {}
            # Extract tickers from titles/contents (simplified approach)
            for i, article in enumerate(articles):
                article_id = article.get("id", f"article_{i}_{hash(article.get('title', ''))}")
                # Find potential ticker symbols in the article
                text_content = article.get("title", "") + " " + article.get("description", "") + " " + article.get("content", "")
                tickers = self._extract_tickers(text_content)
                ticker_mentions[article_id] = list(set(tickers))  # Remove duplicates
        
        # Track overall impacts by ticker
        summary_by_ticker = defaultdict(lambda: {
            "total_articles": 0,
            "total_impact": 0.0,
            "avg_impact": 0.0,
            "positive_articles": 0,
            "negative_articles": 0,
            "neutral_articles": 0,
            "total_sentiment": 0.0,
            "avg_sentiment": 0.0,
            "impacts": []
        })
        
        # Analyze each article
        for i, article in enumerate(articles):
            article_id = article.get("id", f"article_{i}_{hash(str(article.get('title', '')))}")
            ticker_list = ticker_mentions.get(article_id, [])
            
            if not ticker_list:
                continue  # Skip articles that don't mention specific tickers
            
            # Calculate sentiment
            content = article.get("content", article.get("description", ""))
            source = article.get("source", article.get("publisher", ""))
            sentiment_score = self._calculate_sentiment_score(
                article.get("title", ""),
                content,
                source
            )
            
            # Analyze impact for each mentioned ticker
            for ticker in ticker_list:
                ticker_upper = ticker.upper()
                
                # Get price data around the article publication time
                article_time = article.get("pubDate", article.get("publishedAt", article.get("timestamp")))
                if not article_time:
                    # Use current time if no publication time available (fallback)
                    article_time = datetime.utcnow().isoformat() + "Z"
                
                # Get prices before and after the news
                price_before, price_after = self._get_prices_around_news(
                    ticker_upper, 
                    article_time, 
                    price_history
                )
                
                # Calculate impact strength and type
                impact_strength, impact_type = self._calculate_price_impact(
                    sentiment_score, 
                    price_before, 
                    price_after
                )
                
                # Create impact record
                impact_record = {
                    "article_id": article_id,
                    "ticker": ticker_upper,
                    "sentiment_score": round(sentiment_score, 4),
                    "impact_strength": round(impact_strength, 4),
                    "impact_type": impact_type,
                    "price_before": price_before,
                    "price_after": price_after,
                    "price_change_pct": round(((price_after - price_before) / price_before) * 100, 4) if price_before != 0 else 0.0,
                    "article_title": article.get("title", "")[:100] + "..." if len(article.get("title", "")) > 100 else article.get("title", ""),
                    "publication_date": article_time,
                    "relevance_score": abs(sentiment_score) * abs(impact_strength),
                    "confidence": min(abs(sentiment_score * 0.7) + (1 - abs(sentiment_score) * 0.3), 1.0)  # Confidence based on sentiment strength
                }
                
                # Add to impacts
                if article_id not in impact_analysis["impacts"]:
                    impact_analysis["impacts"][article_id] = {}
                impact_analysis["impacts"][article_id][ticker_upper] = impact_record
                
                # Update ticker summary
                ticker_summary = summary_by_ticker[ticker_upper]
                ticker_summary["total_articles"] += 1
                ticker_summary["total_impact"] += impact_strength
                ticker_summary["total_sentiment"] += sentiment_score
                ticker_summary["avg_impact"] = ticker_summary["total_impact"] / ticker_summary["total_articles"]
                ticker_summary["avg_sentiment"] = ticker_summary["total_sentiment"] / ticker_summary["total_articles"]
                ticker_summary["impacts"].append(impact_record)
                
                if impact_strength > 0.1:
                    ticker_summary["positive_articles"] += 1
                elif impact_strength < -0.1:
                    ticker_summary["negative_articles"] += 1
                else:
                    ticker_summary["neutral_articles"] += 1
        
        # Add ticker summaries to result
        impact_analysis["summary_by_ticker"] = dict(summary_by_ticker)
        impact_analysis["total_mentions"] = sum(summary["total_articles"] for summary in summary_by_ticker.values())
        
        # Add overall summary statistics
        impact_analysis["stats"] = {
            "total_articles_processed": len(articles),
            "total_tickers_affected": len(summary_by_ticker),
            "total_impact_events": sum(summary["total_articles"] for summary in summary_by_ticker.values()),
            "avg_sentiment_across_all": sum(summary["total_sentiment"] for summary in summary_by_ticker.values()) / len(summary_by_ticker) if summary_by_ticker else 0.0,
            "avg_impact_across_all": sum(summary["total_impact"] for summary in summary_by_ticker.values()) / len(summary_by_ticker) if summary_by_ticker else 0.0
        }
        
        return impact_analysis
    
    def _get_prices_around_news(self, ticker: str, news_time: str, 
                               price_history: Dict[str, List[Dict[str, Any]]]) -> Tuple[float, float]:
        """
        Get prices before and after news publication
        
        Args:
            ticker: Ticker symbol to get prices for
            news_time: Time news was published
            price_history: Price history data
        
        Returns:
            Tuple of (price_before, price_after)
        """
        if ticker not in price_history:
            return 100.0, 100.0  # Return default if no price history available
        
        try:
            # Parse news time
            from datetime import datetime
            # Remove timezone info and parse
            news_str = news_time.replace('Z', '').replace('T', ' ')
            if '.' in news_str:
                news_str = news_str.split('.')[0]
            news_dt = datetime.fromisoformat(news_str)
            
            # Get price history for this ticker
            prices = price_history[ticker]
            
            # Find prices before and after news
            prices_before = []
            prices_after = []
            
            for price_point in prices:
                if isinstance(price_point, dict):
                    date_str = price_point.get("date") or price_point.get("timestamp") or price_point.get("time")
                    if date_str:
                        try:
                            # Handle different date formats
                            if 'T' in str(date_str):
                                date_str_clean = str(date_str).replace('Z', '').split('.')[0]
                                price_dt = datetime.fromisoformat(date_str_clean)
                            elif '-' in str(date_str) and ':' in str(date_str):
                                date_str_clean = str(date_str).split('.')[0]
                                price_dt = datetime.fromisoformat(date_str_clean)
                            else:
                                continue  # Skip if we can't parse the date
                            
                            if price_dt < news_dt:
                                price_value = price_point.get("close") or price_point.get("adjusted_close") or price_point.get("price") or price_point.get("value", 0.0)
                                if price_value and price_value != 0:
                                    prices_before.append((price_dt, float(price_value)))
                            elif price_dt >= news_dt:
                                price_value = price_point.get("close") or price_point.get("adjusted_close") or price_point.get("price") or price_point.get("value", 0.0)
                                if price_value and price_value != 0:
                                    prices_after.append((price_dt, float(price_value)))
                        except ValueError:
                            continue  # Skip if date parsing fails
            
            # Get closest prices before and after news
            price_before = 100.0  # Default fallback price
            if prices_before:
                # Sort by date descending and take the latest before news
                prices_before.sort(key=lambda x: x[0], reverse=True)
                if prices_before:
                    price_before = prices_before[0][1]
            
            price_after = price_before  # Default to same price if no after data
            if prices_after:
                # Sort by date ascending and take the earliest after news
                prices_after.sort(key=lambda x: x[0])
                if prices_after:
                    price_after = prices_after[0][1]
            
            return price_before, price_after
            
        except Exception as e:
            print(f"Error getting prices around news for {ticker}: {str(e)}")
            return 100.0, 100.0  # Return default prices
    
    def _calculate_price_impact(self, sentiment: float, price_before: float, price_after: float) -> Tuple[float, str]:
        """
        Calculate the actual price impact of the news based on sentiment and price movement
        
        Args:
            sentiment: Sentiment score from -1 to 1
            price_before: Price before news
            price_after: Price after news
        
        Returns:
            Tuple of (impact_strength, impact_type)
        """
        if price_before == 0:
            return 0.0, "no_price_data"
        
        # Calculate price change percentage
        price_change_pct = (price_after - price_before) / price_before
        price_change_abs = abs(price_change_pct)
        
        # Calculate how aligned sentiment and movement are
        if sentiment > 0.1 and price_change_pct > 0.01:  # Positive sentiment AND positive move
            impact_strength = min(abs(sentiment) * price_change_abs * 2, 1.0)
            impact_type = "positive_aligned"  # Bullish news, bullish reaction
        elif sentiment < -0.1 and price_change_pct < -0.01:  # Negative sentiment AND negative move
            impact_strength = min(abs(sentiment) * price_change_abs * 2, 1.0)
            impact_type = "negative_aligned"  # Bearish news, bearish reaction
        elif sentiment > 0.1 and price_change_pct < -0.01:  # Positive sentiment BUT negative move
            impact_strength = min(abs(sentiment) * price_change_abs * 2, 1.0)
            impact_type = "contrarian_negative"  # Bullish news, bearish reaction
        elif sentiment < -0.1 and price_change_pct > 0.01:  # Negative sentiment BUT positive move
            impact_strength = min(abs(sentiment) * price_change_abs * 2, 1.0)
            impact_type = "contrarian_positive"  # Bearish news, bullish reaction
        else:
            # Weak sentiment or small price movement
            impact_strength = min(abs(sentiment) * price_change_abs, 0.5)
            impact_type = "minimal" if abs(impact_strength) < 0.05 else "low_alignment"
        
        # Scale impact by magnitude of change to reward significant moves
        magnitude_factor = 1 + (price_change_abs * 2)  # Amplify for larger moves
        impact_strength = impact_strength * magnitude_factor
        
        # Clamp to reasonable bounds
        impact_strength = max(-1.0, min(1.0, impact_strength))
        
        return impact_strength, impact_type
    
    def _extract_tickers(self, text: str) -> List[str]:
        """
        Extract potential ticker symbols from text
        This is a simplified version, in reality would use more sophisticated NLP
        """
        # Look for uppercase letter sequences (potential tickers)
        potential_tickers = re.findall(r'\b[A-Z]{2,5}\b', text)
        
        # Filter out common words that might be capitalized
        common_words = {
            'THE', 'AND', 'FOR', 'NOT', 'HAS', 'HAD', 'GET', 'CAN', 'NOW', 'NEW', 
            'END', 'SET', 'RUN', 'LET', 'ALL', 'ANY', 'EACH', 'EVERY', 'MORE',
            'MOST', 'OTHER', 'SOME', 'SUCH', 'NO', 'ONLY', 'OWN', 'SAME', 'SO',
            'THAN', 'TOO', 'VERY', 'JUST', 'COME', 'GIVE', 'LIVE', 'MOVE', 'PUT',
            'SEE', 'SEEM', 'TRY', 'TURN', 'USE', 'WORK', 'ACT', 'BAD', 'BUSY',
            'COLD', 'COOL', 'DUE', 'EARLY', 'EASY', 'FREE', 'GOOD', 'HOT', 'HUGE',
            'IDEA', 'MAD', 'MAIN', 'NEW', 'NICE', 'OKAY', 'OPEN', 'REAL', 'SAFE',
            'SLOW', 'SURE', 'TINY', 'TRUE', 'WARM', 'WAY', 'WILD', 'YOUNG', 'TOP',
            'LOT', 'DAY', 'HOUR', 'MIN', 'AGO', 'AGO'
        }
        
        # Filter out common words and return unique tickers
        tickers = [ticker for ticker in potential_tickers if ticker not in common_words and len(ticker) >= 2]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tickers = []
        for ticker in tickers:
            upper_ticker = ticker.upper()
            if upper_ticker not in seen:
                seen.add(upper_ticker)
                unique_tickers.append(upper_ticker)
        
        return unique_tickers
    
    def calculate_correlation_news_price(self, 
                                       articles: List[Dict[str, Any]], 
                                       price_history: Dict[str, List[Dict[str, Any]]],
                                       ticker: str) -> Dict[str, float]:
        """
        Calculate correlation between news sentiment and price movements for a specific ticker
        """
        try:
            # Perform full impact analysis first to get paired data
            ticker_mentions = {}
            for i, article in enumerate(articles):
                article_id = article.get("id", f"article_{i}_{hash(str(article.get('title', '')))}")
                # Check if this article mentions the specific ticker
                text_content = article.get("title", "") + " " + article.get("description", "") + " " + article.get("content", "")
                if ticker in text_content.upper():
                    ticker_mentions[article_id] = [ticker]
            
            # Run impact analysis
            analysis = self.analyze_news_impact(articles, price_history, ticker_mentions)
            
            # Get data for this specific ticker
            ticker_data = analysis["summary_by_ticker"].get(ticker.upper(), {})
            impacts = ticker_data.get("impacts", [])
            
            if not impacts or len(impacts) < 2:
                return {
                    "correlation": 0.0,
                    "sentiment_price_correlation": 0.0,
                    "count": len(impacts),
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "message": "Insufficient data points to calculate correlation (need at least 2 events)"
                }
            
            # Collect sentiment and impact values for correlation
            sentiments = []
            price_changes = []
            
            for impact in impacts:
                sentiment = impact.get("sentiment_score", 0.0)
                price_change = impact.get("price_change_pct", 0.0)
                
                # Only include if both values are available
                if sentiment != 0.0 and price_change != 0.0:
                    sentiments.append(sentiment)
                    price_changes.append(price_change)
            
            if len(sentiments) < 2:
                return {
                    "correlation": 0.0,
                    "sentiment_price_correlation": 0.0,
                    "count": len(sentiments),
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "message": "Insufficient data points with both sentiment and price change to calculate correlation"
                }
            
            # Calculate Pearson correlation coefficient using the actual formula
            n = len(sentiments)
            sum_sentiment = sum(sentiments)
            sum_price_change = sum(price_changes)
            sum_sentiment_sq = sum(s ** 2 for s in sentiments)
            sum_price_sq = sum(p ** 2 for p in price_changes)
            sum_sentiment_price = sum(s * p for s, p in zip(sentiments, price_changes))
            
            numerator = n * sum_sentiment_price - sum_sentiment * sum_price_change
            denominator_sqrt_part1 = (n * sum_sentiment_sq - sum_sentiment ** 2)
            denominator_sqrt_part2 = (n * sum_price_sq - sum_price_change ** 2)
            
            if denominator_sqrt_part1 <= 0 or denominator_sqrt_part2 <= 0:
                correlation = 0.0
            else:
                denominator = (denominator_sqrt_part1 * denominator_sqrt_part2) ** 0.5
                if denominator == 0:
                    correlation = 0.0
                else:
                    correlation = numerator / denominator
            
            return {
                "correlation": correlation,
                "sentiment_price_correlation": correlation,
                "count": len(sentiments),
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "sample_data": {
                    "first_few_sentiments": sentiments[:5],
                    "first_few_price_changes": price_changes[:5]
                }
            }
            
        except Exception as e:
            print(f"Error calculating correlation for {ticker}: {str(e)}")
            return {
                "correlation": 0.0,
                "sentiment_price_correlation": 0.0,
                "count": 0,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "error": str(e),
                "message": "Correlation calculation failed, returning fallback values to maintain never-empty contract"
            }


# Global instance
news_impact_model = NewsImpactModel()

# Convenience functions
def analyze_news_impact(articles: List[Dict[str, Any]], 
                      price_history: Dict[str, List[Dict[str, Any]]],
                      ticker_mentions: Optional[Dict[str, List[str]]] = None):
    """
    Analyze the impact of news articles on specific assets
    """
    return news_impact_model.analyze_news_impact(articles, price_history, ticker_mentions)

def calculate_news_price_correlation(articles: List[Dict[str, Any]], 
                                   price_history: Dict[str, List[Dict[str, Any]]],
                                   ticker: str):
    """
    Calculate correlation between news sentiment and price movements for a ticker
    """
    return news_impact_model.calculate_correlation_news_price(articles, price_history, ticker)

def get_sentiment_score(title: str, content: str = "", source: str = ""):
    """
    Get sentiment score for news article
    """
    return news_impact_model._calculate_sentiment_score(title, content, source)