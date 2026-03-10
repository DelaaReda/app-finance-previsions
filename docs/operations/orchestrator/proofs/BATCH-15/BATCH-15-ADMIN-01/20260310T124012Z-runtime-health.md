# BATCH-15-ADMIN-01 Runtime Health Evidence

- Scope: Strategy Playbooks Engine admin/runtime validation after DEV chain.
- Runtime host check: `runtime_is_vm=1` in `/home/venom/analyse-financiere`.
- Blocking evidence before fix:
  - `docs/operations/orchestrator/dynamic-workers-results/worker_qa_review_worker_657bcc0100.raw.json`
  - `ERROR: {"detail":"The 'codex-full/gpt-5.4' model is not supported when using Codex with a ChatGPT account."}`
- Fix:
  - normalized QA worker secondary `codex exec` fallback from `codex-full/gpt-5.4` to `gpt-5.4` in `platform/automation/worker_manager.py`
- Verification:
  - `python3 -m pytest platform/automation/tests/test_worker_manager.py -q` => `9 passed`
  - `python3` import check => `_secondary_codex_model("codex-full/gpt-5.3-codex-spark") == ("gpt-5.4", "low")`
- Residual blocker:
  - `python3 scripts/qwen_orchestrator.py --tmux-cmd health --status-format compact --status-core-roles planner,dev,tester,qa`
  - returns `TMUX_REQUIRED_ROLES_NOT_READY`; this is an observability mismatch against planner-only scheduling, not a Strategy Playbooks runtime outage.
