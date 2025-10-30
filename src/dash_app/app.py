from __future__ import annotations

import os
import json
import requests
from pathlib import Path
from typing import Callable, Dict

import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
import time
import os as _os_logging
import logging as _logging
# Initialize global logging early (bridges stdlib -> Loguru and captures warnings)
try:
    import hub.logging_setup as _boot_logging  # side-effect: configure root logging
    # Optional level override via env
    lvl = _os_logging.getenv("AF_LOG_LEVEL")
    if lvl:
        try:
            _boot_logging.setup_logging(level=lvl.upper())
        except Exception:
            pass
    # Expose a named logger and ensure a trace id exists for correlation
    from hub.logging_setup import get_logger, ensure_trace  # type: ignore
    log = get_logger("dash-ui")  # type: ignore
    ensure_trace()  # type: ignore
    # Propagate framework logs to root so they're visible in console/file
    for name, lvl in [("werkzeug", "INFO"), ("dash", "INFO"), ("engineio", "WARNING"), ("socketio", "WARNING")] :
        try:
            lg = _logging.getLogger(name)
            lg.handlers = []
            lg.propagate = True
            lg.setLevel(getattr(_logging, lvl, _logging.INFO))
        except Exception:
            pass
except Exception:
    pass
try:
    from flask import request, g, send_file
except Exception:  # fallback if not available in context
    request = None  # type: ignore
    g = None  # type: ignore
    def send_file(*a, **k):  # type: ignore
        raise RuntimeError("send_file unavailable")

try:
    from hub import profiler as _prof
except Exception:  # never fail app if profiler import fails
    class _Dummy:
        def log_event(self, *a, **k):
            pass
    _prof = _Dummy()  # type: ignore


# Dash app (theme: dark Bootstrap)
external_stylesheets = [dbc.themes.CYBORG]
app = dash.Dash(
    __name__,
    external_stylesheets=external_stylesheets,
    suppress_callback_exceptions=True,
    title="Finance Agent — Dash",
)
server = app.server

# --- Profiler HTTP hooks (opt-in to avoid any startup risk) ---
if os.getenv("AF_PROFILER", "0") == "1" and request is not None:
    @server.before_request
    def _prof_before():  # type: ignore
        try:
            if g is not None:
                g._t0 = time.perf_counter()
        except Exception:
            pass

    @server.after_request
    def _prof_after(resp):  # type: ignore
        try:
            dur_ms = None
            if g is not None and hasattr(g, "_t0"):
                dur_ms = int((time.perf_counter() - getattr(g, "_t0", time.perf_counter())) * 1000)
            _prof.log_event("http", {
                "method": getattr(request, 'method', None),
                "path": getattr(request, 'path', None),
                "status": getattr(resp, 'status_code', None),
                "duration_ms": dur_ms,
            })
            try:
                # Also log to console/file via our logger
                msg = f"HTTP {getattr(request,'method',None)} {getattr(request,'path',None)} -> {getattr(resp,'status_code',None)} ({dur_ms} ms)"
                if 'log' in globals():
                    log.info(msg)  # type: ignore
            except Exception:
                pass
        except Exception:
            pass
        return resp


def sidebar() -> html.Div:
    return html.Div(
        [
            html.H4("Finance Agent", className="mt-3 mb-2"),
            html.Small("Analyse & Prévisions", className="text-muted"),
            dbc.Nav(
                [
                    dbc.NavLink("Dashboard", href="/dashboard", active="exact", id="nav-dashboard"),
                    dbc.NavLink("Signals", href="/signals", active="exact", id="nav-signals"),
                    dbc.NavLink("Portfolio", href="/portfolio", active="exact", id="nav-portfolio"),
                    dbc.NavLink("Watchlist", href="/watchlist", active="exact"),
                    dbc.NavLink("Alerts", href="/alerts", active="exact"),
                    dbc.NavLink("News", href="/news", active="exact"),
                    dbc.NavLink("Deep Dive", href="/deep_dive", active="exact"),
                    dbc.NavLink("Memos", href="/memos", active="exact"),
                    dbc.NavLink("Notes", href="/notes", active="exact"),
                    dbc.NavLink("Changes", href="/changes", active="exact"),
                    dbc.NavLink("Events", href="/events", active="exact"),
                    dbc.NavLink("Earnings", href="/earnings", active="exact"),
                    dbc.NavLink("Reports", href="/reports", active="exact"),
                    dbc.NavLink("Advisor", href="/advisor", active="exact"),
                    dbc.NavLink("LLM Judge", href="/llm_judge", active="exact"),
                    dbc.NavLink("LLM Summary", href="/llm_summary", active="exact"),
                    dbc.NavLink("LLM Models", href="/llm_models", active="exact"),
                    dbc.NavLink("Forecasts", href="/forecasts", active="exact"),
                    dbc.NavLink("Backtests", href="/backtests", active="exact"),
                    dbc.NavLink("Evaluation", href="/evaluation", active="exact"),
                    dbc.NavLink("Regimes", href="/regimes", active="exact", id="nav-regimes"),
                    dbc.NavLink("Risk", href="/risk", active="exact", id="nav-risk"),
                    dbc.NavLink("Recession", href="/recession", active="exact", id="nav-recession"),
                ] + (
                    [dbc.NavLink("DevTools", href="/devtools", active="exact")] if os.getenv("DEVTOOLS_ENABLED", "0") == "1" else []
                ),
                vertical=True,
                pills=True,
                className="mb-3",
            ),
            html.Small("Administration", className="text-muted"),
            dbc.Nav(
                [
                    dbc.NavLink("Agents Status", href="/agents", active="exact", id="nav-agents"),
                    dbc.NavLink("Quality", href="/quality", active="exact"),
                    dbc.NavLink("Profiler", href="/profiler", active="exact"),
                    dbc.NavLink("Observability", href="/observability", active="exact", id="nav-observability"),
                    dbc.NavLink("Settings", href="/settings", active="exact"),
                ] + (
                    [
                        dbc.NavLink("Integration Agent Status", href="/integration_agent_status", active="exact"),
                        dbc.NavLink("Integration Data Quality", href="/integration_data_quality", active="exact"),
                        dbc.NavLink("Integration Macro Data", href="/integration_macro_data", active="exact"),
                        dbc.NavLink("Integration LLM Scoreboard", href="/integration_llm_scoreboard", active="exact"),
                    ] if os.getenv("DEVTOOLS_ENABLED", "0") == "1" else []
                ),
                vertical=True,
                pills=True,
            ),
            html.Div(id='global-status-badge', className="mt-3"),
            html.Small([dbc.NavLink("Détails", href="/agents", className="text-muted", style={"fontSize": "0.8rem"})], className="mb-2"),
        ],
        style={"padding": "0.75rem"},
    )


def _page_registry() -> Dict[str, Callable[[], html.Div]]:
    # Use absolute imports so running as script works with PYTHONPATH=src
    from dash_app.pages import (
        dashboard, signals, portfolio, observability, agents_status, regimes, risk, recession, 
        news, deep_dive, forecasts, backtests, evaluation, quality, llm_judge, profiler, llm_summary, 
        alerts, settings, watchlist, memos, notes, changes, events, earnings, reports, advisor, llm_models, home
    )
    if os.getenv("DEVTOOLS_ENABLED", "0") == "1":
        from dash_app.pages import devtools  # type: ignore
        # Import integration pages only in DEV mode
        from dash_app.pages import integration_agent_status, integration_data_quality, integration_macro_data, integration_llm_scoreboard  # type: ignore

    pages = {
        "/": dashboard.layout,
        "/home": home.layout,
        "/dashboard": dashboard.layout,
        "/signals": signals.layout,
        "/portfolio": portfolio.layout,
        "/regimes": regimes.layout,
        "/risk": risk.layout,
        "/recession": recession.layout,
        "/news": news.layout,
        "/deep_dive": deep_dive.layout,
        "/llm_judge": llm_judge.layout,
        "/llm_summary": llm_summary.layout,
        "/llm_models": llm_models.layout,
        "/forecasts": forecasts.layout,
        "/backtests": backtests.layout,
        "/evaluation": evaluation.layout,
        "/agents": agents_status.layout,
        "/quality": quality.layout,
        "/profiler": profiler.layout,
        "/observability": observability.layout,
        "/alerts": alerts.layout,
        "/watchlist": watchlist.layout,
        "/memos": memos.layout,
        "/notes": notes.layout,
        "/settings": settings.layout,
        "/changes": changes.layout,
        "/events": events.layout,
        "/earnings": earnings.layout,
        "/reports": reports.layout,
        "/advisor": advisor.layout,
    }
    if os.getenv("DEVTOOLS_ENABLED", "0") == "1":
        pages["/devtools"] = devtools.layout  # type: ignore
        pages["/integration_agent_status"] = integration_agent_status.layout  # type: ignore
        pages["/integration_data_quality"] = integration_data_quality.layout  # type: ignore
        pages["/integration_macro_data"] = integration_macro_data.layout  # type: ignore
        pages["/integration_llm_scoreboard"] = integration_llm_scoreboard.layout  # type: ignore
    return pages


from dash_app.pages import dashboard as _dashboard_initial

app.layout = dbc.Container(
    [
        dcc.Location(id="url"),
        dbc.Row(
            [
                dbc.Col(sidebar(), width=2),
                # Pre-render Dashboard as initial content so tests and users see content immediately
                dbc.Col(html.Div(id="page-content", children=_dashboard_initial.layout(), style={"padding": "0.75rem"}), width=10),
            ],
            className="g-0",
        ),
        dcc.Interval(id='status-interval', interval=30*1000, n_intervals=0),  # refresh every 30s
    ],
    fluid=True,
)


@app.callback(dash.Output("page-content", "children"), dash.Input("url", "pathname"))
def render_page(pathname: str):
    try:
        pages = _page_registry()
        fn = pages.get(pathname, pages.get("/"))
        if not fn:
            return html.Div([html.H4("Page introuvable"), html.Small(pathname or "/")])
        try:
            try:
                # Trace route selection to console logs
                if 'log' in globals():
                    log.info("nav.select", extra={"ctx": {"path": pathname, "target": getattr(fn, '__module__', str(fn))}})  # type: ignore
            except Exception:
                pass
            return fn()
        except Exception as e:
            # Log the rendering error for visibility (UI still shows friendly message)
            try:
                import traceback as _tb
                _prof.log_event("error", {"where": "render_page.fn", "path": pathname, "error": repr(e)})
                _tb.print_exc()
            except Exception:
                pass
            return html.Div([
                html.H4("Erreur lors du rendu de la page"),
                html.Small(str(e)),
            ])
    except Exception as e:
        # Log navigation errors as well
        try:
            import traceback as _tb
            _prof.log_event("error", {"where": "render_page", "path": pathname, "error": repr(e)})
            _tb.print_exc()
        except Exception:
            pass
        return html.Div([
            html.H4("Erreur de navigation"),
            html.Small(str(e)),
        ])


@app.callback(dash.Output('global-status-badge', 'children'), dash.Input('status-interval', 'n_intervals'))
def update_global_status(n):
    try:
        # Check HTTP health
        port = int(os.getenv("AF_DASH_PORT", "8050"))
        url = f"http://127.0.0.1:{port}/"
        try:
            resp = requests.get(url, timeout=2)
            health_ok = resp.status_code == 200
        except:
            health_ok = False

        # Check freshness
        freshness_ok = True
        try:
            paths = sorted(Path('data/quality').glob('dt=*/freshness.json'))
            if paths:
                fresh = json.loads(paths[-1].read_text())
                now = pd.Timestamp.now()
                latest_dt = pd.to_datetime(fresh.get('latest_dt', '2000-01-01'))
                hours_diff = (now - latest_dt).total_seconds() / 3600
                freshness_ok = hours_diff < 25  # data du jour
        except:
            freshness_ok = False

        if health_ok and freshness_ok:
            return dbc.Badge("✓ OK", color="success")
        elif health_ok:
            return dbc.Badge("⚠ Données", color="warning")
        else:
            return dbc.Badge("✗ Box", color="danger")
    except:
        return dbc.Badge("? Err", color="secondary")


# Serve QA tester HTML under same origin so the tester can inspect the app DOM via iframe
@server.route("/qa/tester")
def _qa_tester():  # type: ignore
    try:
        p = Path("src/apps/app_tester_qa/finance_app_test-v2.html").resolve()
        return send_file(str(p))
    except Exception as e:
        return (f"Tester not available: {e}", 404)

# ------------------------------- API (React) ------------------------------- #
try:
    from flask import jsonify, request as _flask_req
    from dash_app import api as _api
except Exception:
    _flask_req = None  # type: ignore
    _api = None  # type: ignore

def _cors(resp):
    try:
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Trace-Id'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    except Exception:
        pass
    return resp

@server.route('/api/health', methods=['GET'])
def _api_health():  # type: ignore
    if _api is None:
        r = jsonify({"ok": True, "status": "up"})
        return _cors(r)
    r = jsonify({"ok": True, "status": "up"})
    return _cors(r)

@server.route('/api/forecasts', methods=['GET', 'OPTIONS'])
def _api_forecasts():  # type: ignore
    if _flask_req.method == 'OPTIONS':
        return _cors(jsonify({"ok": True}))
    asset_type = _flask_req.args.get('asset_type', 'all')
    horizon = _flask_req.args.get('horizon', 'all')
    search = _flask_req.args.get('search')
    sort_by = _flask_req.args.get('sort_by', 'score')
    data = _api.forecasts(asset_type, horizon, search, sort_by) if _api else {"ok": False, "error": "api not available"}
    return _cors(jsonify(data))

@server.route('/api/news', methods=['GET', 'OPTIONS'])
def _api_news():  # type: ignore
    if _flask_req.method == 'OPTIONS':
        return _cors(jsonify({"ok": True}))
    sector = _flask_req.args.get('sector', 'all')
    search = _flask_req.args.get('search')
    data = _api.news(sector, search) if _api else {"ok": False, "error": "api not available"}
    return _cors(jsonify(data))

@server.route('/api/watchlist', methods=['GET','POST','OPTIONS'])
def _api_watchlist():  # type: ignore
    if _flask_req.method == 'OPTIONS':
        return _cors(jsonify({"ok": True}))
    if _flask_req.method == 'GET':
        data = _api.watchlist_get() if _api else {"ok": False, "error": "api not available"}
        return _cors(jsonify(data))
    try:
        js = _flask_req.get_json(silent=True) or {}
        ticks = js.get('tickers') or []
        data = _api.watchlist_set([str(t).upper() for t in ticks]) if _api else {"ok": False, "error": "api not available"}
        return _cors(jsonify(data))
    except Exception as e:
        return _cors(jsonify({"ok": False, "error": str(e)}))

@server.route('/api/settings', methods=['GET','POST','OPTIONS'])
def _api_settings():  # type: ignore
    if _flask_req.method == 'OPTIONS':
        return _cors(jsonify({"ok": True}))
    if _flask_req.method == 'GET':
        data = _api.settings_get() if _api else {"ok": False, "error": "api not available"}
        return _cors(jsonify(data))
    try:
        js = _flask_req.get_json(silent=True) or {}
        data = _api.settings_set(float(js.get('move_abs_pct', 1.0)), str(js.get('tilt', 'balanced'))) if _api else {"ok": False, "error": "api not available"}
        return _cors(jsonify(data))
    except Exception as e:
        return _cors(jsonify({"ok": False, "error": str(e)}))

@server.route('/api/llm/judge/run', methods=['POST','OPTIONS'])
def _api_llm_judge_run():  # type: ignore
    if _flask_req.method == 'OPTIONS':
        return _cors(jsonify({"ok": True}))
    try:
        js = _flask_req.get_json(silent=True) or {}
        model = str(js.get('model') or 'deepseek-ai/DeepSeek-V3-0324-Turbo')
        max_er = float(js.get('max_er', 0.08))
        min_conf = float(js.get('min_conf', 0.6))
        tickers = js.get('tickers')
        if isinstance(tickers, list):
            tickers = ','.join([str(t).upper() for t in tickers])
        data = _api.llm_judge_run(model, max_er, min_conf, tickers) if _api else {"ok": False, "error": "api not available"}
        return _cors(jsonify(data))
    except Exception as e:
        return _cors(jsonify({"ok": False, "error": str(e)}))

if __name__ == "__main__":
    port = int(os.getenv("AF_DASH_PORT", "8050"))
    debug = os.getenv("AF_DASH_DEBUG", "false").lower() == "true"
    # Optional devtools controls to reduce console spam when hot reload is not desired
    hot_reload = os.getenv("DASH_HOT_RELOAD", "true").lower() == "true"
    devtools_ui = os.getenv("DASH_DEVTOOLS_UI", "true").lower() == "true"
    try:
        if 'log' in globals():
            log.info(
                "dash.start",
                extra={"ctx": {"port": port, "debug": debug, "hot_reload": hot_reload, "devtools_ui": devtools_ui}},  # type: ignore
            )
    except Exception:
        pass
    # Dash >=3 replaced run_server with run
    app.run(host="0.0.0.0", port=port, debug=debug,
            dev_tools_hot_reload=hot_reload, dev_tools_ui=devtools_ui)
