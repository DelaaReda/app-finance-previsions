---
status: historical
last_verified: 2026-03-07
superseded_by:
  - /home/venom/analyse-financiere/docs/product/planning/README.md
  - /home/venom/analyse-financiere/docs/product/planning/BACKEND_FIRST_PRODUCT_BACKLOG.md
---

# Plan MVP Exécution (Finance Copilot) — 2026-02-24

Historical note:
- This file captures an older MVP execution plan.
- It remains useful as background only.
- Do not treat it as the current backlog or architecture source of truth.

## 1) Constat rapide du repo

- **Backend actif**: `apps/api/src/domains/judge/api/main.py` (routes MVP présentes)
- **Frontend actif**: `apps/web/src/domains/*/pages/` (statique, beaucoup de logique mock dans pages)
- **Run local**: `./finance-copilot.sh restart`
- **Socle tests actuel**: `apps/api/tests/*`, smoke script `scripts/smoke.sh`
- **Risque principal**: contrat API/UI non stabilisé (formes de payload variables + fallback silencieux)

## Orchestration (source normative)

- Spec: `docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml`
- Schéma EVIDENCE: `docs/ops/ROLE_CONTRACT_EVIDENCE_SCHEMA.md`

## 2) Objectif MVP (reconfirmé)

Livrer un MVP local **fiable, démontrable, et exécutable par agents codex (OpenClaw)** sur 5 endpoints:
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
3. **EPIC C — Quality gate & orchestration (codex/OpenClaw)**
   - Pipeline d’exécution standardisé (DoR/DoD, preuves, runbook, gating).

## 4) Séquencement recommandé (agents codex/OpenClaw)

### Vague 1 (jour 1)
- A1. Contrats API (`/health`, `/stocks/prices`, `/news/feed`, `/copilot/ask`)
- A2. Consolidation `/forecasts` via router unique
- C1. Smoke gate minimal reproductible

### Vague 2 (jour 2)
- B1. Wiring UI KPI/News/Forecasts sur API
- B2. Badges fallback simulé + états vide/erreur
- C2. Ajout gate backend/frontend compact et artefacts de preuve

### Vague 3 (jour 3)
- C3. Stabilisation exécution multi-agents codex (rôles, runbook, preuves)
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
cd apps/api
([ -x .venv/bin/pytest ] || (python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)) && \
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
- Lot de dispatch recommandé (codex/OpenClaw):
  1. `planner` — cadrage T-A1.1 + T-A2.1 (DoR explicite)
  2. `dev` — implémentation backend ciblée
  3. `tester` — tests contrat + smoke endpoint
  4. `qa` — vérification des preuves et verdict PASS/BLOCKED
- Gate de sortie du lot: aucun 500 sur health/stocks + tests dédiés verts + artefacts déposés.

## 11) Exécution par batch (codex/OpenClaw)

Règle: pas d’orchestrateur legacy. La boucle d’exécution est pilotée par OpenClaw (`cron_tmux_role_runner.sh`) et les gates (`preflight_dispatch`, `validate_roles_sequential`, `run_delivery_gate`).

### Runbook (pour un `<BATCH-ID>`)

1. Préflight (bloquant sur états invalides):

```bash
bash scripts/preflight_dispatch.sh
```

2. Exécution séquentielle stricte (core chain):

```bash
SEQUENTIAL_VALIDATE_TIMEOUT_SECONDS=480000 \
  bash scripts/validate_roles_sequential.sh \
    --roles planner,dev,tester,qa \
    --strict-ready-chain \
    --chain-target "<BATCH-ID>"
```

3. Artefact de preuve (obligatoire) + gate:

```bash
# Exemple: finance-app/openclaw-gates/batch-03-20260226-2359.md
bash scripts/run_delivery_gate.sh "finance-app/openclaw-gates/batch-<NN>-<timestamp>.md"
```

Artefact requis: sections `DELTA`, `EVIDENCE`, `RISKS`, `NEXT`, `VERDICT`, `BLOCKER_ID`, `NEXT_ACTION_UNIQUE`.

### Brief opératoire (template)

```text
Objectif: livrer le batch sans élargir le scope.
In-scope: uniquement les tasks du batch courant.
Out-of-scope: tout refactor global non requis par le batch.
Pré-requis: backend local up (si pertinent), tests exécutables.
Plan: implémenter -> tester -> produire preuves -> QA verdict.
Format sortie (contrat): STATUS / DELTA / EVIDENCE / RISKS / NEXT / VERDICT / BLOCKER_ID / NEXT_ACTION_UNIQUE
EVIDENCE (kv): task_update=...;lock_check=ok;stream_id=<BATCH-ID>;task_id=<...>;cmd=...;tests_run=...
```

## Changelog
- 2026-02-24 19:46 America/New_York — Ajout du delta de pilotage MVP: priorisation du lot A1/A2 et séquence de dispatch avec gate de sortie.
- 2026-02-24 19:50 America/New_York — Ajout du plan de lots Batch-01/Batch-02 avec critères PASS explicites et artefacts attendus.
- 2026-02-24 20:05 America/New_York — Ajout d’un brief opératoire Batch-01 (scope strict, critères testables, format de preuves).
- 2026-02-24 20:20 America/New_York — Verrouillage du paquet de dispatch Batch-01, gate PASS durci et règle de pré-activation stricte pour Batch-02.
- 2026-02-24 20:35 America/New_York — Ajout d’un brief d’exécution Batch-01 (gates entrée/sortie/blocage) et d’une carte Batch-02 strictement conditionnelle au verdict PASS QA.
- 2026-02-24 20:50 America/New_York — Finalisation du packet de lancement Batch-01 (preuves + escalade BLOCKED) et verrou formel d’activation Batch-02 sur PASS QA.
- 2026-02-24 21:05 America/New_York — Ajout du delta de continuité/exécution: escalade explicite selon présence/absence d’artefact Batch-01, règle anti-dérive sur VERDICT obligatoire, et chemin séquentiel conditionnel vers Batch-02.
- 2026-02-24 22:05 America/New_York — Durcissement qualité doc cron: commandes de tests backend rendues auto-bootstrap (`python3 -m venv ...`) pour exécution reproductible sur VM neuve.
- 2026-02-26 14:10 America/New_York — Alignement complet sur orchestration codex-only/OpenClaw: suppression des commandes legacy et remplacement par `preflight_dispatch` + `validate_roles_sequential` + `run_delivery_gate`.
