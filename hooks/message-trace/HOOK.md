---
name: message-trace
description: Send a compact execution trace after each outbound WhatsApp reply to owner, showing commands/files/network touched in that turn.
metadata:
  openclaw:
    emoji: 🔎
    events:
      - message:sent
    os:
      - linux
      - darwin
---

# Message Trace Hook

Adds an Execution Trace message after outbound assistant replies in owner WhatsApp DM.

Behavior:
- Trigger on message:sent
- Scope: channel whatsapp, recipient +14389799898
- Reads current session turn from session transcript
- Emits a second message with commands/files/network summary
