# FRONTEND_DATA_DEBUG.md — Protocole pour débloquer les pages avec vraies données

Ce guide décrit exactement comment un agent peut diagnostiquer et corriger une page frontend bloquée (chargement infini, données vides) en s’assurant que l’API renvoie des données réelles.

---

## 1. Redémarrage propre

```bash
cd /Users/venom/Documents/analyse-financiere
./finance-copilot.sh stop
./finance-copilot.sh start
```

- Frontend : `cd copilot-app/frontend/webapp && pnpm dev`
- Debug panel (VITE_APP_DEBUG=1) doit être actif pour afficher les erreurs réseau/runtime.

---

## 2. Vérification rapide des endpoints clés

```bash
# Santé
curl -s http://127.0.0.1:8050/api/health | jq

# Macro FRED (30 points sur 2 séries)
curl -s "http://127.0.0.1:8050/api/macro/series?ids=CPIAUCSL,UNRATE&limit=30" | jq '.data.series[0].points[:5]'

# Screener (Top 5 trié par momentum 30j)
curl -s "http://127.0.0.1:8050/api/stocks/screener?page=1&page_size=5&sort=momentum_30d" | jq '.data.items'

# Métadonnées (Donut/Heatmap)
curl -s "http://127.0.0.1:8050/api/stocks/meta?tickers=SPY,QQQ,AAPL" | jq

# Univers suivi
curl -s http://127.0.0.1:8050/api/stocks/universe | jq
```

Si l’une de ces requêtes échoue, corriger l’endpoint dans `copilot-app/backend/src/api/main.py`.

---

## 3. Diagnostic UI systématique

1. Ouvrir la page (`/macro`, `/stocks`, etc.).
2. DevTools navigateur → onglets **Console** & **Network** :
   - Identifier les requêtes `/api/...` KO (statut, payload).
   - Noter l’URL exacte pour reproduire avec `curl`.
3. Observer le panel “DEV DEBUG” (en bas à droite) : il liste immédiatement les erreurs (timeout, 4xx/5xx).

---

## 4. Corriger côté backend

1. Pour chaque endpoint vide, localiser la fonction (généralement dans `src/api/main.py`).
2. Utiliser les helpers :
   - `get_fred_series` (macro), `get_price_history` + `_compute_stock_metrics` (stocks).
   - `DEFAULT_STOCKS_UNIVERSE` (surveillez env `STOCKS_UNIVERSE`).
3. Jamais de mock : si la source manque, lancer les jobs (news/forecasts/brief) ou enrichir la récupération.
4. `tail -f copilot-app/backend/api.log` pour voir les erreurs runtime.

---

## 5. Corriger les hooks frontend

1. Chercher les appels API :
   ```bash
   rg -n "/api/macro/series" src
   rg -n "/api/stocks/screener" src
   ```
2. Vérifier que chaque hook (`useMacroSeries`, `useStocksScreener`, `useStocksMeta`, etc.) :
   - utilise `api.fetchJson` via `client.ts`,
   - parse `json.data` correctement,
   - emploie `placeholderData: keepPreviousData` (React Query v5),
   - gère les erreurs (`query.error` dans les composants).

---

## 6. Tests finaux (CLI)

```bash
curl -s "http://127.0.0.1:8050/api/macro/series?ids=CPIAUCSL&limit=5" | jq '.data.series[0].points'
curl -s "http://127.0.0.1:8050/api/stocks/screener?page=1&page_size=10" | jq '.data.total'
```

Capture UI :
```bash
cd copilot-app/frontend/webapp
npx playwright screenshot --browser chromium --viewport-size 1920,1080 \
  "http://localhost:5173/stocks" \
  "/Users/venom/Documents/analyse-financiere/proofs/stocks.png"
```

---

## 7. Commit & scoreboard

1. `git status` → vérifier les fichiers modifiés (backend + hooks/front).
2. Preuve (curl + screenshot) → joindre au commit/PR.
3. Mettre à jour `SCORE_AGENTS.md` + votre fichier personnel (`PSEUDO-...md`).
4. Commit avec message clair :  
   `feat(stocks): screener uses live metrics`

---

En appliquant ce protocole à chaque page en “chargement infini” ou “vides”, on élimine les données mockées et on livre une UI professionnelle branchée sur les vraies sources.
