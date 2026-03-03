# Role Dispatch Low-Context Pack (BATCH-11 to BATCH-14)

Updated: 2026-03-02
Purpose: réduire le contexte inutile et augmenter le débit utile par tick.

## 1) Règles communes (tous les rôles)

- Une seule mission active par tick.
- Pas de reread massif: lire uniquement les fichiers listés dans la carte.
- Réponse contrat strict 8 clés:
  - `STATUS`
  - `DELTA`
  - `EVIDENCE`
  - `RISKS`
  - `NEXT`
  - `VERDICT`
  - `BLOCKER_ID`
  - `NEXT_ACTION_UNIQUE`
- Si blocage > 1 cycle: proposer contournement concret, pas juste un constat.

## 2) Memory profile par rôle

### `planner`
- Profile: coordination
- Context max: 900 tokens
- Inputs:
  - priority queue item courant
  - workstream batch courant
  - dernier contrat de chaque rôle actif
- Exclusions:
  - MEMORY.md complet
  - historique chat long

### `backend_engineer`
- Profile: delivery
- Context max: 750 tokens
- Inputs:
  - task card backend active
  - contrat API ciblé
  - dernier blocker backend

### `frontend_engineer`
- Profile: delivery
- Context max: 750 tokens
- Inputs:
  - task card frontend active
  - contrat UI/API cible
  - preuve UX attendue

### `data_analyst`
- Profile: analysis
- Context max: 850 tokens
- Inputs:
  - task card data active
  - schema/métriques batch
  - dernier rapport qualité

### `qa`
- Profile: coordination
- Context max: 800 tokens
- Inputs:
  - success criteria batch
  - evidence_required batch
  - derniers deltas des rôles delivery

### `infra_engineer`
- Profile: delivery
- Context max: 700 tokens
- Inputs:
  - task card infra active
  - runbook incident ciblé
  - état runtime minimal

## 3) Dispatch cards prêtes (ordre recommandé)

## Card `D11-BE`
Role: `backend_engineer`  
Task: `BATCH-11-BACKEND`  
Goal: ingestion robuste + freshness contract v1  
Must prove:
- `INGESTION_HEALTH_PROOF`
- `FRESHNESS_SLO_PROOF` (partie contrat)

## Card `D11-INF`
Role: `infra_engineer`  
Task: `BATCH-11-INFRA`  
Goal: endpoint health et signaux d'incident  
Must prove:
- `INGESTION_HEALTH_PROOF`

## Card `D11-DA`
Role: `data_analyst`  
Task: `BATCH-11-DATA`  
Goal: mesure SLO fraîcheur 24h  
Must prove:
- `FRESHNESS_SLO_PROOF`

## Card `D11-PLAN`
Role: `planner`  
Task: `BATCH-11-PLAN`  
Goal: décider PASS/BLOCKED avec blocker explicite  
Must prove:
- `VERDICT: PASS` ou `BLOCKED + reason`

## Card `D12-BE`
Role: `backend_engineer`  
Task: `BATCH-12-BACKEND`  
Goal: CRUD portefeuille + profil risque  
Must prove:
- `PORTFOLIO_PERSISTENCE_PROOF`

## Card `D12-FE`
Role: `frontend_engineer`  
Task: `BATCH-12-FRONTEND`  
Goal: UI édition portefeuille en <= 3 étapes  
Must prove:
- `API_UI_PROOF`

## Card `D12-QA`
Role: `qa`  
Task: `BATCH-12-QA`  
Goal: robustesse corruption légère  
Must prove:
- `DEGRADED_RECOVERY_PROOF`

## 4) Anti-loop protections

- Si même `BLOCKER_ID` revient 2 cycles:
  - le rôle ne répète pas l'analyse;
  - il propose 1 workaround exécutable immédiatement.
- Si `NEXT_ACTION_UNIQUE` est identique 2 cycles:
  - marquer `VERDICT=GO_WITH_CAUTION` + action alternative.
- Si aucune preuve nouvelle:
  - `STATUS=WAITING` interdit; passer `BLOCKED` avec cause technique.

## 5) Cadence recommandée

- Tick roles de delivery: toutes les 20-30 min.
- Tick planner/qa: toutes les 30-40 min.
- Cooldown forcé si erreur rate limit ou parser noise.
