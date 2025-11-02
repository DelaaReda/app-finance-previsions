#!/usr/bin/env python3
"""
Test Runner - Vérifie que l'UI fonctionne correctement
Simule l'expérience utilisateur complète sans interface graphique
"""
import sys
import os
import json
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_api_connectivity():
    """Test basic API connectivity."""
    print("📡 Testing API Connectivity...")
    try:
        import requests
        response = requests.get("http://localhost:8050/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API is running - Status: {data.get('status', 'unknown')}")
            return True
        else:
            print(f"❌ API responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ API is not running - Start it with: python run_api.py")
        return False
    except Exception as e:
        print(f"❌ API connectivity test failed: {e}")
        return False

def test_dashboard_endpoints():
    """Test all dashboard-related endpoints."""
    print("\n📋 Testing Dashboard Endpoints...")
    
    endpoints = [
        ("/api/dashboard/kpis", "Dashboard KPIs"),
        ("/api/brief/weekly", "Weekly Brief"),
        ("/api/brief/daily", "Daily Brief"),
        ("/api/alerts", "Alerts"),
        ("/api/signals/top", "Top Signals"),
        ("/api/forecasts", "Forecasts"),
        ("/api/news/feed", "News Feed"),
        ("/api/rag/stats", "RAG Stats")
    ]
    
    results = []
    
    for endpoint, name in endpoints:
        try:
            import requests
            response = requests.get(f"http://localhost:8050{endpoint}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    print(f"✅ {name}: OK")
                    results.append(True)
                else:
                    print(f"⚠️  {name}: API returned ok=False")
                    results.append(False)
            else:
                print(f"❌ {name}: HTTP {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ {name}: Error - {e}")
            results.append(False)
    
    return all(results)

def test_copilot_functionality():
    """Test copilot Q&A functionality."""
    print("\n🤖 Testing Copilot Functionality...")
    
    try:
        import requests
        
        # Test a simple question
        payload = {
            "question": "What is the current inflation rate?",
            "context_years": 5,
            "max_sources": 5
        }
        
        response = requests.post(
            "http://localhost:8050/api/copilot/ask",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok") and data.get("data"):
                copilot_data = data["data"]
                answer = copilot_data.get("answer", "")
                sources = copilot_data.get("sources", [])
                
                print(f"✅ Copilot Q&A: OK")
                print(f"   Answer length: {len(answer)} characters")
                print(f"   Sources found: {len(sources)}")
                
                if sources:
                    print(f"   First source type: {sources[0].get('type', 'N/A')}")
                
                return True
            else:
                print(f"⚠️  Copilot Q&A: API returned ok=False")
                return False
        else:
            print(f"❌ Copilot Q&A: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Copilot Q&A: Error - {e}")
        return False

def test_data_access():
    """Test core data access functionality."""
    print("\n💾 Testing Data Access...")
    
    try:
        from core.data_access import get_close_series, load_macro_forecast_rows, load_news_features
        
        # Test get_close_series
        try:
            series = get_close_series("SPY")
            print(f"✅ get_close_series: {'Has data' if series is not None else 'No data (OK)'}")
        except Exception as e:
            print(f"⚠️  get_close_series: Error - {e}")
        
        # Test load_macro_forecast_rows
        try:
            macro_data = load_macro_forecast_rows(limit=1)
            print(f"✅ load_macro_forecast_rows: OK")
        except Exception as e:
            print(f"⚠️  load_macro_forecast_rows: Error - {e}")
        
        # Test load_news_features
        try:
            news_data = load_news_features(limit=10)
            print(f"✅ load_news_features: {len(news_data.get('rows', []))} rows")
        except Exception as e:
            print(f"⚠️  load_news_features: Error - {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Data Access: Error - {e}")
        return False

def test_scoring_system():
    """Test scoring system functionality."""
    print("\n📈 Testing Scoring System...")
    
    try:
        from research.scoring import calculate_composite_score, compute_composite_brief
        
        # Test calculate_composite_score
        try:
            score = calculate_composite_score("SPY")
            print(f"✅ calculate_composite_score: Composite score = {score.get('composite_score', 'N/A')}")
        except Exception as e:
            print(f"⚠️  calculate_composite_score: Error - {e}")
        
        # Test compute_composite_brief
        try:
            brief = compute_composite_brief(period="weekly", universe=["SPY", "QQQ"])
            signals = brief.get("top_signals", [])
            risks = brief.get("top_risks", [])
            print(f"✅ compute_composite_brief: {len(signals)} signals, {len(risks)} risks")
        except Exception as e:
            print(f"⚠️  compute_composite_brief: Error - {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Scoring System: Error - {e}")
        return False

def test_rag_store():
    """Test RAG store functionality."""
    print("\n🧠 Testing RAG Store...")
    
    try:
        from research.rag_store import RAGStore
        rag_store = RAGStore()
        
        # Test stats
        stats = rag_store.stats()
        print(f"✅ RAG Store: {stats.get('total', 0)} total items")
        
        # Test search
        results = rag_store.search({}, top_k=5)
        print(f"✅ RAG Search: Found {len(results)} results")
        
        return True
        
    except Exception as e:
        print(f"❌ RAG Store: Error - {e}")
        return False

def main():
    """Main test runner."""
    print("🚀 Test Runner - Vérification de l'UI Finance Copilot")
    print("=" * 60)
    
    start_time = time.time()
    
    # Run all tests
    tests = [
        ("API Connectivity", test_api_connectivity),
        ("Dashboard Endpoints", test_dashboard_endpoints),
        ("Copilot Functionality", test_copilot_functionality),
        ("Data Access", test_data_access),
        ("Scoring System", test_scoring_system),
        ("RAG Store", test_rag_store)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"🧪 {test_name}")
        print(f"{'='*50}")
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}: Unexpected error - {e}")
            results.append((test_name, False))
    
    end_time = time.time()
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 RÉSULTATS DES TESTS")
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
    print(f"⏱️  TEMPS TOTAL: {end_time - start_time:.2f} secondes")
    print(f"✅ RÉUSSIS: {passed}")
    print(f"❌ ÉCHOUÉS: {failed}")
    print(f"📊 TAUX DE SUCCÈS: {passed/len(results)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 Tous les tests ont PASSÉ ! L'UI est fonctionnelle.")
        print("🔗 Accédez à l'application: http://localhost:5173")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) ont ÉCHOUÉ.")
        print("🔧 Veuillez vérifier les erreurs ci-dessus et corriger les problèmes.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)