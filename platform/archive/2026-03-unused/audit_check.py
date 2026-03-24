#!/usr/bin/env python3
"""Audit checks: symlinks, JSON configs, memory structure."""

import os
import json
from pathlib import Path


def resolve_workspace_root() -> Path:
    env_root = os.environ.get("FC_WORKSPACE_ROOT", "").strip()
    if env_root:
        cand = Path(env_root).expanduser()
        if cand.exists():
            return cand
    # platform/scripts/audit_check.py -> workspace root is two levels up
    return Path(__file__).resolve().parents[2]


ROOT = resolve_workspace_root()
os.chdir(ROOT)

# Check 1: Broken symlinks
print("=== SYMLINK VALIDATION ===\n")
broken = []
for item in Path(".").rglob("*"):
    if item.is_symlink() and not item.resolve().exists():
        broken.append(str(item))

if broken:
    print(f"BROKEN SYMLINKS: {len(broken)}")
    for b in sorted(broken)[:10]:
        print(f"  - {b}")
else:
    print("✓ No broken symlinks found")

# Check 2: JSON validity
print("\n=== JSON CONFIG VALIDATION ===\n")
json_files = [
    "logs-codex-runs/orchestrator-state/priority-queue.json",
    "logs-codex-runs/orchestrator-state/parallel-workstreams.json",
    "platform/config/llm-models.json",
]

for jf in json_files:
    if Path(jf).exists():
        try:
            with open(jf) as f:
                json.load(f)
            print(f"✓ {jf}")
        except Exception as e:
            print(f"✗ {jf}: {str(e)[:50]}")
    else:
        print(f"⚠ {jf} (missing)")

# Check 3: Memory structure
print("\n=== MEMORY STRUCTURE ===\n")
memory_daily = len(list(Path("memory").glob("2026-*.md")))
memory_agents = len(list(Path("memory/agents").glob("*.md"))) if Path("memory/agents").exists() else 0
print(f"Daily memory files: {memory_daily}")
print(f"Role agent memories: {memory_agents}")

# Check 4: Key files status
print("\n=== KEY FILES STATUS ===\n")
key_files = [
    ("SOUL.md", "Identity"),
    ("MEMORY.md", "Long-term memory"),
    ("scripts/cron_tmux_role_runner.sh", "Agent runner"),
    ("docs/ops/ROLE_MEMORY_STRATEGY_3DAY.md", "3-day strategy"),
]

for fname, desc in key_files:
    exists = "✓" if Path(fname).exists() else "✗"
    print(f"{exists} {fname:50} ({desc})")

print("\nAudit complete.")
