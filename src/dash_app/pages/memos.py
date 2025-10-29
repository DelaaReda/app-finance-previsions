"""
Page Memos — Investment Memos Par Titre
Affiche les mémos d'investissement générés pour chaque ticker.
"""
from __future__ import annotations

import json
from pathlib import Path

import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, callback


def layout() -> html.Div:
    """Layout principal de la page Memos."""
    return html.Div([
        html.H3("📄 Investment Memos — Par Titre", className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Sélection")),
                    dbc.CardBody([
                        dbc.Label("Dossier date:"),
                        dcc.Dropdown(
                            id='memos-date-dropdown',
                            placeholder="Sélectionnez une date...",
                            className="mb-3"
                        ),
                        dbc.Label("Ticker:"),
                        dcc.Dropdown(
                            id='memos-ticker-dropdown',
                            placeholder="Sélectionnez un ticker...",
                            className="mb-3"
                        ),
                        dbc.Alert(
                            [
                                html.P("Pour générer des memos:"),
                                html.Code("PYTHONPATH=src python scripts/run_memos.py"),
                            ],
                            color="info"
                        ),
                    ]),
                ]),
            ], width=3),
            
            dbc.Col([
                html.Div(id="memos-content"),
            ], width=9),
        ]),
    ])


@callback(
    Output("memos-date-dropdown", "options"),
    Output("memos-date-dropdown", "value"),
    Input("memos-date-dropdown", "id"),  # trigger on mount
)
def load_dates(_):
    """Charge les dates disponibles."""
    base = Path('data/memos')
    if not base.exists():
        return [], None
    
    dates = sorted([p.name for p in base.glob('dt=*')], reverse=True)
    options = [{'label': d, 'value': d} for d in dates]
    value = dates[0] if dates else None
    
    return options, value


@callback(
    Output("memos-ticker-dropdown", "options"),
    Output("memos-ticker-dropdown", "value"),
    Input("memos-date-dropdown", "value"),
)
def load_tickers(date_folder):
    """Charge les tickers disponibles pour la date sélectionnée."""
    if not date_folder:
        return [], None
    
    ddir = Path('data/memos') / date_folder
    if not ddir.exists():
        return [], None
    
    files = sorted(ddir.glob('*.json'))
    tickers = [f.stem for f in files]
    options = [{'label': t, 'value': t} for t in tickers]
    value = tickers[0] if tickers else None
    
    return options, value


@callback(
    Output("memos-content", "children"),
    Input("memos-ticker-dropdown", "value"),
    Input("memos-date-dropdown", "value"),
)
def display_memo(ticker, date_folder):
    """Affiche le mémo pour le ticker sélectionné."""
    if not ticker or not date_folder:
        return dbc.Alert(
            "Sélectionnez un dossier date et un ticker pour afficher le mémo.",
            color="info"
        )
    
    try:
        memo_path = Path('data/memos') / date_folder / f"{ticker}.json"
        if not memo_path.exists():
            return dbc.Alert(
                f"Aucun mémo trouvé pour {ticker} dans {date_folder}.",
                color="warning"
            )
        
        obj = json.loads(memo_path.read_text(encoding='utf-8'))
        
        answer = obj.get('answer') or "Aucun contenu disponible."
        parsed = obj.get('parsed') or {}
        ensemble = obj.get('ensemble') or {}
        
        return html.Div([
            dbc.Card([
                dbc.CardHeader(html.H4(ticker)),
                dbc.CardBody([
                    dcc.Markdown(answer, className="mb-3"),
                ]),
            ], className="mb-3"),
            
            dbc.Accordion([
                dbc.AccordionItem([
                    html.Pre(
                        json.dumps(parsed, indent=2, ensure_ascii=False),
                        style={
                            'backgroundColor': '#212529',
                            'color': '#00ff00',
                            'padding': '1rem',
                            'maxHeight': '400px',
                            'overflow': 'auto',
                        }
                    ),
                ], title="Parsed JSON"),
                
                dbc.AccordionItem([
                    html.Div([
                        html.H6("Résumé Ensemble:"),
                        html.P(f"Models: {ensemble.get('models', 'N/A')}"),
                        html.P(f"Avg Agreement: {ensemble.get('avg_agreement', 'N/A')}"),
                        html.Hr(),
                        html.Pre(
                            json.dumps(ensemble, indent=2, ensure_ascii=False),
                            style={
                                'backgroundColor': '#212529',
                                'color': '#00ff00',
                                'padding': '1rem',
                                'maxHeight': '400px',
                                'overflow': 'auto',
                            }
                        ),
                    ]),
                ], title="Ensemble (résumé)"),
            ], start_collapsed=True),
        ])
    
    except Exception as e:
        return dbc.Alert(
            f"Erreur lors de la lecture du mémo: {e}",
            color="danger"
        )
