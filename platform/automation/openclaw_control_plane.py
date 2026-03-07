#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


CANONICAL_WORKSPACE = "/home/venom/analyse-financiere"
CANONICAL_PRIMARY_MODEL = "codex-cli/gpt-5.4"
OPENCLAW_MINIMAL_CODEX_CONFIG = """model = "{model}"
model_reasoning_effort = "{thinking}"

[features]
multi_agent = true
apps = true
js_repl = true
prevent_idle_sleep = true
"""
CANONICAL_PERSISTENT_AGENTS: dict[str, dict[str, Any]] = {
    "main": {},
    "planner": {
        "name": "Planner",
        "model": CANONICAL_PRIMARY_MODEL,
        "thinking": "high",
        "identity": {"name": "Planner", "theme": "planning"},
    },
    "adminapp-codex": {
        "name": "AdminApp Codex",
        "model": CANONICAL_PRIMARY_MODEL,
        "thinking": "high",
        "identity": {"name": "AdminApp Codex", "theme": "runtime"},
    },
    "clawsentinel": {
        "name": "ClawSentinel",
        "model": CANONICAL_PRIMARY_MODEL,
        "thinking": "high",
        "identity": {"name": "ClawSentinel", "theme": "safety"},
    },
}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _write_text_if_changed(path: Path, content: str) -> None:
    existing = ""
    if path.exists():
        existing = path.read_text(encoding="utf-8", errors="ignore")
    if existing == content:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _control_workspace(repo_root: str, agent_id: str, model: str, thinking: str) -> str:
    base = Path(repo_root) / "logs-codex-runs" / "openclaw-control-plane" / agent_id
    config_path = base / ".codex" / "config.toml"
    _write_text_if_changed(
        config_path,
        OPENCLAW_MINIMAL_CODEX_CONFIG.format(model=model, thinking=thinking),
    )
    return str(base)


def _canonical_agent_entry(agent_id: str, config_path: Path, repo_root: str, primary_model: str) -> dict[str, Any]:
    spec = CANONICAL_PERSISTENT_AGENTS[agent_id]
    if agent_id == "main":
        return {"id": "main"}
    workspace = _control_workspace(
        repo_root,
        agent_id,
        spec.get("model", primary_model),
        str(spec.get("thinking", "high") or "high"),
    )
    entry = {
        "id": agent_id,
        "name": spec["name"],
        "workspace": workspace,
        "agentDir": str(config_path.parent / "agents" / agent_id / "agent"),
        "model": spec.get("model", primary_model),
        "identity": spec["identity"],
    }
    return entry


def _sync_defaults(payload: dict[str, Any], workspace: str, primary_model: str) -> None:
    agents = payload.setdefault("agents", {})
    defaults = agents.setdefault("defaults", {})
    model_cfg = defaults.setdefault("model", {})
    model_cfg["primary"] = primary_model
    defaults["workspace"] = _control_workspace(workspace, "default", primary_model, "high")
    defaults.setdefault("maxConcurrent", 2)
    defaults.setdefault("subagents", {}).setdefault("maxConcurrent", 3)


def _sync_agent_list(payload: dict[str, Any], config_path: Path, workspace: str, primary_model: str) -> tuple[list[str], list[str]]:
    agents = payload.setdefault("agents", {})
    existing = agents.get("list", [])
    existing_ids = []
    if isinstance(existing, list):
        for item in existing:
            if isinstance(item, dict):
                agent_id = str(item.get("id", "")).strip()
                if agent_id:
                    existing_ids.append(agent_id)
    kept_ids = list(CANONICAL_PERSISTENT_AGENTS.keys())
    removed_ids = [agent_id for agent_id in existing_ids if agent_id and agent_id not in CANONICAL_PERSISTENT_AGENTS]
    agents["list"] = [
        _canonical_agent_entry(agent_id, config_path, workspace, primary_model)
        for agent_id in kept_ids
    ]
    return kept_ids, removed_ids


def _remove_agent_dirs(config_path: Path, agent_ids: list[str]) -> list[str]:
    removed: list[str] = []
    agents_root = config_path.parent / "agents"
    for agent_id in agent_ids:
        target = agents_root / agent_id
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
            removed.append(agent_id)
    return removed


def sync_control_plane(config_path: Path, workspace: str, primary_model: str, apply: bool, prune_dirs: bool, reset_kept_dirs: bool) -> dict[str, Any]:
    payload = _load_json(config_path)
    _sync_defaults(payload, workspace, primary_model)
    kept_ids, removed_ids = _sync_agent_list(payload, config_path, workspace, primary_model)
    removed_dirs: list[str] = []
    reset_dirs: list[str] = []
    if apply:
        backup = config_path.with_suffix(config_path.suffix + ".bak")
        if config_path.exists():
            backup.write_text(config_path.read_text(encoding="utf-8"), encoding="utf-8")
        _write_json(config_path, payload)
        if prune_dirs:
            removed_dirs = _remove_agent_dirs(config_path, removed_ids)
        if reset_kept_dirs:
            reset_dirs = _remove_agent_dirs(config_path, [agent_id for agent_id in kept_ids if agent_id != "main"])
    return {
        "ok": True,
        "config_path": str(config_path),
        "workspace": workspace,
        "primary_model": primary_model,
        "kept_ids": kept_ids,
        "removed_ids": removed_ids,
        "removed_dirs": removed_dirs,
        "reset_dirs": reset_dirs,
        "applied": apply,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Align OpenClaw control plane with planner-capability runtime.")
    parser.add_argument("--config", default=str(Path.home() / ".openclaw" / "openclaw.json"))
    parser.add_argument("--workspace", default=CANONICAL_WORKSPACE)
    parser.add_argument("--primary-model", default=CANONICAL_PRIMARY_MODEL)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--prune-dirs", action="store_true")
    parser.add_argument("--reset-kept-dirs", action="store_true")
    args = parser.parse_args()

    result = sync_control_plane(
        config_path=Path(args.config).expanduser(),
        workspace=str(args.workspace).strip() or CANONICAL_WORKSPACE,
        primary_model=str(args.primary_model).strip() or CANONICAL_PRIMARY_MODEL,
        apply=bool(args.apply),
        prune_dirs=bool(args.prune_dirs),
        reset_kept_dirs=bool(args.reset_kept_dirs),
    )
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
