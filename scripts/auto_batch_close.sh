#!/usr/bin/env bash
# auto_batch_close.sh — Ferme automatiquement les batches dont toutes les sous-tâches sont DONE
# Lance: bash scripts/auto_batch_close.sh
# Idéalement ajouté en cron (ex: toutes les 30 min après les agents)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

python3 << 'PY'
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

# Use canonical paths (orchestrator-ops is a symlink to operations/orchestrator)
wb_path = Path('docs/operations/orchestrator/parallel-workstreams.json')
pq_path = Path('docs/operations/orchestrator/priority-queue.json')
wb = json.loads(wb_path.read_text())
pq = json.loads(pq_path.read_text())
ts = datetime.now(timezone.utc).isoformat()

tasks = wb.get('tasks', [])
closed = []
unlocked = []

# FIX: Group by stream_id field OR by BATCH-NN prefix extracted from task id.
# Previous code only handled 3-part IDs (BATCH-NN-CODE) and ignored
# multi-part IDs like BATCH-26-DEV-02 → caused premature batch close bug.
by_batch = defaultdict(list)
for t in tasks:
    stream = t.get('stream_id', '')
    if stream and re.match(r'^BATCH-\d+$', stream):
        by_batch[stream].append(t)
        continue
    # Fallback: extract BATCH-NN prefix from task id
    tid = t.get('id', '')
    m = re.match(r'^(BATCH-\d+)-', tid)
    if m:
        by_batch[m.group(1)].append(t)

# Vérifier si toutes les sous-tâches d'un batch sont DONE
for batch_id, subtasks in sorted(by_batch.items()):
    if not subtasks:
        continue
    all_done = all(t.get('state') in ('DONE', 'CLOSED', 'PASS') for t in subtasks)
    if not all_done:
        pending = [t.get('id') for t in subtasks if t.get('state') not in ('DONE', 'CLOSED', 'PASS')]
        print(f'  {batch_id}: {len(pending)} tâches non-DONE: {pending[:5]}')
        continue

    # Chercher le batch parent dans la priority queue
    for item in pq.get('items', []):
        if item.get('id') == batch_id and item.get('state') not in ('CLOSED', 'DONE', 'PASS'):
            item['state'] = 'CLOSED'
            item['closed_at'] = ts
            item['closed_by'] = 'auto_batch_close'
            closed.append(batch_id)

            # Fermer aussi le stream correspondant dans parallel-workstreams.json
            for stream in wb.get('streams', []):
                if stream.get('id') == batch_id and stream.get('state') not in ('CLOSED', 'DONE'):
                    stream['state'] = 'CLOSED'
                    stream['updated_at'] = ts

            # Débloquer le batch suivant si WAITING_DEP
            nn = int(batch_id.split('-')[1])
            next_id = f"BATCH-{nn+1:02d}"
            for next_item in pq.get('items', []):
                if next_item.get('id') == next_id and next_item.get('state') == 'WAITING_DEP':
                    next_item['state'] = 'READY'
                    next_item['updated_at'] = ts
                    unlocked.append(next_id)
            break

if closed or unlocked:
    pq_path.write_text(json.dumps(pq, indent=2, ensure_ascii=False))
    wb['updated_at'] = ts
    wb_path.write_text(json.dumps(wb, indent=2, ensure_ascii=False))
    for b in closed:
        print(f'✅ CLOSED {b} (toutes sous-tâches DONE)')
    for b in unlocked:
        print(f'🔓 UNLOCKED {b} (WAITING_DEP → READY)')
    if unlocked:
        import subprocess
        r = subprocess.run(
            ['python3', 'platform/automation/parallel_workstream.py', 'sync-priority'],
            capture_output=True, text=True
        )
        print(f'sync-priority: {r.stdout.strip() or r.stderr.strip()}')
else:
    print('ℹ️  Aucun batch à fermer automatiquement')
PY
