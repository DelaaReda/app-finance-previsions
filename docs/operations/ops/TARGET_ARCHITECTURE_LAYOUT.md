# Target Architecture Layout

Repository target (actuel)

- `apps/api/src` → backend runtime (domaines, services, API routes, orchestration locale)
- `apps/web/src` → frontend statique (domaines UI)
- `apps/api/runtime` → runtime mutable (data, cache, launcher)
- `docs/*` → documentation, plans, règles d’exécution
- `packages/*` → artefacts packageables/partagés (contrats, SDK, kits UI)
- `platform/*` → configuration, automation, policy
- `tests/*` → tests cross-cutting + fixtures
- `evidence/*` → preuves d’exécution/gates/snapshots

Contrainte de navigation

- `apps/api/src` et `apps/web/src` sont les seules racines applicatives à modifier.
- Les aliases `data` / `cache` sont des compatibilités vers `apps/api/runtime/*`.
- `finance-copilot.sh` reste l’entrée opératoire principale.

Règles de découpage

- backend: `/api/*` = orchestrateurs légers, business dans `domains/*` et `services/*`
- frontend: `/domains/*` = composants métier + pages; `/platform/*` = client/infra front
- ops: `platform/automation`, `platform/policies`, `platform/config`

Points de vérité

- Contrat API: `docs/ops/API_ENDPOINT_BEST_PRACTICES.md`
- Réutilisation: `docs/ops/REUSE_MODULES_CATALOG.md`
- Gates: `scripts/run_delivery_gate.sh` et `platform/policies/*`
