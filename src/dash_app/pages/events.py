"""
Page Events — Upcoming Events (Calendrier Macro)
Affiche les événements macro à venir.
"""
from __future__ import annotations

import json
import datetime as dt
from pathlib import Path

import pandas as pd
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table, Input, Output, callback


def _fmt_date(s: str) -> str:
    """Formate une date ISO en texte lisible."""
    try:
        d = dt.date.fromisoformat(s)
        return d.strftime("%A %d %B %Y")
    except Exception:
        return s


def layout() -> html.Div:
    """Layout principal de la page Events."""
    return html.Div([
        html.H3("📅 Upcoming Events — Calendrier Macro", className="mb-3"),
        
        dbc.Alert(
            "Les dates sont générées de façon approximative (heuristiques). Vérifiez toujours les sources officielles.",
            color="warning",
            className="mb-3"
        ),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Source")),
                    dbc.CardBody([
                        dbc.Label("Dossier date:"),
                        dcc.Dropdown(
                            id='events-date-dropdown',
                            placeholder="Sélectionnez une date...",
                        ),
                    ]),
                ]),
            ], width=3),
            
            dbc.Col([
                html.Div(id="events-content"),
            ], width=9),
        ]),
    ])


@callback(
    Output("events-date-dropdown", "options"),
    Output("events-date-dropdown", "value"),
    Input("events-date-dropdown", "id"),  # trigger on mount
)
def load_dates(_):
    """Charge les dates disponibles."""
    base = Path("data/events")
    if not base.exists():
        return [], None
    
    dates = sorted([p.name for p in base.glob("dt=*")], reverse=True)
    options = [{'label': d, 'value': d} for d in dates]
    value = dates[0] if dates else None
    
    return options, value


@callback(
    Output("events-content", "children"),
    Input("events-date-dropdown", "value"),
)
def display_events(date_folder):
    """Affiche les événements."""
    if not date_folder:
        return dbc.Alert(
            "Sélectionnez un dossier date pour afficher les événements.",
            color="info"
        )
    
    try:
        events_path = Path("data/events") / date_folder / "events.json"
        
        if not events_path.exists():
            return dbc.Alert(
                f"Aucun fichier events.json trouvé dans {date_folder}.",
                color="warning"
            )
        
        obj = json.loads(events_path.read_text(encoding='utf-8'))
        events = obj.get('events') or []
        
        if not events:
            return dbc.Alert("Aucun événement à afficher.", color="info")
        
        # Prepare data for table
        rows = []
        for e in events:
            rows.append({
                'date': _fmt_date(e.get('date', '')),
                'event': e.get('event', ''),
                'importance': e.get('importance', ''),
                'country': e.get('country', ''),
            })
        
        df = pd.DataFrame(rows)
        
        return dash_table.DataTable(
            columns=[
                {"name": "Date", "id": "date"},
                {"name": "Événement", "id": "event"},
                {"name": "Importance", "id": "importance"},
                {"name": "Pays", "id": "country"},
            ],
            data=df.to_dict('records'),
            style_cell={'textAlign': 'left', 'padding': '8px'},
            style_header={'backgroundColor': '#343a40', 'fontWeight': 'bold'},
            style_data_conditional=[
                {
                    'if': {'filter_query': '{importance} = "high"'},
                    'backgroundColor': '#ffc107',
                    'color': 'black',
                },
            ],
            page_size=20,
            sort_action="native",
            filter_action="native",
        )
    
    except Exception as e:
        return dbc.Alert(
            f"Erreur lors du chargement des événements: {e}",
            color="danger"
        )
