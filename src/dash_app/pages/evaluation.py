"""Evaluation Dash page

Displays evaluation metrics computed by `src.agents.evaluation_agent`.
Empty-state FR if no metrics found.
"""
from pathlib import Path
import json
import pandas as pd
import dash_bootstrap_components as dbc
from dash import html


def layout():
    return html.Div([
        html.H3("Évaluation des agents — MAE / RMSE / Hit ratio"),
        html.Div(id='evaluation-content')
    ], style={"padding": "1rem"})


def _load_latest_metrics():
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


def render_metrics():
    m = _load_latest_metrics()
    if not m:
        return dbc.Alert("Aucune métrique d'évaluation disponible. Exécutez l'agent d'évaluation.", color='info')

    rows = []
    by = m.get('by') or 'all'
    results = m.get('results') or {}
    for k, v in results.items():
        rows.append(dbc.ListGroupItem([
            html.H6(str(k)),
            html.Ul([
                html.Li(f"Count: {v.get('count')}") ,
                html.Li(f"MAE: {v.get('mae')}") ,
                html.Li(f"RMSE: {v.get('rmse')}") ,
                html.Li(f"Hit ratio: {v.get('hit_ratio')}")
            ])
        ]))

    return dbc.Card([
        dbc.CardHeader(f"Evaluation (group by: {by})"),
        dbc.CardBody(dbc.ListGroup(rows))
    ])


# simple server-side render helper used by the main app
def content():
    return render_metrics()
