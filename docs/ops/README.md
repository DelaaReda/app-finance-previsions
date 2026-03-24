---
status: reference
last_verified: 2026-03-13
superseded_by: ACTIVE_DOCS_INDEX.md
---

# Ops documentation

This subtree documents the canonical operating model and the remaining migration gap.

Canonical entrypoint:
- [ACTIVE_DOCS_INDEX.md](./ACTIVE_DOCS_INDEX.md)

This README is a convenience redirect only. It is not a second canonical entrypoint.

## Current state
- The documentation canon is aligned.
- The durable runtime already exists around LangGraph, SQLite, event state, and model plane.
- Plane is already the canonical backlog front-door in doctrine.
- The migration is not finished yet: several compatibility bridges and legacy registries are still central in active code paths.

## Target split
- Plane OSS = backlog front-door
- official Plane MCP + Plane webhooks = backlog interface and sync intake
- LangGraph + SQLite = runtime truth
- OpenClaw + systemd = operator plane
- codex exec = primary agent execution
- qwen cli = fallback for agents only
- g4f = app only

## Reference and history
- [reference/README.md](./reference/README.md)
- [archive/README.md](./archive/README.md)
