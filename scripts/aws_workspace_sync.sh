#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

MODE="push"
DRY_RUN=0
DELETE_REMOTE=1
SYNC_HOST="${AWS_SYNC_HOST:-}"
SYNC_USER="${AWS_SYNC_USER:-ubuntu}"
SYNC_KEY="${AWS_SYNC_KEY:-$HOME/.ssh/id_aws_lightsail}"
SYNC_DEST="${AWS_SYNC_DEST:-/home/${SYNC_USER}/analyse-financiere}"

usage() {
  cat <<EOF
Usage:
  $(basename "$0") [push|pull] [--dry-run] [--no-delete] [--host HOST] [--user USER] [--key PATH] [--dest PATH]

Examples:
  AWS_SYNC_HOST=1.2.3.4 $(basename "$0")
  $(basename "$0") push --host 1.2.3.4
  $(basename "$0") pull --host ec2-public-ip

Defaults:
  mode      = push
  user      = ${SYNC_USER}
  key       = ${SYNC_KEY}
  dest      = ${SYNC_DEST}
  delete    = enabled on push

This sync mirrors the whole workspace directory to AWS, with only minimal macOS junk exclusions.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    push|pull)
      MODE="$1"
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --no-delete)
      DELETE_REMOTE=0
      shift
      ;;
    --host)
      SYNC_HOST="${2:-}"
      shift 2
      ;;
    --user)
      SYNC_USER="${2:-}"
      shift 2
      ;;
    --key)
      SYNC_KEY="${2:-}"
      shift 2
      ;;
    --dest)
      SYNC_DEST="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "${SYNC_HOST}" ]]; then
  echo "AWS sync host is required. Set AWS_SYNC_HOST or pass --host." >&2
  exit 1
fi

if [[ ! -f "${SYNC_KEY}" ]]; then
  echo "SSH key not found: ${SYNC_KEY}" >&2
  exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo "rsync is required but not installed." >&2
  exit 1
fi

SSH_CMD=(
  ssh
  -i "${SYNC_KEY}"
  -o StrictHostKeyChecking=accept-new
  -o ServerAliveInterval=30
  -o ServerAliveCountMax=3
)

RSYNC_CMD=(
  rsync
  -az
  --human-readable
  --partial
  --progress
  --stats
  --exclude=.DS_Store
  --exclude='._*'
  -e "$(printf '%q ' "${SSH_CMD[@]}")"
)

if [[ "${DRY_RUN}" == "1" ]]; then
  RSYNC_CMD+=(--dry-run)
fi

if [[ "${MODE}" == "push" ]]; then
  if [[ "${DELETE_REMOTE}" == "1" ]]; then
    RSYNC_CMD+=(--delete)
  fi
  "${SSH_CMD[@]}" "${SYNC_USER}@${SYNC_HOST}" "mkdir -p '${SYNC_DEST}'"
  echo "Sync push: ${WORKSPACE_ROOT} -> ${SYNC_USER}@${SYNC_HOST}:${SYNC_DEST}"
  "${RSYNC_CMD[@]}" "${WORKSPACE_ROOT}/" "${SYNC_USER}@${SYNC_HOST}:${SYNC_DEST}/"
else
  echo "Sync pull: ${SYNC_USER}@${SYNC_HOST}:${SYNC_DEST} -> ${WORKSPACE_ROOT}"
  "${RSYNC_CMD[@]}" "${SYNC_USER}@${SYNC_HOST}:${SYNC_DEST}/" "${WORKSPACE_ROOT}/"
fi
