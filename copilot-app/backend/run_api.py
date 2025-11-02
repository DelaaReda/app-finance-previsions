#!/usr/bin/env python3
"""
Script de lancement de l'API FastAPI.
Usage: python run_api.py
"""
import sys
from pathlib import Path

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Lancement de l'API Finance Copilot...")
    print("📍 URL: http://127.0.0.1:8050")
    print("📖 Docs: http://127.0.0.1:8050/docs")
    print()
    
    # Utiliser l'approche avec import string pour éviter les problèmes de reload
    uvicorn.run(
        "api.main:create_app",
        host="127.0.0.1",
        port=8050,
        reload=True,
        factory=True,
        log_level="info"
    )
