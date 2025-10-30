from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html


def layout():
    """
    Page Earnings — Calendrier des résultats
    """
    return html.Div([
        html.H3("💰 Earnings"),
        dbc.Alert("Page en construction. Affichera le calendrier des résultats trimestriels.", color="info")
    ], id='earnings-root')
