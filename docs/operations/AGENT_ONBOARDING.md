# Agent Onboarding (Architecture & Delivery)

## Rôle de ce document

Ce document est la fiche de démarrage pour toute personne ou agent qui rejoint le projet.
Il vise à stabiliser :

- la structure d’architecture cible,
- les règles d’orchestration multi-agents,
- les sources de vérité opérationnelles et produit.

## Ordre de lecture recommandé

1. [`README.md`](../../README.md) pour la vue produit.
2. [`docs/architecture/ARCHITECTURE_MAP.md`](../architecture/ARCHITECTURE_MAP.md).
3. [`docs/architecture/ARCHITECTURE_STYLE_GUIDE.md`](../architecture/ARCHITECTURE_STYLE_GUIDE.md).
4. [`docs/architecture/TARGET_ARCHITECTURE_LAYOUT.md`](../architecture/TARGET_ARCHITECTURE_LAYOUT.md).
5. [`docs/ops/AGENT_WORKSPACE_INDEX.md`](../ops/AGENT_WORKSPACE_INDEX.md).
6. `docs/product/planning/*` pour les tâches actives (WORKSTATE → epics → stories → tasks).

## Commandes de base

- Validation workspace: `bash scripts/validate_agent_workspace_layout.sh`
- Vue d’état run/parallélisme: `python3 scripts/parallel_workstream.py status`
- Vérification rapide des plannings: `python3 scripts/parallel_workstream.py sync-priority`
- Contrôle orchestration: `openclaw cron list --all`

## Références opérationnelles obligatoires

- Config runtime modèle LLM : `platform/config/lm_used_model_config.sh`
- Contrats de coordination : `docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml`
- Source de vérité API : `docs/ops/API_ENDPOINTS.md`
- Playbook cron admin : `docs/ops/ADMIN_TEAM_CRON_PLAYBOOK.md`
- Baseline Codex : `docs/ops/ADMIN_CODEX_BASELINE.md`
- Coordination admin → livraison : `docs/ops/ADMIN_TEAM_CHAT.md`, `docs/ops/ADMIN_TEAM_ITERATIONS.md`, `docs/orchestrator-ops/agent-watchdog.md`

## Règles de stabilité documentaire

- Toute action de livraison doit respecter les conventions d’unicité de source (`source of truth`) déjà définies par doc.
- Pour les runbooks opérationnels, privilégier les docs dans `docs/ops` et éviter de réviser les archives historiques (`docs/operations/*` datées) sans note de version claire.
