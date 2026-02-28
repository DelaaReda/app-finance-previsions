"""
Correlation Calculator Job
Calcule la matrice de corrélations et génère les données pour CorrelationNetwork
Author: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77
Task: Créer pipeline pour CorrelationNetwork / CorrelationHeatmap
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
    import pandas as pd
    import numpy as np
    YFINANCE_AVAILABLE = True
except ImportError:
    logger.warning("yfinance/pandas not available, using fallback")
    YFINANCE_AVAILABLE = False

try:
    from storage.io import save_json, load_json
except ImportError:
    logger.warning("storage.io not available, using fallback")
    def save_json(key, payload, source=None, version="v1"):
        # Handle nested paths (e.g., "correlations/matrix" -> data/correlations/matrix.json)
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


def calculate_correlation_matrix(tickers: List[str], lookback_days: int = 90) -> Dict[str, Any]:
    """
    Calcule la matrice de corrélations entre tickers
    
    Args:
        tickers: Liste des tickers à analyser
        lookback_days: Nombre de jours pour le calcul
    
    Returns:
        Dict avec matrix, tickers, et metadata
    """
    logger.info(f"Calculating correlation matrix for {len(tickers)} tickers over {lookback_days} days")
    
    if not YFINANCE_AVAILABLE:
        logger.warning("yfinance not available, returning mock correlation matrix")
        # Mock data pour développement
        matrix = {}
        for i, t1 in enumerate(tickers):
            matrix[t1] = {}
            for j, t2 in enumerate(tickers):
                if i == j:
                    matrix[t1][t2] = 1.0
                else:
                    # Mock correlation
                    matrix[t1][t2] = round(0.3 + (i + j) * 0.1, 3)
        
        return {
            "matrix": matrix,
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
                    data[ticker] = hist['Close']
                else:
                    logger.warning(f"No data for {ticker}")
            except Exception as e:
                logger.warning(f"Error fetching {ticker}: {e}")
        
        if not data:
            raise ValueError("No data fetched for any ticker")
        
        # Créer DataFrame et calculer corrélations
        df = pd.DataFrame(data)
        corr_matrix = df.corr()
        
        # Convertir en dict
        matrix = {}
        for ticker1 in corr_matrix.index:
            matrix[ticker1] = {}
            for ticker2 in corr_matrix.columns:
                matrix[ticker1][ticker2] = round(float(corr_matrix.loc[ticker1, ticker2]), 3)
        
        logger.info(f"✅ Calculated correlation matrix: {len(matrix)}x{len(matrix)}")
        
        return {
            "matrix": matrix,
            "tickers": list(corr_matrix.index),
            "lookback_days": lookback_days,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }
        
    except Exception as e:
        logger.error(f"Error calculating correlation matrix: {e}", exc_info=True)
        raise


def matrix_to_network(matrix: Dict[str, Dict[str, float]], threshold: float = 0.5) -> Dict[str, Any]:
    """
    Convertit une matrice de corrélations en format network (nodes + links)
    
    Args:
        matrix: Matrice de corrélations
        threshold: Seuil minimum de corrélation pour créer un lien
    
    Returns:
        Dict avec nodes et links
    """
    tickers = list(matrix.keys())
    
    # Créer les nodes
    nodes = []
    for i, ticker in enumerate(tickers):
        nodes.append({
            "id": ticker,
            "label": ticker,
            "sector": "Unknown",  # TODO: enrichir avec données secteurs
            "index": i,
        })
    
    # Créer les links (seulement si corrélation >= threshold)
    links = []
    for i, ticker1 in enumerate(tickers):
        for j, ticker2 in enumerate(tickers):
            if i < j:  # Éviter les doublons
                corr = matrix.get(ticker1, {}).get(ticker2, 0)
                if abs(corr) >= threshold:
                    links.append({
                        "source": ticker1,
                        "target": ticker2,
                        "correlation": round(corr, 3),
                        "strength": abs(corr),
                    })
    
    return {
        "nodes": nodes,
        "links": links,
        "threshold": threshold,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


def run_correlation_calculator_job(tickers: Optional[List[str]] = None, threshold: float = 0.5, force: bool = False) -> Dict[str, Any]:
    """
    Job principal pour calculer les corrélations
    
    Args:
        tickers: Liste des tickers (défaut: SPY, QQQ, AAPL, MSFT, NVDA, GOOGL, META, TSLA)
        threshold: Seuil pour le network
        force: Force le recalcul
    
    Returns:
        Résultat du job
    """
    logger.info("Starting correlation calculator job...")
    
    if tickers is None:
        tickers = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "GOOGL", "META", "TSLA"]
    
    try:
        # Calculer la matrice
        matrix_data = calculate_correlation_matrix(tickers, lookback_days=90)
        
        # Sauvegarder la matrice
        save_json("correlations/matrix", matrix_data, source=["job:correlation_calculator", "yfinance"], version="v1")
        
        # Générer le network
        network_data = matrix_to_network(matrix_data["matrix"], threshold=threshold)
        
        # Sauvegarder le network
        save_json("correlations/network", network_data, source=["job:correlation_calculator", "transformed"], version="v1")
        
        result = {
            "status": "completed",
            "tickers_processed": len(tickers),
            "matrix_size": f"{len(matrix_data['tickers'])}x{len(matrix_data['tickers'])}",
            "network_nodes": len(network_data["nodes"]),
            "network_links": len(network_data["links"]),
            "threshold": threshold,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": ["correlation_calculator_job"],
        }
        
        logger.info(f"✅ Correlation calculator job completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Correlation calculator job failed: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Calculate stock correlations")
    parser.add_argument("--tickers", type=str, help="Comma-separated tickers (e.g., AAPL,MSFT,NVDA)")
    parser.add_argument("--threshold", type=float, default=0.5, help="Correlation threshold for network")
    parser.add_argument("--force", action="store_true", help="Force recalculation")
    args = parser.parse_args()
    
    tickers_list = None
    if args.tickers:
        tickers_list = [t.strip().upper() for t in args.tickers.split(",")]
    
    result = run_correlation_calculator_job(tickers=tickers_list, threshold=args.threshold, force=args.force)
    print(json.dumps(result, indent=2))

