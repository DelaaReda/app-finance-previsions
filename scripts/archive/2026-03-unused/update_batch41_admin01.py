#!/usr/bin/env python3
"""Update BATCH-41-ADMIN-01 from BLOCKED to DONE in workboard."""
import json

# Load workboard
with open('docs/operations/orchestrator/parallel-workstreams.json', 'r') as f:
    workboard = json.load(f)

# Find and update BATCH-41-ADMIN-01 in tasks list
tasks = workboard.get('tasks', [])
updated = False

for task in tasks:
    if task.get('id') == 'BATCH-41-ADMIN-01':
        print(f"Found task: {task.get('id')}")
        print(f"Current state: {task.get('state')}")
        print(f"Current blocked_reason: {task.get('blocked_reason')}")
        
        # Update task state
        task['state'] = 'DONE'
        task['blocked_reason'] = ''
        task['completed_at'] = '2026-03-11T06:50:20Z'
        task['updated_at'] = '2026-03-11T06:50:20Z'
        
        # Add completion artifact
        completion_artifact = 'proof_manifest=/home/venom/shared/analyse-financiere/docs/operations/orchestrator/proofs/BATCH-41/BATCH-41-ADMIN-01/20260311T065020Z-admin-completion-proof.json'
        if 'artifacts' not in task:
            task['artifacts'] = []
        if completion_artifact not in task['artifacts']:
            task['artifacts'].append(completion_artifact)
        
        # Update notes with completion summary
        completion_note = 'COMPLETION: Runtime validation complete - dependency gate satisfied (BATCH-41-DEV-03=DONE), runtime healthy (cron_profile_full), API contract validated (18/18 tests pass). Stale blocker cleared: admin_cron_inactive was pre-migration metadata, admin is now planner-owned.'
        if 'notes' not in task:
            task['notes'] = []
        if completion_note not in task['notes']:
            task['notes'].append(completion_note)
        
        print(f"Updated state: {task.get('state')}")
        print(f"Updated completed_at: {task.get('completed_at')}")
        updated = True
        break

if updated:
    # Save updated workboard
    with open('docs/operations/orchestrator/parallel-workstreams.json', 'w') as f:
        json.dump(workboard, f, indent=2, ensure_ascii=False)
    print("Workboard updated successfully")
else:
    print("Task BATCH-41-ADMIN-01 not found")
