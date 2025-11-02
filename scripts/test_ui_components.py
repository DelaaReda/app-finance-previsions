#!/usr/bin/env python3
"""
UI Component Test - Teste les composants UI avec le backend
Simule l'interaction utilisateur complète
"""
import sys
import requests
import json
from datetime import datetime
from typing import Dict, Any, List

def test_ui_component(component_name: str, endpoint: str, expected_fields: List[str] = None) -> Dict[str, Any]:
    """Test a UI component by calling its API endpoint."""
    print(f"🧩 Testing UI Component: {component_name}")
    print(f"   Endpoint: {endpoint}")
    
    try:
        # Call the API endpoint
        response = requests.get(endpoint, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("ok"):
                result_data = data.get("data", {})
                
                print(f"   ✅ SUCCESS - Status: 200 OK")
                print(f"   📦 Data keys: {list(result_data.keys())}")
                
                # Check expected fields
                if expected_fields:
                    missing_fields = []
                    present_fields = []
                    
                    for field in expected_fields:
                        if field in result_data:
                            present_fields.append(field)
                        else:
                            missing_fields.append(field)
                    
                    if missing_fields:
                        print(f"   ⚠️  Missing fields: {missing_fields}")
                    if present_fields:
                        print(f"   ✅ Present fields: {present_fields}")
                
                # Show sample data
                if result_data:
                    print(f"   📝 Sample data:")
                    for key, value in list(result_data.items())[:3]:
                        if isinstance(value, (list, dict)):
                            print(f"      {key}: {type(value).__name__} ({len(value) if isinstance(value, list) else 'object'})")
                        else:
                            print(f"      {key}: {value}")
                
                return {
                    "success": True,
                    "component": component_name,
                    "data": result_data,
                    "status": response.status_code
                }
            else:
                print(f"   ❌ FAILED - API returned ok=False")
                print(f"   📛 Error: {data.get('error', 'Unknown error')}")
                return {
                    "success": False,
                    "component": component_name,
                    "error": data.get("error", "Unknown error"),
                    "status": response.status_code
                }
        else:
            print(f"   ❌ FAILED - HTTP {response.status_code}")
            return {
                "success": False,
                "component": component_name,
                "error": f"HTTP {response.status_code}",
                "status": response.status_code
            }
            
    except requests.exceptions.ConnectionError:
        print(f"   ❌ FAILED - Connection error (API not running?)")
        return {
            "success": False,
            "component": component_name,
            "error": "Connection failed - API not running?",
            "status": "connection_error"
        }
    except Exception as e:
        print(f"   ❌ FAILED - Unexpected error: {e}")
        return {
            "success": False,
            "component": component_name,
            "error": str(e),
            "status": "exception"
        }

def test_dashboard_components():
    """Test all dashboard components."""
    print("📋 Testing Dashboard Components")
    print("=" * 50)
    
    base_url = "http://localhost:8050"
    
    # Dashboard components to test
    components = [
        {
            "name": "Dashboard KPIs",
            "endpoint": f"{base_url}/api/dashboard/kpis",
            "expected_fields": ["last_forecast_dt", "forecasts_count", "tickers"]
        },
        {
            "name": "Weekly Market Brief",
            "endpoint": f"{base_url}/api/brief/weekly",
            "expected_fields": ["top_signals", "top_risks", "picks"]
        },
        {
            "name": "Daily Market Brief",
            "endpoint": f"{base_url}/api/brief/daily",
            "expected_fields": ["top_signals", "top_risks", "market_overview"]
        },
        {
            "name": "Top Signals",
            "endpoint": f"{base_url}/api/signals/top",
            "expected_fields": ["signals", "risks"]
        },
        {
            "name": "News Feed",
            "endpoint": f"{base_url}/api/news/feed",
            "expected_fields": ["articles", "count"]
        },
        {
            "name": "Stocks Universe",
            "endpoint": f"{base_url}/api/stocks/universe",
            "expected_fields": ["tickers", "count"]
        },
        {
            "name": "Macro Overview",
            "endpoint": f"{base_url}/api/macro/overview",
            "expected_fields": ["indicators", "snapshot"]
        },
        {
            "name": "RAG Stats",
            "endpoint": f"{base_url}/api/rag/stats",
            "expected_fields": ["stats"]
        }
    ]
    
    results = []
    
    for component in components:
        result = test_ui_component(
            component["name"],
            component["endpoint"],
            component.get("expected_fields")
        )
        results.append(result)
        print()
    
    return results

def test_copilot_components():
    """Test copilot components."""
    print("🤖 Testing Copilot Components")
    print("=" * 50)
    
    base_url = "http://localhost:8050"
    
    # Test copilot ask endpoint
    copilot_result = test_ui_component(
        "Copilot Ask",
        f"{base_url}/api/copilot/ask",
        ["answer", "sources", "confidence"]
    )
    
    # Test copilot history endpoint
    history_result = test_ui_component(
        "Copilot History",
        f"{base_url}/api/copilot/history",
        ["conversations", "count"]
    )
    
    return [copilot_result, history_result]

def test_alert_components():
    """Test alert components."""
    print("🚨 Testing Alert Components")
    print("=" * 50)
    
    base_url = "http://localhost:8050"
    
    # Test alerts endpoint
    alerts_result = test_ui_component(
        "Market Alerts",
        f"{base_url}/api/alerts",
        ["alerts", "count", "total_available"]
    )
    
    return [alerts_result]

def main():
    """Run complete UI component tests."""
    print("🚀 UI Component Test Suite - Finance Copilot")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test all component categories
    all_results = []
    
    # Dashboard components
    dashboard_results = test_dashboard_components()
    all_results.extend(dashboard_results)
    print()
    
    # Copilot components
    copilot_results = test_copilot_components()
    all_results.extend(copilot_results)
    print()
    
    # Alert components
    alert_results = test_alert_components()
    all_results.extend(alert_results)
    print()
    
    # Summary
    print("=" * 60)
    print("📊 COMPONENT TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for result in all_results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"{status:<10} {result['component']}")
        if result["success"]:
            passed += 1
        else:
            failed += 1
            print(f"           Error: {result.get('error', 'Unknown error')}")
    
    print(f"\n{'=' * 60}")
    print(f"⏱️  TOTAL TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"✅ PASSED: {passed}")
    print(f"❌ FAILED: {failed}")
    print(f"📊 SUCCESS RATE: {passed/len(all_results)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 All UI components are working correctly!")
        print("🌐 Visit http://localhost:5173 to use the application")
        return True
    else:
        print(f"\n⚠️  {failed} component(s) failed")
        print("🔧 Check the errors above and fix the issues")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)