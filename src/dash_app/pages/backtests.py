"""Backtests page

Reads latest `data/backtest/dt=*/details.parquet` (written by
`src.agents.backtest_agent`) and renders a cumulative Top-N performance
curve (mean realized return per backtest date cumulated over time).

Behaviour:
 - If no parquet found, shows a French empty-state message.
 - Exposes a Plotly line graph with id `backtests-topn-curve` so tests can
   assert its presence.
"""
from pathlib import Path
from typing import Optional

import pandas as pd
from dash import html, dcc
import plotly.express as px
import dash_bootstrap_components as dbc


def _latest_details_parquet() -> Optional[Path]:
    parts = sorted(Path('data/backtest').glob('dt=*'))
    if not parts:
        return None
    latest = parts[-1]
    p = latest / 'details.parquet'
    if p.exists():
        return p
    return None


def _build_topn_figure() -> Optional[dict]:
    p = _latest_details_parquet()
    if not p:
        return None
    try:
        df = pd.read_parquet(p)
    except Exception:
        return None

    if df.empty or 'realized_return' not in df.columns:
        return None

    # ensure dt as datetime and compute daily basket mean
    if 'dt' in df.columns:
        df['dt'] = pd.to_datetime(df['dt'], errors='coerce')
    else:
        df['dt'] = pd.NaT

    series = df.dropna(subset=['dt', 'realized_return']).groupby('dt')['realized_return'].mean().sort_index()
    if series.empty:
        return None

    # cumulative return (start at 0)
    cum = (1 + series).cumprod() - 1
    fig = px.line(x=cum.index, y=cum.values, labels={'x': 'Date', 'y': 'Cumulative return'}, title='Top-N Basket - Cumulative')
    fig.update_layout(margin=dict(l=40, r=20, t=40, b=30), template='plotly_dark')
    return fig


def layout():
    fig = _build_topn_figure()
    if fig is None:
        return html.Div(
            [
                html.H3("Backtests & Évaluation"),
                dbc.Alert(
                    "Aucun backtest disponible. Pour générer des backtests : exécutez l'agent de backtest.",
                    color='info',
                ),
                html.Div(id='backtests-metrics', children=[html.P("Métriques à venir...")]),
                html.Div(id='backtests-charts', children=[html.P("Courbes de performance à venir...")]),
            ],
            style={"padding": "1rem"},
        )

    return html.Div(
        [
            html.H3("Backtests & Évaluation"),
            html.Div(id='backtests-metrics', children=[html.P("Résumé des backtests")]),
            dcc.Graph(id='backtests-topn-curve', figure=fig, config={"displayModeBar": False}),
        ],
        style={"padding": "1rem"},
    )
