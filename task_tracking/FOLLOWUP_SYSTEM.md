# 🔄 Follow-up System for Task Completion

This system ensures proper tracking of agent progress and verifies genuine delivery.

## Daily Check-ins Protocol

### Morning Check (09:00 UTC)
1. Review current task statuses in DASHBOARD.md
2. Check if any tasks are stuck in CLAIMED/IN_PROGRESS for > 24h
3. Send gentle reminder to agent via AGENTS_MESSAGES.md if stuck
4. Update progress tracking in individual task files

### Mid-day Check (14:00 UTC) 
1. Verify if claimed tasks have active commits in git log
2. Test endpoints mentioned in tasks if available
3. Check for communication in AGENTS_MESSAGES.md
4. Update DASHBOARD.md with progress

### Evening Check (18:00 UTC)
1. Verify completed tasks with smoke tests
2. Validate that locks have been removed for done tasks
3. Update TASKS_BOARD.md status if verification passes
4. Update SCORE_AGENTS.md if applicable

## Verification Methods

### 1. Code Verification
- Check git log for recent commits related to claimed tasks
- Verify file creation/modification dates
- Check that claimed files are not empty or placeholder
- Verify imports work correctly (no ModuleNotFoundError)

### 2. Functionality Verification  
- Run smoke tests mentioned in TASKS_BOARD.md
- Verify endpoints return actual data, not empty responses
- Test backend startup and stability via curl requests
- Confirm API responses follow {ok, data} contract

### 3. Quality Verification
- Check for proper error handling (never-empty patterns)
- Verify API contracts are respected ({ok, data} structure)
- Confirm proper data persistence and caching
- Validate that no mock/fake data is used

## Communication Templates

### Status Check
```
[UTC YYYY-MM-DD HH:MM] [ASK] MSG: MSG-YYYYMMDD-HHMM-MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23
From: @MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23  →  To: @<AGENT_HANDLE>
Task: <TASK_ID>
Subject: [ASK] - <TASK_ID> status check
Message:
- How is the progress on <TASK_ID>, <AGENT_NAME>?
- Are endpoints responding with real data instead of empty responses?
- Any blockers I can help resolve?
Links:
- TASKS_BOARD.md#<TASK_ID>
Need by: <DATE_TIME_UTC>
```

### Quality Verification Request
```
[UTC YYYY-MM-DD HH:MM] [VERIFY] MSG: MSG-YYYYMMDD-HHMM-MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23
From: @MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23  →  To: @<AGENT_HANDLE>
Task: <TASK_ID>
Subject: [VERIFY] - <TASK_ID> quality check
Message:
- Hi <AGENT_NAME>, can you confirm <TASK_ID> implementation?
- Does it follow never-empty pattern with cached snapshots?
- Can you share curl output proving data is real, not mocked?
Links:
- backend/storage/io.py
- curl output in proofs/<TASK_ID>/
Need by: <DATE_TIME_UTC>
```

## Quality Gates

Before marking any task as complete, verify:
1. ✅ No mock/fake data - real data sources used
2. ✅ Never-empty pattern implemented properly with caching
3. ✅ Proper error handling and fallbacks to cached data
4. ✅ API contracts respected ({ok, data} format)
5. ✅ Endpoints respond with real data (not empty arrays/objects)
6. ✅ Backend stability maintained after changes
7. ✅ Import errors resolved (no ModuleNotFoundError)
8. ✅ Proper metadata (freshness, source, version) included

## Verification Process for Completed Tasks

When an agent marks a task as DONE:
1. Check that corresponding lock file is removed
2. Verify the endpoint/api described in the task is functional
3. Run smoke test on the specific endpoint: `curl -sS http://localhost:8050/api/[endpoint] | jq .`
4. Confirm responses follow never-empty pattern with proper structure
5. Validate that actual data is returned, not placeholder/empty responses
6. Check git log for related commits from the claiming agent
7. Update verification status in task_tracking/[TASK_ID].md file