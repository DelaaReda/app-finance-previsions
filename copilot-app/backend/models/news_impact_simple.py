"""
Simple News Impact Analysis Model
Task: FC-API-030 - News Impact Analysis
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


class SimpleNewsImpactModel:
    """
    Simple but effective model for analyzing news impact on assets
    """
    
    def __init__(self):
        pass
    
    def calculate_news_price_correlation(self, 
                                       news_articles: List[Dict[str, Any]], 
                                       price_data: Dict[str, List[Dict[str, Any]]],
                                       ticker: str) -> float:
        """
        Calculate basic correlation between news sentiment and price movements
        """
        try:
            target_ticker = ticker.upper()
            
            # Check if price data exists for this ticker
            if target_ticker not in price_data:
                return 0.0
            
            ticker_prices = price_data[target_ticker]
            
            # Find news articles mentioning this ticker
            relevant_news = []
            for article in news_articles:
                title = article.get("title", "").upper()
                description = article.get("description", "").upper()
                article_tickers = [t.upper() for t in article.get("tickers", [])]
                
                if (target_ticker in title or 
                    target_ticker in description or 
                    target_ticker in article_tickers):
                    
                    # Calculate sentiment for this article
                    sentiment = self._calculate_sentiment_score(
                        article.get("title", ""), 
                        article.get("description", ""), 
                        article.get("source", "")
                    )
                    
                    pub_date = article.get("pubDate") or article.get("date") or article.get("timestamp")
                    if pub_date:
                        relevant_news.append({
                            "date": pub_date,
                            "sentiment": sentiment
                        })
            
            if not relevant_news or len(ticker_prices) < 2:
                return 0.0  # Not enough data
            
            # Match sentiment with subsequent price changes
            changes_and_sentiments = []
            
            for news_item in relevant_news:
                try:
                    news_dt = datetime.fromisoformat(news_item["date"].replace('Z', '+00:00'))
                    
                    # Find closest price before and after news
                    price_before = self._find_closest_price(ticker_prices, news_dt, -24)  # 24h before
                    price_after = self._find_closest_price(ticker_prices, news_dt, 48)   # 48h after
                    
                    if (price_before is not None and price_after is not None and 
                        price_before != 0):
                        price_change = (price_after - price_before) / price_before
                        changes_and_sentiments.append((price_change, news_item["sentiment"]))
                        
                except ValueError:
                    continue  # Skip if date parsing fails
                except:
                    continue
            
            if len(changes_and_sentiments) < 2:
                return 0.0  # Need at least 2 pairs for correlation
            
            # Calculate correlation
            changes, sentiments = zip(*changes_and_sentiments)
            return self._calculate_simple_correlation(list(changes), list(sentiments))
                
        except Exception as e:
            print(f"Error calculating correlation: {str(e)}")
            return 0.0  # Return 0 as fallback
    
    def _calculate_sentiment_score(self, title: str, description: str = "", source: str = "") -> float:
        """
        Calculate basic sentiment score using keyword counting
        """
        try:
            text = (title + " " + description).lower()
            
            positive_keywords = [
                'rise', 'gain', 'profit', 'increase', 'up', 'boost', 'positive', 'growth', 
                'outperform', 'upgrade', 'buy', 'strong', 'excellent', 'beat', 'surprise',
                'bullish', 'rally', 'success', 'expansion', 'approval', 'deal',
                'partnership', 'contract', 'acquisition', 'merger', 'dividend'
            ]
            
            negative_keywords = [
                'fall', 'loss', 'drop', 'down', 'decline', 'decrease', 'weak', 'negative',
                'miss', 'downgrade', 'sell', 'bearish', 'crash', 'crisis', 'failure',
                'scandal', 'lawsuit', 'regulatory', 'ban', 'shutdown', 'bankruptcy'
            ]
            
            pos_count = sum(1 for word in positive_keywords if word in text)
            neg_count = sum(1 for word in negative_keywords if word in text)
            
            total_sentiment = pos_count + neg_count
            if total_sentiment > 0:
                sentiment = (pos_count - neg_count) / total_sentiment
            else:
                sentiment = 0.0  # Neutral if no sentiment words
            
            return max(-1.0, min(1.0, sentiment))
        except:
            return 0.0  # Neutral if error
    
    def _find_closest_price(self, price_history: List[Dict[str, Any]], 
                           target_time: datetime, offset_hours: int) -> Optional[float]:
        """
        Find price at specified offset from target time
        """
        try:
            search_time = target_time + timedelta(hours=offset_hours)
            best_match = None
            best_diff = timedelta.max
            
            for price_point in price_history:
                price_timestamp = price_point.get("timestamp") or price_point.get("date")
                if price_timestamp:
                    try:
                        price_time = datetime.fromisoformat(price_timestamp.replace('Z', '+00:00'))
                        time_diff = abs(price_time - search_time)
                        
                        if time_diff < best_diff:
                            price_value = (price_point.get("close") or 
                                         price_point.get("adjusted_close") or 
                                         price_point.get("price"))
                            if price_value is not None and isinstance(price_value, (int, float)):
                                best_match = price_value
                                best_diff = time_diff
                    except ValueError:
                        continue
            
            return best_match
        except:
            return None
    
    def _calculate_simple_correlation(self, x_vals: List[float], y_vals: List[float]) -> float:
        """
        Calculate simple correlation between two lists
        """
        try:
            if len(x_vals) != len(y_vals) or len(x_vals) < 2:
                return 0.0
            
            n = len(x_vals)
            mean_x = sum(x_vals) / n
            mean_y = sum(y_vals) / n
            
            numer = sum((x_vals[i] - mean_x) * (y_vals[i] - mean_y) for i in range(n))
            sum_sq_x = sum((x_vals[i] - mean_x)**2 for i in range(n))
            sum_sq_y = sum((y_vals[i] - mean_y)**2 for i in range(n))
            
            denom = (sum_sq_x * sum_sq_y)**0.5
            if denom == 0:
                return 0.0
            
            correlation = numer / denom
            return max(-1.0, min(1.0, correlation))
        except:
            return 0.0
    
    def calculate_impact_score(self, 
                             sentiment_score: float, 
                             price_correlation: float,
                             news_reliability: float = 0.5,
                             time_weight: float = 1.0) -> float:
        """
        Calculate basic impact score from multiple factors
        """
        try:
            # Simple weighted impact calculation
            impact = (abs(sentiment_score) * 0.4 + 
                     abs(price_correlation) * 0.4 + 
                     news_reliability * 0.15 + 
                     time_weight * 0.05)
            return max(0.0, min(1.0, impact))
        except:
            return 0.0  # No impact if error
    
    def analyze_news_impact(self, 
                           articles: List[Dict[str, Any]], 
                           price_history: Dict[str, List[Dict[str, Any]]],
                           target_tickers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Analyze comprehensive news impact on assets with fallback protection
        """
        try:
            result = {
                "articles_analyzed": len(articles),
                "tickers_analyzed": [],
                "impact_results": {},
                "summary": {},
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "source": ["simple_news_impact_model", "fc-api-030"]
            }
            
            if not articles or not price_history:
                result["message"] = "Insufficient data for analysis"
                return result
            
            # Determine tickers to analyze
            if target_tickers:
                tickers_to_analyze = [t.upper() for t in target_tickers]
            else:
                # Extract mentioned tickers from articles
                all_tickers = set()
                for article in articles:
                    # From tickers field
                    article_tickers = article.get("tickers", [])
                    for ticker in article_tickers:
                        if isinstance(ticker, str) and ticker.strip():
                            all_tickers.add(ticker.upper())
                    
                    # From content using regex
                    title = article.get("title", "").upper()
                    description = article.get("description", "").upper()
                    text = title + " " + description
                    potential_tickers = re.findall(r'\b([A-Z]{2,5})\b', text)
                    
                    # Filter out common words
                    common_words = {
                        'THE', 'AND', 'FOR', 'NOT', 'HAS', 'GET', 'CAN', 'NOW', 'NEW', 'END', 'SET', 
                        'RUN', 'ALL', 'ANY', 'USD', 'EUR', 'GBP', 'COM', 'INC', 'LTD', 'CORP',
                        'DATE', 'TIME', 'USER', 'API', 'URL', 'ID', 'DATA', 'FILE'
                    }
                    
                    for potential in potential_tickers:
                        if potential not in common_words and len(potential) >= 2:
                            all_tickers.add(potential)
                
                tickers_to_analyze = list(all_tickers)[:15]  # Limit analysis
            
            # Process each ticker
            for ticker in tickers_to_analyze:
                if ticker in price_history:
                    correlation = self.calculate_news_price_correlation(articles, price_history, ticker)
                    
                    # Aggregate sentiment for this ticker
                    ticker_sentiments = []
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
                            ticker_sentiments.append(sentiment)
                    
                    avg_sentiment = sum(ticker_sentiments) / len(ticker_sentiments) if ticker_sentiments else 0.0
                    article_count = len(ticker_sentiments)
                    
                    impact_score = self.calculate_impact_score(avg_sentiment, correlation)
                    
                    result["impact_results"][ticker] = {
                        "impact_score": impact_score,
                        "avg_sentiment": avg_sentiment,
                        "price_correlation": correlation,
                        "articles_mentioned": article_count,
                        "generated_at": datetime.utcnow().isoformat() + "Z"
                    }
                    result["tickers_analyzed"].append(ticker)
            
            # Add summary
            all_scores = [v["impact_score"] for v in result["impact_results"].values()]
            avg_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
            
            result["summary"] = {
                "total_tickers": len(result["tickers_analyzed"]),
                "average_impact_score": avg_score,
                "total_relevant_articles": sum(v["articles_mentioned"] for v in result["impact_results"].values()),
                "generated_at": datetime.utcnow().isoformat() + "Z"
            }
            
            return result
            
        except Exception as e:
            # Return fallback to maintain never-empty contract
            return {
                "articles_analyzed": len(articles),
                "tickers_analyzed": [],
                "impact_results": {},
                "summary": {
                    "total_tickers": 0,
                    "average_impact_score": 0.0,
                    "total_relevant_articles": 0,
                    "generated_at": datetime.utcnow().isoformat() + "Z"
                },
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "error": str(e),
                "message": "News impact analysis failed but fallback data returned to maintain never-empty contract"
            }


# Global instance
simple_news_impact_model = SimpleNewsImpactModel()

# Convenience functions
def calculate_news_price_correlation(articles, prices, ticker):
    return simple_news_impact_model.calculate_news_price_correlation(articles, prices, ticker)

def calculate_impact_score(sentiment, correlation, reliability=0.5, time_weight=1.0):
    return simple_news_impact_model.calculate_impact_score(sentiment, correlation, reliability, time_weight)

def analyze_news_impact(articles, prices, tickers=None):
    return simple_news_impact_model.analyze_news_impact(articles, prices, tickers)