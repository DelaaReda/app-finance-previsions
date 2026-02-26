# Orchestrator Ops — Experiments

## Changelog
- Initialized.

## 2026-02-24 22:55 ET — Expériences proposées

### EXP-01 — State-contract gate (queue/preflight)
- **Hypothèse:** un contrat d’états explicite supprime >80% des blocages préflight récurrents.
- **Plan:**
  1. Ajouter test de validation des états queue en CI locale.
  2. Exécuter sur 5 dispatchs consécutifs.
- **Success criteria:** 0 blocage `state_validation` sur 5 runs.
- **Owner role:** Scrum Master
- **Rollback:** désactiver le test bloquant (mode warning).

### EXP-02 — DoD completeness gate strict
- **Hypothèse:** la gate réduit les faux positifs DONE et le carry-over.
- **Plan:**
  1. Activer gate en warn-only (2 runs), puis enforce.
  2. Mesurer ratio `DONE validés / DONE déclarés`.
- **Success criteria:** ratio >= 0.9 après enforcement.
- **Owner role:** QA
- **Rollback:** retour warn-only.

### EXP-03 — Prompt budget par rôle
- **Hypothèse:** plafond de longueur réduit warnings `too_long` de 50% sans baisse qualité.
- **Plan:**
  1. Définir budget (ex: 900-1400 chars par rôle).
  2. Mesurer warnings et taux de reformulation sur 3 runs.
- **Success criteria:** warnings `too_long` <= 50% baseline, verdicts toujours exploitables.
- **Owner role:** Architect
- **Rollback:** augmenter budgets de 20-30%.

### EXP-04 — WIP limit Sprint P0=2
- **Hypothèse:** réduire WIP augmente throughput DONE hebdo.
- **Plan:** appliquer immédiatement sur sprint W09.
- **Success criteria:** >=1 story P0 DONE avant mi-sprint.
- **Owner role:** Product Owner
- **Rollback:** lever limite si dépendances externes bloquent toute capacité.