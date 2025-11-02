#!/usr/bin/env python3
"""
Script to populate RAG store with historical data for 5+ years of context
"""
import sys
from pathlib import Path
import os

# Add src to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime, timedelta
import random
from research.rag_store import RAGStore

def populate_rag_store():
    """Populate RAG store with historical data spanning 5+ years."""
    print("Initializing RAG store...")
    rag_store = RAGStore()
    
    print("Populating with historical data...")
    
    # Generate synthetic news data for the past 5+ years
    start_date = datetime.now() - timedelta(days=365 * 5)  # 5 years ago
    current_date = start_date
    
    tickers = ["SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "TSM"]
    base_news = [
        "Fed holds rates steady amid inflation concerns",
        "Tech earnings beat expectations across the board",
        "Oil prices surge on supply concerns",
        "Bond yields rise as recession fears subside",
        "Retail sales show strong growth",
        "Unemployment rate drops to new low",
        "Economic data shows mixed signals",
        "Market volatility increases ahead of earnings season",
        "New trade agreement announced",
        "Major tech company announces new product line",
        "Central bank signals potential rate change",
        "Housing data shows signs of cooling",
        "Employment report beats expectations",
        "Consumer confidence reaches new high",
        "Supply chain disruptions affect multiple sectors",
        "Major acquisition announced in tech sector",
        "GDP growth exceeds forecasts",
        "Inflation data comes in lower than expected",
        "Corporate earnings disappoint",
        "Bitcoin experiences significant volatility"
    ]
    
    print("Adding news items...")
    added_news = 0
    while current_date < datetime.now():
        # Add 2-5 news items per day randomly
        daily_news_count = random.randint(2, 5)
        for _ in range(daily_news_count):
            news_title = random.choice(base_news)
            ticker = random.choice(tickers)
            
            # Create news item
            news_item = {
                "title": f"{ticker}: {news_title}",
                "url": f"https://example.com/news/{ticker.lower()}/{current_date.strftime('%Y%m%d')}",
                "published": current_date.isoformat(),
                "summary": f"{news_title} This news event has potential impact on {ticker} stock performance and market sentiment.",
                "score": random.uniform(0.3, 1.0),  # Score between 0.3 and 1.0
                "tickers": [ticker],
                "source": "synthetic"
            }
            
            rag_store.add_news_item(news_item)
            added_news += 1
            
        # Move to next day
        current_date += timedelta(days=1)
        
        # Print progress every 30 days
        if added_news % (30 * 3) == 0:  # Every ~30 days worth of data
            print(f"Added {added_news} news items so far...")
    
    # Add some series data (macro and price data)
    print("Adding series facts...")
    series_data = {
        "CPIAUCSL": {"name": "Consumer Price Index", "values": []},
        "FEDFUNDS": {"name": "Federal Funds Rate", "values": []},
        "GDP": {"name": "Gross Domestic Product", "values": []}
    }
    
    # Generate some synthetic series data
    start_date = datetime.now() - timedelta(days=365 * 5)  # 5 years ago
    current_date = start_date
    
    while current_date < datetime.now():
        # Add GDP data quarterly
        if current_date.day == 1 and current_date.month % 3 == 1:  # Beginning of each quarter
            series_data["GDP"]["values"].append({
                "date": current_date.isoformat(),
                "value": round(random.uniform(2.0, 4.0), 2)  # GDP growth rate
            })
        
        # Add CPI data monthly
        if current_date.day == 1:  # Beginning of each month
            series_data["CPIAUCSL"]["values"].append({
                "date": current_date.isoformat(),
                "value": round(random.uniform(2.0, 8.0), 2)  # Inflation rate
            })
            series_data["FEDFUNDS"]["values"].append({
                "date": current_date.isoformat(),
                "value": round(random.uniform(0.25, 5.5), 2)  # Fed funds rate
            })
        
        current_date += timedelta(days=30)  # Monthly
    
    # Add all series data to RAG
    rag_store.add_series_facts(series_data)
    
    # Show stats
    stats = rag_store.stats()
    print(f"\nPopulation complete! RAG store now contains:")
    print(f"- News items: {stats['news_count']}")
    print(f"- Series facts: {stats['facts_count']}")
    print(f"- Total items: {stats['total']}")
    
    print("\nRAG store is now populated with 5+ years of historical context data!")

if __name__ == "__main__":
    populate_rag_store()