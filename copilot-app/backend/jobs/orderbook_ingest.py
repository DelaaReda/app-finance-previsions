"""
OrderBook Ingest Job
Simule/ingère les données de carnet d'ordres (bid/ask)
Author: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77
Task: Créer pipeline pour OrderBook widget
Note: En production, cela nécessiterait une source de données temps réel (WebSocket, API market data)
"""
from datetime import datetime
import logging
from pathlib import Path
import sys
from typing import Dict, Any, List, Optional
import json
import random

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
        data_dir = Path(__file__).parent.parent / "data" / "market"
        data_dir.mkdir(parents=True, exist_ok=True)
        filepath = data_dir / f"{key}.json"
        filepath.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    
    def load_json(key):
        data_dir = Path(__file__).parent.parent / "data" / "market"
        filepath = data_dir / f"{key}.json"
        if not filepath.exists():
            return None
        return json.loads(filepath.read_text())


def generate_orderbook_data(ticker: str, depth: int = 10) -> Dict[str, Any]:
    """
    Génère des données de carnet d'ordres pour un ticker
    
    Args:
        ticker: Ticker symbol
        depth: Nombre de niveaux bid/ask
    
    Returns:
        Dict avec bids, asks, lastPrice, spread
    """
    logger.info(f"Generating orderbook data for {ticker} (depth={depth})")
    
    # Obtenir le prix actuel
    last_price = 100.0  # Default
    if YFINANCE_AVAILABLE:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            last_price = info.get("currentPrice") or info.get("regularMarketPrice") or 100.0
        except Exception as e:
            logger.warning(f"Error fetching price for {ticker}: {e}")
    
    # Générer les bids (achats) - prix < lastPrice
    bids = []
    for i in range(depth):
        price = last_price - (i + 1) * 0.01  # Décrément de $0.01
        quantity = random.randint(100, 10000)  # Quantité aléatoire
        bids.append({
            "price": round(price, 2),
            "quantity": quantity,
        })
    
    # Générer les asks (ventes) - prix > lastPrice
    asks = []
    for i in range(depth):
        price = last_price + (i + 1) * 0.01  # Incrément de $0.01
        quantity = random.randint(100, 10000)  # Quantité aléatoire
        asks.append({
            "price": round(price, 2),
            "quantity": quantity,
        })
    
    # Calculer le spread
    if bids and asks:
        spread = asks[0]["price"] - bids[0]["price"]
        spread_pct = (spread / last_price) * 100 if last_price > 0 else 0
    else:
        spread = 0.02
        spread_pct = 0.02
    
    return {
        "ticker": ticker,
        "bids": bids,
        "asks": asks,
        "lastPrice": round(last_price, 2),
        "spread": round(spread, 2),
        "spreadPct": round(spread_pct, 3),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def run_orderbook_ingest_job(tickers: Optional[List[str]] = None, force: bool = False) -> Dict[str, Any]:
    """
    Job principal pour ingérer les carnets d'ordres
    
    Args:
        tickers: Liste des tickers (défaut: AAPL, MSFT, NVDA, TSLA)
        force: Force le recalcul
    
    Returns:
        Résultat du job
    """
    logger.info("Starting orderbook ingest job...")
    
    if tickers is None:
        tickers = ["AAPL", "MSFT", "NVDA", "TSLA"]
    
    try:
        results = {}
        
        for ticker in tickers:
            orderbook_data = generate_orderbook_data(ticker, depth=10)
            results[ticker] = orderbook_data
            
            # Sauvegarder individuellement
            save_json(f"market/orderbook_{ticker}", orderbook_data, source=["job:orderbook_ingest", "simulated"], version="v1")
        
        # Sauvegarder aussi un fichier global
        save_json("market/orderbook_all", results, source=["job:orderbook_ingest", "aggregated"], version="v1")
        
        result = {
            "status": "completed",
            "tickers_processed": len(tickers),
            "orderbooks_generated": len(results),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": ["orderbook_ingest_job"],
        }
        
        logger.info(f"✅ Orderbook ingest job completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Orderbook ingest job failed: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest orderbook data")
    parser.add_argument("--tickers", type=str, help="Comma-separated tickers (e.g., AAPL,MSFT,NVDA)")
    parser.add_argument("--force", action="store_true", help="Force recalculation")
    args = parser.parse_args()
    
    tickers_list = None
    if args.tickers:
        tickers_list = [t.strip().upper() for t in args.tickers.split(",")]
    
    result = run_orderbook_ingest_job(tickers=tickers_list, force=args.force)
    print(json.dumps(result, indent=2))

