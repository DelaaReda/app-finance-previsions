from __future__ import annotations

import json
import subprocess
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output


def _latest_partition(base: Path) -> Path | None:
    parts = sorted(base.glob("dt=*/summary.json"))
    return parts[-1].parent if parts else None


def _load_summary(part: Path) -> dict:
    try:
        return json.loads((part / "summary.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_trace(part: Path) -> dict:
    try:
        return json.loads((part / "trace_raw.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def _render_body() -> list:
    base = Path("data/llm_summary")
    part = _latest_partition(base)
    if not part:
        return [
            dbc.Alert("Aucun résumé trouvé (data/llm_summary/dt=*/summary.json).", color="info"),
            dbc.Button("Relancer maintenant", id="llm-run", color="primary"),
            dcc.Loading(html.Pre(id="llm-run-log", style={"whiteSpace": "pre-wrap"})),
        ]

    summary = _load_summary(part)
    trace = _load_trace(part)

    cards = dbc.Row([
        dbc.Col(dbc.Card([dbc.CardHeader("Régime"), dbc.CardBody(html.H4(summary.get("regime") or "—"))]), md=3),
        dbc.Col(dbc.Card([dbc.CardHeader("Risque"), dbc.CardBody(html.H4(summary.get("risk_level") or "—"))]), md=3),
        dbc.Col(dbc.Card([dbc.CardHeader("Biais 7j"), dbc.CardBody(html.H4(summary.get("outlook_days_7") or "—"))]), md=3),
        dbc.Col(dbc.Card([dbc.CardHeader("Biais 30j"), dbc.CardBody(html.H4(summary.get("outlook_days_30") or "—"))]), md=3),
    ], className="mb-3")

    drivers = summary.get("key_drivers") or []
    drivers_list = html.Ul([html.Li(str(x)) for x in drivers]) if drivers else html.Small("—")

    contribs = summary.get("contributors") or []
    table = dbc.Table([
        html.Thead(html.Tr([html.Th(h) for h in [
            "source", "model", "horizon", "symbol", "score", "prediction", "rationale"
        ]])),
        html.Tbody([
            html.Tr([html.Td(str(row.get(k, ""))) for k in [
                "source", "model", "horizon", "symbol", "score", "prediction", "rationale"
            ]]) for row in contribs
        ])
    ], bordered=True, hover=True, striped=True, size="sm")

    return [
        html.Small(f"Partition: {part.name}"),
        html.Div(cards),
        html.H5("Facteurs clés"),
        drivers_list,
        html.H5("Contributeurs"),
        table,
        dbc.Row([dbc.Col(dbc.Button("Relancer maintenant", id="llm-run", color="primary"), md=3)], className="my-2"),
        dcc.Loading(html.Pre(id="llm-run-log", style={"whiteSpace": "pre-wrap", "maxHeight": "40vh", "overflowY": "auto"})),
        html.Hr(),
        html.Details([html.Summary("Entrées & Trace brute"), html.Pre(json.dumps(trace, ensure_ascii=False, indent=2)[:40000], style={"whiteSpace": "pre-wrap"})]),
    ]


def layout() -> html.Div:
    return html.Div([
        html.H3("LLM Summary"),
        html.Div(id="llm-content", children=_render_body()),
    ], className="p-3")


@callback(
    Output("llm-run-log", "children"),
    Output("llm-content", "children"),
    Input("llm-run", "n_clicks"),
    prevent_initial_call=True,
)
def _run_now(n):
    try:
        p = subprocess.Popen(["make", "llm-summary-run"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        out, _ = p.communicate(timeout=600)
        # re-render content after run
        body = _render_body()
        return out[-40000:], body
    except Exception as e:
        return f"Erreur lors de l'exécution: {e}", dash.no_update
