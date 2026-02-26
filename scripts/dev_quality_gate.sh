#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

MODE="changed"
STRICT=0
RUN_PRECOMMIT=1

usage() {
  cat <<'EOF'
Usage: dev_quality_gate.sh [--staged|--changed|--all] [--strict] [--no-pre-commit]

Lightweight local quality gate that works even when optional tools are missing.

Modes:
  --staged   Only staged files
  --changed  Tracked files changed vs HEAD (default)
  --all      All tracked files

Checks:
  - Python syntax: python3 -m py_compile
  - Shell syntax:  bash -n
  - Optional shell lint: shellcheck (if installed)
  - Optional pre-commit: pre-commit run --files ... (if installed, unless --no-pre-commit)

Exit policy:
  - syntax failures always fail.
  - missing optional tools only warn, unless --strict.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --staged)
      MODE="staged"
      shift
      ;;
    --changed)
      MODE="changed"
      shift
      ;;
    --all)
      MODE="all"
      shift
      ;;
    --strict)
      STRICT=1
      shift
      ;;
    --no-pre-commit)
      RUN_PRECOMMIT=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! command -v git >/dev/null 2>&1; then
  echo "QUALITY_SUMMARY mode=${MODE} py=0 sh=0 syntax_fail=0 shellcheck_fail=0 warnings=1 verdict=BLOCKED reason=git_missing"
  exit 5
fi

case "$MODE" in
  staged)
    file_list="$(git diff --cached --name-only --diff-filter=ACMR)"
    ;;
  changed)
    file_list="$(git diff --name-only --diff-filter=ACMR HEAD --)"
    ;;
  all)
    file_list="$(git ls-files)"
    ;;
  *)
    echo "QUALITY_SUMMARY mode=${MODE} py=0 sh=0 syntax_fail=0 shellcheck_fail=0 warnings=1 verdict=BLOCKED reason=mode_invalid"
    exit 2
    ;;
esac

py_files="$(printf '%s\n' "$file_list" | rg '\.py$' || true)"
sh_files="$(printf '%s\n' "$file_list" | rg '\.sh$' || true)"

py_checked=0
sh_checked=0
syntax_fail=0
shellcheck_fail=0
warnings=0

if [[ -n "$py_files" ]]; then
  if ! command -v python3 >/dev/null 2>&1; then
    echo "QUALITY_WARN python3_missing"
    warnings=$((warnings + 1))
    syntax_fail=$((syntax_fail + 1))
  else
    while IFS= read -r f; do
      [[ -z "$f" || ! -f "$f" ]] && continue
      py_checked=$((py_checked + 1))
      if python3 -m py_compile "$f" >/dev/null 2>&1; then
        echo "QUALITY_OK py_compile file=$f"
      else
        syntax_fail=$((syntax_fail + 1))
        echo "QUALITY_FAIL py_compile file=$f"
      fi
    done <<< "$py_files"
  fi
fi

if [[ -n "$sh_files" ]]; then
  while IFS= read -r f; do
    [[ -z "$f" || ! -f "$f" ]] && continue
    sh_checked=$((sh_checked + 1))
    if bash -n "$f" >/dev/null 2>&1; then
      echo "QUALITY_OK bash_syntax file=$f"
    else
      syntax_fail=$((syntax_fail + 1))
      echo "QUALITY_FAIL bash_syntax file=$f"
    fi
  done <<< "$sh_files"

  if command -v shellcheck >/dev/null 2>&1; then
    while IFS= read -r f; do
      [[ -z "$f" || ! -f "$f" ]] && continue
      if shellcheck "$f" >/dev/null 2>&1; then
        echo "QUALITY_OK shellcheck file=$f"
      else
        shellcheck_fail=$((shellcheck_fail + 1))
        echo "QUALITY_FAIL shellcheck file=$f"
      fi
    done <<< "$sh_files"
  else
    echo "QUALITY_WARN shellcheck_missing"
    warnings=$((warnings + 1))
  fi
fi

if [[ "$RUN_PRECOMMIT" -eq 1 ]]; then
  if command -v pre-commit >/dev/null 2>&1; then
    if [[ -n "$file_list" ]]; then
      if pre-commit run --files $file_list >/dev/null 2>&1; then
        echo "QUALITY_OK pre_commit"
      else
        echo "QUALITY_FAIL pre_commit"
        syntax_fail=$((syntax_fail + 1))
      fi
    fi
  else
    echo "QUALITY_WARN pre_commit_missing"
    warnings=$((warnings + 1))
  fi
fi

verdict="PASS"
if [[ "$syntax_fail" -gt 0 || "$shellcheck_fail" -gt 0 ]]; then
  verdict="BLOCKED"
elif [[ "$STRICT" -eq 1 && "$warnings" -gt 0 ]]; then
  verdict="BLOCKED"
fi

echo "QUALITY_SUMMARY mode=${MODE} py=${py_checked} sh=${sh_checked} syntax_fail=${syntax_fail} shellcheck_fail=${shellcheck_fail} warnings=${warnings} strict=${STRICT} verdict=${verdict}"
if [[ "$verdict" != "PASS" ]]; then
  exit 9
fi
exit 0
