# Runner Config v1

## Canonical files
- Config: `platform/config/runner/runner_config.v1.yaml`
- Schema: `platform/config/runner/runner_config.schema.json`
- Loader: `platform/automation/runner/config_loader.py`
- Legacy compatibility loader: `platform/automation/runner_config.py`

## Runtime policy
- Default mode: progressive fallback (`RUNNER_CONFIG_FALLBACK_ENV=1`).
- Strict mode: fail startup on missing required keys (`RUNNER_CONFIG_FALLBACK_ENV=0`).
- `RUNNER_CONFIG_VERSION` is exported and propagated to runner traces.

## Entry points using v1 config
- `scripts/fc_agent_tick.sh`
- `platform/automation/cron_tmux_role_runner.sh`
- `scripts/fc_setup_crons.sh` (startup validation + env propagation in cron commands)
  - cron lines now export `RUNNER_CONFIG_FILE`, `RUNNER_CONFIG_LOADER`, `RUNNER_CONFIG_FALLBACK_ENV`.

## Validate manually
- `python3 platform/automation/runner/config_loader.py validate`
- `python3 platform/automation/runner_config.py --config platform/config/runner/runner_config.v1.yaml validate`

## Notes
- Existing env variables remain supported for compatibility.
- Cron commands now pass `RUNNER_CONFIG_FILE`, `RUNNER_CONFIG_LOADER`, and `RUNNER_CONFIG_FALLBACK_ENV` explicitly.
