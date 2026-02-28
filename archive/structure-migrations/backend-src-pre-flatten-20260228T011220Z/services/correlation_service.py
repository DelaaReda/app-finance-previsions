"""
Correlation Service
Service pour exposer les données de corrélations (matrix et network)
Author: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77
"""
from typing import Dict, Any
from pathlib import Path
import sys
import logging

# Add backend to path
backend_root = Path(__file__).resolve().parents[3]
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

logger = logging.getLogger(__name__)

try:
    from services.service_standard import utc_now_iso, unwrap_storage_payload
except Exception:  # pragma: no cover
    from src.services.service_standard import utc_now_iso, unwrap_storage_payload  # type: ignore

try:
    from storage.io import load_json
except ImportError:
    try:
        from storage.base import load_json
    except ImportError:
        logger.warning("storage modules not available")
        def load_json(key):
            data_dir = Path(__file__).resolve().parents[3] / "data" / "correlations"
            filepath = data_dir / f"{key}.json"
            if not filepath.exists():
                return None
            import json
            return json.loads(filepath.read_text())


def get_correlation_matrix() -> Dict[str, Any]:
    """
    Récupère la matrice de corrélations
    
    Returns:
        Dict avec la matrice ou structure vide
    """
    try:
        matrix_data = unwrap_storage_payload(load_json("correlations/matrix"))
        if matrix_data:
            return matrix_data
        
        # Fallback: structure vide mais valide
        logger.warning("No correlation matrix found, returning empty structure")
        return {
            "matrix": {},
            "tickers": [],
            "lookback_days": 90,
            "generated_at": utc_now_iso(),
        }
        
    except Exception as e:
        logger.error(f"Error loading correlation matrix: {str(e)}")
        return {
            "matrix": {},
            "tickers": [],
            "lookback_days": 90,
            "generated_at": utc_now_iso(),
        }


def get_correlation_network(threshold: float = 0.5) -> Dict[str, Any]:
    """
    Récupère le network de corrélations
    
    Args:
        threshold: Seuil de corrélation minimum
    
    Returns:
        Dict avec nodes et links
    """
    try:
        network_data = unwrap_storage_payload(load_json("correlations/network"))
        
        if network_data:
            data = dict(network_data) if isinstance(network_data, dict) else network_data
            
            # Filtrer par threshold si nécessaire
            if isinstance(data, dict) and data.get("threshold", 0) != threshold:
                # Re-filtrer les links
                links = [l for l in data.get("links", []) if abs(l.get("correlation", 0)) >= threshold]
                data["links"] = links
                data["threshold"] = threshold
            
            return data
        
        # Fallback: structure vide mais valide
        logger.warning("No correlation network found, returning empty structure")
        return {
            "nodes": [],
            "links": [],
            "threshold": threshold,
            "generated_at": utc_now_iso(),
        }
        
    except Exception as e:
        logger.error(f"Error loading correlation network: {str(e)}")
        return {
            "nodes": [],
            "links": [],
            "threshold": threshold,
            "generated_at": utc_now_iso(),
        }
