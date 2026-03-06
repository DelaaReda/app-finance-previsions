#!/usr/bin/env python3
"""
Fetch key macro series (FRED/VIX) and persist them under data/macro_series.json.
The API layer can then serve the cached file instantly.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Dict, Any, List

import sys

import pandas as pd
import requests
import yfinance as yf

# Load environment variables from .env file using centralized loader
try:
    from core.env_loader import ensure_env_loaded, get_env_path
    ensure_env_loaded()
    env_path = get_env_path()
    if env_path:
        print(f"✅ Loaded .env from: {env_path}")
except ImportError:
    # Fallback: try to load manually if env_loader not available
    try:
        from dotenv import load_dotenv
        backend_dir = Path(__file__).resolve().parents[1]  # backend/
        project_root = backend_dir.parent  # copilot-app/
        env_file = project_root / ".env"  # copilot-app/.env (PRIORITÉ)
        if env_file.exists():
            load_dotenv(env_file, override=False)
            print(f"✅ Loaded .env from: {env_file}")
        else:
            load_dotenv(override=False)
    except ImportError:
        pass  # dotenv not available, but env vars may already be set by parent process

BACKEND_DIR = Path(__file__).resolve().parents[1]
# Backend is now flattened (no nested src/ directory).
SRC_DIR = BACKEND_DIR
# Ajouter backend à sys.path pour les imports
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from core.sentry_runtime import install_global_excepthook, init_sentry, set_job_context, capture_exception
except Exception:  # pragma: no cover
    def install_global_excepthook(job_name: str) -> bool:
        return False

    def init_sentry(component: str) -> bool:
        return False

    def set_job_context(job_name: str, **context: Any) -> None:
        return None

    def capture_exception(exc: BaseException, *, job_name: str | None = None, context: Dict[str, Any] | None = None) -> None:
        return None

# Imports avec gestion d'erreur robuste
try:
    from core.market_data import get_fred_series  # noqa: E402
except ImportError:
    # Fallback: essayer avec alias legacy src.core
    try:
        from src.core.market_data import get_fred_series  # noqa: E402
    except ImportError:
        # Fallback final: import direct depuis le fichier
        import importlib.util
        market_data_path = SRC_DIR / "core" / "market_data.py"
        if market_data_path.exists():
            spec = importlib.util.spec_from_file_location("market_data", market_data_path)
            market_data = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(market_data)
            get_fred_series = market_data.get_fred_series
        else:
            raise ImportError(f"Could not find market_data.py at {market_data_path}")

try:
    from storage.io import save_json  # noqa: E402
except ImportError:
    # Fallback: essayer avec alias legacy src.storage
    try:
        from src.storage.io import save_json  # noqa: E402
    except ImportError:
        # Fallback final: import direct depuis le fichier
        import importlib.util
        # Essayer plusieurs chemins possibles
        storage_io_path = None
        for path_candidate in [
            BACKEND_DIR / "storage" / "io.py",  # backend/storage/io.py
        ]:
            if path_candidate.exists():
                storage_io_path = path_candidate
                break
        
        if storage_io_path and storage_io_path.exists():
            spec = importlib.util.spec_from_file_location("storage_io", storage_io_path)
            storage_io = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(storage_io)
            save_json = storage_io.save_json
        else:
            raise ImportError(f"Could not find storage/io.py. Tried: {BACKEND_DIR / 'storage' / 'io.py'}")

# Include FX + commodities by default so downstream consumers (judge, briefs) always
# get dollar regime and key energy/metals signals without relying on env overrides.
# - DTWEXBGS : Broad dollar index (DXY proxy)
# - DCOILWTICO / DCOILBRENTEU : WTI & Brent crude
# - GOLDAMGBD228NLBM : Gold (London fix)
DEFAULT_SERIES = os.getenv(
    "MACRO_SNAPSHOT_SERIES",
    ",".join(
        [
            "CPIAUCSL",        # US CPI
            "VIXCLS",         # VIX
            "DFF",            # Fed funds effective
            "UNRATE",         # Unemployment rate
            "DGS10", "DGS2",  # Treasury 10Y / 2Y
            "MICH",           # Michigan sentiment
            "DTWEXBGS",       # Dollar index (broad)
            "DCOILWTICO",     # WTI crude
            "DCOILBRENTEU",   # Brent crude
            "GOLDAMGBD228NLBM",  # Gold
        ]
    ),
).split(",")
MAX_POINTS = int(os.getenv("MACRO_SNAPSHOT_MAX_POINTS", "1200"))


def _fred_metadata(series_id: str) -> Dict[str, Any]:
    key = os.getenv("FRED_API_KEY")
    if not key:
        return {}
    try:
        resp = requests.get(
            "https://api.stlouisfed.org/fred/series",
            params={
                "series_id": series_id,
                "file_type": "json",
                "api_key": key,
            },
            timeout=20,
        )
        resp.raise_for_status()
        payload = resp.json()
        data = (payload.get("seriess") or payload.get("series") or [])
        return data[0] if data else {}
    except Exception:
        return {}


def _observations_from_df(df: pd.DataFrame, series_id: str) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []
    col = df.columns[0]
    tail = df.sort_index().tail(MAX_POINTS)
    observations = []
    for idx, value in tail[col].items():
        if isinstance(idx, pd.Timestamp):
            date_str = idx.strftime("%Y-%m-%d")
        else:
            date_str = str(idx)
        observations.append(
            {
                "date": date_str,
                "value": None if pd.isna(value) else float(value),
            }
        )
    return observations


def _gold_fallback_from_yf(max_points: int) -> pd.DataFrame | None:
    """
    FRED gold series can occasionally be unavailable.
    Fall back to yfinance front-month gold futures (GC=F) if needed.
    """
    try:
        ticker = yf.Ticker("GC=F")
        hist = ticker.history(period="10y")  # enough history, trimmed later
        if hist is None or hist.empty:
            return None
        close = hist[["Close"]].rename(columns={"Close": "GOLD"})
        # Keep only the last max_points rows to align with other series trimming
        return close.tail(max_points)
    except Exception:
        return None


def main(argv: List[str] | None = None) -> int:
    init_sentry("macro_series_snapshot")
    parser = argparse.ArgumentParser(description="Persist macro series snapshot")
    parser.add_argument("--series", type=str, help="Comma separated list of series IDs to fetch")
    parser.add_argument("--stdout", action="store_true", help="Print the resulting JSON to stdout")
    args = parser.parse_args(argv)

    ids = [s.strip() for s in (args.series.split(",") if args.series else DEFAULT_SERIES) if s.strip()]
    set_job_context("macro_series_snapshot", series_count=len(ids))
    result: Dict[str, Any] = {"series": {}}
    
    # Check if FRED_API_KEY is available
    fred_key = os.getenv("FRED_API_KEY")
    if fred_key:
        print(f"✅ FRED_API_KEY trouvée (longueur: {len(fred_key)})")
    else:
        print("⚠️  FRED_API_KEY non trouvée dans les variables d'environnement.")
        print("   Vérifiez que la clé est définie dans .env ou dans les variables d'environnement système.")
        print("   Le job va continuer avec fallback CSV si disponible.")
    
    successful_series = 0
    failed_series = []
    macro_fallback_stats = {
        "fred_empty_fallback_attempted_total": 0,
        "fred_empty_fallback_recovered_total": 0,
        "fred_empty_fallback_failed_total": 0,
        "fred_empty_fallback_by_series": {},
    }

    for series_id in ids:
        try:
            # Verify FRED_API_KEY is available before fetching
            current_key = os.getenv("FRED_API_KEY")
            if not current_key:
                # Try to reload env one more time
                try:
                    from dotenv import load_dotenv
                    load_dotenv(override=True)  # Force reload
                    current_key = os.getenv("FRED_API_KEY")
                except:
                    pass
            
            if current_key:
                print(f"   Récupération de {series_id} avec FRED API...")
            else:
                print(f"   Récupération de {series_id} avec fallback CSV...")
            
            df = get_fred_series(series_id)
            # Gold fallback via yfinance if FRED returns empty
            if (df is None or df.empty) and series_id == "GOLDAMGBD228NLBM":
                print("   ⚠️  GOLDAMGBD228NLBM: empty from FRED, trying yfinance GC=F fallback...")
                macro_fallback_stats["fred_empty_fallback_attempted_total"] += 1
                df = _gold_fallback_from_yf(MAX_POINTS)
                if df is not None and not df.empty:
                    df.columns = [series_id]
                    print("   ✅ GOLD fallback GC=F (yfinance) recovered data")
                    macro_fallback_stats["fred_empty_fallback_recovered_total"] += 1
                    macro_fallback_stats["fred_empty_fallback_by_series"][series_id] = {
                        "attempted": 1,
                        "recovered": 1,
                        "failed": 0,
                    }
                else:
                    macro_fallback_stats["fred_empty_fallback_failed_total"] += 1
                    macro_fallback_stats["fred_empty_fallback_by_series"][series_id] = {
                        "attempted": 1,
                        "recovered": 0,
                        "failed": 1,
                    }
            if df is None or df.empty:
                print(f"   ⚠️  {series_id}: DataFrame vide ou None")
                failed_series.append(series_id)
                continue
            observations = _observations_from_df(df, series_id)
            if not observations:
                print(f"   ⚠️  {series_id}: Aucune observation extraite")
                failed_series.append(series_id)
                continue
            meta = _fred_metadata(series_id)
            result["series"][series_id] = {
                "title": meta.get("title") or meta.get("name") or series_id,
                "units": meta.get("units") or meta.get("unit"),
                "frequency": meta.get("frequency"),
                "observations": observations,
            }
            successful_series += 1
            print(f"   ✅ {series_id}: {len(observations)} observations")
        except Exception as e:
            print(f"   ❌ Erreur lors de la récupération de {series_id}: {e}")
            import traceback
            traceback.print_exc()
            capture_exception(
                e,
                job_name="macro_series_snapshot",
                context={"series_id": series_id, "stage": "fetch"},
            )
            failed_series.append(series_id)
            continue

    if not result["series"]:
        print(f"⚠️  Aucun série macro n'a pu être récupérée. Séries échouées: {', '.join(failed_series)}")
        # Save empty structure to prevent repeated failures
        result["provider_fallback_stats"] = {"macro": macro_fallback_stats}
        save_json("macro_series", result, source=["fred", "error_fallback"])
        save_json(
            "provider_fallback_macro",
            {
                "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "macro": macro_fallback_stats,
            },
            source=["job:macro_series_snapshot", "provider_fallback_stats", "error_fallback"],
        )
        return 1

    result["provider_fallback_stats"] = {"macro": macro_fallback_stats}
    save_json("macro_series", result, source=["fred"])
    save_json(
        "provider_fallback_macro",
        {
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "macro": macro_fallback_stats,
        },
        source=["job:macro_series_snapshot", "provider_fallback_stats"],
    )
    
    if failed_series:
        print(f"⚠️  {len(failed_series)} série(s) n'ont pas pu être récupérée(s): {', '.join(failed_series)}")

    if args.stdout:
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"✅ Macro snapshot enregistré ({successful_series}/{len(ids)} séries).")
    return 0


def run_macro_snapshot_job():
    """
    Wrapper function for the macro snapshot job.
    Can be called from scheduler or startup event.
    """
    try:
        result = main([])
        return {"status": "completed" if result == 0 else "failed", "exit_code": result}
    except Exception as e:
        print(f"❌ Error in macro snapshot job: {e}")
        capture_exception(e, job_name="macro_series_snapshot", context={"stage": "wrapper"})
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    install_global_excepthook("macro_series_snapshot")
    raise SystemExit(main())
