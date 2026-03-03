# Pre-Reactivation Acceleration Plan

Updated: 2026-03-02
Scope: préparer l'exécution des batches core sans réactiver immédiatement tous les agents.

## 1) Objectif

Prendre de l'avance sur la préparation opérationnelle pour que la réactivation se fasse avec:
- moins de token burn,
- moins de boucles inutiles,
- moins de blocages de coordination.

## 2) Work Packages avant réactivation complète

### `PR-01` — Readiness Gate unique (P0)
Owner: planner  
Output:
- checklist binaire `PASS/BLOCKED` sur runtime + API + workboard.
- blocker explicite par item en échec.
Done criteria:
- aucun item ambigu.
- un seul `NEXT_ACTION_UNIQUE`.

### `PR-02` — Runbook incident standardisé (P0)
Owner: admin  
Output:
- procédures courtes: `rate_limit`, `provider_down`, `stale_lock`, `chromium_loop`, `cron_empty`.
- commande de recovery par incident + rollback.
Done criteria:
- toutes les procédures testables en moins de 10 min.

### `PR-03` — Dispatch cards low-context (P0)
Owner: planner  
Output:
- cartes de mission par lane canonique (`planner`, `dev`, `admin`).
- scope in/out strict + preuves attendues.
Done criteria:
- chaque rôle a une mission unique par tick.

### `PR-04` — Contract guard hardening (P1)
Owner: qa + planner  
Output:
- règles anti `signal_unparseable`, `STALE_READY_ACTION`, `task_update` invalide.
Done criteria:
- transitions d'état invalides bloquées côté contrat.

### `PR-05` — Preload mémoire par rôle (P1)
Owner: planner  
Output:
- profil mémoire appliqué par rôle (coordination, delivery, analysis).
- budget contexte max par tick documenté.
Done criteria:
- pas de chargement MEMORY.md dans sessions rôles.

### `PR-06` — Batch sequencing pack (P0)
Owner: planner  
Output:
- ordre strict d'ouverture: BATCH-11 -> BATCH-12 -> BATCH-13 -> BATCH-14.
- critères pour autoriser le batch suivant.
Done criteria:
- aucun chevauchement inter-batch non justifié.

## 3) Gate avant canary reactivation

Tous les points ci-dessous doivent être `PASS`:
1. Locks stales = 0.
2. Workboard lock sain (pas de lock orphelin).
3. Core API endpoints disponibles: `health`, `brief/daily`, `forecasts`, `copilot/ask`.
4. Charge machine stable (pas de boucle Chromium active).
5. Crontab cohérente avec profil canary (pas de jobs legacy concurrents).
6. OpenClaw jobs parallèles non essentiels désactivés.
7. Dispatch cards prêtes pour les rôles canary.

## 4) Reactivation sequence recommandée

### Phase A — Canary (durée cible: 60-90 min)
- Activer `planner` + `dev` uniquement.
- Objectif: ouvrir et lancer `BATCH-11` sans bruit orchestration.
- Stop condition:
  - 2 cycles consécutifs sans blocker P0,
  - contract parsing stable.

### Phase B — Extended canary (durée cible: 60 min)
- Ajouter `admin`.
- Objectif: verrouiller santé runtime + evidence quality pendant `BATCH-11`.

### Phase C — Full core lanes
- Conserver les 3 lanes lean (`planner/dev/admin`) et augmenter le débit task-level.
- Objectif: exécuter `BATCH-12` puis préparer `BATCH-13` sans réintroduire de lanes legacy.

## 5) Priorités concrètes de dispatch (J0/J1)

1. `BATCH-11-BACKEND` (ingestion + freshness contract)
2. `BATCH-11-INFRA` (ingestion health + alert hooks)
3. `BATCH-11-DATA` (SLO 24h + drift)
4. `BATCH-11-PLAN` (gate close)
5. `BATCH-12-BACKEND` (portfolio persistence)
6. `BATCH-12-FRONTEND` (portfolio editor)

## 6) Kill switches

Suspendre la montée en charge si:
- `signal_unparseable` dépasse le seuil de fenêtre glissante (`fc_health_check`, section quality window),
- latence copilot dépasse le seuil contractuel pendant 2 cycles,
- load average remonte de façon durable après réactivation.

## 7) Definition of done globale pré-réactivation

- Plan de dispatch prêt pour 2 batches d'avance.
- Runbooks incident prêts.
- Rôles et mémoire configurés pour limiter les boucles/token burn.
- Réactivation possible sans bricolage manuel ad hoc.
