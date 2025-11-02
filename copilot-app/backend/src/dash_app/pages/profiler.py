from __future__ import annotations

import json
from pathlib import Path
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
from dash import Output, Input

try:
    from hub import profiler as _prof
except Exception:
    class _Dummy:
        def read_last(self, *a, **k):
            return []
        def clear(self):
            pass
    _prof = _Dummy()  # type: ignore


def _render_events() -> tuple[list[dict], str]:
    rows = []
    raw_lines = []
    events = _prof.read_last(200) if hasattr(_prof, 'read_last') else []
    for e in events:
        p = e.get('payload') or {}
        rows.append({
            'ts': e.get('ts'),
            'type': e.get('type'),
            'path': p.get('path') or p.get('cmd') or p.get('id') or '',
            'status': p.get('status') or p.get('returncode'),
            'duration_ms': p.get('duration_ms'),
        })
        raw_lines.append(json.dumps(e, ensure_ascii=False))
    return rows, "\n".join(raw_lines)


def layout() -> html.Div:
    rows, raw = _render_events()
    table = dash.dash_table.DataTable(
        id='profiler-table',
        columns=[{'id':'ts','name':'ts'},{'id':'type','name':'type'},{'id':'path','name':'path'},{'id':'status','name':'status'},{'id':'duration_ms','name':'duration_ms'}],
        data=rows,
        page_size=15,
        sort_action='native',
        filter_action='native',
        style_table={'overflowX':'auto'},
        style_cell={'padding':'6px','fontSize':12}
    )
    return html.Div([
        html.H3('Profiler — Events & Logs'),
        html.Div([
            dbc.Button('Refresh', id='prof-refresh', size='sm', className='me-2'),
            dbc.Button('Clear', id='prof-clear', color='danger', size='sm')
        ], className='mb-2'),
        table,
        html.Hr(),
        html.Small('Raw (JSONL):'),
        html.Pre(id='prof-raw', children=raw, style={'maxHeight':'240px','overflowY':'auto'}) ,
        dcc.Interval(id='prof-interval', interval=3000, n_intervals=0)
    ])


@dash.callback(
    Output('profiler-table','data'),
    Output('prof-raw','children'),
    Input('prof-interval','n_intervals'),
    Input('prof-refresh','n_clicks'),
    prevent_initial_call=True
)
def _tick(_n, _c):
    rows, raw = _render_events()
    return rows, raw


@dash.callback(Output('prof-raw','children'), Input('prof-clear','n_clicks'), prevent_initial_call=True)
def _clear(_):
    try:
        _prof.clear()
    except Exception:
        pass
    return ''

