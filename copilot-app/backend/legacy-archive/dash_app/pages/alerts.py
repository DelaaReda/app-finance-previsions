from __future__ import annotations

from pathlib import Path
import json
import pandas as pd
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
import dash


def _read_quality_issues() -> pd.DataFrame:
    """Lit les issues du dernier rapport de qualité"""
    parts = sorted(Path('data/quality').glob('dt=*/report.json'))
    if not parts:
        return pd.DataFrame()
    
    try:
        obj = json.loads(parts[-1].read_text(encoding='utf-8'))
        issues = []
        for sec in ['news', 'macro', 'prices', 'forecasts', 'features', 'events']:
            s = obj.get(sec) or {}
            for it in (s.get('issues') or []):
                issues.append({'section': sec, **it})
        
        if not issues:
            return pd.DataFrame()
        
        df = pd.DataFrame(issues)
        # Order by severity
        sev_order = {'error': 0, 'warn': 1, 'info': 2}
        df['sev_rank'] = df['sev'].map(lambda x: sev_order.get(str(x).lower(), 9))
        df = df.sort_values(['sev_rank', 'section'])
        return df[['section', 'sev', 'msg']]
    except Exception:
        return pd.DataFrame()


def _quality_card() -> dbc.Card:
    """Carte des problèmes de qualité"""
    df = _read_quality_issues()
    
    if df.empty:
        return dbc.Card([
            dbc.CardHeader("✅ Qualité des données"),
            dbc.CardBody(dbc.Alert("Aucun problème détecté.", color="success"))
        ])
    
    table = dash_table.DataTable(
        id='alerts-quality-table',
        columns=[{"name": c, "id": c} for c in df.columns],
        data=df.to_dict('records'),
        page_size=10,
        export_format='csv',
        style_table={"overflowX": "auto"},
        style_cell={"fontSize": 13},
    )
    
    return dbc.Card([
        dbc.CardHeader("⚠️ Qualité des données"),
        dbc.CardBody(table)
    ])


def _movements_card() -> dbc.Card:
    """Carte des mouvements inhabituels sur la watchlist"""
    parts = sorted(Path('data/forecast').glob('dt=*/brief.json'))
    if not parts:
        return dbc.Card([
            dbc.CardHeader("Mouvements récents"),
            dbc.CardBody(dbc.Alert("Aucun brief disponible.", color="info"))
        ])
    
    try:
        br = json.loads(parts[-1].read_text(encoding='utf-8'))
        changes = (br or {}).get('changes') or {}
        m = changes.get('macro') or {}
        
        bullets = []
        if 'DXY_d1' in m:
            bullets.append(f"DXY (1j): {round(float(m['DXY_d1'])*100, 2)}%")
        if 'UST10Y_bp_d1' in m:
            bullets.append(f"UST10Y (1j): {round(float(m['UST10Y_bp_d1']), 1)} bp")
        if 'Gold_d1' in m:
            bullets.append(f"Or (1j): {round(float(m['Gold_d1'])*100, 2)}%")
        
        if not bullets:
            bullets.append("Aucun mouvement significatif")
        
        return dbc.Card([
            dbc.CardHeader("Mouvements macro récents"),
            dbc.CardBody([html.Li(b) for b in bullets])
        ])
    except Exception:
        return dbc.Card([
            dbc.CardHeader("Mouvements récents"),
            dbc.CardBody(dbc.Alert("Erreur de lecture.", color="warning"))
        ])


def layout():
    """
    Page Alerts — Qualité & Mouvements Inhabituels
    """
    return html.Div([
        html.H3("⚠️ Alerts"),
        html.Small("Qualité des données et mouvements inhabituels"),
        html.Hr(),
        dbc.Row([
            dbc.Col(_quality_card(), md=6),
            dbc.Col(_movements_card(), md=6),
        ], className="mb-3"),
    ], id='alerts-root')
