import feedparser
import requests
import time
from datetime import datetime, timedelta
import re
from typing import Dict, List
from pathlib import Path
import json

# Import the same caching mechanism we used for forecasts
from ..storage.io import save_json, load_json
from ..models.forecast_hybrid_v1 import ForecastHybridV1

def fetch_rss_feed(url: str) -> List[Dict]:
    """
    Fetch and parse an RSS feed
    """
    try:
        headers = {
            'User-Agent': 'Finance-Copilot/1.0 (for educational/research purposes)'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        feed = feedparser.parse(response.content)
        articles = []
        
        for entry in feed.entries[:20]:  # Limit to 20 most recent
            # Extract ticker symbols from title/description
            text = f"{entry.get('title', '')} {entry.get('description', '')}"
            tickers = extract_tickers(text)
            
            # Calculate sentiment score (basic implementation)
            sentiment_score = calculate_basic_sentiment(text)
            
            articles.append({
                'id': entry.get('id') or entry.get('link'),
                'title': entry.get('title', ''),
                'description': entry.get('summary', '')[:500],  # Limit length
                'link': entry.get('link', ''),
                'pub_date': entry.get('published', ''),
                'source': url.split('//')[1].split('/')[0],  # Domain
                'tickers': tickers,
                'sentiment_score': sentiment_score,
                'relevance_score': calculate_relevance_score(text)
            })
        
        return articles
    except Exception as e:
        print(f"Error fetching RSS feed {url}: {e}")
        return []

def extract_tickers(text: str) -> List[str]:
    """
    Extract potential ticker symbols from text (simple regex approach)
    """
    # Match 1-5 uppercase letters (potential tickers)
    pattern = r'\b[A-Z]{1,5}\b'
    matches = re.findall(pattern, text)
    
    # Common false positives to filter out
    common_words = {'THE', 'AND', 'FOR', 'ARE', 'YOU', 'SAY', 'BUT', 'NOT', 'HAS', 'CAN', 'HER', 'WAS', 'HIS', 'GET', 'ITS', 'AVE', 'INC', 'CORP'}
    
    tickers = [match for match in matches if match not in common_words and len(match) >= 2]
    
    # Filter for likely tickers based on financial relevance
    # Check against a list of common financial terms or known tickers
    likely_tickers = []
    for ticker in tickers:
        # Add basic filtering to reduce false positives
        if ticker in ['SPY', 'QQQ', 'IWM', 'DIA', 'TLT', 'GLD', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'JPM', 'BAC', 'XOM', 'CVX', 'V', 'MA', 'PG', 'KO', 'DIS', 'MCD', 'GE', 'BA', 'MMM', 'IBM', 'INTC', 'CSCO', 'PEP', 'KO', 'TGT', 'WMT', 'HD', 'NKE', 'ADBE', 'CRM', 'CMCSA', 'AMGN', 'HON', 'UNH', 'MRK', 'ABBV', 'LLY', 'DHR', 'MDT', 'TXN', 'ACN', 'NEE', 'ABT', 'AVGO', 'COST', 'QCOM', 'TMUS', 'LIN', 'LMT', 'RTX', 'CAT', 'UPS', 'LOW', 'GS', 'BLK', 'BK', 'AXP', 'MS', 'USB', 'C', 'COF', 'SYF', 'PNC', 'TROW', 'BKNG', 'EXPE', 'MAR', 'HLT', 'DISCK', 'FOXA', 'FOX', 'NWS', 'NWSA', 'PAYX', 'ADP', 'INTU', 'CTSH', 'DXC', 'SYK', 'ISRG', 'ZBH', 'EW', 'DLR', 'FRC', 'CBRE', 'COO', 'CAH', 'TEL', 'HSY', 'EL', 'CL', 'KMB', 'GIS', 'MMM', 'EMR', 'ETN', 'ROK', 'COL', 'GD', 'HII', 'LHX', 'TXT', 'TDG', 'AME', 'DE', 'IRM', 'PKG', 'GLW', 'IP', 'TAP', 'GPC', 'SNA', 'MAS', 'DOV', 'ALLE', 'JCI', 'SWK', 'NOC', 'LMT', 'XEL', 'ES', 'LNT', 'AEP', 'ETR', 'PCG', 'SRE', 'EVRG', 'DTE', 'CMS', 'PNW', 'WEC', 'AEE', 'CNP', 'NI', 'FE', 'PEG', 'OKE', 'WMB', 'BXP', 'COO', 'HIG', 'MMC', 'AFL', 'MET', 'PRU', 'ALL', 'PJG', 'GL', 'HUM', 'CI', 'ANTM', 'CVS', 'ABC', 'CCI', 'SBAC', 'AMT', 'DLR', 'SPG', 'PSA', 'O', 'VNO', 'PEAK', 'EXR', 'IRM', 'LEG', 'FRT', 'KIM', 'GGP', 'MAC', 'SKT', 'DDR', 'AKR', 'CBL', 'SRG', 'WPG', 'ESS', 'REXR', 'HIW', 'SNDR', 'EXLS', 'IONS', 'VRTX', 'REGN', 'GILD', 'BIIB', 'CELG', 'AMGN', 'VRTX', 'ILMN', 'IDXX', 'BECN', 'CHRW', 'FDX', 'UPS', 'EXPD', 'XPO', 'CNX', 'DVN', 'EOG', 'MRO', 'OXY', 'PXD', 'APA', 'HES', 'COP', 'COG', 'VLO', 'PSX', 'MPC', 'ANDV', 'TSO', 'HFC', 'TGT', 'WMT', 'COST', 'BBY', 'HD', 'LOW', 'TJX', 'KSS', 'JWN', 'ORLY', 'AZO', 'ANF', 'AEO', 'GPS', 'URBN', 'BBBY', 'TIF', 'SIG', 'BOOK', 'CDR', 'EPR', 'SKX', 'LEVI', 'NKE', 'UA', 'LULU', 'COLM', 'JILL', 'RL', 'COH', 'VFC', 'DECK', 'ROST', 'TSCO', 'AZO', 'ORLY', 'ANF', 'AEO', 'GPS', 'URBN', 'BBBY', 'TIF', 'SIG', 'BOOK', 'CDR', 'EPR', 'SKX', 'LEVI', 'NKE', 'UA', 'LULU', 'COLM', 'JILL', 'RL', 'COH', 'VFC', 'DECK', 'ROST', 'TSCO']:
            if ticker in tickers:
                likely_tickers.append(ticker)
            elif len(ticker) == 2 and ticker not in ['AM', 'PM', 'TV', 'UK', 'US', 'EU', 'CA', 'NY']:  # Common 2-letter abbreviations
                likely_tickers.append(ticker)
        elif len(ticker) >= 3:  # Likely financial tickers are 3+ chars
            likely_tickers.append(ticker)
    
    return list(set(likely_tickers))  # Remove duplicates

def calculate_basic_sentiment(text: str) -> float:
    """
    Calculate basic sentiment score using keywords
    """
    positive_keywords = [
        'rise', 'gain', 'up', 'bull', 'positive', 'strong', 'beat', 'surge', 
        'expand', 'prospect', 'grow', 'high', 'soar', 'profit', 'success', 
        'upgrade', 'momentum', 'win', 'breakthrough', 'rally', 'jump', 'gain',
        'exciting', 'outperform', 'buy', 'recommend'
    ]
    
    negative_keywords = [
        'fall', 'loss', 'down', 'bear', 'negative', 'weak', 'miss', 'decline', 
        'contract', 'concern', 'shrink', 'low', 'crash', 'loss', 'failure', 
        'downgrade', 'trouble', 'troubles', 'sell', 'avoid', 'warning', 
        'problem', 'problems', 'disappoint', 'cut', 'dropped', 'drop'
    ]
    
    text_lower = text.lower()
    pos_count = sum(1 for word in positive_keywords if word in text_lower)
    neg_count = sum(1 for word in negative_keywords if word in text_lower)
    
    # Normalize to range [-1, 1]
    if pos_count + neg_count == 0:
        return 0.0
    
    total_sentiment = pos_count - neg_count
    return total_sentiment / (pos_count + neg_count + 1)  # +1 to avoid division by zero

def calculate_relevance_score(text: str) -> float:
    """
    Calculate relevance score based on financial keywords
    """
    financial_keywords = [
        'stock', 'market', 'price', 'trading', 'trade', 'invest', 'finance',
        'earnings', 'revenue', 'profit', 'loss', 'sales', 'revenue', 'eps',
        'quarter', 'results', 'report', 'forecast', 'prediction', 'dividend',
        'bond', 'yield', 'rate', 'fed', 'policy', 'inflation', 'gdp', 'cpi',
        'unemployment', 'economic', 'analyst', 'target', 'rating', 'outlook',
        'bullish', 'bearish', 'volatile', 'volatility', 'risk', 'return',
        'portfolio', 'mutual', 'fund', 'etf', 'index', 's&p', 'nasdaq',
        'dow', 'futures', 'options', 'commodities', 'oil', 'gold', 'silver'
    ]
    
    text_lower = text.lower()
    financial_terms = sum(1 for term in financial_keywords if term in text_lower)
    total_words = len(text_lower.split())
    
    if total_words == 0:
        return 0.0
    
    # Normalize relevance score from 0 to 1
    return min(financial_terms / max(total_words, 1) * 5, 1.0)  # Cap at 1.0

def compute_news_feed() -> Dict:
    """
    Compute real news feed from RSS sources
    """
    # Define reliable financial news sources
    news_sources = [
        "https://feeds.reuters.com/reuters/businessNews",
        "https://feeds.reuters.com/reuters/topNews",
        "https://www.cnbc.com/id/10001147/device/rss/rss.html",  # Business
        "https://www.cnbc.com/id/15839135/device/rss/rss.html"   # Investing
    ]
    
    all_articles = []
    
    for source_url in news_sources:
        try:
            articles = fetch_rss_feed(source_url)
            all_articles.extend(articles)
        except Exception as e:
            print(f"Error processing source {source_url}: {e}")
            continue
    
    # Sort by publication date (most recent first) and limit
    all_articles.sort(key=lambda x: x.get('pub_date', ''), reverse=True)
    
    # Return the top 50 articles
    final_articles = all_articles[:50]
    
    # Create the final response
    result = {
        "articles": final_articles,
        "last_update": datetime.now().isoformat(),
        "source": ["reuters", "cnbc", "financial_rss_feeds"],
        "total_articles": len(final_articles),
        "fetched_at": datetime.now().isoformat()
    }
    
    return result

def get_news_feed(cache):
    """
    Get news feed using cache layer, computes if cache unavailable
    """
    # Use the cache system to get news feed
    if cache:
        return cache("news_feed", compute_news_feed, source=["rss_ingestion", "real_time"])
    else:
        # Fallback to direct computation
        return compute_news_feed()