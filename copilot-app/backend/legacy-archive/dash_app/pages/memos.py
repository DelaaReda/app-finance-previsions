from __future__ import annotations

from pathlib import Path
import json
import pandas as pd
import dash_bootstrap_components as dbc
from dash import html


def layout():
    """
    Page Memos — Investment memos générés par les agents
    """
    parts = sorted(Path('data/reports').glob('dt=*/memos.json'))
    
    if not parts:
        return html.Div([
            html.H3("📝 Investment Memos"),
            dbc.Alert("Aucun memo disponible. Exécutez 'make run-memos' pour générer.", color="info")
        ], id='memos-root')
    
    try:
        memos = json.loads(parts[-1].read_text(encoding='utf-8'))
        cards = []
        
        for ticker, data in memos.items():
            if isinstance(data, dict):
                content = data.get('memo', 'N/A')
                cards.append(dbc.Card([
                    dbc.CardHeader(f"📊 {ticker}"),
                    dbc.CardBody(html.Pre(content, style={"whiteSpace": "pre-wrap"}))
                ], className="mb-3"))
        
        if not cards:
            cards.append(dbc.Alert("Aucun memo trouvé dans le fichier.", color="warning"))
        
        return html.Div([
            html.H3("📝 Investment Memos"),
            html.Small(f"Dernière génération: {parts[-1].parent.name}"),
            html.Hr(),
            html.Div(cards)
        ], id='memos-root')
    
    except Exception as e:
        return html.Div([
            html.H3("📝 Investment Memos"),
            dbc.Alert(f"Erreur de lecture: {e}", color="danger")
        ], id='memos-root')
