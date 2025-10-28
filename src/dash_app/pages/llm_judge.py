from __future__ import annotations

import json
from pathlib import Path
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
from dash import dash_table
from dash import Output, Input, State

try:
    from hub import profiler as _prof
except Exception:
    class _Dummy:
        def log_event(self, *a, **k):
            pass
    _prof = _Dummy()  # type: ignore


def _latest_llm_agents() -> dict:
    base = Path('data/forecast')
    parts = sorted(base.glob('dt=*/llm_agents.json'))
    if not parts:
        return {}
    try:
        return json.loads(parts[-1].read_text(encoding='utf-8'))
    except Exception:
        return {}


def _judge_rows_and_summary() -> tuple[list[dict], dict]:
    js = _latest_llm_agents()
    tickers = js.get('tickers') or []
    if not tickers:
        return [], { 'total': 0, 'ups': 0, 'downs': 0, 'flats': 0, 'avg_exp': 0.0, 'avg_conf': 0.0 }
    rows = []
    for t in tickers:
        m = (t.get('models') or [{}])[0]
        rows.append({
            'ticker': t.get('ticker'),
            'direction': m.get('direction'),
            'expected_return': m.get('expected_return'),
            'confidence': m.get('confidence'),
            'rationale': m.get('rationale'),
            'provider': m.get('name') or m.get('source'),
        })
    total = len(tickers)
    ups = sum(1 for t in tickers if ((t.get('models') or [{}])[0].get('direction') == 'up'))
    downs = sum(1 for t in tickers if ((t.get('models') or [{}])[0].get('direction') == 'down'))
    flats = total - ups - downs
    exp = [float((t.get('models') or [{}])[0].get('expected_return') or 0.0) for t in tickers]
    conf = [float((t.get('models') or [{}])[0].get('confidence') or 0.0) for t in tickers]
    summary = {
        'total': total,
        'ups': ups,
        'downs': downs,
        'flats': flats,
        'avg_exp': (sum(exp)/len(exp)) if exp else 0.0,
        'avg_conf': (sum(conf)/len(conf)) if conf else 0.0,
    }
    return rows, summary


def _current_rows() -> list[dict]:
    rows, _ = _judge_rows_and_summary()
    return rows


def _judge_table() -> dash_table.DataTable | dbc.Alert:
    rows, _ = _judge_rows_and_summary()
    if not rows:
        return dbc.Alert("Aucun verdict LLM disponible. Lancez la construction de contexte puis l'agent LLM.", color="info")
    tbl = dash_table.DataTable(
        id='judge-table',
        columns=[
            {"id": 'ticker', "name": 'Ticker'},
            {"id": 'direction', "name": 'Direction'},
            {"id": 'expected_return', "name": 'Exp. Return'},
            {"id": 'confidence', "name": 'Confidence'},
            {"id": 'provider', "name": 'Provider'},
        ],
        data=rows,
        sort_action='native', filter_action='native', page_size=20,
        export_format='csv',
        style_table={'overflowX': 'auto'},
        style_cell={'padding': '6px', 'fontSize': 12},
        style_data_conditional=[
            {
                'if': {'filter_query': '{direction} = "up"'},
                'backgroundColor': '#0a2e0a'
            },
            {
                'if': {'filter_query': '{direction} = "down"'},
                'backgroundColor': '#2e0a0a'
            },
        ]
    )
    return tbl


def _judge_reasoning() -> html.Div:
    rows, s = _judge_rows_and_summary()
    if not rows:
        return html.Div(id='judge-reasoning', children=html.Small("(vide)"))
    return html.Div(id='judge-reasoning', children=[
        html.Small(
            f"Tickers: {s['total']} • Up: {s['ups']} • Down: {s['downs']} • Flat: {s['flats']} • Avg ER: {s['avg_exp']:.2%} • Avg Conf: {s['avg_conf']:.1%}"
        )
    ])


def _dir_badge(direction: str) -> dbc.Badge:
    direction = (direction or 'flat').lower()
    if direction == 'up':
        return dbc.Badge("↑ Up", color="success", className="ms-2")
    if direction == 'down':
        return dbc.Badge("↓ Down", color="danger", className="ms-2")
    return dbc.Badge("→ Flat", color="secondary", className="ms-2")


def _build_cards(min_conf: float = 0.6):
    rows, _ = _judge_rows_and_summary()
    if not rows:
        return html.Div()
    # Filter by confidence and order by expected_return desc
    filtered = [r for r in rows if (r.get('confidence') or 0.0) >= (min_conf or 0.0)]
    filtered.sort(key=lambda r: float(r.get('expected_return') or 0.0), reverse=True)
    def _rec_label(r):
        dir = (r.get('direction') or 'flat').lower()
        er = float(r.get('expected_return') or 0.0)
        conf = float(r.get('confidence') or 0.0)
        if dir == 'up' and er >= 0.02 and conf >= 0.6:
            return 'Achat (1m)', 'success'
        if dir == 'down' and er <= -0.02 and conf >= 0.6:
            return 'Vente/Allègement (1m)', 'danger'
        return 'Surveiller', 'secondary'
    cards = []
    for r in filtered:
        label, color = _rec_label(r)
        er = float(r.get('expected_return') or 0.0)
        conf = float(r.get('confidence') or 0.0)
        cards.append(
            dbc.Card([
                dbc.CardHeader([html.B(r['ticker']), _dir_badge(r.get('direction')), dbc.Badge(label, color=color, className='ms-2')]),
                dbc.CardBody([
                    html.Div([
                        html.Small("Expected Return: "), html.B(f"{er*100:.1f}%"),
                        html.Small(" • Confidence: "), html.B(f"{conf*100:.0f}%")
                    ], className='mb-1'),
                    dbc.Progress(value=int(conf*100), color='info', style={'height':'8px'}, className='mb-2'),
                    html.Small((r.get('rationale') or '—')[:240])
                ]),
                dbc.CardFooter(html.Small(r.get('provider') or '—'))
            ], className='mb-2')
        )
    # Layout as 3 columns grid
    col_size = max(1, min(4, (len(cards)+2)//3))
    return dbc.Row([dbc.Col(c, md=12//col_size) for c in cards])


def layout() -> html.Div:
    return html.Div([
        html.H3("LLM Judge — Verdicts & Actions"),
        dbc.Alert([
            html.B("Comment lire cette page :"), html.Br(),
            html.Small("• Le modèle LLM propose une direction (↑/→/↓), un gain attendu (ER%) et une confiance."), html.Br(),
            html.Small("• Les cartes résument les meilleures idées (filtrées par confiance)."), html.Br(),
            html.Small("• Horizon visé : 1 mois. Ce n’est pas un conseil financier."),
        ], color='dark', className='mb-2'),
        # Controls: model, min confidence, ER cap
        dbc.Row([
            dbc.Col([
                html.Small("Model"),
                dcc.Dropdown(
                    id='judge-model',
                    options=[
                        {'label':'DeepSeek V3 Turbo','value':'deepseek-ai/DeepSeek-V3-0324-Turbo'},
                        {'label':'DeepSeek V3','value':'deepseek-ai/DeepSeek-V3'},
                        {'label':'Qwen 235B Thinking','value':'Qwen/Qwen3-235B-A22B-Thinking-2507'},
                        {'label':'Qwen Next 80B','value':'Qwen/Qwen3-Next-80B-A3B-Instruct'},
                        {'label':'GLM-4.5','value':'zai-org/GLM-4.5'},
                        {'label':'Llama 3.3 70B','value':'meta-llama/Llama-3.3-70B-Instruct-Turbo'},
                    ],
                    value='deepseek-ai/DeepSeek-V3-0324-Turbo', clearable=False,
                    style={'minWidth':'280px'}
                )
            ], md=4),
            dbc.Col([
                html.Small("Min confidence"),
                dcc.Slider(id='judge-min-conf', min=0.0, max=1.0, step=0.05, value=0.6,
                           marks={0.0:'0%',0.5:'50%',1.0:'100%'})
            ], md=4),
            dbc.Col([
                html.Small("Cap |expected_return|"),
                dcc.Slider(id='judge-max-er', min=0.05, max=0.15, step=0.01, value=0.08,
                           marks={0.05:'5%',0.10:'10%',0.15:'15%'})
            ], md=4),
        ], className='mb-2'),
        dbc.Row([
            dbc.Col([
                html.Small("Tickers (comma, optionnel)"),
                dcc.Input(id='judge-tickers', type='text', placeholder='AAPL,MSFT,NGD.TO', style={'width':'100%'})
            ], md=8),
            dbc.Col([
                html.Small("Seuil ER% Achat"),
                dcc.Slider(id='judge-buy-thres', min=0.0, max=0.1, step=0.005, value=0.02,
                           marks={0.0:'0%',0.02:'2%',0.05:'5%',0.1:'10%'})
            ], md=4),
        ], className='mb-2'),
        html.Div([
            dbc.Button("1) Build Contexts", id='btn-ctx', color='secondary', size='sm', className='me-2'),
            dbc.Button("2) Run LLM Forecast", id='btn-llm', color='primary', size='sm'),
            dbc.Button("Download Top Picks CSV", id='judge-dl-csv', color='light', size='sm', className='ms-2'),
            dcc.Download(id='judge-dl')
        ], className='mb-2'),
        dcc.Loading(dcc.Textarea(id='judge-actions-output', value='(click a button to run actions)', style={'width':'100%','height':'120px'}), type='default'),
        html.Hr(),
        html.Div(id='judge-exec-summary', className='mb-2'),
        html.Div(_judge_reasoning()),
        html.Div(id='judge-cards', children=_build_cards(0.6)),
        html.Div(id='judge-table-wrap', children=_judge_table()),
    ])


def _run_cmd(cmd: list[str], extra_env: dict | None = None) -> str:
    import subprocess
    try:
        t0 = __import__('time').perf_counter()
        env = None
        if extra_env:
            import os as _os
            env = {**_os.environ.copy(), **{k: str(v) for k,v in extra_env.items()}}
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
        dt_ms = int((__import__('time').perf_counter() - t0) * 1000)
        _prof.log_event("subprocess", {
            "cmd": cmd,
            "returncode": out.returncode,
            "duration_ms": dt_ms,
            "stdout_len": len(out.stdout or ''),
            "stderr_len": len(out.stderr or ''),
        })
        return (out.stdout or '').strip() + ("\nSTDERR:\n" + (out.stderr or '').strip() if out.stderr else '')
    except Exception as e:
        _prof.log_event("error", {"where": "_run_cmd", "cmd": cmd, "error": str(e)})
        return f"Erreur: {e}"


@dash.callback(
    Output('judge-actions-output','value'),
    Output('judge-table-wrap','children'),
    Output('judge-reasoning','children'),
    Output('judge-cards','children'),
    Input('btn-ctx','n_clicks'),
    Input('btn-llm','n_clicks'),
    State('judge-model','value'),
    State('judge-max-er','value'),
    State('judge-min-conf','value'),
    prevent_initial_call=True)
def on_actions(_n_ctx, _n_llm, model, max_er, min_conf, tickers):
    # For reliability: always run both steps on any click (fast + idempotent)
    _prof.log_event("callback", {"id": "llm_judge.on_actions", "action": "start"})
    cmd_ctx = ["python3", "-m", "src.agents.llm_context_builder_agent"]
    if tickers and str(tickers).strip():
        cmd_ctx += ["--tickers", str(tickers).strip()]
    out1 = _run_cmd(cmd_ctx)  # builds data/llm/context
    # Run LLM with chosen model and ER cap; always enable g4f usage if available
    out2 = _run_cmd(["python3", "scripts/llm_forecast_agent.py"], extra_env={
        'LLM_USE_G4F': '1',
        'LLM_MODEL': model or 'deepseek-ai/DeepSeek-V3-0324-Turbo',
        'LLM_MAX_ER': max_er or 0.08,
    })
    combined = (out1 or '').strip() + "\n----\n" + (out2 or '').strip()
    table = _judge_table()
    summary_div = _judge_reasoning().children
    _prof.log_event("callback", {"id": "llm_judge.on_actions", "action": "end"})
    cards = _build_cards(min_conf)
    return combined, table, summary_div, cards


# (moved earlier)


@dash.callback(Output('judge-cards','children'), Input('judge-min-conf','value'))
def on_filter_cards(min_conf):
    return _build_cards(min_conf or 0.6)


def _build_exec_summary(min_conf: float, buy_thres: float) -> str:
    rows = _current_rows()
    if not rows:
        return "(aucune donnée)"
    picks = []
    watch = []
    for r in rows:
        er = float(r.get('expected_return') or 0.0)
        conf = float(r.get('confidence') or 0.0)
        dir = str(r.get('direction') or 'flat').lower()
        if conf >= (min_conf or 0.6) and dir == 'up' and er >= (buy_thres or 0.02):
            picks.append((r['ticker'], er, conf))
        else:
            watch.append((r['ticker'], er, conf))
    picks.sort(key=lambda x: x[1], reverse=True)
    head = ", ".join([f"{t} ({er*100:.1f}% / {conf*100:.0f}%)" for t,er,conf in picks[:5]]) or "—"
    others = len(picks) - min(len(picks), 5)
    tail = f" (+{others})" if others>0 else ""
    return f"Recommandations (≥{buy_thres*100:.0f}% ER & ≥{min_conf*100:.0f}% conf) : {head}{tail}"


@dash.callback(Output('judge-exec-summary','children'), Input('judge-min-conf','value'), Input('judge-buy-thres','value'))
def on_summary(min_conf, buy_thres):
    txt = _build_exec_summary(float(min_conf or 0.6), float(buy_thres or 0.02))
    return dbc.Alert(html.Small(txt), color='secondary')


@dash.callback(Output('judge-dl','data'), Input('judge-dl-csv','n_clicks'), State('judge-min-conf','value'), State('judge-buy-thres','value'), prevent_initial_call=True)
def on_download_csv(n, min_conf, buy_thres):
    rows = _current_rows()
    if not rows:
        return dash.no_update
    min_conf = float(min_conf or 0.6)
    buy_thres = float(buy_thres or 0.02)
    picks = []
    for r in rows:
        er = float(r.get('expected_return') or 0.0)
        conf = float(r.get('confidence') or 0.0)
        dir = str(r.get('direction') or 'flat').lower()
        if conf >= min_conf and dir == 'up' and er >= buy_thres:
            picks.append({
                'ticker': r['ticker'],
                'direction': r.get('direction'),
                'expected_return': er,
                'confidence': conf,
                'provider': r.get('provider'),
            })
    if not picks:
        return dash.no_update
    # build CSV string
    cols = ['ticker','direction','expected_return','confidence','provider']
    lines = [','.join(cols)]
    for p in picks:
        lines.append(','.join(str(p[c]) for c in cols))
    csv_str = '\n'.join(lines)
    return dcc.send_string(csv_str, filename='llm_top_picks.csv')
