#!/bin/bash
# Finance Copilot Team Chat - Post Message Helper
# Usage: ./team_chat_post.sh <TYPE> <SUBJECT> <MESSAGE> [PRIORITY]

TEAM_CHAT_FILE="docs/ops/TEAM_CHAT.md"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M EST')
ROLE="${TEAM_CHAT_ROLE:-unknown}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
TYPE="${1:-QUESTION}"
SUBJECT="${2:-No subject}"
MESSAGE="${3:-No message}"
PRIORITY="${4:-🟢 LOW}"

# Validate type
case "$TYPE" in
  ANNOUNCEMENT|BLOCKER|PROGRESS|QUESTION|HELP)
    ;;
  *)
    echo -e "${RED}Error: Invalid type '$TYPE'${NC}"
    echo "Valid types: ANNOUNCEMENT, BLOCKER, PROGRESS, QUESTION, HELP"
    exit 1
    ;;
esac

# Create message
MESSAGE_BLOCK="## ${TIMESTAMP} [${ROLE}] TYPE: ${TYPE}

**Subject**: ${SUBJECT}

**Message**: 
${MESSAGE}

**Impact**: 
- Add impact description here

**Next Action**:
- Add next action here

**Priority**: ${PRIORITY}
"

# Insert message after "ACTIVE CONVERSATIONS" section
if grep -q "## 💬 ACTIVE CONVERSATIONS" "$TEAM_CHAT_FILE"; then
  # Create temp file with new message
  awk -v msg="$MESSAGE_BLOCK" '
    /## 💬 ACTIVE CONVERSATIONS/ {
      print $0
      print ""
      print msg
      next
    }
    {print}
  ' "$TEAM_CHAT_FILE" > "${TEAM_CHAT_FILE}.tmp" && mv "${TEAM_CHAT_FILE}.tmp" "$TEAM_CHAT_FILE"
  
  echo -e "${GREEN}✅ Message posted to TEAM_CHAT.md${NC}"
  echo ""
  echo "Type: $TYPE"
  echo "Subject: $SUBJECT"
  echo "Priority: $PRIORITY"
  echo ""
  echo "View: cat $TEAM_CHAT_FILE"
else
  echo -e "${RED}Error: TEAM_CHAT.md not found or invalid format${NC}"
  exit 1
fi
