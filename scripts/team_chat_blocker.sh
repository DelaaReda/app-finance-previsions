#!/bin/bash
# Post BLOCKER to TEAM_CHAT (HIGH priority)
# Usage: ./team_chat_blocker.sh "Subject" "Message"

export TEAM_CHAT_ROLE="${TEAM_CHAT_ROLE:-unknown}"
./scripts/team_chat_post.sh "BLOCKER" "$1" "$2" "🔴 HIGH"
