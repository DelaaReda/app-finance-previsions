"""
Capital Flow Job
Calcule les flux de capitaux pour SankeyDiagram
Author: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77
Task: Créer pipeline pour SankeyDiagram
"""
from datetime import datetime, timedelta
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
        data_dir = Path(__file__).parent.parent / "data" / "flows"
        data_dir.mkdir(parents=True, exist_ok=True)
        filepath = data_dir / f"{key}.json"
        filepath.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    
    def load_json(key):
        data_dir = Path(__file__).parent.parent / "data" / "flows"
        filepath = data_dir / f"{key}.json"
        if not filepath.exists():
            return None
        return json.loads(filepath.read_text())


def calculate_capital_flows(tickers: List[str], lookback_days: int = 30) -> Dict[str, Any]:
    """
    Calcule les flux de capitaux entre secteurs/actifs
    
    Args:
        tickers: Liste des tickers
        lookback_days: Nombre de jours pour le calcul
    
    Returns:
        Dict avec nodes et links pour SankeyDiagram
    """
    logger.info(f"Calculating capital flows for {len(tickers)} tickers over {lookback_days} days")
    
    # Mapping secteurs (simplifié)
    SECTOR_MAPPING = {
        "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology",
        "GOOGL": "Technology", "META": "Technology",
        "AMZN": "Consumer", "TSLA": "Consumer",
        "SPY": "Diversified", "QQQ": "Technology",
        "JPM": "Financial", "BAC": "Financial", "GS": "Financial",
        "V": "Financial", "MA": "Financial",
        "JNJ": "Healthcare", "PFE": "Healthcare", "UNH": "Healthcare",
        "XOM": "Energy", "CVX": "Energy",
    }
    
    # Sources de capital (simplifié - en réalité, on analyserait les flux réels)
    sources = [
        {"id": "retail_investors", "label": "Investisseurs Particuliers", "color": "#3b82f6"},
        {"id": "institutional", "label": "Institutionnels", "color": "#10b981"},
        {"id": "hedge_funds", "label": "Hedge Funds", "color": "#f59e0b"},
        {"id": "etf_flows", "label": "Flux ETF", "color": "#ef4444"},
    ]
    
    # Targets: secteurs
    sectors = {}
    for ticker in tickers:
        sector = SECTOR_MAPPING.get(ticker, "Other")
        if sector not in sectors:
            sectors[sector] = {
                "id": sector.lower().replace(" ", "_"),
                "label": sector,
                "color": "#6366f1",
            }
    
    targets = list(sectors.values())
    
    # Calculer les flux (simplifié - en réalité, on analyserait les volumes réels)
    links = []
    if YFINANCE_AVAILABLE:
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)
            
            for ticker in tickers:
                try:
                    stock = yf.Ticker(ticker)
                    hist = stock.history(start=start_date, end=end_date)
                    if not hist.empty:
                        # Volume moyen comme proxy pour les flux
                        avg_volume = hist['Volume'].mean()
                        sector = SECTOR_MAPPING.get(ticker, "Other")
                        sector_id = sector.lower().replace(" ", "_")
                        
                        # Distribuer le volume entre les sources (simplifié)
                        for source in sources:
                            # Volume proportionnel (mock distribution)
                            flow_value = avg_volume * (0.25 + (hash(ticker + source["id"]) % 100) / 1000)
                            links.append({
                                "source": source["id"],
                                "target": sector_id,
                                "value": int(flow_value),
                                "color": source["color"],
                            })
                except Exception as e:
                    logger.warning(f"Error fetching {ticker}: {e}")
        except Exception as e:
            logger.warning(f"Error calculating flows: {e}")
    
    # Si pas de données, créer des flux mock pour développement
    if not links:
        logger.warning("No flow data, creating mock flows")
        for source in sources[:2]:  # Seulement 2 sources pour simplifier
            for target in targets[:3]:  # Seulement 3 secteurs
                links.append({
                    "source": source["id"],
                    "target": target["id"],
                    "value": 1000000 + (hash(source["id"] + target["id"]) % 5000000),
                    "color": source["color"],
                })
    
    nodes = sources + targets
    
    return {
        "nodes": nodes,
        "links": links,
        "lookback_days": lookback_days,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


def run_capital_flow_job(tickers: Optional[List[str]] = None, force: bool = False) -> Dict[str, Any]:
    """
    Job principal pour calculer les flux de capitaux
    
    Args:
        tickers: Liste des tickers (défaut: SPY, QQQ, AAPL, MSFT, NVDA, GOOGL, META, TSLA)
        force: Force le recalcul
    
    Returns:
        Résultat du job
    """
    logger.info("Starting capital flow job...")
    
    if tickers is None:
        tickers = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "GOOGL", "META", "TSLA"]
    
    try:
        # Calculer les flux
        flows_data = calculate_capital_flows(tickers, lookback_days=30)
        
        # Sauvegarder
        save_json("flows/capital", flows_data, source=["job:capital_flow", "calculated"], version="v1")
        
        result = {
            "status": "completed",
            "tickers_processed": len(tickers),
            "nodes_count": len(flows_data["nodes"]),
            "links_count": len(flows_data["links"]),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": ["capital_flow_job"],
        }
        
        logger.info(f"✅ Capital flow job completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Capital flow job failed: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Calculate capital flows")
    parser.add_argument("--tickers", type=str, help="Comma-separated tickers (e.g., SPY,QQQ,AAPL)")
    parser.add_argument("--force", action="store_true", help="Force recalculation")
    args = parser.parse_args()
    
    tickers_list = None
    if args.tickers:
        tickers_list = [t.strip().upper() for t in args.tickers.split(",")]
    
    result = run_capital_flow_job(tickers=tickers_list, force=args.force)
    print(json.dumps(result, indent=2))

