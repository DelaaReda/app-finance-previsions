"""Evaluation Dash page

Displays evaluation metrics computed by `src.agents.evaluation_agent`.
We render a tidy DataTable for the results (group / count / mae / rmse / hit_ratio)
and show a French empty-state when metrics are missing.
"""
from pathlib import Path
import json
import pandas as pd
import dash_bootstrap_components as dbc
from dash import html
from dash import dash_table
from typing import Optional


def layout():
    return html.Div([
        html.H3("Évaluation des agents — MAE / RMSE / Hit ratio"),
        html.Div(id='evaluation-summary', children=[]),
        html.Div(id='evaluation-content', children=[render_metrics()])
    ], style={"padding": "1rem"})


def _load_latest_metrics() -> Optional[dict]:
    parts = sorted(Path('data/evaluation').glob('dt=*'))
    if not parts:
        return None
    latest = parts[-1]
    mfile = latest / 'metrics.json'
    if not mfile.exists():
        return None
    try:
        return json.loads(mfile.read_text(encoding='utf-8'))
    except Exception:
        return None


def _load_latest_details() -> Optional[pd.DataFrame]:
    parts = sorted(Path('data/evaluation').glob('dt=*/details.parquet'))
    if not parts:
        return None
    try:
        return pd.read_parquet(parts[-1])
    except Exception:
        return None


def render_metrics():
    m = _load_latest_metrics()
    if not m:
        # Fallback: show latest details table if available
        details = _load_latest_details()
        if details is not None and not details.empty:
            cols = [c for c in ['dt','ticker','horizon','expected_return','realized_return','direction','provider','agent','source'] if c in details.columns]
            view = details[cols].tail(30) if cols else details.tail(30)
            table = dash_table.DataTable(
                id='evaluation-table',
                data=view.reset_index(drop=True).to_dict('records'),
                columns=[{"id": c, "name": c} for c in view.columns],
                page_size=15,
                style_table={'overflowX': 'auto'},
                style_cell={'padding': '6px', 'textAlign': 'left', 'minWidth': '80px'},
                style_header={'fontWeight': 'bold'},
            )
            return dbc.Card([
                dbc.CardHeader("Détails d'évaluation (fallback)"),
                dbc.CardBody(table)
            ])
        return dbc.Alert("Aucune métrique d'évaluation disponible. Exécutez l'agent d'évaluation.", color='info')

    results = m.get('results') or {}
    # build DataFrame from results mapping
    rows = []
    for grp, vals in results.items():
        rows.append({
            'group': str(grp),
            'count': vals.get('count'),
            'mae': vals.get('mae'),
            'rmse': vals.get('rmse'),
            'hit_ratio': vals.get('hit_ratio')
        })

    if not rows:
        return dbc.Alert("Aucune métrique d'évaluation disponible (aucun groupe).", color='info')

    df = pd.DataFrame(rows)

    # Prepare DataTable columns with formatting
    columns = [
        {'id': 'group', 'name': 'Groupe', 'type': 'text'},
        {'id': 'count', 'name': 'Count', 'type': 'numeric'},
        {'id': 'mae', 'name': 'MAE', 'type': 'numeric', 'format': {'specifier': '.4f'}},
        {'id': 'rmse', 'name': 'RMSE', 'type': 'numeric', 'format': {'specifier': '.4f'}},
        {'id': 'hit_ratio', 'name': 'Hit ratio', 'type': 'numeric', 'format': {'specifier': '.2%'}},
    ]

    total = int(df['count'].sum()) if 'count' in df.columns else len(df)
    header = dbc.CardHeader([
        "Evaluation ", html.Small(f"(group by: {m.get('by') or 'all'}, total obs: {total})", className='text-muted ms-2')
    ])
    return dbc.Card([
        header,
        dbc.CardBody([
            dash_table.DataTable(
                id='evaluation-table',
                data=df.to_dict('records'),
                columns=columns,
                sort_action='native',
                filter_action='native',
                export_format='csv',
                style_table={'overflowX': 'auto'},
                style_cell={'padding': '6px', 'textAlign': 'left', 'minWidth': '80px'},
                style_header={'fontWeight': 'bold'},
                page_size=10,
            )
        ])
    ])


# simple server-side render helper used by the main app
def content():
    return render_metrics()
