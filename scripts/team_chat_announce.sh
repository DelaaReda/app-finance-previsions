#!/bin/bash
# Post ANNOUNCEMENT to TEAM_CHAT
# Usage: ./team_chat_announce.sh "Subject" "Message"

export TEAM_CHAT_ROLE="${TEAM_CHAT_ROLE:-unknown}"
./scripts/team_chat_post.sh "ANNOUNCEMENT" "$1" "$2" "🟢 LOW"
