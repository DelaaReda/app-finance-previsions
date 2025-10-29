# 📊 Page Spec — Investor Overview

**Page Route**: `/integration_overview` → `/overview` (production)
**Priority**: 🥇 Haute (RoI = 25.0)
**Status**: 🚧 DEV-only → Production Ready
**Assigné**: Dev Team

---

## 🎯 Objectif UX

Fournir à Reda **vue 360° en 1 page** (30 secondes) comprenant:
1. **Régime macro** actuel (expansion/désinflation/contraction)
2. **Risque** niveau (low/medium/high) avec indicateurs clés
3. **Top-N signaux** finaux (equity + commodities, horizon 1m)
4. **Synthèse LLM** (3-5 drivers clés FR + contributors)
5. **Action manuelle** (bouton "Relancer LLM maintenant" + logs)

**Persona**: Reda (investisseur privé, non-expert, 30 min/jour)

**Use Case**: Morning routine → ouvrir Dashboard → clic "Overview" → décider si investiguer Deep Dive ou attendre

---

## 📥 Sources de Données

### 1. Régime Macro
**Partition**: `data/macro/forecast/dt=YYYYMMDD/macro_forecast.parquet`

**Colonnes requises**:
- `regime` (str): `"expansion_modérée"` | `"désinflation"` | `"contraction"` | `"incertain"`
- `inflation_yoy` (float): CPI YoY % (ex: 2.4)
- `yield_curve_slope` (float): DGS10 - DGS2 en bp (ex: 0.35)
- `unemployment` (float): Taux chômage % (ex: 4.1)
- `recession_prob` (float): Probabilité récession 0-1 (ex: 0.15)

**Loader**: `read_parquet_latest("data/macro/forecast", "macro_forecast.parquet")`

**Empty State**: "Aucune donnée macro disponible. Agent macro-forecast n'a pas été exécuté."

---

### 2. Risque Niveau
**Partition**: `data/macro/forecast/dt=YYYYMMDD/macro_forecast.parquet` (même que régime)

**Colonnes requises**:
- `risk_level` (str): `"low"` | `"medium"` | `"high"`
- `unemployment` (float)
- `vix` (float, optionnel): VIX index (ex: 18.5)
- `credit_spread` (float, optionnel): High yield spreads bp (ex: 350)

**Fallback si colonnes optionnelles absentes**:
- `vix` → "N/A"
- `credit_spread` → "N/A"

**Calcul heuristique si `risk_level` absent**:
```python
def compute_risk_level(unemployment, vix=None, recession_prob=None):
    if unemployment > 5.5 or (vix and vix > 25) or (recession_prob and recession_prob > 0.5):
        return "high"
    elif unemployment > 4.5 or (vix and vix > 20):
        return "medium"
    else:
        return "low"
```

---

### 3. Top-N Signaux Finaux
**Partitions**:
- `data/forecast/dt=YYYYMMDD/final.parquet` (equity)
- `data/forecast/dt=YYYYMMDD/commodities.parquet` (commodities)

**Colonnes final.parquet**:
- `ticker` (str): NVDA, AAPL, etc.
- `horizon` (str): `"1m"` (filter sur 1 mois)
- `final_score` (float): 0.0-1.0
- `direction` (str, optionnel): `"haussier"` | `"baissier"` | `"neutre"`
- `confidence` (float, optionnel): 0.0-1.0

**Colonnes commodities.parquet**:
- `commodity_name` (str): Gold, WTI Crude Oil, etc.
- `ticker` (str): GC=F, CL=F, etc.
- `horizon` (str): `"1m"`
- `expected_return` (float): % return expected
- `direction` (str): `"haussier"` | `"baissier"`
- `confidence` (float): 0.0-1.0

**Top-N**: 10 equity + 5 commodities

**Tri**: `final_score DESC` (equity), `abs(expected_return) DESC` (commodities)

---

### 4. Synthèse LLM
**Partition**: `data/llm_summary/dt=YYYYMMDDHH/summary.json`

**Schema JSON (LLMEnsembleSummary)**:
```json
{
  "regime": "expansion_modérée",
  "risk_level": "medium",
  "outlook_days_7": "positive",
  "outlook_days_30": "neutral",
  "key_drivers": [
    "Désinflation continue (CPI -0.2% MoM, slope +15bp)",
    "Tech surperformance (NVDA +8% 7j, IA demande)",
    "Risque taux (DGS10 4.5%, pénalise growth)"
  ],
  "contributors": [
    {
      "source": "technique",
      "model": "momentum",
      "horizon": "1m",
      "symbol": "NVDA",
      "score": 0.82,
      "prediction": "haussier",
      "rationale": "Momentum 21j fort (+12%), volume confirmant"
    }
  ],
  "limits": ["Données macro H-48 (FRED delay)"]
}
```

**Loader**: `load_json_latest("data/llm_summary/dt=*/summary.json")`

**Empty State**: "Aucune synthèse LLM disponible. Cliquez 'Relancer maintenant'."

---

## 🎨 Layout & IDs

### Structure Globale
```python
html.Div([
    html.H2("Vue d'Ensemble Investisseur", className="mb-4"),

    # Row 1: Régime + Risque
    dbc.Row([
        dbc.Col([
            # Carte Régime
        ], md=6),
        dbc.Col([
            # Carte Risque
        ], md=6)
    ], className="mb-4"),

    # Row 2: Top-N Signaux
    dbc.Row([
        dbc.Col([
            # Carte Top-10 Equity
        ], md=7),
        dbc.Col([
            # Carte Top-5 Commodities
        ], md=5)
    ], className="mb-4"),

    # Row 3: Synthèse LLM
    dbc.Row([
        dbc.Col([
            # Carte Synthèse LLM
        ], md=12)
    ], className="mb-4"),

    # Interval pour refresh logs
    dcc.Interval(id="overview-llm-log-interval", interval=4000, disabled=True)
])
```

---

### Carte 1: Régime Macro
**ID**: `#overview-regime-card`

**Composants**:
```python
dbc.Card([
    dbc.CardHeader("Régime Macro Actuel"),
    dbc.CardBody([
        # Badge régime (coloré)
        dbc.Badge(
            regime,  # "Expansion Modérée"
            id="overview-regime-badge",
            color={
                "expansion_modérée": "success",
                "désinflation": "info",
                "contraction": "danger",
                "incertain": "warning"
            }[regime],
            className="fs-4 mb-3"
        ),

        # Trend icon (optionnel si historique disponible)
        html.Span("↗️", id="overview-regime-trend", className="ms-2"),  # ↗️↘️➡️

        # Explication 1 phrase
        html.P(
            f"Inflation {inflation_yoy:.1f}% YoY, courbe rendement {slope:+.2f}bp, chômage {unemployment:.1f}%",
            id="overview-regime-explanation",
            className="text-muted mb-0"
        )
    ])
], id="overview-regime-card", className="h-100")
```

**Empty State**:
```python
dbc.Alert("Aucune donnée macro disponible.", color="info")
```

---

### Carte 2: Risque Niveau
**ID**: `#overview-risk-card`

**Composants**:
```python
dbc.Card([
    dbc.CardHeader("Niveau de Risque"),
    dbc.CardBody([
        # Badge risque (coloré)
        dbc.Badge(
            risk_level.capitalize(),  # "Medium"
            id="overview-risk-badge",
            color={
                "low": "success",
                "medium": "warning",
                "high": "danger"
            }[risk_level],
            className="fs-4 mb-3"
        ),

        # Table indicateurs
        dbc.Table([
            html.Tr([html.Th("Chômage"), html.Td(f"{unemployment:.1f}%")]),
            html.Tr([html.Th("VIX"), html.Td(f"{vix:.1f}" if vix else "N/A")]),
            html.Tr([html.Th("Spreads HY"), html.Td(f"{credit_spread:.0f}bp" if credit_spread else "N/A")]),
            html.Tr([html.Th("Prob. Récession"), html.Td(f"{recession_prob:.0%}")])
        ], bordered=True, hover=True, size="sm", id="overview-risk-metrics-table")
    ])
], id="overview-risk-card", className="h-100")
```

---

### Carte 3: Top-10 Equity
**ID**: `#overview-topN-equity-card`

**Composants**:
```python
dbc.Card([
    dbc.CardHeader([
        "Top 10 Actions (1 mois)",
        dbc.Button("Export CSV", id="overview-equity-export-btn", size="sm", color="link", className="float-end")
    ]),
    dbc.CardBody([
        dbc.Table.from_dataframe(
            df_equity[["ticker", "final_score", "direction", "confidence"]].head(10),
            id="overview-topN-equity-table",
            striped=True,
            bordered=True,
            hover=True
        )
    ])
], id="overview-topN-equity-card")
```

**Formatage Colonnes**:
- `final_score`: `0.82` → "0.82" (2 decimals)
- `direction`: `"haussier"` → Badge vert ↗️, `"baissier"` → Badge rouge ↘️
- `confidence`: `0.75` → "75%" (percentage)

---

### Carte 4: Top-5 Commodities
**ID**: `#overview-topN-commodities-card`

**Composants**:
```python
dbc.Card([
    dbc.CardHeader("Top 5 Matières Premières"),
    dbc.CardBody([
        dbc.Table.from_dataframe(
            df_commodities[["commodity_name", "expected_return", "direction", "confidence"]].head(5),
            id="overview-topN-commodities-table",
            striped=True,
            bordered=True,
            hover=True
        )
    ])
], id="overview-topN-commodities-card")
```

**Formatage Colonnes**:
- `expected_return`: `0.08` → "+8.0%" (percentage with sign)
- `direction`: Badge vert/rouge
- `confidence`: "75%"

---

### Carte 5: Synthèse LLM
**ID**: `#overview-llm-summary-card`

**Composants**:
```python
dbc.Card([
    dbc.CardHeader([
        "Synthèse LLM (Drivers Clés)",
        dbc.Button(
            "Relancer maintenant",
            id="overview-llm-run-btn",
            size="sm",
            color="primary",
            className="float-end"
        )
    ]),
    dbc.CardBody([
        # Key drivers (bullets)
        html.Ul([
            html.Li(driver) for driver in key_drivers
        ], id="overview-llm-drivers-list", className="mb-3"),

        # Outlook badges
        dbc.Row([
            dbc.Col([
                html.Small("Outlook 7j:", className="text-muted me-2"),
                dbc.Badge(outlook_days_7, color={
                    "positive": "success",
                    "neutral": "secondary",
                    "negative": "danger"
                }[outlook_days_7])
            ], md=6),
            dbc.Col([
                html.Small("Outlook 30j:", className="text-muted me-2"),
                dbc.Badge(outlook_days_30, color={
                    "positive": "success",
                    "neutral": "secondary",
                    "negative": "danger"
                }[outlook_days_30])
            ], md=6)
        ], className="mb-3"),

        # Contributors expander (collapsible)
        dbc.Accordion([
            dbc.AccordionItem([
                dbc.Table.from_dataframe(
                    pd.DataFrame(contributors)[["source", "symbol", "horizon", "prediction", "rationale"]],
                    id="overview-llm-contributors-table",
                    striped=True,
                    hover=True,
                    size="sm"
                )
            ], title=f"Voir Contributors ({len(contributors)})")
        ], id="overview-llm-contributors-accordion", start_collapsed=True, className="mb-3"),

        # Limits (warnings)
        html.Div([
            dbc.Alert([
                html.Strong("Limites: "),
                html.Ul([html.Li(limit) for limit in limits])
            ], color="warning", className="mb-0")
        ], id="overview-llm-limits") if limits else None,

        # Logs (collapsible, live refresh if running)
        dbc.Accordion([
            dbc.AccordionItem([
                html.Div(id="overview-llm-run-log", style={"maxHeight": "300px", "overflowY": "auto"})
            ], title="Voir Logs LLM")
        ], id="overview-llm-log-accordion", start_collapsed=True)
    ])
], id="overview-llm-summary-card")
```

---

## 🔄 Callbacks

### Callback 1: Bouton "Relancer LLM"
**Inputs**:
- `Input("overview-llm-run-btn", "n_clicks")`

**Outputs**:
- `Output("overview-llm-run-btn", "disabled")` (disable pendant exécution)
- `Output("overview-llm-run-btn", "children")` (texte → spinner)
- `Output("overview-llm-log-interval", "disabled")` (enable interval pour logs)
- `Output("overview-llm-run-log", "children")` (logs stdout)

**Logique**:
```python
from src.tools.make import run_make
from src.tools.lock import acquire_lock, release_lock

@callback(
    Output("overview-llm-run-btn", "disabled"),
    Output("overview-llm-run-btn", "children"),
    Output("overview-llm-log-interval", "disabled"),
    Output("overview-llm-run-log", "children"),
    Input("overview-llm-run-btn", "n_clicks"),
    prevent_initial_call=True
)
def run_llm_manual(n):
    if not n:
        raise PreventUpdate

    # Check lock
    if not acquire_lock("llm-summary-run", ttl=3600):
        return (
            True,
            [dbc.Spinner(size="sm"), " En cours..."],
            True,
            dbc.Alert("Un autre processus LLM est déjà en cours. Veuillez attendre.", color="warning")
        )

    try:
        # Run make target (async background)
        result = run_make("llm-summary-run", timeout=120)

        # Enable interval pour refresh logs
        return (
            False,  # Re-enable button
            "Relancer maintenant",
            False,  # Enable interval
            dbc.Alert(result["stdout"], color="info" if result["returncode"] == 0 else "danger")
        )
    finally:
        release_lock("llm-summary-run")
```

### Callback 2: Refresh Logs (Interval)
**Inputs**:
- `Input("overview-llm-log-interval", "n_intervals")`

**Outputs**:
- `Output("overview-llm-run-log", "children")`
- `Output("overview-llm-log-interval", "disabled")` (disable si terminé)

**Logique**:
```python
import subprocess

@callback(
    Output("overview-llm-run-log", "children", allow_duplicate=True),
    Output("overview-llm-log-interval", "disabled", allow_duplicate=True),
    Input("overview-llm-log-interval", "n_intervals"),
    prevent_initial_call=True
)
def refresh_llm_logs(n):
    if not n:
        raise PreventUpdate

    # Check if process still running
    lock_path = Path("artifacts/locks/llm-summary-run.lock")
    if not lock_path.exists():
        # Process terminé → disable interval
        return dbc.Alert("Terminé.", color="success"), True

    # Read latest logs
    log_path = Path("artifacts/logs/llm_summary.log")
    if log_path.exists():
        logs = log_path.read_text().split("\n")[-20:]  # Last 20 lines
        return html.Pre("\n".join(logs), style={"fontSize": "0.8rem"}), False
    else:
        return dbc.Alert("Logs en cours de génération...", color="info"), False
```

### Callback 3: Export CSV Top-N
**Inputs**:
- `Input("overview-equity-export-btn", "n_clicks")`

**Outputs**:
- `Output("overview-equity-download", "data")`

**Logique**:
```python
@callback(
    Output("overview-equity-download", "data"),
    Input("overview-equity-export-btn", "n_clicks"),
    State("overview-topN-equity-table", "data"),
    prevent_initial_call=True
)
def export_equity_csv(n, data):
    if not n:
        raise PreventUpdate

    df = pd.DataFrame(data)
    return dcc.send_data_frame(df.to_csv, "top10_equity.csv", index=False)
```

---

## 🧪 Tests

### 1. Test Route HTTP 200
**Fichier**: `tests/e2e/test_overview_page.py`

```python
def test_overview_page_loads(dash_duo):
    """Test page /integration_overview charge sans erreurs."""
    dash_duo.start_server(app)
    dash_duo.wait_for_page("/integration_overview", timeout=5)
    assert dash_duo.get_logs() == [], "Console errors detected"
```

### 2. Test Empty States
```python
def test_overview_empty_macro(dash_duo, monkeypatch):
    """Test empty state si macro_forecast absent."""
    monkeypatch.setattr("src.tools.parquet_io.read_parquet_latest", lambda *args: None)
    dash_duo.start_server(app)
    dash_duo.wait_for_text_to_equal("#overview-regime-card .alert", "Aucune donnée macro disponible.", timeout=5)
```

### 3. Test Bouton Relancer LLM
```python
def test_overview_llm_run_button(dash_duo, monkeypatch):
    """Test bouton 'Relancer LLM' disable/enable."""
    mock_result = {"stdout": "LLM summary generated", "stderr": "", "returncode": 0}
    monkeypatch.setattr("src.tools.make.run_make", lambda *args, **kwargs: mock_result)

    dash_duo.start_server(app)
    dash_duo.wait_for_element("#overview-llm-run-btn", timeout=5)

    # Click button
    dash_duo.find_element("#overview-llm-run-btn").click()

    # Check disabled during execution
    assert dash_duo.find_element("#overview-llm-run-btn").get_attribute("disabled") == "true"

    # Wait for completion (mock instant)
    time.sleep(0.5)

    # Check re-enabled
    assert dash_duo.find_element("#overview-llm-run-btn").get_attribute("disabled") is None
```

### 4. Test UI Health (Playwright)
**Fichier**: `ops/ui/dash_smoke.py`

```python
def test_overview_no_errors():
    """Screenshot Overview page, vérifie pas de .alert-danger."""
    page.goto("http://localhost:8050/integration_overview")
    page.wait_for_selector("#overview-regime-card", timeout=5000)

    # Check no errors
    errors = page.locator(".alert-danger").all()
    assert len(errors) == 0, "Error alerts found on Overview page"

    # Screenshot
    page.screenshot(path="artifacts/ui_health/overview.png")
```

---

## ✅ Définition de Fini (DoD)

- [ ] Page route `/integration_overview` accessible HTTP 200
- [ ] 5 cartes affichées (Régime, Risque, Top-10 Equity, Top-5 Commodities, Synthèse LLM)
- [ ] Empty states FR si partitions absentes
- [ ] Bouton "Relancer LLM" fonctionne (disable/enable + logs)
- [ ] Callback interval refresh logs (4s) pendant exécution
- [ ] Export CSV Top-10 fonctionne
- [ ] Tests dash.testing passent (routes, empty states, callbacks)
- [ ] UI health screenshot sans .alert-danger
- [ ] Retirer gate `DEVTOOLS_ENABLED` (page production-ready)
- [ ] Docs mises à jour (engineering_rules.md, module_index.md)

---

## 📚 Références

- **Backlog Idée**: `docs/ideas/10_feature_backlog.md` (Idée #01)
- **ADR Partitions**: `docs/architecture/adr/ADR-001-partitions-et-format.md`
- **ADR LLM**: `docs/architecture/adr/ADR-002-llm-g4f-arbitrage.md`
- **Module LLM Runtime**: `src/agents/llm/runtime.py`
- **Module Parquet IO**: `src/tools/parquet_io.py`

---

**Version**: 1.0
**Next Review**: Après implémentation Sprint 1
