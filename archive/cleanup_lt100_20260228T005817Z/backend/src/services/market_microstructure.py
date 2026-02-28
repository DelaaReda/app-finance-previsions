"""
Market Microstructure Service
Service pour exposer les données de microstructure de marché (orderbook)
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
            data_dir = Path(__file__).resolve().parents[3] / "data" / "market"
            filepath = data_dir / f"{key}.json"
            if not filepath.exists():
                return None
            import json
            return json.loads(filepath.read_text())


def get_orderbook(ticker: str) -> Dict[str, Any]:
    """
    Récupère le carnet d'ordres pour un ticker
    
    Args:
        ticker: Ticker symbol
    
    Returns:
        Dict avec bids, asks, lastPrice, spread
    """
    try:
        orderbook_data = load_json(f"market/orderbook_{ticker}")
        
        if orderbook_data:
            # Si c'est un wrapper, extraire les données
            if "data" in orderbook_data:
                return orderbook_data["data"]
            elif "payload" in orderbook_data:
                return orderbook_data["payload"]
            else:
                return orderbook_data
        
        # Fallback: structure vide mais valide
        logger.warning(f"No orderbook data found for {ticker}, returning empty structure")
        return {
            "ticker": ticker,
            "bids": [],
            "asks": [],
            "lastPrice": 0.0,
            "spread": 0.0,
            "spreadPct": 0.0,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        
    except Exception as e:
        logger.error(f"Error loading orderbook for {ticker}: {str(e)}")
        return {
            "ticker": ticker,
            "bids": [],
            "asks": [],
            "lastPrice": 0.0,
            "spread": 0.0,
            "spreadPct": 0.0,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

