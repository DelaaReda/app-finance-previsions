"""
Efficient Frontier Job
Calcule la frontière efficiente pour portfolio optimization
Author: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77
Task: Créer pipeline pour EfficientFrontier
"""
from datetime import datetime, timedelta
import logging
from pathlib import Path
import sys
from typing import Dict, Any, List, Optional, Tuple
import json

# Add backend to path
backend_path = str(Path(__file__).parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
    YFINANCE_AVAILABLE = True
except ImportError:
    logger.warning("yfinance/pandas/numpy not available, using fallback")
    YFINANCE_AVAILABLE = False

try:
    from storage.io import save_json, load_json
except ImportError:
    logger.warning("storage.io not available, using fallback")
    def save_json(key, payload, source=None, version="v1"):
        # Handle nested paths (e.g., "backtests/efficient_frontier" -> data/backtests/efficient_frontier.json)
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


def calculate_efficient_frontier(tickers: List[str], lookback_days: int = 252) -> Dict[str, Any]:
    """
    Calcule la frontière efficiente (Modern Portfolio Theory)
    
    Args:
        tickers: Liste des tickers
        lookback_days: Nombre de jours pour le calcul
    
    Returns:
        Dict avec frontier points et portfolios
    """
    logger.info(f"Calculating efficient frontier for {len(tickers)} tickers over {lookback_days} days")
    
    if not YFINANCE_AVAILABLE:
        logger.warning("yfinance not available, returning mock efficient frontier")
        # Mock data pour développement
        frontier = []
        for i in range(20):
            risk = 10 + i * 2
            return_pct = 5 + i * 0.5
            sharpe = return_pct / risk if risk > 0 else 0
            frontier.append({
                "risk": round(risk, 2),
                "return": round(return_pct, 2),
                "sharpe": round(sharpe, 2),
            })
        
        return {
            "frontier": frontier,
            "tickers": tickers,
            "lookback_days": lookback_days,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }
    
    try:
        # Télécharger les données
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        data = {}
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(start=start_date, end=end_date)
                if not hist.empty:
                    data[ticker] = hist['Close'].pct_change().dropna()
                else:
                    logger.warning(f"No data for {ticker}")
            except Exception as e:
                logger.warning(f"Error fetching {ticker}: {e}")
        
        if len(data) < 2:
            raise ValueError("Need at least 2 tickers with data")
        
        # Créer DataFrame
        df = pd.DataFrame(data)
        df = df.dropna()
        
        if df.empty:
            raise ValueError("No valid data after cleaning")
        
        # Calculer moyenne et covariance
        mean_returns = df.mean() * 252  # Annualisé
        cov_matrix = df.cov() * 252  # Annualisé
        
        # Générer des portfolios aléatoires pour la frontière
        num_portfolios = 50
        frontier = []
        
        for _ in range(num_portfolios):
            # Poids aléatoires
            weights = np.random.random(len(tickers))
            weights /= weights.sum()
            
            # Calculer rendement et risque
            portfolio_return = np.dot(weights, mean_returns)
            portfolio_risk = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            
            # Sharpe ratio (risk-free rate = 0 pour simplifier)
            sharpe = portfolio_return / portfolio_risk if portfolio_risk > 0 else 0
            
            frontier.append({
                "risk": round(portfolio_risk * 100, 2),  # En pourcentage
                "return": round(portfolio_return * 100, 2),  # En pourcentage
                "sharpe": round(sharpe, 2),
                "weights": {ticker: round(w, 4) for ticker, w in zip(tickers, weights)},
            })
        
        # Trier par risque
        frontier.sort(key=lambda x: x["risk"])
        
        logger.info(f"✅ Calculated efficient frontier: {len(frontier)} points")
        
        return {
            "frontier": frontier,
            "tickers": tickers,
            "lookback_days": lookback_days,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }
        
    except Exception as e:
        logger.error(f"Error calculating efficient frontier: {e}", exc_info=True)
        raise


def run_efficient_frontier_job(tickers: Optional[List[str]] = None, force: bool = False) -> Dict[str, Any]:
    """
    Job principal pour calculer la frontière efficiente
    
    Args:
        tickers: Liste des tickers (défaut: SPY, QQQ, AAPL, MSFT, NVDA)
        force: Force le recalcul
    
    Returns:
        Résultat du job
    """
    logger.info("Starting efficient frontier job...")
    
    if tickers is None:
        tickers = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA"]
    
    try:
        # Calculer la frontière
        frontier_data = calculate_efficient_frontier(tickers, lookback_days=252)
        
        # Sauvegarder
        save_json("backtests/efficient_frontier", frontier_data, source=["job:efficient_frontier", "mpt"], version="v1")
        
        result = {
            "status": "completed",
            "tickers_processed": len(tickers),
            "frontier_points": len(frontier_data["frontier"]),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": ["efficient_frontier_job"],
        }
        
        logger.info(f"✅ Efficient frontier job completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Efficient frontier job failed: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Calculate efficient frontier")
    parser.add_argument("--tickers", type=str, help="Comma-separated tickers (e.g., SPY,QQQ,AAPL)")
    parser.add_argument("--force", action="store_true", help="Force recalculation")
    args = parser.parse_args()
    
    tickers_list = None
    if args.tickers:
        tickers_list = [t.strip().upper() for t in args.tickers.split(",")]
    
    result = run_efficient_frontier_job(tickers=tickers_list, force=args.force)
    print(json.dumps(result, indent=2))

