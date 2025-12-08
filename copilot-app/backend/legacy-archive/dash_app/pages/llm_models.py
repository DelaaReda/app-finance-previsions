from __future__ import annotations

from pathlib import Path
import json
import dash_bootstrap_components as dbc
from dash import html


def _read_models() -> dict:
    """Lit le fichier des modèles LLM"""
    fp = Path('tools/g4f-proxy/.g4f_working.txt')
    if fp.exists():
        try:
            return {'models': fp.read_text(encoding='utf-8').strip().split('\n')}
        except Exception:
            pass
    return {}


def layout():
    """
    Page LLM Models — Modèles LLM disponibles
    """
    data = _read_models()
    models = data.get('models', [])
    
    if not models:
        return html.Div([
            html.H3("🤖 LLM Models"),
            dbc.Alert("Aucun modèle LLM disponible.", color="info")
        ], id='llm-models-root')
    
    items = [html.Li(m) for m in models]
    
    return html.Div([
        html.H3("🤖 LLM Models"),
        html.Small(f"{len(models)} modèles disponibles"),
        html.Hr(),
        dbc.Card([
            dbc.CardHeader("Modèles actifs"),
            dbc.CardBody(html.Ul(items))
        ])
    ], id='llm-models-root')
