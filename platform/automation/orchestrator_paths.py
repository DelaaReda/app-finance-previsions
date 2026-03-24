from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_RUNTIME_STATE_DIR = Path("logs-codex-runs/orchestrator-state")
CANONICAL_DOCS_DIR = Path("docs/operations/orchestrator")
RUNTIME_STATE_FILE = "runtime-state.json"
VALID_LIFECYCLES = {"running", "paused", "maintenance"}
LEGACY_RUNTIME_SUBDIR = Path("legacy")
LEGACY_BRIDGE_FILES = {
    "planner-subagents-registry.json",
    "planner-subagents-events.jsonl",
    "dynamic-workers-registry.json",
    "dynamic-workers-events.jsonl",
    "agent-message-bus.jsonl",
    "intent-registry.json",
}
LEGACY_BRIDGE_PREFIXES = (
    "planner-subagents-results/",
    "dynamic-workers-results/",
)
DOC_MIRROR_JSON_FILES = {
    "priority-queue.json",
    "parallel-workstreams.json",
    "state-reconcile-report.json",
}
CANONICAL_VM_ROOT = Path("/home/venom/analyse-financiere")
SHARED_VM_ROOT = Path("/home/venom/shared/analyse-financiere")


def _normalized_root(root: Path) -> Path:
    candidate = Path(root).expanduser()
    try:
        if str(candidate).startswith(str(SHARED_VM_ROOT)) and CANONICAL_VM_ROOT.exists():
            if (CANONICAL_VM_ROOT / "platform").is_dir() and (CANONICAL_VM_ROOT / "scripts").is_dir():
                return CANONICAL_VM_ROOT
    except Exception:
        pass
    return candidate


def runtime_state_root(root: Path) -> Path:
    normalized_root = _normalized_root(root)
    token = str(os.environ.get("FC_ORCHESTRATOR_STATE_DIR", "")).strip()
    if token:
        path = Path(token).expanduser()
        return path if path.is_absolute() else (normalized_root / path)
    return normalized_root / DEFAULT_RUNTIME_STATE_DIR


def canonical_docs_root(root: Path) -> Path:
    return _normalized_root(root) / CANONICAL_DOCS_DIR


def _runtime_relative_path(relative_path: str) -> Path:
    rel = Path(str(relative_path or "").strip().lstrip("/"))
    rel_posix = rel.as_posix()
    if rel_posix in LEGACY_BRIDGE_FILES or any(rel_posix.startswith(prefix) for prefix in LEGACY_BRIDGE_PREFIXES):
        return LEGACY_RUNTIME_SUBDIR / rel
    return rel


def orchestrator_read_candidates(root: Path, relative_path: str) -> list[Path]:
    rel = Path(str(relative_path or "").strip().lstrip("/"))
    runtime_rel = _runtime_relative_path(str(rel))
    candidates = [
        runtime_state_root(root) / runtime_rel,
        runtime_state_root(root) / rel,
        canonical_docs_root(root) / LEGACY_RUNTIME_SUBDIR / rel,
        canonical_docs_root(root) / rel,
    ]
    deduped: list[Path] = []
    seen: set[str] = set()
    for item in candidates:
        key = str(item)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def resolve_orchestrator_read_path(root: Path, relative_path: str) -> Path:
    candidates = orchestrator_read_candidates(root, relative_path)
    for item in candidates:
        if item.exists():
            return item
    return candidates[0]


def resolve_orchestrator_write_path(root: Path, relative_path: str, *, create_parent: bool = True) -> Path:
    path = runtime_state_root(root) / _runtime_relative_path(relative_path)
    if create_parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_orchestrator_json(
    root: Path,
    relative_path: str,
    payload: Any,
    *,
    mirror_docs: bool | None = None,
) -> Path:
    rel = Path(str(relative_path or "").strip().lstrip("/"))
    rendered = json.dumps(payload, ensure_ascii=True, indent=2) + "\n"

    runtime_path = resolve_orchestrator_write_path(root, str(rel))
    runtime_path.write_text(rendered, encoding="utf-8")

    should_mirror = mirror_docs if mirror_docs is not None else rel.as_posix() in DOC_MIRROR_JSON_FILES
    if should_mirror:
        seen: set[str] = {str(runtime_path)}
        for base in (canonical_docs_root(root),):
            mirror_path = base / rel
            key = str(mirror_path)
            if key in seen:
                continue
            seen.add(key)
            mirror_path.parent.mkdir(parents=True, exist_ok=True)
            mirror_path.write_text(rendered, encoding="utf-8")

    return runtime_path


def read_json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return None


def runtime_state_file(root: Path) -> Path:
    return resolve_orchestrator_write_path(root, RUNTIME_STATE_FILE)


def load_runtime_state(root: Path) -> dict[str, Any]:
    path = resolve_orchestrator_read_path(root, RUNTIME_STATE_FILE)
    payload = read_json_file(path)
    state = payload if isinstance(payload, dict) else {}
    lifecycle = str(state.get("lifecycle", "")).strip().lower()
    if lifecycle not in VALID_LIFECYCLES:
        lifecycle = "running"
    return {
        "lifecycle": lifecycle,
        "reason": str(state.get("reason", "inferred") or "inferred").strip() or "inferred",
        "operator_mode": str(state.get("operator_mode", "") or "").strip(),
        "execution_mode": str(state.get("execution_mode", "") or "").strip(),
        "source": str(state.get("source", "inferred") or "inferred").strip() or "inferred",
        "updated_at": str(state.get("updated_at", "") or "").strip(),
        "path": str(path),
    }


def persist_runtime_state(
    root: Path,
    *,
    lifecycle: str,
    reason: str,
    execution_mode: str = "",
    operator_mode: str = "",
    source: str = "manual",
) -> Path:
    lifecycle_token = str(lifecycle or "").strip().lower()
    if lifecycle_token not in VALID_LIFECYCLES:
        raise ValueError(f"invalid lifecycle: {lifecycle}")
    payload = {
        "lifecycle": lifecycle_token,
        "reason": str(reason or "none").strip() or "none",
        "operator_mode": str(operator_mode or "").strip(),
        "execution_mode": str(execution_mode or "").strip(),
        "source": str(source or "manual").strip() or "manual",
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    path = runtime_state_file(root)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    return path


def runtime_state_is_paused(root: Path) -> bool:
    return load_runtime_state(root).get("lifecycle") in {"paused", "maintenance"}
