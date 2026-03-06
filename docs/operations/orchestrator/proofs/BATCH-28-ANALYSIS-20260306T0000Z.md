# BATCH-28 — Frontend Dynamic UX Hardening (Freshness + Error States) [ANALYSIS]

## Problème
Les surfaces UI dynamiques ont des états d’erreur/vide/fraîcheur incohérents, ce qui crée des faux `NO_DATA`, des erreurs non actionnables, et des régressions de lisibilité.

## Objectifs mesurables
- Réduire les occurrences de `UNKNOWN/NO_DATA` dues à un mapping/contrat incomplet.
- Rendre la freshness visible et cohérente (ok/stale) sur les routes ciblées.
- Rendre les erreurs actionnables (retry/CTA) + telemetry minimale.

## Périmètre & audit (paths impactés)
- Frontend: `apps/web/src` (widgets/facettes, états UI partagés, telemetry)
- API/runtime: `apps/api/runtime/` (normalisation erreurs/payload)
- API/domaines: `apps/api/src/domains/*` (DTO/contrats consommés)
- Orchestration: `platform/automation/` (preuves/gates, pas de logique produit)

## Hypothèses / risques
- Les “erreurs colorées” doivent rester accessibles (contraste, fallback texte).
- Freshness peut être absente sur certains endpoints: prévoir defaults contractuels.

## Stratégie (single batch, intra-batch sequencing)
1) FE: contrat d’état standard (`loading/empty/error/no_data/freshness_stale`) + composants.
2) API: payload/erreurs normalisés pour supprimer ambiguïtés (null vs vide) côté UI.
3) QA: scénarios e2e + preuves (captures + payload + telemetry).

## Acceptance gate
- UI: états cohérents + freshness visible; erreurs actionnables; pas de `NO_DATA` transitif.
- API: contrats stables (champs/valeurs par défaut); exemples payload.
- Preuves: 1 capture UI + 1 payload + 1 event/metric de telemetry.

## Dépendances
- Uniquement intra-batch (pas de dépendances top-level inter-batch).

