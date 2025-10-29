"""
Page Earnings — Earnings Calendar
Affiche le calendrier des publications de résultats pour la watchlist.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table, Input, Output, callback


def layout() -> html.Div:
    """Layout principal de la page Earnings."""
    return html.Div([
        html.H3("📊 Earnings Calendar", className="mb-3"),
        
        dbc.Alert(
            "Calendrier des publications de résultats pour les tickers de la watchlist.",
            color="info",
            className="mb-3"
        ),
        
        dbc.Card([
            dbc.CardHeader([
                html.H5("Filtre", className="mb-2"),
                html.Div([
                    html.Label("Fenêtre (jours à venir):", className="me-2"),
                    dcc.Slider(
                        id='earnings-days-slider',
                        min=3,
                        max=90,
                        step=1,
                        value=30,
                        marks={i: str(i) for i in [3, 7, 14, 30, 60, 90]},
                        tooltip={"placement": "bottom", "always_visible": True},
                    ),
                ]),
            ]),
            dbc.CardBody(id="earnings-table-container"),
        ]),
    ])


@callback(
    Output("earnings-table-container", "children"),
    Input("earnings-days-slider", "value"),
)
def display_earnings(days):
    """Affiche le calendrier des earnings."""
    try:
        # Find latest earnings.json
        parts = sorted(Path('data/earnings').glob('dt=*/earnings.json'))
        
        if not parts:
            return dbc.Alert(
                "Aucun fichier earnings.json trouvé. Exécutez l'agent earnings.",
                color="info"
            )
        
        earnings_path = parts[-1]
        obj = json.loads(earnings_path.read_text(encoding='utf-8'))
        
        evs = obj.get('events') or []
        if not evs:
            return dbc.Alert("Aucun événement earnings à afficher.", color="info")
        
        # Build dataframe
        rows = []
        for e in evs:
            rows.append({
                'ticker': e.get('ticker'),
                'date': e.get('date'),
                'info': e.get('info', ''),
            })
        
        df = pd.DataFrame(rows)
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # Filter by date window
        now = pd.Timestamp.utcnow().normalize()
        filtered = df[(df['date'] >= now) & (df['date'] <= now + pd.Timedelta(days=days))].copy()
        
        if filtered.empty:
            return dbc.Alert(
                f"Aucun earnings dans les {days} prochains jours.",
                color="info"
            )
        
        # Sort by date
        filtered = filtered.sort_values('date')
        filtered['date'] = filtered['date'].dt.strftime('%Y-%m-%d')
        
        return dash_table.DataTable(
            columns=[
                {"name": "Ticker", "id": "ticker"},
                {"name": "Date", "id": "date"},
                {"name": "Info", "id": "info"},
            ],
            data=filtered.to_dict('records'),
            style_cell={'textAlign': 'left', 'padding': '8px'},
            style_header={'backgroundColor': '#343a40', 'fontWeight': 'bold'},
            page_size=20,
            sort_action="native",
            filter_action="native",
        )
    
    except Exception as e:
        return dbc.Alert(
            f"Erreur lors du chargement des earnings: {e}",
            color="danger"
        )
