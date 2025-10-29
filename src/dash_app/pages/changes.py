"""
Page Changes — Changements depuis la veille
Affiche les changements de régime macro, risque composite, Top-N et brief macro.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple, Optional

import pandas as pd
import dash_bootstrap_components as dbc
from dash import html, dash_table, Input, Output, callback


def _latest_prev(globpat: str) -> Tuple[Optional[Path], Optional[Path]]:
    """Retourne les deux dernières partitions."""
    parts = sorted(Path().glob(globpat))
    if len(parts) >= 2:
        return parts[-1], parts[-2]
    elif parts:
        return parts[-1], None
    return None, None


def layout() -> html.Div:
    """Layout principal de la page Changes."""
    return html.Div([
        html.H3("🔄 What Changed — Depuis la veille", className="mb-3"),
        
        dbc.Card([
            dbc.CardHeader(html.H5("Régime macro")),
            dbc.CardBody(id="changes-regime-body"),
        ], className="mb-4"),
        
        dbc.Card([
            dbc.CardHeader(html.H5("Risque (composite)")),
            dbc.CardBody(id="changes-risk-body"),
        ], className="mb-4"),
        
        dbc.Card([
            dbc.CardHeader(html.H5("Top-N (1m) — changements")),
            dbc.CardBody(id="changes-topn-body"),
        ], className="mb-4"),
        
        dbc.Card([
            dbc.CardHeader(html.H5("Brief Macro")),
            dbc.CardBody(id="changes-brief-body"),
        ], className="mb-4"),
    ])


@callback(
    Output("changes-regime-body", "children"),
    Input("changes-regime-body", "id"),  # trigger on mount
)
def render_regime_changes(_):
    """Affiche les changements de régime macro."""
    try:
        cur, prev = _latest_prev('data/macro/regime/dt=*/regime.json')
        
        if not cur:
            return dbc.Alert("Aucune donnée de régime disponible.", color="info")
        
        cobj = json.loads(Path(cur).read_text(encoding='utf-8'))
        pobj = json.loads(Path(prev).read_text(encoding='utf-8')) if prev and Path(prev).exists() else {}
        
        def _top(o):
            pr = o.get('probs') or {}
            return (sorted(pr.items(), key=lambda x: -x[1])[0] if pr else (None, None))
        
        cn, cp = _top(cobj)
        pn, pp = _top(pobj)
        
        # Format display
        current_display = f"{cn} ({cp:.1%})" if cn and cp else "N/A"
        previous_display = f"{pn} ({pp:.1%})" if pn and pp else "N/A"
        
        changed = cn != pn if cn and pn else False
        
        return dbc.Row([
            dbc.Col([
                html.P("Actuel:", className="text-muted mb-1"),
                html.H5(current_display, className=f"text-{'success' if not changed else 'warning'}"),
            ], width=6),
            dbc.Col([
                html.P("Précédent:", className="text-muted mb-1"),
                html.H5(previous_display),
            ], width=6),
        ])
    
    except Exception as e:
        return dbc.Alert(f"Erreur lors du chargement des régimes: {e}", color="warning")


@callback(
    Output("changes-risk-body", "children"),
    Input("changes-risk-body", "id"),  # trigger on mount
)
def render_risk_changes(_):
    """Affiche les changements de risque composite."""
    try:
        cur, prev = _latest_prev('data/risk/dt=*/risk.json')
        
        if not cur:
            return dbc.Alert("Aucune donnée de risque disponible.", color="info")
        
        cobj = json.loads(Path(cur).read_text(encoding='utf-8'))
        pobj = json.loads(Path(prev).read_text(encoding='utf-8')) if prev and Path(prev).exists() else {}
        
        current = cobj.get('composite')
        previous = pobj.get('composite')
        
        # Format display
        current_display = f"{current:.2f}" if current is not None else "N/A"
        previous_display = f"{previous:.2f}" if previous is not None else "N/A"
        
        # Calculate change
        if current is not None and previous is not None:
            delta = current - previous
            delta_display = f"{delta:+.2f}"
            color = "danger" if delta > 0 else "success"
        else:
            delta_display = "N/A"
            color = "secondary"
        
        return dbc.Row([
            dbc.Col([
                html.P("Actuel:", className="text-muted mb-1"),
                html.H5(current_display),
            ], width=4),
            dbc.Col([
                html.P("Précédent:", className="text-muted mb-1"),
                html.H5(previous_display),
            ], width=4),
            dbc.Col([
                html.P("Δ:", className="text-muted mb-1"),
                html.H5(delta_display, className=f"text-{color}"),
            ], width=4),
        ])
    
    except Exception as e:
        return dbc.Alert(f"Erreur lors du chargement des risques: {e}", color="warning")


@callback(
    Output("changes-topn-body", "children"),
    Input("changes-topn-body", "id"),  # trigger on mount
)
def render_topn_changes(_):
    """Affiche les changements dans le Top-N."""
    try:
        cur, prev = _latest_prev('data/forecast/dt=*/final.parquet')
        
        if not cur:
            return dbc.Alert("Aucune donnée de forecast disponible.", color="info")
        
        cdf = pd.read_parquet(cur)
        pdf = pd.read_parquet(prev) if prev and Path(prev).exists() else pd.DataFrame(columns=cdf.columns)
        
        # Get Top 10 for 1m horizon
        ctop = cdf[cdf['horizon'] == '1m'].sort_values('final_score', ascending=False).head(10)
        ptop = pdf[pdf['horizon'] == '1m'].sort_values('final_score', ascending=False).head(10) if not pdf.empty else pd.DataFrame()
        
        # Build position map
        pos_prev = {t: i for i, t in enumerate(list(ptop['ticker']))} if not ptop.empty else {}
        
        rows = []
        for i, ticker in enumerate(ctop['ticker']):
            prev_pos = pos_prev.get(ticker)
            rows.append({
                'ticker': ticker,
                'pos_now': i + 1,
                'pos_prev': (prev_pos + 1) if prev_pos is not None else None,
                'movement': '🆕 New' if prev_pos is None else (
                    f'↑ {prev_pos - i}' if prev_pos > i else (
                        f'↓ {i - prev_pos}' if prev_pos < i else '='
                    )
                )
            })
        
        df = pd.DataFrame(rows)
        
        return dash_table.DataTable(
            columns=[
                {"name": "Ticker", "id": "ticker"},
                {"name": "Position Actuelle", "id": "pos_now"},
                {"name": "Position Précédente", "id": "pos_prev"},
                {"name": "Mouvement", "id": "movement"},
            ],
            data=df.to_dict('records'),
            style_cell={'textAlign': 'left', 'padding': '8px'},
            style_header={'backgroundColor': '#343a40', 'fontWeight': 'bold'},
            style_data_conditional=[
                {
                    'if': {'filter_query': '{movement} contains "New"'},
                    'backgroundColor': '#28a745',
                    'color': 'white',
                },
            ],
        )
    
    except Exception as e:
        return dbc.Alert(f"Erreur lors du chargement du Top-N: {e}", color="warning")


@callback(
    Output("changes-brief-body", "children"),
    Input("changes-brief-body", "id"),  # trigger on mount
)
def render_brief_changes(_):
    """Affiche le brief macro."""
    try:
        cur, prev = _latest_prev('data/forecast/dt=*/brief.json')
        
        if not cur:
            return dbc.Alert("Aucun brief disponible.", color="info")
        
        cobj = json.loads(Path(cur).read_text(encoding='utf-8'))
        
        changes = cobj.get('changes') or {}
        macro_changes = changes.get('macro') or {}
        
        # Extract key metrics
        bullets = []
        if 'DXY_d1' in macro_changes:
            bullets.append(f"DXY (1j): {round(float(macro_changes['DXY_d1'])*100, 2)}%")
        if 'UST10Y_bp_d1' in macro_changes:
            bullets.append(f"UST10Y (1j): {round(float(macro_changes['UST10Y_bp_d1']), 1)} bp")
        if 'Gold_d1' in macro_changes:
            bullets.append(f"Or (1j): {round(float(macro_changes['Gold_d1'])*100, 2)}%")
        
        if not bullets:
            return dbc.Alert("Aucun changement macro significatif.", color="info")
        
        return html.Ul([html.Li(b) for b in bullets])
    
    except Exception as e:
        return dbc.Alert(f"Erreur lors du chargement du brief: {e}", color="warning")
