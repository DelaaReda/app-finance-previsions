# Agent Tool/Skill Requests

- Auto-generated requests from role contracts (`EVIDENCE`) when `tool_request` or `skill_request` is non-`none`.
- This file is the human-readable queue for admins/executors.
- Canonical machine feed: `docs/orchestrator-ops/agent-tool-requests.jsonl`.

Format:
- `[ts] [role] tool_request=<...>; skill_request=<...>; stream_id=<...>; task_id=<...>; source=<...>; issues=<...>; suggestion=<...>.`

- [2026-02-26T21:44:56Z] [dev] tool_request=browser_cdp_access; skill_request=playwright-mcp; stream_id=none; task_id=none; source=fallback_checkpoint; issues=signal_unparseable; suggestion=stabiliser_prompt_et_tmux_capture.
- [2026-03-01T02:54:10Z] [planner] tool_request=qwen; skill_request=none; stream_id=RATELIMIT_planner; task_id=RATELIMIT_planner; source=rate_limit_gate_cache; issues=rate_limit_detected; suggestion=attendre le déblocage du quota avant nouveau lancement.
- [2026-03-01T02:54:16Z] [planner] tool_request=codex; skill_request=none; stream_id=RATELIMIT_planner; task_id=RATELIMIT_planner; source=rate_limit_gate_probe; issues=rate_limit_detected; suggestion=attendre le déblocage du quota avant nouveau lancement.
- [2026-03-01T04:20:05Z] [backend_engineer] tool_request=codex; skill_request=none; stream_id=RATELIMIT_backend_engineer; task_id=RATELIMIT_backend_engineer; source=rate_limit_gate_cache; issues=rate_limit_detected; suggestion=attendre le déblocage du quota avant nouveau lancement.
