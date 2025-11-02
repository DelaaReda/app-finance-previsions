# ARCHITECTURE (aperçu)

```
apps/                # UI/flows (macro, stock, briefs)
core/                # market_data, config, utils
ingestion/           # news pipeline (RSS), sources
research/            # nlp_enrich, RAG (à implémenter), scoring
utils/               # st_compat, helpers
runners/             # scripts/tests d'intégration
tests/               # unit + integration
```

**Flux clé**
1. Ingestion macro/prix/news → normalisation + métadonnées (date/source/ticker)
2. Scoring par pilier → score composite (40/40/20 par défaut)
3. RAG → indexation news (12–24m) + séries (≥5 ans)
4. UI/Briefs → vues, graphes, citations, export HTML/MD

**Points d’extension**
- `research/rag_store.py` (embeddings/index)
- `research/scoring.py` (combinaisons/pondérations)
- `alerts/` (règles + notifications)

**Observabilité**
- `@trace_call` autour des I/O (FRED, yfinance, RSS)
- Logs structurés (loguru intégré)

**Tests**
- Unit par défaut
- Intégration réseau opt-in (`AF_ALLOW_INTERNET=1`)
