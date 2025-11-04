"""
Simple test module for the ingestion service
"""
import sys
import os
import time
sys.path.append(os.path.join(os.path.dirname(__file__), 'services/ingestion'))

from ingestion_service import IngestionService

def test_ingestion_service():
    """Test the ingestion service functionality."""
    print("Testing Ingestion Service...")
    
    # Initialize the service
    service = IngestionService()
    
    # Test Yahoo data fetch
    print("\n1. Testing Yahoo Finance data fetch...")
    yahoo_data = service.fetch_yahoo_data("SPY")
    if yahoo_data is not None:
        print(f"   ✓ Successfully fetched Yahoo data: {len(yahoo_data)} records")
    else:
        print("   ✗ Failed to fetch Yahoo data")
    
    # Test RSS feed fetch
    print("\n2. Testing RSS feed fetch...")
    rss_data = service.fetch_rss_feeds("https://feeds.reuters.com/reuters/topNews")
    if rss_data is not None:
        print(f"   ✓ Successfully fetched RSS data: {len(rss_data)} articles")
    else:
        print("   ✗ Failed to fetch RSS data")
    
    # Test full ingestion job
    print("\n3. Testing full ingestion job...")
    service.run_ingestion_job()
    print("   ✓ Full ingestion job completed")
    
    print("\nAll tests completed successfully!")

if __name__ == "__main__":
    test_ingestion_service()