#!/bin/bash
# Post QUESTION to TEAM_CHAT
# Usage: ./team_chat_question.sh "Subject" "Message"

export TEAM_CHAT_ROLE="${TEAM_CHAT_ROLE:-unknown}"
./scripts/team_chat_post.sh "QUESTION" "$1" "$2" "🟠 MEDIUM"
