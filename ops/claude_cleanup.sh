#!/usr/bin/env bash
set -euo pipefail

# Claude Code (Anthropic CLI) cleanup helper (safe by default)
# - Dry-run by default (prints what would be done)
# - Use -y to actually perform removals
#
# Usage:
#   chmod +x ops/claude_cleanup.sh
#   ./ops/claude_cleanup.sh          # dry-run
#   ./ops/claude_cleanup.sh -y       # apply changes

APPLY=0
if [[ "${1:-}" == "-y" || "${1:-}" == "--yes" ]]; then
  APPLY=1
fi

say() { printf "[claude-cleanup] %s\n" "$*"; }
do_or_echo() {
  if [[ $APPLY -eq 1 ]]; then eval "$1"; else say "DRY: $1"; fi
}

say "Scanning environment …"
command -v claude >/dev/null 2>&1 && say "Found 'claude' in PATH: $(command -v claude)" || say "'claude' not found in PATH"

say "Node/npm info (for global uninstall attempts):"
command -v node >/dev/null 2>&1 && node -v || say "node not found"
command -v npm  >/dev/null 2>&1 && npm -v  || say "npm not found"

say "Checking npm globals for @anthropic-ai/claude-code …"
if command -v npm >/dev/null 2>&1; then
  (npm ls -g --depth=0 2>/dev/null | grep -i "@anthropic-ai/claude-code") && FOUND_NPM=1 || FOUND_NPM=0
else
  FOUND_NPM=0
fi

if [[ $FOUND_NPM -eq 1 ]]; then
  say "Preparing to npm uninstall -g @anthropic-ai/claude-code"
  do_or_echo "npm uninstall -g @anthropic-ai/claude-code || true"
else
  say "Package not listed in npm globals (may be installed via yarn/pnpm or npx cache)."
fi

say "Attempting yarn/pnpm global removals (harmless if not installed) …"
command -v yarn >/dev/null 2>&1 && do_or_echo "yarn global remove @anthropic-ai/claude-code || true" || true
command -v pnpm >/dev/null 2>&1 && do_or_echo "pnpm remove -g @anthropic-ai/claude-code || true" || true

say "Removing leftover binary link if present …"
if command -v npm >/dev/null 2>&1; then
  BIN_DIR=$(npm bin -g 2>/dev/null || true)
  if [[ -n "${BIN_DIR}" && -e "${BIN_DIR}/claude" ]]; then
    do_or_echo "rm -f '${BIN_DIR}/claude'"
  fi
fi

say "Cleaning npm/npx caches (safe) …"
command -v npm >/dev/null 2>&1 && do_or_echo "npm cache clean --force || true"
do_or_echo "rm -rf ~/.npm/_npx ~/.npm/_cacache || true"

say "Removing local configs/tokens if any …"
for p in ~/.claude ~/.claude-code ~/.config/claude ~/.config/claude-code ~/.config/anthropic ~/.anthropic; do
  if [[ -e $p ]]; then do_or_echo "rm -rf '$p'"; fi
done

say "Killing running TUI/processes if any …"
do_or_echo "pkill -f 'claude' || true"

say "Environment variables (session) …"
if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then say "ANTHROPIC_API_KEY is set in this session (will unset if APPLY)."; fi
if [[ -n "${OPENROUTER_API_KEY:-}" ]]; then say "OPENROUTER_API_KEY is set in this session (will unset if APPLY)."; fi
[[ $APPLY -eq 1 ]] && unset ANTHROPIC_API_KEY OPENROUTER_API_KEY || true

say "Search hints for dotfiles (manual edit recommended):"
for rc in ~/.zshrc ~/.bashrc ~/.bash_profile; do
  [[ -e $rc ]] && (grep -nE 'ANTHROPIC_API_KEY|OPENROUTER_API_KEY' "$rc" || true)
done
say "If matches above, edit the files and remove the export lines, then 'source ~/.zshrc' (or restart terminal)."

say "Verification checklist:"
say " - 'command -v claude' should be empty"
say " - 'env | grep -E \"ANTHROPIC|OPENROUTER\"' should be empty"
say " - Starting the CLI should fail (or not exist) — expected after cleanup"

if [[ $APPLY -eq 1 ]]; then
  say "Cleanup complete."
else
  say "DRY-RUN complete. Re-run with -y to apply."
fi

