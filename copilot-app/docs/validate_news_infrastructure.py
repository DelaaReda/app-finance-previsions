#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
News Infrastructure Validation Script
Test all components to ensure everything is working correctly.

Usage:
    python scripts/validate_news_infrastructure.py
    
Author: AI Assistant
Created: 2025-10-30
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# =======================
# Test Suite
# =======================

class NewsInfrastructureValidator:
    """Validator for news infrastructure."""
    
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.passed = 0
        self.failed = 0
    
    def test(self, name: str, func):
        """Run a test and record result."""
        print(f"\n{'='*60}")
        print(f"TEST: {name}")
        print(f"{'='*60}")
        
        try:
            func()
            self.passed += 1
            self.results.append({
                "name": name,
                "status": "✅ PASS",
                "error": None
            })
            print(f"✅ PASS: {name}")
        
        except Exception as e:
            self.failed += 1
            self.results.append({
                "name": name,
                "status": "❌ FAIL",
                "error": str(e)
            })
            print(f"❌ FAIL: {name}")
            print(f"   Error: {e}")
    
    def print_summary(self):
        """Print test summary."""
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total: {self.passed + self.failed}")
        print(f"Passed: {self.passed} ✅")
        print(f"Failed: {self.failed} ❌")
        print(f"Success Rate: {100 * self.passed / (self.passed + self.failed):.1f}%")
        
        if self.failed > 0:
            print(f"\nFailed Tests:")
            for result in self.results:
                if result["status"] == "❌ FAIL":
                    print(f"  - {result['name']}")
                    print(f"    {result['error']}")


# =======================
# Test Functions
# =======================

def test_imports():
    """Test that all modules can be imported."""
    from src.ingestion import news_schemas
    from src.ingestion import bronze_pipeline
    from src.ingestion import silver_pipeline
    from src.ingestion import gold_features_pipeline
    from src.api.services import news_service
    print("  ✓ All modules imported successfully")


def test_schemas():
    """Test that schemas are valid PyArrow schemas."""
    from src.ingestion.news_schemas import (
        BRONZE_SCHEMA, SILVER_SCHEMA, FEATURES_DAILY_SCHEMA,
        EVENTS_SCHEMA, EMBEDDINGS_SCHEMA
    )
    import pyarrow as pa
    
    # Validate schemas
    assert isinstance(BRONZE_SCHEMA, pa.Schema)
    assert isinstance(SILVER_SCHEMA, pa.Schema)
    assert isinstance(FEATURES_DAILY_SCHEMA, pa.Schema)
    assert isinstance(EVENTS_SCHEMA, pa.Schema)
    assert isinstance(EMBEDDINGS_SCHEMA, pa.Schema)
    
    print(f"  ✓ Bronze schema: {len(BRONZE_SCHEMA)} fields")
    print(f"  ✓ Silver schema: {len(SILVER_SCHEMA)} fields")
    print(f"  ✓ Features schema: {len(FEATURES_DAILY_SCHEMA)} fields")
    print(f"  ✓ Events schema: {len(EVENTS_SCHEMA)} fields")
    print(f"  ✓ Embeddings schema: {len(EMBEDDINGS_SCHEMA)} fields")


def test_bronze_pipeline():
    """Test Bronze pipeline functions."""
    from src.ingestion.bronze_pipeline import (
        canonicalize_url, detect_language, generate_article_id
    )
    import datetime as dt
    
    # Test URL canonicalization
    url = "https://example.com/article?utm_source=twitter&ref=share"
    canonical = canonicalize_url(url)
    assert "utm_source" not in canonical
    print(f"  ✓ URL canonicalization: {url} → {canonical}")
    
    # Test language detection
    text = "This is an English article about finance"
    lang = detect_language(text)
    assert lang in ["en", "fr", "de", "es"]
    print(f"  ✓ Language detection: '{text[:30]}...' → {lang}")
    
    # Test ID generation
    article_id = generate_article_id(
        canonical_url="https://example.com/article",
        published_at=dt.datetime(2025, 10, 30, 12, 0, 0, tzinfo=dt.timezone.utc),
        title="Test Article"
    )
    assert len(article_id) == 64  # SHA256 hash
    print(f"  ✓ Article ID generation: {article_id[:16]}...")


def test_silver_pipeline():
    """Test Silver pipeline functions."""
    from src.ingestion.silver_pipeline import (
        normalize_text, generate_simhash, hamming_distance,
        analyze_sentiment, classify_topics
    )
    
    # Test text normalization
    text = "This   is    a\n\ntest   with   extra    spaces"
    normalized = normalize_text(text)
    assert "  " not in normalized
    print(f"  ✓ Text normalization: '{text}' → '{normalized}'")
    
    # Test SimHash
    text1 = "Apple announces new iPhone with advanced features"
    text2 = "Apple unveils new iPhone with cutting-edge features"
    hash1 = generate_simhash(text1)
    hash2 = generate_simhash(text2)
    distance = hamming_distance(hash1, hash2)
    print(f"  ✓ SimHash distance: {distance} bits (similar articles)")
    
    # Test sentiment
    sentiment = analyze_sentiment("The stock price surged to new highs, beating expectations")
    assert "polarity" in sentiment
    assert -1.0 <= sentiment["polarity"] <= 1.0
    print(f"  ✓ Sentiment analysis: polarity={sentiment['polarity']:.2f}")
    
    # Test topics
    topics = classify_topics(
        text="Apple reported strong earnings, beating EPS estimates",
        title="Apple Earnings Beat"
    )
    assert "earnings" in topics
    print(f"  ✓ Topic classification: {topics}")


def test_gold_pipeline():
    """Test Gold pipeline query functions."""
    from src.ingestion.gold_features_pipeline import query_features
    import pandas as pd
    
    # Just test that the function exists and returns a DataFrame
    df = query_features(ticker="AAPL", start_date="2025-10-01", end_date="2025-10-31")
    assert isinstance(df, pd.DataFrame)
    print(f"  ✓ Query features function works (returned {len(df)} rows)")


def test_news_service():
    """Test NewsService class."""
    from src.api.services.news_service import NewsService
    
    service = NewsService()
    
    # Test that methods exist
    assert hasattr(service, "get_feed")
    assert hasattr(service, "get_daily_features")
    assert hasattr(service, "get_tickers_for_date")
    assert hasattr(service, "get_stats")
    
    print(f"  ✓ NewsService initialized")
    print(f"  ✓ All service methods present")


def test_orchestrator():
    """Test orchestrator script."""
    from scripts.news_orchestrator import (
        run_bronze_ingestion, run_silver_processing, run_gold_features
    )
    
    # Just verify functions exist (don't run them)
    assert callable(run_bronze_ingestion)
    assert callable(run_silver_processing)
    assert callable(run_gold_features)
    
    print(f"  ✓ Orchestrator functions available")


def test_dependencies():
    """Test that required dependencies are installed."""
    required_packages = [
        "pyarrow",
        "pandas",
        "duckdb",
        "feedparser",
        "requests",
        "bs4",  # beautifulsoup4
    ]
    
    optional_packages = [
        "langdetect",
        "vaderSentiment",
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✓ Required: {package}")
        except ImportError:
            raise ImportError(f"Required package missing: {package}")
    
    for package in optional_packages:
        try:
            __import__(package)
            print(f"  ✓ Optional: {package}")
        except ImportError:
            print(f"  ⚠ Optional package missing: {package} (will use fallback)")


def test_data_directories():
    """Test that data directories can be created."""
    from pathlib import Path
    
    base_dir = Path("data/news")
    
    dirs_to_check = [
        base_dir / "bronze",
        base_dir / "silver",
        base_dir / "gold/features_daily",
        base_dir / "gold/events",
        base_dir / "gold/embeddings",
    ]
    
    for dir_path in dirs_to_check:
        dir_path.mkdir(parents=True, exist_ok=True)
        assert dir_path.exists()
        print(f"  ✓ Directory exists: {dir_path}")


def test_duckdb_queries():
    """Test DuckDB can query Parquet files."""
    import duckdb
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    from pathlib import Path
    
    # Create test data
    test_dir = Path("data/news/test")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    test_data = {
        "id": ["test1", "test2"],
        "title": ["Test Article 1", "Test Article 2"],
        "ticker": ["AAPL", "MSFT"]
    }
    
    df = pd.DataFrame(test_data)
    table = pa.Table.from_pandas(df)
    
    test_file = test_dir / "test.parquet"
    pq.write_table(table, test_file)
    
    # Query with DuckDB
    conn = duckdb.connect(":memory:")
    result = conn.execute(f"SELECT * FROM read_parquet('{test_file}')").df()
    
    assert len(result) == 2
    assert "AAPL" in result["ticker"].values
    
    print(f"  ✓ DuckDB query successful ({len(result)} rows)")
    
    # Cleanup
    test_file.unlink()
    test_dir.rmdir()


# =======================
# Main
# =======================

def main():
    """Run all validation tests."""
    validator = NewsInfrastructureValidator()
    
    print(f"\n{'#'*60}")
    print(f"# NEWS INFRASTRUCTURE VALIDATION")
    print(f"{'#'*60}")
    
    # Run tests
    validator.test("Module Imports", test_imports)
    validator.test("Schema Validation", test_schemas)
    validator.test("Bronze Pipeline Functions", test_bronze_pipeline)
    validator.test("Silver Pipeline Functions", test_silver_pipeline)
    validator.test("Gold Pipeline Functions", test_gold_pipeline)
    validator.test("News Service", test_news_service)
    validator.test("Orchestrator", test_orchestrator)
    validator.test("Dependencies", test_dependencies)
    validator.test("Data Directories", test_data_directories)
    validator.test("DuckDB Queries", test_duckdb_queries)
    
    # Print summary
    validator.print_summary()
    
    # Exit with status code
    if validator.failed > 0:
        print(f"\n⚠️  Some tests failed. Please check errors above.")
        sys.exit(1)
    else:
        print(f"\n✅ All tests passed! Infrastructure is ready.")
        print(f"\nNext steps:")
        print(f"  1. Run your first pipeline: python scripts/news_orchestrator.py --today")
        print(f"  2. Check data: ls -lh data/news/silver/dt=2025-10-30/")
        print(f"  3. Query with DuckDB: See docs/NEWS_QUICKSTART.md")
        sys.exit(0)


if __name__ == "__main__":
    main()
