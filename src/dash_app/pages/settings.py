from __future__ import annotations

from pathlib import Path
import json
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State
import dash


def _load_settings() -> dict:
    """Charge les paramètres depuis data/config/alerts.json"""
    fp = Path('data/config/alerts.json')
    if fp.exists():
        try:
            return json.loads(fp.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {'move_abs_pct': 1.0, 'tilt': 'balanced'}


def layout():
    """
    Page Settings — Configuration des seuils et préférences
    """
    settings = _load_settings()
    
    return html.Div([
        html.H3("⚙️ Settings"),
        html.Small("Configuration des seuils d'alertes et préférences"),
        html.Hr(),
        
        dbc.Card([
            dbc.CardHeader("Seuils d'alertes"),
            dbc.CardBody([
                html.Label("Seuil de mouvement absolu (%, 1j)"),
                dcc.Slider(
                    id='settings-move-threshold',
                    min=0.0,
                    max=5.0,
                    step=0.1,
                    value=settings.get('move_abs_pct', 1.0),
                    marks={i: f'{i}%' for i in range(0, 6)},
                ),
                html.Hr(),
                html.Label("Tilt de portefeuille"),
                dcc.RadioItems(
                    id='settings-tilt',
                    options=[
                        {'label': 'Conservateur', 'value': 'conservative'},
                        {'label': 'Équilibré', 'value': 'balanced'},
                        {'label': 'Agressif', 'value': 'aggressive'},
                    ],
                    value=settings.get('tilt', 'balanced'),
                    inline=True
                ),
                html.Hr(),
                dbc.Button("💾 Enregistrer", id="settings-save-btn", color="primary", className="mt-3"),
                html.Div(id='settings-result', className="mt-3"),
            ])
        ], className="mb-3"),
    ], id='settings-root')


@dash.callback(
    Output('settings-result', 'children'),
    Input('settings-save-btn', 'n_clicks'),
    State('settings-move-threshold', 'value'),
    State('settings-tilt', 'value'),
    prevent_initial_call=True
)
def save_settings(n_clicks, threshold, tilt):
    """Enregistre les paramètres"""
    if not n_clicks:
        return dash.no_update
    
    try:
        config_dir = Path('data/config')
        config_dir.mkdir(parents=True, exist_ok=True)
        
        settings = {
            'move_abs_pct': float(threshold) if threshold is not None else 1.0,
            'tilt': tilt or 'balanced'
        }
        
        (config_dir / 'alerts.json').write_text(
            json.dumps(settings, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        
        return dbc.Alert("✅ Paramètres enregistrés avec succès", color="success")
    
    except Exception as e:
        return dbc.Alert(f"❌ Erreur: {e}", color="danger")
