"""
Page Watchlist — Gestion de la liste de surveillance
Permet de visualiser et modifier la watchlist des tickers suivis.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, callback


def layout() -> html.Div:
    """Layout principal de la page Watchlist."""
    # Load current watchlist from env or default
    current = os.getenv('WATCHLIST') or "NGD.TO,AEM.TO,ABX.TO,K.TO,GDX"
    
    return html.Div([
        html.H3("📜 Watchlist — Gestion", className="mb-3"),
        
        dbc.Alert(
            "La plupart des scripts utilisent la variable d'environnement WATCHLIST.",
            color="info",
            className="mb-3"
        ),
        
        # Current watchlist
        dbc.Card([
            dbc.CardHeader(html.H5("Watchlist Actuelle")),
            dbc.CardBody([
                html.Pre(
                    current,
                    id="watchlist-current-display",
                    style={
                        'backgroundColor': '#212529',
                        'color': '#00ff00',
                        'padding': '1rem',
                        'borderRadius': '4px',
                        'fontFamily': 'monospace',
                    }
                ),
            ]),
        ], className="mb-4"),
        
        # Editor
        dbc.Card([
            dbc.CardHeader(html.H5("Modifier (local)")),
            dbc.CardBody([
                dbc.Label("Tickers séparés par des virgules:"),
                dcc.Textarea(
                    id='watchlist-editor',
                    value=current,
                    style={'width': '100%', 'height': '120px', 'fontFamily': 'monospace'},
                    className="form-control mb-3"
                ),
                dbc.Row([
                    dbc.Col([
                        dbc.Button(
                            "💾 Enregistrer dans data/watchlist.json",
                            id="watchlist-save-btn",
                            color="primary",
                            className="w-100"
                        ),
                    ], width=6),
                    dbc.Col([
                        dbc.Button(
                            "📋 Générer commande export",
                            id="watchlist-export-btn",
                            color="secondary",
                            className="w-100"
                        ),
                    ], width=6),
                ]),
                html.Div(id="watchlist-feedback", className="mt-3"),
            ]),
        ], className="mb-4"),
    ])


@callback(
    Output("watchlist-feedback", "children"),
    Input("watchlist-save-btn", "n_clicks"),
    Input("watchlist-export-btn", "n_clicks"),
    State("watchlist-editor", "value"),
    prevent_initial_call=True,
)
def handle_watchlist_actions(save_clicks, export_clicks, text_value):
    """Gère les actions de sauvegarde et génération de commande."""
    from dash import ctx
    
    if not ctx.triggered:
        return None
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    try:
        # Parse tickers
        tickers = [x.strip().upper() for x in (text_value or "").split(',') if x.strip()]
        
        if not tickers:
            return dbc.Alert("⚠️ Veuillez entrer au moins un ticker.", color="warning")
        
        if button_id == "watchlist-save-btn":
            # Save to data/watchlist.json
            Path('data').mkdir(parents=True, exist_ok=True)
            watchlist_path = Path('data/watchlist.json')
            watchlist_path.write_text(
                json.dumps({'watchlist': tickers}, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
            return dbc.Alert(
                f"✓ data/watchlist.json enregistré avec {len(tickers)} ticker(s).",
                color="success"
            )
        
        elif button_id == "watchlist-export-btn":
            # Generate export command
            cmd = f"export WATCHLIST={','.join(tickers)}"
            return html.Div([
                dbc.Alert("Commande générée:", color="info"),
                html.Pre(
                    cmd,
                    style={
                        'backgroundColor': '#212529',
                        'color': '#00ff00',
                        'padding': '1rem',
                        'borderRadius': '4px',
                        'fontFamily': 'monospace',
                    }
                ),
                html.Small(
                    "Copiez/collez dans votre shell pour l'utiliser dans les scripts.",
                    className="text-muted"
                ),
            ])
    
    except Exception as e:
        return dbc.Alert(f"❌ Erreur: {e}", color="danger")
