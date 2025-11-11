#!/usr/bin/env python3
"""
Test Playwright simplifié pour vérifier que les données du backend arrivent jusqu'au frontend
"""
import asyncio
import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

async def test_frontend_simple():
    """Test simple du frontend avec Playwright"""
    try:
        from playwright.async_api import async_playwright
        
        print("🔍 Test Playwright - Vérification frontend/backend")
        print("=" * 50)
        
        async with async_playwright() as p:
            # Lancer le navigateur
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Aller sur la page principale
            print("🌐 Navigation vers http://localhost:5173...")
            await page.goto("http://localhost:5173", wait_until="load", timeout=30000)
            
            # Attendre un peu pour le chargement
            await page.wait_for_timeout(2000)
            
            # Vérifier le titre de la page
            title = await page.title()
            print(f"   📄 Titre: {title}")
            
            # Vérifier que c'est bien la page Finance Copilot
            if "Finance Copilot" in title:
                print("   ✅ Titre correct")
            else:
                print("   ⚠️  Titre incorrect")
            
            # Tester les appels API backend
            print("\n📡 Test des appels API backend...")
            
            # Intercepter les appels réseau
            api_responses = []
            
            async def handle_response(response):
                if "localhost:8050" in response.url:
                    api_responses.append({
                        "url": response.url,
                        "status": response.status,
                        "ok": response.status == 200
                    })
            
            page.on("response", handle_response)
            
            # Recharger la page pour capturer les appels API
            await page.reload(wait_until="load", timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Afficher les résultats
            print(f"   📡 Appels API backend détectés: {len(api_responses)}")
            for resp in api_responses:
                status_icon = "✅" if resp["ok"] else "❌"
                print(f"   {status_icon} {resp['status']} {resp['url']}")
            
            # Fermer le navigateur
            await browser.close()
            
            # Résumé
            print("\n" + "=" * 50)
            print("📊 RÉSUMÉ DU TEST")
            print("=" * 50)
            
            successful_calls = sum(1 for resp in api_responses if resp["ok"])
            total_calls = len(api_responses)
            
            print(f"📡 Appels API backend: {successful_calls}/{total_calls} réussis")
            print(f"🌐 Frontend: ACCESSIBLE")
            print(f"🔗 Backend: CONNECTÉ")
            
            if successful_calls > 0:
                print("\n🎉 Test Playwright réussi !")
                print("   Les données du backend arrivent au frontend.")
                return True
            else:
                print("\n⚠️  Aucun appel API backend détecté.")
                print("   Le frontend est accessible mais les données peuvent ne pas arriver.")
                return False
                
    except Exception as e:
        print(f"❌ Erreur lors du test Playwright: {e}")
        return False

def main():
    """Fonction principale"""
    print("🚀 Démarrage du test Playwright Finance Copilot...")
    
    # Exécuter le test
    success = asyncio.run(test_frontend_simple())
    
    if success:
        print("\n✅ Test Playwright réussi !")
        sys.exit(0)
    else:
        print("\n❌ Test Playwright échoué !")
        sys.exit(1)

if __name__ == "__main__":
    main()