"""
Adapter unifié pour accès données (scoring).
Wrappe core.market_data, analytics.phase3_macro, ingestion.finnews.
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add src to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.market_data import get_price_history, get_fred_series
from analytics.phase3_macro import get_us_macro_bundle
from ingestion.finnews import run_pipeline


def get_close_series(ticker: str) -> Optional[pd.Series]:
    """
    Retourne série Close nettoyée pour un ticker.
    """
    df = get_price_history(ticker, start=None, interval="1d")
    if df is None or df.empty:
        return None
    return df["Close"].dropna()


def load_macro_forecast_rows(limit: int = 1) -> Dict[str, Any]:
    """
    Retourne snapshot macro actuel via phase3_macro.
    
    Mapping:
    - inflation_yoy: CPI YoY %
    - yield_curve_slope: 10Y - 2Y (bp)
    - unemployment: Taux chômage %
    - recession_prob: Proxy via yield curve < 0
    """
    try:
        bundle = get_us_macro_bundle(start="2020-01-01", monthly=True)
        data = bundle.data
        
        # CPI YoY
        inflation_yoy = None
        if "CPIAUCSL" in data.columns:
            cpi = data["CPIAUCSL"].dropna()
            if len(cpi) >= 12:
                inflation_yoy = float((cpi.iloc[-1] / cpi.iloc[-13] - 1) * 100)
        
        # Yield curve slope
        yield_curve_slope = None
        if "DGS10" in data.columns and "DGS2" in data.columns:
            dgs10 = data["DGS10"].dropna().iloc[-1] if not data["DGS10"].dropna().empty else None
            dgs2 = data["DGS2"].dropna().iloc[-1] if not data["DGS2"].dropna().empty else None
            if dgs10 is not None and dgs2 is not None:
                yield_curve_slope = float(dgs10 - dgs2)
        
        # Unemployment
        unemployment = None
        try:
            unrate = get_fred_series("UNRATE", start="2020-01-01")
            if unrate is not None and not unrate.empty:
                unemployment = float(unrate.iloc[-1])
        except:
            pass
        
        # Recession prob (proxy: yield inversé = +0.5, sinon distance à inversion)
        recession_prob = 0.0
        if yield_curve_slope is not None:
            if yield_curve_slope < 0:
                recession_prob = 0.5 + min(abs(yield_curve_slope) / 100, 0.5)
            else:
                recession_prob = max(0, 0.3 - yield_curve_slope / 100)
        
        return {
            "rows": [{
                "inflation_yoy": inflation_yoy,
                "yield_curve_slope": yield_curve_slope,
                "unemployment": unemployment,
                "recession_prob": float(recession_prob)
            }]
        }
    
    except Exception as e:
        # Fallback vide
        return {
            "rows": [{
                "inflation_yoy": None,
                "yield_curve_slope": None,
                "unemployment": None,
                "recession_prob": 0.0
            }]
        }


def load_news_features(limit: int = 100) -> Dict[str, Any]:
    """
    Retourne features news via finnews pipeline.
    
    Mapping:
    - symbol: ticker extrait (ou None)
    - news_score_mean: score moyen (0..1)
    - hours_since_publish: fraîcheur
    """
    try:
        items = run_pipeline(
            regions=["US", "CA", "INTL"],
            window="last_week",
            query="",
            tgt_ticker=None,
            per_source_cap=None,
            limit=limit
        )
        
        rows = []
        for item in items:
            # Extract ticker (first if multiple)
            tickers = item.get("tickers", [])
            symbol = tickers[0] if tickers else None
            
            # Score moyen (importance * sentiment)
            importance = item.get("importance", 0.5)
            sentiment = item.get("sentiment", 0.0) if item.get("sentiment") is not None else 0.0
            # Normaliser sentiment -1..+1 → 0..1
            sentiment_norm = (sentiment + 1) / 2
            news_score_mean = importance * sentiment_norm
            
            # Fraîcheur
            published = item.get("published", "")
            hours_since = 24.0  # default
            if published:
                try:
                    pub_dt = pd.to_datetime(published)
                    hours_since = (datetime.utcnow() - pub_dt).total_seconds() / 3600
                except:
                    pass
            
            rows.append({
                "symbol": symbol,
                "news_score_mean": float(news_score_mean),
                "hours_since_publish": float(hours_since)
            })
        
        return {"rows": rows}
    
    except Exception as e:
        return {"rows": []}


if __name__ == "__main__":
    # Test the functions
    print("Testing core.data_access functions...")
    
    # Test get_close_series
    try:
        series = get_close_series("SPY")
        if series is not None:
            print(f"✓ get_close_series('SPY'): {len(series)} rows, last value: {series.iloc[-1]:.2f}")
        else:
            print("✗ get_close_series('SPY'): None")
    except Exception as e:
        print(f"✗ get_close_series error: {e}")
    
    # Test load_macro_forecast_rows
    try:
        macro_data = load_macro_forecast_rows()
        print(f"✓ load_macro_forecast_rows(): {len(macro_data['rows'])} rows")
        if macro_data['rows']:
            row = macro_data['rows'][0]
            print(f"  - inflation_yoy: {row.get('inflation_yoy')}")
            print(f"  - yield_curve_slope: {row.get('yield_curve_slope')}")
            print(f"  - unemployment: {row.get('unemployment')}")
    except Exception as e:
        print(f"✗ load_macro_forecast_rows error: {e}")
    
    # Test load_news_features
    try:
        news_data = load_news_features(limit=10)
        print(f"✓ load_news_features(): {len(news_data['rows'])} rows")
    except Exception as e:
        print(f"✗ load_news_features error: {e}")
