# Audit Pertinence Agents (OpenClaw / Codex-only)

Date: 2026-02-26

Update applique (pruning):
- Retrait des roles always-on `po` et `scrum_master` du topology + template workboard.
- Les responsabilites scope/value + flow/WIP sont absorbees par `planner`.

## Objectif
Rendre l'orchestration **plus utile, moins bruyante**, en gardant uniquement les agents qui ont un **mandat non-redondant** et un **ROI** mesurable. Les autres agents doivent passer en **on-demand** (lances manuels) ou etre **retirees** du dispositif (cron + workboard).

## Sources (repo)
- Catalogue agents: `docs/orchestrator-ops/openclaw-agent-catalog.json`
- Topology roles: `docs/orchestrator-ops/parallel-role-topology.json`
- Cron map snapshot: `docs/orchestrator-ops/parallel-role-cron-map.json`
- Workboard: `docs/orchestrator-ops/parallel-workstreams.json`
- Queue: `docs/orchestrator-ops/priority-queue.json`

## Snapshot Factuel (au moment de l'audit)
- Queue:
  - `BATCH-01` = `PASS`
  - `BATCH-02` = `READY`
- Workboard (taches non `DONE`):
  - `BATCH-02-PLAN` (planner) = `IN_PROGRESS`
  - `BATCH-02-INFRA` (infra_engineer) = `READY`
  - `BATCH-02-BACKEND` (backend_engineer) = `READY`
  - `BATCH-02-FRONTEND` (frontend_engineer) = `READY`
  - `BATCH-02-TEST_PLAN` (tester) = `WAITING_DEP`
  - `BATCH-02-INTEGRATION` (integrator) = `WAITING_DEP`
  - `BATCH-02-QA_EXEC` (qa) = `WAITING_DEP`
  - `BATCH-02-SENTINEL_CHECK` (clawsentinel) = `WAITING_DEP`

## Signal d'activite (traces role-runner)
Les fichiers `logs-codex-runs/role-runner/*.live.log` montrent que certains roles tournent beaucoup sans pouvoir debloquer le flux quand ils sont en `WAITING_DEP` (bruit/cout).

Extrait (nombre de `final_output` dans les logs):
- `planner`: 63
- `dev`: 53
- `backend_engineer`: 42
- `frontend_engineer`: 35
- `tester`: 32
- `analyst`: 31
- `architect`: 28
- `qa`: 27
- `integrator`: 23
- `data_analyst`: 21
- `infra_engineer`: 21
- `clawsentinel`: 14
Note: les compteurs ci-dessus incluaient l'ancien dispositif avant pruning; `po` et `scrum_master` sont retires des loops et ne doivent plus etre provisionnes.

## Critere "Garder vs Eliminer"
Un agent reste "always-on" si:
- il a un mandat unique (pas duplicable proprement par un autre role),
- il debloque directement le flux (code, tests, integration, runtime),
- il a un declencheur clair et frequent (READY/IN_PROGRESS) avec deltas concrets.

Un agent passe en on-demand / est supprime si:
- son mandat est deja couvert (planner/admin-agents/qa),
- il tourne surtout en `WAITING_DEP` (donc bruit/cout),
- il introduit de la ceremonie sans impact sur la livraison.

## Decision Par Agent

### Admins (garder)
- `adminapp-codex` (KEEP / always-on)
  - Mandat: stabilite runtime (cron/tmux/locks/recovery).
  - Non redondant.
- `admin-agents` (KEEP / always-on)
  - Mandat: detection deterministic_issue + routage owner/scope + next_action actionnable.
  - Non redondant.

### Delivery core (garder always-on)
- `planner` (KEEP / always-on)
  - Mandat: dispatch / priorisation / regles de conformite vision.
  - Couvre aussi une bonne partie de `po` + `scrum_master` si on les retire.
- `backend_engineer` (KEEP / always-on tant que BATCH-02 BACKEND est READY)
  - Mandat: implementation API.
- `frontend_engineer` (KEEP / always-on tant que BATCH-02 FRONTEND est READY)
  - Mandat: implementation UI.
- `infra_engineer` (KEEP / always-on tant que BATCH-02 INFRA est READY)
  - Mandat: CI/CD, plumbing, perf, runtime app.
- `integrator` (KEEP / always-on)
  - Mandat: integration cross-role + reduction duplications (reutiliser modules/UI/API existants).
- `tester` (KEEP / always-on)
  - Mandat: tests automatiques + checks reproductibles.
- `qa` (KEEP / always-on)
  - Mandat: gate final + preuve.

### Specialists (passer en on-demand)
- `analyst` (ON-DEMAND)
  - Valeur: clarifier hypotheses/edge-cases au debut d'un nouveau batch.
  - Raison: cadence continue inutile hors "nouvelle spec" ou incident.
- `architect` (ON-DEMAND)
  - Valeur: contraintes architecture anti-derive (naming, patterns, boundaries).
  - Raison: utile par jalons, pas en boucle.
- `data_analyst` (ON-DEMAND)
  - Valeur: data quality, metrics, verifs sur donnees.
  - Raison: utile quand une tache data/forecasting est READY, pas en continu.
- `clawsentinel` (ON-DEMAND ou cadence tres basse)
  - Valeur: checks anti-derive / hygiene / risques.
  - Raison: grande partie absorbable par `qa` + `admin-agents` (gate + detection) si on veut reduire le nombre d'agents.

### Candidats elimination (retirer du cron + retirer du workboard template)
- `po` (REMOVE de l'execution continue)
  - Overlap: `planner` (vision/dispatch) + owner humain (vrai PO).
  - Remplacement: ajouter au `planner` un bloc "scope/value decision" quand un batch passe en READY.
- `scrum_master` (REMOVE de l'execution continue)
  - Overlap: `admin-agents` (WIP, blocages, routing) + `planner` (cadence/dispatch).
  - Remplacement: `admin-agents` publie un mini etat WIP + blocages, sans ceremonie.

### Cas particulier
- `dev` (ON-DEMAND, ou supprimer si vous voulez "specialists only")
  - Aujourd'hui, le trio `backend_engineer` + `frontend_engineer` + `integrator` couvre l'essentiel.
  - Garder `dev` seulement si vous avez beaucoup de taches "glue" (scripts/docs/refactors) qui ne rentrent pas bien dans backend/frontend/infra.

## Portfolio Recommande
Si l'objectif est "moins d'agents, meme qualite":
- Always-on: `adminapp-codex`, `admin-agents`, `planner`, `backend_engineer`, `frontend_engineer`, `infra_engineer`, `integrator`, `tester`, `qa`
- On-demand: `analyst`, `architect`, `data_analyst`, `clawsentinel`, `dev`
- Retire: `po`, `scrum_master`

## Etapes de Decommission (safe)
1. Desactiver les crons: `po`, `scrum_master` (et optionnellement `clawsentinel`, `analyst`, `architect`, `data_analyst`, `dev`).
2. (DONE 2026-02-26) Mettre a jour le template workboard pour ne plus creer de taches `PO_REVIEW` et `SCRUM_REVIEW` sur les nouveaux batches (remplace par `GOV_REVIEW` dans la lane `planner`).
3. Mettre a jour `docs/ops/AGENT_ROLE_INTEGRATION_MODEL.md` pour supprimer ces roles et deplacer leurs responsabilites vers `planner` + `admin-agents`.
4. Conserver les definitions d'agents en catalogue en mode on-demand (sauf si suppression totale desiree).
