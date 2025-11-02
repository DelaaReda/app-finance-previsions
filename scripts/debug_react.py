#!/usr/bin/env python3
"""
Helper script for debugging React application with React Developer Tools
Provides guidance and quick checks for common debugging scenarios
"""
import sys
import os
import subprocess
import webbrowser
from pathlib import Path

def check_react_devtools_installed():
    """Check if React Developer Tools is installed in the browser."""
    print("🔍 Vérification de React Developer Tools...")
    print("")
    print("Pour vérifier si React Developer Tools est installé :")
    print("1. Ouvrez votre navigateur (Chrome, Firefox, ou Edge)")
    print("2. Allez sur http://localhost:5173 (l'application Finance Copilot)")
    print("3. Ouvrez les Outils Développeur (F12 ou Ctrl+Shift+I)")
    print("4. Regardez les onglets : vous devriez voir 'Components' et 'Profiler'")
    print("")
    print("Si vous ne voyez pas ces onglets :")
    print("  - Installez l'extension React Developer Tools depuis le store de votre navigateur")
    print("  - Redémarrez votre navigateur")
    print("  - Rafraîchissez la page de l'application")

def launch_with_debugging():
    """Launch the application with debugging hints."""
    print("🚀 Lancement de l'application Finance Copilot avec conseils de débogage...")
    print("")
    
    # Check if API is running
    try:
        import requests
        response = requests.get("http://localhost:8050/health", timeout=2)
        if response.status_code == 200:
            print("✅ API Backend déjà en cours d'exécution")
        else:
            print("⚠️  API Backend répond mais avec un statut inattendu")
    except:
        print("ℹ️  API Backend non détecté - assurez-vous qu'il est lancé")
        print("   Commande : python run_api.py")
    
    # Check if frontend is running
    try:
        import requests
        response = requests.get("http://localhost:5173", timeout=2)
        if response.status_code == 200:
            print("✅ Frontend React déjà en cours d'exécution")
            webbrowser.open("http://localhost:5173")
        else:
            print("⚠️  Frontend React répond mais avec un statut inattendu")
    except:
        print("ℹ️  Frontend React non détecté - démarrez-le avec :")
        print("   cd webapp && npm run dev")
    
    print("")
    print("📊 Conseils de débogage avec React Developer Tools :")
    print("1. Une fois l'application chargée, ouvrez les Outils Développeur")
    print("2. Cliquez sur l'onglet 'Components'")
    print("3. Explorez l'arbre des composants :")
    print("   - Dashboard")
    print("   - MarketBrief") 
    print("   - Copilot")
    print("   - News")
    print("   - Stocks")
    print("4. Sélectionnez un composant pour voir ses props et state")
    print("5. Utilisez l'onglet 'Profiler' pour analyser les performances")

def debug_common_issues():
    """Provide guidance for common debugging issues."""
    print("🛠️  Guide de débogage des problèmes courants")
    print("")
    print("PROBLÈME: Les données ne s'affichent pas")
    print("SOLUTION:")
    print("  1. Dans Components, trouvez le composant concerné (ex: Dashboard)")
    print("  2. Vérifiez les props - sont-elles correctement passées ?")
    print("  3. Vérifiez l'état (state) - y a-t-il des erreurs ?")
    print("  4. Dans la console, regardez les erreurs réseau (onglet Network)")
    print("  5. Vérifiez que l'API répond correctement :")
    print("     curl http://localhost:8050/api/brief/weekly")
    print("")
    print("PROBLÈME: L'application est lente")
    print("SOLUTION:")
    print("  1. Onglet 'Profiler' → Record → Interagissez avec l'application → Stop")
    print("  2. Analysez les commits avec les temps les plus longs")
    print("  3. Identifiez les composants qui re-rendent inutilement")
    print("  4. Vérifiez Why did this render ? pour chaque composant")
    print("")
    print("PROBLÈME: Les filtres ne fonctionnent pas")
    print("SOLUTION:")
    print("  1. Dans Components, trouvez le composant de filtre")
    print("  2. Surveillez les changements d'état lors des interactions")
    print("  3. Vérifiez que les handlers d'événements sont correctement attachés")
    print("  4. Dans Network, vérifiez que les requêtes API sont correctes")

def show_component_hierarchy():
    """Show the expected component hierarchy for debugging."""
    print("🌳 Hiérarchie des Composants Finance Copilot")
    print("")
    print("App")
    print("├── MainLayout")
    print("│   ├── Header")
    print("│   ├── Routes")
    print("│   │   ├── Dashboard")
    print("│   │   │   ├── Filters (Sector/Horizon/Theme)")
    print("│   │   │   ├── KPIsGrid")
    print("│   │   │   ├── TopSignals")
    print("│   │   │   └── TopRisks") 
    print("│   │   ├── MarketBrief")
    print("│   │   │   ├── BriefHeader")
    print("│   │   │   ├── PeriodSelector")
    print("│   │   │   ├── TopSignals")
    print("│   │   │   └── TopRisks")
    print("│   │   ├── Copilot")
    print("│   │   │   ├── ChatInterface")
    print("│   │   │   ├── MessageHistory")
    print("│   │   │   └── QuestionInput")
    print("│   │   ├── News")
    print("│   │   │   ├── NewsFilters")
    print("│   │   │   ├── NewsFeed")
    print("│   │   │   └── NewsCard")
    print("│   │   ├── Stocks")
    print("│   │   │   ├── StockFilters")
    print("│   │   │   ├── StockList")
    print("│   │   │   └── StockCard")
    print("│   │   └── TickerSheet")
    print("│   │       ├── TickerHeader")
    print("│   │       ├── PriceChart")
    print("│   │       ├── TechnicalIndicators")
    print("│   │       └── FundamentalData")
    print("│   └── Footer")
    print("└── Providers")
    print("    ├── QueryClientProvider")
    print("    └── ThemeProvider")

def main():
    """Main function to provide debugging guidance."""
    print("🔧 Assistant de Débogage React Developer Tools")
    print("=" * 50)
    print("")
    
    if len(sys.argv) < 2:
        print("UsageId: python debug_react.py [command]")
        print("")
        print("Commandes disponibles:")
        print("  check     - Vérifier si React DevTools est installé")
        print("  launch    - Lancer l'application avec conseils de débogage")
        print("  issues    - Guide pour les problèmes courants")
        print("  hierarchy - Hiérarchie des composants")
        print("  help      - Afficher cette aide")
        print("")
        return
    
    command = sys.argv[1]
    
    if command == "check":
        check_react_devtools_installed()
    elif command == "launch":
        launch_with_debugging()
    elif command == "issues":
        debug_common_issues()
    elif command == "hierarchy":
        show_component_hierarchy()
    elif command == "help":
        print("UsageId: python debug_react.py [command]")
        print("")
        print("Commandes disponibles:")
        print("  check     - Vérifier si React DevTools est installé")
        print("  launch    - Lancer l'application avec conseils de débogage")
        print("  issues    - Guide pour les problèmes courants")
        print("  hierarchy - Hiérarchie des composants")
        print("  help      - Afficher cette aide")
    else:
        print(f"❌ Commande inconnue: {command}")
        print("Utilisez 'help' pour voir les commandes disponibles")

if __name__ == "__main__":
    main()