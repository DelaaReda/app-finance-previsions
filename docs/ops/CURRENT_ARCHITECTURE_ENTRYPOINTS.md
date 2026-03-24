---
status: reference
last_verified: 2026-03-13
superseded_by: ACTIVE_DOCS_INDEX.md
---

# Current architecture summary

Canonical entrypoint:
- [ACTIVE_DOCS_INDEX.md](./ACTIVE_DOCS_INDEX.md)

## Current implementation reality
- The target mode is fixed.
- The repo is still in bridge-removal phase, not in minimal-plumbing end state.
- Plane sync code, runtime truth reading, and the durable planner runtime already exist.
- Several JSON and JSONL registries still remain central in real execution or observability paths.

## Canonical rules
- Create and prioritize backlog in Plane OSS, not in Markdown docs, queue files, or workboards.
- Agents manipulate backlog through the official Plane MCP server.
- Plane webhooks must become the main sync intake, with lightweight polling as fallback.
- LangGraph + SQLite are the only execution truth.
- OpenClaw and systemd own operator supervision.
- Plane webhook intake is exposed at `/api/planning/plane/webhook` and must write runtime truth before projections.
- Active prompts and scripts must treat repo planning markdown as reference only and use Plane sync plus SQLite or planner graph as the operational truth.
