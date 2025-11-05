#!/usr/bin/env python3
"""
Script de lancement de l'API FastAPI.
Usage: python run_api.py
"""
import sys
from pathlib import Path

# Ajouter le répertoire backend racine et src au path pour permettre les imports corrects
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))  # Ajoute le répertoire backend lui-même
sys.path.insert(0, str(backend_dir / "src"))  # Ajoute le répertoire src pour modules imbriqués

# Définir explicitement PYTHONPATH pour que tous les imports fonctionnent correctement
import os
os.environ['PYTHONPATH'] = str(backend_dir) + ':' + str(backend_dir / "src")

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Lancement de l'API Finance Copilot...")
    print("📍 URL: http://127.0.0.1:8050")
    print("📖 Docs: http://127.0.0.1:8050/docs")
    print()
    
    # Utiliser l'approche avec import string pour éviter les problèmes de reload
    # Ajouter PYTHONPATH au contexte d'exécution
    uvicorn.run(
        "api.main:create_app",
        host="127.0.0.1",
        port=8050,
        reload=True,
        factory=True,
        log_level="info"
    )
