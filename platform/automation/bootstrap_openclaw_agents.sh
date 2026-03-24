#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd -P)"
cd "$ROOT"

MODEL_CONFIG_FILE="${ROOT}/platform/config/lm_used_model_config.sh"
if [[ ! -f "$MODEL_CONFIG_FILE" ]]; then
  MODEL_CONFIG_FILE="${ROOT}/platform/config/model-config.sh"
fi
if [[ -f "$MODEL_CONFIG_FILE" ]]; then
  # shellcheck source=../platform/config/lm_used_model_config.sh
  source "$MODEL_CONFIG_FILE"
fi

CATALOG_FILE="${OPENCLAW_AGENT_CATALOG_FILE:-logs-codex-runs/orchestrator-state/openclaw-agent-catalog.json}"
WORKSPACE_DEFAULT="$ROOT"
MODEL_DEFAULT="${MODEL_DEFAULT:-${LM_USED_ROLE_MODEL:-${MODEL_CONFIG_ROLE_MODEL:-${MODEL_CONFIG_PARALLEL_ROLE_MODEL}}}}"
MEMORY_DIR="${OPENCLAW_AGENT_MEMORY_DIR:-$ROOT/memory/agents}"
APPLY=0
LINK_CRON=1
FULL_ACCESS=0

usage() {
  cat <<'EOF'
Usage: bootstrap_openclaw_agents.sh [options]

Options:
  --apply            Create/update agents and cron bindings (default: dry-run)
  --no-link-cron     Do not bind existing cron jobs to agent IDs
  --full-access      Apply permissive VM-test access policy (sandbox off + /** allowlist)
  --catalog <path>   Agent catalog JSON (default: logs-codex-runs/orchestrator-state/openclaw-agent-catalog.json)
  -h, --help         Show help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      APPLY=1
      shift
      ;;
    --no-link-cron)
      LINK_CRON=0
      shift
      ;;
    --full-access)
      FULL_ACCESS=1
      shift
      ;;
    --catalog)
      CATALOG_FILE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if ! command -v openclaw >/dev/null 2>&1; then
  echo "openclaw not found in PATH" >&2
  exit 5
fi
if [[ ! -f "$CATALOG_FILE" ]]; then
  echo "catalog not found: $CATALOG_FILE" >&2
  exit 6
fi

workspace="$(jq -r '.workspace // empty' "$CATALOG_FILE" 2>/dev/null || true)"
model_default="$MODEL_DEFAULT"
if [[ -z "$workspace" ]]; then
  workspace="$WORKSPACE_DEFAULT"
fi
if [[ -z "$model_default" ]]; then
  model_default="$MODEL_DEFAULT"
fi

mkdir -p "$MEMORY_DIR"

agents_json="$(openclaw agents list --json)"

agent_exists() {
  local id="$1"
  printf '%s' "$agents_json" | jq -e --arg id "$id" '.[] | select(.id==$id)' >/dev/null 2>&1
}

refresh_agents_json() {
  agents_json="$(openclaw agents list --json)"
}

ensure_memory_file() {
  local id="$1"
  local path="$MEMORY_DIR/${id}.md"
  if [[ -f "$path" ]]; then
    return 0
  fi
  cat > "$path" <<EOF
# Agent Memory: ${id}

- Role focus:
- Stable decisions:
- Useful commands:
- Recurring blockers:
- Handoff expectations:
EOF
}

ensure_agent() {
  local id="$1"
  local name="$2"
  local theme="$3"
  local model="$4"
  local exists=0

  if agent_exists "$id"; then
    exists=1
  fi

  if [[ "$exists" -eq 1 ]]; then
    echo "AGENT_EXISTS id=${id}"
  else
    echo "AGENT_CREATE id=${id} workspace=${workspace} model=${model} apply=${APPLY}"
    if [[ "$APPLY" -eq 1 ]]; then
      openclaw agents add "$id" --workspace "$workspace" --model "$model" --non-interactive --json >/dev/null
      refresh_agents_json
    fi
  fi

  ensure_memory_file "$id"

  if [[ "$APPLY" -eq 1 ]]; then
    openclaw agents set-identity --agent "$id" --name "$name" --theme "$theme" >/dev/null 2>&1 || true
  fi
}

cron_name_to_agent() {
  local name="$1"
  local prefix=""
  case "$name" in
    adminapp-codex-sync-*) echo "adminapp-codex"; return 0 ;;
    admin-agents-supervisor-*) echo "admin-agents"; return 0 ;;
  esac
  if [[ "$name" == *-tmux-* ]]; then
    prefix="${name%%-tmux-*}"
    echo "${prefix//-/_}"
    return 0
  fi
  if [[ "$name" == *-tmux-loop ]]; then
    prefix="${name%-tmux-loop}"
    echo "${prefix//-/_}"
    return 0
  fi
  echo ""
}

apply_full_access_policy() {
  local approvals_json=""
  local has_root=0
  local has_home=0

  if [[ "$APPLY" -eq 0 ]]; then
    echo "FULL_ACCESS_PLAN sandbox=off approvals_allowlist=[/**,/home/venom/**]"
    return 0
  fi

  openclaw config set agents.defaults.sandbox.mode off >/dev/null
  approvals_json="$(openclaw approvals get --json | jq '.file')"
  has_root="$(printf '%s' "$approvals_json" | jq -r '[.agents["*"].allowlist[]?.pattern] | index("/**") | if .==null then 0 else 1 end')"
  has_home="$(printf '%s' "$approvals_json" | jq -r '[.agents["*"].allowlist[]?.pattern] | index("/home/venom/**") | if .==null then 0 else 1 end')"
  if [[ "$has_root" != "1" ]]; then
    openclaw approvals allowlist add --agent "*" "/**" >/dev/null
  fi
  if [[ "$has_home" != "1" ]]; then
    openclaw approvals allowlist add --agent "*" "/home/venom/**" >/dev/null
  fi
  echo "FULL_ACCESS_APPLIED sandbox=off approvals_allowlist_updated=1"
}

# backup config only for apply mode
if [[ "$APPLY" -eq 1 ]]; then
  ts="$(date +%Y%m%d-%H%M%S)"
  cp /home/venom/.openclaw/openclaw.json "/home/venom/.openclaw/openclaw.json.backup-agents-${ts}"
fi

created=0
existing=0
while IFS='|' read -r id name theme model; do
  [[ -z "$id" ]] && continue
  [[ -z "$name" ]] && name="$id"
  [[ -z "$theme" ]] && theme="default"
  [[ -z "$model" ]] && model="$model_default"

  if agent_exists "$id"; then
    existing=$((existing + 1))
  else
    created=$((created + 1))
  fi

  ensure_agent "$id" "$name" "$theme" "$model"
done < <(jq -r --arg m "$model_default" '.agents[]? | select((.id // "") != "") | "\(.id)|\(.name // .id)|\(.theme // "default")|\(.model // $m)"' "$CATALOG_FILE" 2>/dev/null)

bound=0
if [[ "$LINK_CRON" -eq 1 ]]; then
  cron_json="$(openclaw cron list --json 2>/dev/null || echo '{"jobs":[]}')"
  while IFS='|' read -r job_id job_name job_agent; do
    [[ -z "$job_id" || -z "$job_name" ]] && continue
    target_agent="$(cron_name_to_agent "$job_name")"
    [[ -z "$target_agent" ]] && continue

    if ! agent_exists "$target_agent"; then
      echo "CRON_BIND_SKIP job=${job_name} reason=agent_missing target=${target_agent}"
      continue
    fi
    if [[ "$job_agent" == "$target_agent" ]]; then
      continue
    fi

    echo "CRON_BIND job=${job_name} id=${job_id} agent=${target_agent} apply=${APPLY}"
    if [[ "$APPLY" -eq 1 ]]; then
      openclaw cron edit "$job_id" --agent "$target_agent" >/dev/null
      bound=$((bound + 1))
    fi
  done < <(printf '%s' "$cron_json" | jq -r '.jobs[]? | "\(.id)|\(.name // "")|\(.agentId // "")"')
fi

if [[ "$FULL_ACCESS" -eq 1 ]]; then
  apply_full_access_policy
fi

echo "AGENT_BOOTSTRAP_SUMMARY apply=${APPLY} created=${created} existing=${existing} cron_bound=${bound} link_cron=${LINK_CRON} full_access=${FULL_ACCESS} catalog=${CATALOG_FILE}"
