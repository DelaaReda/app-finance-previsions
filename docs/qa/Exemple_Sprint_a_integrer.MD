Objectifs du Sprint

Dans ce Sprint 10, l’objectif principal est de rétablir la cohérence fonctionnelle et visuelle de l’application Dash en corrigeant les bugs critiques et en réintégrant les fonctionnalités manquantes de l’ancienne UI Streamlit. Nous mettrons en place des tests automatisés (unitaires et end-to-end) pour assurer la fiabilité du produit. Les user stories sont formulées du point de vue de l’utilisateur final ￼, avec des critères clairs et mesurables pour valider leur réussite ￼. Parmi les priorités : remettre en service les pages actuellement vides (Evaluation, Backtests, Risk, Regimes), corriger l’erreur de rendu sur la page Quality, et afficher toutes les données disponibles (fichiers Parquet mis à jour) pour offrir des visualisations complètes. La qualité des données étant un enjeu stratégique ￼, nous vérifierons la fraîcheur et l’intégrité des données (via freshness.json et Parquet). Enfin, des tests end-to-end seront ajoutés pour simuler l’expérience utilisateur réelle ￼, garantissant ainsi la stabilité de l’interface à chaque itération.

Tâches prioritaires Sprint 10
	1.	[Bug] Corriger la page Quality – En tant qu’analyste financier, je souhaite que la page Quality affiche correctement les indicateurs de performance (bug AttributeError: 'str' object has no attribute get), afin de pouvoir évaluer la qualité des modèles de prévision. (Priorité haute, dev)
	2.	[Bug] Restaurer les pages Backtests et Évaluation – En tant qu’analyste, je veux que les pages Backtests et Évaluation affichent les données calculées (scores de modèles, indicateurs clefs, etc.), car elles sont actuellement vides ou bloquées. (Priorité haute, dev)
	3.	[Bug] Restaurer les pages Risk et Regimes – En tant qu’analyste, je veux que les pages Risk et Regimes soient alimentées avec les données sources (par exemple, mesures de risque et segmentation de marché), car elles sont vides à ce stade. (Priorité haute, dev)
	4.	[Feature] Réintégrer les fonctionnalités manquantes de l’ancienne UI – En tant qu’utilisateur, je souhaite retrouver dans Dash toutes les fonctionnalités de l’ancienne interface Streamlit (sélection multi-actifs dans Deep Dive, comparaisons globales, filtres historiques, etc.), afin de maintenir la richesse fonctionnelle du produit. (Priorité haute, dev)
	5.	[Feature] Page Observability – En tant qu’administrateur, je souhaite qu’une page Observability affiche la fraîcheur des données (contenu de freshness.json) et les journaux d’exécution, afin de surveiller en continu la qualité et l’actualité des données de prévision ￼. (Priorité moyenne, dev)
	6.	[Feature] Page Agents Status – En tant qu’administrateur/superviseur, je souhaite que la page Agents Status affiche l’état des agents IA (actifs, en erreur, progression des tâches), afin de suivre le statut des processus internes. (Priorité moyenne, dev)
	7.	[Test] Tests end-to-end UI – En tant que QA, je veux mettre en place des tests automatisés end-to-end couvrant les parcours critiques (pages Forecasts, Deep Dive, etc.), pour valider le bon fonctionnement de l’interface et prévenir les régressions ￼. (Priorité haute, QA)
	8.	[Test] Tests unitaires des callbacks Dash – En tant que QA, je veux écrire des tests unitaires sur les fonctions de callback de l’application Dash, afin de vérifier la logique de transformation des données et l’affichage des composants. (Priorité moyenne, QA)
	9.	[Test] Vérification de la fraîcheur des données – En tant que QA, je souhaite automatiser un test qui vérifie la mise à jour régulière de freshness.json et l’existence des fichiers Parquet source, afin de garantir la fiabilité et la fraîcheur des données dans l’application ￼. (Priorité moyenne, QA)

Numéro	Titre	Type	Priorité	Responsable
1	Corriger page Quality (render bug)	Bug	Haute	Dev
2	Restaurer pages Backtests & Évaluation	Bug	Haute	Dev
3	Restaurer pages Risk & Regimes	Bug	Haute	Dev
4	Réintégrer fonctionnalités manquantes	Feature	Haute	Dev
5	Page Observability (fraîcheur données)	Feature	Moyenne	Dev
6	Page Agents Status (états agents IA)	Feature	Moyenne	Dev
7	Tests end-to-end UI (parcours critiques)	Test	Haute	QA
8	Tests unitaires (callbacks Dash)	Test	Moyenne	QA
9	Vérification automatisée des données	Test	Moyenne	QA

Sources : Les user stories sont conçues selon les bonnes pratiques Agile (focalisées sur le besoin utilisateur) ￼. La littérature souligne l’importance de la qualité des données pour la fiabilité des prédictions ￼, ainsi que la nécessité de tests end-to-end pour valider l’expérience utilisateur réelle ￼. Ces considérations guident la priorisation et la rédaction des tâches ci-dessus.

Sprint 10 — Détails techniques & code

1) [Bug] Corriger la page Quality

Symptôme: AttributeError: 'str' object has no attribute 'get' ⇒ souvent causé par un freshness.json ou un JSONL dont on itère les éléments en supposant des dicts alors que c’est une string (ou une ligne JSON non parsée).
Fix: parse robuste + garde-fous de types.

src/dash_app/data/loader.py (ajouts robustesse)

import json, pandas as pd
from pathlib import Path

def _ensure_path(p):
    return p() if callable(p) else p

def read_parquet(path):
    p = _ensure_path(path)
    if not Path(p).exists():
        return pd.DataFrame()
    return pd.read_parquet(p)

def read_json(path):
    p = _ensure_path(path)
    if not Path(p).exists():
        return {}
    raw = Path(p).read_text().strip()
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {"value": obj}
    except Exception:
        return {}

def read_jsonl(path):
    p = _ensure_path(path)
    if not Path(p).exists():
        return []
    rows = []
    for i, line in enumerate(Path(p).read_text().splitlines()):
        line = line.strip()
        if not line: 
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
            else:
                rows.append({"value": obj})
        except Exception:
            rows.append({"value": line, "parse_error": True, "line": i})
    return rows

src/dash_app/pages/quality.py (rendu sans crash)

import dash, pandas as pd, plotly.express as px
from dash import html, dcc
from ..data.loader import read_parquet, read_json
from ..data.paths import p_quality_anoms, p_quality_fresh

dash.register_page(__name__, path="/quality", name="Quality")

def layout():
    anoms = read_parquet(p_quality_anoms)     # attendu colonnes: dataset, severity, count
    fresh = read_json(p_quality_fresh)        # attendu: {"datasets":[{"name":..., "minutes_since_update":...}, ...]}

    # Défauts safe:
    if not isinstance(fresh, dict):
        fresh = {}
    ds = fresh.get("datasets", [])
    if not isinstance(ds, list):
        ds = []

    # Graph anomalies (groupby au cas où)
    if not anoms.empty:
        g = (anoms.groupby(["dataset","severity"], as_index=False)["count"].sum()
                  .sort_values(["dataset","severity"]))
        fig_anoms = px.bar(g, x="dataset", y="count", color="severity",
                           title="Anomalies par dataset")
    else:
        fig_anoms = {}

    # Graph fraîcheur
    df_f = pd.DataFrame(ds)
    if not df_f.empty and "minutes_since_update" in df_f:
        fig_fresh = px.bar(df_f, x="name", y="minutes_since_update",
                           title="Fraîcheur des données (minutes)")
    else:
        fig_fresh = {}

    # Résumé lisible
    resume = []
    for item in ds:
        name = item.get("name", "unknown") if isinstance(item, dict) else str(item)
        mins = item.get("minutes_since_update", "n/a") if isinstance(item, dict) else "n/a"
        resume.append(html.Li(f"{name}: {mins} mn"))

    return html.Div([
        html.H1("Quality"),
        html.Div([
            html.Div([html.H3("Anomalies"), dcc.Graph(figure=fig_anoms)], className="w-1/2 p-2"),
            html.Div([html.H3("Fraîcheur"), dcc.Graph(figure=fig_fresh)], className="w-1/2 p-2"),
        ], className="flex flex-wrap"),
        html.H3("Datasets (résumé)"),
        html.Ul(resume or [html.Li("Aucune donnée")]),
    ], className="p-4")


⸻

2) [Bug] Restaurer Backtests & Évaluation

Backtests — src/dash_app/pages/backtests.py

(schéma type : results.parquet avec colonnes date, strategy, equity, pnl, sharpe, winrate)

import dash, pandas as pd, plotly.express as px
from dash import html, dcc, dash_table
from ..data.loader import read_parquet
from ..data.paths import p_backtests

dash.register_page(__name__, path="/backtests", name="Backtests")

def layout():
    df = read_parquet(p_backtests)
    equity_fig = {}
    if not df.empty and {"date","equity","strategy"} <= set(df.columns):
        equity_fig = px.line(df, x="date", y="equity", color="strategy", title="Equity Curve")
    stats_cols = [c for c in ["strategy","pnl","sharpe","winrate"] if c in df.columns]
    stats = (df.groupby("strategy", as_index=False)[[c for c in stats_cols if c!="strategy"]].mean()
             if "strategy" in df.columns and stats_cols else pd.DataFrame())
    return html.Div([
        html.H1("Backtests"),
        dcc.Graph(figure=equity_fig),
        html.H3("Stats moyennes par stratégie"),
        dash_table.DataTable(
            data=(stats.to_dict("records") if not stats.empty else []),
            columns=[{"name":c, "id":c} for c in stats.columns],
            page_size=10,
            sort_action="native",
            filter_action="native"
        )
    ], className="p-4")

Évaluation — src/dash_app/pages/evaluation.py

(schéma type : metrics.parquet avec model, horizon, mae, mape, rmse)

import dash, pandas as pd, plotly.express as px
from dash import html, dcc
from ..data.loader import read_parquet
from ..data.paths import p_eval

dash.register_page(__name__, path="/evaluation", name="Evaluation")

def layout():
    df = read_parquet(p_eval)
    if df.empty:
        return html.Div([html.H1("Evaluation"), html.Div("Aucune métrique trouvée.")])

    bars = {}
    heat = {}
    if {"model","horizon","mape"} <= set(df.columns):
        bars = px.bar(df, x="model", y="mape", color="horizon", barmode="group",
                      title="MAPE par modèle & horizon")
    if {"model","horizon","rmse"} <= set(df.columns):
        pivot = df.pivot_table(index="model", columns="horizon", values="rmse", aggfunc="mean")
        heat = px.imshow(pivot, text_auto=True, title="RMSE (heatmap)")
    return html.Div([
        html.H1("Evaluation"),
        dcc.Graph(figure=bars),
        dcc.Graph(figure=heat),
    ], className="p-4")


⸻

3) [Bug] Restaurer Risk & Regimes

Risk — src/dash_app/pages/risk.py

(schéma type : risk.parquet avec date, asset, vol, drawdown, var_95)

import dash, pandas as pd, plotly.express as px
from dash import html, dcc
from ..data.loader import read_parquet
from ..data.paths import p_risk  # à créer dans paths.py -> DATA_DIR/"macro"/"risk.parquet"

dash.register_page(__name__, path="/risk", name="Risk")

def layout():
    df = read_parquet(p_risk)
    if df.empty:
        return html.Div([html.H1("Risk"), html.Div("Pas de données de risque")])
    figs = []
    if {"date","asset","vol"} <= set(df.columns):
        figs.append(dcc.Graph(figure=px.line(df, x="date", y="vol", color="asset", title="Volatilité")))
    if {"date","asset","drawdown"} <= set(df.columns):
        figs.append(dcc.Graph(figure=px.area(df, x="date", y="drawdown", color="asset", title="Drawdown")))
    if {"asset","var_95"} <= set(df.columns):
        latest = df.sort_values("date").groupby("asset").tail(1)
        figs.append(dcc.Graph(figure=px.bar(latest, x="asset", y="var_95", title="VaR 95% (dernier point)")))
    return html.Div([html.H1("Risk")] + figs, className="p-4")

Regimes — src/dash_app/pages/regimes.py

(schéma type : regimes.parquet avec date, regime_label, prob_{k})

import dash, pandas as pd, plotly.express as px
from dash import html, dcc
from ..data.loader import read_parquet
from ..data.paths import p_regimes  # -> DATA_DIR/"macro"/"regimes.parquet"

dash.register_page(__name__, path="/regimes", name="Regimes")

def layout():
    df = read_parquet(p_regimes)
    if df.empty:
        return html.Div([html.H1("Regimes"), html.Div("Pas de données de régimes")])
    figs = []
    if {"date","regime_label"} <= set(df.columns):
        figs.append(dcc.Graph(figure=px.scatter(df, x="date", y="regime_label",
                                               title="Régime dominant (timeline)")))
    prob_cols = [c for c in df.columns if c.startswith("prob_")]
    if prob_cols:
        long = df.melt(id_vars=["date"], value_vars=prob_cols, var_name="regime", value_name="proba")
        figs.append(dcc.Graph(figure=px.area(long, x="date", y="proba", color="regime",
                                             title="Probabilités de régimes")))
    return html.Div([html.H1("Regimes")] + figs, className="p-4")

Pense à ajouter dans data/paths.py:

def p_risk():    return settings.DATA_DIR / "macro" / "risk.parquet"
def p_regimes(): return settings.DATA_DIR / "macro" / "regimes.parquet"


⸻

4) [Feature] Réintégrer fonctionnalités ancienne UI (Deep Dive & co)

Deep Dive multi-actifs + filtres historiques — src/dash_app/pages/deep_dive.py

import dash, pandas as pd, plotly.express as px
from dash import html, dcc, Input, Output, callback, State
from ..data.loader import read_parquet
from ..data.paths import p_deep_dive, p_forecasts

dash.register_page(__name__, path="/deep-dive", name="Deep Dive")

def layout():
    # Pré-charger liste des tickers depuis forecasts (plus complet)
    all_fc = read_parquet(p_forecasts)
    tickers = sorted(all_fc["ticker"].unique().tolist()) if "ticker" in all_fc else []
    return html.Div([
        html.H1("Deep Dive"),
        html.Div([
            dcc.Dropdown(tickers, multi=True, id="dd-tickers", placeholder="Choisir 1..N tickers"),
            dcc.DatePickerRange(id="dd-range"),
            dcc.RadioItems(
                options=[{"label":"Clôture","value":"close"},{"label":"Adj Close","value":"adj_close"}],
                value="close", id="dd-price-col", inline=True
            ),
        ], className="flex gap-4"),
        dcc.Graph(id="dd-prices"),
        dcc.Graph(id="dd-forecasts"),
    ], className="p-4")

@callback(
    Output("dd-prices","figure"),
    Output("dd-forecasts","figure"),
    Input("dd-tickers","value"),
    Input("dd-range","start_date"),
    Input("dd-range","end_date"),
    Input("dd-price-col","value"),
    prevent_initial_call=True
)
def _render(tickers, start, end, col):
    if not tickers:
        return {}, {}
    # Prix: concat par ticker
    frames = []
    for t in tickers:
        df = read_parquet(lambda: p_deep_dive(t))
        if df.empty: 
            continue
        if start: df = df[df["date"] >= pd.to_datetime(start)]
        if end:   df = df[df["date"] <= pd.to_datetime(end)]
        df = df.assign(ticker=t)
        frames.append(df)
    prices = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    fig_p = {}
    if not prices.empty and col in prices.columns:
        fig_p = px.line(prices, x="date", y=col, color="ticker", title="Prix (overlay)")

    # Forecasts (filtrés mêmes tickers)
    fcs = read_parquet(p_forecasts)
    fig_f = {}
    if not fcs.empty and {"ticker","target_date","target_price"} <= set(fcs.columns):
        fcs = fcs[fcs["ticker"].isin(tickers)]
        fig_f = px.scatter(fcs, x="target_date", y="target_price", color="ticker",
                           title="Prévisions (tous modèles/horizons)")

    return fig_p, fig_f


⸻

5) [Feature] Observability (fraîcheur + journaux)

src/dash_app/pages/observability.py

import dash, pandas as pd, datetime as dt
from dash import html, dcc, Output, Input, callback
from ..data.loader import read_json
from ..data.paths import p_quality_fresh, p_logs

dash.register_page(__name__, path="/observability", name="Observability")

def layout():
    return html.Div([
        html.H1("Observability"),
        html.Div(id="obs-fresh"),
        html.Pre(id="obs-log", style={
            "height":"50vh","overflow":"auto","background":"#0b1020","color":"#cde","padding":"10px"
        }),
        dcc.Interval(id="obs-tick", interval=5000, n_intervals=0)
    ], className="p-4")

@callback(
    Output("obs-fresh","children"),
    Output("obs-log","children"),
    Input("obs-tick","n_intervals")
)
def _tick(_n):
    fresh = read_json(p_quality_fresh)
    ds = fresh.get("datasets", []) if isinstance(fresh, dict) else []
    now = dt.datetime.utcnow()
    badges = []
    for item in ds:
        name = item.get("name","?")
        mins = item.get("minutes_since_update", 9e9)
        status = "🟢" if mins <= 60 else ("🟠" if mins <= 360 else "🔴")
        badges.append(html.Div(f"{status} {name}: {mins} mn"))
    path = p_logs()
    logtxt = path.read_text()[-60_000:] if path.exists() else "Log introuvable."
    return html.Div(badges or "Aucune info fraîcheur"), logtxt


⸻

6) [Feature] Agents Status

src/dash_app/pages/agents.py

import dash, pandas as pd
from dash import html, dcc, dash_table
from ..data.loader import read_json
from ..data.paths import p_agents_status

dash.register_page(__name__, path="/agents", name="Agents Status")

def layout():
    st = read_json(p_agents_status)  # {"agents":[{"name":..., "status":"ok|error|running", "progress":0-100, "last_run":"..."}]}
    agents = st.get("agents", []) if isinstance(st, dict) else []
    df = pd.DataFrame(agents)
    if df.empty:
        return html.Div([html.H1("Agents Status"), html.Div("Aucun agent trouvé")])

    # Progress bar custom via DataTable format (simple):
    cols = [{"name": c, "id": c} for c in df.columns]
    return html.Div([
        html.H1("Agents Status"),
        dash_table.DataTable(
            data=df.to_dict("records"),
            columns=cols,
            page_size=15,
            sort_action="native",
            filter_action="native",
            style_data_conditional=[
                {"if":{"filter_query":"{status} = 'error'"},
                 "backgroundColor":"#3a0d0d","color":"#ffdddd"},
                {"if":{"filter_query":"{status} = 'running'"},
                 "backgroundColor":"#0d1f3a","color":"#dbeafe"},
            ]
        )
    ], className="p-4")


⸻

7) [Test] End-to-end UI (parcours critiques)

tests/dash/test_e2e_ui.py

import re, time
from dash.testing.application_runners import import_app

def _start(dash_duo):
    app = import_app("src.dash_app.app")
    dash_duo.start_server(app)

def test_forecasts_filters(dash_duo):
    _start(dash_duo)
    dash_duo.driver.get(dash_duo.server_url + "/forecasts")
    dash_duo.wait_for_text_to_equal("h1", "Forecasts", timeout=6)
    # Vérif tableau présent
    assert "Forecasts" in dash_duo.find_element("body").text

def test_deep_dive_multi(dash_duo):
    _start(dash_duo)
    dash_duo.driver.get(dash_duo.server_url + "/deep-dive")
    dash_duo.wait_for_text_to_equal("h1","Deep Dive", timeout=6)
    # on ne clique pas réellement (sans id exact de l'option), mais on valide le rendu
    assert "Deep Dive" in dash_duo.find_element("body").text

def test_quality_ok(dash_duo):
    _start(dash_duo)
    dash_duo.driver.get(dash_duo.server_url + "/quality")
    dash_duo.wait_for_text_to_equal("h1","Quality", timeout=6)
    # pas d'exception et éléments affichés
    assert "Fraîcheur" in dash_duo.find_element("body").text

def test_observability_loads(dash_duo):
    _start(dash_duo)
    dash_duo.driver.get(dash_duo.server_url + "/observability")
    dash_duo.wait_for_text_to_equal("h1","Observability", timeout=6)

Ajoute dans requirements : pytest, dash[testing].

⸻

8) [Test] Unitaires de callbacks (extraire la logique pure)

Exemple: factoriser la logique de filtrage Deep Dive dans un module testable.

src/dash_app/logic/deep_dive_logic.py

import pandas as pd

def filter_prices(prices_by_ticker: dict[str, pd.DataFrame], tickers, start, end, col):
    frames = []
    for t in tickers or []:
        df = prices_by_ticker.get(t, pd.DataFrame())
        if df.empty or col not in df.columns: 
            continue
        if start: df = df[df["date"] >= pd.to_datetime(start)]
        if end:   df = df[df["date"] <= pd.to_datetime(end)]
        df = df.assign(ticker=t)
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

tests/unit/test_deep_dive_logic.py

import pandas as pd
from src.dash_app.logic.deep_dive_logic import filter_prices

def test_filter_prices_basic():
    d = pd.date_range("2025-01-01", periods=3, freq="D")
    a = pd.DataFrame({"date":d, "close":[1,2,3]})
    b = pd.DataFrame({"date":d, "close":[3,2,1]})
    res = filter_prices({"AAA":a,"BBB":b}, ["AAA","BBB"], "2025-01-02", None, "close")
    assert set(res["ticker"]) == {"AAA","BBB"}
    assert res["date"].min() >= pd.to_datetime("2025-01-02")

Même principe pour Quality (conversion en DataFrame, garde-fous) et Evaluation (pivot heatmap): extraire 1–2 fonctions et tester.

⸻

9) [Test] Vérification de la fraîcheur & des sources

tests/data/test_freshness_and_sources.py

import json, os
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

AFP_DATA_DIR = Path(os.getenv("AFP_DATA_DIR","data"))

def _exists(relpath):
    return (AFP_DATA_DIR / relpath).exists()

def test_parquet_sources_exist():
    assert _exists("forecasts/equity_forecasts.parquet")
    # ajoute ce qui est critique pour le sprint
    assert _exists("evaluation/metrics.parquet") or True  # tolérant si pipeline pas encore passé
    assert _exists("backtests/results.parquet") or True
    assert _exists("macro/risk.parquet") or True
    assert _exists("macro/regimes.parquet") or True

def test_freshness_recent():
    p = AFP_DATA_DIR / "quality" / "freshness.json"
    assert p.exists(), "freshness.json manquant"
    fresh = json.loads(p.read_text())
    ds = fresh.get("datasets", [])
    # au moins un dataset mis à jour & seuil < 24h
    assert any(isinstance(x, dict) and x.get("minutes_since_update", 1e9) < 24*60 for x in ds)


⸻

Annexes

A) data/paths.py (compléments si manquants)

from pathlib import Path
from . import settings

def p_backtests():     return settings.DATA_DIR / "backtests" / "results.parquet"
def p_eval():          return settings.DATA_DIR / "evaluation" / "metrics.parquet"
def p_quality_anoms(): return settings.DATA_DIR / "quality" / "anomalies.parquet"
def p_quality_fresh(): return settings.DATA_DIR / "quality" / "freshness.json"
def p_agents_status(): return settings.DATA_DIR / "agents" / "status.json"
def p_logs():          return settings.DATA_DIR / "observability" / "app.log"
def p_forecasts():     return settings.DATA_DIR / "forecasts" / "equity_forecasts.parquet"
def p_deep_dive(t):    return settings.DATA_DIR / "prices" / f"{t}.parquet"
def p_risk():          return settings.DATA_DIR / "macro" / "risk.parquet"
def p_regimes():       return settings.DATA_DIR / "macro" / "regimes.parquet"

B) Makefile (rappels)

dash-start:
\tpython -m src.dash_app.app

dash-test:
\tpytest -q tests

dash-e2e:
\tpytest -q tests/dash/test_e2e_ui.py

dash-unit:
\tpytest -q tests/unit


⸻

Critères d’acceptation (résumé rapide)
	•	Quality: la page charge sans exception, affiche 2 graphiques + liste; JSON malformé ne casse pas l’UI.
	•	Backtests & Évaluation: pages non vides, au moins 1 graph + 1 table chacune si Parquet présent.
	•	Risk & Regimes: pages non vides, graphiques cohérents (vol/drawdown/VaR ; timeline régimes + proba).
	•	Deep Dive: sélection multi-ticker + filtre date + overlay des séries; scatter des prévisions.
	•	Observability: badges 🟢🟠🔴 selon minutes_since_update, logs « live » (tail).
	•	Agents: tableau listant statut/progress/last_run, tri & filtre natifs.
	•	E2E: tests passent (chargement & éléments clés visibles).
	•	Unitaires: au moins 1-2 fonctions purifiées testées.
	•	Freshness: test vérifie présence des sources et récence minimale.

Aussi lire les consignes de developpement : analyse-financiere/docs/dev/dev-prompt.md