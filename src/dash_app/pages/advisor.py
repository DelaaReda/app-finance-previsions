"""
Page Advisor — Assistant IA
Interface de chat avec l'assistant IA pour obtenir des conseils d'investissement.
"""
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html, dcc


def layout() -> html.Div:
    """Layout principal de la page Advisor."""
    return html.Div([
        html.H3("🤖 Advisor — Assistant IA", className="mb-3"),
        
        dbc.Alert([
            html.H5("🚧 En construction"),
            html.P(
                "Cette page permettra d'interagir avec un assistant IA pour obtenir des conseils "
                "d'investissement basés sur l'analyse des données disponibles."
            ),
            html.Hr(),
            html.P("Fonctionnalités prévues:", className="mb-2"),
            html.Ul([
                html.Li("Chat interactif avec l'IA"),
                html.Li("Analyse contextuelle des positions actuelles"),
                html.Li("Suggestions basées sur les signaux et prévisions"),
                html.Li("Explications des recommandations"),
            ]),
        ], color="info"),
        
        dbc.Card([
            dbc.CardHeader(html.H5("Interface de Chat")),
            dbc.CardBody([
                html.Div([
                    html.P("Cette fonctionnalité nécessite l'intégration avec le runtime LLM.", className="text-muted"),
                    dbc.Button(
                        "Voir LLM Summary",
                        href="/llm_summary",
                        color="primary",
                        external_link=True,
                    ),
                ]),
            ]),
        ]),
    ])
