# Rapport Intervention Admin-Claude — 2026-02-28 (après-midi)

## 🎯 Ce qui a été accompli aujourd'hui

### ✅ FAIT (intervention admin)

| Fix | Impact | Status |
|-----|--------|--------|
| Cron path corrigé | Agents auto-recovery opérationnel | ✅ |
| 56 → 5 processus zombies tués | CPU/RAM libérés | ✅ |
| BATCH-03 créé + workboard jusqu'à BATCH-07 | Planner débloqué | ✅ |
| PRODUCT_VISION.md créé | Vision claire pour agents | ✅ |
| apiConnector.js créé + corrigé | Bridge API↔UI fonctionnel | ✅ |
| `ta` package installé | Endpoint top-movers débloqué | ✅ |
| Stock % change calculé depuis historique | Vrais chiffres (+41.8% NVDA etc.) | ✅ |
| Event dispatch vers applyLiveDashboardData | UI reçoit les données live | ✅ |

---

## 📊 État actuel du système

### Backend (port 8050) — ✅ UP
- 460+ news réelles (MarketWatch, RSS)
- 20 forecasts générés (SPY 54%, QQQ 50%, etc.)
- 6 tickers de prix avec historique 1 an
- Backtests actifs (hit_rate: 56.5%, 23 trades)
- Refresh toutes les ~75 min (cron openclaw)

### Frontend (port 5173) — ✅ UP
- apiConnector.js charge les données live au démarrage
- window.newsItems peuplé avec vraies news
- window.liveForecasts peuplé (20 forecasts)
- window.topMovers avec vrais % de changement
- Auto-refresh toutes les 2 min
- Badge LIVE vert visible

---

## ⚠️ Problèmes restants (pour BATCH-03 agents)

### P0 — Forecasts confidence bloquée à 50-55%
**Cause:** `forecasts_simple.py` utilise `change_percent=0.0` du `/api/stocks/top` endpoint pour calculer la confiance. Résultat: tout tombe dans la plage 45-55%.  
**Fix:** backend_engineer doit passer le calcul de confiance depuis l'historique de prix (déjà dispo dans `/api/stocks/prices`).  
**Fichier:** `apps/api/src/platform/legacy/jobs/forecasts_simple.py` lignes 85-120

### P1 — Stocks top movers change_percent=0.0 dans /api/stocks/top  
**Cause:** `/api/stocks/top` ne calcule pas les % de changement (renvoie 0.0)  
**Fix:** Calculer depuis l'historique dans le endpoint stocks/top ou ajouter calcul dans forecasts_simple  
**Fichier:** backend, endpoint `/api/stocks/top`

### P2 — Seulement 6 tickers de prix (SPY, QQQ, AAPL, NVDA, MSFT, GOOGL)
**Vision:** couvrir or (GLD), argent (SLV), Tesla (TSLA), énergie (XLE), BTC  
**Fix:** Ajouter ces tickers dans la liste de fetch stocks

### P3 — Multi-IA Judge non implémenté
**Vision:** au moins 2 modèles analysent + 1 juge tranche  
**Status:** endpoint `/api/judge` existe, retourne des verdicts. Vérifier si c'est 1 ou N modèles.

---

## 🗺️ Roadmap BATCH-04 → BATCH-07 (pour le planner)

**BATCH-04:** Brief quotidien intelligent + secteurs réels  
**BATCH-05:** Copilot "Que faire aujourd'hui ?" (input portefeuille → recommandation)  
**BATCH-06:** Forecasts multi-assets couvrant tous les actifs vision + Judge IA  
**BATCH-07:** Deep dive asset + news intelligence avec scoring importance

---

## 💡 Instruction pour le planner

À chaque run, lire en priorité:
1. `docs/product/planning/PRODUCT_VISION.md` — vision
2. `docs/product/planning/WORKSTATE.md` — état actuel
3. `docs/operations/orchestrator/priority-queue.json` — queue actuelle

Le BATCH-03 est IN_PROGRESS. Monitorer la livraison des rôles et ouvrir BATCH-04 quand les success criteria sont atteints.
