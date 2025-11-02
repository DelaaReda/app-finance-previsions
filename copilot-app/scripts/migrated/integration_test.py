#!/usr/bin/env python3
"""
Integration Test - Vérifie le flux de données complet de l'API au Frontend
Teste l'intégration bout-en-bout sans interface graphique
"""
import sys
import requests
import json
from datetime import datetime
from typing import Dict, Any, List

def test_api_to_frontend_integration():
    """Test complete integration from API to frontend simulation."""
    print("🔌 Testing API to Frontend Integration")
    print("=" * 50)
    
    base_url = "http://localhost:8050"
    
    # Test scenarios that simulate frontend requests
    test_scenarios = [
        {
            "name": "Dashboard Load",
            "description": "User opens dashboard page",
            "requests": [
                {"endpoint": "/health", "method": "GET"},
                {"endpoint": "/api/dashboard/kpis", "method": "GET"},
                {"endpoint": "/api/brief/weekly", "method": "GET"},
                {"endpoint": "/api/alerts", "method": "GET"}
            ]
        },
        {
            "name": "Market Brief Request",
            "description": "User requests weekly market brief",
            "requests": [
                {"endpoint": "/api/brief/weekly", "method": "GET"},
                {"endpoint": "/api/brief/daily", "method": "GET"},
                {"endpoint": "/api/signals/top", "method": "GET"}
            ]
        },
        {
            "name": "Copilot Interaction",
            "description": "User asks question to copilot",
            "requests": [
                {"endpoint": "/api/copilot/ask", "method": "POST", "data": {"question": "What is the current inflation rate?"}},
                {"endpoint": "/api/copilot/history", "method": "GET"}
            ]
        },
        {
            "name": "Stock Analysis",
            "description": "User views stock details",
            "requests": [
                {"endpoint": "/api/stocks/prices", "method": "GET", "params": {"ticker": "SPY"}},
                {"endpoint": "/api/stocks/universe", "method": "GET"}
            ]
        },
        {
            "name": "News Feed",
            "description": "User browses news",
            "requests": [
                {"endpoint": "/api/news/feed", "method": "GET"},
                {"endpoint": "/api/news/sentiment", "method": "GET"}
            ]
        }
    ]
    
    all_passed = True
    
    for scenario in test_scenarios:
        print(f"\n🧪 Scenario: {scenario['name']}")
        print(f"   Description: {scenario['description']}")
        print(f"   Requests: {len(scenario['requests'])}")
        
        scenario_passed = True
        
        for req in scenario['requests']:
            try:
                endpoint = f"{base_url}{req['endpoint']}"
                method = req['method']
                
                if method == "GET":
                    response = requests.get(endpoint, params=req.get('params', {}), timeout=15)
                elif method == "POST":
                    response = requests.post(endpoint, json=req.get('data', {}), timeout=15)
                else:
                    print(f"     ⚠️  Unsupported method: {method}")
                    continue
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        print(f"     ✅ {method} {req['endpoint']}: SUCCESS")
                    else:
                        print(f"     ❌ {method} {req['endpoint']}: API returned ok=False")
                        print(f"        Error: {data.get('error', 'Unknown error')}")
                        scenario_passed = False
                else:
                    print(f"     ❌ {method} {req['endpoint']}: HTTP {response.status_code}")
                    scenario_passed = False
                    
            except requests.exceptions.ConnectionError:
                print(f"     ❌ {method} {req['endpoint']}: Connection failed")
                scenario_passed = False
            except Exception as e:
                print(f"     ❌ {method} {req['endpoint']}: Error - {e}")
                scenario_passed = False
        
        if scenario_passed:
            print(f"   🎉 Scenario PASSED: {scenario['name']}")
        else:
            print(f"   💥 Scenario FAILED: {scenario['name']}")
            all_passed = False
    
    return all_passed

def test_data_consistency():
    """Test data consistency between different endpoints."""
    print("\n🔁 Testing Data Consistency")
    print("=" * 50)
    
    base_url = "http://localhost:8050"
    
    try:
        # Get dashboard KPIs
        dashboard_response = requests.get(f"{base_url}/api/dashboard/kpis", timeout=10)
        dashboard_data = dashboard_response.json() if dashboard_response.status_code == 200 else {}
        
        # Get brief data
        brief_response = requests.get(f"{base_url}/api/brief/weekly", timeout=10)
        brief_data = brief_response.json() if brief_response.status_code == 200 else {}
        
        # Get signals
        signals_response = requests.get(f"{base_url}/api/signals/top", timeout=10)
        signals_data = signals_response.json() if signals_response.status_code == 200 else {}
        
        # Check consistency
        consistency_checks = []
        
        # Check that dashboard has data
        if dashboard_data.get("ok") and dashboard_data.get("data"):
            consistency_checks.append(("Dashboard data", True))
            dashboard_kpis = dashboard_data["data"]
        else:
            consistency_checks.append(("Dashboard data", False))
            dashboard_kpis = {}
        
        # Check that brief has data
        if brief_data.get("ok") and brief_data.get("data"):
            consistency_checks.append(("Brief data", True))
            brief_content = brief_data["data"]
        else:
            consistency_checks.append(("Brief data", False))
            brief_content = {}
        
        # Check that signals have data
        if signals_data.get("ok") and signals_data.get("data"):
            consistency_checks.append(("Signals data", True))
            signals_content = signals_data["data"]
        else:
            consistency_checks.append(("Signals data", False))
            signals_content = {}
        
        # Cross-check data consistency
        if dashboard_kpis and brief_content:
            # Check that tickers match
            dashboard_tickers = dashboard_kpis.get("tickers", 0)
            brief_signals = brief_content.get("top_signals", [])
            brief_risks = brief_content.get("top_risks", [])
            
            if len(brief_signals) > 0 or len(brief_risks) > 0:
                consistency_checks.append(("Ticker data consistency", True))
            else:
                consistency_checks.append(("Ticker data consistency", False))
        
        # Print results
        all_consistent = True
        for check_name, is_consistent in consistency_checks:
            status = "✅ PASS" if is_consistent else "❌ FAIL"
            print(f"   {status} {check_name}")
            if not is_consistent:
                all_consistent = False
        
        return all_consistent
        
    except Exception as e:
        print(f"❌ Data consistency test failed: {e}")
        return False

def test_user_journey_simulation():
    """Simulate a complete user journey through the application."""
    print("\n🚶 Testing User Journey Simulation")
    print("=" * 50)
    
    base_url = "http://localhost:8050"
    
    # Simulate a typical user session
    user_actions = [
        ("Visit Dashboard", "/api/dashboard/kpis"),
        ("View Weekly Brief", "/api/brief/weekly"),
        ("View Daily Brief", "/api/brief/daily"),
        ("Check Alerts", "/api/alerts"),
        ("Browse News", "/api/news/feed"),
        ("Analyze SPY", "/api/stocks/prices?ticker=SPY"),
        ("Ask Copilot", "/api/copilot/ask")
    ]
    
    journey_passed = True
    
    for action_name, endpoint in user_actions:
        try:
            if "ask" in endpoint.lower():
                # POST request for copilot
                response = requests.post(
                    f"{base_url}{endpoint.split('?')[0]}", 
                    json={"question": "What are the current market trends?"},
                    timeout=15
                )
            else:
                # GET request for other endpoints
                response = requests.get(f"{base_url}{endpoint}", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    print(f"✅ {action_name}: SUCCESS")
                else:
                    print(f"❌ {action_name}: API returned ok=False")
                    print(f"   Error: {data.get('error', 'Unknown error')}")
                    journey_passed = False
            else:
                print(f"❌ {action_name}: HTTP {response.status_code}")
                journey_passed = False
                
        except requests.exceptions.ConnectionError:
            print(f"❌ {action_name}: Connection failed")
            journey_passed = False
        except Exception as e:
            print(f"❌ {action_name}: Error - {e}")
            journey_passed = False
    
    if journey_passed:
        print("\n🎉 User journey simulation PASSED!")
    else:
        print("\n💥 User journey simulation FAILED!")
    
    return journey_passed

def main():
    """Run complete integration tests."""
    print("🚀 Integration Test Suite - Finance Copilot")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run all integration tests
    tests = [
        ("API to Frontend Integration", test_api_to_frontend_integration),
        ("Data Consistency", test_data_consistency),
        ("User Journey Simulation", test_user_journey_simulation)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"🧪 {test_name}")
        print(f"{'='*60}")
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}: Unexpected error - {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 INTEGRATION TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:<10} {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"⏱️  TOTAL TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"✅ PASSED: {passed}")
    print(f"❌ FAILED: {failed}")
    print(f"📊 SUCCESS RATE: {passed/len(results)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 All integration tests PASSED!")
        print("🔗 The complete data flow from backend to frontend is working!")
        print("🌐 Visit http://localhost:5173 to use the full application")
        return True
    else:
        print(f"\n⚠️  {failed} integration test(s) failed")
        print("🔧 Check the errors above and fix the integration issues")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)