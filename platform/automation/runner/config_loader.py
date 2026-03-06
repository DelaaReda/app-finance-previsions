#!/usr/bin/env python3
"""Canonical runner config loader.

Precedence:
1) CLI explicit `--set key=value`
2) ENV whitelist overrides
3) Versioned YAML/JSON config defaults
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = ROOT / "platform" / "config" / "runner" / "runner.v1.yaml"
DEFAULT_SCHEMA = ROOT / "platform" / "config" / "schema" / "runner.v1.schema.json"
LEGACY_LOADER = ROOT / "platform" / "automation" / "runner_config.py"

if not DEFAULT_CONFIG.exists():
    fallback_cfg = ROOT / "platform" / "config" / "runner" / "runner_config.v1.yaml"
    if fallback_cfg.exists():
        DEFAULT_CONFIG = fallback_cfg
if not DEFAULT_SCHEMA.exists():
    fallback_schema = ROOT / "platform" / "config" / "runner" / "runner_config.schema.json"
    if fallback_schema.exists():
        DEFAULT_SCHEMA = fallback_schema

REQUIRED_TOP_KEYS = (
    "version",
    "defaults",
    "roles",
    "features",
    "paths",
    "timeouts",
    "retries",
    "telemetry",
)
REQUIRED_ROLES = ("planner", "dev", "admin", "scrum_master")

ROLE_ENV_PREFIX = {
    "planner": "FC_PLANNER",
    "dev": "FC_DEV",
    "admin": "FC_ADMIN",
    "scrum_master": "FC_SCRUM_MASTER",
}


def _load_config(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    try:
        return json.loads(text)
    except Exception:
        pass

    try:
        import yaml  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "config_parse_failed: install pyyaml or keep config JSON-compatible"
        ) from exc

    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise RuntimeError("config_root_must_be_object")
    return data


def _config_hash(cfg: dict[str, Any]) -> str:
    payload = json.dumps(cfg, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _set_path(cfg: dict[str, Any], dotted: str, raw_value: str) -> None:
    parts = [p for p in dotted.strip().split(".") if p.strip()]
    if not parts:
        return
    node: Any = cfg
    for part in parts[:-1]:
        if not isinstance(node, dict):
            raise RuntimeError(f"invalid_path:{dotted}")
        if part not in node or not isinstance(node[part], dict):
            node[part] = {}
        node = node[part]

    leaf = parts[-1]
    value: Any = raw_value
    if raw_value in {"0", "1"}:
        value = int(raw_value)
    else:
        try:
            value = int(raw_value)
        except Exception:
            pass
    if not isinstance(node, dict):
        raise RuntimeError(f"invalid_path:{dotted}")
    node[leaf] = value


def _apply_env_whitelist(cfg: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    out = copy.deepcopy(cfg)
    applied: list[str] = []

    env_top_map = {
        "FC_DEFAULT_PROMPT_TIMEOUT_SECONDS": "defaults.prompt_timeout_seconds",
        "FC_DEFAULT_RETRY_TIMEOUT_SECONDS": "defaults.retry_prompt_timeout_seconds",
        "FC_DEFAULT_TICK_TIMEOUT_SECONDS": "defaults.tick_timeout_seconds",
        "FC_FORCE_ALLOW_FILE_EDITS_ALL": "features.force_allow_file_edits_all",
        "FC_PLANNER_ORCHESTRATOR_ENABLED": "features.planner_orchestrator.enabled",
        "FC_PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY": "features.planner_orchestrator.cron_planner_only",
        "FC_PLANNER_ORCHESTRATOR_MAX_ACTIVE": "features.planner_orchestrator.max_active",
        "FC_PLANNER_ORCHESTRATOR_DEFAULT_TTL_MIN": "features.planner_orchestrator.default_ttl_min",
        "FC_PLANNER_ORCHESTRATOR_RETRY_MAX": "features.planner_orchestrator.retry_max",
        "FC_DYNAMIC_WORKERS_ENABLED": "features.dynamic_workers.enabled",
        "FC_DYNAMIC_WORKERS_MAX_ACTIVE": "features.dynamic_workers.max_active",
        "FC_DYNAMIC_WORKERS_DEFAULT_TTL_MIN": "features.dynamic_workers.default_ttl_min",
        "FC_DYNAMIC_WORKERS_RETRY_MAX": "features.dynamic_workers.retry_max",
    }
    for env_key, dotted in env_top_map.items():
        value = os.environ.get(env_key, "").strip()
        if not value:
            continue
        _set_path(out, dotted, value)
        applied.append(env_key)

    experimental_planner_only = os.environ.get("FC_EXPERIMENTAL_PLANNER_ONLY", "").strip()
    if experimental_planner_only:
        _set_path(out, "features.planner_orchestrator.enabled", experimental_planner_only)
        _set_path(out, "features.planner_orchestrator.cron_planner_only", experimental_planner_only)
        applied.append("FC_EXPERIMENTAL_PLANNER_ONLY")

    for role, prefix in ROLE_ENV_PREFIX.items():
        prefixes = [prefix]
        if role == "scrum_master":
            prefixes.append("FC_PO_SCRUM_MASTER")
        for px in prefixes:
            env_role_map = {
                f"{px}_MODEL": f"roles.{role}.model",
                f"{px}_THINKING": f"roles.{role}.thinking",
                f"{px}_PROMPT_TIMEOUT_SECONDS": f"roles.{role}.prompt_timeout_seconds",
                f"{px}_RETRY_TIMEOUT_SECONDS": f"roles.{role}.retry_timeout_seconds",
                f"{px}_TICK_TIMEOUT_SECONDS": f"roles.{role}.tick_timeout_seconds",
                f"{px}_RATE_LIMIT_PRECHECK": f"roles.{role}.rate_limit_precheck",
                f"{px}_CODEX_EXEC_RESUME": f"roles.{role}.resume",
            }
            for env_key, dotted in env_role_map.items():
                value = os.environ.get(env_key, "").strip()
                if not value:
                    continue
                _set_path(out, dotted, value)
                applied.append(env_key)

    return out, applied


def _validate_custom(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED_TOP_KEYS:
        if key not in cfg:
            errors.append(f"missing_top_key:{key}")
    if str(cfg.get("version", "")).strip() != "v1":
        errors.append("invalid_version:expected_v1")
    roles = cfg.get("roles")
    if not isinstance(roles, dict):
        errors.append("roles_must_be_object")
    else:
        for role in REQUIRED_ROLES:
            if role not in roles:
                errors.append(f"missing_role:{role}")
            elif not isinstance(roles.get(role), dict):
                errors.append(f"role_must_be_object:{role}")
    return errors


def _validate_schema(cfg: dict[str, Any], schema_path: Path) -> list[str]:
    try:
        import jsonschema  # type: ignore
    except Exception:
        return []

    schema_obj = json.loads(schema_path.read_text(encoding="utf-8", errors="ignore"))
    validator = jsonschema.Draft202012Validator(schema_obj)
    errors: list[str] = []
    for err in validator.iter_errors(cfg):
        loc = ".".join(str(x) for x in err.path) if err.path else "<root>"
        errors.append(f"{loc}:{err.message}")
    return errors


def _load_legacy_module():
    spec = importlib.util.spec_from_file_location("legacy_runner_config", LEGACY_LOADER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"legacy_loader_missing:{LEGACY_LOADER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _resolve_config(args: argparse.Namespace) -> tuple[dict[str, Any], list[str], list[str]]:
    cfg_file = Path(args.config).expanduser().resolve()
    schema_file = Path(args.schema).expanduser().resolve()
    cfg = _load_config(cfg_file)

    env_applied: list[str] = []
    if str(args.disable_env_whitelist) != "1":
        cfg, env_applied = _apply_env_whitelist(cfg)

    cli_applied: list[str] = []
    for item in args.set or []:
        if "=" not in item:
            raise RuntimeError(f"invalid_set_arg:{item}")
        key, value = item.split("=", 1)
        _set_path(cfg, key, value)
        cli_applied.append(key)

    errors = _validate_custom(cfg)
    errors.extend(_validate_schema(cfg, schema_file))
    if errors:
        raise RuntimeError("config_validation_failed:" + ",".join(errors))

    return cfg, env_applied, cli_applied


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        cfg, env_applied, cli_applied = _resolve_config(args)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": str(exc),
                    "config": str(Path(args.config).expanduser().resolve()),
                    "schema": str(Path(args.schema).expanduser().resolve()),
                },
                ensure_ascii=True,
            )
        )
        return 2

    print(
        json.dumps(
            {
                "ok": True,
                "version": cfg.get("version"),
                "config": str(Path(args.config).expanduser().resolve()),
                "schema": str(Path(args.schema).expanduser().resolve()),
                "env_overrides_applied": env_applied,
                "cli_overrides_applied": cli_applied,
            },
            ensure_ascii=True,
        )
    )
    return 0


def cmd_emit_env(args: argparse.Namespace) -> int:
    role = str(args.role).strip()
    if role not in REQUIRED_ROLES:
        print(f"invalid role: {role}", file=sys.stderr)
        return 2

    try:
        cfg, env_applied, cli_applied = _resolve_config(args)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 2

    # Use legacy flattening logic for output compatibility.
    legacy = _load_legacy_module()
    env_map, missing = legacy._flatten(cfg, role)  # noqa: SLF001
    env_map["RUNNER_CONFIG_SOURCE"] = str(Path(args.config).expanduser().resolve())
    env_map["RUNNER_CONFIG_HASH"] = _config_hash(cfg)
    strict = str(args.fallback_env).strip() == "0"
    if strict and missing:
        print(
            json.dumps(
                {"ok": False, "error": "missing_config_keys", "missing": missing, "role": role},
                ensure_ascii=True,
            ),
            file=sys.stderr,
        )
        return 2

    summary = {
        "role": role,
        "config": str(Path(args.config).expanduser().resolve()),
        "env_overrides_applied": env_applied,
        "cli_overrides_applied": cli_applied,
        "missing_with_fallback": missing,
    }
    print("# resolved_config " + json.dumps(summary, ensure_ascii=True), file=sys.stderr)

    for key in sorted(env_map.keys()):
        print(f"{key}={_shell_quote(str(env_map[key]))}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Canonical runner config loader")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    parser.add_argument("--set", action="append", default=[], help="CLI override in dotted.path=value format")
    parser.add_argument(
        "--disable-env-whitelist",
        default=os.environ.get("RUNNER_CONFIG_DISABLE_ENV_WHITELIST", "0"),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_validate = sub.add_parser("validate")
    p_validate.set_defaults(func=cmd_validate)

    p_emit = sub.add_parser("emit-env")
    p_emit.add_argument("--role", required=True)
    p_emit.add_argument("--fallback-env", default=os.environ.get("RUNNER_CONFIG_FALLBACK_ENV", "1"))
    p_emit.set_defaults(func=cmd_emit_env)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
