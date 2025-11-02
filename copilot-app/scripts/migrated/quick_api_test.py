#!/usr/bin/env python3
"""
Quick API Test - Vérifie rapidement que les endpoints critiques fonctionnent
"""
import sys
import requests
import json
from datetime import datetime

def test_endpoint(url, name, expected_keys=None):
    """Test a single API endpoint."""
    try:
        print(f"📡 Testing {name}...")
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("ok"):
                print(f"✅ {name}: SUCCESS")
                
                if expected_keys:
                    for key in expected_keys:
                        if key in data.get("data", {}):
                            print(f"   ↳ Found key: {key}")
                        else:
                            print(f"   ↳ Missing key: {key}")
                
                return True
            else:
                print(f"❌ {name}: API returned ok=False")
                print(f"   Error: {data.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ {name}: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ {name}: Connection failed - Is API running?")
        return False
    except Exception as e:
        print(f"❌ {name}: Error - {e}")
        return False

def main():
    """Run quick API tests."""
    print("🚀 Quick API Test - Finance Copilot")
    print("=" * 40)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    base_url = "http://localhost:8050"
    
    # Test endpoints
    endpoints = [
        (f"{base_url}/health", "Health Check", ["status"]),
        (f"{base_url}/api/dashboard/kpis", "Dashboard KPIs", ["last_forecast_dt", "forecasts_count"]),
        (f"{base_url}/api/brief/weekly", "Weekly Brief", ["top_signals", "top_risks"]),
        (f"{base_url}/api/brief/daily", "Daily Brief", ["top_signals", "top_risks"]),
        (f"{base_url}/api/news/feed", "News Feed", ["articles", "count"]),
        (f"{base_url}/api/stocks/universe", "Stock Universe", ["tickers", "count"]),
        (f"{base_url}/api/rag/stats", "RAG Stats", ["total", "news_count"]),
    ]
    
    results = []
    
    for url, name, expected_keys in endpoints:
        result = test_endpoint(url, name, expected_keys)
        results.append((name, result))
        print()
    
    # Summary
    print("=" * 40)
    print("📊 SUMMARY")
    print("=" * 40)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Success Rate: {passed/len(results)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 All API endpoints are working!")
        print("🔗 Visit http://localhost:5173 to use the UI")
        return True
    else:
        print(f"\n⚠️  {failed} endpoint(s) failed")
        print("🔧 Check the errors above and fix the issues")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)