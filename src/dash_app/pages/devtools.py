from __future__ import annotations

import os
import pathlib
import subprocess
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc

DEV_ENABLED = os.getenv("DEVTOOLS_ENABLED", "0") == "1"


def layout():
    if not DEV_ENABLED:
        return html.Div([dbc.Alert("DevTools désactivé (DEVTOOLS_ENABLED=0).", color="secondary")])
    return html.Div([
        html.H2("DevTools"),
        dbc.Button("Exécuter smoke (dash-smoke)", id="btn-smoke", n_clicks=0, color="primary", className="me-2"),
        dbc.Button("UI Health (screenshots)", id="btn-uihealth", n_clicks=0, color="info"),
        html.Hr(),
        html.H4("Résultats récents"),
        dcc.Loading(html.Pre(id="devtools-output", style={"whiteSpace": "pre-wrap", "maxHeight": "40vh", "overflowY": "auto"})),
        html.Hr(),
        html.H4("Derniers screenshots"),
        html.Ul(id="devtools-shots"),
    ], className="p-3")


def _run(cmd: list[str]) -> str:
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out, _ = p.communicate()
    return out


@callback(
    Output("devtools-output", "children"),
    Output("devtools-shots", "children"),
    Input("btn-smoke", "n_clicks"),
    Input("btn-uihealth", "n_clicks"),
    prevent_initial_call=True,
)
def on_actions(n_smoke, n_uih):
    ctx = dcc.callback_context
    if not DEV_ENABLED:
        return "DevTools disabled.", []
    shots = []
    msg = ""
    if ctx.triggered and "btn-smoke" in ctx.triggered[0]["prop_id"]:
        msg += "$ make dash-smoke\n" + _run(["make", "dash-smoke"]) + "\n"
    if ctx.triggered and "btn-uihealth" in ctx.triggered[0]["prop_id"]:
        msg += "$ make ui-health\n" + _run(["make", "ui-health"]) + "\n"
    # Lister derniers PNG
    shots_dir = pathlib.Path("artifacts/ui_health")
    if shots_dir.exists():
        last = sorted(shots_dir.glob("*.png"))[-8:]
        shots = [html.Li(html.A(x.name, href=f"/assets/{x.name}", target="_blank")) for x in last]
    return msg[-40000:], shots

