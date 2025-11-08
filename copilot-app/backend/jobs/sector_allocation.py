"""
Sector Allocation Job
Calcule l'allocation par secteur pour SectorWheel et TreemapChart
Author: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77
Task: Créer pipeline pour SectorWheel / TreemapChart
"""
from datetime import datetime
import logging
from pathlib import Path
import sys
from typing import Dict, Any, List, Optional
import json

# Add backend to path
backend_path = str(Path(__file__).parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    logger.warning("yfinance not available, using fallback")
    YFINANCE_AVAILABLE = False

try:
    from storage.io import save_json, load_json
except ImportError:
    logger.warning("storage.io not available, using fallback")
    def save_json(key, payload, source=None, version="v1"):
        # Handle nested paths (e.g., "stocks/sectors" -> data/stocks/sectors.json)
        data_dir = Path(__file__).parent.parent / "data"
        filepath = data_dir / f"{key}.json"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        import json
        final_payload = dict(payload)
        final_payload["freshness"] = datetime.utcnow().isoformat() + "Z"
        final_payload["source"] = source or []
        final_payload["version"] = version
        filepath.write_text(json.dumps(final_payload, ensure_ascii=False, indent=2))
    
    def load_json(key):
        data_dir = Path(__file__).parent.parent / "data"
        filepath = data_dir / f"{key}.json"
        if not filepath.exists():
            return None
        import json
        return json.loads(filepath.read_text())


# Mapping secteurs (simplifié, à enrichir)
SECTOR_MAPPING = {
    "AAPL": "Technology",
    "MSFT": "Technology",
    "NVDA": "Technology",
    "GOOGL": "Technology",
    "META": "Technology",
    "AMZN": "Consumer Cyclical",
    "TSLA": "Consumer Cyclical",
    "SPY": "Diversified",
    "QQQ": "Technology",
    "IBM": "Technology",
    "JPM": "Financial Services",
    "BAC": "Financial Services",
    "GS": "Financial Services",
    "V": "Financial Services",
    "MA": "Financial Services",
    "JNJ": "Healthcare",
    "PFE": "Healthcare",
    "UNH": "Healthcare",
    "XOM": "Energy",
    "CVX": "Energy",
}


def calculate_sector_allocation(tickers: List[str]) -> Dict[str, Any]:
    """
    Calcule l'allocation par secteur basée sur les tickers
    
    Args:
        tickers: Liste des tickers
    
    Returns:
        Dict avec allocation par secteur
    """
    logger.info(f"Calculating sector allocation for {len(tickers)} tickers")
    
    # Grouper par secteur
    sector_weights = {}
    sector_tickers = {}
    
    for ticker in tickers:
        sector = SECTOR_MAPPING.get(ticker, "Other")
        
        if sector not in sector_weights:
            sector_weights[sector] = 0
            sector_tickers[sector] = []
        
        # Poids égal pour chaque ticker (à améliorer avec market cap)
        sector_weights[sector] += 1.0 / len(tickers)
        sector_tickers[sector].append(ticker)
    
    # Convertir en format pour visualisation
    sectors_data = []
    for sector, weight in sector_weights.items():
        sectors_data.append({
            "id": sector.lower().replace(" ", "_"),
            "label": sector,
            "value": round(weight * 100, 2),  # Pourcentage
            "weight": round(weight, 4),
            "tickers": sector_tickers[sector],
            "count": len(sector_tickers[sector]),
        })
    
    # Trier par poids décroissant
    sectors_data.sort(key=lambda x: x["value"], reverse=True)
    
    return {
        "sectors": sectors_data,
        "total_tickers": len(tickers),
        "total_sectors": len(sectors_data),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


def run_sector_allocation_job(tickers: Optional[List[str]] = None, force: bool = False) -> Dict[str, Any]:
    """
    Job principal pour calculer l'allocation par secteur
    
    Args:
        tickers: Liste des tickers (défaut: SPY, QQQ, AAPL, MSFT, NVDA, GOOGL, META, TSLA)
        force: Force le recalcul
    
    Returns:
        Résultat du job
    """
    logger.info("Starting sector allocation job...")
    
    if tickers is None:
        tickers = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "GOOGL", "META", "TSLA"]
    
    try:
        # Calculer l'allocation
        allocation_data = calculate_sector_allocation(tickers)
        
        # Sauvegarder
        save_json("stocks/sectors", allocation_data, source=["job:sector_allocation", "calculated"], version="v1")
        
        result = {
            "status": "completed",
            "tickers_processed": len(tickers),
            "sectors_count": allocation_data["total_sectors"],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": ["sector_allocation_job"],
        }
        
        logger.info(f"✅ Sector allocation job completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Sector allocation job failed: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Calculate sector allocation")
    parser.add_argument("--tickers", type=str, help="Comma-separated tickers (e.g., AAPL,MSFT,NVDA)")
    parser.add_argument("--force", action="store_true", help="Force recalculation")
    args = parser.parse_args()
    
    tickers_list = None
    if args.tickers:
        tickers_list = [t.strip().upper() for t in args.tickers.split(",")]
    
    result = run_sector_allocation_job(tickers=tickers_list, force=args.force)
    print(json.dumps(result, indent=2))

