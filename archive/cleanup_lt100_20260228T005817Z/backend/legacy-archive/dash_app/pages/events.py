from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html


def layout():
    """
    Page Events — Événements économiques et calendriers
    """
    return html.Div([
        html.H3("📅 Events"),
        dbc.Alert("Page en construction. Affichera les événements économiques et calendriers.", color="info")
    ], id='events-root')
