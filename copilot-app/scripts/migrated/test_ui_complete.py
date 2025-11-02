#!/usr/bin/env python3
"""
Test UI Complet - Simule l'expérience utilisateur entière
Teste tous les parcours de l'utilisateur sans interface graphique
"""
import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_api_health():
    """Test API health endpoint."""
    print("🔍 Testing API Health...")
    try:
        import requests
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
    except Exception as e:
        print(f"❌ API Health: Connection failed - {e}")
        return False

def test_dashboard_kpis():
    """Test dashboard KPIs endpoint."""
    print("\n📊 Testing Dashboard KPIs...")
    try:
        import requests
        response = requests.get("http://localhost:8050/api/dashboard/kpis", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok") and data.get("data"):
                dashboard_data = data["data"]
                print(f"✅ Dashboard KPIs: OK")
                print(f"   Last forecast: {dashboard_data.get('last_forecast_dt', 'N/A')}")
                print(f"   Forecasts count: {dashboard_data.get('forecasts_count', 0)}")
                print(f"   Tickers: {dashboard_data.get('tickers', 0)}")
                return True
            else:
                print("❌ Dashboard KPIs: Response not OK")
                return False
        else:
            print(f"❌ Dashboard KPIs: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Dashboard KPIs: Error - {e}")
        return False

def test_weekly_brief():
    """Test weekly market brief endpoint."""
    print("\n📅 Testing Weekly Market Brief...")
    try:
        import requests
        response = requests.get("http://localhost:8050/api/brief/weekly", timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok") and data.get("data"):
                brief_data = data["data"]
                signals = brief_data.get("top_signals", [])
                risks = brief_data.get("top_risks", [])
                print(f"✅ Weekly Brief: OK")
                print(f"   Signals found: {len(signals)}")
                print(f"   Risks found: {len(risks)}")
                if signals:
                    print(f"   Top signal: {signals[0].get('ticker', 'N/A')} - Score: {signals[0].get('composite_score', 'N/A')}")
                return True
            else:
                print("❌ Weekly Brief: Response not OK")
                return False
        else:
            print(f"❌ Weekly Brief: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Weekly Brief: Error - {e}")
        return False

def test_daily_brief():
    """Test daily market brief endpoint."""
    print("\n📆 Testing Daily Market Brief...")
    try:
        import requests
        response = requests.get("http://localhost:8050/api/brief/daily", timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok") and data.get("data"):
                brief_data = data["data"]
                signals = brief_data.get("top_signals", [])
                risks = brief_data.get("top_risks", [])
                print(f"✅ Daily Brief: OK")
                print(f"   Signals found: {len(signals)}")
                print(f"   Risks found: {len(risks)}")
                if signals:
                    print(f"   Top signal: {signals[0].get('ticker', 'N/A')} - Score: {signals[0].get('composite_score', 'N/A')}")
                return True
            else:
                print("❌ Daily Brief: Response not OK")
                return False
        else:
            print(f"❌ Daily Brief: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Daily Brief: Error - {e}")
        return False

def test_copilot_ask():
    """Test copilot ask endpoint."""
    print("\n🤖 Testing Copilot Ask...")
    try:
        import requests
        question = "Quelle est l'inflation actuelle aux États-Unis ?"
        payload = {
            "question": question,
            "context_years": 5,
            "max_sources": 10
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
                print(f"✅ Copilot Ask: OK")
                print(f"   Question: {question}")
                print(f"   Answer length: {len(answer)} chars")
                print(f"   Sources found: {len(sources)}")
                if sources:
                    print(f"   First source type: {sources[0].get('type', 'N/A')}")
                return True
            else:
                print("❌ Copilot Ask: Response not OK")
                return False
        else:
            print(f"❌ Copilot Ask: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Copilot Ask: Error - {e}")
        return False

def test_alerts():
    """Test alerts endpoint."""
    print("\n🚨 Testing Alerts...")
    try:
        import requests
        response = requests.get("http://localhost:8050/api/alerts?limit=10", timeout=10)
        if response.status_code == 00:
            data = response.json()
            if data.get("ok") and data.get("data"):
                alerts_data = data["data"]
                alerts = alerts_data.get("alerts", [])
                print(f"✅ Alerts: OK")
                print(f"   Alerts found: {len(alerts)}")
                if alerts:
                    print(f"   First alert type: {alerts[0].get('type', 'N/A')}")
                    print(f"   First alert severity: {alerts[0].get('severity', 'N/A')}")
                return True
            else:
                print("❌ Alerts: Response not OK")
                return False
        else:
            print(f"❌ Alerts: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Alerts: Error - {e}")
        return False

def test_data_access_layer():
    """Test core data access functions."""
    print("\n💾 Testing Data Access Layer...")
    try:
        from core.data_access import get_close_series, load_macro_forecast_rows, load_news_features
        
        # Test get_close_series
        series = get_close_series("SPY")
        print(f"✅ get_close_series: {'Has data' if series is not None else 'No data (OK)'}")
        
        # Test load_macro_forecast_rows
        macro_data = load_macro_forecast_rows(limit=1)
        print(f"✅ load_macro_forecast_rows: OK")
        
        # Test load_news_features
        news_data = load_news_features(limit=10)
        print(f"✅ load_news_features: {len(news_data.get('rows', []))} rows")
        
        return True
    except Exception as e:
        print(f"❌ Data Access Layer: Error - {e}")
        return False

def test_scoring_system():
    """Test scoring system functions."""
    print("\n📈 Testing Scoring System...")
    try:
        from research.scoring import calculate_composite_score, compute_composite_brief, get_top_signals_and_risks
        
        # Test calculate_composite_score
        try:
            score = calculate_composite_score("SPY")
            print(f"✅ calculate_composite_score: Score = {score.get('composite_score', 'N/A')}")
        except Exception as e:
            print(f"⚠️  calculate_composite_score: No data available (OK) - {e}")
        
        # Test compute_composite_brief
        brief = compute_composite_brief(period="weekly", universe=["SPY"])
        print(f"✅ compute_composite_brief: OK")
        
        # Test get_top_signals_and_risks
        signals_data = get_top_signals_and_risks(["SPY", "QQQ"], top_n=3)
        signals = signals_data.get("signals", [])
        risks = signals_data.get("risks", [])
        print(f"✅ get_top_signals_and_risks: {len(signals)} signals, {len(risks)} risks")
        
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
        print(f"✅ RAG Store stats: {stats}")
        
        # Test search
        results = rag_store.search({}, top_k=5)
        print(f"✅ RAG Search: Found {len(results)} results")
        
        return True
    except Exception as e:
        print(f"❌ RAG Store: Error - {e}")
        return False

def main():
    """Run complete UI test simulation."""
    print("🚀 Lancement du Test UI Complet - Simulation de l'Expérience Utilisateur")
    print("=" * 70)
    
    start_time = time.time()
    
    # Test sequence - simulate user journey
    tests = [
        ("API Health Check", test_api_health),
        ("Dashboard KPIs", test_dashboard_kpis),
        ("Weekly Market Brief", test_weekly_brief),
        ("Daily Market Brief", test_daily_brief),
        ("Copilot Q&A", test_copilot_ask),
        ("Alerts System", test_alerts),
        ("Data Access Layer", test_data_access_layer),
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
    print(f"\n{'='*70}")
    print("📊 RÉSULTATS DU TEST UI COMPLET")
    print(f"{'='*70}")
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:<10} {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n{'='*70}")
    print(f"⏱️  TEMPS TOTAL: {end_time - start_time:.2f} secondes")
    print(f"✅ RÉUSSIS: {passed}")
    print(f"❌ ÉCHOUÉS: {failed}")
    print(f"📊 TAUX DE SUCCÈS: {passed/len(results)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 Tous les tests UI ont PASSÉ ! L'application est prête.")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) ont ÉCHOUÉ. Veuillez vérifier les erreurs ci-dessus.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)