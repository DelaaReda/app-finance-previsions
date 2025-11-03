#!/usr/bin/env python3
"""
Script de diagnostic complet pour l'application Finance Copilot
Teste tous les services et endpoints pour identifier les problèmes
"""
import requests
import json
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys
import subprocess

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Base URLs
API_BASE = "http://localhost:8050"
FRONTEND_BASE = "http://localhost:5173"

class FinanceCopilotDiagnostic:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.results = {
            'backend': {},
            'frontend': {},
            'api_endpoints': {},
            'errors': []
        }
    
    def check_backend_health(self) -> bool:
        """Vérifie l'état de santé du backend"""
        try:
            response = self.session.get(f"{API_BASE}/api/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.results['backend']['health'] = {
                    'status': 'OK',
                    'data': data
                }
                print("✅ Backend Health: OK")
                return True
            else:
                error_msg = f"HTTP {response.status_code} - {response.text[:200]}"
                self.results['backend']['health'] = {
                    'status': 'ERROR',
                    'error': error_msg
                }
                print(f"❌ Backend Health: {error_msg}")
                return False
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            self.results['backend']['health'] = {
                'status': 'ERROR',
                'error': error_msg
            }
            print(f"❌ Backend Health: {error_msg}")
            return False
    
    def check_frontend_health(self) -> bool:
        """Vérifie si le frontend est accessible"""
        try:
            response = self.session.get(FRONTEND_BASE, timeout=10)
            if response.status_code == 200 and '<html' in response.text.lower():
                self.results['frontend']['status'] = 'OK'
                print("✅ Frontend Access: OK")
                return True
            else:
                error_msg = f"HTTP {response.status_code} - Pas de contenu HTML valide"
                self.results['frontend']['status'] = 'ERROR'
                self.results['frontend']['error'] = error_msg
                print(f"❌ Frontend Access: {error_msg}")
                return False
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            self.results['frontend']['status'] = 'ERROR'
            self.results['frontend']['error'] = error_msg
            print(f"❌ Frontend Access: {error_msg}")
            return False
    
    def test_api_endpoint(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
        """Teste un endpoint API spécifique"""
        try:
            url = f"{API_BASE}{endpoint}"
            
            if method.upper() == "GET":
                response = self.session.get(url, timeout=15)
            elif method.upper() == "POST" and data:
                response = self.session.post(url, json=data, timeout=15)
            else:
                raise ValueError(f"Méthode non supportée: {method}")
            
            status = response.status_code
            try:
                json_data = response.json()
                is_json = True
            except:
                json_data = response.text
                is_json = False
            
            return {
                "status": status,
                "ok": response.ok,
                "data": json_data if is_json else None,
                "text": json_data if not is_json else None,
                "is_json": is_json,
                "error": None
            }
        except Exception as e:
            return {
                "status": None,
                "ok": False,
                "data": None,
                "text": None,
                "is_json": False,
                "error": f"Exception: {str(e)}"
            }
    
    def comprehensive_api_test(self) -> Dict[str, bool]:
        """Teste tous les endpoints API critiques"""
        endpoints_to_test = [
            # Health endpoints
            ("/api/health", "GET"),
            ("/api/freshness", "GET"),
            
            # Macro endpoints
            ("/api/macro/series?ids=CPIAUCSL&limit=1", "GET"),
            ("/api/macro/snapshot", "GET"),
            ("/api/macro/indicators", "GET"),
            
            # Stocks endpoints
            ("/api/stocks/prices?ticker=SPY&range=1mo", "GET"),
            ("/api/stocks/universe", "GET"),
            
            # News endpoints
            ("/api/news/feed?limit=5", "GET"),
            ("/api/news/sentiment", "GET"),
            ("/api/news/events", "GET"),
            
            # Brief endpoints
            ("/api/brief/daily", "GET"),
            ("/api/brief/weekly", "GET"),
            
            # Copilot endpoints
            ("/api/copilot/ask", "POST", {"question": "What is the current market trend?", "scope": {}}),
            
            # Dashboard endpoints
            ("/api/dashboard/kpis", "GET"),
            
            # RAG endpoints
            ("/api/rag/stats", "GET"),
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
                if result['error']:
                    print(f"     Error: {result['error']}")
                elif result['text']:
                    print(f"     Response: {result['text'][:200]}...")
                results[key] = False
                
                # Save error details
                self.results['api_endpoints'][key] = result
                self.results['errors'].append({
                    'endpoint': endpoint,
                    'method': method,
                    'status': result['status'],
                    'error': result['error'] or result['text'][:200] if result['text'] else 'No response'
                })
        
        return results
    
    def check_processes(self):
        """Vérifie si les processus backend/frontend sont en cours d'exécution"""
        print("\n🔍 Vérification des processus...")
        
        # Check backend
        try:
            backend_check = subprocess.run(['lsof', '-i', ':8050'], 
                                          capture_output=True, text=True, timeout=5)
            if backend_check.returncode == 0 and 'LISTEN' in backend_check.stdout:
                print("✅ Backend process: RUNNING (port 8050)")
                self.results['processes'] = {'backend': 'RUNNING'}
            else:
                print("❌ Backend process: NOT RUNNING")
                self.results['processes'] = {'backend': 'NOT RUNNING'}
        except Exception as e:
            print(f"⚠️  Backend process check failed: {e}")
            self.results['processes'] = {'backend': f'CHECK FAILED: {e}'}
        
        # Check frontend
        try:
            frontend_check = subprocess.run(['lsof', '-i', ':5173'], 
                                          capture_output=True, text=True, timeout=5)
            if frontend_check.returncode == 0 and 'LISTEN' in frontend_check.stdout:
                print("✅ Frontend process: RUNNING (port 5173)")
                if 'processes' not in self.results:
                    self.results['processes'] = {}
                self.results['processes']['frontend'] = 'RUNNING'
            else:
                print("❌ Frontend process: NOT RUNNING")
                if 'processes' not in self.results:
                    self.results['processes'] = {}
                self.results['processes']['frontend'] = 'NOT RUNNING'
        except Exception as e:
            print(f"⚠️  Frontend process check failed: {e}")
            if 'processes' not in self.results:
                self.results['processes'] = {}
            self.results['processes']['frontend'] = f'CHECK FAILED: {e}'
    
    def generate_report(self):
        """Génère un rapport de diagnostic complet"""
        print("\n" + "="*80)
        print("📊 RAPPORT DE DIAGNOSTIC COMPLET - Finance Copilot")
        print("="*80)
        
        # Backend status
        backend_health = self.results.get('backend', {}).get('health', {})
        if backend_health.get('status') == 'OK':
            print("✅ Backend: OPÉRATIONNEL")
        else:
            print("❌ Backend: PROBLÈMES DÉTECTÉS")
            if 'error' in backend_health:
                print(f"   → {backend_health['error']}")
        
        # Frontend status
        frontend_status = self.results.get('frontend', {}).get('status')
        if frontend_status == 'OK':
            print("✅ Frontend: ACCESSIBLE")
        else:
            print("❌ Frontend: PROBLÈMES D'ACCÈS")
            frontend_error = self.results.get('frontend', {}).get('error')
            if frontend_error:
                print(f"   → {frontend_error}")
        
        # Processes
        processes = self.results.get('processes', {})
        if processes.get('backend') == 'RUNNING':
            print("✅ Processus Backend: EN COURS")
        else:
            print("❌ Processus Backend: ARRÊTÉ")
            print(f"   → {processes.get('backend', 'INCONNU')}")
            
        if processes.get('frontend') == 'RUNNING':
            print("✅ Processus Frontend: EN COURS")
        else:
            print("❌ Processus Frontend: ARRÊTÉ")
            print(f"   → {processes.get('frontend', 'INCONNU')}")
        
        # API Endpoints summary
        api_results = self.results.get('api_endpoints', {})
        working_endpoints = sum(1 for r in api_results.values() if r.get('ok'))
        total_endpoints = len(api_results)
        
        print(f"\n📊 Endpoints API: {working_endpoints}/{total_endpoints} fonctionnels")
        
        if total_endpoints > 0:
            success_rate = (working_endpoints / total_endpoints) * 100
            print(f"   Taux de succès: {success_rate:.1f}%")
            
            if success_rate < 80:
                print("   ⚠️  Taux de succès faible - Problèmes majeurs détectés")
            elif success_rate < 100:
                print("   ⚠️  Quelques endpoints rencontrent des problèmes")
            else:
                print("   ✅ Tous les endpoints fonctionnent correctement")
        
        # Errors summary
        errors = self.results.get('errors', [])
        if errors:
            print(f"\n❌ {len(errors)} ERREURS DÉTECTÉES:")
            for i, error in enumerate(errors[:10], 1):  # Show first 10 errors
                print(f"   {i}. {error['method']} {error['endpoint']}")
                print(f"      → {error['error']}")
                if i >= 10 and len(errors) > 10:
                    print(f"      ... et {len(errors) - 10} autres erreurs")
                    break
        else:
            print("\n✅ Aucune erreur détectée")
        
        # Recommendations
        print("\n" + "="*80)
        print("💡 RECOMMANDATIONS")
        print("="*80)
        
        if not processes.get('backend') == 'RUNNING':
            print("🔧 Backend non démarré:")
            print("   → Exécutez: cd /Users/venom/Documents/analyse-financiere && python run_api.py")
        
        if not processes.get('frontend') == 'RUNNING':
            print("🔧 Frontend non démarré:")
            print("   → Exécutez: cd /Users/venom/Documents/analyse-financiere/webapp && npm run dev")
        
        if backend_health.get('status') != 'OK':
            print("🔧 Problèmes backend:")
            print("   → Vérifiez les logs: tail -f /Users/venom/Documents/analyse-financiere/api.log")
            print("   → Vérifiez la configuration .env")
        
        if frontend_status != 'OK':
            print("🔧 Problèmes frontend:")
            print("   → Vérifiez la configuration Vite")
            print("   → Vérifiez les dépendances: npm install")
        
        if errors:
            print("🔧 Problèmes API spécifiques:")
            for error in errors[:3]:
                print(f"   → {error['method']} {error['endpoint']}: {error['error'][:100]}...")
        
        print("\n" + "="*80)
        print("📝 Pour un diagnostic plus détaillé, exécutez:")
        print("   python scripts/full_diagnostic.py --verbose")
        print("="*80)
    
    def run_full_diagnostic(self):
        """Exécute le diagnostic complet"""
        print("🚀 Démarrage du diagnostic complet Finance Copilot...")
        print("="*80)
        
        # Check processes first
        self.check_processes()
        
        # Test backend health
        print("\n1. Test de l'état de santé du backend...")
        backend_ok = self.check_backend_health()
        
        # Test frontend access
        print("\n2. Test de l'accès au frontend...")
        frontend_ok = self.check_frontend_health()
        
        # Test API endpoints
        print("\n3. Test complet des endpoints API...")
        api_results = self.comprehensive_api_test()
        
        # Generate final report
        self.generate_report()
        
        return {
            'backend_healthy': backend_ok,
            'frontend_accessible': frontend_ok,
            'api_results': api_results
        }

def main():
    diagnostic = FinanceCopilotDiagnostic()
    
    # Run with verbose mode if requested
    verbose = '--verbose' in sys.argv
    
    results = diagnostic.run_full_diagnostic()
    
    # Exit with appropriate code
    overall_success = all([
        results['backend_healthy'],
        results['frontend_accessible'],
        all(results['api_results'].values()) if results['api_results'] else True
    ])
    
    sys.exit(0 if overall_success else 1)

if __name__ == "__main__":
    main()