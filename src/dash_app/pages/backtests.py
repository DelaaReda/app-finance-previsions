"""Backtests / Evaluation page (scaffold)

Provides a layout() with placeholders for agent-run metrics and performance curves.
Empty-state FR when data missing.
"""
from dash import html
import dash_bootstrap_components as dbc


def layout():
    return html.Div(
        [
            html.H3("Backtests & Évaluation"),
            html.Div(
                """
                État vide — Pas de backtests disponibles.
                Pour générer des backtests : exécutez les agents d'évaluation.
                """,
                style={"color": "#666", "marginBottom": "1rem"},
            ),
            html.Div(id='backtests-metrics', children=[html.P("Métriques à venir...")]),
            html.Div(id='backtests-charts', children=[html.P("Courbes de performance à venir...")]),
        ],
        style={"padding": "1rem"},
    )
