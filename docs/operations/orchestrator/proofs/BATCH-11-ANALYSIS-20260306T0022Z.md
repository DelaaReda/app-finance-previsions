# BATCH-11 — Data Ingestion Core + Freshness SLO [ANALYSIS]

## Problème
La chaîne ingestion → API → UI ne garantit pas une freshness mesurable ni des contrats stables, ce qui produit des états transitoires (`UNKNOWN/NO_DATA`) et des écarts de SLO.

## Objectifs (SLO/qualité)
- Définir un SLO freshness (seuil + métrique) et rendre la mesure disponible.
- Stabiliser les contrats API: champs freshness présents + defaults appliqués.
- Réduire les cas de `NO_DATA` non contractuels (mapping/normalisation).

## Architecture audit (paths impactés)
- API/runtime: `apps/api/runtime/` (normalisation payload/erreurs, headers/correlation)
- API/domaines: `apps/api/src/domains/*` (DTO/contrats, endpoints ingestion)
- Web: `apps/web/src` (affichage freshness/erreurs/stale)
- Orchestration: `platform/automation/` (preuves/gates; pas de logique produit)

## Hypothèses / risques
- Données historiques: backfill minimal nécessaire pour valider SLO.
- Idempotence ingestion: éviter doublons lors des retries.

## Stratégie (single batch, intra-batch sequencing)
1) Backend/API: contrat freshness (timestamp/status) + defaults + exemples payload.
2) Data/Ingestion: pipeline idempotent + métriques freshness; backfill minimal.
3) Observabilité: métriques + alerting basique + corrélation req_id.
4) UI: affichage stale/ok + erreurs actionnables (si requis par produit).

## Acceptance gate
- Une métrique freshness existe et le seuil SLO est documenté.
- Payload exemple prouve présence des champs freshness + defaults.
- Preuves: payload + capture métrique + scénario UI (ok/stale/erreur).

## Dépendances
- Uniquement intra-batch (pas de dépendances top-level inter-batch).

