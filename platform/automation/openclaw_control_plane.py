#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


CANONICAL_WORKSPACE = "/home/venom/analyse-financiere"
CANONICAL_MAIN_WORKSPACE = "/home/venom"
CANONICAL_PRIMARY_MODEL = "codex-cli/gpt-5.4"
CANONICAL_MAIN_MODEL = "codex-cli-main/gpt-5.4"
CANONICAL_DEFAULT_THINKING = "xhigh"
CANONICAL_OWNER_E164 = "+14389799898"
CANONICAL_CODEX_CLI_BACKEND = {
    "command": "codex",
    "args": [
        "exec",
        "--json",
        "--sandbox",
        "read-only",
        "--skip-git-repo-check",
    ],
    "resumeArgs": [
        "exec",
        "resume",
        "{sessionId}",
        "--skip-git-repo-check",
    ],
    "output": "jsonl",
    "resumeOutput": "text",
    "input": "arg",
    "modelArg": "--model",
    "sessionIdFields": ["thread_id"],
    "sessionMode": "existing",
    "imageArg": "--image",
    "imageMode": "repeat",
    "serialize": True,
}
CANONICAL_MAIN_CODEX_CLI_BACKEND = {
    "command": "codex",
    "args": [
        "exec",
        "--json",
        "--dangerously-bypass-approvals-and-sandbox",
        "--skip-git-repo-check",
    ],
    "resumeArgs": [
        "exec",
        "resume",
        "{sessionId}",
        "--dangerously-bypass-approvals-and-sandbox",
        "--skip-git-repo-check",
    ],
    "output": "jsonl",
    "resumeOutput": "text",
    "input": "arg",
    "modelArg": "--model",
    "sessionIdFields": ["thread_id"],
    "sessionMode": "existing",
    "imageArg": "--image",
    "imageMode": "repeat",
    "serialize": True,
}
CANONICAL_MAIN_MEMORY_EXTRA_PATHS = [
    "/home/venom/analyse-financiere/SOUL.md",
    "/home/venom/analyse-financiere/USER.md",
    "/home/venom/analyse-financiere/MEMORY.md",
    "/home/venom/analyse-financiere/memory",
    "/home/venom/analyse-financiere/docs",
    "/home/venom/analyse-financiere/docs/ops",
    "/home/venom/analyse-financiere/docs/operations/orchestrator",
    "/home/venom/.openclaw/workspace/memory",
]
OPENCLAW_MINIMAL_CODEX_CONFIG = """model = "{model}"
model_reasoning_effort = "{thinking}"

[features]
multi_agent = true
apps = true
js_repl = true
prevent_idle_sleep = true
"""
CANONICAL_PERSISTENT_AGENTS: dict[str, dict[str, Any]] = {
    "main": {
        "name": "Main",
        "model": CANONICAL_MAIN_MODEL,
        "workspace": CANONICAL_MAIN_WORKSPACE,
        "tools": {
            "exec": {"host": "gateway", "security": "full", "ask": "off"},
        },
        "sandbox": {
            "mode": "off",
            "browser": {"autoStart": True, "autoStartTimeoutMs": 30000},
        },
        "memorySearch": {
            "enabled": True,
            "sources": ["memory", "sessions"],
            "extraPaths": CANONICAL_MAIN_MEMORY_EXTRA_PATHS,
        },
    },
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
        return {
            "id": "main",
            "default": True,
            "name": spec.get("name", "Main"),
            "model": spec.get("model", primary_model),
            "workspace": spec.get("workspace", CANONICAL_MAIN_WORKSPACE),
            "tools": spec.get("tools", {}),
            "sandbox": spec.get("sandbox", {}),
            "memorySearch": spec.get("memorySearch", {}),
        }
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
    defaults["thinkingDefault"] = CANONICAL_DEFAULT_THINKING
    cli_backends = defaults.setdefault("cliBackends", {})
    cli_backends["codex-cli"] = json.loads(json.dumps(CANONICAL_CODEX_CLI_BACKEND))
    cli_backends["codex-cli-main"] = json.loads(json.dumps(CANONICAL_MAIN_CODEX_CLI_BACKEND))


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


def _sync_channels(payload: dict[str, Any]) -> None:
    channels = payload.setdefault("channels", {})
    whatsapp = channels.setdefault("whatsapp", {})
    whatsapp["enabled"] = True
    whatsapp.setdefault("dmPolicy", "allowlist")
    whatsapp.setdefault("groupPolicy", "allowlist")
    whatsapp.setdefault("selfChatMode", True)
    whatsapp.setdefault("debounceMs", 0)
    whatsapp.setdefault("mediaMaxMb", 50)
    allow_from = [str(item).strip() for item in whatsapp.get("allowFrom", []) if str(item).strip()]
    if CANONICAL_OWNER_E164 not in allow_from:
        allow_from.append(CANONICAL_OWNER_E164)
    whatsapp["allowFrom"] = allow_from
    group_allow_from = [str(item).strip() for item in whatsapp.get("groupAllowFrom", []) if str(item).strip()]
    if CANONICAL_OWNER_E164 not in group_allow_from:
        group_allow_from.append(CANONICAL_OWNER_E164)
    whatsapp["groupAllowFrom"] = group_allow_from


def _remove_agent_dirs(config_path: Path, agent_ids: list[str]) -> list[str]:
    removed: list[str] = []
    agents_root = config_path.parent / "agents"
    for agent_id in agent_ids:
        target = agents_root / agent_id
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
            removed.append(agent_id)
    return removed


def validate_bridge(agent_id: str, timeout_seconds: int) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    env = dict(os.environ)
    desired = str(env.get("OPENCLAW_NODE_OPTIONS", "")).strip() or "--max-old-space-size=1536 --max-semi-space-size=64"
    existing = str(env.get("NODE_OPTIONS", "")).strip()
    if desired not in existing:
        env["NODE_OPTIONS"] = f"{existing} {desired}".strip()
    for index in range(2):
        proc = subprocess.run(
            [
                "openclaw",
                "agent",
                "--agent",
                agent_id,
                "--json",
                "--thinking",
                "low",
                "--timeout",
                str(max(30, timeout_seconds)),
                "--message",
                "Reply with exactly OK",
            ],
            text=True,
            capture_output=True,
            check=False,
            env=env,
            timeout=max(45, timeout_seconds + 15),
        )
        attempts.append(
            {
                "attempt": index + 1,
                "rc": proc.returncode,
                "stdout": (proc.stdout or "").strip()[:600],
                "stderr": (proc.stderr or "").strip()[:600],
            }
        )
    ok = all(item["rc"] == 0 and "OK" in item["stdout"] for item in attempts)
    return {"ok": ok, "agent_id": agent_id, "attempts": attempts}


def sync_control_plane(config_path: Path, workspace: str, primary_model: str, apply: bool, prune_dirs: bool, reset_kept_dirs: bool) -> dict[str, Any]:
    payload = _load_json(config_path)
    _sync_defaults(payload, workspace, primary_model)
    kept_ids, removed_ids = _sync_agent_list(payload, config_path, workspace, primary_model)
    _sync_channels(payload)
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
    parser.add_argument("--validate-bridge", action="store_true")
    parser.add_argument("--validate-agent", default="planner")
    parser.add_argument("--validate-timeout", type=int, default=60)
    args = parser.parse_args()

    result = sync_control_plane(
        config_path=Path(args.config).expanduser(),
        workspace=str(args.workspace).strip() or CANONICAL_WORKSPACE,
        primary_model=str(args.primary_model).strip() or CANONICAL_PRIMARY_MODEL,
        apply=bool(args.apply),
        prune_dirs=bool(args.prune_dirs),
        reset_kept_dirs=bool(args.reset_kept_dirs),
    )
    if args.validate_bridge:
        result["bridge_validation"] = validate_bridge(
            agent_id=str(args.validate_agent).strip() or "planner",
            timeout_seconds=max(15, int(args.validate_timeout)),
        )
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
