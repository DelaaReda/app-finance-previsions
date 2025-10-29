"""
Page Settings — Presets & Seuils
Configuration des presets de tilt macro et seuils d'alertes.
"""
from __future__ import annotations

import json
from pathlib import Path

import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, callback


def layout() -> html.Div:
    """Layout principal de la page Settings."""
    base_cfg = Path('data/config')
    base_cfg.mkdir(parents=True, exist_ok=True)
    
    # Load tilt presets
    tilt_path = base_cfg / 'tilt_presets.json'
    default_presets = {
        "inflation": ["GDX", "GLD", "XLE"],
        "slowdown": ["XLU", "XLV"],
        "deflation": ["TLT", "IEF"],
    }
    try:
        presets = json.loads(tilt_path.read_text(encoding='utf-8')) if tilt_path.exists() else default_presets
    except Exception:
        presets = default_presets
    
    # Load alerts config
    alerts_path = base_cfg / 'alerts.json'
    default_alerts = {"move_abs_pct": 1.0}
    try:
        alerts = json.loads(alerts_path.read_text(encoding='utf-8')) if alerts_path.exists() else default_alerts
    except Exception:
        alerts = default_alerts
    
    return html.Div([
        html.H3("⚙️ Settings — Presets & Seuils", className="mb-3"),
        
        # Tilt Presets Section
        dbc.Card([
            dbc.CardHeader(html.H5("Tilt Presets (macro → tickers)")),
            dbc.CardBody([
                dbc.Label("Configuration JSON (tilt_presets.json):"),
                dcc.Textarea(
                    id='settings-tilt-editor',
                    value=json.dumps(presets, ensure_ascii=False, indent=2),
                    style={
                        'width': '100%',
                        'height': '180px',
                        'fontFamily': 'monospace',
                        'backgroundColor': '#212529',
                        'color': '#00ff00',
                        'border': '1px solid #495057',
                        'padding': '0.5rem',
                    },
                    className="mb-3"
                ),
                dbc.Button(
                    "💾 Enregistrer presets",
                    id="settings-save-tilt-btn",
                    color="primary",
                ),
                html.Div(id="settings-tilt-feedback", className="mt-2"),
            ]),
        ], className="mb-4"),
        
        # Alerts Thresholds Section
        dbc.Card([
            dbc.CardHeader(html.H5("Seuils Alerts")),
            dbc.CardBody([
                dbc.Label("Mouvement (%, 1j) minimum:"),
                dcc.Slider(
                    id='settings-alerts-slider',
                    min=0.0,
                    max=5.0,
                    step=0.1,
                    value=float(alerts.get('move_abs_pct', 1.0)),
                    marks={i: f"{i}%" for i in range(0, 6)},
                    tooltip={"placement": "bottom", "always_visible": True},
                    className="mb-3"
                ),
                dbc.Button(
                    "💾 Enregistrer seuils",
                    id="settings-save-alerts-btn",
                    color="primary",
                ),
                html.Div(id="settings-alerts-feedback", className="mt-2"),
            ]),
        ], className="mb-4"),
    ])


@callback(
    Output("settings-tilt-feedback", "children"),
    Input("settings-save-tilt-btn", "n_clicks"),
    State("settings-tilt-editor", "value"),
    prevent_initial_call=True,
)
def save_tilt_presets(n_clicks, text_value):
    """Sauvegarde les presets de tilt."""
    try:
        # Validate JSON
        obj = json.loads(text_value)
        
        # Save to file
        base_cfg = Path('data/config')
        base_cfg.mkdir(parents=True, exist_ok=True)
        tilt_path = base_cfg / 'tilt_presets.json'
        tilt_path.write_text(
            json.dumps(obj, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        
        return dbc.Alert(
            f"✓ Enregistré: {tilt_path}",
            color="success"
        )
    except json.JSONDecodeError as e:
        return dbc.Alert(
            f"❌ Erreur JSON: {e}",
            color="danger"
        )
    except Exception as e:
        return dbc.Alert(
            f"❌ Erreur: {e}",
            color="danger"
        )


@callback(
    Output("settings-alerts-feedback", "children"),
    Input("settings-save-alerts-btn", "n_clicks"),
    State("settings-alerts-slider", "value"),
    prevent_initial_call=True,
)
def save_alerts_thresholds(n_clicks, move_pct):
    """Sauvegarde les seuils d'alertes."""
    try:
        # Save to file
        base_cfg = Path('data/config')
        base_cfg.mkdir(parents=True, exist_ok=True)
        alerts_path = base_cfg / 'alerts.json'
        alerts_path.write_text(
            json.dumps({"move_abs_pct": move_pct}, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        
        return dbc.Alert(
            f"✓ Enregistré: {alerts_path} (seuil: {move_pct}%)",
            color="success"
        )
    except Exception as e:
        return dbc.Alert(
            f"❌ Erreur: {e}",
            color="danger"
        )
