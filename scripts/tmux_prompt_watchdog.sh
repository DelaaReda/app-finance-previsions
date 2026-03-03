#!/usr/bin/env bash
# tmux_prompt_watchdog.sh — Détecte et dismiss les prompts interactifs bloquants
# Cron: */2 * * * * (toutes les 2 min)
# Prompts gérés:
#   - "Approaching rate limits / Switch model?" → garde le modèle actuel
#   - "Trust this project?" → accepte
#   - "Press enter to confirm or esc" → confirme avec Enter

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
LOG="${TMUX_PROMPT_WATCHDOG_LOG:-$ROOT/logs-codex-runs/tmux-watchdog.log}"
mkdir -p "$(dirname "$LOG")"

ts() { date '+%Y-%m-%dT%H:%M:%S'; }

DISMISSED=0

for session in $(tmux list-sessions -F '#{session_name}' 2>/dev/null); do
  capture=$(tmux capture-pane -t "$session" -p 2>/dev/null || true)
  [[ -z "$capture" ]] && continue

  # Rate limit switch model menu
  if echo "$capture" | grep -qE "Approaching rate limits|Switch to .* for lower credit"; then
    echo "$(ts) [DISMISS] rate_limit_menu in $session → sending 2 (keep model)" >> "$LOG"
    tmux send-keys -t "$session" "2" Enter 2>/dev/null || true
    DISMISSED=$((DISMISSED + 1))
    sleep 1

  # "Press enter to confirm" generic confirm
  elif echo "$capture" | grep -qE "Press enter to confirm or esc to go back"; then
    echo "$(ts) [DISMISS] confirm_prompt in $session → sending Enter" >> "$LOG"
    tmux send-keys -t "$session" "" Enter 2>/dev/null || true
    DISMISSED=$((DISMISSED + 1))
    sleep 1

  # Trust project prompt
  elif echo "$capture" | grep -qE "Trust this project|Allow all file operations|trust_level.*trusted"; then
    echo "$(ts) [DISMISS] trust_prompt in $session → sending 1 (trust)" >> "$LOG"
    tmux send-keys -t "$session" "1" Enter 2>/dev/null || true
    DISMISSED=$((DISMISSED + 1))
    sleep 1

  # Session vide/zombie depuis > 5 min (aucune activité)
  elif echo "$capture" | grep -qE "^\s*$" && [[ ${#capture} -lt 50 ]]; then
    echo "$(ts) [INFO] empty session $session — skipping" >> "$LOG"
  fi
done

if [[ "$DISMISSED" -gt 0 ]]; then
  echo "$(ts) [DONE] dismissed $DISMISSED prompt(s)" >> "$LOG"
fi
