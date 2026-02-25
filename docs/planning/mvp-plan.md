# Plan MVP Exécution (Finance Copilot) — 2026-02-24

## 1) Constat rapide du repo

- **Backend actif**: `copilot-app/backend/src/api/main.py` (routes MVP présentes)
- **Frontend actif**: `copilot-app/frontend/app/` (statique, beaucoup de logique mock dans `app.js`/`mockData.js`)
- **Run local**: `./finance-copilot.sh restart`
- **Socle tests actuel**: `copilot-app/backend/tests/*`, smoke script `scripts/smoke.sh`
- **Risque principal**: contrat API/UI non stabilisé (formes de payload variables + fallback silencieux)

## 2) Objectif MVP (reconfirmé)

Livrer un MVP local **fiable, démontrable, et exécutable par agents qwen** sur 5 endpoints:
- `GET /api/health`
- `GET /api/stocks/prices`
- `GET /api/news/feed`
- `GET /api/forecasts`
- `POST /api/copilot/ask`

avec UI statique consommant ces endpoints sans crash.

## 3) Découpage exécutable en Epics

1. **EPIC A — Stabilisation contrat API MVP**
   - Normaliser les payloads et erreurs sur les 5 endpoints.
   - Ajouter tests API ciblés et checks de non-régression.
2. **EPIC B — Intégration frontend MVP sans dépendance mock cachée**
   - Brancher les vues MVP sur API réelle.
   - Afficher explicitement les fallbacks simulés.
3. **EPIC C — Quality gate & orchestration qwen**
   - Pipeline d’exécution standardisé (DoR/DoD, preuves, runbook, gating).

## 4) Séquencement recommandé (agents qwen)

### Vague 1 (jour 1)
- A1. Contrats API (`/health`, `/stocks/prices`, `/news/feed`, `/copilot/ask`)
- A2. Consolidation `/forecasts` via router unique
- C1. Smoke gate minimal reproductible

### Vague 2 (jour 2)
- B1. Wiring UI KPI/News/Forecasts sur API
- B2. Badges fallback simulé + états vide/erreur
- C2. Ajout gate backend/frontend compact et artefacts de preuve

### Vague 3 (jour 3)
- C3. Stabilisation exécution multi-agents qwen (prompts, rôles, runbook)
- Durcissement final + revue des écarts ouverts

## 5) Definition of Ready (DoR) pour toute story

- Objectif business explicite
- In/Out scope explicite
- Fichiers cibles listés
- Commandes de test prévues
- Dépendances identifiées

## 6) Definition of Done (DoD)

- Code/doc modifié
- Tests/commandes exécutés avec sortie vérifiable
- Résultat visible (endpoint/UI)
- Risques résiduels documentés
- Rollback simple défini

## 7) Commandes de validation transverses (référence)

```bash
# 1. Démarrage local
./finance-copilot.sh restart

# 2. Santé API
curl -sS http://localhost:8050/api/health | jq

# 3. Endpoints MVP
curl -sS "http://localhost:8050/api/stocks/prices?ticker=SPY" | jq
curl -sS "http://localhost:8050/api/news/feed?limit=5" | jq
curl -sS "http://localhost:8050/api/forecasts" | jq
curl -sS -X POST "http://localhost:8050/api/copilot/ask" \
  -H 'Content-Type: application/json' \
  -d '{"question":"Résumé marché US","max_sources":3}' | jq

# 4. Tests backend ciblés
cd copilot-app/backend
.venv/bin/pytest -q tests/test_health.py tests/test_ticker_normalization.py

# 5. Smoke existant
cd /home/venom/analyse-financiere
./scripts/smoke.sh
```

## 8) Critères de succès MVP (gates)

- 5/5 endpoints MVP répondent sans 500 sur smoke
- Contrat minimal des payloads documenté et testé
- UI MVP charge les données API (ou fallback explicite « Données simulées »)
- Rapport de preuve exécutable archivé dans `finance-app/openclaw-gates/`

## 9) Plan de rollback

- Rollback applicatif: `git revert <commit>` sur lot story
- Rollback runtime: redémarrage clean via `./finance-copilot.sh restart`
- Rollback data: conserver snapshots existants `copilot-app/backend/data/*.json` (pas de suppression destructive)
