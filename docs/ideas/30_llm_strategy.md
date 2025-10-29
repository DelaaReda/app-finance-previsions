# 🤖 Stratégie LLM — App Finance Prévisions

**Date**: 2025-10-29
**Architecte**: Claude Sonnet 4.5

---

## 🎯 Objectif

Définir **comment, quand, et pourquoi** utiliser les LLMs dans l'application:
- **Pattern**: Agents spécialisés → Arbitre LLM → Synthèse FR lisible
- **Provider**: g4f (gratuit, local-first, multi-models)
- **Prompts**: Structurés, JSON-mode, guidés par schémas
- **Explicabilité**: Sources + rationales + contributors

---

## 🏗️ Architecture LLM

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Pipeline LLM (Horaire + Manuel)               │
│                                                                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │ Agent        │    │ Agent        │    │ Agent        │          │
│  │ Technique    │    │ Macro        │    │ Sentiment    │          │
│  │ (forecasts)  │    │ (régimes)    │    │ (news)       │          │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘          │
│         │                   │                    │                  │
│         └───────────────────┼────────────────────┘                  │
│                             ▼                                        │
│                   ┌─────────────────────┐                           │
│                   │  Arbitre LLM        │                           │
│                   │  (DeepSeek R1)      │                           │
│                   │  Réconcilie + Justifie                          │
│                   └─────────┬───────────┘                           │
│                             │                                        │
│                             ▼                                        │
│                   ┌─────────────────────┐                           │
│                   │ summary.json         │                           │
│                   │ (LLMEnsembleSummary) │                           │
│                   │ dt=YYYYMMDDHH/       │                           │
│                   └─────────────────────┘                           │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Provider: g4f (GPT4Free)

### Pourquoi g4f?
1. **Gratuit**: Aucun coût API (vs OpenAI $0.03/1k tokens)
2. **Multi-models**: 50+ models (DeepSeek R1, Qwen 2.5, GLM-4, Llama 3.3, etc.)
3. **Anonyme**: Pas de tracking, pas de clés API
4. **Local-first**: Agents tournent sur infra Reda (pas de dépendance cloud)

### Limitations
1. **Instabilité providers**: Certains models down/rate-limited aléatoirement
2. **Latency**: 3-15s par requête (vs 1-2s OpenAI)
3. **Qualité variable**: Pas tous models égaux (DeepSeek R1 > autres)
4. **Pas de streaming**: Réponses complètes seulement

### Mitigations
- **Retry automatique**: 2 retries avec backoff exponentiel
- **Model fallback**: Si DeepSeek R1 down → Qwen 2.5 → GLM-4
- **Timeout**: 30s max par requête
- **Stub LLM tests**: Tests unitaires mockent LLMClient (pas de vrais calls)

---

## 📋 Pattern: Agents Spécialisés → Arbitre

### Principe
Au lieu d'un **seul prompt LLM "fais tout"** (fragile, opaque), on utilise **plusieurs agents spécialisés** qui génèrent des **hypothèses structurées**, puis un **arbitre LLM** qui:
1. Lit toutes les hypothèses
2. Réconcilie (pondère, identifie contradictions)
3. Justifie (explicite sources + poids)
4. Génère synthèse JSON (Pydantic validé)

### Avantages
- **Explicabilité**: Chaque contributor identifié (technique/macro/sentiment/qualité)
- **Robustesse**: Si 1 agent échoue, arbitre peut compenser
- **Testabilité**: Chaque agent testable unitairement
- **Évolutivité**: Ajouter agents sans changer arbitre

---

## 🧩 Agents Spécialisés

### 1. Agent Technique
**Rôle**: Analyser forecasts Top-N (scores, directions, confiance)

**Input**:
- `data/forecast/dt=*/final.parquet` (Top-50 par horizon)

**Prompt** (fonction toolkit):
```python
@toolkit_function
def analyze_technique(top_n: int = 50) -> str:
    """
    Analyse les Top-N forecasts techniques.
    Retourne JSON: [{"ticker": "NVDA", "horizon": "1m", "score": 0.82, "direction": "haussier", "confidence": 0.75}]
    """
    df = read_parquet_latest("data/forecast", "final.parquet")
    top = df.nlargest(top_n, "final_score")[["ticker", "horizon", "final_score", "direction", "confidence"]]
    return json.dumps(top.to_dict("records"), ensure_ascii=False)
```

**Output** (hypothèse):
```json
{
  "source": "technique",
  "top_picks": [
    {"ticker": "NVDA", "horizon": "1m", "score": 0.82, "rationale": "Momentum 21j fort (+12%), volume confirmant"}
  ],
  "trend": "bullish"
}
```

---

### 2. Agent Macro
**Rôle**: Analyser régime macro (expansion/contraction, risque)

**Input**:
- `data/macro/forecast/dt=*/macro_forecast.parquet` (dernière partition)

**Prompt** (fonction toolkit):
```python
@toolkit_function
def analyze_macro() -> str:
    """
    Analyse le régime macro actuel.
    Retourne JSON: {"regime": "expansion_modérée", "inflation_yoy": 2.4, "yield_curve_slope": 0.35, "unemployment": 4.1, "recession_prob": 0.15}
    """
    df = read_parquet_latest("data/macro/forecast", "macro_forecast.parquet")
    latest = df.tail(1).to_dict("records")[0]
    return json.dumps(latest, ensure_ascii=False)
```

**Output** (hypothèse):
```json
{
  "source": "macro",
  "regime": "expansion_modérée",
  "risk_level": "medium",
  "rationale": "Courbe pentification (+35bp) mais inflation persistante (2.4% YoY)"
}
```

---

### 3. Agent Sentiment (News)
**Rôle**: Agréger sentiment news par ticker

**Input**:
- `data/news/dt=*/news_*.parquet` (derniers 7 jours)

**Prompt** (fonction toolkit):
```python
@toolkit_function
def analyze_sentiment(days: int = 7) -> str:
    """
    Agrège sentiment news derniers N jours par ticker.
    Retourne JSON: [{"ticker": "NVDA", "sentiment": "positive", "articles_count": 5, "facts": ["Earnings beat Q4", "Nouveaux contrats cloud"]}]
    """
    news = read_parquet_latest("data/news", "news_*.parquet")
    # Filtrer derniers 7 jours
    news = news[news["published"] >= (datetime.utcnow() - timedelta(days=days))]
    # Agréger par ticker
    agg = news.groupby("ticker").agg({
        "sentiment": lambda x: "positive" if x.mean() > 0.5 else "negative" if x.mean() < -0.5 else "neutral",
        "title": "count"
    }).reset_index()
    agg.columns = ["ticker", "sentiment", "articles_count"]
    return json.dumps(agg.to_dict("records"), ensure_ascii=False)
```

**Output** (hypothèse):
```json
{
  "source": "sentiment",
  "ticker_sentiments": [
    {"ticker": "NVDA", "sentiment": "positive", "rationale": "5 articles positifs (earnings beat, nouveaux contrats cloud)"}
  ]
}
```

---

### 4. Agent Qualité
**Rôle**: Pénaliser tickers avec données périmées/manquantes

**Input**:
- `data/quality/dt=*/freshness.json`
- `data/quality/dt=*/report.json`

**Prompt** (fonction toolkit):
```python
@toolkit_function
def analyze_quality() -> str:
    """
    Identifie issues qualité (données périmées, schémas manquants).
    Retourne JSON: {"issues": [{"section": "prices", "severity": "error", "message": "10 tickers missing 5y data"}], "penalties": ["TICKER1", "TICKER2"]}
    """
    freshness = load_json("data/quality/dt=*/freshness.json")
    report = load_json("data/quality/dt=*/report.json")

    # Pénaliser si données > 48h
    penalties = []
    if (datetime.utcnow() - datetime.fromisoformat(freshness["latest"]["forecast_dt"])).days > 2:
        penalties.append("forecasts_stale")

    # Issues report
    issues = []
    for section, data in report.get("sections", {}).items():
        for issue in data.get("issues", []):
            if issue["sev"] == "error":
                issues.append({"section": section, "message": issue["msg"]})

    return json.dumps({"issues": issues, "penalties": penalties}, ensure_ascii=False)
```

**Output** (hypothèse):
```json
{
  "source": "quality",
  "issues": [
    {"section": "prices", "message": "10 tickers missing 5y data"}
  ],
  "penalties": ["forecasts_stale"]
}
```

---

## 🎭 Arbitre LLM

### Rôle
**Réconcilier** les 4 agents → **synthèse cohérente** + **justifications**

### Prompt (système)
```
Tu es membre d'un comité d'investissement. Ton rôle est de réconcilier les analyses de 4 analystes spécialisés et de générer une synthèse consensuelle pour un investisseur privé non-expert (Reda).

Contexte:
- Reda cherche 5-10 actions à fort potentiel court/moyen terme (7d, 30d)
- Il n'a pas de background finance → utilise français clair, pas de jargon
- Il veut COMPRENDRE pourquoi les signaux, pas juste "acheter X"

Règles:
1. Pondère les analystes selon confiance data (qualité > technique > sentiment > macro)
2. Si contradictions (ex: technique bullish mais macro bearish) → explique tensions
3. Si données périmées (penalties qualité) → mentionne dans limits
4. Génère JSON strictement conforme au schéma LLMEnsembleSummary (Pydantic)
5. key_drivers = 3-5 bullets FR (1 phrase chacun, explicite sources)
6. contributors = liste complète (1 row par agent/ticker/horizon avec rationale)
```

### Prompt (user)
```
Voici les 4 analyses:

1. **Analyste Technique (Forecasts Top-50)**:
{analyze_technique()}

2. **Analyste Macro (Régime actuel)**:
{analyze_macro()}

3. **Analyste Sentiment (News 7j)**:
{analyze_sentiment()}

4. **Analyste Qualité (Freshness/Issues)**:
{analyze_quality()}

Génère la synthèse JSON (schema ci-dessous):

```json
{
  "regime": "expansion_modérée | désinflation | contraction | incertain",
  "risk_level": "low | medium | high",
  "outlook_days_7": "positive | neutral | negative",
  "outlook_days_30": "positive | neutral | negative",
  "key_drivers": [
    "Driver 1 (source: technique/macro/sentiment)",
    "Driver 2",
    "Driver 3"
  ],
  "contributors": [
    {
      "source": "technique | macro | sentiment | quality",
      "model": "momentum | regime | news_llm | freshness",
      "horizon": "7d | 30d | 1y",
      "symbol": "NVDA",
      "score": 0.82,
      "prediction": "haussier | baissier | neutre",
      "rationale": "Explication 1 phrase FR"
    }
  ],
  "limits": [
    "Limitation 1 (ex: données macro H-48)",
    "Limitation 2"
  ]
}
```
```

### Paramètres LLM
- **Model**: `deepseek-ai/DeepSeek-R1-0528` (meilleur reasoning gratuit)
- **Temperature**: 0.2 (peu de créativité, reproductibilité)
- **Max tokens**: 2048 (synthèses longues OK)
- **JSON mode**: `json_mode=True` (force format)
- **Retries**: 2 (avec backoff 2s, 4s)

### Output (exemple réel)
```json
{
  "regime": "expansion_modérée",
  "risk_level": "medium",
  "outlook_days_7": "positive",
  "outlook_days_30": "neutral",
  "key_drivers": [
    "Désinflation continue (CPI YoY -0.2% MoM, slope +15bp)",
    "Tech surperformance (NVDA +8% 7j, IA demande robuste, 5 articles positifs)",
    "Risque taux persistant (DGS10 4.5%, pénalise valorisations growth)"
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
    },
    {
      "source": "macro",
      "model": "regime",
      "horizon": "3m",
      "symbol": "SPY",
      "score": 0.65,
      "prediction": "modéré",
      "rationale": "Slope +0.35 mais unemployment stable 4.1%"
    },
    {
      "source": "sentiment",
      "model": "news_llm",
      "horizon": "7d",
      "symbol": "NVDA",
      "score": 0.75,
      "prediction": "positive",
      "rationale": "5 articles positifs (earnings beat, nouveaux contrats)"
    },
    {
      "source": "quality",
      "model": "freshness",
      "horizon": "n/a",
      "symbol": "n/a",
      "score": 0.85,
      "prediction": "vert",
      "rationale": "Toutes partitions < 24h sauf macro (H-48)"
    }
  ],
  "limits": [
    "Données macro H-48 (FRED delay)",
    "Faible couverture sectorielle utilities/healthcare (< 10 tickers)"
  ]
}
```

---

## 📅 Orchestration

### Horaire (Automatique)
- **Scheduler**: APScheduler (src/agents/agent_runner/scheduler.py)
- **Fréquence**: **Top of every hour** (00 minutes)
- **Target Make**: `llm-summary-run`
- **Durée**: 30-60s (4 agents + arbitre)
- **Output**: `data/llm_summary/dt=YYYYMMDDHH/summary.json`

### Manuel (UI)
- **Page**: `/llm_summary`
- **Bouton**: "Relancer maintenant"
- **Callback**:
  ```python
  @callback(
      Output("llm-run-btn", "disabled"),
      Output("llm-run-log", "children"),
      Input("llm-run-btn", "n_clicks")
  )
  def run_llm_manual(n):
      if n:
          # Disable button
          result = run_make("llm-summary-run", timeout=120)
          # Log stdout
          return False, dbc.Alert(result["stdout"], color="info")
      return False, ""
  ```

### Locks (Anti Collision)
- **Lock file**: `artifacts/locks/llm-summary-run.lock`
- **TTL**: 3600s (1h)
- **Logique**:
  ```python
  if acquire_lock("llm-summary-run"):
      try:
          run_llm_summary()
      finally:
          release_lock("llm-summary-run")
  else:
      logger.warning("Lock held, skipping")
  ```

---

## 🧪 Validation & Tests

### 1. Schema Pydantic
**Fichier**: `src/agents/llm/schemas.py`

```python
from pydantic import BaseModel, Field
from typing import List, Literal

class Contributor(BaseModel):
    source: Literal["technique", "macro", "sentiment", "quality"]
    model: str  # "momentum", "regime", "news_llm", "freshness"
    horizon: str  # "7d", "30d", "1y", "n/a"
    symbol: str  # "NVDA", "SPY", "n/a"
    score: float = Field(ge=0.0, le=1.0)
    prediction: str  # "haussier", "baissier", "neutre", "vert"
    rationale: str  # 1-2 phrases FR

class LLMEnsembleSummary(BaseModel):
    regime: Literal["expansion_modérée", "désinflation", "contraction", "incertain"]
    risk_level: Literal["low", "medium", "high"]
    outlook_days_7: Literal["positive", "neutral", "negative"]
    outlook_days_30: Literal["positive", "neutral", "negative"]
    key_drivers: List[str] = Field(min_items=3, max_items=5)
    contributors: List[Contributor]
    limits: List[str] = Field(default_factory=list)
```

### 2. Tests Unitaires
**Fichier**: `tests/llm/test_llm_summary.py`

```python
def test_llm_summary_schema_valid():
    """Vérifie que le schema Pydantic valide correctement."""
    data = {
        "regime": "expansion_modérée",
        "risk_level": "medium",
        "outlook_days_7": "positive",
        "outlook_days_30": "neutral",
        "key_drivers": ["Driver 1", "Driver 2", "Driver 3"],
        "contributors": [
            {
                "source": "technique",
                "model": "momentum",
                "horizon": "1m",
                "symbol": "NVDA",
                "score": 0.82,
                "prediction": "haussier",
                "rationale": "Momentum fort"
            }
        ],
        "limits": []
    }
    summary = LLMEnsembleSummary(**data)
    assert summary.regime == "expansion_modérée"
    assert len(summary.contributors) == 1

def test_llm_summary_invalid_regime():
    """Vérifie que Pydantic rejette régimes invalides."""
    data = {"regime": "invalid_regime", ...}
    with pytest.raises(ValidationError):
        LLMEnsembleSummary(**data)

def test_llm_arbiter_with_mock():
    """Test arbiter avec LLMClient mocké."""
    with patch("src.agents.llm.runtime.LLMClient.generate") as mock_gen:
        mock_gen.return_value = json.dumps({
            "regime": "expansion_modérée",
            "risk_level": "medium",
            "outlook_days_7": "positive",
            "outlook_days_30": "neutral",
            "key_drivers": ["Driver 1", "Driver 2", "Driver 3"],
            "contributors": [],
            "limits": []
        })

        summary = run_llm_summary()
        assert summary["regime"] == "expansion_modérée"
        mock_gen.assert_called_once()
```

### 3. Tests Integration
**Fichier**: `tests/integration/test_llm_arbiter.py`

```python
@pytest.mark.skipif(not os.getenv("AF_ALLOW_INTERNET"), reason="Requires internet")
def test_llm_arbiter_real_call():
    """Test arbiter avec vrai call g4f (slow, skip CI)."""
    summary = run_llm_summary()
    assert "regime" in summary
    assert len(summary["key_drivers"]) >= 3
    assert len(summary["contributors"]) >= 1
```

---

## 🔍 Monitoring & Observability

### Logs (Structured)
- **Fichier**: `artifacts/logs/llm_summary.log`
- **Format**: JSON lines
  ```json
  {"timestamp": "2025-10-29T14:00:00Z", "level": "INFO", "agent": "technique", "duration_ms": 3200, "top_n": 50}
  {"timestamp": "2025-10-29T14:00:03Z", "level": "INFO", "agent": "macro", "duration_ms": 1800}
  {"timestamp": "2025-10-29T14:00:05Z", "level": "INFO", "agent": "sentiment", "duration_ms": 4100}
  {"timestamp": "2025-10-29T14:00:09Z", "level": "INFO", "agent": "quality", "duration_ms": 1200}
  {"timestamp": "2025-10-29T14:00:11Z", "level": "INFO", "arbiter": "DeepSeek-R1", "duration_ms": 8500, "status": "success"}
  ```

### Metrics (Prometheus-style)
- `llm_summary_duration_seconds{agent="technique"}`: Latency par agent
- `llm_summary_calls_total{status="success|failure"}`: Count success/errors
- `llm_summary_tokens_total{model="DeepSeek-R1"}`: Token usage (si API supporte)

### Alerts
- **Critère**: `llm_summary_calls_total{status="failure"}` > 3 last 1h → Slack/Email
- **Page UI**: `/observability` affiche derniers 10 runs (success/failure + durée)

---

## 🚀 Évolutions Futures

### Court Terme
1. **Retry intelligent**: Si DeepSeek R1 down → fallback Qwen 2.5
2. **Cache LLM**: Si inputs identiques dernière heure → réutiliser réponse
3. **Parallel agents**: Run 4 agents en parallèle (async) → réduire latency totale 60s → 15s

### Moyen Terme
1. **Fine-tune local**: Llama 3.3 70B fine-tuné sur historique summaries Reda → quality++
2. **RAG integration**: Vector DB (ChromaDB) pour recherche news similaires → context enrichi
3. **Multi-langue**: Support EN/FR switch (env LANGUAGE=fr)

### Long Terme
1. **Self-improving**: Feedback loop Reda (👍👎 sur summary) → fine-tune adaptatif
2. **Causal reasoning**: Intégrer causal graphs (macro → secteurs → tickers)
3. **Explainable AI**: SHAP/LIME pour expliquer poids contributors

---

## 📚 Références

- **Code**: `src/agents/llm/arbiter_agent.py`, `runtime.py`, `toolkit.py`, `schemas.py`
- **Tests**: `tests/llm/test_llm_summary.py`, `tests/integration/test_llm_arbiter.py`
- **Docs g4f**: https://github.com/xtekky/gpt4free
- **DeepSeek R1**: https://huggingface.co/deepseek-ai/DeepSeek-R1
- **Pydantic**: https://docs.pydantic.dev/

---

**Version**: 1.0
**Next Review**: Après intégration arbiter multi-agents (idée #09 backlog)
