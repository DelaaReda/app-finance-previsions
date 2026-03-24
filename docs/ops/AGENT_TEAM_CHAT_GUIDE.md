# 🤖 Agent Guide: Using TEAM_CHAT

**For**: All agent roles (planner, dev, tester, qa, backend_engineer, frontend_engineer, data_analyst, analyst, architect, integrator, infra_engineer)

---

## 🎯 QUICK START

### Step 1: Set Your Role
```bash
export TEAM_CHAT_ROLE=<your_role>
```

**Examples**:
```bash
export TEAM_CHAT_ROLE=planner
export TEAM_CHAT_ROLE=frontend_engineer
export TEAM_CHAT_ROLE=backend_engineer
export TEAM_CHAT_ROLE=data_analyst
export TEAM_CHAT_ROLE=tester
export TEAM_CHAT_ROLE=qa
```

### Step 2: Post Message
```bash
# Choose the right helper
./scripts/team_chat_<type>.sh "Your subject" "Your message"
```

---

## 📝 WHEN TO USE EACH TYPE

### 🔴 BLOCKER (Use `team_chat_blocker.sh`)

**When**: You're completely stuck and cannot proceed

**Examples**:
- API endpoint not working
- Missing dependencies
- Cannot access required files
- Test failures blocking progress

**Template**:
```bash
export TEAM_CHAT_ROLE=<your_role>
./scripts/team_chat_blocker.sh "<What's blocking you>" "<Details + error messages>"
```

**Real Example**:
```bash
export TEAM_CHAT_ROLE=frontend_engineer
./scripts/team_chat_blocker.sh "CORS errors blocking API integration" \
  "Cannot call localhost:8050 from frontend. Getting CORS policy errors. \
   Need backend to enable CORS or provide workaround."
```

---

### 🟢 PROGRESS (Use `team_chat_progress.sh`)

**When**: You completed a task or made significant progress

**Examples**:
- Task completed
- Feature implemented
- Bug fixed
- Test passing

**Template**:
```bash
export TEAM_CHAT_ROLE=<your_role>
./scripts/team_chat_progress.sh "<What you completed>" "<Details + impact>"
```

**Real Example**:
```bash
export TEAM_CHAT_ROLE=backend_engineer
./scripts/team_chat_progress.sh "Forecasts API structure fixed" \
  "Fixed response structure. Now returns forecasts array with confidence scores. \
   Endpoint ready for frontend integration."
```

---

### 🟠 QUESTION (Use `team_chat_question.sh`)

**When**: You need clarification or information

**Examples**:
- Which endpoint to use
- Unclear requirements
- Need guidance on approach
- Conflicting documentation

**Template**:
```bash
export TEAM_CHAT_ROLE=<your_role>
./scripts/team_chat_question.sh "<Your question>" "<Context + what you've tried>"
```

**Real Example**:
```bash
export TEAM_CHAT_ROLE=data_analyst
./scripts/team_chat_question.sh "Which backtests endpoint for MVP?" \
  "I see /api/backtests, /api/backtests/simple, and /api/backtests/job. \
   Which one should I prioritize for BATCH-03?"
```

---

### 🔴 HELP (Use `team_chat_help.sh`)

**When**: You need immediate assistance from specific role(s)

**Examples**:
- Need code review
- Need help debugging
- Need second opinion
- Pair programming request

**Template**:
```bash
export TEAM_CHAT_ROLE=<your_role>
./scripts/team_chat_help.sh "<What help you need>" "<Tag specific roles>"
```

**Real Example**:
```bash
export TEAM_CHAT_ROLE=frontend_engineer
./scripts/team_chat_help.sh "Need help with API connector" \
  "@backend_engineer Can you review my apiConnector.js implementation? \
   Want to make sure I'm handling errors correctly."
```

---

### 🟢 ANNOUNCEMENT (Use `team_chat_announce.sh`)

**When**: You have important information for entire team

**Examples**:
- System status updates
- New documentation available
- Process changes
- Milestone reached

**Template**:
```bash
export TEAM_CHAT_ROLE=<your_role>
./scripts/team_chat_announce.sh "<Announcement subject>" "<Details>"
```

**Real Example**:
```bash
export TEAM_CHAT_ROLE=planner
./scripts/team_chat_announce.sh "BATCH-03 tasks dispatched" \
  "All roles have been assigned tasks for BATCH-03. \
   Check your role memory for task details and success criteria."
```

---

## ⏰ RESPONSE TIME EXPECTATIONS

| Priority | Expected Response | If No Response |
|----------|------------------|----------------|
| 🔴 HIGH (BLOCKER/HELP) | 30 min | Escalate to admin-agents |
| 🟠 MEDIUM (QUESTION) | 2 hours | Post reminder |
| 🟢 LOW (PROGRESS/ANNOUNCEMENT) | 24 hours | No action needed |

---

## 🎯 BEST PRACTICES

### ✅ DO

- Set your role before posting
- Use specific, descriptive subjects
- Include impact in your message
- Tag relevant roles when needed
- Update status when blocker resolved

### ❌ DON'T

- Post without setting role
- Use vague subjects like "Help" or "Issue"
- Post same message multiple times
- Use 🔴 HIGH for non-urgent issues
- Forget to update when issue resolved

---

## 📊 EXAMPLE WORKFLOW

### Scenario: Frontend Engineer Integrating API

```bash
# 1. Set role
export TEAM_CHAT_ROLE=frontend_engineer

# 2. Start integration
./scripts/team_chat_progress.sh "Starting API integration" \
  "Beginning work on apiConnector.js integration. Will update with progress."

# 3. Encounter blocker
./scripts/team_chat_blocker.sh "CORS errors on API calls" \
  "Cannot call localhost:8050 from frontend. CORS policy blocking requests. \
   @backend_engineer Need help enabling CORS."

# 4. Blocker resolved, continue
./scripts/team_chat_progress.sh "CORS issue resolved" \
  "Backend enabled CORS. API integration proceeding normally."

# 5. Complete task
./scripts/team_chat_progress.sh "API integration complete" \
  "All widgets now using live API instead of mock data. \
   BATCH-03 frontend tasks complete."
```

---

## 🔧 TROUBLESHOOTING

### Script not found
```bash
# Check you're in project root
cd /home/venom/analyse-financiere

# Verify scripts exist
ls -la scripts/team_chat_*.sh
```

### Message not appearing
```bash
# Check ARCHIVE_TEAM_CHAT.md exists
ls -la docs/ops/ARCHIVE_TEAM_CHAT.md

# View recent messages
tail -50 docs/ops/ARCHIVE_TEAM_CHAT.md
```

### Wrong role set
```bash
# Check current role
echo $TEAM_CHAT_ROLE

# Reset role
export TEAM_CHAT_ROLE=<correct_role>
```

---

## 📚 RELATED DOCUMENTATION

- **ARCHIVE_TEAM_CHAT.md**: Main chat file (`docs/ops/ARCHIVE_TEAM_CHAT.md`)
- **Helper Scripts**: `scripts/team_chat_*.sh`
- **Product Vision**: `docs/product/PRODUCT_VISION.md`
- **Onboarding**: `docs/ops/ARCHIVE_NOUVEAUX_AGENTS_ONBOARDING.md`

---

**Guide Created**: 2026-02-28 15:40 EST  
**For**: All agent roles  
**Status**: ✅ Ready to use
