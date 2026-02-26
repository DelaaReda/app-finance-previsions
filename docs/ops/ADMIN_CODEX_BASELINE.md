# Admin Codex Baseline (Obligatoire)

## Objectif
Imposer une configuration unique pour tous les admins: les rôles tmux doivent tourner avec `codex`, pas `qwen`.

## Règle ferme
- `TMUX_ROLE_AGENT_BIN` doit être `codex` sur tous les jobs cron de rôles.
- Toute valeur `qwen` dans `payload.message` est une dérive à corriger immédiatement.
- Toute modification cron admin doit passer via `scripts/cron_admin_lock.sh` pour éviter les collisions multi-sessions.

## Profil attendu par job
Chaque job role (toutes lanes, cf. `docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml`) doit exécuter ce pattern:

```bash
TMUX_ROLE_AGENT_BIN=codex \
TMUX_ROLE_RETRY_ENGINE_DEFAULT=sdk \
TMUX_ROLE_CODEX_EXEC_RESUME=1 \
TMUX_ROLE_CODEX_EXEC_FALLBACK=1 \
TMUX_ROLE_CODEX_MODEL=gpt-5.3-codex \
PROMPT_TIMEOUT_SECONDS=55 \
RETRY_PROMPT_TIMEOUT_SECONDS=30 \
TMUX_ROLE_RECOVERY_THRESHOLD=2 \
SKIP_RETRY_ON_TIMEOUT=1 \
TMUX_ROLE_ALLOW_FILE_EDITS=auto \
bash scripts/cron_tmux_role_runner.sh <role>
```

Execution policy note:
- `TMUX_ROLE_ALLOW_FILE_EDITS=auto` means:
  - `dev/tester/qa` can switch to delivery mode only when queue has a `READY` item.
  - all roles stay read-only when queue has no `READY`, to avoid fake/noisy delivery loops.

## Vérification rapide

```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "codex --version"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "jq -r '.jobs[] | [.name,.payload.message] | @tsv' /home/venom/.openclaw/cron/jobs.json"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "rg -n 'TMUX_ROLE_AGENT_BIN=qwen' /home/venom/.openclaw/cron/jobs.json || true"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "scripts/cron_admin_lock.sh -- openclaw cron list --all"
```

Critère de conformité:
- aucun match `TMUX_ROLE_AGENT_BIN=qwen`
- tous les jobs incluent `TMUX_ROLE_AGENT_BIN=codex`

## Remédiation (forcée, tous rôles)

1. Sauvegarde:
```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "cp /home/venom/.openclaw/cron/jobs.json /home/venom/.openclaw/cron/jobs.json.backup-$(date +%Y%m%d-%H%M%S)-before-codex-baseline"
```

2. Refresh IDs:
```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "scripts/cron_admin_lock.sh -- openclaw cron list --all"
```

3. Patch par rôle (adapter `<job-id>`):
```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "scripts/cron_admin_lock.sh -- openclaw cron edit <job-id> --thinking high --timeout-seconds 480 --message 'Execute exactly this shell command and return ONLY its stdout, verbatim, no explanation.\nNever call send/message/delivery actions.\nCommand: TMUX_ROLE_AGENT_BIN=codex TMUX_ROLE_RETRY_ENGINE_DEFAULT=sdk TMUX_ROLE_CODEX_EXEC_RESUME=1 TMUX_ROLE_CODEX_EXEC_FALLBACK=1 TMUX_ROLE_CODEX_MODEL=gpt-5.3-codex PROMPT_TIMEOUT_SECONDS=55 RETRY_PROMPT_TIMEOUT_SECONDS=30 TMUX_ROLE_RECOVERY_THRESHOLD=2 SKIP_RETRY_ON_TIMEOUT=1 TMUX_ROLE_ALLOW_FILE_EDITS=auto bash scripts/cron_tmux_role_runner.sh <role>'"
```

4. Validation:
```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "scripts/cron_admin_lock.sh -- openclaw cron run <job-id> --expect-final --timeout 480000"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "scripts/cron_admin_lock.sh -- openclaw cron runs --id <job-id> --limit 1"
```

## Contrôle post-restart machine
Après reboot, appliquer d'abord:
- `docs/ops/ADMIN_POST_RESTART_RUNBOOK.md`

Puis vérifier explicitement la baseline codex via cette doc.

## Journal obligatoire
Après correction:
1. Ajouter une entrée horodatée dans `docs/orchestrator-ops/agent-watchdog.md`.
2. Ajouter un résumé dans `memory/YYYY-MM-DD.md`.
