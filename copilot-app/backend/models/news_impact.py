"""
News Impact Analysis Model
Task: FC-API-030 - News Impact Analysis
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import sys
from pathlib import Path
import re


class NewsImpactModel:
    """
    Model for analyzing the impact of news on financial assets
    """
    
    def __init__(self):
        pass
    
    def calculate_news_price_correlation(self, 
                                       news_articles: List[Dict[str, Any]], 
                                       price_data: Dict[str, List[Dict[str, Any]]],
                                       ticker: str) -> float:
        """
        Calculate correlation between news sentiment and price movements for a specific ticker
        """
        try:
            target_ticker = ticker.upper()
            
            # Get price history for the specific ticker
            if target_ticker not in price_data:
                return 0.0  # No price data available for this ticker
            
            ticker_prices = price_data[target_ticker]
            
            # Find relevant news articles for this ticker
            relevant_news = []
            for article in news_articles:
                # Check if article mentions the target ticker
                title = article.get("title", "").upper()
                description = article.get("description", "").upper()
                article_tickers = [t.upper() for t in article.get("tickers", [])]
                
                if (target_ticker in title or 
                    target_ticker in description or 
                    target_ticker in article_tickers):
                    
                    # Calculate sentiment score for this news article
                    sentiment = self._calculate_sentiment_score(
                        article.get("title", ""), 
                        article.get("description", ""), 
                        article.get("source", "")
                    )
                    
                    pub_date = article.get("pubDate") or article.get("date") or article.get("timestamp")
                    if pub_date:
                        relevant_news.append({
                            "pub_date": pub_date,
                            "sentiment": sentiment
                        })
            
            if not relevant_news or not ticker_prices:
                return 0.0  # Insufficient data for correlation calculation
            
            # Calculate price changes around news times and match with sentiment scores
            price_changes = []
            sentiment_scores = []
            
            for news_item in relevant_news:
                try:
                    # Parse news publication time
                    news_time = datetime.fromisoformat(news_item["pub_date"].replace('Z', '+00:00'))
                    
                    # Find price before and after news publication
                    price_before = self._find_price_around_time(ticker_prices, news_time, hours_offset=-1)
                    price_after = self._find_price_around_time(ticker_prices, news_time, hours_offset=2)
                    
                    if price_before is not None and price_after is not None and price_before != 0:
                        # Calculate price change percentage
                        price_change = (price_after - price_before) / price_before
                        price_changes.append(price_change)
                        sentiment_scores.append(news_item["sentiment"])
                except ValueError:
                    continue  # Skip if date parsing fails
                except:
                    continue  # Continue with other articles if one fails
            
            # Calculate correlation if we have sufficient data points
            if len(price_changes) >= 2 and len(sentiment_scores) >= 2:
                correlation = self._calculate_correlation(price_changes, sentiment_scores)
                return correlation
            else:
                return 0.0  # Not enough data points for meaningful correlation
                
        except Exception as e:
            print(f"Error calculating news price correlation: {str(e)}")
            # Return 0 correlation as fallback to maintain never-empty contract
            return 0.0
    
    def _calculate_sentiment_score(self, title: str, description: str = "", source: str = "") -> float:
        """
        Calculate sentiment score from news content
        """
        try:
            text = (title + " " + description).lower()
            
            # Sentiment keywords
            positive_keywords = [
                'rise', 'gain', 'profit', 'increase', 'up', 'boost', 'positive', 'growth', 
                'outperform', 'upgrade', 'buy', 'strong', 'excellent', 'beat', 'surprise',
                'bullish', 'rally', 'success', 'expansion', 'approval', 'deal',
                'partnership', 'contract', 'acquisition', 'merger', 'dividend', 'return',
                'rebound', 'recovery', 'momentum', 'breakthrough', 'innovation', 'leadership'
            ]
            
            negative_keywords = [
                'fall', 'loss', 'drop', 'down', 'decline', 'decrease', 'weak', 'negative',
                'miss', 'downgrade', 'sell', 'bearish', 'crash', 'crisis', 'failure',
                'scandal', 'lawsuit', 'regulatory', 'ban', 'shutdown', 'bankruptcy', 'fraud',
                'recession', 'volatile', 'risk', 'concern', 'warn', 'cut', 'layoffs'
            ]
            
            # Count sentiment words
            pos_count = sum(1 for word in positive_keywords if word in text)
            neg_count = sum(1 for word in negative_keywords if word in text)
            
            # Calculate normalized sentiment score
            total_sentiment_words = pos_count + neg_count
            if total_sentiment_words > 0:
                sentiment_score = (pos_count - neg_count) / total_sentiment_words
            else:
                sentiment_score = 0.0  # Neutral if no sentiment words found
            
            # Clamp to [-1.0, 1.0] range
            return max(-1.0, min(1.0, sentiment_score))
            
        except Exception as e:
            print(f"Error calculating sentiment score: {str(e)}")
            return 0.0  # Neutral sentiment as fallback
    
    def _find_price_around_time(self, price_history: List[Dict[str, Any]], 
                               target_time: datetime, hours_offset: int) -> Optional[float]:
        """
        Find the price closest to a specific time offset
        """
        try:
            search_time = target_time + timedelta(hours=hours_offset)
            best_match = None
            best_time_diff = timedelta.max
            
            for price_point in price_history:
                price_timestamp = price_point.get("timestamp") or price_point.get("date") or price_point.get("time")
                if price_timestamp:
                    try:
                        price_time = datetime.fromisoformat(price_timestamp.replace('Z', '+00:00'))
                        time_diff = abs(price_time - search_time)
                        
                        # Check if this is the closest match so far
                        if time_diff < best_time_diff:
                            # Get price value from available fields
                            price_value = (price_point.get("close") or 
                                         price_point.get("adjusted_close") or 
                                         price_point.get("price") or 
                                         price_point.get("value"))
                            
                            if price_value is not None and isinstance(price_value, (int, float)) and price_value != 0:
                                best_match = price_value
                                best_time_diff = time_diff
                    except ValueError:
                        continue  # Skip if timestamp parsing fails
            
            return best_match
        except Exception as e:
            print(f"Error finding price around time: {str(e)}")
            return None
    
    def _calculate_correlation(self, x_values: List[float], y_values: List[float]) -> float:
        """
        Calculate Pearson correlation coefficient between two series
        """
        try:
            if len(x_values) != len(y_values) or len(x_values) < 2:
                return 0.0
            
            n = len(x_values)
            
            # Calculate means
            mean_x = sum(x_values) / n
            mean_y = sum(y_values) / n
            
            # Calculate correlation components
            numerator = sum((x_values[i] - mean_x) * (y_values[i] - mean_y) for i in range(n))
            sum_sq_x = sum((x_values[i] - mean_x) ** 2 for i in range(n))
            sum_sq_y = sum((y_values[i] - mean_y) ** 2 for i in range(n))
            
            # Calculate correlation
            denominator = (sum_sq_x * sum_sq_y) ** 0.5
            
            if denominator == 0:
                return 0.0  # No variation in one or both series
            
            correlation = numerator / denominator
            return max(-1.0, min(1.0, correlation))  # Clamp to valid range
        except Exception as e:
            print(f"Error calculating correlation: {str(e)}")
            return 0.0  # Return 0 as fallback
    
    def calculate_impact_score(self, 
                             sentiment_score: float, 
                             price_correlation: float,
                             news_reliability: float = 0.5,
                             time_decay: float = 1.0) -> float:
        """
        Calculate overall impact score combining multiple factors
        """
        try:
            # Weighted impact calculation
            sentiment_weight = 0.3
            correlation_weight = 0.4
            reliability_weight = 0.2
            time_weight = 0.1
            
            # Calculate combined impact score
            weighted_impact = (
                abs(sentiment_score) * sentiment_weight +
                abs(price_correlation) * correlation_weight +
                news_reliability * reliability_weight +
                time_decay * time_weight
            )
            
            # Normalize to [0, 1] range
            final_impact = max(0.0, min(1.0, weighted_impact))
            return final_impact
        except Exception as e:
            print(f"Error calculating impact score: {str(e)}")
            return 0.0  # Return no impact as fallback
    
    def analyze_news_impact(self, 
                           articles: List[Dict[str, Any]], 
                           price_history: Dict[str, List[Dict[str, Any]]],
                           target_tickers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Comprehensive analysis of news impact on financial assets
        """
        try:
            result = {
                "articles_analyzed": len(articles),
                "tickers_analyzed": [],
                "ticker_impacts": {},
                "summary_statistics": {},
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "source": ["news_impact_model", "comprehensive_impact_analysis", "fc-api-030"]
            }
            
            if not articles or not price_history:
                result["message"] = "Insufficient data for news impact analysis"
                return result
            
            # Determine which tickers to analyze
            if target_tickers:
                tickers_to_analyze = [t.upper() for t in target_tickers]
            else:
                # Extract all tickers mentioned in articles
                all_mentioned_tickers = set()
                for article in articles:
                    # Extract from tickers field
                    article_tickers = article.get("tickers", [])
                    for ticker in article_tickers:
                        if isinstance(ticker, str) and ticker.strip():
                            all_mentioned_tickers.add(ticker.upper())
                    
                    # Extract potential tickers from title/description using regex
                    title = article.get("title", "").upper()
                    description = article.get("description", "").upper()
                    text_content = title + " " + description
                    
                    # Find potential ticker symbols (2-5 uppercase letters)
                    potential_tickers = re.findall(r'\b([A-Z]{2,5})\b', text_content)
                    
                    # Filter out common words that aren't tickers
                    common_words = {
                        'THE', 'AND', 'FOR', 'NOT', 'HAS', 'HAD', 'GET', 'CAN', 'NOW', 'NEW', 
                        'END', 'SET', 'RUN', 'LET', 'ALL', 'ANY', 'EACH', 'EVERY', 'MORE',
                        'MOST', 'OTHER', 'SOME', 'SUCH', 'NO', 'ONLY', 'OWN', 'SAME', 'SO',
                        'THAN', 'TOO', 'VERY', 'JUST', 'COME', 'GIVE', 'LIVE', 'MOVE', 'PUT',
                        'SEE', 'SEEM', 'TRY', 'TURN', 'USE', 'WORK', 'ACT', 'BAD', 'BUSY',
                        'COLD', 'COOL', 'DUE', 'EARLY', 'EASY', 'FREE', 'GOOD', 'HOT', 'HUGE',
                        'IDEA', 'MAD', 'MAIN', 'NICE', 'OKAY', 'OPEN', 'REAL', 'SAFE', 'SLOW',
                        'SURE', 'TINY', 'TRUE', 'WARM', 'WAY', 'WILD', 'YOUNG', 'TOP', 'LOT',
                        'DAY', 'AGO', 'HOUR', 'DATE', 'TIME', 'USER', 'DATA', 'FILE', 'API',
                        'URL', 'ID', 'COM', 'INC', 'LTD', 'CORP', 'GROUP', 'BANK', 'FUND'
                    }
                    
                    for potential in potential_tickers:
                        if potential not in common_words and len(potential) >= 2:
                            all_mentioned_tickers.add(potential)
                
                tickers_to_analyze = list(all_mentioned_tickers)[:20]  # Limit to 20 to avoid overwhelming analysis
            
            # Analyze impact for each ticker
            for ticker in tickers_to_analyze:
                if ticker in price_history:
                    # Calculate correlation for this ticker
                    correlation = self.calculate_news_price_correlation(articles, price_history, ticker)
                    
                    # Calculate aggregate sentiment for articles mentioning this ticker
                    relevant_sentiment_scores = []
                    for article in articles:
                        title = article.get("title", "").upper()
                        description = article.get("description", "").upper()
                        article_tickers = [t.upper() for t in article.get("tickers", [])]
                        
                        if (ticker in title or ticker in description or ticker in article_tickers):
                            sentiment = self._calculate_sentiment_score(
                                article.get("title", ""),
                                article.get("description", ""),
                                article.get("source", "")
                            )
                            if sentiment is not None:
                                relevant_sentiment_scores.append(sentiment)
                    
                    avg_sentiment = sum(relevant_sentiment_scores) / len(relevant_sentiment_scores) if relevant_sentiment_scores else 0.0
                    total_articles = len(relevant_sentiment_scores)
                    
                    # Calculate impact score
                    news_reliability = 0.6  # Default medium reliability
                    time_decay = 1.0  # Default full impact for recent news
                    
                    impact_score = self.calculate_impact_score(
                        avg_sentiment,
                        correlation,
                        news_reliability,
                        time_decay
                    )
                    
                    # Store results for this ticker
                    result["ticker_impacts"][ticker] = {
                        "impact_score": impact_score,
                        "average_sentiment": avg_sentiment,
                        "price_correlation": correlation,
                        "articles_mentioned": total_articles,
                        "metrics": {
                            "sentiment_strength": abs(avg_sentiment),
                            "correlation_strength": abs(correlation),
                            "news_volume_impact": min(1.0, total_articles / 10.0)  # Scale by volume
                        }
                    }
                    result["tickers_analyzed"].append(ticker)
            
            # Add summary statistics
            all_impact_scores = [data["impact_score"] for data in result["ticker_impacts"].values()]
            avg_impact = sum(all_impact_scores) / len(all_impact_scores) if all_impact_scores else 0.0
            
            # Find highest impact ticker
            highest_impact_ticker = None
            highest_impact_score = 0.0
            for ticker, data in result["ticker_impacts"].items():
                if data["impact_score"] > highest_impact_score:
                    highest_impact_score = data["impact_score"]
                    highest_impact_ticker = ticker
            
            result["summary_statistics"] = {
                "total_tickers_analyzed": len(result["tickers_analyzed"]),
                "average_impact_score": avg_impact,
                "highest_impact_ticker": highest_impact_ticker,
                "highest_impact_score": highest_impact_score,
                "total_relevant_articles": sum(data["articles_mentioned"] for data in result["ticker_impacts"].values()),
                "generated_at": datetime.utcnow().isoformat() + "Z"
            }
            
            return result
            
        except Exception as e:
            print(f"Error in comprehensive news impact analysis: {str(e)}")
            
            # Return fallback structure to maintain never-empty contract
            return {
                "articles_analyzed": len(articles),
                "tickers_analyzed": [],
                "ticker_impacts": {},
                "summary_statistics": {
                    "total_tickers_analyzed": 0,
                    "average_impact_score": 0.0,
                    "highest_impact_ticker": None,
                    "highest_impact_score": 0.0,
                    "total_relevant_articles": 0,
                    "generated_at": datetime.utcnow().isoformat() + "Z"
                },
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "source": ["news_impact_model", "error_fallback", "fc-api-030"],
                "error": str(e),
                "message": "News impact analysis failed but fallback data returned to maintain never-empty contract"
            }


# Global instance
news_impact_model = NewsImpactModel()

# Convenience functions
def calculate_news_price_correlation(news_articles: List[Dict[str, Any]], 
                                  price_history: Dict[str, List[Dict[str, Any]]],
                                  ticker: str) -> float:
    """Calculate correlation between news sentiment and price movements"""
    return news_impact_model.calculate_news_price_correlation(news_articles, price_history, ticker)

def calculate_impact_score(sentiment: float, price_correlation: float, 
                         reliability: float = 0.5, time_decay: float = 1.0) -> float:
    """Calculate overall impact score from multiple factors"""
    return news_impact_model.calculate_impact_score(sentiment, price_correlation, reliability, time_decay)

def analyze_news_impact(articles: List[Dict[str, Any]], 
                      price_history: Dict[str, List[Dict[str, Any]]],
                      tickers: Optional[List[str]] = None) -> Dict[str, Any]:
    """Comprehensive news impact analysis"""
    return news_impact_model.analyze_news_impact(articles, price_history, tickers)