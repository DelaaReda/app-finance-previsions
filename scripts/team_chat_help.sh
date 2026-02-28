#!/bin/bash
# Post HELP request to TEAM_CHAT (HIGH priority)
# Usage: ./team_chat_help.sh "Subject" "Message"

export TEAM_CHAT_ROLE="${TEAM_CHAT_ROLE:-unknown}"
./scripts/team_chat_post.sh "HELP" "$1" "$2" "🔴 HIGH"
