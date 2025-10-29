from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html


def layout():
    """
    Page Changes — Changements de régime et top-N
    """
    return html.Div([
        html.H3("🔄 Changes"),
        dbc.Alert("Page en construction. Affichera les changements de régime, risque et top-N.", color="info")
    ], id='changes-root')
