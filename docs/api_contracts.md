# Contrats d'API (canonique)

Dernière mise à jour : 2025-11-02

Ces contrats définissent les endpoints stables de l'API FastAPI. Toutes les réponses incluent les champs de traçabilité : `source`, `asof_date`, `created_at`, `hash`.

## GET /api/health

**Params** : Aucun  
**Response** :
```json
{
  "status": "ok",
  "version": "2.0.0",
  "time": "2025-11-02T10:00:00Z"
}
```

## GET /api/macro/snapshot

**Params** : Aucun  
**Response** :
```json
{
  "asof_date": "2025-10-31",
  "zscores": {
    "GRW": 1.2,
    "INF": -0.5,
    "POL": 0.8,
    "USD": -1.1,
    "CMD": 0.3
  },
  "components": {
    "GDP": 2.1,
    "CPI": 2.5,
    "Yield10Y": 4.2,
    "VIX": 18.5,
    "OilPrice": 75.0
  },
  "source": "FRED/indicators",
  "created_at": "2025-10-31T12:00:00Z",
  "hash": "abcd1234..."
}
```

## GET /api/stocks/indicators

**Params** : `ticker` (string, required), `start` (date, optional), `end` (date, optional)  
**Response** :
```json
{
  "ticker": "AAPL",
  "price": [
    {"t": "2025-10-01", "v": 150.0},
    {"t": "2025-10-02", "v": 152.5}
  ],
  "sma": [
    {"t": "2025-10-01", "v": 149.5},
    {"t": "2025-10-02", "v": 151.0}
  ],
  "rsi": [
    {"t": "2025-10-01", "v": 65.0},
    {"t": "2025-10-02", "v": 68.0}
  ],
  "macd": [
    {"t": "2025-10-01", "v": 1.2},
    {"t": "2025-10-02", "v": 1.5}
  ],
  "bb": {
    "upper": [
      {"t": "2025-10-01", "v": 155.0},
      {"t": "2025-10-02", "v": 157.5}
    ],
    "lower": [
      {"t": "2025-10-01", "v": 145.0},
      {"t": "2025-10-02", "v": 147.5}
    ]
  },
  "asof_date": "2025-10-31",
  "source": "yfinance/indicators",
  "hash": "efgh5678..."
}
```

## GET /api/news/feed

**Params** : `ticker` (string, optional), `start` (date, optional), `end` (date, optional), `q` (string, optional), `page` (int, default 1), `limit` (int, default 50)  
**Response** : Array of news items
```json
[
  {
    "id": "news123",
    "ticker": "AAPL",
    "title": "Apple annonce nouveau produit",
    "text": "Contenu détaillé...",
    "url": "https://example.com/news123",
    "source": "Reuters",
    "published_at": "2025-10-31T09:00:00Z",
    "sentiment": 0.8
  }
]
```

## GET /api/news/features/daily

**Params** : `ticker` (string, required), `start` (date, optional), `end` (date, optional)  
**Response** : Array of daily features
```json
[
  {
    "ticker": "AAPL",
    "date": "2025-10-31",
    "news_count": 15,
    "sent_mean": 0.6,
    "novelty": 0.4,
    "tier1_share": 0.7,
    "impact_proxy_mean": 0.5
  }
]
```

## GET /api/brief

**Params** : `period` (daily|weekly, required), `universe` (comma-separated tickers, optional)  
**Response** :
```json
{
  "period": "weekly",
  "top_signals": [
    {"ticker": "NVDA", "score": 85, "notes": ["macro:+", "tech:+", "news:+"]}
  ],
  "top_risks": [
    {"ticker": "TSLA", "score": 25, "notes": ["tech:-", "news:-"]}
  ],
  "picks": [
    {"ticker": "AAPL", "score": 78, "notes": ["macro:+", "tech:+"]}
  ],
  "rationale": [
    "Macro : Inflation stabilisée, USD faible.",
    "Tech : Momentum positif sur IA.",
    "News : Annonces positives sur semi-conducteurs."
  ],
  "source": "compose(macro,tech,news)",
  "asof_date": "2025-10-31",
  "hash": "ijkl9012..."
}
```

## POST /api/rag/search

**Body** : `{"q": "string", "ticker"?: "string", "start"?: "date", "end"?: "date", "k"?: 8}`  
**Response** :
```json
{
  "query": "Impact de l'IA sur Apple",
  "docs": [
    {
      "text": "Apple investit massivement en IA...",
      "source": "news/article123",
      "published_at": "2025-10-30T10:00:00Z"
    }
  ]
}
```

## GET /api/freshness (optionnel, à implémenter)

**Params** : Aucun  
**Response** :
```json
{
  "news": {"max_dt": "2025-10-31", "volume": 5000},
  "macro": {"max_dt": "2025-10-31", "volume": 100},
  "prices": {"max_dt": "2025-10-31", "volume": 2000}
}
```
