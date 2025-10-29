"""
Page Home — Page d'accueil
Vue d'ensemble du système avec liens vers les principales sections.
"""
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html


def layout() -> html.Div:
    """Layout principal de la page Home."""
    return html.Div([
        dbc.Jumbotron([
            html.H1("🏠 Finance Agent", className="display-3"),
            html.P(
                "Plateforme d'analyse financière et de prévisions",
                className="lead"
            ),
            html.Hr(className="my-4"),
            html.P(
                "Utilisez la barre latérale pour accéder aux différentes sections d'analyse et d'administration."
            ),
        ]),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H4("📊 Analyse")),
                    dbc.CardBody([
                        html.Ul([
                            html.Li([html.A("Dashboard", href="/dashboard")]),
                            html.Li([html.A("Signals", href="/signals")]),
                            html.Li([html.A("Forecasts", href="/forecasts")]),
                            html.Li([html.A("Portfolio", href="/portfolio")]),
                            html.Li([html.A("Deep Dive", href="/deep_dive")]),
                            html.Li([html.A("News", href="/news")]),
                        ]),
                    ]),
                ]),
            ], width=4),
            
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H4("📈 Risque & Macro")),
                    dbc.CardBody([
                        html.Ul([
                            html.Li([html.A("Regimes", href="/regimes")]),
                            html.Li([html.A("Risk", href="/risk")]),
                            html.Li([html.A("Recession", href="/recession")]),
                        ]),
                    ]),
                ]),
            ], width=4),
            
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H4("⚙️ Administration")),
                    dbc.CardBody([
                        html.Ul([
                            html.Li([html.A("Agents Status", href="/agents")]),
                            html.Li([html.A("Quality", href="/quality")]),
                            html.Li([html.A("Observability", href="/observability")]),
                        ]),
                    ]),
                ]),
            ], width=4),
        ], className="mb-4"),
        
        dbc.Alert([
            html.H5("📚 Documentation"),
            html.P("Consultez le README et les docs dans le dossier /docs pour plus d'informations."),
        ], color="info"),
    ])
