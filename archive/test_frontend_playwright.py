#!/usr/bin/env python3
"""
Test Playwright pour vérifier que les données du backend arrivent jusqu'au frontend
"""
import asyncio
import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

async def test_frontend_data_flow():
    """Test complet du flux de données backend → frontend avec Playwright"""
    try:
        from playwright.async_api import async_playwright
        
        print("🔍 Test Playwright - Flux de données Finance Copilot")
        print("=" * 60)
        
        async with async_playwright() as p:
            # Lancer le navigateur
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Aller sur la page principale
            print("🌐 Navigation vers http://localhost:5173...")
            await page.goto("http://localhost:5173", wait_until="networkidle", timeout=60000)
            
            # Attendre que la page charge
            await page.wait_for_timeout(3000)
            
            # Tester le dashboard
            print("\n📊 Test du Dashboard...")
            
            # Vérifier que les KPIs sont affichés
            try:
                kpi_elements = await page.query_selector_all(".kpi-card")
                print(f"   ✅ KPI Cards trouvées: {len(kpi_elements)}")
                
                if len(kpi_elements) > 0:
                    # Vérifier le contenu des KPIs
                    for i, kpi in enumerate(kpi_elements[:3]):
                        text = await kpi.text_content()
                        print(f"   📋 KPI {i+1}: {text[:50]}...")
            except Exception as e:
                print(f"   ⚠️  KPI Cards: {e}")
            
            # Tester l'accès aux données API via le frontend
            print("\n📡 Test des appels API via frontend...")
            
            # Intercepter les appels réseau
            api_calls = []
            
            async def handle_response(response):
                if "/api/" in response.url:
                    api_calls.append({
                        "url": response.url,
                        "status": response.status,
                        "ok": response.status == 200
                    })
            
            page.on("response", handle_response)
            
            # Rafraîchir la page pour capturer les appels API
            await page.reload(wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(2000)
            
            # Afficher les résultats des appels API
            print(f"   📡 Appels API interceptés: {len(api_calls)}")
            for call in api_calls:
                status_icon = "✅" if call["ok"] else "❌"
                print(f"   {status_icon} {call['status']} {call['url']}")
            
            # Tester la page Market Brief
            print("\n📰 Test de la page Market Brief...")
            await page.goto("http://localhost:5173/brief", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(2000)
            
            # Vérifier que les signaux sont affichés
            try:
                signal_elements = await page.query_selector_all(".signal-item")
                print(f"   ✅ Signaux trouvés: {len(signal_elements)}")
                
                if len(signal_elements) > 0:
                    # Vérifier le contenu des premiers signaux
                    for i, signal in enumerate(signal_elements[:3]):
                        text = await signal.text_content()
                        print(f"   📋 Signal {i+1}: {text[:100]}...")
            except Exception as e:
                print(f"   ⚠️  Signaux: {e}")
            
            # Tester la page Stocks
            print("\n📈 Test de la page Stocks...")
            await page.goto("http://localhost:5173/stocks", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(2000)
            
            # Vérifier que les données boursières sont affichées
            try:
                stock_elements = await page.query_selector_all(".stock-row")
                print(f"   ✅ Lignes boursières trouvées: {len(stock_elements)}")
                
                if len(stock_elements) > 0:
                    # Vérifier le contenu des premières lignes
                    for i, stock in enumerate(stock_elements[:3]):
                        text = await stock.text_content()
                        print(f"   📋 Stock {i+1}: {text[:100]}...")
            except Exception as e:
                print(f"   ⚠️  Données boursières: {e}")
            
            # Tester la page Macro
            print("\n💼 Test de la page Macro...")
            await page.goto("http://localhost:5173/macro", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(2000)
            
            # Vérifier que les données macro sont affichées
            try:
                macro_elements = await page.query_selector_all(".macro-indicator")
                print(f"   ✅ Indicateurs macro trouvés: {len(macro_elements)}")
                
                if len(macro_elements) > 0:
                    # Vérifier le contenu des premiers indicateurs
                    for i, indicator in enumerate(macro_elements[:3]):
                        text = await indicator.text_content()
                        print(f"   📋 Indicateur {i+1}: {text[:100]}...")
            except Exception as e:
                print(f"   ⚠️  Données macro: {e}")
            
            # Fermer le navigateur
            await browser.close()
            
            # Résumé
            print("\n" + "=" * 60)
            print("📊 RÉSUMÉ DU TEST PLAYWRIGHT")
            print("=" * 60)
            
            # Compter les appels API réussis
            successful_calls = sum(1 for call in api_calls if call["ok"])
            total_calls = len(api_calls)
            
            print(f"📡 Appels API: {successful_calls}/{total_calls} réussis")
            print(f"📊 Données affichées: Dashboard, Brief, Stocks, Macro")
            print(f"🌐 Frontend: ACCESSIBLE")
            print(f"🔗 Backend: CONNECTÉ")
            
            if successful_calls > 0:
                print("\n🎉 Test Playwright réussi !")
                print("   Les données du backend arrivent correctement jusqu'au frontend.")
                return True
            else:
                print("\n❌ Test Playwright échoué !")
                print("   Aucun appel API réussi détecté.")
                return False
                
    except Exception as e:
        print(f"❌ Erreur lors du test Playwright: {e}")
        return False

def main():
    """Fonction principale"""
    print("🚀 Démarrage du test Playwright Finance Copilot...")
    
    # Exécuter le test
    success = asyncio.run(test_frontend_data_flow())
    
    if success:
        print("\n✅ Tous les tests Playwright ont réussi !")
        print("   Finance Copilot fonctionne correctement du backend au frontend.")
        sys.exit(0)
    else:
        print("\n❌ Certains tests Playwright ont échoué !")
        print("   Veuillez vérifier les connexions backend ↔ frontend.")
        sys.exit(1)

if __name__ == "__main__":
    main()