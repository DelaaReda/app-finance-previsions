---
name: message-journal
description: "Append inbound/outbound chat messages to memory/chat-journal/YYYY-MM-DD.md for durable long-term recall."
metadata: {"openclaw":{"emoji":"🧠","events":["message:received","message:sent"]}}
---

# Message Journal Hook

Persists chat messages into workspace memory files for durable recall across restarts and new sessions.

- Output path: `memory/chat-journal/YYYY-MM-DD.md`
- Trigger: every inbound/outbound message event
