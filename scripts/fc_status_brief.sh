#!/usr/bin/env bash
# fc_status_brief.sh — compact operator brief (read-only)
set -euo pipefail

BASE_URL="${FC_MONITOR_BASE_URL:-http://127.0.0.1:7779}"
TIMEOUT_S="${FC_STATUS_BRIEF_TIMEOUT_S:-15}"
STATUS_FILE="$(mktemp)"
STATUS_ENDPOINT="${FC_STATUS_BRIEF_ENDPOINT:-/api/status?lite=1}"

cleanup() {
  rm -f "$STATUS_FILE"
}
trap cleanup EXIT

curl -fsS --max-time "$TIMEOUT_S" "${BASE_URL%/}${STATUS_ENDPOINT}" -o "$STATUS_FILE" || {
  echo "Santé: monitor_unreachable (${BASE_URL%/}${STATUS_ENDPOINT})"
  echo "Batches: unknown"
  echo "Agents: unknown"
  echo "Blocages: monitor_unreachable"
  echo "Lecture réelle: monitor indisponible, impossible d'établir l'état runtime."
  echo "Action recommandée: restaurer monitor puis relancer scripts/fc_health_check.sh."
  exit 1
}

python3 - "$STATUS_FILE" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
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
execution_mode = str(payload.get("execution_mode", "unknown"))
core_roles = payload.get("core_roles", [])
if not isinstance(core_roles, list) or not core_roles:
    core_roles = ["planner", "dev", "admin"]
planner_subagents = payload.get("planner_subagents", {}) if isinstance(payload.get("planner_subagents"), dict) else {}
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

subagent_note = ""
if execution_mode == "planner_experimental":
    active_count = int(planner_subagents.get("active_count", 0) or 0)
    managed_roles = planner_subagents.get("managed_roles", [])
    if not isinstance(managed_roles, list):
        managed_roles = []
    subagent_note = f"planner_subagents:active={active_count} managed={','.join(managed_roles) if managed_roles else 'none'}"

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
    action = "forcer l’absorption de l’item READY prioritaire via planner ou délégation planner-owned."
else:
    lecture = "orchestration en flux nominal avec progression active."
    action = "poursuivre le cycle normal et surveiller qualité planner + sync."

print(f"Santé: {health} · mode={execution_mode} · freshness={fresh_state}/{fresh_s}s")
print(f"Batches: ready={ready} in_progress={in_progress} waiting_dep={waiting_dep} closed={closed}")
agent_line = f"Agents: {' | '.join(agent_chunks)}"
if subagent_note:
    agent_line += f" | {subagent_note}"
print(agent_line)
print(f"Blocages: {', '.join(blockers) if blockers else 'none'} · mismatch_count={mismatch_count} · planner_quality={planner_quality}")
print(f"Lecture réelle: {lecture}")
print(f"Action recommandée: {action}")
PY
