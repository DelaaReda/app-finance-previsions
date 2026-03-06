# BATCH-27 — ANALYSIS (complété) — 2026-03-05

Constat clé
- Les symptômes "UNKNOWN/NO_DATA" viennent le plus souvent d’une normalisation incomplète (payloads partiels → contrat implicite).

Hypothèses à valider côté dev
- Chaque facette/widget a une source de vérité unique (API endpoint / hook / store) et un mapping stable.
- Les états UI doivent distinguer: `loading` vs `empty` vs `error` (pas de fallback silencieux).

Critères d’implémentation (à appliquer partout)
- Normaliser les payloads à l’entrée (adapter unique) et refuser les champs obligatoires manquants (error/empty explicite).
- Instrumenter les "no data" avec une cause (ex: `missing_field:<name>`), pas une valeur générique.

Livrables attendus (preuves)
- Une liste facettes/widgets couverts (nom + source données + état empty/error attendu).
- 2 tests de non-régression minimum (1 facette, 1 widget) couvrant données réelles/fixture + empty.

Handoff implicite
- Les tâches DEV-01/02/03 appliquent ces règles et produisent la preuve de couverture.

