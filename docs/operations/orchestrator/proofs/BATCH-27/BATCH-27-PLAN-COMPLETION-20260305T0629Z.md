# BATCH-27 — PLAN (complété) — 2026-03-05

Objectif
- Définir le plan de livraison pour "Frontend Dynamic Data Coverage (Facettes + Widgets)" (BATCH-27).

Portée (MVP)
- Facettes: données dynamiques (sources runtime), mapping stable (ids/labels), états (loading/empty/error).
- Widgets: mêmes garanties de couverture + cohérence d’affichage avec facettes.
- Contrats: normalisation payload (éviter UNKNOWN/NO_DATA par défaut silencieux), champs obligatoires documentés.

Découpage exécution (tracks)
- DEV-01: inventaire facettes/widgets + points d’entrée données (API/hooks) + fixtures réalistes.
- DEV-02: implémentation couverture facettes (données + rendu + erreurs).
- DEV-03: implémentation couverture widgets + harmonisation UI/états.
- ADMIN-01: gate de validation (preuves, captures, checks) + clôture stream.

Acceptance gate (definition of done)
- Au moins 1 test de non-régression sur facettes et 1 sur widgets (états loading/empty + données réelles/fixture).
- Aucun fallback implicite vers UNKNOWN/NO_DATA si la donnée attendue est absente: erreur/empty explicite.
- Preuve de couverture: capture/artefact listant facettes/widgets validés et la source de données.

Dépendances / ordre
- BATCH-27-ANALYSIS dépend de ce plan (PLAN → ANALYSIS → DEV-01 → DEV-02 → DEV-03 → ADMIN-01 → GOV_REVIEW).

