from __future__ import annotations

from dash import dash_table, html
import dash_bootstrap_components as dbc
import pandas as pd
import json
from pathlib import Path


def _load_contributors_df() -> pd.DataFrame | None:
    paths = sorted(Path("data/llm_summary").glob("dt=*/summary.json"))
    if not paths:
        return None
    obj = json.loads(paths[-1].read_text(encoding="utf-8"))
    contribs = obj.get("contributors") or []
    if not contribs:
        return pd.DataFrame()
    # normalize to DataFrame
    return pd.DataFrame(contribs)


def layout():
    df = _load_contributors_df()
    if df is None or df.empty:
        return html.Div([
            html.H3("LLM Scoreboard (Contributeurs)"),
            dbc.Alert("Aucun contributeur LLM disponible (summary.json).", color="info"),
        ])
    keep = [c for c in ["model", "source", "symbol", "horizon", "score", "prediction", "rationale"] if c in df.columns]
    return html.Div([
        html.H3("LLM Scoreboard (Contributeurs)"),
        dash_table.DataTable(
            data=df[keep].to_dict("records"),
            columns=[{"name": c, "id": c} for c in keep],
            sort_action="native",
            filter_action="native",
            page_size=25,
            style_cell={"textAlign": "left"},
            style_table={"overflowX": "auto"},
        ),
    ])
