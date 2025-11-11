#!/usr/bin/env python3
"""
Fetch key macro series (FRED/VIX) and persist them under data/macro_series.json.
The API layer can then serve the cached file instantly.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Dict, Any, List

import sys

import pandas as pd
import requests

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
SRC_DIR = BACKEND_DIR / "src"
# Ajouter src et backend à sys.path pour les imports
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Imports avec gestion d'erreur robuste
try:
    from core.market_data import get_fred_series  # noqa: E402
except ImportError:
    # Fallback: essayer avec src.core
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
    # Fallback: essayer avec src.storage
    try:
        from src.storage.io import save_json  # noqa: E402
    except ImportError:
        # Fallback final: import direct depuis le fichier
        import importlib.util
        # Essayer plusieurs chemins possibles
        storage_io_path = None
        for path_candidate in [
            BACKEND_DIR / "storage" / "io.py",  # backend/storage/io.py
            BACKEND_DIR / "src" / "storage" / "io.py",  # backend/src/storage/io.py
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
            raise ImportError(f"Could not find storage/io.py. Tried: {BACKEND_DIR / 'storage' / 'io.py'}, {BACKEND_DIR / 'src' / 'storage' / 'io.py'}")

DEFAULT_SERIES = os.getenv(
    "MACRO_SNAPSHOT_SERIES",
    "CPIAUCSL,VIXCLS,DFF,UNRATE,DGS10,DGS2,MICH",
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


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Persist macro series snapshot")
    parser.add_argument("--series", type=str, help="Comma separated list of series IDs to fetch")
    parser.add_argument("--stdout", action="store_true", help="Print the resulting JSON to stdout")
    args = parser.parse_args(argv)

    ids = [s.strip() for s in (args.series.split(",") if args.series else DEFAULT_SERIES) if s.strip()]
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
            failed_series.append(series_id)
            continue

    if not result["series"]:
        print(f"⚠️  Aucun série macro n'a pu être récupérée. Séries échouées: {', '.join(failed_series)}")
        # Save empty structure to prevent repeated failures
        save_json("macro_series", result, source=["fred", "error_fallback"])
        return 1

    save_json("macro_series", result, source=["fred"])
    
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
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    raise SystemExit(main())
