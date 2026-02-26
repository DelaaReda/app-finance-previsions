# Agent Role Integration Model (Codex-only)

## But
Rendre chaque agent utile, non redondant, et mesurable dans la chaine:
`main -> admins -> delivery -> admins -> main`.

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
| `planner` | mentor de conformite vision + dispatch (absorbe aussi scope/value ex-PO + flow/WIP ex-scrum_master) | verdict conformite + decision scope/value + check WIP/blocages + `PLANNER_ARTIFACT=` |
| `dev` | implementer l’item READY | patch/commande + `DEV_ARTIFACT=` + `cmd=` |
| `tester` | verifier execution/tests | tests + `TESTER_ARTIFACT=` + `cmd=` |
| `qa` | verdict gate final | verdict + `QA_ARTIFACT=` + `cmd=` |
| `architect` | contraintes architecture anti-derive | decision contrainte + `ARCHITECT_ARTIFACT=` |

## Regles d’integration
1. `admin-agents` detecte le probleme et assigne un owner explicite.
2. `adminapp-codex` n’auto-execute que si `action_owner=adminapp-codex`.
3. Si `action_owner` est externe (`admin-agents` ou `clawsentinel`), `adminapp-codex` route le handoff dans `ADMIN_TEAM_CHAT.md` (dedupe par `action_id`) et ne force pas de faux `BLOCKED`.
4. Sans item `READY`, le mode normal est `monitoring` (pas d’escalade artificielle).
5. Les admins ne livrent pas le code applicatif a la place de `dev/tester/qa`; ils garantissent la plomberie, le routage et la qualite du flux.

## Protocole pre-annonce obligatoire (anti-chevauchement)
1. Avant toute action delivery (`claim|edit|complete|handoff`), l’agent execute:
   - `bash scripts/preannounce_intent.sh preannounce --role <role> --scope <scope> --files <csv_paths> --eta-minutes <n>`
2. Cette commande publie automatiquement l’`INTENT` dans `docs/ops/ADMIN_TEAM_CHAT.md`, logue la pre-annonce dans `memory/YYYY-MM-DD.md`, et enregistre l’intent actif dans `docs/orchestrator-ops/intent-registry.json`.
3. Apres pre-annonce seulement, l’agent execute `scripts/parallel_workstream.py claim --role <role>`.
4. Si un autre intent actif cible les memes fichiers/sections, la pre-annonce est `BLOCKED` (pas d’ecrasement); l’agent doit reduire le scope ou faire un handoff explicite.
5. Les preuves de livraison (`EVIDENCE`) doivent contenir `intent_id`, `intent_chat_ref`, `intent_memory_ref`, `intent_registry_ref`, `edit_scope`.
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
