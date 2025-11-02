#!/usr/bin/env python3
"""
Test script pour vérifier les interactions UI et détecter les erreurs
"""
import requests
import json
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Base URLs
API_BASE = "http://localhost:8050"
FRONTEND_BASE = "http://localhost:5173"

class UIInteractionTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.errors_found = []
    
    def test_api_health(self) -> bool:
        """Test API health endpoint"""
        try:
            response = self.session.get(f"{API_BASE}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    print("✅ API Health: OK")
                    return True
                else:
                    print(f"❌ API Health: Response not OK - {data}")
                    return False
            else:
                print(f"❌ API Health: HTTP {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
        except Exception as e:
            print(f"❌ API Health: Error - {e}")
            return False
    
    def test_api_endpoint(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
        """Test a specific API endpoint"""
        try:
            url = f"{API_BASE}{endpoint}"
            
            if method.upper() == "GET":
                response = self.session.get(url, timeout=10)
            elif method.upper() == "POST" and data:
                response = self.session.post(url, json=data, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            status = response.status_code
            try:
                json_data = response.json()
                return {
                    "status": status,
                    "ok": response.ok,
                    "data": json_data,
                    "error": None
                }
            except:
                # If not JSON, it's likely an HTML error page
                return {
                    "status": status,
                    "ok": False,
                    "data": None,
                    "error": f"Non-JSON response: {response.text[:200]}..."
                }
        except Exception as e:
            return {
                "status": None,
                "ok": False,
                "data": None,
                "error": f"Exception: {e}"
            }
    
    def comprehensive_api_test(self) -> Dict[str, bool]:
        """Test all critical API endpoints"""
        endpoints_to_test = [
            ("/health", "GET"),
            ("/api/macro/series?ids=CPIAUCSL&limit=1", "GET"),
            ("/api/stocks/prices?ticker=SPY&range=1mo", "GET"),
            ("/api/news/feed?limit=5", "GET"),
            ("/api/brief/daily", "GET"),
            ("/api/brief/weekly", "GET"),
            ("/api/dashboard/kpis", "GET"),
            ("/api/forecasts", "GET"),
            ("/api/copilot/ask", "POST", {"question": "test", "scope": {}}),
            ("/api/rag/stats", "GET")
        ]
        
        results = {}
        
        for test in endpoints_to_test:
            if len(test) == 2:
                endpoint, method = test
                data = None
            elif len(test) == 3:
                endpoint, method, data = test
            else:
                continue
            
            print(f"Testing {method} {endpoint}...")
            result = self.test_api_endpoint(endpoint, method, data)
            
            key = f"{method} {endpoint}"
            if result["ok"]:
                print(f"  ✅ {key}: Success (Status: {result['status']})")
                results[key] = True
            else:
                print(f"  ❌ {key}: Failed")
                print(f"     Status: {result['status']}")
                print(f"     Error: {result['error']}")
                results[key] = False
                
                # Save error details
                self.errors_found.append({
                    "endpoint": endpoint,
                    "method": method,
                    "status": result["status"],
                    "error": result["error"]
                })
        
        return results
    
    def frontend_page_test(self) -> Dict[str, bool]:
        """Test frontend page loading"""
        pages_to_test = [
            "/",
            "/brief",
            "/macro",
            "/stocks", 
            "/news",
            "/copilot",
            "/forecasts",
            "/backtests",
            "/judge"
        ]
        
        results = {}
        
        for page in pages_to_test:
            try:
                response = self.session.get(f"{FRONTEND_BASE}{page}", timeout=10)
                if response.status_code == 200:
                    print(f"✅ Frontend page {page}: OK")
                    results[page] = True
                else:
                    print(f"❌ Frontend page {page}: HTTP {response.status_code}")
                    results[page] = False
                    self.errors_found.append({
                        "page": page,
                        "status": response.status_code,
                        "error": f"HTTP {response.status_code}"
                    })
            except Exception as e:
                print(f"❌ Frontend page {page}: Error - {e}")
                results[page] = False
                self.errors_found.append({
                    "page": page,
                    "status": None,
                    "error": str(e)
                })
        
        return results
    
    def run_all_tests(self):
        """Run all tests and report results"""
        print("🚀 Running UI Interaction Tests...")
        print("=" * 60)
        
        # Test API health first
        print("\n1. Testing API Health...")
        api_healthy = self.test_api_health()
        
        if not api_healthy:
            print("\n⚠️  API is not healthy. Please start the backend first.")
            print("   Command: python run_api.py")
            return False
        
        # Test API endpoints
        print("\n2. Testing API Endpoints...")
        api_results = self.comprehensive_api_test()
        
        # Test frontend pages
        print("\n3. Testing Frontend Pages...")
        frontend_results = self.frontend_page_test()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        api_success = sum(1 for v in api_results.values() if v)
        api_total = len(api_results)
        print(f"API Endpoints: {api_success}/{api_total} successful")
        
        frontend_success = sum(1 for v in frontend_results.values() if v)
        frontend_total = len(frontend_results)
        print(f"Frontend Pages: {frontend_success}/{frontend_total} successful")
        
        print(f"\nTotal Errors Found: {len(self.errors_found)}")
        
        # Detailed errors
        if self.errors_found:
            print("\n❌ DETAILED ERRORS:")
            for error in self.errors_found:
                if "endpoint" in error:
                    print(f"  API: {error['method']} {error['endpoint']} - {error['error']}")
                elif "page" in error:
                    print(f"  Frontend: {error['page']} - {error['error']}")
        
        overall_success = (api_success == api_total) and (frontend_success == frontend_total)
        
        print(f"\n🎯 Overall Status: {'✅ SUCCESS' if overall_success else '❌ FAILED'}")
        
        # Provide specific troubleshooting for the JSON error
        if len(self.errors_found) > 0:
            print(f"\n🔧 SUGGESTED FIXES:")
            print("  - Check if backend is running on http://localhost:8050")
            print("  - Verify that API routes return proper JSON (not HTML error pages)")
            print("  - Check backend logs for errors")
            print("  - Ensure .env variables are properly configured")
            print("  - Verify database connections if applicable")
        
        return overall_success
    
    def run_smoke_test(self):
        """Quick test for critical functionality"""
        print("💨 Running Smoke Test...")
        
        # Test the critical endpoints that were mentioned in the error
        critical_tests = [
            "/api/dashboard/kpis",
            "/api/brief/daily",
            "/api/forecasts"
        ]
        
        for endpoint in critical_tests:
            result = self.test_api_endpoint(endpoint, "GET")
            if not result["ok"] or result["data"] is None:
                print(f"❌ Critical endpoint {endpoint} failed: {result['error']}")
                return False
            else:
                print(f"✅ Critical endpoint {endpoint}: OK")
        
        print("✅ Smoke test passed!")
        return True

def main():
    tester = UIInteractionTester()
    
    # Run smoke test first
    smoke_success = tester.run_smoke_test()
    
    if smoke_success:
        print("\n" + "="*60)
        print("All critical endpoints are working!")
        print("Now running comprehensive tests...")
        print("="*60)
        
        # Run full test suite
        tester.run_all_tests()
    else:
        print("\n❌ Smoke test failed - critical endpoints not working")
        print("Please fix the backend before running full tests")
        
        # Show errors found in smoke test
        for error in tester.errors_found:
            print(f"  Error: {error}")

if __name__ == "__main__":
    main()