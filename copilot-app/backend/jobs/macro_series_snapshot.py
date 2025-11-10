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

import pandas as pd
import requests

import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BACKEND_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core.market_data import get_fred_series  # noqa: E402
from storage.io import save_json  # noqa: E402

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

    for series_id in ids:
        df = get_fred_series(series_id)
        observations = _observations_from_df(df, series_id)
        if not observations:
            continue
        meta = _fred_metadata(series_id)
        result["series"][series_id] = {
            "title": meta.get("title") or meta.get("name") or series_id,
            "units": meta.get("units") or meta.get("unit"),
            "frequency": meta.get("frequency"),
            "observations": observations,
        }

    if not result["series"]:
        print("⚠️  Aucun série macro n'a pu être récupérée.")
        return 1

    save_json("macro_series", result, source=["fred"])

    if args.stdout:
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"✅ Macro snapshot enregistré ({len(result['series'])} séries).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
