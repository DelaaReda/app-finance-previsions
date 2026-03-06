# BATCH-27 — Frontend Dynamic Data Coverage (Facettes + Widgets) [ARCH]

## Objectif (alignement vision)
- Assurer une couverture "data dynamique" côté UI pour les facettes et widgets, pilotée par des contrats API stables, afin de réduire les écrans `UNKNOWN/NO_DATA` et accélérer l’itération produit.

## Périmètre
- Frontend (apps/web): normalisation des états `loading/empty/error/no_data` + instrumentation.
- API (apps/api): contrats de payload cohérents (champs obligatoires, valeurs par défaut) pour éviter les états transitoires.
- Orchestration: preuves et gates d’acceptance (ce document + artefacts de complétion).

## Décisions d’architecture
1) Contrat “Coverage” (UI)
   - Chaque widget/facette expose un état standardisé: `HAS_DATA | EMPTY_OK | NO_DATA | ERROR`.
   - L’affichage `NO_DATA` est réservé aux cas contractuels (pas aux trous de mapping).

2) Normalisation de payload (API)
   - Définir des defaults côté API pour les champs utilisés en UI (ex: listes -> `[]`, compteurs -> `0`).
   - Éviter les `null` ambigus dans les DTO publics; préférer des formes explicites et documentées.

3) Observabilité minimale
   - Event/UI telemetry: `widget_render_state` (state, widget_id, route, correlation_id).
   - Côté API: `contract_normalization_applied` (endpoint, fields_filled_count).

## Tracks d’implémentation (handoff dev attendu)
- Track FE: factoriser un helper de rendu “coverage state” + appliquer aux widgets/facettes priorisés.
- Track API: compléter la normalisation des payloads sur endpoints touchés par les widgets/facettes.
- Track QA: gate d’acceptance sur 3 écrans clés (1 vide légitime, 1 data présente, 1 erreur).

## Réutilisation / intégration
- Réutiliser les composants d’état déjà existants (spinner/empty/error) et les aligner sur le contrat “Coverage”.
- Réutiliser les domaines existants `apps/api/src/domains/*` sans créer de chemins legacy.

## Acceptance gate (DONE)
- 0 occurrence de `UNKNOWN/NO_DATA` due à mapping incomplet sur le set de routes ciblées.
- Contrats API: champs requis non absents (defaults appliqués) et test snapshot/contract validé.
- Preuves: 1 artefact FE (captures/logs) + 1 artefact API (exemple payload normalisé) référencés dans la tâche de complétion.

## Architecture audit (zones impactées)
- apps/web: widgets + facettes (components/pages correspondant aux routes priorisées).
- apps/api: endpoints et DTOs des domaines consommés par ces widgets/facettes.

