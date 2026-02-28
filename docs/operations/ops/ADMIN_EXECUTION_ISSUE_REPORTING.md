# Admin Execution Issue Reporting Policy

## But

Accélérer la livraison en rendant **obligatoire** la remontée des problèmes d’exécution (cron/tmux/runner) avec un **mini-rapport machine-readable** et une **action proposée**.

Cette politique s’applique aux 3 admins:
- **adminapp-codex** (runtime governance owner)
- **admin-agents** (delivery productivity owner)
- **clawsentinel** (safety/quality owner)

## Sources de vérité à surveiller (ordre)

1. `openclaw cron list --json` + `scripts/cron_run_manager.sh status` (timeouts, error, stale running)
2. `docs/orchestrator-ops/executors-monitoring-latest.json` (digest role-level sans logs bruts)
3. `docs/ops/AGENT_TOOL_REQUESTS.md` + `docs/orchestrator-ops/agent-tool-requests.jsonl` (demandes outillage)
4. `~/.openclaw/cron/role-state/<role>.last_contract` (BLOCKER_ID/NEXT_ACTION)
5. `~/.openclaw/cron/runs/<jobId>.jsonl` (derniers summaries)
6. `docs/orchestrator-ops/priority-queue.json` (READY/BLOCKED)
7. `finance-app/openclaw-gates/*.md` (VERDICT)

## Définition d’un “problème d’exécution”

Remonter systématiquement si l’un des signaux apparaît:
- `cron: job execution timed out`
- `stale_running_jobs` (runningAtMs sans process live)
- `TMUX_REPLY_UNPARSEABLE` / `TMUX_RESPONSE_UNSTRUCTURED`
- `EXEC_REPORT_MISSING` / `ISSUES_SUMMARY_MISSING` / `SUGGESTIONS_SUMMARY_MISSING`
- `PREANNOUNCE_EVIDENCE_MISSING` (si édition attendue)
- `TOOL_SKILL_REQUEST_PENDING` (demande outillage non traitée)
- toute dérive de modèle/thinking non conforme aux standards (roles codex / main gpt-5.2)

## Format de remontée (obligatoire)

Dans `docs/ops/ADMIN_TEAM_CHAT.md`:
- TYPE: `ALERT` (ou `BLOCKER` si la livraison est arrêtée)
- MSG: doit inclure **evidence + action**.

Template recommandé:

- [<ts>] [<admin>] TYPE: ALERT MSG: exec_issue=<id>; scope=<role|cron>; evidence=<fichier+extrait>; impact=<ce que ça casse>; suggestion=<action unique>.

## Exigence “mini rapport” par tick

Quand un rôle produit un tick, son `EVIDENCE` doit contenir:
- `exec_report=<resume_execution_concret>`
- `issues=<none|liste_priorisee>`
- `suggestions=<none|actions>`

Si manquant: remonter + proposer correction du prompt/runner (sans changer 10 variables).

## Règle d’intervention

**Une seule variable par intervention** (et toujours journaliser):
lock -> backup -> minimal edit -> force-run -> journal.
