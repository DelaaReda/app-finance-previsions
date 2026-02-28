# App Src Unification

Voir aussi le guide agent centralisé :
[`docs/architecture/AGENT_ONBOARDING.md`](AGENT_ONBOARDING.md)

Objectif: garantir une arborescence unique et exploitable par humain/agent.

## Canonical root

- `apps/`

## Canonical application roots

- `apps/api/src` (backend)
- `apps/web/src` (frontend)
- `apps/api/runtime` (assets runtime: `data`, `cache`, launcher)

## Legacy compatibility

- `data` et `cache` à la racine du repo pointent vers `apps/api/runtime/*`.
- `apps/api/src/data` et `apps/api/src/cache` pointent vers `apps/api/runtime/*`.
- Les anciens chemins `copilot-app/...` sont conservés uniquement dans l’historique.

## Règle de développement

- Créer/modifier uniquement sous `apps/api/src/**` ou `apps/web/src/**` pour la logique produit.
- Les changements opérationnels (jobs, crons, gates, config) vont dans `platform/*` ou `docs/orchestrator-ops/*`.
- Aucun module applicatif majeur ne doit être créé hors de `apps/`.

Project documentation can stay outside this app tree (for example in repository-level `docs/`).
