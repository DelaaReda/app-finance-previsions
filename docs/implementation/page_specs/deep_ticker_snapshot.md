# 🔍 Page Spec — Deep Ticker Snapshot Multi-Horizons

**Page Route**: `/deep_dive` (amélioration existante)
**Priority**: 🥈 Medium (RoI = 12.0)
**Status**: ✅ Fonctionnelle → Améliorations UX
**Assigné**: Dev Team

---

## 🎯 Objectif UX

Améliorer page `/deep_dive` existante pour fournir **analyse complète 1 ticker** avec:
1. **Tableau multi-horizons** (7d/30d/1y en 1 vue, pas 3 tableaux séparés)
2. **Mini-justification LLM** par ticker (2-3 phrases: drivers techniques + macro)
3. **Overlay prix enrichi** (graphique avec bandes Bollinger + événements earnings annotés)
4. **Comparateur peers** (5 tickers secteur similaire, returns 1m/3m)

**Persona**: Reda (investisseur, veut comprendre "pourquoi" signal avant décision)

**Use Case**:
- Overview → Top-10 affiche NVDA score 0.82
- → Clic ticker → Deep Dive NVDA
- → Voit tableau multi-horizons (7d haussier 0.78, 30d modéré 0.65, 1y neutre 0.45)
- → Lit justification LLM ("Momentum court terme fort mais macro tensions taux")
- → Voit graphique prix + Bollinger bands + annotation "Earnings Q4 +15%"
- → Compare peers (AMD +8%, INTC +2%, QCOM +5% sur 1m)
- → Décision: "OK acheter NVDA short-term, exit avant 1y"

---

## 📥 Sources de Données

### 1. Forecasts Multi-Horizons (Existant)
**Partition**: `data/forecast/dt=YYYYMMDD/final.parquet`

**Colonnes**:
- `ticker` (str): NVDA
- `horizon` (str): "1w", "1m", "1y"
- `final_score` (float): 0.0-1.0
- `direction` (str, optionnel): "haussier" | "baissier" | "neutre"
- `confidence` (float, optionnel): 0.0-1.0

**Transformation pour tableau multi-horizons**:
```python
df = read_parquet_latest("data/forecast", "final.parquet")
df_ticker = df[df["ticker"] == selected_ticker]

# Pivot pour avoir 1 row par ticker, colonnes par horizon
pivot = df_ticker.pivot_table(
    index="ticker",
    columns="horizon",
    values=["final_score", "direction", "confidence"]
).reset_index()

# Renommer colonnes: final_score_1w, final_score_1m, final_score_1y, etc.
```

**Empty State**: "Aucun forecast disponible pour ce ticker."

---

### 2. LLM Context (Rationale)
**Partition**: `data/llm/context/dt=YYYYMMDD/TICKER.json`

**Schema JSON**:
```json
{
  "ticker": "NVDA",
  "asof": "2025-10-29T14:00:00Z",
  "rationale_short": "Momentum 21j fort (+12%), volume confirmant. Macro: taux élevés pénalisent valorisation long terme.",
  "technical": {
    "rsi_14": 68.5,
    "macd_signal": "bullish",
    "sma_20": 145.2,
    "sma_50": 138.7
  },
  "fundamental": {
    "pe_ratio": 45.2,
    "debt_to_equity": 0.35,
    "roe": 0.28
  },
  "news_summary": "5 articles positifs (earnings beat Q4, nouveaux contrats cloud)"
}
```

**Loader**: `load_json(f"data/llm/context/dt=*/{ ticker}.json")`

**Fallback si absent**: Générer rationale à la volée (appel LLM light):
```python
def generate_rationale_light(ticker: str, forecasts: pd.DataFrame) -> str:
    """
    Génère rationale 2-3 phrases si llm/context absent.
    Utilise forecasts + macro actuel.
    """
    client = LLMClient(provider="g4f", model="deepseek-ai/DeepSeek-R1-0528")
    prompt = f"""
    Tu es analyste. Explique en 2-3 phrases FR pourquoi {ticker} a ces forecasts:
    - 7j: {forecasts['1w']['final_score']:.2f} ({forecasts['1w']['direction']})
    - 30j: {forecasts['1m']['final_score']:.2f} ({forecasts['1m']['direction']})
    - 1y: {forecasts['1y']['final_score']:.2f} ({forecasts['1y']['direction']})

    Inclus drivers techniques (momentum, RSI) ET macro (taux, régime).
    """
    response = client.generate([{"role": "user", "content": prompt}], temperature=0.3, max_tokens=256)
    return response
```

---

### 3. Prix + Événements (Existant + Nouveaux)
**Partition Prix**: `data/prices/ticker=TICKER/prices.parquet`

**Colonnes**:
- `date` (datetime)
- `Open`, `High`, `Low`, `Close`, `Volume` (float)

**Partition Earnings** (nouveau):
**Partition**: `data/earnings/dt=YYYYMMDD/earnings.json`

**Schema**:
```json
{
  "events": [
    {
      "ticker": "NVDA",
      "date": "2025-11-15",
      "type": "earnings",
      "info": "Q4 FY2025"
    }
  ]
}
```

**Calculs Bollinger Bands**:
```python
def calculate_bollinger_bands(df: pd.DataFrame, window: int = 20, num_std: int = 2) -> pd.DataFrame:
    df["sma_20"] = df["Close"].rolling(window).mean()
    df["std_20"] = df["Close"].rolling(window).std()
    df["bb_upper"] = df["sma_20"] + (num_std * df["std_20"])
    df["bb_lower"] = df["sma_20"] - (num_std * df["std_20"])
    return df
```

---

### 4. Peers Comparison (Nouveau)
**Source**: Hardcodé par secteur OU yfinance similar tickers

**Secteurs hardcodés** (exemples):
```python
SECTOR_PEERS = {
    "tech": ["NVDA", "AMD", "INTC", "QCOM", "TSM"],
    "finance": ["JPM", "BAC", "WFC", "C", "GS"],
    "energy": ["XOM", "CVX", "COP", "SLB", "EOG"],
    # ...
}

def get_peers(ticker: str, sector: str = None) -> List[str]:
    """
    Retourne 5 peers du même secteur.
    Si secteur inconnu, return tickers watchlist.
    """
    if sector and sector in SECTOR_PEERS:
        peers = SECTOR_PEERS[sector]
        # Remove ticker itself
        peers = [p for p in peers if p != ticker]
        return peers[:5]
    else:
        # Fallback: watchlist
        watchlist = load_json("data/watchlist.json").get("watchlist", [])
        return [t for t in watchlist if t != ticker][:5]
```

**Calcul Returns Peers**:
```python
def calculate_peer_returns(tickers: List[str], periods: List[int] = [21, 63]) -> pd.DataFrame:
    """
    Calcule returns 1m (21d), 3m (63d) pour chaque ticker.
    """
    results = []
    for ticker in tickers:
        prices = read_parquet(f"data/prices/ticker={ticker}/prices.parquet")
        if prices is None or len(prices) < 63:
            continue
        close = prices["Close"]
        ret_1m = (close.iloc[-1] - close.iloc[-21]) / close.iloc[-21]
        ret_3m = (close.iloc[-1] - close.iloc[-63]) / close.iloc[-63]
        results.append({
            "ticker": ticker,
            "return_1m": ret_1m,
            "return_3m": ret_3m
        })
    return pd.DataFrame(results)
```

---

## 🎨 Layout & IDs

### Structure Globale (Amélioration existante)
```python
html.Div([
    html.H2("Analyse Approfondie", className="mb-4"),

    # Row 0: Ticker selector (existant)
    dbc.Row([
        dbc.Col([
            dbc.InputGroup([
                dbc.InputGroupText("Ticker"),
                dbc.Input(
                    id="deep-dive-ticker-input",
                    type="text",
                    placeholder="NVDA",
                    value="NGD.TO"  # Default
                ),
                dbc.Button("Analyser", id="deep-dive-submit-btn", color="primary")
            ])
        ], md=6)
    ], className="mb-4"),

    # Row 1: Tableau Multi-Horizons + LLM Rationale
    dbc.Row([
        dbc.Col([
            # Carte Tableau Multi-Horizons
        ], md=8),
        dbc.Col([
            # Carte LLM Rationale
        ], md=4)
    ], className="mb-4"),

    # Row 2: Graphique Prix + Bollinger + Événements (existant amélioré)
    dbc.Row([
        dbc.Col([
            # Carte Graphique Prix
        ], md=12)
    ], className="mb-4"),

    # Row 3: Peers Comparison (nouveau)
    dbc.Row([
        dbc.Col([
            # Carte Peers
        ], md=12)
    ], className="mb-4"),

    # Row 4+: Sections existantes (News, Fundamentals, Technical, etc.)
    # ...
])
```

---

### Carte 1: Tableau Multi-Horizons (NOUVEAU)
**ID**: `#deep-dive-multi-horizon-card`

**Composants**:
```python
dbc.Card([
    dbc.CardHeader("Forecasts Multi-Horizons"),
    dbc.CardBody([
        dbc.Table(
            [
                html.Thead(html.Tr([
                    html.Th("Horizon"),
                    html.Th("Score"),
                    html.Th("Direction"),
                    html.Th("Confiance"),
                    html.Th("Interprétation")
                ])),
                html.Tbody([
                    # Row 7 jours
                    html.Tr([
                        html.Td("7 jours"),
                        html.Td(f"{score_7d:.2f}"),
                        html.Td(dbc.Badge(direction_7d, color="success" if direction_7d == "haussier" else "danger")),
                        html.Td(f"{confidence_7d:.0%}"),
                        html.Td(html.Small("Court terme fort" if score_7d > 0.7 else "Court terme faible", className="text-muted"))
                    ]),
                    # Row 30 jours
                    html.Tr([
                        html.Td("30 jours"),
                        html.Td(f"{score_30d:.2f}"),
                        html.Td(dbc.Badge(direction_30d, color="success" if direction_30d == "haussier" else "danger")),
                        html.Td(f"{confidence_30d:.0%}"),
                        html.Td(html.Small("Moyen terme modéré" if 0.5 < score_30d < 0.7 else "Moyen terme fort/faible", className="text-muted"))
                    ]),
                    # Row 1 an
                    html.Tr([
                        html.Td("1 an"),
                        html.Td(f"{score_1y:.2f}"),
                        html.Td(dbc.Badge(direction_1y, color="success" if direction_1y == "haussier" else "danger")),
                        html.Td(f"{confidence_1y:.0%}"),
                        html.Td(html.Small("Long terme incertain" if score_1y < 0.5 else "Long terme positif", className="text-muted"))
                    ])
                ])
            ],
            id="deep-dive-multi-horizon-table",
            bordered=True,
            hover=True,
            striped=True
        )
    ])
], id="deep-dive-multi-horizon-card")
```

**Interprétation Colonne** (aide Reda non-expert):
- Score > 0.7: "Fort"
- 0.5 < Score < 0.7: "Modéré"
- Score < 0.5: "Faible"

---

### Carte 2: LLM Rationale (NOUVEAU)
**ID**: `#deep-dive-llm-rationale-card`

**Composants**:
```python
dbc.Card([
    dbc.CardHeader("Justification LLM"),
    dbc.CardBody([
        html.P(
            rationale_text,
            id="deep-dive-llm-rationale-text",
            className="mb-3"
        ),
        dbc.Button(
            "Régénérer",
            id="deep-dive-llm-rationale-refresh-btn",
            size="sm",
            color="link"
        ),
        dbc.Spinner(
            html.Div(id="deep-dive-llm-rationale-spinner"),
            size="sm",
            spinner_style={"display": "none"}
        )
    ])
], id="deep-dive-llm-rationale-card", className="h-100")
```

**Empty State**: "Aucune justification disponible. Cliquez 'Régénérer'."

---

### Carte 3: Graphique Prix + Bollinger + Événements (AMÉLIORATION EXISTANTE)
**ID**: `#deep-dive-price-chart` (existant)

**Améliorations**:
1. **Ajouter Bollinger Bands** (traces Plotly)
2. **Annoter Earnings** (shapes Plotly)

**Plotly Code**:
```python
import plotly.graph_objects as go

# Calcul Bollinger
df_prices = calculate_bollinger_bands(df_prices)

# Earnings events
earnings_dates = [e["date"] for e in earnings_events if e["ticker"] == selected_ticker]

fig = go.Figure()

# Trace Prix
fig.add_trace(go.Scatter(
    x=df_prices["date"],
    y=df_prices["Close"],
    mode="lines",
    name="Prix",
    line=dict(color="blue", width=2)
))

# Trace SMA 20
fig.add_trace(go.Scatter(
    x=df_prices["date"],
    y=df_prices["sma_20"],
    mode="lines",
    name="SMA 20",
    line=dict(color="orange", width=1, dash="dash")
))

# Trace Bollinger Upper/Lower
fig.add_trace(go.Scatter(
    x=df_prices["date"],
    y=df_prices["bb_upper"],
    mode="lines",
    name="Bollinger Upper",
    line=dict(color="gray", width=1, dash="dot"),
    showlegend=False
))

fig.add_trace(go.Scatter(
    x=df_prices["date"],
    y=df_prices["bb_lower"],
    mode="lines",
    name="Bollinger Lower",
    line=dict(color="gray", width=1, dash="dot"),
    fill="tonexty",  # Fill between upper and lower
    fillcolor="rgba(200, 200, 200, 0.2)",
    showlegend=False
))

# Annotations Earnings
for earnings_date in earnings_dates:
    fig.add_vline(
        x=earnings_date,
        line=dict(color="green", width=2, dash="dash"),
        annotation_text="Earnings",
        annotation_position="top"
    )

fig.update_layout(
    title=f"{selected_ticker} — Prix + Bollinger Bands (20j, 2σ)",
    xaxis_title="Date",
    yaxis_title="Prix ($)",
    hovermode="x unified",
    template="plotly_dark"
)

dcc.Graph(figure=fig, id="deep-dive-price-chart")
```

---

### Carte 4: Peers Comparison (NOUVEAU)
**ID**: `#deep-dive-peers-card`

**Composants**:
```python
dbc.Card([
    dbc.CardHeader(f"Comparaison Peers (Secteur: {sector})"),
    dbc.CardBody([
        dbc.Table.from_dataframe(
            df_peers[["ticker", "return_1m", "return_3m"]],
            id="deep-dive-peers-table",
            striped=True,
            bordered=True,
            hover=True
        )
    ])
], id="deep-dive-peers-card")
```

**Formatage Colonnes**:
- `return_1m`: `0.08` → "+8.0%" (vert si > 0, rouge si < 0)
- `return_3m`: `0.15` → "+15.0%"

**Tri**: Par `return_1m DESC` (meilleurs performers en haut)

---

## 🔄 Callbacks

### Callback 1: Submit Ticker (Existant, à améliorer)
**Inputs**:
- `Input("deep-dive-submit-btn", "n_clicks")`
- `State("deep-dive-ticker-input", "value")`

**Outputs**:
- `Output("deep-dive-multi-horizon-table", "children")`
- `Output("deep-dive-llm-rationale-text", "children")`
- `Output("deep-dive-price-chart", "figure")`
- `Output("deep-dive-peers-table", "children")`
- (+ outputs existants: news, fundamentals, etc.)

**Logique**:
```python
@callback(
    Output("deep-dive-multi-horizon-table", "children"),
    Output("deep-dive-llm-rationale-text", "children"),
    Output("deep-dive-price-chart", "figure"),
    Output("deep-dive-peers-table", "children"),
    Input("deep-dive-submit-btn", "n_clicks"),
    State("deep-dive-ticker-input", "value"),
    prevent_initial_call=False  # Load default ticker on page load
)
def update_deep_dive(n, ticker):
    if not ticker:
        ticker = "NGD.TO"

    ticker = ticker.upper().strip()

    # 1. Load forecasts multi-horizons
    df_forecasts = read_parquet_latest("data/forecast", "final.parquet")
    df_ticker = df_forecasts[df_forecasts["ticker"] == ticker]

    if df_ticker.empty:
        multi_horizon_table = html.Tr([html.Td("Aucun forecast disponible.", colspan=5)])
    else:
        # Pivot horizons
        horizons = {"1w": "7 jours", "1m": "30 jours", "1y": "1 an"}
        rows = []
        for h_code, h_label in horizons.items():
            row_data = df_ticker[df_ticker["horizon"] == h_code].iloc[0] if len(df_ticker[df_ticker["horizon"] == h_code]) > 0 else None
            if row_data is not None:
                score = row_data["final_score"]
                direction = row_data.get("direction", "neutre")
                confidence = row_data.get("confidence", 0.5)
                interpretation = "Fort" if score > 0.7 else "Modéré" if score > 0.5 else "Faible"

                rows.append(html.Tr([
                    html.Td(h_label),
                    html.Td(f"{score:.2f}"),
                    html.Td(dbc.Badge(direction, color="success" if direction == "haussier" else "danger" if direction == "baissier" else "secondary")),
                    html.Td(f"{confidence:.0%}"),
                    html.Td(html.Small(interpretation, className="text-muted"))
                ]))
        multi_horizon_table = rows

    # 2. Load LLM rationale
    rationale = load_json(f"data/llm/context/dt=*/{ticker}.json")
    if rationale:
        rationale_text = rationale.get("rationale_short", "Aucune justification disponible.")
    else:
        # Generate on-the-fly
        rationale_text = generate_rationale_light(ticker, df_ticker)

    # 3. Load prices + Bollinger
    df_prices = read_parquet(f"data/prices/ticker={ticker}/prices.parquet")
    if df_prices is None or df_prices.empty:
        price_chart = go.Figure().add_annotation(text="Aucune donnée prix disponible.", showarrow=False)
    else:
        df_prices = calculate_bollinger_bands(df_prices)
        earnings_events = load_json("data/earnings/dt=*/earnings.json").get("events", [])
        price_chart = create_price_chart_with_bollinger(df_prices, ticker, earnings_events)

    # 4. Load peers
    sector = "tech"  # TODO: infer from ticker or hardcode mapping
    peers = get_peers(ticker, sector)
    df_peers = calculate_peer_returns(peers)
    if df_peers.empty:
        peers_table = html.Tr([html.Td("Aucun peer disponible.", colspan=3)])
    else:
        peers_table = dbc.Table.from_dataframe(df_peers, striped=True, bordered=True, hover=True)

    return multi_horizon_table, rationale_text, price_chart, peers_table
```

---

### Callback 2: Régénérer LLM Rationale (NOUVEAU)
**Inputs**:
- `Input("deep-dive-llm-rationale-refresh-btn", "n_clicks")`
- `State("deep-dive-ticker-input", "value")`

**Outputs**:
- `Output("deep-dive-llm-rationale-text", "children", allow_duplicate=True)`
- `Output("deep-dive-llm-rationale-spinner", "spinner_style")`

**Logique**:
```python
@callback(
    Output("deep-dive-llm-rationale-text", "children", allow_duplicate=True),
    Output("deep-dive-llm-rationale-spinner", "spinner_style"),
    Input("deep-dive-llm-rationale-refresh-btn", "n_clicks"),
    State("deep-dive-ticker-input", "value"),
    prevent_initial_call=True
)
def regenerate_rationale(n, ticker):
    if not n or not ticker:
        raise PreventUpdate

    # Show spinner
    # Generate rationale
    df_forecasts = read_parquet_latest("data/forecast", "final.parquet")
    df_ticker = df_forecasts[df_forecasts["ticker"] == ticker.upper()]

    rationale = generate_rationale_light(ticker.upper(), df_ticker)

    return rationale, {"display": "none"}
```

---

## 🧪 Tests

### 1. Test Route HTTP 200
**Fichier**: `tests/e2e/test_deep_dive_enhanced.py`

```python
def test_deep_dive_page_loads(dash_duo):
    """Test page /deep_dive charge sans erreurs."""
    dash_duo.start_server(app)
    dash_duo.wait_for_page("/deep_dive", timeout=5)
    assert dash_duo.get_logs() == [], "Console errors detected"
```

### 2. Test Multi-Horizon Table
```python
def test_deep_dive_multi_horizon_table(dash_duo):
    """Test tableau multi-horizons présent avec 3 rows."""
    dash_duo.start_server(app)
    dash_duo.wait_for_element("#deep-dive-multi-horizon-table", timeout=5)
    rows = dash_duo.find_elements("#deep-dive-multi-horizon-table tbody tr")
    assert len(rows) == 3, f"Expected 3 horizon rows (7d/30d/1y), got {len(rows)}"
```

### 3. Test LLM Rationale
```python
def test_deep_dive_llm_rationale(dash_duo, monkeypatch):
    """Test rationale LLM affichée."""
    mock_rationale = "Momentum fort court terme mais macro tensions."
    monkeypatch.setattr("src.dash_app.pages.deep_dive.generate_rationale_light", lambda *args: mock_rationale)

    dash_duo.start_server(app)
    dash_duo.wait_for_text_to_equal("#deep-dive-llm-rationale-text", mock_rationale, timeout=5)
```

### 4. Test Bollinger Bands Chart
```python
def test_deep_dive_bollinger_chart(dash_duo):
    """Test graphique contient traces Bollinger."""
    dash_duo.start_server(app)
    dash_duo.wait_for_element("#deep-dive-price-chart", timeout=5)

    # Check Plotly figure contains Bollinger traces
    fig_json = dash_duo.driver.execute_script("return document.getElementById('deep-dive-price-chart').data")
    trace_names = [trace["name"] for trace in fig_json]
    assert "Bollinger Upper" in trace_names, "Bollinger Upper trace missing"
    assert "Bollinger Lower" in trace_names, "Bollinger Lower trace missing"
```

### 5. Test Peers Table
```python
def test_deep_dive_peers_table(dash_duo):
    """Test peers table présente avec ≥1 row."""
    dash_duo.start_server(app)
    dash_duo.wait_for_element("#deep-dive-peers-table", timeout=5)
    rows = dash_duo.find_elements("#deep-dive-peers-table tbody tr")
    assert len(rows) >= 1, "Expected at least 1 peer row"
```

---

## ✅ Définition de Fini (DoD)

- [ ] Tableau multi-horizons remplace 3 tableaux séparés
- [ ] Rationale LLM affichée (context partition OU généré on-the-fly)
- [ ] Bouton "Régénérer" rationale fonctionne
- [ ] Graphique prix inclut Bollinger Bands (upper/lower/fill)
- [ ] Événements earnings annotés (vlines Plotly)
- [ ] Peers table affiche 5 tickers avec returns 1m/3m
- [ ] Empty states FR si données absentes
- [ ] Tests passent (5 tests E2E)
- [ ] UI health screenshot sans .alert-danger
- [ ] Docs mises à jour

---

## 🔧 Modules Réutilisés

- ✅ `src/tools/parquet_io.py`: `read_parquet_latest()`, `read_parquet()`
- ✅ `src/dash_app/data/loader.py`: `load_json()`
- ✅ `src/agents/llm/runtime.py`: `LLMClient.generate()` (rationale on-the-fly)
- ✅ `src/dash_app/logic/deep_dive_logic.py`: `calculate_returns()` (peers)

---

## 📊 Améliorations Futures (Post-Sprint 1)

### 1. Secteur Auto-Détection
Utiliser yfinance `Ticker.info["sector"]` pour inférer secteur automatiquement.

### 2. Comparateur Multi-Tickers
Graphique overlay 5 tickers (normalized base 100).

### 3. Technical Indicators Enrichis
MACD, Stochastic, Ichimoku Cloud.

### 4. News Timeline
Timeline annotée avec articles majeurs (plotly timeline).

---

## 📚 Références

- **Backlog Idée**: `docs/ideas/10_feature_backlog.md` (Idée #06)
- **Page Existante**: `src/dash_app/pages/deep_dive.py:1`
- **Logic Helpers**: `src/dash_app/logic/deep_dive_logic.py`

---

**Version**: 1.0
**Next Review**: Après implémentation Sprint 1 ou 2
