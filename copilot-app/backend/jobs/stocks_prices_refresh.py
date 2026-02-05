"""
Stocks Prices Refresh Job
Calcule et sauvegarde les prix historiques de tous les tickers
Author: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77
Task: Cache-First Architecture - Pré-calculer stocks prices
"""
from datetime import datetime, timedelta
import io
import json
import subprocess
import time
import logging
from pathlib import Path
import sys
from typing import Dict, Any, List
import pandas as pd

# Add backend to path
backend_root = Path(__file__).parent.parent
backend_path = str(backend_root)
src_path = str(backend_root / "src")
# Ensure src takes precedence over legacy backend core package
for p in (backend_path, src_path):
    if p in sys.path:
        sys.path.remove(p)
for p in (backend_path, src_path):
    sys.path.insert(0, p)

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
        
        # Helper: stooq CSV fallback (no auth)
        def _stooq_symbol(sym: str) -> str:
            s = sym.lower()
            mapping = {
                "spy": "spy.us",
                "qqq": "qqq.us",
                "aapl": "aapl.us",
                "msft": "msft.us",
                "googl": "googl.us",
                "goog": "goog.us",
                "amzn": "amzn.us",
                "nvda": "nvda.us",
                "meta": "meta.us",
                "tsla": "tsla.us",
                "brk.b": "brk.b.us",
                "unh": "unh.us",
                "jnj": "jnj.us",
                "v": "v.us",
                "pg": "pg.us",
                "jpm": "jpm.us",
                "ma": "ma.us",
                "hd": "hd.us",
                "dis": "dis.us",
            }
            return mapping.get(s, f"{s}.us")

        def _fetch_stooq_prices(sym: str) -> pd.DataFrame:
            try:
                stooq_sym = _stooq_symbol(sym)
                # Prefer stooq.pl (stooq.com can fail DNS in some environments)
                urls = [
                    f"https://stooq.pl/q/d/l/?s={stooq_sym}&i=d",
                    f"https://stooq.com/q/d/l/?s={stooq_sym}&i=d",
                ]
                # Use curl via subprocess (more reliable in this environment)
                df = pd.DataFrame()
                for url in urls:
                    res = subprocess.run(
                        ["curl", "-sS", url],
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=20,
                    )
                    if res.returncode != 0 or not res.stdout:
                        continue
                    try:
                        df = pd.read_csv(io.StringIO(res.stdout))
                    except Exception:
                        df = pd.DataFrame()
                    if not df.empty:
                        break
                if df.empty or "Date" not in df.columns or "Close" not in df.columns:
                    return pd.DataFrame()
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                df = df.dropna(subset=["Date"]).set_index("Date").sort_index()
                df = df[df.index >= pd.to_datetime(start_date)]
                return df
            except Exception:
                return pd.DataFrame()

        def _fetch_yahoo_chart(sym: str) -> pd.DataFrame:
            """Fallback to Yahoo chart API (avoids yfinance guce redirects)."""
            hosts = ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]
            params = f"range={timeframe}&interval=1d&includePrePost=false&events=div%7Csplit"
            for host in hosts:
                url = f"https://{host}/v8/finance/chart/{sym}?{params}"
                res = subprocess.run(
                    ["curl", "-sS", url],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                if res.returncode != 0 or not res.stdout:
                    continue
                try:
                    js = json.loads(res.stdout)
                except Exception:
                    continue
                result = (js.get("chart", {}).get("result") or [None])[0]
                if not result:
                    continue
                timestamps = result.get("timestamp") or []
                indicators = (result.get("indicators", {}).get("quote") or [{}])[0]
                closes = indicators.get("close") or []
                if not timestamps or not closes:
                    continue
                rows = []
                for ts, close in zip(timestamps, closes):
                    if close is None:
                        continue
                    try:
                        dt = datetime.utcfromtimestamp(int(ts))
                    except Exception:
                        continue
                    rows.append({"Date": dt, "Close": float(close)})
                if not rows:
                    continue
                df = pd.DataFrame(rows).set_index("Date").sort_index()
                df = df[df.index >= pd.to_datetime(start_date)]
                return df
            return pd.DataFrame()

        def _load_stooq_cache(sym: str) -> pd.DataFrame:
            try:
                cache_dir = Path(__file__).resolve().parents[1] / "data" / "price_cache" / "stooq"
                fp = cache_dir / f"{sym}.csv"
                if not fp.exists():
                    return pd.DataFrame()
                df = pd.read_csv(fp)
                if df.empty:
                    return pd.DataFrame()
                date_col = "Date" if "Date" in df.columns else ("Data" if "Data" in df.columns else None)
                close_col = "Close" if "Close" in df.columns else ("Zamkniecie" if "Zamkniecie" in df.columns else None)
                if not date_col or not close_col:
                    return pd.DataFrame()
                if date_col != "Date":
                    df = df.rename(columns={date_col: "Date"})
                if close_col != "Close":
                    df = df.rename(columns={close_col: "Close"})
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                df = df.dropna(subset=["Date"]).set_index("Date").sort_index()
                df = df[df.index >= pd.to_datetime(start_date)]
                return df
            except Exception:
                return pd.DataFrame()

        # Calculer pour tous les tickers
        results = {}
        errors = {}
        
        for ticker in DEFAULT_STOCKS_UNIVERSE:
            try:
                logger.debug(f"Fetching prices for {ticker}...")
                
                df = _load_stooq_cache(ticker)
                if df is None or df.empty:
                    df = get_price_history(ticker, start=start_date, interval="1d")
                if df is None or df.empty:
                    df = _fetch_yahoo_chart(ticker)
                if df is None or df.empty:
                    df = _fetch_stooq_prices(ticker)
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
                time.sleep(0.2)
                
            except Exception as e:
                logger.warning(f"Failed to fetch prices for {ticker}: {e}")
                errors[ticker] = str(e)
                continue
        
        # Sauvegarder (éviter d'écraser un cache existant si aucun résultat)
        if not results:
            cached = load_json("stocks/prices")
            if cached and cached.get("tickers"):
                logger.warning("No fresh prices fetched, keeping existing cache")
                return {
                    "status": "cached",
                    "count": len(cached.get("tickers", {})),
                    "errors_count": len(errors),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }

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
