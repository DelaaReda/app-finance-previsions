#!/bin/bash
# Post PROGRESS to TEAM_CHAT
# Usage: ./team_chat_progress.sh "Subject" "Message"

export TEAM_CHAT_ROLE="${TEAM_CHAT_ROLE:-unknown}"
./scripts/team_chat_post.sh "PROGRESS" "$1" "$2" "🟢 LOW"
