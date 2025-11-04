# Contrats API - Finance Copilot

Documentation de référence pour les contrats d'API du Finance Copilot.
Toutes les routes respectent ces contrats pour assurer une intégration front/back stable.

---

## Règles générales

* **Collections**: toujours `[]`, jamais `null`
* **Dates**: format ISO-8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`)
* **Erreur**: format `{ok: false, error: {code, message}}`
* **Succès**: format `{ok: true, data: {...}}`
* **Métadonnées**: tous les objets incluent `freshness`, `source[]`, `version`

---

## /api/health

### GET

**But**: Vérifier la santé du service.

**Réponse (succès)**:
```json
{
  "status": "ok",
  "timestamp": "2025-11-03T19:03:00Z",
  "services": {
    "fred": true,
    "yfinance": true,
    "news": true,
    "rag": true
  }
}
```

---

## /api/macro/series

### GET

**But**: Récupérer des séries macroéconomiques (FRED).

**Paramètres**: 
- `ids`: Array de string (IDs FRED)
- `start`: String (optionnel, format YYYY-MM-DD)
- `end`: String (optionnel, format YYYY-MM-DD)

**Réponse (succès)**:
```json
{
  "ok": true,
  "data": {
    "CPIAUCSL": {
      "data": [{"t": "2024-01-01", "v": 298.4}, ...],
      "yoy": [{"t": "2024-01-01", "v": 3.14}, ...], 
      "source": "FRED",
      "generated_at": "2025-11-03T19:03:00Z"
    }
  }
}
```

---

## /api/macro/bundle

### GET

**But**: Récupérer le bundle macro US complet.

**Réponse (succès)**:
```json
{
  "ok": true, 
  "data": {
    "gdp": {...},
    "cpi": {...},
    "fed_rate": {...},
    "unemployment": {...},
    "freshness": "2025-11-03T19:03:00Z",
    "source": ["fred", "bea"],
    "version": "v1"
  }
}
```

---

## /api/stocks/prices

### GET

**But**: Récupérer les prix et indicateurs techniques.

**Paramètres**:
- `tickers`: Array de string (ex: ["SPY", "NVDA"])
- `range`: String (1d, 1y, etc.)
- `interval`: String (1d, 1wk, etc.)

**Réponse (succès)**:
```json
{
  "ok": true,
  "data": {
    "SPY": {
      "prices": [
        {"t": "2025-11-02", "o": 540.1, "h": 542.3, "l": 539.8, "c": 541.7, "v": 45123456}
      ],
      "indicators": {
        "rsi": 0.45,
        "sma_20": 538.2,
        "sma_50": 532.1,
        "macd": 2.1
      },
      "last_price": 541.7,
      "source": "yfinance",
      "generated_at": "2025-11-03T19:03:00Z"
    }
  }
}
```

---

## /api/stocks/fundamentals/{ticker}

### GET

**But**: Données fondamentales d'un ticker.

**Réponse (succès)**:
```json
{
  "ok": true,
  "data": {
    "market_cap": 3421000000000,
    "pe_ratio": 31.2,
    "dividend_yield": 0.005,
    "sector": "Technology",
    "freshness": "2025-11-03T19:03:00Z",
    "source": "yfinance",
    "version": "v1"
  }
}
```

---

## /api/news/feed

### GET

**But**: Flux d'actualités financières avec scoring.

**Paramètres**:
- `tickers`: Array de string (optionnel, filtre)
- `q`: String (optionnel, recherche)
- `limit`: Number (défaut: 50)
- `window`: String (défaut: "last_week")

**Réponse (succès)**:
```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "title": "Company Announces New Product",
        "url": "https://...",
        "published": "2025-11-03T15:30:00Z",
        "source": "bloomberg",
        "summary": "Company has...",
        "score": 0.82,
        "importance": 0.7,
        "freshness": 0.95,
        "relevance": 0.65,
        "sentiment": 0.25,
        "entities": ["COMP"],
        "tickers": ["COMP"]
      }
    ],
    "count": 12,
    "freshness": "2025-11-03T19:03:00Z",
    "source": ["rss:bloomberg", "rss:reuters"],
    "version": "v1"
  }
}
```

---

## /api/brief

### GET

**But**: Générer le Market Brief (daily/weekly).

**Paramètres**:
- `period`: String ("daily" | "weekly", défaut: "weekly")
- `universe`: Array de string (tickers, défaut: ["SPY", "QQQ"])

**Réponse (succès)**:
```json
{
  "ok": true,
  "data": {
    "top_signals": [{"title": "...", "score": 0.85, "type": "bullish"}],
    "top_risks": [{"title": "...", "score": -0.72, "type": "bearish"}],
    "picks": [{"ticker": "AAPL", "rationale": "..."}],
    "sources": ["macro", "tech", "news"],
    "generated_at": "2025-11-03T19:03:00Z",
    "period": "weekly",
    "universe": ["SPY", "QQQ"]
  }
}
```

---

## /api/dashboard/kpis

### GET

**But**: KPIs pour le dashboard.

**Réponse (succès)**:
```json
{
  "ok": true,
  "data": {
    "last_forecast_dt": "2025-11-03T18:00:00Z",
    "forecasts_count": 42,
    "tickers": 23,
    "horizons": ["1w", "1m", "3m"],
    "last_macro_dt": "2025-11-03T17:45:00Z",
    "last_quality_dt": "2025-11-03T19:00:00Z"
  }
}
```

---

## /api/tickers/{ticker}/sheet

### GET

**But**: Fiche complète d'un ticker.

**Réponse (succès)**:
```json
{
  "ok": true,
  "data": {
    "ticker": "SPY",
    "overview": {"last_price": 541.7, "change_pct": 0.85},
    "prices": [...],
    "indicators": {"rsi": 0.45, "sma_20": 538.2, ...},
    "news_top": [...],
    "levels": {...},
    "generated_at": "2025-11-03T19:03:00Z"
  }
}
```

---

## /api/copilot/ask

### POST

**But**: Q&A avec citations via LLM.

**Body**:
```json
{
  "question": "What is the outlook for NVDA?",
  "scope": {"tickers": ["NVDA"]},
  "horizon": "1w"
}
```

**Réponse (succès)**:
```json
{
  "ok": true,
  "data": {
    "answer": "Based on 15 sources...",
    "citations": [
      {"type": "news", "url": "...", "date": "...", "excerpt": "..."}
    ],
    "generated_at": "2025-11-03T19:03:00Z"
  }
}
```

---

## /api/forecasts

### GET

**But**: Prévisions hybrides ML + LLM.

**Paramètres**:
- `asset_type`: String ("all", "equity", "commodity")
- `horizon`: String ("all", "1w", "1m", "3m")
- `sort_by`: String ("score", "confidence")

**Réponse (succès)**:
```json
{
  "ok": true,
  "data": {
    "rows": [
      {
        "ticker": "NVDA",
        "horizon": "1w",
        "direction": "up",
        "confidence": 0.82,
        "expected_return": 0.032,
        "drivers": {"sma": "bullish", "sentiment": "positive"},
        "generated_at": "2025-11-03T18:00:00Z"
      }
    ],
    "count": 1,
    "asset_type": "all",
    "freshness": "2025-11-03T18:00:00Z",
    "source": ["ml", "g4f"],
    "version": "v1"
  }
}
```

---

## /api/backtests

### GET

**But**: Résultats des backtests de prévisions.

**Réponse (succès)**:
```json
{
  "ok": true,
  "data": {
    "results": [
      {
        "ticker": "NVDA",
        "strategy": "momentum",
        "hit_rate": 0.68,
        "avg_return": 0.021,
        "sharpe": 1.24,
        "period": {"from": "2024-01-01", "to": "2024-12-31"},
        "generated_at": "2025-11-02T23:00:00Z"
      }
    ],
    "since": "2024-01-01",
    "until": "2024-12-31",
    "freshness": "2025-11-02T23:00:00Z",
    "source": ["backtest_engine"],
    "version": "v1"
  }
}
```