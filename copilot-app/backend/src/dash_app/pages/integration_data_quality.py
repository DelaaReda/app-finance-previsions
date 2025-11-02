from __future__ import annotations

from dash import dash_table, html
import dash_bootstrap_components as dbc
import pandas as pd
import json
from pathlib import Path


def _load_freshness_rows() -> list[dict] | None:
    paths = sorted(Path("data/quality").glob("dt=*/freshness.json"))
    if not paths:
        return None
    obj = json.loads(paths[-1].read_text(encoding="utf-8"))
    # flatten to name/value rows for display
    rows = []
    for k, v in obj.items():
        rows.append({"name": k, "value": v})
    return rows


def layout():
    rows = _load_freshness_rows()
    if not rows:
        return html.Div([
            html.H3("Data Quality"),
            dbc.Alert("Aucun freshness.json recent.", color="info"),
        ])
    df = pd.DataFrame(rows)
    return html.Div([
        html.H3("Data Quality — Freshness"),
        dash_table.DataTable(
            data=df.to_dict("records"),
            columns=[{"id": c, "name": c} for c in df.columns],
            sort_action="native",
            page_size=20,
            style_cell={"textAlign": "left"},
        ),
    ])
