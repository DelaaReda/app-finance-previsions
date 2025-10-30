from __future__ import annotations

from pathlib import Path
import json
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State
import dash
try:
    from hub.logging_setup import get_logger  # type: ignore
    from hub import profiler as _prof  # type: ignore
    _log = get_logger("settings")  # type: ignore
except Exception:
    class _P:
        def log_event(self,*a,**k): pass
    class _L:
        def info(self,*a,**k): pass
        def exception(self,*a,**k): pass
    _prof = _P()  # type: ignore
    _log = _L()   # type: ignore


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
        _prof.log_event("callback", {"id": "settings.save", "move_abs_pct": threshold, "tilt": tilt})
        try:
            _log.info("settings.save.start", extra={"ctx": {"move_abs_pct": threshold, "tilt": tilt}})
        except Exception:
            pass
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
        try:
            _log.info("settings.save.ok", extra={"ctx": settings})
        except Exception:
            pass
        return dbc.Alert("✅ Paramètres enregistrés avec succès", color="success")
    
    except Exception as e:
        _prof.log_event("error", {"where": "settings.save", "error": str(e)})
        try:
            _log.exception("settings.save.fail", extra={"ctx": {"error": str(e)}})
        except Exception:
            pass
        return dbc.Alert(f"❌ Erreur: {e}", color="danger")
