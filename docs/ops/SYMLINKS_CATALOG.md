# Catalogue des symlinks – Référence agents

**Date:** 2026-02-28  
**Objectif:** Documenter les symlinks pour éviter confusion et maintenir un chemin canonique dans le code/docs.

---

## Règle générale

**Chemin canonique** = utiliser celui-ci dans tout nouveau code et documentation.  
**Alias** = symlink conservé pour compatibilité, à ne pas privilégier pour les nouvelles références.

---

## Symlinks racine

| Alias (symlink) | Cible canonique | Usage |
|-----------------|-----------------|-------|
| `data` | `apps/api/runtime/data` | Données runtime (forecasts, news, etc.) |
| `cache` | `apps/api/runtime/cache` | Cache runtime |
| `runtime` | `apps/api/runtime` | Répertoire runtime global |

**Convention:** Dans les scripts et la doc, préférer `apps/api/runtime/` et sous-chemins.

---

## Mémoire / planning

| Alias | Cible canonique | Usage |
|-------|-----------------|-------|
| `memory/today.md` | `memory/YYYY-MM-DD.md` | Lien vers mémoire du jour |
| `memory/yesterday.md` | `memory/YYYY-MM-DD.md` | Lien vers mémoire veille |
| `docs/planning/*` | `docs/product/planning/*` | Accès court au planning |

---

## Gates et preuves

| Alias | Cible canonique | Usage |
|-------|-----------------|-------|
| `finance-app/openclaw-gates` | `evidence/gates/openclaw-gates` | Artefacts batch (batch-01, batch-02, etc.) |

**Canonique:** `evidence/gates/openclaw-gates/` — scripts (`preflight_dispatch`, `run_delivery_gate`) et nouvelle doc doivent l’utiliser. L’alias `finance-app/` reste pour compatibilité avec `tasks.md`, `priority-queue.json`, etc.

---

## Backend (apps/api/src)

| Alias | Cible canonique | Usage |
|-------|-----------------|-------|
| `apps/api/src/data` | `../runtime/data` | Données vues depuis le code |
| `apps/api/src/cache` | `../runtime/cache` | Cache vu depuis le code |
| `apps/api/src/tests` | `../tests` | Découverte pytest (tests dans `domains/*/tests/`) |
| `apps/api/src/.venv` | `../../../.venv` | Environnement virtuel |
| `apps/api/src/legacy-archive` | `archive/legacy/...` | Archive legacy |

---

## Documentation

| Alias | Cible canonique | Usage |
|-------|-----------------|-------|
| `docs/ops/AGENT_ONBOARDING.md` | `docs/operations/AGENT_ONBOARDING.md` | Onboarding architecture |
| `docs/ops/AGENTS_READY.md` | `docs/ops/AGENTS_READY.md` | État prêt agents (canonique) |
| `docs/ops/ORCHESTRATION_AGENTS_READY.md` | `docs/ops/ORCHESTRATION_AGENTS_READY.md` | Orchestration prêt agents (canonique) |
| `docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml` | `docs/ops/ops/ORCHESTRATION_COORDINATION_SPEC.yaml` | Spec orchestration |
| `docs/ops/ADMIN_TEAM_CHAT.md` | `docs/operations/ops/ADMIN_TEAM_CHAT.md` | Journal d'intention/admin ops |
| `docs/ops/ADMIN_TEAM_ITERATIONS.md` | `docs/operations/ops/ADMIN_TEAM_ITERATIONS.md` | Journal des itérations |
| `docs/ops/ADMIN_TEAM_CRON_PLAYBOOK.md` | `docs/operations/ops/ADMIN_TEAM_CRON_PLAYBOOK.md` | Playbook cron admin |
| `docs/ops/AGENT_ROLE_INTEGRATION_MODEL.md` | `docs/operations/ops/AGENT_ROLE_INTEGRATION_MODEL.md` | Modèle d'intégration rôles |
| `docs/ops/AGENT_TOOL_REQUESTS.md` | `docs/operations/ops/AGENT_TOOL_REQUESTS.md` | Requêtes outillage |
| `docs/ops/AGENT_WORKFLOW.md` | `docs/operations/ops/AGENT_WORKFLOW.md` | Workflow d'agents |
| `docs/ops/AGENT_MEMORY_POLICY.md` | `docs/operations/ops/AGENT_MEMORY_POLICY.md` | Politique mémoire |
| `docs/ops/ADMIN_CODEX_BASELINE.md` | `docs/operations/ops/ADMIN_CODEX_BASELINE.md` | Baseline admin |
| `docs/ops/ADMIN_EXECUTION_ISSUE_REPORTING.md` | `docs/operations/ops/ADMIN_EXECUTION_ISSUE_REPORTING.md` | Reporting incidents |
| `docs/ops/ADMIN_POST_RESTART_RUNBOOK.md` | `docs/operations/ops/ADMIN_POST_RESTART_RUNBOOK.md` | Reprise après redémarrage |
| `docs/ops/API_ENDPOINT_BEST_PRACTICES.md` | `docs/operations/ops/API_ENDPOINT_BEST_PRACTICES.md` | Contrat API |
| `docs/ops/APP_SRC_UNIFICATION.md` | `docs/operations/ops/APP_SRC_UNIFICATION.md` | Unification source |
| `docs/ops/ARCHITECTURE_MAP.md` | `docs/operations/ops/ARCHITECTURE_MAP.md` | Carte architecture |
| `docs/ops/ARCHITECTURE_STYLE_GUIDE.md` | `docs/operations/ops/ARCHITECTURE_STYLE_GUIDE.md` | Style architecture |
| `docs/ops/CLEANUP_LT100_REPORT.md` | `docs/operations/ops/CLEANUP_LT100_REPORT.md` | Rapport de nettoyage |
| `docs/ops/CODEX_RECOVERY_MONITORING_POST_MIGRATION.md` | `docs/operations/CODEX_RECOVERY_MONITORING_POST_MIGRATION.md` | Monitoring post-migration |
| `docs/ops/CRON_STRATEGY.md` | `docs/operations/ops/CRON_STRATEGY.md` | Stratégie cron |
| `docs/ops/DIRECTIVE_BUS.md` | `docs/operations/ops/DIRECTIVE_BUS.md` | Bus directives |
| `docs/ops/DIRECTIVE_BUS.jsonl` | `docs/operations/ops/DIRECTIVE_BUS.jsonl` | Bus directives (jsonl) |
| `docs/ops/DIRECT_CRON_METHODOLOGY.md` | `docs/operations/ops/DIRECT_CRON_METHODOLOGY.md` | Méthode cron |
| `docs/ops/ENGINEERING_PLAYBOOK.md` | `docs/operations/ops/ENGINEERING_PLAYBOOK.md` | Playbook engineering |
| `docs/ops/INCIDENT_TAXONOMY.md` | `docs/operations/ops/INCIDENT_TAXONOMY.md` | Taxonomie incidents |
| `docs/ops/INSPECTEUR_ADMIN_CHAT.md` | `docs/operations/INSPECTEUR_ADMIN_CHAT.md` | Rapport inspecteur |
| `docs/ops/INTEGRATION_APP_ENGINEER_RECOMMENDATIONS.md` | `docs/operations/ops/INTEGRATION_APP_ENGINEER_RECOMMENDATIONS.md` | Intégration app |
| `docs/ops/LARGE_MODULE_REUSE_INDEX.md` | `docs/operations/ops/LARGE_MODULE_REUSE_INDEX.md` | Index modules |
| `docs/ops/LEGACY_POLICY.md` | `docs/operations/ops/LEGACY_POLICY.md` | Politique legacy |
| `docs/ops/OPENCLAW_ADMIN_NOTES.md` | `docs/operations/ops/OPENCLAW_ADMIN_NOTES.md` | Notes openclaw admin |
| `docs/ops/OPENCLAW_CONFIG_LOCK.md` | `docs/operations/ops/OPENCLAW_CONFIG_LOCK.md` | Lock config openclaw |
| `docs/ops/OPERATIONAL_GOVERNANCE.md` | `docs/operations/ops/OPERATIONAL_GOVERNANCE.md` | Gouvernance opérationnelle |
| `docs/ops/PARALLEL_PLUMBING_QUICKSTART.md` | `docs/operations/ops/PARALLEL_PLUMBING_QUICKSTART.md` | Démarrage plomberie |
| `docs/ops/PARALLEL_SCRUM_DELIVERY_MODEL.md` | `docs/operations/ops/PARALLEL_SCRUM_DELIVERY_MODEL.md` | Modèle de livraison |
| `docs/ops/REUSE_MODULES_CATALOG.md` | `docs/operations/ops/REUSE_MODULES_CATALOG.md` | Réutilisabilité modules |
| `docs/ops/ROLE_CONTRACT_EVIDENCE_SCHEMA.md` | `docs/operations/ops/ROLE_CONTRACT_EVIDENCE_SCHEMA.md` | Schéma preuve rôle |
| `docs/ops/POST_MIGRATION_RECOVERY.md` | `docs/operations/POST_MIGRATION_RECOVERY.md` | Recovery post-migration |
| `docs/ops/MIGRATION_SUMMARY.md` | `docs/operations/MIGRATION_SUMMARY.md` | Résumé migration |
| `docs/ops/STABILISATION_POST_MIGRATION.md` | `docs/operations/STABILISATION_POST_MIGRATION.md` | Stabilisation post-migration |
| `docs/ops/STABLE_STATE_RUNBOOK.md` | `docs/operations/STABILISATION_POST_MIGRATION.md` | Alias historique (legacy) |
| `docs/ops/TARGET_ARCHITECTURE_LAYOUT.md` | `docs/operations/ops/TARGET_ARCHITECTURE_LAYOUT.md` | Layout cible |
| `docs/ops/TMUX_CRON_OPERATIONS.md` | `docs/operations/ops/TMUX_CRON_OPERATIONS.md` | Opérations tmux/cron |
| `docs/ops/VM_SLEEP_RESUME_GUARD.md` | `docs/operations/ops/VM_SLEEP_RESUME_GUARD.md` | Protection sommeil VM |
| `docs/ops/ADMIN_CODEX_BASELINE.md` | `docs/operations/ops/ADMIN_CODEX_BASELINE.md` | Baseline Codex |
| `docs/ops/API_ENDPOINT_BEST_PRACTICES.md` | `docs/operations/ops/API_ENDPOINT_BEST_PRACTICES.md` | Meilleures pratiques API |
| `docs/ops/QWEN_CLI_TMUX_INSPECTION.md` | `docs/operations/QWEN_CLI_TMUX_INSPECTION.md` | Guide legacy inspection |
| `docs/ops/QWEN_TMUX_ORCHESTRATOR_GUIDE.md` | `docs/operations/QWEN_TMUX_ORCHESTRATOR_GUIDE.md` | Guide legacy orchestrator |
| `docs/ops/QWEN_TEAM_ACTIVATION.md` | `docs/operations/QWEN_TEAM_ACTIVATION.md` | Activation équipe legacy |
| `docs/ops/RAPPORT_10H00_2026-02-28.md` | `docs/operations/RAPPORT_10H00_2026-02-28.md` | Rapport 10h |
| `docs/ops/RAPPORT_QUOTIDIEN_2026-02-28.md` | `docs/operations/RAPPORT_QUOTIDIEN_2026-02-28.md` | Rapport quotidien |
| `docs/ops/CODEX_PRO_CONFIG_UPDATE.md` | `docs/operations/CODEX_PRO_CONFIG_UPDATE.md` | Config post-migration |
| `docs/ops/WORKSPACE_MAP.md` | `../WORKSPACE_MAP.md` | Carte documentaire |
| `docs/ops/TMUX_HANDOFF_admin-agents_20260225-134514.md` | `../operations/ops/TMUX_HANDOFF_admin-agents_20260225-134514.md` | Référence legacy historique |
| `docs/ops/TMUX_HANDOFF_clawsentinel_20260225-084008.md` | `../operations/ops/TMUX_HANDOFF_clawsentinel_20260225-084008.md` | Référence legacy historique |

### Arborescences alias

| Alias | Cible canonique | Usage |
|-------|-----------------|-------|
| `docs/ops/ops` | `docs/operations/ops` | Espace docs opération |
| `docs/ops/orchestrator` | `docs/operations/orchestrator` | Monitoring orchestrateur |
| `docs/ops/safety` | `docs/operations/safety` | Notes sécurité |

## Scripts

De nombreux scripts dans `scripts/` sont des symlinks vers `platform/policies/` ou `platform/automation/`.  
**Canonique:** le fichier se trouve dans `platform/` ; `scripts/` expose un alias pour les commandes courtes.

---

## Risques et bonnes pratiques

1. **Ne pas créer de symlink** sans le documenter ici.
2. **Les chemins `docs/operations/*` sont historiques.** Référencer en priorité `docs/ops/*` et utiliser l’archive uniquement pour traçabilité.
2. **Préférer le chemin canonique** dans tout nouveau code ou documentation.
3. En cas de **renommage ou déplacement** de la cible, mettre à jour ce catalogue et vérifier les liens.
4. Les **chemins relatifs** dans les symlinks peuvent casser si la structure du projet change.

---

*Voir aussi: `docs/ops/AGENTS_READY.md`, `docs/ops/REMPISE_ORDRE_POST_MIGRATION.md`*
