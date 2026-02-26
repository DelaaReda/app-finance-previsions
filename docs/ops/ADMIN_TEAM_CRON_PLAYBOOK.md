# Admin Team Playbook - Cron Agents (Codex-First)

## Equipe admin (3 identites)
- `adminapp-codex`:
  - owner architecture runtime cron (cadence, timeout, payload, rollback).
- `admin-agents`:
  - owner productivite des roles (DELTA utile, priorites MVP, alignement backlog).
- `clawsentinel`:
  - owner surveillance qualite/safety (logs, incidents, KPI, escalade).

## Gouvernance de reference (obligatoire)
- Source normative unique: `docs/ops/OPERATIONAL_GOVERNANCE.md`.
- Ce playbook couvre l'execution admin cron/tmux; il ne redefinit pas la gouvernance de commandement.

## Chaine de commandement (obligatoire)
1. `main` (Directeur operationnel WhatsApp) -> `admins`.
2. `admins` -> organisation/process de l'equipe de livraison.
3. `equipe de livraison` -> `admins` -> `main` (reporting et escalade).
4. Interdit:
   - directive directe de `main` vers les roles livraison (voir `docs/orchestrator-ops/parallel-role-topology.json`);
   - reponse directe de l'equipe livraison vers `main` hors circuit admin.

## Routage documentaire (obligatoire)
1. directive recue sur WhatsApp (`main`) -> publiee dans `docs/ops/ADMIN_TEAM_CHAT.md`;
2. adaptation process par admins -> tracee dans `docs/ops/ADMIN_TEAM_ITERATIONS.md`;
3. execution equipe livraison -> suivie via `docs/orchestrator-ops/agent-watchdog.md`;
4. continuité journaliere -> consignée dans `memory/YYYY-MM-DD.md`;
5. reference normative en cas de doute -> `docs/ops/OPERATIONAL_GOVERNANCE.md`.

## Noms a afficher dans chaque mise a jour
- `[adminapp-codex]`
- `[admin-agents]` (label humain: `admin agents`)
- `[clawsentinel]`
- Alias historique autorise dans les anciens logs uniquement: `AgentSentinel`.

## Signature obligatoire dans les docs
- Toute mise a jour doit commencer par un prefixe nomme:
  - `[adminapp-codex]`
  - `[admin-agents]`
  - `[clawsentinel]`
- Format recommande par entree:
  - `[YYYY-MM-DD HH:MM EST] [name] STATUS: ... DELTA: ... NEXT: ...`

## Fichiers partages uniques (single place)
- Chat de coordination tri-admin (avant toute action):
  - `docs/ops/ADMIN_TEAM_CHAT.md`
- Avancement tri-admin par iteration (source primaire):
  - `docs/ops/ADMIN_TEAM_ITERATIONS.md`
- Politique et responsabilites:
  - `docs/ops/ADMIN_TEAM_CRON_PLAYBOOK.md`
  - `docs/ops/AGENT_ROLE_INTEGRATION_MODEL.md`
  - `docs/ops/PARALLEL_SCRUM_DELIVERY_MODEL.md`
  - `docs/ops/PARALLEL_PLUMBING_QUICKSTART.md`
- Runtime incidents/decisions:
  - `docs/orchestrator-ops/agent-watchdog.md`
- Avancement MVP produit:
  - `docs/planning/WORKSTATE.md`
- Journal quotidien:
  - `memory/YYYY-MM-DD.md`
- Regle anti-dispersion:
  - toute intention d'action doit etre postee d'abord dans `ADMIN_TEAM_CHAT.md`,
  - toute iteration doit etre ecrite d'abord dans `ADMIN_TEAM_ITERATIONS.md`,
  - puis referencee dans `agent-watchdog.md` et `memory/YYYY-MM-DD.md`.

## Cadence d'iteration synchronisee (obligatoire)
Chaque iteration cron admin suit cet ordre:
1. intention courte dans `docs/ops/ADMIN_TEAM_CHAT.md`,
2. note d'iteration dans `docs/ops/ADMIN_TEAM_ITERATIONS.md`,
3. decision runtime recopiee dans `docs/orchestrator-ops/agent-watchdog.md`,
4. trace de continuite dans `memory/YYYY-MM-DD.md`.

Format minimal (3 lignes, une par admin):
- `[YYYY-MM-DD HH:MM EST] [adminapp-codex] STATUS: ... DELTA: ... NEXT: ...`
- `[YYYY-MM-DD HH:MM EST] [admin-agents] STATUS: ... DELTA: ... NEXT: ...`
- `[YYYY-MM-DD HH:MM EST] [clawsentinel] STATUS: ... DELTA: ... NEXT: ...`

Regle:
- une iteration n'est "complete" que si les 3 lignes existent.
- si un admin est indisponible, ecrire `STATUS: PENDING_SYNC` pour garder le suivi explicite.
- toute directive du directeur doit etre reformulee en plan admin avant execution (pas d'execution brute).

## Notes operationnelles de la triade
1. Regle de changement:
   - une seule variable changee par intervention (cadence, timeout, message, retry), jamais plusieurs axes a la fois.
2. Routine minimale a chaque iteration:
   - verifier `openclaw cron list --json`,
   - verifier les derniers `cron runs` sur `planner`, `backend_engineer`, `qa`,
   - publier une entree signee par chacun dans `agent-watchdog`.
3. Seuils d'escalade:
   - `tmux_unparseable` > 40% sur fenetre recente,
   - `NO_DELTA` > 70% sur fenetre recente,
   - `error/timeout` > 5%.
4. Discipline d'execution:
   - lock obligatoire avant edit, backup obligatoire avant patch, force-run de validation apres patch.

## Repartition MVP (responsabilites actives)
1. `adminapp-codex`:
   - optimiser fiabilite cron (timeouts, collisions, recoveries),
   - publier snapshot runtime (`ok/error/duration`) a chaque iteration.
2. `admin-agents`:
   - optimiser productivite role outputs (reduction `NO_DELTA`, action unique exploitable),
   - maintenir mapping backlog READY -> action dev/test/qa prioritaire.
3. `clawsentinel`:
   - optimiser investigabilite (logs propres, alertes, postmortem),
   - verifier KPI de derive (`tmux_unparseable`, `NO_DELTA`, `BLOCKED`).

Definition de done (iteration admin):
- cron profile conforme baseline codex/scheduler/high/480 (cf. `docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml`),
- entree signee 3 admins dans `agent-watchdog`,
- decision unique documentee (keep/change + preuve runs).

## Objectif
Donner un protocole unique pour les admins qui travaillent en parallèle sur les cron agents:
- stabiliser les jobs,
- garder des logs exploitables,
- éviter la dérive vers des payloads fragiles,
- utiliser les capacités OpenClaw/skills de façon cohérente.

## Décisions non négociables
1. Les jobs cron rôles restent séparés (1 job par rôle, profil parallel/17 jobs).
2. Les payloads cron appellent uniquement le runner de rôle:
   - `bash scripts/cron_tmux_role_runner.sh <role>`
3. Interdit dans `payload.message`:
   - appel direct à un orchestrator legacy (ex: `qwen_orchestrator*.py`)
   - payload ad hoc qui contourne le runner de rôle
4. Baseline agent:
   - `TMUX_ROLE_AGENT_BIN=codex`
   - `TMUX_ROLE_RETRY_ENGINE_DEFAULT=sdk`
   - `TMUX_ROLE_CODEX_EXEC_RESUME=1`
5. Baseline qualité:
   - `thinking=high`
   - `timeoutSeconds=900`
   - output structuré 8 clés (`STATUS/DELTA/EVIDENCE/RISKS/NEXT/VERDICT/BLOCKER_ID/NEXT_ACTION_UNIQUE`)
   - rapport de fin obligatoire par tick: `exec_report`, `issues`, `suggestions` (si `issues!=none`, suggestion actionnable obligatoire)
6. Logs:
   - conserver les logs par itération/run
   - logs propres par défaut (sanitized stream), pas de suppression historique sans demande explicite.

## Modèle d'équipe (3 rôles)
At each iteration, assign one of `adminapp-codex`, `admin-agents`, `clawsentinel` to each role and log it in `agent-watchdog.md`.

1. `Driver`:
   - exécute les modifications cron
   - ne modifie qu'un axe à la fois (timeout, cadence, message, etc.)
2. `Reviewer`:
   - valide commandes, diff de config, cohérence baseline
   - contrôle `cron runs` après changement
3. `Observer`:
   - surveille `journalctl` + `openclaw cron runs`
   - documente incidents et actions dans les logs d'équipe

Rotation recommandée: changer les rôles toutes les 2 heures.

## Protocole d'intervention (obligatoire)

### 0) Pre-annonce avant action
- Avant tout changement cron/runtime, exécuter:
```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "bash scripts/preannounce_intent.sh preannounce --role adminapp-codex --scope cron_runtime_change --files scripts/configure_parallel_team_crons.sh,docs/ops/ADMIN_TEAM_CRON_PLAYBOOK.md --eta-minutes 20"
```
- Cette commande:
  - publie l’`INTENT` dans `docs/ops/ADMIN_TEAM_CHAT.md`,
  - écrit la pre-annonce dans `memory/YYYY-MM-DD.md`,
  - réserve le scope dans `docs/orchestrator-ops/intent-registry.json` et bloque les chevauchements.

### 1) Prendre le lock admin
```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "scripts/cron_admin_lock.sh -- openclaw cron list"
```

### 2) Snapshot avant changement
```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "cp /home/venom/.openclaw/cron/jobs.json /home/venom/.openclaw/cron/jobs.json.backup-$(date +%Y%m%d-%H%M%S)-team-playbook"
```

### 3) Audit baseline (avant/après)
```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "jq -r '.jobs[] | [.name,.payload.thinking,.payload.timeoutSeconds,.payload.message] | @tsv' /home/venom/.openclaw/cron/jobs.json"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "rg -n 'qwen_orchestrator.py' /home/venom/.openclaw/cron/jobs.json || true"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "rg -n 'TMUX_ROLE_AGENT_BIN=codex|TMUX_ROLE_RETRY_ENGINE_DEFAULT=sdk|TMUX_ROLE_CODEX_EXEC_RESUME=1' /home/venom/.openclaw/cron/jobs.json"
```

### 4) Modifier minimalement
Toujours via lock:
```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "scripts/cron_admin_lock.sh -- openclaw cron edit <job-id> ..."
```

### 5) Forcer validation ciblée
```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "scripts/cron_admin_lock.sh -- openclaw cron run <job-id> --expect-final --timeout 900000"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "scripts/cron_admin_lock.sh -- openclaw cron runs --id <job-id> --limit 3"
```

### 6) Publier trace d'équipe
Mettre à jour:
- `docs/orchestrator-ops/agent-watchdog.md`
- `memory/YYYY-MM-DD.md`

## Politique logs clean

### Par défaut
- Les logs tmux sont nettoyés au fil de l'eau via:
  - `scripts/tmux_log_clean_stream.py`
- Les logs restent stockés par run:
  - `finance-app/orchestrator-runs/<run-id>/tmux/*.log`

### Post-traitement (si bruit résiduel)
```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "bash scripts/clean_tmux_logs.sh --mode compact finance-app/orchestrator-runs"
```

### Interdit sans validation explicite
- purge globale des logs de run
- suppression des archives en masse

## Règle "éviter orchestrator legacy"
Interprétation opérationnelle:
1. Pas d'appel direct à un orchestrator legacy (qwen/old) dans les payloads cron.
2. Le planificateur OpenClaw doit piloter les rôles via le runner unique.
3. Pour debugging: préférer `openclaw cron runs`, `tmux ls`, `tmux_codex_live_monitor`, et les scripts `validate_*`.

## Skills (admin)
Politique:
- ne pas activer de skills d'orchestration "autopilot" (derive probable).
- privilégier les scripts du repo + runner-only payloads.

Commandes utiles:
```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "openclaw skills check"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "openclaw agents list"
```

## Runbook incident (résumé)
1. `timeout` répétés:
   - monter `timeoutSeconds`, vérifier `lane wait exceeded`, forcer run
2. `NO_DELTA` excessif + `tmux_unparseable`:
   - vérifier qualité des logs tmux, prompt/contract role runner, restart rôle ciblé
3. `already-running` persistant:
   - vérifier lock cron/scheduler, éviter les runs manuels concurrents

## KPIs d'efficacité (hebdo)
1. Taux d'erreur par rôle (cible `<5%`)
2. Taux `NO_DELTA` (cible décroissante)
3. Fréquence `tmux_unparseable`
4. Temps moyen run par rôle
5. Nombre d'interventions manuelles/admin par jour

---
Références:
- `docs/ops/ADMIN_CODEX_BASELINE.md`
- `docs/ops/TMUX_CRON_OPERATIONS.md`
- `docs/ops/ADMIN_POST_RESTART_RUNBOOK.md`
- `docs/ops/CRON_STRATEGY.md`
