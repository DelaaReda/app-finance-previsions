from __future__ import annotations

from pathlib import Path
import json
from datetime import datetime
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State
import dash


def _load_notes() -> list:
    """Charge les notes depuis data/notes"""
    parts = sorted(Path('data/notes').glob('dt=*/notes.json'), reverse=True)
    notes = []
    for p in parts[:10]:  # Dernières 10 partitions
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
            if isinstance(data, list):
                notes.extend(data)
        except Exception:
            pass
    return notes


def layout():
    """
    Page Notes — Journal d'investissement personnel
    """
    notes = _load_notes()
    
    cards = []
    for note in notes:
        if isinstance(note, dict):
            cards.append(dbc.Card([
                dbc.CardHeader(f"📅 {note.get('date', 'N/A')} - {note.get('ticker', 'Général')}"),
                dbc.CardBody(html.P(note.get('content', '')))
            ], className="mb-2"))
    
    if not cards:
        cards.append(dbc.Alert("Aucune note enregistrée.", color="info"))
    
    return html.Div([
        html.H3("📓 Notes"),
        html.Small("Journal d'investissement personnel"),
        html.Hr(),
        
        dbc.Card([
            dbc.CardHeader("➕ Nouvelle note"),
            dbc.CardBody([
                dcc.Input(id='note-ticker', placeholder="Ticker (optionnel)", style={"width": "100%"}, className="mb-2"),
                dcc.Textarea(
                    id='note-content',
                    placeholder="Votre note...",
                    style={"width": "100%", "height": "100px"}
                ),
                dbc.Button("💾 Enregistrer", id="note-save-btn", color="primary", className="mt-2"),
                html.Div(id='note-result', className="mt-2"),
            ])
        ], className="mb-3"),
        
        html.H5("Historique"),
        html.Div(cards)
    ], id='notes-root')


@dash.callback(
    Output('note-result', 'children'),
    Output('note-content', 'value'),
    Output('note-ticker', 'value'),
    Input('note-save-btn', 'n_clicks'),
    State('note-ticker', 'value'),
    State('note-content', 'value'),
    prevent_initial_call=True
)
def save_note(n_clicks, ticker, content):
    """Enregistre une nouvelle note"""
    if not n_clicks or not content:
        return dash.no_update, dash.no_update, dash.no_update
    
    try:
        dt = datetime.now().strftime('%Y%m%d')
        notes_dir = Path(f'data/notes/dt={dt}')
        notes_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing notes
        notes_file = notes_dir / 'notes.json'
        notes = []
        if notes_file.exists():
            notes = json.loads(notes_file.read_text(encoding='utf-8'))
        
        # Add new note
        notes.append({
            'date': datetime.now().isoformat(),
            'ticker': ticker.upper() if ticker else 'Général',
            'content': content
        })
        
        # Save
        notes_file.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding='utf-8')
        
        return dbc.Alert("✅ Note enregistrée", color="success"), '', ''
    
    except Exception as e:
        return dbc.Alert(f"❌ Erreur: {e}", color="danger"), dash.no_update, dash.no_update
