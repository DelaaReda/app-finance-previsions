#!/usr/bin/env python3
"""
Script de test complet pour vérifier que tous les endpoints fonctionnent
Usage: python scripts/test_endpoints.py
"""
import sys
import json
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_path = Path(__file__).resolve().parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

import requests
import time

BASE_URL = "http://localhost:8050"
TIMEOUT = 10

def test_endpoint(path, description, expected_keys=None):
    """Test un endpoint et retourne le résultat"""
    url = f"{BASE_URL}{path}"
    print(f"\n🔍 Test: {description}")
    print(f"   URL: {url}")
    
    try:
        response = requests.get(url, timeout=TIMEOUT)
        status = response.status_code
        
        if status == 200:
            try:
                data = response.json()
                
                # Vérifier la structure {ok, data} si présente
                if isinstance(data, dict) and 'ok' in data and 'data' in data:
                    actual_data = data['data']
                    ok_status = data.get('ok', False)
                    if not ok_status:
                        print(f"   ❌ Status: 200 mais ok=false")
                        print(f"   Error: {data.get('error', 'Unknown')}")
                        return False
                else:
                    actual_data = data
                
                # Vérifier les clés attendues
                if expected_keys:
                    missing = [k for k in expected_keys if k not in actual_data]
                    if missing:
                        print(f"   ⚠️  Clés manquantes: {missing}")
                    else:
                        print(f"   ✅ Toutes les clés présentes")
                
                # Afficher un résumé
                if isinstance(actual_data, dict):
                    print(f"   ✅ Réponse: {len(actual_data)} clés")
                    for key in list(actual_data.keys())[:5]:
                        value = actual_data[key]
                        if isinstance(value, list):
                            print(f"      - {key}: {len(value)} éléments")
                        elif isinstance(value, dict):
                            print(f"      - {key}: {len(value)} sous-clés")
                        else:
                            print(f"      - {key}: {type(value).__name__}")
                elif isinstance(actual_data, list):
                    print(f"   ✅ Réponse: {len(actual_data)} éléments")
                
                return True
                
            except json.JSONDecodeError:
                print(f"   ❌ Réponse n'est pas du JSON valide")
                print(f"   Contenu: {response.text[:200]}")
                return False
        else:
            print(f"   ❌ Status: {status}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data}")
            except:
                print(f"   Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"   ❌ CONNEXION REFUSÉE - Le backend n'est pas démarré")
        print(f"   → Démarrez le backend: ./finance-copilot.sh start")
        return False
    except requests.exceptions.Timeout:
        print(f"   ❌ TIMEOUT - Le backend ne répond pas dans les {TIMEOUT}s")
        return False
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return False

def main():
    print("=" * 70)
    print("🧪 TEST COMPLET DES ENDPOINTS")
    print("=" * 70)
    print(f"Base URL: {BASE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 70)
    
    # Vérifier que le backend est accessible
    print("\n📡 Vérification de la connexion au backend...")
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend accessible")
        else:
            print(f"⚠️  Backend répond mais avec status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ BACKEND NON ACCESSIBLE")
        print("   → Démarrez le backend: ./finance-copilot.sh start")
        print("   → Attendez quelques secondes puis relancez ce script")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        sys.exit(1)
    
    # Tests des endpoints
    results = {}
    
    results['health'] = test_endpoint(
        '/api/health',
        'Health Check',
        ['status', 'backend_up']
    )
    
    results['forecasts'] = test_endpoint(
        '/api/forecasts',
        'Forecasts',
        ['rows']
    )
    
    results['intelligence'] = test_endpoint(
        '/api/intelligence/snapshot',
        'Intelligence Snapshot',
        ['insights']
    )
    
    results['recommendations'] = test_endpoint(
        '/api/recommendations/daily?limit=3',
        'Recommendations Daily',
        ['recommendations', 'market_context']
    )
    
    results['news'] = test_endpoint(
        '/api/news/feed',
        'News Feed',
        ['articles']
    )
    
    results['macro'] = test_endpoint(
        '/api/macro/series',
        'Macro Series',
        None
    )
    
    # Résumé
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for endpoint, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {endpoint:20} : {status}")
    
    print("=" * 70)
    print(f"Résultat: {passed}/{total} tests réussis")
    
    if passed == total:
        print("✅ TOUS LES TESTS SONT PASSÉS")
        sys.exit(0)
    else:
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print("\n💡 Actions recommandées:")
        print("   1. Vérifier les logs du backend: tail -f copilot-app/backend/api.log")
        print("   2. Vérifier que les données sont générées: python scripts/generate_data.py")
        print("   3. Redémarrer le backend: ./finance-copilot.sh restart")
        sys.exit(1)

if __name__ == "__main__":
    main()

