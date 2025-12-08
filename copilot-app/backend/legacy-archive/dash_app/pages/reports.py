from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html


def layout():
    """
    Page Reports — Rapports générés
    """
    return html.Div([
        html.H3("📊 Reports"),
        dbc.Alert("Page en construction. Affichera les rapports d'analyse générés.", color="info")
    ], id='reports-root')
