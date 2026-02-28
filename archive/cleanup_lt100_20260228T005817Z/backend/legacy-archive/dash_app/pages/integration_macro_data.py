from __future__ import annotations

from dash import dash_table, html
import dash_bootstrap_components as dbc
import pandas as pd
from pathlib import Path
import json

from src.tools.parquet_io import latest_partition


def _load_macro_df() -> pd.DataFrame | None:
    base = Path("data/macro/forecast")
    part = latest_partition(base)
    if not part:
        return None
    # prefer parquet then json
    pq = part / "macro_forecast.parquet"
    js = part / "macro_forecast.json"
    if pq.exists():
        try:
            return pd.read_parquet(pq)
        except Exception:
            return None
    if js.exists():
        try:
            obj = json.loads(js.read_text(encoding="utf-8"))
            if isinstance(obj, list):
                return pd.DataFrame(obj)
            if isinstance(obj, dict):
                return pd.DataFrame([obj])
        except Exception:
            return None
    return None


def layout():
    df = _load_macro_df()
    if df is None or df.empty:
        return html.Div([
            html.H3("Macroeconomic Data"),
            dbc.Alert("Aucune macro‑prévision disponible (macro_forecast).", color="info"),
        ])
    cols = [
        {"name": c, "id": c}
        for c in df.columns[:12]  # limiter l'affichage
    ]
    return html.Div([
        html.H3("Macroeconomic Data"),
        dash_table.DataTable(
            data=df.to_dict("records"),
            columns=cols,
            sort_action="native",
            page_size=20,
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left"},
        ),
    ])
