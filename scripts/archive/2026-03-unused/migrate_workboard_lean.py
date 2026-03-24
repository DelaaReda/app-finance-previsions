#!/usr/bin/env python3
"""
LEGACY ONLY.

Ce script historique modifiait directement les projections runtime depuis des docs legacy.
Il est gelé: planning truth = Plane, runtime truth = SQLite, projections = compat seulement.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).parent.parent
WS_FILE = ROOT / "logs-codex-runs" / "orchestrator-state" / "parallel-workstreams.json"
PQ_FILE = ROOT / "logs-codex-runs" / "orchestrator-state" / "priority-queue.json"

NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# Mapping ancien → nouveau rôle
ROLE_MAP = {
    "backend_engineer": "dev",
    "frontend_engineer": "dev",
    "data_analyst": "dev",
    "integrator": "dev",
    "infra_engineer": "admin",
    "tester": "dev",
    "qa": "admin",
    "clawsentinel": "admin",
    "architect": "planner",
    "po": "planner",
    "scrum_master": "planner",
    "analyst": "planner",
}

def migrate_task(task: dict) -> dict:
    """Remap assigned_to to new consolidated role."""
    t = dict(task)
    old_role = t.get("assigned_to", "")
    t["assigned_to"] = ROLE_MAP.get(old_role, old_role)
    return t

def migrate_workboard():
    with open(WS_FILE) as f:
        ws = json.load(f)

    # Update roles section
    ws["roles"] = {
        "dev": {
            "wip_limit": 1,
            "can_edit": True,
            "focus": "full-stack dev: backend + frontend + data + self-QA"
        },
        "planner": {
            "wip_limit": 1,
            "can_edit": True,
            "focus": "vision + specs + batch planning + unblocking dev"
        },
        "admin": {
            "wip_limit": 1,
            "can_edit": True,
            "focus": "system health + rate limit management + service restarts"
        }
    }

    # Migrate all task assignments in streams
    for stream in ws.get("streams", []):
        if "tasks" in stream:
            stream["tasks"] = [migrate_task(t) for t in stream["tasks"]]

    # Add BATCH-05 open state clearly for dev
    for stream in ws.get("streams", []):
        if stream["id"] == "BATCH-05" and stream.get("state") not in ("DONE", "CLOSED"):
            stream["state"] = "OPEN"
            # Ensure dev has the task
            has_dev = any(t.get("assigned_to") == "dev" for t in stream.get("tasks", []))
            if not has_dev:
                stream.setdefault("tasks", []).append({
                    "id": "BATCH-05-DEV",
                    "assigned_to": "dev",
                    "status": "ready",
                    "has_work": True,
                    "description": "Implémenter /api/brief/daily + améliorer /api/copilot/ask avec contexte marché"
                })
            # Ensure planner has task
            has_planner = any(t.get("assigned_to") == "planner" for t in stream.get("tasks", []))
            if not has_planner:
                stream.setdefault("tasks", []).append({
                    "id": "BATCH-05-PLAN",
                    "assigned_to": "planner",
                    "status": "ready",
                    "has_work": True,
                    "description": "Valider livraison dev + ouvrir BATCH-06 quand BATCH-05 complété"
                })

    ws["updated_at"] = NOW
    ws["_migration"] = "lean-team-3-roles-2026-03-02"

    with open(WS_FILE, "w") as f:
        json.dump(ws, f, indent=2, ensure_ascii=False)
    print(f"✅ Workboard migré: {WS_FILE}")

def migrate_priority_queue():
    with open(PQ_FILE) as f:
        pq = json.load(f)

    # Remap owner_role
    for item in pq.get("items", []):
        old_role = item.get("owner_role", "")
        item["owner_role"] = ROLE_MAP.get(old_role, old_role)

    pq["updated_at"] = NOW
    with open(PQ_FILE, "w") as f:
        json.dump(pq, f, indent=2, ensure_ascii=False)
    print(f"✅ Priority queue migrée: {PQ_FILE}")

if __name__ == "__main__":
    raise SystemExit(
        "DEPRECATED: migrate_workboard_lean.py is legacy-only. "
        "Planning truth = Plane sync; runtime truth = SQLite; queue/workboard are compatibility projections."
    )
    migrate_workboard()
    migrate_priority_queue()
    print("\n✅ Migration lean team terminée.")
    print("Rôles actifs: dev | planner | admin")
    print("Lancez: bash scripts/setup_lean_team.sh pour appliquer le crontab")
