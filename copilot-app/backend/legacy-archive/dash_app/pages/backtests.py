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
from dash_app.data.loader import read_parquet
from dash_app.data.paths import (
    p_backtests_results,
    p_backtest_details,
)


def _latest_details_parquet() -> Optional[Path]:
    return p_backtest_details()


def _latest_results_parquet() -> Optional[Path]:
    return p_backtests_results()


def _latest_summary_json() -> Optional[Path]:
    """Latest backtest summary.json under data/backtest/dt=*/summary.json.

    Returns None if no partition exists.
    """
    parts = sorted(Path('data/backtest').glob('dt=*/summary.json'))
    return parts[-1] if parts else None


def _build_topn_figure() -> Optional[dict]:
    # Prefer consolidated results.parquet if present
    rp = _latest_results_parquet()
    if rp and rp.exists():
        rdf = read_parquet(rp)
        if not rdf.empty and {'date', 'strategy', 'equity'} <= set(rdf.columns):
            try:
                rdf['date'] = pd.to_datetime(rdf['date'], errors='coerce')
                fig = px.line(rdf, x='date', y='equity', color='strategy', title='Equity Curve (par stratégie)')
                fig.update_layout(margin=dict(l=40, r=20, t=40, b=30), template='plotly_dark')
                return fig
            except Exception:
                pass

    # Fallback: build cumulative basket from details.parquet
    p = _latest_details_parquet()
    if not p:
        return None
    df = read_parquet(p)
    if df.empty or 'realized_return' not in df.columns:
        return None
    if 'dt' in df.columns:
        df['dt'] = pd.to_datetime(df['dt'], errors='coerce')
    series = df.dropna(subset=['dt', 'realized_return']).groupby('dt')['realized_return'].mean().sort_index()
    if series.empty:
        return None
    cum = (1 + series).cumprod() - 1
    fig = px.line(x=cum.index, y=cum.values, labels={'x': 'Date', 'y': 'Cumulative return'}, title='Top-N Basket - Cumulative')
    fig.update_layout(margin=dict(l=40, r=20, t=40, b=30), template='plotly_dark')
    return fig


def _metrics_card() -> dbc.Card:
    p = _latest_summary_json()
    if not p or not p.exists():
        return dbc.Card([
            dbc.CardHeader("Métriques (résumé)"),
            dbc.CardBody(html.Small("Aucun summary.json trouvé (exécutez l'agent de backtest)."))
        ])
    try:
        import json
        js = json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        js = {}

    def _badge(label: str, val, color: str = 'secondary'):
        try:
            if isinstance(val, (int, float)):
                text = f"{val:.4f}"
            else:
                text = str(val)
        except Exception:
            text = str(val)
        return dbc.Badge(f"{label}: {text}", color=color, className="me-2")

    badges = []
    for k, col in [("CAGR", 'success'), ("Sharpe", 'info'), ("MaxDD", 'danger'), ("count_days", 'secondary')]:
        if k in js:
            badges.append(_badge(k, js[k], col))
    body = html.Div(badges) if badges else html.Small("Métriques indisponibles dans summary.json")
    return dbc.Card([dbc.CardHeader("Métriques (résumé)"), dbc.CardBody(body)], className="mb-3")


def _histogram_card() -> Optional[dbc.Card]:
    p = _latest_details_parquet()
    if not p or not p.exists():
        return None
    try:
        df = pd.read_parquet(p)
    except Exception:
        return None
    if df.empty or 'realized_return' not in df.columns:
        return None
    s = pd.to_numeric(df['realized_return'], errors='coerce').dropna()
    if s.empty:
        return None
    fig = px.histogram(s, nbins=30, labels={'value': 'Realized return'}, title='Distribution des rendements réalisés')
    fig.update_layout(margin=dict(l=40, r=20, t=40, b=30), template='plotly_dark')
    return dbc.Card([dbc.CardHeader("Distribution des rendements"), dbc.CardBody(dcc.Graph(figure=fig, config={"displayModeBar": False}))], className="mb-3")


def layout():
    metrics = _metrics_card()
    fig = _build_topn_figure()
    hist = _histogram_card()
    if fig is None:
        # Fallback: if details.parquet exists, show a compact table
        p = _latest_details_parquet()
        if p and p.exists():
            try:
                df = pd.read_parquet(p)
            except Exception:
                df = pd.DataFrame()

            if not df.empty:
                cols = [c for c in ['dt','ticker','horizon','score','realized_return'] if c in df.columns]
                view = df[cols].tail(20) if cols else df.tail(20)
                table = dbc.Table.from_dataframe(view.reset_index(drop=True), striped=True, bordered=False, hover=True, size='sm')
                return html.Div(
                    [
                        html.H3("Backtests & Évaluation"),
                        metrics,
                        html.Div([
                            dbc.Alert("Courbe indisponible (série vide). Affichage des derniers enregistrements.", color='warning'),
                            dbc.Card([
                                dbc.CardHeader("Derniers enregistrements (details.parquet)"),
                                dbc.CardBody(table),
                            ]),
                            hist or html.Div(),
                        ], id='backtests-charts')
                    ],
                    style={"padding": "1rem"},
                )

        # No file at all: keep explicit guidance
        return html.Div(
            [
                html.H3("Backtests & Évaluation"),
                metrics,
                html.Div([
                    dbc.Alert(
                        "Aucun backtest disponible. Pour générer des backtests : exécutez l'agent de backtest.",
                        color='info',
                    ),
                ], id='backtests-charts'),
            ],
            style={"padding": "1rem"},
        )

    return html.Div(
        [
            html.H3("Backtests & Évaluation"),
            metrics,
            html.Div([
                dcc.Graph(id='backtests-topn-curve', figure=fig, config={"displayModeBar": False}),
                hist or html.Div(),
            ], id='backtests-charts'),
        ],
        style={"padding": "1rem"},
    )
