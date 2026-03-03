# DEV_AGENT_AUTONOMY_PROTOCOL

Objectif: rendre `dev` autonome, orienté livraison, aligné architecture, avec preuves QA exploitables.

## Cycle obligatoire par tick (dev)
- `context` lane dev puis `status` lane dev.
- Choisir 1 tâche: `IN_PROGRESS` prioritaire, sinon `READY`.
- Exécuter `claim -> root_cause -> patch minimal -> test ciblé -> complete/handoff`.
- Éviter créations inutiles: réutiliser modules/API/composants existants avant tout nouveau fichier.

## Evidence contract (dev)
- Champs obligatoires sur `claim`: `root_cause`, `architecture_check`, `vision_alignment`, `reuse_check`.
- Champs obligatoires sur `complete|handoff`: `root_cause`, `fix_applied`, `verify`, `reuse_check`, `architecture_check`, `vision_alignment`, `qa_proof`.
- `run_note` doit être un mini paragraphe (>= 5 mots).

## Architecture-first guardrails
- Valider la couche cible avant patch: `domain/application/api/platform`.
- Refuser imports cross-layer non justifiés.
- Référence de qualité d’intégration: pattern endpoint Judge (réutilisation clients/modules avant duplication).

## Monitoring parental (admin)
- Commande de contrôle: `bash scripts/dev_parent_monitor.sh --strict`.
- Si FAIL:
  - corriger prompt/spec/guard (pas de patch hasardeux),
  - relancer un tick dev avec scope limité,
  - vérifier preuve `qa_proof` + `tests_run` sur tâche close.

## KPI à suivre
- `failures_last_24h` dev = 0.
- `tick_markers contract/action` présents dans les logs tick récents.
- % tâches dev closes avec `qa_proof` non vide.
