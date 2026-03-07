from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_RUNTIME_STATE_DIR = Path("logs-codex-runs/orchestrator-state")
CANONICAL_DOCS_DIR = Path("docs/operations/orchestrator")
LEGACY_DOCS_DIR = Path("docs/orchestrator-ops")
RUNTIME_STATE_FILE = "runtime-state.json"
VALID_LIFECYCLES = {"running", "paused", "maintenance"}


def runtime_state_root(root: Path) -> Path:
    token = str(os.environ.get("FC_ORCHESTRATOR_STATE_DIR", "")).strip()
    if token:
        path = Path(token).expanduser()
        return path if path.is_absolute() else (root / path)
    return root / DEFAULT_RUNTIME_STATE_DIR


def canonical_docs_root(root: Path) -> Path:
    return root / CANONICAL_DOCS_DIR


def legacy_docs_root(root: Path) -> Path:
    return root / LEGACY_DOCS_DIR


def orchestrator_read_candidates(root: Path, relative_path: str) -> list[Path]:
    rel = Path(str(relative_path or "").strip().lstrip("/"))
    candidates = [
        runtime_state_root(root) / rel,
        canonical_docs_root(root) / rel,
        legacy_docs_root(root) / rel,
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
    existing = [item for item in candidates if item.exists()]
    if existing:
        try:
            existing.sort(key=lambda item: float(item.stat().st_mtime), reverse=True)
        except Exception:
            pass
        return existing[0]
    return candidates[0]


def resolve_orchestrator_write_path(root: Path, relative_path: str, *, create_parent: bool = True) -> Path:
    path = runtime_state_root(root) / Path(str(relative_path or "").strip().lstrip("/"))
    if create_parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    return path


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
