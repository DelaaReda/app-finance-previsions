#!/usr/bin/env bash
# auto_batch_close.sh — Ferme automatiquement les batches dont toutes les sous-tâches sont DONE
# Lance: bash scripts/auto_batch_close.sh
# Idéalement ajouté en cron (ex: toutes les 30 min après les agents)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

python3 << 'PY'
import json
from datetime import datetime, timezone
from pathlib import Path

wb_path = Path('docs/orchestrator-ops/parallel-workstreams.json')
pq_path = Path('docs/orchestrator-ops/priority-queue.json')
wb = json.loads(wb_path.read_text())
pq = json.loads(pq_path.read_text())
ts = datetime.now(timezone.utc).isoformat()

tasks = wb.get('tasks', [])
closed = []
unlocked = []

# Grouper les tâches par batch parent (BATCH-NN)
from collections import defaultdict
by_batch = defaultdict(list)
for t in tasks:
    tid = t.get('id', '')
    parts = tid.split('-')
    if len(parts) == 3 and parts[0] == 'BATCH':
        parent = f"{parts[0]}-{parts[1]}"
        by_batch[parent].append(t)

# Vérifier si toutes les sous-tâches d'un batch sont DONE
for batch_id, subtasks in by_batch.items():
    if not subtasks:
        continue
    all_done = all(t.get('state') in ('DONE', 'CLOSED', 'PASS') for t in subtasks)
    if not all_done:
        continue

    # Chercher le batch parent dans la priority queue
    for item in pq.get('items', []):
        if item.get('id') == batch_id and item.get('state') not in ('CLOSED', 'DONE', 'PASS'):
            item['state'] = 'CLOSED'
            item['closed_at'] = ts
            item['closed_by'] = 'auto_batch_close'
            closed.append(batch_id)

            # Débloquer le batch suivant (BATCH-NN+1) si WAITING_DEP
            parts = batch_id.split('-')
            next_id = f"BATCH-{int(parts[1])+1:02d}"
            for next_item in pq.get('items', []):
                if next_item.get('id') == next_id and next_item.get('state') == 'WAITING_DEP':
                    next_item['state'] = 'READY'
                    next_item['updated_at'] = ts
                    unlocked.append(next_id)
            break

if closed or unlocked:
    pq_path.write_text(json.dumps(pq, indent=2, ensure_ascii=False))
    for b in closed:
        print(f'✅ CLOSED {b} (toutes sous-tâches DONE)')
    for b in unlocked:
        print(f'🔓 UNLOCKED {b} (WAITING_DEP → READY)')
else:
    print('ℹ️  Aucun batch à fermer automatiquement')
PY
