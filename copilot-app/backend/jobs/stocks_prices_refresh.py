"""
Stocks Prices Refresh Job
Calcule et sauvegarde les prix historiques de tous les tickers
Author: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77
Task: Cache-First Architecture - Pré-calculer stocks prices
"""
from datetime import datetime, timedelta
import logging
from pathlib import Path
import sys
from typing import Dict, Any, List
import pandas as pd

# Add backend to path
backend_path = str(Path(__file__).parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

logger = logging.getLogger(__name__)

try:
    from storage.io import save_json, load_json
except ImportError:
    logger.warning("storage.io not available, using fallback")
    def save_json(key, payload, source=None, version="v1"):
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


def run_stocks_prices_job(force: bool = False, timeframe: str = "1y") -> Dict[str, Any]:
    """
    Job principal pour calculer et sauvegarder les prix de tous les tickers
    
    Args:
        force: Si True, force le recalcul même si les données sont récentes
        timeframe: Timeframe pour les prix (1y, 6mo, 3mo, etc.)
    
    Returns:
        Résultat du job avec statistiques
    """
    logger.info(f"Starting stocks prices refresh job (timeframe: {timeframe})...")
    
    try:
        from core.market_data import get_price_history
        
        # Liste des tickers par défaut
        DEFAULT_STOCKS_UNIVERSE = [
            "SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META",
            "TSLA", "BRK.B", "UNH", "JNJ", "V", "PG", "JPM", "MA", "HD", "DIS"
        ]
        
        # Convert timeframe to days
        timeframe_map = {
            "1d": 1, "5d": 5, "1mo": 30, "3mo": 90, "6mo": 180,
            "1y": 365, "2y": 730, "5y": 1825
        }
        days_back = timeframe_map.get(timeframe, 365)
        start_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        # Charger depuis cache si disponible et récent
        if not force:
            cached = load_json("stocks/prices")
            if cached:
                freshness = cached.get("freshness")
                if freshness:
                    try:
                        fresh_date = datetime.fromisoformat(freshness.replace("Z", "+00:00").replace("+00:00", ""))
                        age_hours = (datetime.utcnow() - fresh_date.replace(tzinfo=None)).total_seconds() / 3600
                        if age_hours < 1:  # Moins d'1 heure = utiliser cache
                            logger.info(f"Using cached prices (age: {age_hours:.1f}h)")
                            return {
                                "status": "cached",
                                "count": len(cached.get("tickers", {})),
                                "timestamp": datetime.utcnow().isoformat() + "Z",
                            }
                    except Exception:
                        pass  # Continue avec recalcul
        
        # Calculer pour tous les tickers
        results = {}
        errors = {}
        
        for ticker in DEFAULT_STOCKS_UNIVERSE:
            try:
                logger.debug(f"Fetching prices for {ticker}...")
                
                df = get_price_history(ticker, start=start_date, interval="1d")
                if df is None or df.empty:
                    errors[ticker] = "No data"
                    continue
                
                # Extract Close prices as series
                series = df['Close'] if 'Close' in df.columns else df.iloc[:, 0]
                
                # Convert to points (timestamp, value)
                points = [(int(ts.timestamp()), float(val))
                         for ts, val in series.items()
                         if not pd.isna(val)]
                
                # Downsample if needed (max 1000 points)
                if len(points) > 1000:
                    try:
                        from core.downsample import lttb
                        points = lttb(points, threshold=1000)
                    except ImportError:
                        # Si lttb n'est pas disponible, prendre un échantillon
                        step = len(points) // 1000
                        points = points[::max(1, step)]
                
                results[ticker] = {
                    "range": timeframe,
                    "interval": "1d",
                    "points": points,
                    "count": len(points),
                    "start_date": start_date,
                }
                
            except Exception as e:
                logger.warning(f"Failed to fetch prices for {ticker}: {e}")
                errors[ticker] = str(e)
                continue
        
        # Sauvegarder
        payload = {
            "tickers": results,
            "range": timeframe,
            "interval": "1d",
            "errors": errors,
        }
        
        save_json("stocks/prices", payload, source=["job:stocks_prices_refresh"], version="v1")
        
        result = {
            "status": "completed",
            "count": len(results),
            "errors_count": len(errors),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        
        logger.info(f"✅ Stocks prices job completed: {len(results)} tickers, {len(errors)} errors")
        return result
        
    except Exception as e:
        logger.error(f"❌ Stocks prices job failed: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


if __name__ == "__main__":
    import argparse
    import pandas as pd  # Import pour lttb si nécessaire
    parser = argparse.ArgumentParser(description="Refresh stocks prices")
    parser.add_argument("--force", action="store_true", help="Force refresh even if data is recent")
    parser.add_argument("--timeframe", default="1y", help="Timeframe (1y, 6mo, 3mo, etc.)")
    args = parser.parse_args()
    
    result = run_stocks_prices_job(force=args.force, timeframe=args.timeframe)
    print(f"Result: {result}")

