from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html


def layout():
    """
    Page Advisor — Conseils d'investissement IA
    """
    return html.Div([
        html.H3("🤖 Advisor"),
        dbc.Alert("Page en construction. Fournira des conseils d'investissement basés sur l'IA.", color="info")
    ], id='advisor-root')
