#!/usr/bin/env python3
"""
News Freshness Optimizer
Implements rapid news ingestion to meet <10 min median freshness requirement
"""
import sys
from pathlib import Path
import asyncio
import time
from datetime import datetime, timedelta
import logging

# Add src to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ingestion.finnews import run_pipeline
from research.rag_store import RAGStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/news_freshness.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class NewsFreshnessOptimizer:
    """Optimizes news ingestion to achieve <10 min freshness median."""
    
    def __init__(self):
        self.rag_store = RAGStore()
        self.last_run = None
        self.news_buffer = []
        
    def calculate_freshness_stats(self):
        """Calculate freshness statistics from RAG store."""
        stats = self.rag_store.stats()
        
        if stats['news_count'] == 0:
            return {
                'median_freshness_minutes': float('inf'),
                'avg_freshness_minutes': float('inf'),
                'recent_news_count': 0
            }
        
        # Read news items and calculate freshness
        import json
        from pathlib import Path
        
        news_file = Path("data/rag/news.jsonl")
        if not news_file.exists():
            return {
                'median_freshness_minutes': float('inf'),
                'avg_freshness_minutes': float('inf'),
                'recent_news_count': 0
            }
        
        news_items = []
        with open(news_file, "r") as f:
            for line in f:
                if line.strip():
                    news_items.append(json.loads(line))
        
        # Calculate time differences in minutes
        time_diffs = []
        now = datetime.utcnow()
        
        for item in news_items:
            try:
                # Parse published date from metadata
                pub_date_str = item["meta"].get("date", "")
                if pub_date_str:
                    # Handle ISO format date string
                    pub_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                    if pub_date.tzinfo is not None:
                        from datetime import timezone
                        pub_date = pub_date.astimezone(timezone.utc).replace(tzinfo=None)
                    
                    diff_minutes = (now - pub_date).total_seconds() / 60
                    time_diffs.append(diff_minutes)
            except Exception:
                continue  # Skip if date parsing fails
        
        if not time_diffs:
            return {
                'median_freshness_minutes': float('inf'),
                'avg_freshness_minutes': float('inf'),
                'recent_news_count': 0
            }
        
        # Sort to calculate median
        time_diffs.sort()
        n = len(time_diffs)
        median = time_diffs[n//2] if n % 2 == 1 else (time_diffs[n//2-1] + time_diffs[n//2]) / 2
        
        avg_freshness = sum(time_diffs) / len(time_diffs)
        recent_count = len([d for d in time_diffs if d <= 60])  # News from last hour
        
        return {
            'median_freshness_minutes': median,
            'avg_freshness_minutes': avg_freshness,
            'recent_news_count': recent_count,
            'total_news_count': len(time_diffs),
            'freshness_samples': time_diffs
        }
    
    def optimize_ingestion_schedule(self):
        """Optimize the ingestion schedule based on freshness metrics."""
        stats = self.calculate_freshness_stats()
        
        logger.info(f"Current freshness stats: median={stats['median_freshness_minutes']:.1f}min, "
                   f"avg={stats['avg_freshness_minutes']:.1f}min, "
                   f"recent={stats['recent_news_count']} news in last hour")
        
        # Target: < 10 minutes median freshness
        target_minutes = 10.0
        current_median = stats['median_freshness_minutes']
        
        if current_median <= target_minutes:
            logger.info(f"✅ Current median freshness ({current_median:.1f}min) meets target (<{target_minutes}min)")
            # Slow down ingestion - run every 15-30 minutes
            return timedelta(minutes=20)
        else:
            # Speed up ingestion - run every 5-10 minutes
            speedup_factor = max(0.5, min(3.0, current_median / target_minutes))
            interval_minutes = max(2, min(10, int(15 / speedup_factor)))
            logger.info(f"⏳ Current median freshness ({current_median:.1f}min) exceeds target - "
                       f"increasing ingestion frequency to every {interval_minutes} minutes")
            return timedelta(minutes=interval_minutes)
    
    def ingest_news(self, regions=["US", "CA", "INTL"]):
        """Ingest fresh news and add to RAG store."""
        start_time = time.time()
        
        try:
            # Run the news pipeline for recent news (last hour)
            items = run_pipeline(
                regions=regions,
                window="1h",  # Focus on very recent news to improve freshness
                limit=50,      # Limit to avoid overwhelming
                per_source_cap=10  # Cap per source to spread across sources
            )
            
            # Add to RAG store
            for item in items:
                try:
                    self.rag_store.add_news_item({
                        'title': item.get('title', ''),
                        'url': item.get('link', ''),
                        'published': item.get('published', ''),
                        'summary': item.get('summary', ''),
                        'tickers': item.get('tickers', []),
                        'score': item.get('relevance', 0.5)
                    })
                except Exception as e:
                    logger.warning(f"Failed to add news item to RAG: {e}")
                    continue
            
            elapsed = time.time() - start_time
            logger.info(f"✅ Ingested {len(items)} news items in {elapsed:.2f}s")
            
            # Update last run time
            self.last_run = datetime.utcnow()
            
            return len(items)
            
        except Exception as e:
            logger.error(f"❌ News ingestion failed: {e}")
            return 0
    
    def run_optimized_ingestion(self, max_duration_hours=24):
        """Run continuously optimized news ingestion."""
        start_time = datetime.utcnow()
        total_news_ingested = 0
        
        logger.info("🚀 Starting optimized news ingestion service...")
        
        while True:
            # Check if we should stop based on max duration
            if (datetime.utcnow() - start_time).total_seconds() > (max_duration_hours * 3600):
                logger.info("⏰ Max duration reached, stopping ingestion service.")
                break
            
            # Perform ingestion
            count = self.ingest_news()
            total_news_ingested += count
            
            # Calculate optimal next run interval
            next_interval = self.optimize_ingestion_schedule()
            
            logger.info(f"Total news ingested so far: {total_news_ingested}")
            logger.info(f"Sleeping for {next_interval.total_seconds()/60:.1f} minutes...")
            
            # Sleep until next run
            time.sleep(next_interval.total_seconds())

def main():
    """Main function to run the news freshness optimizer."""
    optimizer = NewsFreshnessOptimizer()
    
    # Calculate initial stats
    logger.info("📊 Calculating initial freshness statistics...")
    stats = optimizer.calculate_freshness_stats()
    logger.info(f"Initial freshness: median={stats['median_freshness_minutes']:.1f}min, "
               f"avg={stats['avg_freshness_minutes']:.1f}min")
    
    # Run a single ingestion cycle to test
    logger.info("🔄 Testing news ingestion...")
    optimizer.ingest_news()
    
    # Calculate stats after ingestion
    stats = optimizer.calculate_freshness_stats()
    logger.info(f"Post-ingestion freshness: median={stats['median_freshness_minutes']:.1f}min, "
               f"avg={stats['avg_freshness_minutes']:.1f}min")
    
    # If we had more resources, we would run the continuous service
    # optimizer.run_optimized_ingestion(max_duration_hours=24)

if __name__ == "__main__":
    main()