# Agent Role Integration Model (OpenClaw/Qwen)

## But
Rendre chaque agent utile, non redondant, et mesurable jusqu'à la livraison finale de la migration vers l'architecture cible avec toi comme point de consolidation.

Chaîne de valeur :
`main -> admins -> delivery -> admins -> main`.

Règle absolue: toute action de livraison doit contribuer à un état plus proche du fini migration (`apps/api`, `apps/web`, `packages`, `platform`, `evidence` structurés), ou lever un blocker qui empêche explicitement la marche.

## Contrat de responsabilite

### Admins
| Role | Mandat unique | Input principal | Output obligatoire | Qui agit apres |
|---|---|---|---|---|
| `adminapp-codex` | stabilite runtime (cron/tmux/locks/recovery) | `openclaw cron list/runs`, etat scheduler | action runtime appliquee ou reroutee, preuve monitor | `adminapp-codex` (auto-exec) ou owner route |
| `admin-agents` | productivite livraison (signal utile, deltas actionnables) | queue READY, traces roles, sessions tmux | `deterministic_issue`, `action_id`, `action_owner`, `action_scope`, `next_action` | owner cible dans `action_owner` |
| `clawsentinel` | qualite/safety/anti-derive (signal, hygiene, risques) | logs, watchdog, chat iterations | action anti-derive ou recommandation qualite | `adminapp-codex` (si runtime) ou delivery/admins |

### Delivery
| Role | Mandat | Output attendu |
|---|---|---|
| `vision-architect-tasks-planner` (`planner` canonique) | piloter la fin migration + ordre de valeur (P0, P1...) + arbitrage WIP/handoffs + clarification batch/task/how + absorption lanes `analyst/architect/po/scrum_master` | verdict conformité + `PLANNER_ARTIFACT=` + `next_owner=` + `batch_scope` + `task_breakdown` + `execution_plan` + `handoff_plan` |
| `dev` | implémenter l’item READY + auto-contrôle local | patch/commande + `DEV_ARTIFACT=` + `cmd=` + preuve `self_qa`/`data_source_check`/`arch_check`/`real_data_check`/`ui_impact` |
| `backend_engineer` | implémentation backend de migration (API/contracts/services) | patch/commande + `BACKEND_ARTIFACT=` + `cmd=` |
| `frontend_engineer` | implémentation UI migration (DOMAINE + contrats frontend) | patch/commande + `FRONTEND_ARTIFACT=` + `cmd=` |
| `integrator` | assembly/finalisation cross-domain de la migration | intégration + `INTEGRATOR_ARTIFACT=` + `cmd=` |
| `data_analyst` | validation pipeline data/feeds + qualité de données | rapport + `DATA_ARTIFACT=` |
| `infra_engineer` | infra/runbook/monitoring migration | scripts/ops + `INFRA_ARTIFACT=` |
| `tester` | vérifier exécution/tests | tests + `TESTER_ARTIFACT=` + `cmd=` |
| `qa` | gate global final (intégration/régression) | verdict + `QA_ARTIFACT=` + `cmd=` + `qa_scope=global_gate` + `self_qa_ref` + checks `app_launch`/`real_data_check` |
| `analyst` / `architect` / `po` / `scrum_master` | lanes legacy regroupées dans `vision-architect-tasks-planner` | utiliser `--role planner` (ou alias public) pour claim/complete |

## Prompts obligatoires par rôle (copier-coller)

Chaque rôle doit envoyer un prompt structuré via `claim`/`complete` avec au moins 5 étapes (scope, dépendances, risque, vérification, rollback) et 3 checks d'architecture distincts.

### vision-architect-tasks-planner / Chef de flux
```bash
python3 scripts/parallel_workstream.py claim --role planner --change-plan "1) lire board + verifier priorite visée migration; 2) confirmer proprietaire et fichier impacte; 3) identifier dependances cross-domain; 4) choisir livraison minimale qui fait progresser architecture cible; 5) definir rollback si regressions; 6) prevoir preuve de completion;" --architecture-checks "target-arch-path; task_scope_match; no_cross_scope_without_handoff; forecast_contract_unchanged_or_updated"
```

### Dev / Backend
```bash
python3 scripts/parallel_workstream.py claim --role dev --change-plan "1) lire task + verifier pre-condition tests; 2) confirmer proprietaire domaine backend; 3) editer seulement chemins ciblés; 4) executer validations ciblées; 5) valider impact migration frontend/ops; 6) definir rollback fichier;" --architecture-checks "scope_only; domain_boundary; no_contract_drift; evidence_required"
```

### Backend Engineer
```bash
python3 scripts/parallel_workstream.py claim --role backend_engineer --change-plan "1) lire la task backend; 2) valider source unique contrats; 3) checker dependencies data/services; 4) appliquer patch minimal; 5) lancer tests d’endpoints ciblés; 6) verifier compatibilité contrats partagés; 7) rollback local documente;" --architecture-checks "api_contract_single_source; domain_boundary; schema_stability; fallback_path; observability_tags"
```

### Frontend Engineer
```bash
python3 scripts/parallel_workstream.py claim --role frontend_engineer --change-plan "1) lire task UI; 2) confirmer contrat frontend depuis packages/contracts; 3) modifier composant domaine ciblé; 4) garantir path runtime unique; 5) valider rendu navigateur; 6) verifier fallback de données; 7) rollback si erreur de rendering;" --architecture-checks "contracted_ui_dto; no_logic_duplication; no_default_mock_nominal; navigation_flow <=3_clicks; monitoring_snapshot"
```

### Tester / QA
```bash
python3 scripts/parallel_workstream.py claim --role tester --change-plan "1) lire artifact attendu; 2) lancer suite ciblée; 3) vérifier contrat output; 4) produire snapshots/browsers quand demandé; 5) noter gaps de preuve; 6) signaler rollback de test ou hard-fail;" --architecture-checks "api_contract_valid; browser_smoke_required; evidence_fields; snapshot_required_when_ui"

python3 scripts/parallel_workstream.py claim --role qa --change-plan "1) collecter artefacts delivery; 2) vérifier 8 clés contrat; 3) confirmer gates (mock/coverage/freshness) ; 4) valider monitoring post-livraison; 5) décider PASS/BLOCKED avec rationale; 6) définir next_action unique;" --architecture-checks "blockers_explicit; verdict_ready; mandatory_evidence; evidence_hash"
```

### Data / Infra (lanes autonomes)
```bash
python3 scripts/parallel_workstream.py claim --role data_analyst --change-plan "1) cartographier flux data/feeds; 2) confirmer fallback de fraîcheur; 3) mesurer gaps forecast/coverage; 4) proposer correction ciblée; 5) définir checks data;" --architecture-checks "freshness_contract; signal_coverage; no_direct_data_access_without_domain"

python3 scripts/parallel_workstream.py claim --role infra_engineer --change-plan "1) vérifier pipeline tmux/crons; 2) valider scripts/monitoring; 3) corriger point de panne isolé; 4) tester runbook; 5) confirmer restauration;" --architecture-checks "monitoring_kpi; recovery_path; runtime_stability"
```
Pour les checks `analyst/architect/po/scrum_master`, utiliser la lane unifiée:
`python3 scripts/parallel_workstream.py claim --role planner ...`
```

### Contrôle commun de fermeture (complete)
```bash
python3 scripts/parallel_workstream.py complete --role <role> --task <task_id> --artifact <path> --exec-cmd "<cmds_executes_or_SKIP(reason)>" --tests-run "<tests_or_SKIP(reason)>" --change-plan "<memoir de ce qui a été fait>" --architecture-checks "<checks_reprises_post_change>"
```

## Regles d’integration
1. `admin-agents` detecte le probleme et assigne un owner explicite.
2. `adminapp-codex` n’auto-execute que si `action_owner=adminapp-codex`.
3. Si `action_owner` est externe (`admin-agents` ou `clawsentinel`), `adminapp-codex` route le handoff dans `ADMIN_TEAM_CHAT.md` (dedupe par `action_id`) et ne force pas de faux `BLOCKED`.
4. Sans item `READY`, le mode normal est `monitoring` (pas d’escalade artificielle).
5. Les admins ne livrent pas le code applicatif a la place de `dev/tester/qa`; ils garantissent la plomberie, le routage et la qualite du flux.
6. Chaque role delivery doit lire les canaux de publication avant action (`python3 scripts/parallel_workstream.py channels --role <role> --limit 5`) et reporter `channels_read`, `impact_assessment`, `impact_action` dans son contrat.

## Protocole pre-annonce obligatoire (anti-chevauchement)
1. Avant toute action delivery (`claim|edit|complete|handoff`), l’agent execute:
   - `bash scripts/preannounce_intent.sh preannounce --role <role> --scope <scope> --files <csv_paths> --eta-minutes <n>`
2. Cette commande publie automatiquement l’`INTENT` dans `docs/ops/ADMIN_TEAM_CHAT.md`, logue la pre-annonce dans `memory/YYYY-MM-DD.md`, et enregistre l’intent actif dans `docs/orchestrator-ops/intent-registry.json`.
3. Après pre-annonce seulement, l’agent exécute la commande `claim` du template correspondant à son rôle ci-dessus.
   - Conditions obligatoires:
     - `<plan_reasoned>` doit contenir au moins 5 étapes concrètes (non-duplicatives, >=2 mots chacune),
     - `<checks_reasoned>` au moins 3 checks d’architecture concrets,
     - l’ensemble `change-plan + architecture-checks` doit couvrir 5 dimensions de réflexion: `scope`, `dependency_impact`, `risk`, `verification`, `rollback`.
4. Si un autre intent actif cible les memes fichiers/sections, la pre-annonce est `BLOCKED` (pas d’ecrasement); l’agent doit reduire le scope ou faire un handoff explicite.
5. Les preuves de livraison (`EVIDENCE`) doivent contenir `intent_id`, `intent_chat_ref`, `intent_memory_ref`, `intent_registry_ref`, `edit_scope`.
   - Pour `task_update=claim|complete|handoff`, ajouter aussi `reflection_passes>=2` (ou plus selon config runtime) et `reflection_dimensions=scope,dependency_impact,risk,verification,rollback`.
6. A la fin de la livraison, fermer l’intent:
   - `bash scripts/preannounce_intent.sh close --intent-id <id> --status done`

## Mapping owner par issue (admin-agents)
- `sessions_missing`, `role_errors_present`, `role_jobs_pending`, `role_jobs_missing`, `role_jobs_disabled`, `sessions_stale_no_recent_runner_activity` -> `adminapp-codex` (`runtime_stability`)
- `sessions_idle_generic_prompt` -> `clawsentinel` (`quality_signal`)
- `roles_disabled_admins_only_mode` -> `admin-agents` (`delivery_governance`)
- `none` -> `none` (`monitoring`)

## Validation minimum par tick admin
1. `admin-agents` doit publier: `action_id`, `action_owner`, `action_scope`, `next_action`.
2. `adminapp-codex` doit publier dans `EVIDENCE`: owner/action/scope/resultat.
3. Si owner externe: une ligne `TYPE: HANDOFF` doit apparaitre dans `docs/ops/ADMIN_TEAM_CHAT.md`.

## Contrôle post-lancement (monitoring de santé)

Après chaque start d’equipe (ou au démarrage d’un lot), chaque admin applique ce protocole de 4 checks 60-120s après actions et 5 minutes après:

1. `python3 scripts/parallel_workstream.py status`
2. `python3 scripts/parallel_workstream.py sync-priority --include-pass`
3. `python3 scripts/qwen_orchestrator.py --tmux-cmd status --status-format compact`
4. `python3 scripts/parallel_workstream.py validate --strict-warn --in-progress-stale-seconds 900`

Conditions de blocage immédiat de lot:
- `ready<` 4/4 sur orchestrator quand le lot cible inclut les rôles de production,
- plus d’une erreur d’exécution similaire en 15 minutes,
- plus d’un bloc `EVIDENCE_MISSING_*` sans correction de prompt.

## Parallel delivery plumbing
- Workboard et dependances inter-roles: `docs/orchestrator-ops/parallel-workstreams.json`
- Registre d intentions actives: `docs/orchestrator-ops/intent-registry.json`
- CLI de claim/handoff/validation: `scripts/parallel_workstream.py`
- CLI de pre-annonce/close/list: `scripts/preannounce_intent.sh`
- Provisioning cron multi-roles specialisees: `scripts/configure_parallel_team_crons.sh`

## Commandes de controle
```bash
openclaw cron runs --id 838deae5-fa39-4052-b31d-66013faccee0 --limit 1
openclaw cron runs --id fbccac5b-1028-4c9a-b021-c1998d3bad97 --limit 1
```
