from __future__ import annotations

from pathlib import Path
import json
import os
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State
import dash
try:
    from hub.logging_setup import get_logger  # type: ignore
    from hub import profiler as _prof  # type: ignore
    _log = get_logger("watchlist")  # type: ignore
except Exception:
    class _P:
        def log_event(self,*a,**k): pass
    class _L:
        def info(self,*a,**k): pass
        def exception(self,*a,**k): pass
    _prof = _P()  # type: ignore
    _log = _L()   # type: ignore


def _current_watchlist() -> str:
    """Récupère la watchlist actuelle depuis l'env ou le fichier"""
    wl = os.getenv('WATCHLIST', '')
    if not wl:
        fp = Path('data/watchlist.json')
        if fp.exists():
            try:
                data = json.loads(fp.read_text(encoding='utf-8'))
                wl = ','.join(data.get('watchlist', []))
            except Exception:
                pass
    return wl if wl else "NGD.TO,AEM.TO,ABX.TO,K.TO,GDX"


def layout():
    """
    Page Watchlist — Gestion de la liste de surveillance
    """
    current = _current_watchlist()
    
    return html.Div([
        html.H3("📜 Watchlist"),
        html.Small("Gestion de la liste de tickers à surveiller"),
        html.Hr(),
        
        dbc.Card([
            dbc.CardHeader("Watchlist actuelle"),
            dbc.CardBody([
                html.Small("Variable d'environnement WATCHLIST ou data/watchlist.json"),
                html.Code(current, className="d-block mt-2 p-2 bg-dark text-light"),
            ])
        ], className="mb-3"),
        
        dbc.Card([
            dbc.CardHeader("Modifier"),
            dbc.CardBody([
                dcc.Textarea(
                    id='watchlist-text',
                    value=current,
                    style={"width": "100%", "height": "120px", "fontFamily": "monospace"},
                    placeholder="Tickers séparés par des virgules (ex: AAPL,MSFT,GOOGL)"
                ),
                html.Div([
                    dbc.Button("💾 Enregistrer", id="watchlist-save-btn", color="primary", className="me-2 mt-2"),
                    dbc.Button("📋 Générer commande export", id="watchlist-export-btn", color="secondary", className="mt-2"),
                ]),
                html.Div(id='watchlist-result', className="mt-3"),
            ])
        ])
    ], id='watchlist-root')


@dash.callback(
    Output('watchlist-result', 'children'),
    Input('watchlist-save-btn', 'n_clicks'),
    Input('watchlist-export-btn', 'n_clicks'),
    State('watchlist-text', 'value'),
    prevent_initial_call=True
)
def handle_watchlist_action(save_clicks, export_clicks, text):
    """Gère les actions sur la watchlist"""
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    try:
        # Parse tickers
        tickers = [x.strip().upper() for x in (text or '').split(',') if x.strip()]
        _prof.log_event("callback", {"id": "watchlist.action", "button": button_id, "count": len(tickers)})
        try:
            _log.info("watchlist.action.start", extra={"ctx": {"button": button_id, "count": len(tickers)}})
        except Exception:
            pass

        if button_id == 'watchlist-save-btn':
            # Save to file
            Path('data').mkdir(parents=True, exist_ok=True)
            Path('data/watchlist.json').write_text(
                json.dumps({'watchlist': tickers}, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
            try:
                _log.info("watchlist.save.ok", extra={"ctx": {"count": len(tickers)}})
            except Exception:
                pass
            return dbc.Alert(f"✅ Enregistré: {len(tickers)} tickers dans data/watchlist.json", color="success")
        
        elif button_id == 'watchlist-export-btn':
            # Generate export command
            cmd = f"export WATCHLIST={','.join(tickers)}"
            try:
                _log.info("watchlist.export.cmd", extra={"ctx": {"cmd": cmd}})
            except Exception:
                pass
            return dbc.Card([
                dbc.CardBody([
                    html.Small("Commande à exécuter dans votre shell:"),
                    html.Code(cmd, className="d-block mt-2 p-2 bg-dark text-light"),
                    html.Small("Copiez/collez cette commande pour l'utiliser dans les scripts.", className="mt-2 d-block"),
                ])
            ])
    
    except Exception as e:
        _prof.log_event("error", {"where": "watchlist.action", "button": button_id, "error": str(e)})
        try:
            _log.exception("watchlist.action.fail", extra={"ctx": {"button": button_id, "error": str(e)}})
        except Exception:
            pass
        return dbc.Alert(f"❌ Erreur: {e}", color="danger")
    
    return dash.no_update
