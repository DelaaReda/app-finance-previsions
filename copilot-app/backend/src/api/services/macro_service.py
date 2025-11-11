# src/api/services/macro_service.py
"""
Macro service facade - wraps analytics/phase3_macro.py and core/market_data.py
"""
from __future__ import annotations

import hashlib
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple

import pandas as pd

from core.market_data import get_fred_series

try:
    from backend.storage.io import load_json  # type: ignore
except ImportError:  # pragma: no cover - fallback path setup when src/ is root
    import sys
    from pathlib import Path

    # Get backend root: from src/api/services/macro_service.py -> backend/
    current_file = Path(__file__).resolve()
    backend_root = current_file.parents[3]  # src/api/services -> src/api -> src -> backend
    storage_dir = backend_root / "storage"

    # Add paths to sys.path if not already there
    paths_to_add = [str(backend_root), str(storage_dir)]
    for path_str in paths_to_add:
        if path_str not in sys.path:
            sys.path.insert(0, path_str)  # Use insert(0) to prioritize these paths

    try:
        from backend.storage.io import load_json  # type: ignore
    except ImportError:
        # Last resort: try direct import with absolute path
        import importlib.util
        storage_io_path = backend_root / "storage" / "io.py"
        if storage_io_path.exists():
            spec = importlib.util.spec_from_file_location("storage.io", storage_io_path)
            if spec and spec.loader:
                storage_io = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(storage_io)
                load_json = storage_io.load_json
            else:
                raise ImportError(f"Cannot load storage.io from {storage_io_path}")
        else:
            raise ImportError(f"storage/io.py not found at {storage_io_path}")
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
CACHE_KEY = "macro_series"


def _load_cached_macro_series() -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Load macro snapshot persisted by jobs/macro_series_snapshot.py."""
    cached = load_json(CACHE_KEY)
    if not cached:
        return None, None
    payload = cached.get("data") or cached.get("payload") or cached
    series_map = payload.get("series")
    if isinstance(series_map, dict) and series_map:
        return series_map, payload
    return None, payload


def _parse_obs_timestamp(raw: Any) -> Optional[datetime]:
    """Parse ISO date or epoch timestamps coming from cached observations."""
    if raw is None:
        return None
    try:
        if isinstance(raw, (int, float)):
            return datetime.fromtimestamp(float(raw))
        raw_str = str(raw)
        if raw_str.endswith("Z"):
            raw_str = raw_str.replace("Z", "+00:00")
        if len(raw_str) == 10 and raw_str[4] == "-" and raw_str[7] == "-":
            return datetime.fromisoformat(raw_str)
        return datetime.fromisoformat(raw_str)
    except ValueError:
        return None


def _observations_to_points(observations: List[Dict[str, Any]]) -> List[DataPoint]:
    datapoints: List[DataPoint] = []
    for obs in observations:
        ts = _parse_obs_timestamp(obs.get("date") or obs.get("timestamp") or obs.get("time"))
        value = obs.get("value")
        if ts is None or value is None:
            continue
        try:
            datapoints.append(DataPoint(timestamp=ts, value=float(value)))
        except (TypeError, ValueError):
            continue
    datapoints.sort(key=lambda d: d.timestamp)
    return datapoints


def _series_from_cache(series_id: str, cached_entry: Dict[str, Any]) -> Optional[MacroSeries]:
    observations = cached_entry.get("observations") or cached_entry.get("data") or []
    datapoints = _observations_to_points(observations)
    if not datapoints:
        return None

    info = FRED_SERIES_INFO.get(series_id, {})
    name = cached_entry.get("title") or cached_entry.get("name") or info.get("name") or series_id
    unit = cached_entry.get("units") or cached_entry.get("unit") or info.get("unit")
    latest_point = datapoints[-1]

    latest = {
        "value": latest_point.value,
        "date": latest_point.timestamp.date().isoformat()
    }

    trace_source = cached_entry.get("source") or "macro_snapshot_cache"
    trace = _create_trace(trace_source, latest_point.timestamp.date(), {
        "series_id": series_id,
        "points": len(datapoints),
        "cached": True
    })

    return MacroSeries(
        series_id=series_id,
        name=name,
        unit=unit,
        values=datapoints,
        latest=latest,
        trace=trace
    )


def _latest_value_from_cache(cached_entry: Dict[str, Any]) -> Optional[float]:
    observations = cached_entry.get("observations") or cached_entry.get("data") or []
    for obs in reversed(observations):
        value = obs.get("value")
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _sorted_observations(cached_entry: Optional[Dict[str, Any]]) -> List[Tuple[datetime, float]]:
    if not cached_entry:
        return []
    observations = cached_entry.get("observations") or cached_entry.get("data") or []
    pairs: List[Tuple[datetime, float]] = []
    for obs in observations:
        ts = _parse_obs_timestamp(obs.get("date") or obs.get("timestamp") or obs.get("time"))
        value = obs.get("value")
        if ts is None or value is None:
            continue
        try:
            pairs.append((ts, float(value)))
        except (TypeError, ValueError):
            continue
    pairs.sort(key=lambda item: item[0])
    return pairs


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
    
    cached_map, _cached_payload = _load_cached_macro_series()

    # Fetch all series
    all_series: List[MacroSeries] = []
    used_ids = set()

    if cached_map:
        for series_id in series_list:
            cached_entry = cached_map.get(series_id)
            if cached_entry:
                cached_series = _series_from_cache(series_id, cached_entry)
                if cached_series:
                    all_series.append(cached_series)
                    used_ids.add(series_id)

    for series_id in series_list:
        if series_id in used_ids:
            continue
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
    trace_source = "macro_cache" if cached_map else "FRED"
    overall_trace = _create_trace(trace_source, date.today(), {
        "series_requested": series_list,
        "series_returned": len(all_series),
        "cached": bool(cached_map)
    })
    
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
    snapshot: Dict[str, float] = {}
    cached_map, _cached_payload = _load_cached_macro_series()

    if cached_map:
        for series_id, entry in cached_map.items():
            latest_val = _latest_value_from_cache(entry)
            if latest_val is not None:
                snapshot[series_id] = latest_val
    
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
    
    # Fallback: fetch individual series for any missing entries
    for series_id in DEFAULT_SERIES:
        if series_id in snapshot:
            continue
        try:
            df = get_fred_series(series_id)
            if not df.empty:
                snapshot[series_id] = float(df[series_id].iloc[-1])
        except Exception:
            continue
    
    trace_source = "macro_cache" if cached_map else "FRED"
    trace = _create_trace(trace_source, date.today(), snapshot)
    
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
    
    cached_map, _ = _load_cached_macro_series()

    try:
        if cached_map:
            cpi_pairs = _sorted_observations(cached_map.get("CPIAUCSL"))
            if len(cpi_pairs) >= 2:
                latest_date, latest_val = cpi_pairs[-1]
                base_val = None
                for dt, val in reversed(cpi_pairs[:-1]):
                    if (latest_date - dt).days >= 365:
                        base_val = val
                        break
                if base_val and base_val != 0:
                    cpi_yoy = ((latest_val - base_val) / base_val) * 100
            
            dgs10_pairs = _sorted_observations(cached_map.get("DGS10"))
            dgs2_pairs = _sorted_observations(cached_map.get("DGS2"))
            if dgs10_pairs and dgs2_pairs:
                yield_curve = dgs10_pairs[-1][1] - dgs2_pairs[-1][1]
            
            vix_pairs = _sorted_observations(cached_map.get("VIXCLS"))
            if vix_pairs:
                vix = vix_pairs[-1][1]
        else:
            # Live fetch fallback
            cpi_df = get_fred_series("CPIAUCSL")
            if not cpi_df.empty:
                latest = cpi_df["CPIAUCSL"].iloc[-1]
                year_ago = cpi_df["CPIAUCSL"].iloc[-13] if len(cpi_df) >= 13 else None
                if latest and year_ago:
                    cpi_yoy = ((latest - year_ago) / year_ago) * 100
            
            yield_10y = get_fred_series("DGS10")
            yield_2y = get_fred_series("DGS2")
            if not yield_10y.empty and not yield_2y.empty:
                y10 = yield_10y["DGS10"].iloc[-1]
                y2 = yield_2y["DGS2"].iloc[-1]
                if pd.notna(y10) and pd.notna(y2):
                    yield_curve = float(y10 - y2)
            
            vix_df = get_fred_series("VIXCLS")
            if not vix_df.empty:
                vix = float(vix_df["VIXCLS"].iloc[-1])
        
        # Recession probability
        if HAS_PHASE3:
            try:
                regime = macro_regime()
                if regime and isinstance(regime, dict):
                    recession_prob = regime.get("recession_probability")
            except Exception:
                pass
        elif yield_curve is not None:
            # Simple heuristic using yield curve inversion if phase3 unavailable
            if yield_curve < -0.75:
                recession_prob = 0.7
            elif yield_curve < 0:
                recession_prob = 0.5
            else:
                recession_prob = 0.2

    except Exception as e:
        print(f"⚠️  Indicator calculation error: {e}")

    trace = _create_trace("macro_cache" if cached_map else "FRED/Derived", date.today(), {
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
