# BATCHES 11-14 — Core Completion Execution Spec

Updated: 2026-03-02
Owner: planner (dispatch), avec exécution multi-rôles.

Objectif global:
Compléter les briques core encore manquantes pour passer d'un MVP fonctionnel à un copilot exploitable au quotidien, mesurable, et robuste en mode nominal comme dégradé.

## BATCH-11 — Data Ingestion Core + Freshness SLO

Outcome attendu:
Les décisions ne reposent plus sur des flux fragiles; la fraîcheur et la santé des sources sont visibles et actionnables.

Epics:
- E11.1 Ingestion multi-sources robuste.
- E11.2 Freshness contract v1 transversal.
- E11.3 Health and alerting opérationnel.

Tâches:
- `B11-T1` (`backend_engineer`) — Refactor adapters ingestion + fallback provider.
  Deliverable: normalisation unique des payloads prix/news/macro avec champs de fraîcheur.
  Done: `schema_validation_pass_rate=100%` sur endpoints core.
- `B11-T2` (`data_analyst`) — SLO fraîcheur 24h.
  Deliverable: calcul `age_seconds` + rapport cycles <= 10 min.
  Done: `freshness_sla_cycles_le_10m >= 90%`.
- `B11-T3` (`infra_engineer`) — `GET /api/ingestion/health`.
  Deliverable: statut par source (`ok/degraded/down`, `last_success_at`, `error_count`).
  Done: incident ingestion détecté et visible en moins de 2 minutes.
- `B11-T4` (`qa`) — Tests de panne provider.
  Deliverable: preuve mode dégradé structuré.
  Done: aucune erreur 500 silencieuse en panne partielle.
- `B11-T5` (`planner`) — Gate batch.
  Deliverable: verdict PASS/BLOCKED avec preuve SLO.

Gate evidence obligatoire:
- `INGESTION_HEALTH_PROOF`
- `FRESHNESS_SLO_PROOF`
- `DEGRADED_MODE_PROOF`

## BATCH-12 — Portfolio State + Risk Profile Core

Outcome attendu:
Le copilot répond sur le vrai contexte portefeuille utilisateur, sans friction de resaisie.

Epics:
- E12.1 Persistance portefeuille et watchlist.
- E12.2 Profil risque/horizon exploitable côté décision.
- E12.3 UX édition/récupération fiable.

Tâches:
- `B12-T1` (`backend_engineer`) — CRUD portfolio profile.
  Deliverable: endpoints `POST/GET/PUT` avec validation stricte.
  Done: save/load < 1 seconde sur environnement local.
- `B12-T2` (`frontend_engineer`) — UI portefeuille.
  Deliverable: édition positions, poids, horizon, conviction.
  Done: parcours complet en 3 étapes max sans erreur bloquante.
- `B12-T3` (`backend_engineer`) — Injection auto portfolio dans `copilot/ask`.
  Deliverable: contexte portfolio utilisé par défaut.
  Done: recommandation cohérente sans resaisie manuelle.
- `B12-T4` (`qa`) — Résilience données corrompues/incomplètes.
  Deliverable: fallback et message utilisateur explicite.
  Done: 0 crash sur cas de corruption légère.
- `B12-T5` (`planner`) — Validation flux end-to-end.
  Deliverable: preuve portefeuille -> copilot -> UI.

Gate evidence obligatoire:
- `PORTFOLIO_PERSISTENCE_PROOF`
- `COPILOT_CONTEXT_INJECTION_PROOF`
- `DEGRADED_RECOVERY_PROOF`

## BATCH-13 — Decision Journal + Outcome Feedback Loop

Outcome attendu:
Chaque recommandation devient traçable et évaluable, avec boucle d'amélioration continue.

Epics:
- E13.1 Journal des décisions.
- E13.2 Calcul outcomes et calibration.
- E13.3 Revue hebdo orientée action.

Tâches:
- `B13-T1` (`backend_engineer`) — Decision journal store.
  Deliverable: stockage immutable (timestamp, contexte, verdict, confidence, horizon).
  Done: >= 95% des réponses copilot journalisées.
- `B13-T2` (`data_analyst`) — Outcome evaluator.
  Deliverable: hit rate + calibration error 1d/1w/1m.
  Done: métriques reproductibles sur dataset de validation.
- `B13-T3` (`frontend_engineer`) — UI historique 7 jours.
  Deliverable: filtres horizon/asset, synthèse gains/pertes.
  Done: consultation claire en moins de 15 secondes.
- `B13-T4` (`qa`) — Vérification cohérence journal <-> outcomes.
  Deliverable: test d'intégrité des liens décision-résultat.
  Done: mismatch critique = 0.
- `B13-T5` (`planner`) — Boucle backlog hebdo.
  Deliverable: top améliorations priorisées selon métriques.

Gate evidence obligatoire:
- `DECISION_LOG_PROOF`
- `OUTCOME_METRICS_PROOF`
- `WEEKLY_REVIEW_UI_PROOF`

## BATCH-14 — Finalisation Core v2: Robustness Drills + GO/NO-GO

Outcome attendu:
Le système est prêt à un usage quotidien intensif avec plan de récupération clair.

Epics:
- E14.1 Drills de robustesse.
- E14.2 Validation clickpath nominal/degraded.
- E14.3 Gate final opérationnel.

Tâches:
- `B14-T1` (`qa`) — Drills de panne.
  Deliverable: tests provider down, stale data, timeout, restart.
  Done: blockers classifiés avec impact et action.
- `B14-T2` (`infra_engineer`) — Rollback and recovery.
  Deliverable: script recovery/rollback chronométré.
  Done: restauration fonctionnelle en moins de 10 minutes.
- `B14-T3` (`frontend_engineer`) — UX dégradée lisible.
  Deliverable: parcours 2-3 clics conservé en nominal + message dégradé explicite.
  Done: 0 blocage utilisateur silencieux.
- `B14-T4` (`tester`) — Non-regression suite.
  Deliverable: smoke suite prioritaire sur flux décision.
  Done: pass rate cible >= 95%.
- `B14-T5` (`planner`) — Gate GO/NO-GO.
  Deliverable: artefact final signé + plan monitoring J+7.
  Done: `critical_blockers_open=0` ou verdict `NO-GO` explicite.

Gate evidence obligatoire:
- `ROBUSTNESS_DRILLS_PROOF`
- `ROLLBACK_DRILL_PROOF`
- `FINAL_GATE_SIGNOFF`

## Priorité d'exécution recommandée

1. `BATCH-11` (fiabilité données d'abord)
2. `BATCH-12` (contexte portefeuille réel)
3. `BATCH-13` (mesure et boucle d'apprentissage)
4. `BATCH-14` (finalisation opérationnelle)

## Règles anti-blocage

- Aucun batch ne passe `CLOSED` sans preuves listées dans `evidence_required`.
- Toute dégradation doit être visible côté API et côté UI (pas de silence).
- Si un blocker P0/P1 persiste plus de 1 cycle, le planner publie un plan de contournement explicite.
