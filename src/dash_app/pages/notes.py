"""
Page Notes — Journal personnel
Permet d'éditer et visualiser des notes quotidiennes en Markdown.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, callback


def layout() -> html.Div:
    """Layout principal de la page Notes."""
    return html.Div([
        html.H3("📝 Notes — Journal personnel", className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Dates")),
                    dbc.CardBody([
                        dcc.Dropdown(
                            id='notes-date-dropdown',
                            placeholder="Sélectionnez une date...",
                            className="mb-3"
                        ),
                        dbc.Button(
                            "➕ Nouveau (aujourd'hui)",
                            id="notes-new-btn",
                            color="primary",
                            className="w-100"
                        ),
                        html.Div(id="notes-new-feedback", className="mt-2"),
                    ]),
                ]),
            ], width=3),
            
            dbc.Col([
                html.Div(id="notes-editor-container"),
            ], width=9),
        ]),
    ])


@callback(
    Output("notes-date-dropdown", "options"),
    Output("notes-date-dropdown", "value"),
    Input("notes-date-dropdown", "id"),  # trigger on mount
    Input("notes-new-btn", "n_clicks"),  # refresh after new
)
def load_dates(_, n_clicks):
    """Charge les dates disponibles."""
    base = Path('data/notes')
    base.mkdir(parents=True, exist_ok=True)
    
    today = dt.datetime.utcnow().strftime('%Y%m%d')
    dates = sorted([p.name for p in base.glob('dt=*')], reverse=True)
    
    # Ensure today exists
    today_dir = base / f"dt={today}"
    if not today_dir.exists():
        today_dir.mkdir(parents=True, exist_ok=True)
        notes_file = today_dir / 'notes.md'
        if not notes_file.exists():
            notes_file.write_text("", encoding='utf-8')
        dates = sorted([p.name for p in base.glob('dt=*')], reverse=True)
    
    options = [{'label': d, 'value': d} for d in dates]
    value = dates[0] if dates else None
    
    return options, value


@callback(
    Output("notes-new-feedback", "children"),
    Input("notes-new-btn", "n_clicks"),
    prevent_initial_call=True,
)
def create_new_note(n_clicks):
    """Crée une nouvelle note pour aujourd'hui."""
    try:
        base = Path('data/notes')
        base.mkdir(parents=True, exist_ok=True)
        today = dt.datetime.utcnow().strftime('%Y%m%d')
        today_dir = base / f"dt={today}"
        today_dir.mkdir(parents=True, exist_ok=True)
        
        notes_file = today_dir / 'notes.md'
        if not notes_file.exists():
            notes_file.write_text("", encoding='utf-8')
        
        return dbc.Alert(
            f"✓ Note créée pour {today}",
            color="success",
            duration=3000,
        )
    except Exception as e:
        return dbc.Alert(
            f"❌ Erreur: {e}",
            color="danger"
        )


@callback(
    Output("notes-editor-container", "children"),
    Input("notes-date-dropdown", "value"),
)
def display_editor(date_folder):
    """Affiche l'éditeur de notes."""
    if not date_folder:
        return dbc.Alert(
            "Sélectionnez une date pour éditer les notes.",
            color="info"
        )
    
    try:
        base = Path('data/notes')
        target_dir = base / date_folder
        target_dir.mkdir(parents=True, exist_ok=True)
        notes_path = target_dir / 'notes.md'
        
        # Load existing content
        text = ""
        if notes_path.exists():
            text = notes_path.read_text(encoding='utf-8')
        
        return html.Div([
            dbc.Card([
                dbc.CardHeader(html.H5(f"Éditer: {date_folder}/notes.md")),
                dbc.CardBody([
                    dcc.Textarea(
                        id='notes-textarea',
                        value=text,
                        style={
                            'width': '100%',
                            'height': '320px',
                            'fontFamily': 'monospace',
                        },
                        className="form-control mb-3"
                    ),
                    dbc.Button(
                        "💾 Enregistrer",
                        id="notes-save-btn",
                        color="primary",
                    ),
                    html.Div(id="notes-save-feedback", className="mt-2"),
                    dcc.Store(id='notes-current-path', data=str(notes_path)),
                ]),
            ], className="mb-3"),
            
            dbc.Card([
                dbc.CardHeader(html.H5("Aperçu")),
                dbc.CardBody([
                    dcc.Markdown(id='notes-preview', children=text),
                ]),
            ]),
        ])
    
    except Exception as e:
        return dbc.Alert(
            f"Erreur lors du chargement des notes: {e}",
            color="danger"
        )


@callback(
    Output("notes-save-feedback", "children"),
    Output("notes-preview", "children"),
    Input("notes-save-btn", "n_clicks"),
    State("notes-textarea", "value"),
    State("notes-current-path", "data"),
    prevent_initial_call=True,
)
def save_notes(n_clicks, text_value, path_str):
    """Sauvegarde les notes et met à jour l'aperçu."""
    try:
        notes_path = Path(path_str)
        notes_path.write_text(text_value or "", encoding='utf-8')
        
        return (
            dbc.Alert("✓ Enregistré", color="success", duration=3000),
            text_value or ""
        )
    except Exception as e:
        return (
            dbc.Alert(f"❌ Erreur: {e}", color="danger"),
            text_value or ""
        )
