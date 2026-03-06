#!/usr/bin/env bash

# Runtime context module (non-breaking extraction layer).
# Provides helper wrappers so cron_tmux_role_runner.sh can progressively
# migrate context construction out of the monolithic script.

runner_runtime_context_script() {
  local root="${1:-}"
  if [[ -n "$root" && -f "$root/platform/automation/role_runtime_context.py" ]]; then
    printf '%s\n' "$root/platform/automation/role_runtime_context.py"
    return 0
  fi
  printf '%s\n' "$root/scripts/role_runtime_context.py"
}

runner_runtime_context_field() {
  local context_line="${1:-}"
  local field="${2:-}"
  [[ -n "$field" ]] || return 0
  python3 - "$context_line" "$field" <<'PY'
import re
import sys
line = sys.argv[1] if len(sys.argv) > 1 else ""
field = sys.argv[2] if len(sys.argv) > 2 else ""
if not field:
    raise SystemExit(0)
m = re.search(rf"{re.escape(field)}=([^|]+)", line)
if m:
    print(m.group(1).strip())
PY
}
