"""
Page Alerts — Qualité & Mouvements Inhabituels
Affiche les problèmes de qualité des données, mouvements macro et watchlist, et earnings à venir.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table, Input, Output, State, callback

from dash_app.data.loader import load_latest_json, load_latest_jsonl


def layout() -> html.Div:
    """Layout principal de la page Alerts."""
    return html.Div([
        html.H3("⚠️ Alerts — Qualité & Mouvements Inhabituels", className="mb-3"),
        
        # Section 1: Data Quality Issues
        dbc.Card([
            dbc.CardHeader(html.H5("Qualité des données (dernier rapport)")),
            dbc.CardBody(id="alerts-quality-body"),
        ], className="mb-4"),
        
        # Section 2: Mouvements récents (watchlist)
        dbc.Card([
            dbc.CardHeader([
                html.H5("Mouvements récents (watchlist)", className="mb-2"),
                html.Div([
                    html.Label("Seuil absolu (%, 1j):", className="me-2"),
                    dcc.Slider(
                        id="alerts-threshold-slider",
                        min=0.0,
                        max=5.0,
                        step=0.1,
                        value=1.0,
                        marks={i: f"{i}%" for i in range(0, 6)},
                        tooltip={"placement": "bottom", "always_visible": True},
                    ),
                ], className="mb-3"),
            ]),
            dbc.CardBody(id="alerts-moves-body"),
        ], className="mb-4"),
        
        # Section 3: Earnings à venir
        dbc.Card([
            dbc.CardHeader([
                html.H5("Earnings à venir (watchlist)", className="mb-2"),
                html.Div([
                    html.Label("Fenêtre (jours à venir):", className="me-2"),
                    dcc.Slider(
                        id="alerts-earnings-days-slider",
                        min=3,
                        max=60,
                        step=1,
                        value=21,
                        marks={i: str(i) for i in [3, 7, 14, 21, 30, 60]},
                        tooltip={"placement": "bottom", "always_visible": True},
                    ),
                ], className="mb-3"),
            ]),
            dbc.CardBody(id="alerts-earnings-body"),
        ], className="mb-4"),
    ])


@callback(
    Output("alerts-quality-body", "children"),
    Input("alerts-quality-body", "id"),  # trigger on mount
)
def render_quality_issues(_):
    """Affiche les problèmes de qualité des données."""
    try:
        report = load_latest_json('data/quality/dt=*/report.json')
        if not report:
            return dbc.Alert(
                "Aucun rapport de qualité disponible. Consultez Admin → Quality pour générer un rapport.",
                color="info"
            )
        
        # Extract issues from all sections
        issues = []
        for sec in ['news', 'macro', 'prices', 'forecasts', 'features', 'events']:
            s = report.get(sec) or {}
            for it in (s.get('issues') or []):
                issues.append({'section': sec, **it})
        
        if not issues:
            return dbc.Alert("✓ Aucun problème détecté.", color="success")
        
        # Create DataFrame and sort by severity
        df = pd.DataFrame(issues)
        sev_order = {'error': 0, 'warn': 1, 'info': 2}
        df['sev_rank'] = df['sev'].map(lambda x: sev_order.get(str(x).lower(), 9))
        df = df.sort_values(['sev_rank', 'section'])
        df_display = df[['section', 'sev', 'msg']].copy()
        
        return html.Div([
            dash_table.DataTable(
                id='alerts-quality-table',
                columns=[
                    {"name": "Section", "id": "section"},
                    {"name": "Sévérité", "id": "sev"},
                    {"name": "Message", "id": "msg"},
                ],
                data=df_display.to_dict('records'),
                style_cell={'textAlign': 'left', 'padding': '8px'},
                style_header={'backgroundColor': '#343a40', 'fontWeight': 'bold'},
                style_data_conditional=[
                    {
                        'if': {'filter_query': '{sev} = "error"'},
                        'backgroundColor': '#dc3545',
                        'color': 'white',
                    },
                    {
                        'if': {'filter_query': '{sev} = "warn"'},
                        'backgroundColor': '#ffc107',
                        'color': 'black',
                    },
                ],
                page_size=10,
                sort_action="native",
                filter_action="native",
            ),
            html.Div([
                dbc.Button(
                    "📥 Exporter issues (CSV)",
                    id="alerts-quality-export-btn",
                    color="secondary",
                    size="sm",
                    className="mt-2",
                ),
                dcc.Download(id="alerts-quality-download"),
            ]),
        ])
    except Exception as e:
        return dbc.Alert(f"Erreur lors de la lecture du rapport: {e}", color="warning")


@callback(
    Output("alerts-quality-download", "data"),
    Input("alerts-quality-export-btn", "n_clicks"),
    State("alerts-quality-table", "data"),
    prevent_initial_call=True,
)
def export_quality_issues(n_clicks, data):
    """Exporte les issues en CSV."""
    if not data:
        return None
    df = pd.DataFrame(data)
    return dcc.send_data_frame(df.to_csv, "alerts_quality.csv", index=False)


@callback(
    Output("alerts-moves-body", "children"),
    Input("alerts-threshold-slider", "value"),
)
def render_moves(threshold):
    """Affiche les mouvements macro et watchlist."""
    try:
        brief = load_latest_json('data/forecast/dt=*/brief.json')
        if not brief:
            return dbc.Alert(
                "Aucun brief récent. Consultez Admin → Agents Status pour vérifier la fraîcheur des données.",
                color="info"
            )
        
        changes = (brief or {}).get('changes') or {}
        
        # Macro moves
        macro_bullets = []
        m = changes.get('macro') or {}
        if 'DXY_d1' in m:
            macro_bullets.append(f"DXY (1j): {round(float(m['DXY_d1'])*100, 2)}%")
        if 'UST10Y_bp_d1' in m:
            macro_bullets.append(f"UST10Y (1j): {round(float(m['UST10Y_bp_d1']), 1)} bp")
        if 'Gold_d1' in m:
            macro_bullets.append(f"Or (1j): {round(float(m['Gold_d1'])*100, 2)}%")
        
        # Watchlist moves
        w = changes.get('watchlist_moves') or []
        if not w:
            watchlist_component = dbc.Alert("Aucun mouvement watchlist disponible.", color="info")
        else:
            dfw = pd.DataFrame(w)
            dfw['abs'] = dfw['d1'].abs()
            dfw = dfw.sort_values('abs', ascending=False).drop(columns=['abs'])
            dfw['d1_%'] = (dfw['d1'] * 100).round(2)
            filt = dfw[dfw['d1_%'].abs() >= threshold]
            df_display = filt if not filt.empty else dfw
            
            watchlist_component = html.Div([
                dash_table.DataTable(
                    id='alerts-moves-table',
                    columns=[
                        {"name": "Ticker", "id": "ticker"},
                        {"name": "Δ 1j (%)", "id": "d1_%"},
                    ],
                    data=df_display[['ticker', 'd1_%']].to_dict('records'),
                    style_cell={'textAlign': 'left', 'padding': '8px'},
                    style_header={'backgroundColor': '#343a40', 'fontWeight': 'bold'},
                    sort_action="native",
                ),
                html.Div([
                    dbc.Button(
                        "📥 Exporter mouvements (CSV)",
                        id="alerts-moves-export-btn",
                        color="secondary",
                        size="sm",
                        className="mt-2",
                    ),
                    dcc.Download(id="alerts-moves-download"),
                ]),
            ])
        
        return html.Div([
            html.H6("Mouvements Macro (1j)", className="mb-2"),
            html.Ul([html.Li(b) for b in macro_bullets]) if macro_bullets else html.P("Aucune donnée macro.", className="text-muted"),
            html.Hr(),
            html.H6(f"Watchlist (|Δ| ≥ {threshold}%)", className="mb-2"),
            watchlist_component,
        ])
    except Exception as e:
        return dbc.Alert(f"Erreur lors de la lecture du brief: {e}", color="warning")


@callback(
    Output("alerts-moves-download", "data"),
    Input("alerts-moves-export-btn", "n_clicks"),
    State("alerts-moves-table", "data"),
    prevent_initial_call=True,
)
def export_moves(n_clicks, data):
    """Exporte les mouvements en CSV."""
    if not data:
        return None
    df = pd.DataFrame(data)
    return dcc.send_data_frame(df.to_csv, "alerts_moves.csv", index=False)


@callback(
    Output("alerts-earnings-body", "children"),
    Input("alerts-earnings-days-slider", "value"),
)
def render_earnings(days):
    """Affiche les earnings à venir."""
    try:
        earnings = load_latest_json('data/earnings/dt=*/earnings.json')
        if not earnings:
            return dbc.Alert("Aucun earnings.json trouvé. Consultez Admin → Agents Status.", color="info")
        
        evs = earnings.get('events') or []
        if not evs:
            return dbc.Alert("Aucun événement à afficher.", color="info")
        
        rows = []
        for e in evs:
            rows.append({
                'ticker': e.get('ticker'),
                'date': e.get('date'),
                'info': e.get('info', ''),
            })
        
        df = pd.DataFrame(rows)
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # Filter by date window
        now = pd.Timestamp.utcnow().normalize()
        soon = df[(df['date'] >= now) & (df['date'] <= now + pd.Timedelta(days=days))].copy()
        df_display = soon if not soon.empty else df
        df_display = df_display.sort_values('date')
        
        # Format date for display
        df_display['date'] = df_display['date'].dt.strftime('%Y-%m-%d')
        
        return html.Div([
            dash_table.DataTable(
                id='alerts-earnings-table',
                columns=[
                    {"name": "Ticker", "id": "ticker"},
                    {"name": "Date", "id": "date"},
                    {"name": "Info", "id": "info"},
                ],
                data=df_display.to_dict('records'),
                style_cell={'textAlign': 'left', 'padding': '8px'},
                style_header={'backgroundColor': '#343a40', 'fontWeight': 'bold'},
                page_size=10,
                sort_action="native",
            ),
            html.Div([
                dbc.Button(
                    "📥 Exporter earnings (CSV)",
                    id="alerts-earnings-export-btn",
                    color="secondary",
                    size="sm",
                    className="mt-2",
                ),
                dcc.Download(id="alerts-earnings-download"),
            ]),
        ])
    except Exception as e:
        return dbc.Alert(f"Erreur lors de la lecture des earnings: {e}", color="warning")


@callback(
    Output("alerts-earnings-download", "data"),
    Input("alerts-earnings-export-btn", "n_clicks"),
    State("alerts-earnings-table", "data"),
    prevent_initial_call=True,
)
def export_earnings(n_clicks, data):
    """Exporte les earnings en CSV."""
    if not data:
        return None
    df = pd.DataFrame(data)
    return dcc.send_data_frame(df.to_csv, "alerts_earnings.csv", index=False)
