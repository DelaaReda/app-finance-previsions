"""
Main ingestion module for financial data pipeline.

This module handles data ingestion from:
- Yahoo Finance API
- RSS feeds (financial news)
- FRED (Federal Reserve Economic Data)
"""
import os
import time
import logging
import yfinance as yf
import feedparser
import requests
import pandas as pd
from datetime import datetime
import schedule
import threading
import redis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IngestionService:
    def __init__(self):
        """Initialize the ingestion service with required configurations."""
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=0,
            decode_responses=True
        )
        self.cache_ttl = int(os.getenv('CACHE_TTL', 60))  # Default 60 seconds
        
    def fetch_yahoo_data(self, symbol):
        """Fetch data from Yahoo Finance for a given symbol."""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d")
            if not data.empty:
                # Cache the data with TTL
                cache_key = f"yahoo:{symbol}"
                self.redis_client.setex(cache_key, self.cache_ttl, data.to_json())
                logger.info(f"Successfully fetched and cached Yahoo data for {symbol}")
                return data
            else:
                logger.warning(f"No data returned for Yahoo symbol {symbol}")
                return None
        except Exception as e:
            logger.error(f"Error fetching Yahoo data for {symbol}: {str(e)}")
            return None

    def fetch_rss_feeds(self, rss_url):
        """Fetch data from RSS feeds."""
        try:
            feed = feedparser.parse(rss_url)
            articles = []
            for entry in feed.entries:
                article = {
                    'title': entry.title,
                    'summary': entry.summary,
                    'link': entry.link,
                    'published': entry.published if hasattr(entry, 'published') else None,
                    'source': rss_url
                }
                articles.append(article)
            
            # Cache the RSS data
            cache_key = f"rss:{rss_url.replace('http://', '').replace('https://', '').replace('/', ':')}"
            self.redis_client.setex(cache_key, self.cache_ttl, str(articles))
            logger.info(f"Successfully fetched and cached RSS data from {rss_url}")
            return articles
        except Exception as e:
            logger.error(f"Error fetching RSS data from {rss_url}: {str(e)}")
            return None

    def fetch_fred_data(self, series_id, api_key):
        """Fetch data from FRED API."""
        try:
            url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={api_key}&file_type=json"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                
                # Cache the FRED data
                cache_key = f"fred:{series_id}"
                self.redis_client.setex(cache_key, self.cache_ttl, str(data))
                logger.info(f"Successfully fetched and cached FRED data for {series_id}")
                return data
            else:
                logger.error(f"Error fetching FRED data for {series_id}: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error fetching FRED data for {series_id}: {str(e)}")
            return None

    def run_ingestion_job(self):
        """Run full ingestion job for all configured data sources."""
        logger.info("Starting ingestion job...")
        
        # Get configuration from environment or defaults
        symbols = os.getenv('YAHOO_SYMBOLS', 'SPY,QQQ,AAPL,MSFT,GOOGL').split(',')
        rss_urls = os.getenv('RSS_FEEDS', 'https://rss.cnn.com/rss/edition.rss,https://feeds.reuters.com/reuters/topNews').split(',')
        fred_series = os.getenv('FRED_SERIES', 'GDP,CPIAUCSL,UNRATE').split(',')
        fred_api_key = os.getenv('FRED_API_KEY')
        
        # Fetch Yahoo data for each symbol
        for symbol in symbols:
            symbol = symbol.strip()
            self.fetch_yahoo_data(symbol)
            time.sleep(0.5)  # Small delay to be respectful to the API
        
        # Fetch RSS feeds
        for rss_url in rss_urls:
            rss_url = rss_url.strip()
            self.fetch_rss_feeds(rss_url)
            time.sleep(0.5)  # Small delay to be respectful to the API
        
        # Fetch FRED data if API key is available
        if fred_api_key:
            for series_id in fred_series:
                series_id = series_id.strip()
                self.fetch_fred_data(series_id, fred_api_key)
                time.sleep(0.5)  # Small delay to be respectful to the API
        else:
            logger.warning("FRED_API_KEY not found in environment variables")
        
        logger.info("Ingestion job completed")

def job_scheduler():
    """Function to run the scheduler in a separate thread."""
    # Schedule the ingestion job to run every 30 seconds for demo purposes
    schedule.every(30).seconds.do(IngestionService().run_ingestion_job)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

def start_scheduler():
    """Start the job scheduler in a separate thread."""
    scheduler_thread = threading.Thread(target=job_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("Job scheduler started in background thread")
    return scheduler_thread

if __name__ == "__main__":
    logger.info("Starting Ingestion Service")
    
    # Initialize the ingestion service
    ingestion_service = IngestionService()
    
    # Start the scheduler in a background thread
    scheduler_thread = start_scheduler()
    
    # Run one initial ingestion job
    ingestion_service.run_ingestion_job()
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Ingestion service stopped by user")