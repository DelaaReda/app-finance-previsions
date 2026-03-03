#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  claude_desktop_new_chat.sh [--prompt "text"] [message words...] [--dry-run] [--gpu-off] [--fresh-profile]

Examples:
  claude_desktop_new_chat.sh --prompt "Plan de trading pour aujourd'hui"
  claude_desktop_new_chat.sh "Nouveau chat test"
  claude_desktop_new_chat.sh --dry-run "bonjour"
  claude_desktop_new_chat.sh --gpu-off --fresh-profile "test login"
EOF
}

prompt=""
dry_run=0
gpu_off=0
fresh_profile=0

while (($#)); do
  case "$1" in
    -p|--prompt)
      shift
      if (($# == 0)); then
        echo "Missing value for --prompt" >&2
        exit 2
      fi
      prompt="$1"
      ;;
    --dry-run)
      dry_run=1
      ;;
    --gpu-off)
      gpu_off=1
      ;;
    --fresh-profile)
      fresh_profile=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      break
      ;;
  esac
  shift
done

if (($# > 0)); then
  if [[ -n "$prompt" ]]; then
    prompt="$prompt $*"
  else
    prompt="$*"
  fi
fi

if ! command -v claude-desktop >/dev/null 2>&1; then
  echo "claude-desktop is not installed or not in PATH" >&2
  exit 127
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required for URL encoding but was not found in PATH" >&2
  exit 127
fi

uri="claude://claude.ai/new"
if [[ -n "$prompt" ]]; then
  encoded_prompt="$(printf '%s' "$prompt" | jq -sRr @uri)"
  uri="${uri}?q=${encoded_prompt}"
fi

if ((dry_run)); then
  printf '%s\n' "$uri"
  exit 0
fi

if ((gpu_off)); then
  electron_bin="/usr/lib/claude-desktop/node_modules/electron/dist/electron"
  app_asar="/usr/lib/claude-desktop/node_modules/electron/dist/resources/app.asar"
  if [[ ! -x "$electron_bin" || ! -f "$app_asar" ]]; then
    echo "Could not find electron/app.asar for --gpu-off mode" >&2
    exit 127
  fi
  cmd=(
    "$electron_bin"
    --disable-features=CustomTitlebar
    --no-sandbox
    --ozone-platform=x11
    --disable-gpu
  )
  if ((fresh_profile)); then
    cmd+=(--user-data-dir=/tmp/claude-fresh-profile)
  fi
  cmd+=("$app_asar" "$uri")
  exec "${cmd[@]}"
fi

exec claude-desktop "$uri"
