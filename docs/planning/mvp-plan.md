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

## 10) Delta de pilotage (cycle cron en cours)

- Priorité immédiate: verrouiller d’abord **A1/A2** pour figer le contrat backend consommé par B1.
- Lot de dispatch recommandé (qwen):
  1. `planner` — cadrage T-A1.1 + T-A2.1 (DoR explicite)
  2. `dev` — implémentation backend ciblée
  3. `tester` — tests contrat + smoke endpoint
  4. `qa` — vérification des preuves et verdict PASS/BLOCKED
- Gate de sortie du lot: aucun 500 sur health/stocks + tests dédiés verts + artefacts déposés.

## 11) Batch d'exécution qwen (delta incrémental)

### Batch-01 (à lancer maintenant)
- **Objectif**: verrouiller le contrat backend minimal pour débloquer l’intégration UI.
- **Contenu**: `T-A1.1` + `T-A2.1`
- **Sortie attendue (obligatoire)**:
  - DELTA (fichiers + comportement)
  - EVIDENCE (commandes + sorties utiles)
  - RISKS (risques résiduels)
  - NEXT (prochaine action unique)
- **Gate PASS Batch-01**:
  - `/api/health` conforme + test dédié vert
  - `/api/stocks/prices?ticker=SPY` conforme
  - artefacts déposés dans `finance-app/openclaw-gates/`

#### Prompt opératoire Batch-01 (qwen)
```text
Objectif: livrer T-A1.1 et T-A2.1 sans élargir le scope.
In-scope: normalisation contrat /api/health et /api/stocks/prices (mono ticker).
Out-of-scope: multi-ticker, news, forecasts, copilot ask, refactor global.
Pré-requis: backend local up, tests backend exécutables.
Fichiers cibles: main.py + tests ciblés uniquement.
Plan: implémenter -> tester -> produire preuves.
Acceptation testable:
1) GET /api/health = 200, ok=true, data.timestamp présent
2) pytest tests/test_health.py vert
3) GET /api/stocks/prices?ticker=SPY = 200, clés ticker/points/count/timestamp présentes
4) aucun 500 sur 5 appels successifs stocks mono
Commandes de test:
- curl health
- pytest test_health.py
- curl stocks mono
- boucle 5x curl stocks mono
Évidences attendues:
- extraits JSON health/stocks
- sortie pytest
- verdict final PASS|BLOCKED + raison
Format réponse: DELTA / EVIDENCE / RISKS / NEXT
```

### Batch-02 (conditionnel)
- **Précondition**: Batch-01 PASS
- **Contenu**: `T-A2.2` + préparation `T-A3.1`
- **Objectif**: figer contrat multi-tickers et ouvrir la normalisation news

## 12) Delta d’exécution immédiat (cycle 20:20)

### Batch-01 — paquet de dispatch verrouillé
- **Objectif unique**: fermer `T-A1.1` + `T-A2.1` avec verdict QA auditable.
- **Scope IN**: health contract + stocks mono ticker contract.
- **Scope OUT**: multi-ticker (`T-A2.2`), news, forecasts, copilot ask, UI.
- **Commande dispatch recommandée**:

```bash
python3 scripts/qwen_orchestrator.py \
  --agent-bin qwen \
  --rounds 2 \
  --with-manager \
  --with-architect \
  --feature "Batch-01 MVP: livrer T-A1.1 + T-A2.1; produire DELTA/EVIDENCE/RISKS/NEXT + VERDICT; déposer artefact finance-app/openclaw-gates/batch-01-<timestamp>.md"
```

### Gate de sortie renforcé (anti-faux PASS)
Le batch est **PASS** seulement si les 4 conditions sont vraies:
1. `pytest tests/test_health.py` vert
2. `GET /api/health` conforme (`ok=true`, `data.timestamp`)
3. `GET /api/stocks/prices?ticker=SPY` conforme (`ticker/points/count/timestamp`)
4. artefact gate présent avec sections complètes + verdict explicite

### Pré-activation Batch-02 (si PASS)
- Ouvrir `T-A2.2` + préparation `T-A3.1` en conservant le même format de preuve.
- Si une condition échoue: statut `BLOCKED`, pas de démarrage Batch-02.

## 13) Delta exécution lot suivant (cycle 20:35)

### Brief d’exécution verrouillé — Batch-01 (run immédiat)
- **Owner qwen/manager**: faire exécuter `T-A1.1` puis `T-A2.1` dans le même run.
- **Gate d’entrée**:
  1. Backend up (`/api/health` répond)
  2. Branche propre sur le scope backend MVP
- **Gate de sortie (PASS)**:
  1. Preuves commandes incluses (health + pytest + stocks mono + boucle stabilité)
  2. Artefact présent: `finance-app/openclaw-gates/batch-01-<timestamp>.md`
  3. Verdict QA explicite: `PASS`
- **Gate de blocage (BLOCKED)**:
  - test non exécuté, section evidence manquante, ou contrat JSON incomplet

### Carte Batch-02 (pré-remplie, conditionnelle)
- **Activation**: uniquement après PASS Batch-01
- **Contenu**: `T-A2.2` (multi ticker contract tests) + `T-A3.1` (normalisation news feed)
- **Objectif**: étendre le contrat backend sans ouvrir le frontend
- **Règle de scope**: aucune implémentation UI tant que Gate G-A n’est pas confirmé

## 14) Delta lancement & continuité (cycle 20:50)

### Packet de lancement Batch-01 (final)
- **Commande recommandée**:

```bash
python3 scripts/qwen_orchestrator.py \
  --agent-bin qwen \
  --rounds 2 \
  --with-manager \
  --with-architect \
  --feature "Batch-01 MVP final: exécuter T-A1.1 + T-A2.1, produire DELTA/EVIDENCE/RISKS/NEXT/VERDICT, déposer finance-app/openclaw-gates/batch-01-<timestamp>.md"
```

- **Critères QA de validation (obligatoires)**:
  1. `pytest tests/test_health.py` vert
  2. 3 appels health consécutifs cohérents
  3. 5 appels stocks SPY sans 500 avec clés attendues
  4. artefact gate horodaté + `VERDICT: PASS|BLOCKED`

### Règle d’escalade explicite
- Si un seul critère échoue: verdict immédiat `BLOCKED`, correction ciblée, puis relance Batch-01 (pas d’ouverture Batch-02).

### Carte Batch-02 (prête mais verrouillée)
- **Activation stricte**: uniquement si artefact Batch-01 contient `VERDICT: PASS` signé QA.
- **Contenu**: `T-A2.2` + `T-A3.1`
- **Sortie attendue**: mêmes sections de preuve, plus impact sur contrat backend documenté.

## Changelog
- 2026-02-24 19:46 America/New_York — Ajout du delta de pilotage MVP: priorisation du lot A1/A2 et séquence de dispatch qwen avec gate de sortie.
- 2026-02-24 19:50 America/New_York — Ajout du plan de lots qwen Batch-01/Batch-02 avec critères PASS explicites et artefacts attendus.
- 2026-02-24 20:05 America/New_York — Ajout d’un prompt opératoire Batch-01 prêt à injecter aux agents qwen, avec scope strict, critères testables et format de preuves obligatoire.
- 2026-02-24 20:20 America/New_York — Verrouillage du paquet de dispatch Batch-01 (commande orchestrator prête), gate PASS durci en 4 conditions et règle de pré-activation stricte pour Batch-02.
- 2026-02-24 20:35 America/New_York — Ajout d’un brief d’exécution Batch-01 prêt à l’emploi (gates entrée/sortie/blocage) et d’une carte Batch-02 pré-remplie strictement conditionnelle au verdict PASS QA.
- 2026-02-24 20:50 America/New_York — Finalisation du packet de lancement Batch-01 (commande, QA gate, escalade BLOCKED) et verrou formel d’activation Batch-02 sur PASS QA.
