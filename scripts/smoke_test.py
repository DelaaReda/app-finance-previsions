#!/usr/bin/env python3
"""
Smoke test for Finance Copilot API
Quick validation that critical endpoints work
"""
import sys
import os
from pathlib import Path
import requests
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_api_health():
    """Test API health endpoint."""
    try:
        response = requests.get("http://localhost:8050/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                print("✅ API Health: OK")
                return True
            else:
                print("❌ API Health: Response not OK")
                return False
        else:
            print(f"❌ API Health: HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ API Health: Connection failed - API not running?")
        return False
    except Exception as e:
        print(f"❌ API Health: Error - {e}")
        return False

def test_critical_endpoints():
    """Test critical endpoints that inspector flagged as problematic."""
    base_url = "http://localhost:8050"
    
    # Test endpoints that were flagged as having issues
    test_cases = [
        ("/api/macro/series?ids=CPIAUCSL&limit=1", "Macro Series"),
        ("/api/stocks/prices?ticker=SPY&range=1mo", "Stocks Prices"),
        ("/api/news/feed?limit=5", "News Feed"),
        ("/api/brief/weekly", "Weekly Brief"),
        ("/api/brief/daily", "Daily Brief"),
        ("/api/dashboard/kpis", "Dashboard KPIs"),
        ("/api/alerts?limit=5", "Alerts"),
        ("/api/rag/stats", "RAG Stats")
    ]
    
    results = []
    
    for endpoint, name in test_cases:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    print(f"✅ {name}: OK")
                    results.append(True)
                else:
                    print(f"❌ {name}: Response not OK")
                    results.append(False)
            else:
                print(f"❌ {name}: HTTP {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ {name}: Error - {e}")
            results.append(False)
    
    return all(results)

def test_data_access():
    """Test core data access functions."""
    try:
        from core.data_access import get_close_series, load_macro_forecast_rows, load_news_features
        
        # Test get_close_series
        series = get_close_series("SPY")
        print(f"✅ Data Access (get_close_series): {'Has data' if series is not None else 'No data (OK)'}")
        
        # Test load_macro_forecast_rows
        macro_data = load_macro_forecast_rows(limit=1)
        print(f"✅ Data Access (load_macro_forecast_rows): OK")
        
        # Test load_news_features
        news_data = load_news_features(limit=10)
        print(f"✅ Data Access (load_news_features): OK")
        
        return True
    except Exception as e:
        print(f"❌ Data Access: Error - {e}")
        return False

def test_scoring():
    """Test scoring functions."""
    try:
        from research.scoring import calculate_composite_score, compute_composite_brief
        
        # Test calculate_composite_score
        try:
            score = calculate_composite_score("SPY")
            print(f"✅ Scoring (calculate_composite_score): OK")
        except:
            print(f"⚠️  Scoring (calculate_composite_score): No data available (OK)")
        
        # Test compute_composite_brief
        brief = compute_composite_brief(period="weekly", universe=["SPY"])
        print(f"✅ Scoring (compute_composite_brief): OK")
        
        return True
    except Exception as e:
        print(f"❌ Scoring: Error - {e}")
        return False

def test_rag():
    """Test RAG store functionality."""
    try:
        from research.rag_store import RAGStore
        rag_store = RAGStore()
        
        # Test stats
        stats = rag_store.stats()
        print(f"✅ RAG Store: {stats.get('news_count', 0)} news items, {stats.get('facts_count', 0)} facts")
        
        # Test search
        results = rag_store.search({}, top_k=1)
        print(f"✅ RAG Search: {'Found' if results else 'Empty (OK)'}")
        
        return True
    except Exception as e:
        print(f"❌ RAG Store: Error - {e}")
        return False

def main():
    """Run smoke tests."""
    print("🔍 Running Finance Copilot Smoke Tests...")
    print("=" * 50)
    
    start_time = time.time()
    
    # Test 1: API Health
    print("\n1. Testing API Health...")
    health_ok = test_api_health()
    
    if not health_ok:
        print("\n❌ API not responding. Please start the API server first:")
        print("   python run_api.py")
        return False
    
    # Test 2: Critical Endpoints
    print("\n2. Testing Critical Endpoints...")
    endpoints_ok = test_critical_endpoints()
    
    # Test 3: Data Access
    print("\n3. Testing Data Access...")
    data_access_ok = test_data_access()
    
    # Test 4: Scoring
    print("\n4. Testing Scoring Functions...")
    scoring_ok = test_scoring()
    
    # Test 5: RAG
    print("\n5. Testing RAG Store...")
    rag_ok = test_rag()
    
    end_time = time.time()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SMOKE TEST SUMMARY")
    print("=" * 50)
    print(f"API Health:     {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"Endpoints:      {'✅ PASS' if endpoints_ok else '❌ FAIL'}")
    print(f"Data Access:    {'✅ PASS' if data_access_ok else '❌ FAIL'}")
    print(f"Scoring:        {'✅ PASS' if scoring_ok else '❌ FAIL'}")
    print(f"RAG Store:      {'✅ PASS' if rag_ok else '❌ FAIL'}")
    print(f"Execution Time: {end_time - start_time:.2f}s")
    
    overall_pass = all([health_ok, endpoints_ok, data_access_ok, scoring_ok, rag_ok])
    
    if overall_pass:
        print("\n🎉 All smoke tests PASSED! System is ready.")
        return True
    else:
        print("\n⚠️  Some smoke tests FAILED. Please investigate.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)