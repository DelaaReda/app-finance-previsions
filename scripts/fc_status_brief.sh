#!/usr/bin/env bash
# fc_status_brief.sh — compact operator brief (read-only)
set -euo pipefail

BASE_URL="${FC_MONITOR_BASE_URL:-http://127.0.0.1:7779}"
TIMEOUT_S="${FC_STATUS_BRIEF_TIMEOUT_S:-4}"

status_json="$(curl -fsS --max-time "$TIMEOUT_S" "${BASE_URL%/}/api/status")" || {
  echo "Santé: monitor_unreachable (${BASE_URL%/}/api/status)"
  echo "Batches: unknown"
  echo "Agents: unknown"
  echo "Blocages: monitor_unreachable"
  echo "Lecture réelle: monitor indisponible, impossible d'établir l'état runtime."
  echo "Action recommandée: restaurer monitor puis relancer scripts/fc_health_check.sh."
  exit 1
}

python3 - "$status_json" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
health = str(payload.get("health", "UNKNOWN"))
fresh = payload.get("runtime_freshness", {}) if isinstance(payload.get("runtime_freshness"), dict) else {}
fresh_s = int(fresh.get("seconds", -1) or -1)
fresh_state = str(fresh.get("state", "unknown"))

queue = payload.get("queue", {}) if isinstance(payload.get("queue"), dict) else {}
ready = int(queue.get("ready", 0) or 0)
in_progress = int(queue.get("in_progress", 0) or 0)
waiting_dep = int(queue.get("waiting_dep", 0) or 0)
closed = int(queue.get("closed", 0) or 0)

agents = payload.get("agents", {}) if isinstance(payload.get("agents"), dict) else {}
core_roles = ("planner", "dev", "admin")
agent_chunks = []
blockers = []
for role in core_roles:
    a = agents.get(role, {}) if isinstance(agents.get(role), dict) else {}
    status = str(a.get("status", "UNKNOWN"))
    delta = str(a.get("delta", "NO_DATA"))
    blocker = str(a.get("blocker", "NONE"))
    agent_chunks.append(f"{role}:{status}/{delta}")
    if blocker and blocker != "NONE" and not bool(a.get("soft_blocker")):
        blockers.append(f"{role}:{blocker}")

po = payload.get("po_scrum_master", {}) if isinstance(payload.get("po_scrum_master"), dict) else {}
po_note = f"po_scrum_master:active={int(bool(po.get('active', False)))} lock_skip_streak={int(po.get('lock_skip_streak', 0) or 0)}"

integrity = payload.get("queue_workboard_integrity", {}) if isinstance(payload.get("queue_workboard_integrity"), dict) else {}
mismatch_count = int(integrity.get("mismatch_count", 0) or 0)
planner_quality = int(payload.get("planner_evidence_quality_score", 0) or 0)

if blockers:
    lecture = "runtime actif avec blocages hard sur lane core."
    action = "traiter le blocker core le plus récent puis relancer un cycle planner/dev/admin."
elif waiting_dep > 0 and ready == 0:
    lecture = "plateau dépendances: flux contraint par WAITING_DEP."
    action = "lancer dependency_recompute.sh (mode reconcile) puis vérifier mismatch queue/workboard."
elif ready > 0 and in_progress == 0:
    lecture = "capacité disponible: items READY non consommés."
    action = "forcer claim sur l’item READY prioritaire (planner/dev selon lane)."
else:
    lecture = "orchestration en flux nominal avec progression active."
    action = "poursuivre le cycle normal et surveiller qualité planner + sync."

print(f"Santé: {health} · freshness={fresh_state}/{fresh_s}s")
print(f"Batches: ready={ready} in_progress={in_progress} waiting_dep={waiting_dep} closed={closed}")
print(f"Agents: {' | '.join(agent_chunks)} | {po_note}")
print(f"Blocages: {', '.join(blockers) if blockers else 'none'} · mismatch_count={mismatch_count} · planner_quality={planner_quality}")
print(f"Lecture réelle: {lecture}")
print(f"Action recommandée: {action}")
PY
