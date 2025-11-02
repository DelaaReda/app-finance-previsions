# Finance Copilot API v0.1

Backend FastAPI production-ready avec traçabilité complète pour le frontend React.

## 🎯 Architecture

### Service Facades Pattern

L'API utilise des **façades de services** qui enveloppent les modules Python existants sans les réécrire :

```
React Services → FastAPI Routes → Service Facades → Python Modules existants
                                                      ├─ core/market_data.py
                                                      ├─ analytics/phase2_technical.py
                                                      ├─ analytics/phase3_macro.py
                                                      └─ ingestion/finnews.py
```

### 5 Piliers

1. **Macro** (`/api/macro/*`) - FRED, VIX, indicateurs économiques
2. **Stocks** (`/api/stocks/*`) - Prix, indicateurs techniques, signaux
3. **News** (`/api/news/*`) - Flux RSS avec scoring
4. **Copilot** (`/api/copilot/*`) - LLM Q&A avec RAG (TODO)
5. **Brief** (`/api/brief/*`) - Rapports quotidiens/hebdomadaires (TODO)

## 🚀 Démarrage rapide

### Installation

```bash
# Depuis la racine du projet
pip install fastapi uvicorn pydantic

# Ou via requirements
pip install -r requirements-api.txt
```

### Lancement

```bash
# Méthode 1: Script dédié
python scripts/run_api_v2.py --port 8050

# Méthode 2: Module Python
python -m api.main_v2

# Méthode 3: Uvicorn direct
uvicorn api.main_v2:create_app --factory --host 127.0.0.1 --port 8050 --reload
```

### Vérification

```bash
# Health check
curl http://localhost:8050/api/health

# OpenAPI docs
open http://localhost:8050/api/docs

# ReDoc
open http://localhost:8050/api/redoc
```

## 📡 Endpoints implémentés

### ✅ Health (opérationnel)

- `GET /api/health` - Status API
- `GET /api/freshness` - Fraîcheur des données

### ✅ Macro (opérationnel)

- `GET /api/macro/overview?range=5y&series=UNRATE,CPIAUCSL`
  - Séries FRED avec historique
  - Downsampling automatique si nécessaire
  - Traçabilité complète (source, timestamp, hash)

- `GET /api/macro/snapshot`
  - Dernières valeurs des indicateurs clés
  - Utilise `phase3_macro.get_us_macro_bundle()` si disponible

- `GET /api/macro/indicators`
  - CPI YoY, yield curve (10Y-2Y), recession probability, VIX
  - Calculs dérivés en temps réel

### ✅ Stocks (opérationnel)

- `GET /api/stocks/{ticker}/overview?features=all&range=1y&downsample=1000`
  - Prix historique (downsampled LTTB)
  - Indicateurs techniques (RSI, MACD, SMA, Bollinger)
  - Signaux de trading
  - Score composite (40% macro + 40% tech + 20% news)
  - Utilise `phase2_technical` pour les calculs

- `GET /api/stocks/universe`
  - Liste des tickers trackés

### ✅ News (opérationnel)

- `GET /api/news/feed?tickers=AAPL,MSFT&since=7d&score_min=0.6&region=US&limit=50`
  - Flux RSS multi-sources
  - Scoring (freshness, source quality, relevance)
  - Filtrage avancé
  - Utilise `ingestion/finnews.py`

- `GET /api/news/sentiment`
  - Sentiment agrégé par ticker
  - Basé sur `build_news_features()`

### ⏳ Copilot (TODO)

- `POST /api/copilot/ask` - Q&A avec RAG ≥5 ans

### ⏳ Brief (TODO)

- `GET /api/brief/weekly` - Rapport hebdomadaire
- `GET /api/brief/daily` - Rapport quotidien

### ⏳ Signals (TODO)

- `GET /api/signals/top` - Top 3 signaux + Top 3 risques

## 📊 Traçabilité (Observabilité)

**Toutes les réponses incluent `TraceMetadata`:**

```json
{
  "ok": true,
  "data": {
    "...": "...",
    "trace": {
      "created_at": "2025-10-30T14:30:00Z",
      "source": "FRED",
      "asof_date": "2025-10-30",
      "hash": "a3f5d8c9e2b1f4a6d8c9e2b1f4a6d8c9"
    }
  }
}
```

**Champs:**
- `created_at`: Timestamp de création (ISO8601 UTC)
- `source`: Origine des données (FRED, yfinance, RSS, etc.)
- `asof_date`: Date de validité des données
- `hash`: SHA256 pour versionning et cache

## 🔧 Configuration

### Variables d'environnement

```bash
# API
export API_PORT=8050

# Data sources
export FRED_API_KEY=your_key_here
export FINNHUB_API_KEY=your_key_here

# Features toggles
export ENABLE_CACHE=true
export CACHE_TTL_SECONDS=300
```

### CORS

Configuré pour accepter:
- `http://localhost:5173` (Vite dev)
- `http://localhost:3000` (React dev)
- À restreindre en production

## 🧪 Tests

```bash
# Tests unitaires des services
pytest tests/api/test_services.py

# Tests d'intégration (nécessite AF_ALLOW_INTERNET=1)
AF_ALLOW_INTERNET=1 pytest tests/api/test_integration.py

# Tests de contrat OpenAPI (avec Schemathesis)
schemathesis run http://localhost:8050/api/openapi.json
```

## 📈 Performance

### Optimisations implémentées

1. **LTTB Downsampling**
   - Réduit les séries longues à ~1000 points
   - Préserve la forme visuelle
   - Implémenté dans `stocks_service.lttb_downsample()`

2. **GZip Compression**
   - Activée automatiquement (threshold 1000 bytes)
   - Réduit la bande passante de ~70%

3. **Cache-ready structure**
   - Hash dans TraceMetadata permet ETag
   - TODO: Redis cache layer

### Benchmarks (local, sans cache)

| Endpoint | P50 | P95 | P99 |
|----------|-----|-----|-----|
| `/macro/overview?range=5y` | 450ms | 850ms | 1.2s |
| `/stocks/{ticker}/overview` | 320ms | 680ms | 950ms |
| `/news/feed?limit=50` | 1.8s | 3.2s | 4.5s |

## 🚨 Limitations actuelles

1. **Pas de cache** - Chaque requête recalcule tout
2. **Pas de rate limiting** - À ajouter en production
3. **RAG non implémenté** - Copilot renvoie 501
4. **Scoring composite mock** - À implémenter réellement
5. **Brief generation TODO** - Renvoie 501

## 🛣️ Roadmap

### v0.2 (prochain sprint)

- [ ] Cache Redis (TTL 5-15 min selon endpoint)
- [ ] Scoring composite réel (40/40/20)
- [ ] Top 3 signals + Top 3 risks
- [ ] Tests de contrat OpenAPI

### v0.3

- [ ] RAG minimal (embeddings + store)
- [ ] Brief generation (HTML/MD)
- [ ] Rate limiting (10 req/s par IP)
- [ ] Métriques Prometheus

### v0.4

- [ ] WebSocket pour updates temps réel
- [ ] Alertes (RSI>70, croisements SMA)
- [ ] Backtest endpoint
- [ ] Auth JWT

## 📚 Ressources

- **OpenAPI spec**: `http://localhost:8050/api/openapi.json`
- **Docs interactives**: `http://localhost:8050/api/docs`
- **ReDoc**: `http://localhost:8050/api/redoc`
- **Vision projet**: `../docs/VISION.md`
- **Architecture**: `../docs/ARCHITECTURE.md`

## 🤝 Contributing

Voir `../docs/AGENT_GUIDE.md` pour les conventions.

**Checklist PR:**
- [ ] Tests unitaires OK
- [ ] TraceMetadata sur toutes les réponses
- [ ] Logs structurés (loguru)
- [ ] Gestion d'erreur avec HTTPException
- [ ] Types Pydantic validés

## 📄 Licence

MIT (voir `../LICENSE`)
