# Rattrapage agents / migration modèle (2026-02-28)

## État validé (runtime)
- `platform/config/model-config.sh` :
  - `MODEL_CONFIG_PARALLEL_ROLE_MODEL=openai-codex/gpt-5.3-codex-spark`
  - `MODEL_CONFIG_PARALLEL_ROLE_THINKING=xhigh`
- `openclaw agents list --json` :
  - `adminapp-codex`, `admin-agents`, `clawsentinel`, `planner`, `analyst`, `architect`, `backend_engineer`, `frontend_engineer`, `data_analyst`, `infra_engineer`, `integrator`, `dev`, `tester`, `qa`, `po`, `scrum_master` => profils `gpt-5.3-codex-spark`.
- `openclaw cron list --json` : payload `model=gpt-5.3-codex-spark`, `thinking=xhigh` pour les jobs tmux.
- `tmux ls` : sessions rôle actives: `codex_*_cron`, `clawsentinel`, `tmux_live_monitor`.  
  `adminapp_codex_sync` et `admin-agents-sync-cron` restent absents tant que les jobs admin restent en erreur.

## Actions de relance effectuées
- Redémarrage watchdog monitor: `bash scripts/tmux_live_watchdog.sh restart`
- `cron_run_manager.sh` a été utilisé pour des `run-now` ciblés (`planner`, `po-tmux-loop`, `scrum_master`, `adminapp-codex-sync-10m`, `admin-agents-supervisor-15m`) pour détecter les jobs bloqués.
- `scripts/tmux_codex_live_monitor.sh` a été ajusté: fallback par défaut basé sur topology (`docs/orchestrator-ops/parallel-role-topology.json`) pour éviter les faux positifs `po` / `scrum_master`.

## Monitoring continu activé
- Session watchdog active: `bash scripts/tmux_live_watchdog.sh status`
- Santé sessions tmux: `bash scripts/tmux_codex_live_monitor.sh --mode status --engine capture --include-admin`
- Vérification jobs: `openclaw cron list --json | python3 - <<'PY'`

```bash
openclaw cron list --json | python3 - <<'PY'
import json
j=json.load(open(0))
for x in j.get('jobs',[]):
    if not x.get('name','').endswith('-tmux-loop'):
        continue
    st=x.get('state',{})
    print(f"{x['name']}\t{st.get('lastStatus')}\t{st.get('lastError','')}")
PY
```
- Surveillance continue dédiée: `bash scripts/watch_codex_runtime.sh --interval 120`  
  Exécution ponctuelle: `bash scripts/watch_codex_runtime.sh --once`.

## Point de blocage actuel
- Les jobs tmux remontent encore `lastError: ⚠️ API rate limit reached. Please try again later.` en continu.
- Bilan snapshot (au moment de la vérif): jobs `-tmux-loop` et administratifs en erreur de manière répétée (quota API externe), même après relance.
- Cause identifiée: saturation externe d’API OpenAI, pas une régression de migration (modèles/runner cohérents).
- Dès que la limite API retombe, garder les réglages existants (`gpt-5.3-codex-spark` + `xhigh`) et relancer via `cron_run_manager.sh run-now`.

## Mode opératoire en continue
1. `bash scripts/tmux_live_watchdog.sh status`
2. `bash scripts/tmux_codex_live_monitor.sh --mode status --engine capture --include-admin`
3. `openclaw cron list --json | jq -r '.jobs[] | select(.name|test("-tmux-loop$|adminapp-codex-sync-10m|admin-agents-supervisor-15m|stale-sweep-autoheal-7m|vm-resume-guard-2m|dg-admin-router-5m|dg-alert-15m")) | [.name, (.state.lastStatus//"none"), (.state.lastError//"-")] | @tsv'`
4. En cas de persistance d’erreur: redémarrer watchdog + relance manuelle des rôles impactés avec `run-now`.
