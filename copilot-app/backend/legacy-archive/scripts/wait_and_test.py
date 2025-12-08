#!/usr/bin/env python3
"""
Script qui attend que le backend démarre puis teste tous les endpoints
Usage: python scripts/wait_and_test.py
"""
import sys
import time
import requests
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).resolve().parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

BASE_URL = "http://localhost:8050"
MAX_WAIT = 60  # Maximum 60 secondes d'attente
CHECK_INTERVAL = 2  # Vérifier toutes les 2 secondes

def wait_for_backend():
    """Attend que le backend soit accessible"""
    print("⏳ Attente que le backend démarre...")
    print(f"   URL: {BASE_URL}")
    print(f"   Timeout: {MAX_WAIT}s")
    
    start_time = time.time()
    attempt = 0
    
    while time.time() - start_time < MAX_WAIT:
        attempt += 1
        try:
            response = requests.get(f"{BASE_URL}/api/health", timeout=2)
            if response.status_code == 200:
                elapsed = time.time() - start_time
                print(f"✅ Backend accessible après {elapsed:.1f}s ({attempt} tentatives)")
                return True
        except requests.exceptions.ConnectionError:
            if attempt % 5 == 0:
                elapsed = time.time() - start_time
                print(f"   ... toujours en attente ({elapsed:.0f}s)")
        except Exception:
            pass
        
        time.sleep(CHECK_INTERVAL)
    
    print(f"❌ Backend non accessible après {MAX_WAIT}s")
    return False

def test_endpoint(path, name, expected_keys=None):
    """Test un endpoint"""
    url = f"{BASE_URL}{path}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and 'ok' in data and 'data' in data:
                actual = data['data']
                if expected_keys:
                    missing = [k for k in expected_keys if k not in actual]
                    if missing:
                        return False, f"Clés manquantes: {missing}"
                return True, "OK"
            return True, "OK"
        return False, f"Status {response.status_code}"
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 70)
    print("🧪 TEST AUTOMATIQUE DES ENDPOINTS")
    print("=" * 70)
    
    # Attendre le backend
    if not wait_for_backend():
        print("\n❌ Impossible de continuer sans backend")
        print("   → Démarrez le backend: ./finance-copilot.sh start")
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("📡 TEST DES ENDPOINTS")
    print("=" * 70)
    
    endpoints = [
        ('/api/health', 'Health Check', ['status']),
        ('/api/forecasts', 'Forecasts', ['rows']),
        ('/api/intelligence/snapshot', 'Intelligence Snapshot', ['insights']),
        ('/api/recommendations/daily?limit=3', 'Recommendations', ['recommendations']),
        ('/api/news/feed', 'News Feed', ['articles']),
    ]
    
    results = {}
    for path, name, keys in endpoints:
        success, message = test_endpoint(path, name, keys)
        status = "✅ PASS" if success else f"❌ FAIL ({message})"
        print(f"  {name:25} : {status}")
        results[name] = success
    
    # Test détaillé intelligence
    print("\n" + "=" * 70)
    print("🔍 TEST DÉTAILLÉ - Intelligence")
    print("=" * 70)
    try:
        response = requests.get(f"{BASE_URL}/api/intelligence/snapshot", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                insights = data['data'].get('insights', {})
                regime = insights.get('market_regime', {})
                explanation = regime.get('explanation', '')
                print(f"✅ Régime: {regime.get('current', 'N/A')}")
                print(f"✅ Explication: {explanation}")
                
                # Vérifier valeurs non-nulles
                if '0.00' in explanation and 'vs bearish +0.00' in explanation:
                    print("⚠️  Bearish pressure à 0.00 (normal si tous forecasts sont bullish)")
                else:
                    print("✅ Valeurs non-nulles détectées")
                
                opps = insights.get('opportunities', [])
                risks = insights.get('risks', [])
                print(f"✅ Opportunités: {len(opps)}")
                print(f"✅ Risques: {len(risks)}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    # Test détaillé recommendations
    print("\n" + "=" * 70)
    print("🔍 TEST DÉTAILLÉ - Recommendations")
    print("=" * 70)
    try:
        response = requests.get(f"{BASE_URL}/api/recommendations/daily?limit=3", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                recs = data['data'].get('recommendations', [])
                print(f"✅ Recommandations: {len(recs)}")
                for i, rec in enumerate(recs[:3]):
                    ticker = rec.get('ticker', 'N/A')
                    action = rec.get('action', 'N/A')
                    print(f"   {i+1}. {ticker}: {action}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    # Résumé final
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ")
    print("=" * 70)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"Tests réussis: {passed}/{total}")
    
    if passed == total:
        print("✅ TOUS LES TESTS SONT PASSÉS!")
        print("\n🎉 Le dashboard devrait maintenant afficher:")
        print("   - Market Intelligence avec valeurs non-nulles")
        print("   - Recommendations")
        print("   - Forecasts")
        sys.exit(0)
    else:
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
        sys.exit(1)

if __name__ == "__main__":
    main()

