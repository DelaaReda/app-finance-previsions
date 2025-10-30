from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html


def layout():
    """
    Page d'accueil — aperçu de l'application Finance Agent
    """
    return html.Div([
        html.H3("Finance Agent — Accueil"),
        dbc.Card([
            dbc.CardHeader("Bienvenue"),
            dbc.CardBody([
                html.P("Finance Agent est une usine de prévisions pour investisseur privé."),
                html.P("Navigation:"),
                html.Ul([
                    html.Li([html.Strong("Analyse"), " : Dashboard, Signals, Portfolio, Forecasts, News, Deep Dive"]),
                    html.Li([html.Strong("Prévisions"), " : Regimes, Risk, Recession, Backtests, Evaluation"]),
                    html.Li([html.Strong("Administration"), " : Agents Status, Quality, Observability, Settings"]),
                ]),
                html.Hr(),
                html.Small("Consultez docs/README.md pour plus d'informations."),
            ])
        ], className="mb-3"),
    ], id='home-root')
