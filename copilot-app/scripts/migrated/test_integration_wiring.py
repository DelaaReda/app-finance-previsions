#!/usr/bin/env python3
"""
Integration test: Validate React ↔ Backend ↔ Agents ↔ Data wiring
Tests all 5 pillars according to VISION.md
"""

import sys
import requests
from pathlib import Path
from typing import Dict, Any

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

BASE_URL = "http://127.0.0.1:8000/api"

def test_endpoint(name: str, url: str, expected_keys: list[str] = None) -> bool:
    """Test a single API endpoint."""
    print(f"\n{BLUE}Testing:{RESET} {name}")
    print(f"  URL: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            print(f"  {RED}✗ FAIL{RESET} - Status: {response.status_code}")
            return False
        
        data = response.json()
        
        if not data.get('ok'):
            error = data.get('error', 'Unknown error')
            print(f"  {RED}✗ FAIL{RESET} - Error: {error}")
            return False
        
        result = data.get('data', {})
        
        if expected_keys:
            missing = [k for k in expected_keys if k not in result]
            if missing:
                print(f"  {YELLOW}⚠ WARNING{RESET} - Missing keys: {missing}")
        
        print(f"  {GREEN}✓ PASS{RESET}")
        if isinstance(result, dict):
            print(f"  Response keys: {list(result.keys())}")
        elif isinstance(result, list):
            print(f"  Response: {len(result)} items")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"  {RED}✗ FAIL{RESET} - Cannot connect to server")
        print(f"  {YELLOW}→ Start server with: python -m src.api.main{RESET}")
        return False
    except Exception as e:
        print(f"  {RED}✗ FAIL{RESET} - {type(e).__name__}: {e}")
        return False

def check_data_files() -> Dict[str, bool]:
    """Check existence of key data files."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}DATA FILES CHECK{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    checks = {
        "Features - Prices": Path("data/features/table=prices_features_daily"),
        "Features - Macro": Path("data/features/table=macro_snapshot_daily"),
        "Features - News": Path("data/features/table=news_features_daily"),
        "Forecasts": Path("data/forecast"),
        "Macro Forecast": Path("data/macro/forecast"),
        "Raw News": Path("data/news"),
    }
    
    results = {}
    for name, path in checks.items():
        exists = path.exists()
        symbol = f"{GREEN}✓{RESET}" if exists else f"{RED}✗{RESET}"
        print(f"  {symbol} {name:30} {path}")
        results[name] = exists
    
    return results

def main():
    """Run integration tests."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}INTEGRATION TEST: React ↔ Backend ↔ Agents ↔ Data{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    # Check data files
    data_checks = check_data_files()
    
    # Test API endpoints
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}API ENDPOINTS TEST{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    tests = [
        ("Health Check", f"{BASE_URL}/health", ["status", "timestamp"]),
        ("Data Freshness", f"{BASE_URL}/freshness", None),
        
        # Pillar 1: Macro
        ("Macro - Series", f"{BASE_URL}/macro/series?limit=10", None),
        ("Macro - Snapshot", f"{BASE_URL}/macro/snapshot", None),
        ("Macro - Indicators", f"{BASE_URL}/macro/indicators", ["cpi_yoy", "vix"]),
        
        # Pillar 2: Stocks
        ("Stocks - Universe", f"{BASE_URL}/stocks/universe", ["tickers", "count"]),
        ("Stocks - Prices (AAPL)", f"{BASE_URL}/stocks/prices?ticker=AAPL&downsample=100", ["ticker", "points"]),
        ("Stocks - Detail (AAPL)", f"{BASE_URL}/stocks/AAPL", ["ticker", "last_price"]),
        
        # Pillar 3: News
        ("News - Feed", f"{BASE_URL}/news/feed?limit=10", ["rows", "count"]),
        ("News - Sentiment", f"{BASE_URL}/news/sentiment", ["sentiment"]),
        
        # Pillar 4: Copilot (placeholder)
        ("Copilot - History", f"{BASE_URL}/copilot/history?limit=5", ["conversations"]),
        
        # Pillar 5: Brief
        ("Brief - Weekly", f"{BASE_URL}/brief/weekly", ["title"]),
        ("Brief - Daily", f"{BASE_URL}/brief/daily", ["title"]),
        
        # Signals
        ("Signals - Top", f"{BASE_URL}/signals/top", ["signals", "risks"]),
        
        # Existing
        ("Dashboard - KPIs", f"{BASE_URL}/dashboard/kpis", None),
        ("Forecasts", f"{BASE_URL}/forecasts?limit=5", None),
    ]
    
    results = []
    for name, url, keys in tests:
        passed = test_endpoint(name, url, keys)
        results.append((name, passed))
    
    # Summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}SUMMARY{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    print(f"\nData Files:")
    data_passed = sum(1 for v in data_checks.values() if v)
    data_total = len(data_checks)
    print(f"  {GREEN}{data_passed}{RESET}/{data_total} present")
    
    print(f"\nAPI Endpoints:")
    print(f"  {GREEN}{passed}{RESET}/{total} passed")
    
    if data_passed < data_total:
        print(f"\n{YELLOW}⚠ Missing data files. Run materialize:{RESET}")
        print(f"  python -m src.research.materialize")
    
    if passed < total:
        print(f"\n{RED}✗ Some tests failed{RESET}")
        sys.exit(1)
    else:
        print(f"\n{GREEN}✓ All tests passed!{RESET}")
        sys.exit(0)

if __name__ == "__main__":
    main()
