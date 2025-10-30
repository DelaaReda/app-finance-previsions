#!/usr/bin/env python3
"""
Quick smoke test for API v0.1 endpoints.
Tests all implemented endpoints without needing network access.
"""
import sys
import os
import time
import json
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Set test mode to avoid network calls
os.environ["AF_TEST_MODE"] = "1"

from fastapi.testclient import TestClient
from api.main_v2 import create_app

def test_endpoint(client: TestClient, method: str, path: str, **kwargs) -> Dict[str, Any]:
    """Test an endpoint and return results."""
    start = time.time()
    
    try:
        if method == "GET":
            response = client.get(path, **kwargs)
        elif method == "POST":
            response = client.post(path, **kwargs)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        elapsed = time.time() - start
        
        return {
            "path": path,
            "status": response.status_code,
            "elapsed_ms": round(elapsed * 1000, 1),
            "ok": response.status_code < 400,
            "body": response.json() if response.status_code < 500 else None
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "path": path,
            "status": 500,
            "elapsed_ms": round(elapsed * 1000, 1),
            "ok": False,
            "error": str(e)
        }


def main():
    print("=" * 70)
    print(" Finance Copilot API v0.1 - Smoke Tests")
    print("=" * 70)
    print()
    
    # Create test client
    app = create_app()
    client = TestClient(app)
    
    # Define tests
    tests = [
        # Health
        ("GET", "/api/health", {}),
        ("GET", "/api/freshness", {}),
        
        # Macro
        ("GET", "/api/macro/overview", {"params": {"range": "1y"}}),
        ("GET", "/api/macro/overview", {"params": {"range": "5y", "series": "UNRATE,CPIAUCSL"}}),
        ("GET", "/api/macro/snapshot", {}),
        ("GET", "/api/macro/indicators", {}),
        
        # Stocks
        ("GET", "/api/stocks/AAPL/overview", {"params": {"range": "1y", "features": "technicals"}}),
        ("GET", "/api/stocks/AAPL/overview", {"params": {"range": "6m", "features": "all", "downsample": "500"}}),
        ("GET", "/api/stocks/universe", {}),
        
        # News
        ("GET", "/api/news/feed", {"params": {"limit": "10", "since": "7d"}}),
        ("GET", "/api/news/feed", {"params": {"tickers": "AAPL,MSFT", "score_min": "0.5", "limit": "20"}}),
        ("GET", "/api/news/sentiment", {}),
    ]
    
    results = []
    passed = 0
    failed = 0
    
    for method, path, kwargs in tests:
        print(f"Testing: {method} {path}")
        result = test_endpoint(client, method, path, **kwargs)
        results.append(result)
        
        if result["ok"]:
            print(f"  ✓ {result['status']} in {result['elapsed_ms']}ms")
            passed += 1
        else:
            print(f"  ✗ {result['status']} in {result['elapsed_ms']}ms")
            if "error" in result:
                print(f"    Error: {result['error']}")
            failed += 1
        print()
    
    # Summary
    print("=" * 70)
    print(f" Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 70)
    print()
    
    # Performance summary
    elapsed_times = [r["elapsed_ms"] for r in results if r["ok"]]
    if elapsed_times:
        print("Performance:")
        print(f"  Average: {sum(elapsed_times) / len(elapsed_times):.1f}ms")
        print(f"  Min: {min(elapsed_times):.1f}ms")
        print(f"  Max: {max(elapsed_times):.1f}ms")
        print()
    
    # Detailed results for failures
    failures = [r for r in results if not r["ok"]]
    if failures:
        print("Failed tests:")
        for f in failures:
            print(f"  - {f['path']}: {f.get('error', 'Unknown error')}")
        print()
    
    # Trace check
    traced = sum(1 for r in results if r["ok"] and r.get("body", {}).get("data", {}).get("trace"))
    print(f"Traceability: {traced}/{passed} responses have TraceMetadata")
    print()
    
    # Exit code
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
