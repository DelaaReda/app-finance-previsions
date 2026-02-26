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
| `planner` | mentor de conformite vision (valider READY/IN_PROGRESS vs vision produit) | verdict conformite + regle verifiee + `PLANNER_ARTIFACT=` |
| `dev` | implementer l’item READY | patch/commande + `DEV_ARTIFACT=` + `cmd=` |
| `tester` | verifier execution/tests | tests + `TESTER_ARTIFACT=` + `cmd=` |
| `qa` | verdict gate final | verdict + `QA_ARTIFACT=` + `cmd=` |
| `architect` | contraintes architecture anti-derive | decision contrainte + `ARCHITECT_ARTIFACT=` |
| `po` | alignement scope/valeur | decision backlog + `PO_ARTIFACT=` |
| `scrum_master` | hygiene flux/WIP/blocages | action cadence + `SCRUM_ARTIFACT=` |

## Regles d’integration
1. `admin-agents` detecte le probleme et assigne un owner explicite.
2. `adminapp-codex` n’auto-execute que si `action_owner=adminapp-codex`.
3. Si `action_owner` est externe (`admin-agents` ou `clawsentinel`), `adminapp-codex` route le handoff dans `ADMIN_TEAM_CHAT.md` (dedupe par `action_id`) et ne force pas de faux `BLOCKED`.
4. Sans item `READY`, le mode normal est `monitoring` (pas d’escalade artificielle).
5. Les admins ne livrent pas le code applicatif a la place de `dev/tester/qa`; ils garantissent la plomberie, le routage et la qualite du flux.

## Protocole pre-annonce obligatoire (anti-chevauchement)
1. Avant toute action delivery (`claim|edit|complete|handoff`), l’agent publie un `TYPE: INTENT` dans `docs/ops/ADMIN_TEAM_CHAT.md` avec: `intent_id`, `planned_files`, `edit_scope`, `eta_minutes`.
2. Le meme `intent_id` doit etre logue dans `memory/YYYY-MM-DD.md` avant la premiere edition.
3. Apres pre-annonce seulement, l’agent execute `scripts/parallel_workstream.py claim --role <role>`.
4. Si un autre intent actif cible les memes fichiers/sections, l’agent n’ecrase pas: il passe en merge/handoff explicite.
5. Les preuves de livraison (`EVIDENCE`) doivent contenir `intent_id`, `intent_chat_ref`, `intent_memory_ref`, `edit_scope`.

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
- CLI de claim/handoff/validation: `scripts/parallel_workstream.py`
- Provisioning cron multi-roles specialisees: `scripts/configure_parallel_team_crons.sh`

## Commandes de controle
```bash
openclaw cron runs --id 838deae5-fa39-4052-b31d-66013faccee0 --limit 1
openclaw cron runs --id fbccac5b-1028-4c9a-b021-c1998d3bad97 --limit 1
```
