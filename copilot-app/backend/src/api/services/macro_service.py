# src/api/services/macro_service.py
"""
Macro service facade - wraps analytics/phase3_macro.py and core/market_data.py
"""
from __future__ import annotations

import hashlib
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any

import pandas as pd

from core.market_data import get_fred_series
from api.schemas import (
    MacroSeries, DataPoint, TraceMetadata,
    MacroOverviewData, MacroSnapshotData, MacroIndicatorsData
)

# Try to import phase3 functions
try:
    from analytics.phase3_macro import (
        fetch_fred_series,
        get_us_macro_bundle,
        macro_nowcast,
        macro_regime
    )
    HAS_PHASE3 = True
except ImportError:
    HAS_PHASE3 = False


# FRED series metadata
FRED_SERIES_INFO = {
    "UNRATE": {"name": "Unemployment Rate", "unit": "Percent"},
    "CPIAUCSL": {"name": "Consumer Price Index", "unit": "Index 1982-84=100"},
    "DFF": {"name": "Federal Funds Rate", "unit": "Percent"},
    "VIXCLS": {"name": "CBOE Volatility Index", "unit": "Index"},
    "DGS10": {"name": "10-Year Treasury Yield", "unit": "Percent"},
    "DGS2": {"name": "2-Year Treasury Yield", "unit": "Percent"},
    "T10Y2Y": {"name": "10Y-2Y Treasury Spread", "unit": "Percent"},
    "DEXUSEU": {"name": "USD/EUR Exchange Rate", "unit": "USD per EUR"},
    "DCOILWTICO": {"name": "WTI Crude Oil", "unit": "Dollars per Barrel"},
    "INDPRO": {"name": "Industrial Production Index", "unit": "Index 2017=100"},
}

DEFAULT_SERIES = ["UNRATE", "CPIAUCSL", "DFF", "VIXCLS", "DGS10", "DGS2"]


def _hash_data(data: Any) -> str:
    """Generate SHA256 hash of data."""
    content = str(data).encode('utf-8')
    return hashlib.sha256(content).hexdigest()[:32]


def _create_trace(source: str, asof: date, data: Any) -> TraceMetadata:
    """Create trace metadata."""
    return TraceMetadata(
        created_at=datetime.utcnow(),
        source=source,
        asof_date=asof,
        hash=_hash_data(data)
    )


def _parse_range(range_str: str) -> Optional[str]:
    """Convert range string to start date."""
    today = datetime.now()
    ranges = {
        "1m": today - timedelta(days=30),
        "3m": today - timedelta(days=90),
        "6m": today - timedelta(days=180),
        "1y": today - timedelta(days=365),
        "2y": today - timedelta(days=730),
        "3y": today - timedelta(days=1095),
        "5y": today - timedelta(days=1825),
        "10y": today - timedelta(days=3650),
        "all": None
    }
    start = ranges.get(range_str)
    return start.strftime("%Y-%m-%d") if start else None


def get_macro_overview(range_str: str = "5y", series_ids: Optional[str] = None) -> MacroOverviewData:
    """
    Get macro overview with specified series.
    
    Args:
        range_str: Time range (1m, 3m, 6m, 1y, 2y, 3y, 5y, 10y, all)
        series_ids: Comma-separated FRED series IDs or None for defaults
    
    Returns:
        MacroOverviewData with time series
    """
    # Parse series IDs
    if series_ids:
        series_list = [s.strip() for s in series_ids.split(",")]
    else:
        series_list = DEFAULT_SERIES
    
    # Get start date
    start_date = _parse_range(range_str)
    
    # Fetch all series
    all_series = []
    for series_id in series_list:
        try:
            # Fetch series
            df = get_fred_series(series_id, start=start_date)
            
            if df.empty:
                continue
            
            # Convert to data points
            values = [
                DataPoint(timestamp=idx.to_pydatetime(), value=float(val))
                for idx, val in df[series_id].items()
                if pd.notna(val)
            ]
            
            if not values:
                continue
            
            # Get metadata
            info = FRED_SERIES_INFO.get(series_id, {})
            name = info.get("name", series_id)
            unit = info.get("unit")
            
            # Latest value
            latest_val = float(df[series_id].iloc[-1])
            latest_date = df.index[-1].date()
            latest = {"value": latest_val, "date": latest_date.isoformat()}
            
            # Create trace
            trace = _create_trace("FRED", latest_date, df.to_dict())
            
            # Build series object
            series = MacroSeries(
                series_id=series_id,
                name=name,
                unit=unit,
                values=values,
                latest=latest,
                trace=trace
            )
            
            all_series.append(series)
            
        except Exception as e:
            print(f"⚠️  Failed to fetch {series_id}: {e}")
            continue
    
    # Create overall trace
    overall_trace = _create_trace("FRED", date.today(), all_series)
    
    return MacroOverviewData(
        series=all_series,
        range=range_str,
        trace=overall_trace
    )


def get_macro_snapshot() -> MacroSnapshotData:
    """
    Get current macro snapshot (latest values only).
    
    Returns:
        MacroSnapshotData with latest values for key series
    """
    snapshot = {}
    
    # Try to use phase3 bundle if available
    if HAS_PHASE3:
        try:
            bundle = get_us_macro_bundle()
            if bundle and isinstance(bundle, dict):
                for key, df in bundle.items():
                    if isinstance(df, pd.DataFrame) and not df.empty:
                        latest = df.iloc[-1]
                        if isinstance(latest, pd.Series):
                            snapshot[key] = float(latest.iloc[0]) if len(latest) > 0 else None
        except Exception as e:
            print(f"⚠️  Phase3 bundle failed: {e}")
    
    # Fallback: fetch individual series
    if not snapshot:
        for series_id in DEFAULT_SERIES:
            try:
                df = get_fred_series(series_id)
                if not df.empty:
                    snapshot[series_id] = float(df[series_id].iloc[-1])
            except Exception:
                continue
    
    trace = _create_trace("FRED", date.today(), snapshot)
    
    return MacroSnapshotData(
        snapshot=snapshot,
        trace=trace
    )


def get_macro_indicators() -> MacroIndicatorsData:
    """
    Get derived macro indicators.
    
    Returns:
        MacroIndicatorsData with computed indicators
    """
    cpi_yoy = None
    yield_curve = None
    recession_prob = None
    vix = None
    
    try:
        # CPI YoY
        cpi_df = get_fred_series("CPIAUCSL")
        if not cpi_df.empty:
            latest = cpi_df["CPIAUCSL"].iloc[-1]
            year_ago = cpi_df["CPIAUCSL"].iloc[-13] if len(cpi_df) >= 13 else None
            if latest and year_ago:
                cpi_yoy = ((latest - year_ago) / year_ago) * 100
        
        # Yield curve (10Y-2Y)
        yield_10y = get_fred_series("DGS10")
        yield_2y = get_fred_series("DGS2")
        if not yield_10y.empty and not yield_2y.empty:
            y10 = yield_10y["DGS10"].iloc[-1]
            y2 = yield_2y["DGS2"].iloc[-1]
            if pd.notna(y10) and pd.notna(y2):
                yield_curve = float(y10 - y2)
        
        # Recession probability (from phase3 if available)
        if HAS_PHASE3:
            try:
                regime = macro_regime()
                if regime and isinstance(regime, dict):
                    recession_prob = regime.get("recession_probability")
            except Exception:
                pass
        
        # VIX
        vix_df = get_fred_series("VIXCLS")
        if not vix_df.empty:
            vix = float(vix_df["VIXCLS"].iloc[-1])
    
    except Exception as e:
        print(f"⚠️  Indicator calculation error: {e}")
    
    trace = _create_trace("FRED/Derived", date.today(), {
        "cpi_yoy": cpi_yoy,
        "yield_curve": yield_curve,
        "recession_prob": recession_prob,
        "vix": vix
    })
    
    return MacroIndicatorsData(
        cpi_yoy=cpi_yoy,
        yield_curve_10y_2y=yield_curve,
        recession_probability=recession_prob,
        vix=vix,
        trace=trace
    )
