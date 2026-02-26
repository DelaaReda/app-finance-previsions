# Agent Tool/Skill Requests

- Auto-generated requests from role contracts (`EVIDENCE`) when `tool_request` or `skill_request` is non-`none`.
- This file is the human-readable queue for admins/executors.
- Canonical machine feed: `docs/orchestrator-ops/agent-tool-requests.jsonl`.

Format:
- `[ts] [role] tool_request=<...>; skill_request=<...>; stream_id=<...>; task_id=<...>; source=<...>; issues=<...>; suggestion=<...>.`

- [2026-02-26T21:44:56Z] [dev] tool_request=browser_cdp_access; skill_request=playwright-mcp; stream_id=none; task_id=none; source=fallback_checkpoint; issues=signal_unparseable; suggestion=stabiliser_prompt_et_tmux_capture.
