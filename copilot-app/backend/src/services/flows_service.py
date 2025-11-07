"""
Flows Service
Service pour exposer les flux de capitaux
Author: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77
"""
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import sys
import logging

# Add backend to path
backend_root = Path(__file__).resolve().parents[3]
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

logger = logging.getLogger(__name__)

try:
    from storage.io import load_json
except ImportError:
    try:
        from storage.base import load_json
    except ImportError:
        logger.warning("storage modules not available")
        def load_json(key):
            data_dir = Path(__file__).resolve().parents[3] / "data" / "flows"
            filepath = data_dir / f"{key}.json"
            if not filepath.exists():
                return None
            import json
            return json.loads(filepath.read_text())


def get_capital_flows() -> Dict[str, Any]:
    """
    Récupère les flux de capitaux depuis le stockage
    
    Returns:
        Dict avec nodes et links ou structure vide
    """
    try:
        flows_data = load_json("flows/capital")
        
        if flows_data:
            # Si c'est un wrapper, extraire les données
            if "data" in flows_data:
                return flows_data["data"]
            elif "payload" in flows_data:
                return flows_data["payload"]
            else:
                return flows_data
        
        # Fallback: structure vide mais valide
        logger.warning("No capital flows found, returning empty structure")
        return {
            "nodes": [],
            "links": [],
            "lookback_days": 30,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }
        
    except Exception as e:
        logger.error(f"Error loading capital flows: {str(e)}")
        return {
            "nodes": [],
            "links": [],
            "lookback_days": 30,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

