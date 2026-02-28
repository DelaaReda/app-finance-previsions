"""
Stocks Metrics Refresh Job
Calcule et sauvegarde les métriques de tous les tickers
Author: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77
Task: Cache-First Architecture - Pré-calculer stocks metrics
"""
from datetime import datetime
import logging
from pathlib import Path
import sys
from typing import Dict, Any, List

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

from core.ticker_normalization import normalize_ticker, normalize_tickers


def run_stocks_metrics_job(force: bool = False) -> Dict[str, Any]:
    """
    Job principal pour calculer et sauvegarder les métriques de tous les tickers
    
    Args:
        force: Si True, force le recalcul même si les données sont récentes
    
    Returns:
        Résultat du job avec statistiques
    """
    logger.info("Starting stocks metrics refresh job...")
    
    try:
        # Import depuis main.py (évite duplication)
        # Note: On doit importer depuis le module API pour accéder à _compute_stock_metrics
        # Pour éviter les imports circulaires, on va utiliser une approche différente
        from core.market_data import get_price_history
        from datetime import timedelta
        
        # Liste des tickers par défaut
        DEFAULT_STOCKS_UNIVERSE = normalize_tickers([
            "SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META",
            "TSLA", "BRK.B", "UNH", "JNJ", "V", "PG", "JPM", "MA", "HD", "DIS"
        ])
        
        # Charger depuis cache si disponible et récent
        if not force:
            cached = load_json("stocks/metrics")
            if cached:
                freshness = cached.get("freshness")
                if freshness:
                    try:
                        from datetime import datetime
                        fresh_date = datetime.fromisoformat(freshness.replace("Z", "+00:00").replace("+00:00", ""))
                        age_hours = (datetime.utcnow() - fresh_date.replace(tzinfo=None)).total_seconds() / 3600
                        if age_hours < 6:  # Moins de 6 heures = utiliser cache
                            logger.info(f"Using cached metrics (age: {age_hours:.1f}h)")
                            return {
                                "status": "cached",
                                "count": len(cached.get("metrics", {})),
                                "timestamp": datetime.utcnow().isoformat() + "Z",
                            }
                    except Exception:
                        pass  # Continue avec recalcul
        
        # Calculer pour tous les tickers
        metrics = {}
        errors = {}
        
        for ticker in DEFAULT_STOCKS_UNIVERSE:
            try:
                normalized_ticker = normalize_ticker(ticker)
                if not normalized_ticker:
                    continue
                logger.debug(f"Computing metrics for {ticker}...")
                
                # Calculer métriques de base
                ticker_upper = normalized_ticker
                lookback_start = (datetime.utcnow() - timedelta(days=120)).strftime("%Y-%m-%d")
                df_prices = get_price_history(ticker_upper, start=lookback_start, interval="1d")
                
                if df_prices is None or df_prices.empty or ("Close" not in df_prices.columns and len(df_prices.columns) == 0):
                    errors[ticker_upper] = "No price data"
                    continue
                
                # Extraire métriques de base
                last_price = float(df_prices['Close'].iloc[-1]) if 'Close' in df_prices.columns else None
                change_1d = None
                momentum_30d = None
                
                if len(df_prices) > 1 and 'Close' in df_prices.columns:
                    prev_close = float(df_prices['Close'].iloc[-2])
                    if prev_close != 0:
                        change_1d = ((last_price - prev_close) / prev_close) * 100
                
                if len(df_prices) > 30 and 'Close' in df_prices.columns:
                    base_price = float(df_prices['Close'].iloc[-30])
                    if base_price != 0:
                        momentum_30d = ((last_price - base_price) / base_price) * 100
                
                # Calculer risque (volatilité simple)
                risk = None
                if len(df_prices) > 20 and 'Close' in df_prices.columns:
                    returns = df_prices['Close'].pct_change().dropna()
                    if len(returns) > 0:
                        risk = float(returns.std() * (252 ** 0.5)) * 100  # Annualized volatility
                
                metrics[ticker_upper] = {
                    "ticker": ticker_upper,
                    "price": last_price,
                    "change_1d": change_1d,
                    "momentum_30d": momentum_30d,
                    "risk": risk,
                    "score": None,  # À calculer si scoring disponible
                    "quality": None,  # À calculer si scoring disponible
                }
                
            except Exception as e:
                logger.warning(f"Failed to compute metrics for {ticker}: {e}")
                errors[normalize_ticker(ticker) or ticker] = str(e)
                continue
        
        # Sauvegarder
        payload = {
            "metrics": metrics,
            "tickers": list(metrics.keys()),
            "count": len(metrics),
            "errors": errors,
        }
        
        save_json("stocks/metrics", payload, source=["job:stocks_metrics_refresh"], version="v1")
        
        result = {
            "status": "completed",
            "count": len(metrics),
            "errors_count": len(errors),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        
        logger.info(f"✅ Stocks metrics job completed: {len(metrics)} tickers, {len(errors)} errors")
        return result
        
    except Exception as e:
        logger.error(f"❌ Stocks metrics job failed: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Refresh stocks metrics")
    parser.add_argument("--force", action="store_true", help="Force refresh even if data is recent")
    args = parser.parse_args()
    
    result = run_stocks_metrics_job(force=args.force)
    print(f"Result: {result}")
