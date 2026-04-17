#!/usr/bin/env python3
"""Runner config loader (v1) with progressive ENV fallback.

The config file is YAML v1. Since YAML is a superset of JSON and this
workspace avoids non-stdlib dependencies, we parse JSON-formatted YAML.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
REQUIRED_ROLES = ("planner", "app-dev", "verifier", "admin", "scrum_master")
DEFAULT_CONFIG_FILE = Path(__file__).resolve().parents[1] / "config" / "runner" / "runner.v1.yaml"
if not DEFAULT_CONFIG_FILE.exists():
    fallback_default = Path(__file__).resolve().parents[1] / "config" / "runner" / "runner_config.v1.yaml"
    if fallback_default.exists():
        DEFAULT_CONFIG_FILE = fallback_default


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str]
    warnings: list[str]


def _read_config(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        raise RuntimeError(f"cannot_read_config:{path}:{exc}") from exc
    try:
        data = json.loads(text)
    except Exception as exc:
        raise RuntimeError(
            "config_parse_failed: expected JSON-formatted YAML (YAML v1 subset)"
        ) from exc
    if not isinstance(data, dict):
        raise RuntimeError("config_root_must_be_object")
    return data


def _validate(cfg: dict[str, Any]) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    for key in REQUIRED_TOP_KEYS:
        if key not in cfg:
            errors.append(f"missing_top_key:{key}")
    version = str(cfg.get("version", "")).strip()
    if version != "v1":
        errors.append("invalid_version:expected_v1")
    roles = cfg.get("roles", {})
    if not isinstance(roles, dict):
        errors.append("roles_must_be_object")
    else:
        for role in REQUIRED_ROLES:
            if role not in roles:
                errors.append(f"missing_role:{role}")
            elif not isinstance(roles.get(role), dict):
                errors.append(f"role_must_be_object:{role}")
    for section in ("defaults", "features", "paths"):
        if section in cfg and not isinstance(cfg.get(section), dict):
            errors.append(f"{section}_must_be_object")
    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)


def _as_int01(value: Any, default: int) -> int:
    try:
        raw = int(str(value).strip())
    except Exception:
        return default
    return 1 if raw != 0 else 0


def _as_int(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default


def _as_text(value: Any, default: str = "") -> str:
    text = str(value if value is not None else "").strip()
    return text if text else default


def _role_prefix(role: str) -> str:
    mapping = {
        "planner": "FC_PLANNER",
        "app-dev": "FC_DEV",
        "dev": "FC_DEV",
        "verifier": "FC_VERIFIER",
        "admin": "FC_ADMIN",
        "scrum_master": "FC_SCRUM_MASTER",
    }
    return mapping.get(role, f"FC_{str(role).upper().replace('-', '_')}")


def _canonical_role(role: str) -> str:
    token = str(role or "").strip()
    if token == "planner_architect_orchestrator":
        return "planner"
    if token in {"vision-architect-tasks-planner", "vision_architect_tasks_planner", "analyst", "architect", "po"}:
        return "planner"
    if token in {"app_dev", "app-dev"}:
        return "app-dev"
    if token in {"dev", "backend_engineer", "frontend_engineer", "data_analyst", "integrator"}:
        return "app-dev"
    if token in {"tester", "qa"}:
        return "verifier"
    if token in {"infra_engineer", "clawsentinel"}:
        return "admin"
    return token


def _flatten(cfg: dict[str, Any], role: str) -> tuple[dict[str, str], list[str]]:
    out: dict[str, str] = {}
    missing: list[str] = []
    defaults = cfg.get("defaults", {}) if isinstance(cfg.get("defaults"), dict) else {}
    features = cfg.get("features", {}) if isinstance(cfg.get("features"), dict) else {}
    roles = cfg.get("roles", {}) if isinstance(cfg.get("roles"), dict) else {}
    role_cfg = roles.get(role, {}) if isinstance(roles.get(role), dict) else {}

    out["RUNNER_CONFIG_VERSION"] = "v1"
    out["AGENT_MESSAGE_BUS_ENABLED"] = str(
        _as_int01(
            (defaults.get("message_bus", {}) or {}).get("enabled", 1),
            1,
        )
    )
    out["AGENT_MESSAGE_STICKY_DEFAULT"] = str(
        _as_int01((defaults.get("message_bus", {}) or {}).get("sticky_default", 1), 1)
    )
    out["AGENT_MESSAGE_DEFAULT_TTL_MIN"] = str(
        _as_int((defaults.get("message_bus", {}) or {}).get("default_ttl_min", 10080), 10080)
    )
    out["AGENT_MESSAGE_MAX_ACTIVE_PER_ROLE"] = str(
        _as_int((defaults.get("message_bus", {}) or {}).get("max_active_per_role", 10), 10)
    )

    prefix = _role_prefix(role)
    out[f"{prefix}_PROMPT_TIMEOUT_SECONDS"] = str(
        _as_int(
            role_cfg.get("prompt_timeout_seconds", defaults.get("prompt_timeout_seconds", 210)),
            210,
        )
    )
    out[f"{prefix}_RETRY_TIMEOUT_SECONDS"] = str(
        _as_int(
            role_cfg.get("retry_timeout_seconds", defaults.get("retry_prompt_timeout_seconds", 90)),
            90,
        )
    )
    out[f"{prefix}_TICK_TIMEOUT_SECONDS"] = str(
        _as_int(
            role_cfg.get("tick_timeout_seconds", defaults.get("tick_timeout_seconds", 540)),
            540,
        )
    )
    out[f"{prefix}_CODEX_EXEC_RESUME"] = str(_as_int01(role_cfg.get("resume", 1), 1))
    out[f"{prefix}_RATE_LIMIT_PRECHECK"] = str(_as_int01(role_cfg.get("rate_limit_precheck", 0), 0))
    if role in {"dev", "app-dev"}:
        autonomy = role_cfg.get("autonomy", {}) if isinstance(role_cfg.get("autonomy"), dict) else {}
        out["FC_DEV_AUTONOMY_STALL_THRESHOLD_TICKS"] = str(
            _as_int(autonomy.get("stall_threshold_ticks", 2), 2)
        )
        out["FC_DEV_AUTONOMY_ENFORCE_COOLDOWN_SECONDS"] = str(
            _as_int(autonomy.get("enforce_cooldown_seconds", 1200), 1200)
        )
        out["FC_DEV_AUTONOMY_MAX_ENFORCED_PER_HOUR"] = str(
            _as_int(autonomy.get("max_enforced_per_hour", 4), 4)
        )
        out["FC_DEV_AUTONOMY_MIN_DELIVERY_ACTIONS_24H"] = str(
            _as_int(autonomy.get("min_delivery_actions_24h", 4), 4)
        )
        out["FC_DEV_AUTONOMY_STRICT_ENFORCE"] = str(
            _as_int01(autonomy.get("strict_enforce", 1), 1)
        )
    if _as_text(role_cfg.get("model")):
        out[f"{prefix}_MODEL"] = _as_text(role_cfg.get("model"))
    if _as_text(role_cfg.get("thinking")):
        out[f"{prefix}_THINKING"] = _as_text(role_cfg.get("thinking"))

    # Direct runner-level hints (used when cron runner is called directly).
    if _as_text(role_cfg.get("model")):
        out["TMUX_ROLE_CODEX_MODEL"] = _as_text(role_cfg.get("model"))
    if _as_text(role_cfg.get("thinking")):
        out["TMUX_ROLE_CODEX_THINKING"] = _as_text(role_cfg.get("thinking"))
    out["TMUX_ROLE_CODEX_EXEC_RESUME"] = str(_as_int01(role_cfg.get("resume", 1), 1))
    out["TMUX_ROLE_RATE_LIMIT_PRECHECK"] = str(_as_int01(role_cfg.get("rate_limit_precheck", 1), 1))
    out["TMUX_ROLE_RATE_LIMIT_QWEN_FALLBACK"] = str(
        _as_int01(role_cfg.get("rate_limit_qwen_fallback", 1), 1)
    )
    out["TMUX_ROLE_CODEX_REQUIRE_FRESH_TICK"] = str(
        _as_int01(role_cfg.get("codex_require_fresh_tick", 1), 1)
    )
    out["TMUX_ROLE_CODEX_TICK_AUTOFIX"] = str(
        _as_int01(role_cfg.get("codex_tick_autofix", 1), 1)
    )
    out["PROMPT_TIMEOUT_SECONDS"] = out[f"{prefix}_PROMPT_TIMEOUT_SECONDS"]
    out["RETRY_PROMPT_TIMEOUT_SECONDS"] = out[f"{prefix}_RETRY_TIMEOUT_SECONDS"]
    out["FC_TICK_TIMEOUT_SECONDS"] = out[f"{prefix}_TICK_TIMEOUT_SECONDS"]

    planner_autonomy = (
        features.get("planner_autonomy", {})
        if isinstance(features.get("planner_autonomy"), dict)
        else {}
    )
    out["FC_PLANNER_AUTONOMY_ENABLED"] = str(_as_int01(planner_autonomy.get("enabled", 1), 1))
    out["FC_PLANNER_WAIT_FORBIDDEN"] = str(_as_int01(planner_autonomy.get("wait_forbidden", 1), 1))
    out["FC_PLANNER_NEVER_WAIT"] = out["FC_PLANNER_WAIT_FORBIDDEN"]
    out["FC_PLANNER_AUTO_CREATE_ON_EMPTY"] = str(
        _as_int01(planner_autonomy.get("auto_create_on_empty", 1), 1)
    )
    out["FC_PLANNER_IDLE_AUTOBATCH"] = out["FC_PLANNER_AUTO_CREATE_ON_EMPTY"]
    out["FC_PLANNER_CREATE_SOURCE"] = _as_text(planner_autonomy.get("create_source"), "vision")

    api_autonomy_mode = (
        features.get("api_autonomy_mode", {})
        if isinstance(features.get("api_autonomy_mode"), dict)
        else {}
    )
    out["FC_API_AUTONOMY_MODE"] = str(_as_int01(api_autonomy_mode.get("enabled", 0), 0))
    out["FC_API_WAVE_MANIFEST_PATH"] = _as_text(
        api_autonomy_mode.get("manifest_path"),
        "platform/automation/config/api_wave_manifest.json",
    )
    out["FC_API_WAVE_STATE_PATH"] = _as_text(
        api_autonomy_mode.get("state_path"),
        "logs-codex-runs/orchestrator-state/api-wave-state.json",
    )
    out["FC_API_WAVE_BATCH_ID"] = _as_text(
        api_autonomy_mode.get("wave_batch_id"),
        "BATCH-900",
    )
    raw_api_domains = api_autonomy_mode.get("allowed_domains", ["copilot", "forecasts", "market_data"])
    if not isinstance(raw_api_domains, list):
        raw_api_domains = ["copilot", "forecasts", "market_data"]
    out["FC_API_WAVE_ALLOWED_DOMAINS"] = ",".join(
        str(token).strip() for token in raw_api_domains if str(token).strip()
    )
    raw_api_roles = api_autonomy_mode.get("managed_roles", ["app-dev"])
    if not isinstance(raw_api_roles, list):
        raw_api_roles = ["app-dev"]
    out["FC_API_WAVE_MANAGED_ROLES"] = ",".join(
        str(token).strip() for token in raw_api_roles if str(token).strip()
    )

    dev_wait_policy = (
        features.get("dev_wait_policy", {})
        if isinstance(features.get("dev_wait_policy"), dict)
        else {}
    )
    out["FC_DEV_WAIT_READY_TASK_ONLY"] = str(
        _as_int01(dev_wait_policy.get("ready_task_only", 1), 1)
    )

    stability = (
        features.get("stability", {})
        if isinstance(features.get("stability"), dict)
        else {}
    )
    out["FC_ADMIN_RUNTIME_STALE_AUTOHEAL"] = str(
        _as_int01(stability.get("admin_runtime_stale_autoheal", 1), 1)
    )
    out["FC_SCRUM_ARTIFACT_AUTOFILL"] = str(
        _as_int01(stability.get("scrum_artifact_autofill", 1), 1)
    )
    out["FC_SCRUM_AUTO_INTENTS_HARDENED"] = str(
        _as_int01(stability.get("scrum_auto_intents_hardened", 1), 1)
    )
    out["FC_MONITOR_READY_DEV_FROM_WORKBOARD"] = str(
        _as_int01(stability.get("monitor_ready_dev_from_workboard", 1), 1)
    )

    scrum_feature = features.get("scrum_master", {}) if isinstance(features.get("scrum_master"), dict) else {}
    if not scrum_feature:
        scrum_feature = features.get("po_scrum_master", {}) if isinstance(features.get("po_scrum_master"), dict) else {}
    out["FC_SCRUM_MASTER_ENABLED"] = str(_as_int01(scrum_feature.get("enabled", 1), 1))
    out["TMUX_ROLE_ENABLE_SCRUM_MASTER"] = out["FC_SCRUM_MASTER_ENABLED"]
    out["TMUX_ROLE_ENABLE_PO_SCRUM_MASTER"] = out["FC_SCRUM_MASTER_ENABLED"]
    out["FC_ENABLE_PO_SCRUM_MASTER"] = out["FC_SCRUM_MASTER_ENABLED"]
    out["FC_FORCE_ALLOW_FILE_EDITS_ALL"] = str(_as_int01(features.get("force_allow_file_edits_all", 1), 1))
    if role == "scrum_master":
        allow_bus_post = str(_as_int01(role_cfg.get("allow_bus_post", 1), 1))
        max_posts_per_tick = str(_as_int(role_cfg.get("max_posts_per_tick", 2), 2))
        post_cooldown_s = str(_as_int(role_cfg.get("post_cooldown_s", 600), 600))
        out["FC_SCRUM_MASTER_ALLOW_BUS_POST"] = allow_bus_post
        out["FC_SCRUM_MASTER_MAX_POSTS_PER_TICK"] = max_posts_per_tick
        out["FC_SCRUM_MASTER_POST_COOLDOWN_S"] = post_cooldown_s
        out["PO_SCRUM_MASTER_ALLOW_BUS_POST"] = allow_bus_post
        out["PO_SCRUM_MASTER_MAX_POSTS_PER_TICK"] = max_posts_per_tick
        out["PO_SCRUM_MASTER_POST_COOLDOWN_S"] = post_cooldown_s

    state_reconciler = (
        features.get("state_reconciler", {})
        if isinstance(features.get("state_reconciler"), dict)
        else {}
    )
    out["FC_STATE_RECONCILER"] = str(_as_int01(state_reconciler.get("enabled", 1), 1))
    out["FC_RECONCILE_STALE_LOCK_SECONDS"] = str(
        _as_int(state_reconciler.get("stale_lock_seconds", 1800), 1800)
    )
    out["FC_RECONCILE_STALE_IN_PROGRESS_SECONDS"] = str(
        _as_int(state_reconciler.get("stale_in_progress_seconds", 14400), 14400)
    )
    out["FC_RECONCILE_READY_STARVATION_SECONDS"] = str(
        _as_int(state_reconciler.get("ready_starvation_seconds", 1800), 1800)
    )

    delivery_gate = (
        features.get("delivery_value_gate", {})
        if isinstance(features.get("delivery_value_gate"), dict)
        else {}
    )
    out["FC_DELIVERY_VALUE_GATE"] = str(_as_int01(delivery_gate.get("enabled", 1), 1))
    out["FC_DELIVERY_VALUE_GATE_MODE"] = _as_text(delivery_gate.get("mode"), "enforce")
    out["FC_DELIVERY_VALUE_GATE_BURST_WINDOW_SECONDS"] = str(
        _as_int(delivery_gate.get("burst_window_seconds", 300), 300)
    )
    out["FC_DELIVERY_VALUE_GATE_BURST_THRESHOLD"] = str(
        _as_int(delivery_gate.get("burst_threshold", 3), 3)
    )

    scrum_policy = (
        features.get("scrum_policy", {})
        if isinstance(features.get("scrum_policy"), dict)
        else {}
    )
    out["FC_SCRUM_POLICY_ENABLED"] = str(_as_int01(scrum_policy.get("enabled", 1), 1))
    out["FC_SCRUM_READY_STARVATION_SECONDS"] = str(
        _as_int(scrum_policy.get("ready_starvation_seconds", 1800), 1800)
    )
    out["FC_SCRUM_STALLED_IN_PROGRESS_SECONDS"] = str(
        _as_int(scrum_policy.get("stalled_in_progress_seconds", 14400), 14400)
    )
    out["FC_SCRUM_ESCALATE_AFTER_CYCLES"] = str(
        _as_int(scrum_policy.get("escalate_after_cycles", 2), 2)
    )

    planner_orchestrator = (
        features.get("planner_orchestrator", {})
        if isinstance(features.get("planner_orchestrator"), dict)
        else {}
    )
    raw_managed_roles = planner_orchestrator.get("managed_roles", ["dev", "admin"])
    if not isinstance(raw_managed_roles, list):
        raw_managed_roles = ["dev", "admin"]
    out["FC_PLANNER_ORCHESTRATOR_ENABLED"] = str(
        _as_int01(planner_orchestrator.get("enabled", 0), 0)
    )
    out["FC_PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY"] = str(
        _as_int01(planner_orchestrator.get("cron_planner_only", 0), 0)
    )
    out["FC_PLANNER_ORCHESTRATOR_MAX_ACTIVE"] = str(
        _as_int(planner_orchestrator.get("max_active", 3), 3)
    )
    out["FC_PLANNER_ORCHESTRATOR_DEFAULT_TTL_MIN"] = str(
        _as_int(planner_orchestrator.get("default_ttl_min", 45), 45)
    )
    out["FC_PLANNER_ORCHESTRATOR_RETRY_MAX"] = str(
        _as_int(planner_orchestrator.get("retry_max", 2), 2)
    )
    out["FC_PLANNER_ORCHESTRATOR_BACKEND"] = _as_text(
        planner_orchestrator.get("backend"), "openclaw"
    )
    backend_by_role = (
        planner_orchestrator.get("backend_by_role", {})
        if isinstance(planner_orchestrator.get("backend_by_role"), dict)
        else {}
    )
    out["FC_PLANNER_ORCHESTRATOR_BACKEND_BY_ROLE"] = ",".join(
        f"{str(key).strip()}={str(value).strip()}"
        for key, value in backend_by_role.items()
        if str(key).strip() and str(value).strip()
    )
    out["FC_PLANNER_ORCHESTRATOR_MANAGED_ROLES"] = ",".join(
        str(tok).strip() for tok in raw_managed_roles if str(tok).strip()
    )
    out["FC_EXPERIMENTAL_PLANNER_ONLY"] = str(
        1
        if out["FC_PLANNER_ORCHESTRATOR_ENABLED"] == "1"
        and out["FC_PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY"] == "1"
        else 0
    )

    dynamic_workers = (
        features.get("dynamic_workers", {})
        if isinstance(features.get("dynamic_workers"), dict)
        else {}
    )
    raw_allowed_roles = dynamic_workers.get("allowed_roles", ["planner", "dev", "admin"])
    if not isinstance(raw_allowed_roles, list):
        raw_allowed_roles = ["planner", "dev", "admin"]
    out["FC_DYNAMIC_WORKERS_ENABLED"] = str(_as_int01(dynamic_workers.get("enabled", 0), 0))
    out["FC_DYNAMIC_WORKERS_MAX_ACTIVE"] = str(
        _as_int(dynamic_workers.get("max_active", 6), 6)
    )
    out["FC_DYNAMIC_WORKERS_DEFAULT_TTL_MIN"] = str(
        _as_int(dynamic_workers.get("default_ttl_min", 60), 60)
    )
    out["FC_DYNAMIC_WORKERS_RETRY_MAX"] = str(
        _as_int(dynamic_workers.get("retry_max", 2), 2)
    )
    out["FC_DYNAMIC_WORKERS_ALLOWED_ROLES"] = ",".join(str(tok).strip() for tok in raw_allowed_roles if str(tok).strip())

    tshape = features.get("tshape", {}) if isinstance(features.get("tshape"), dict) else {}
    out["FC_ADMIN_TSHAPE_ENABLED"] = str(_as_int01(tshape.get("enabled", 1), 1))
    out["FC_ADMIN_TSHAPE_TRIGGER"] = _as_text(tshape.get("trigger"), "blocked")
    out["FC_ADMIN_TSHAPE_BLOCKED_THRESHOLD"] = str(_as_int(tshape.get("blocked_threshold", 1), 1))
    out["FC_ADMIN_TSHAPE_SCOPE"] = _as_text(tshape.get("scope"), "full_takeover")
    out["FC_ADMIN_TSHAPE_EXIT_POLICY"] = _as_text(tshape.get("exit_policy"), "resolved_only")
    out["FC_ADMIN_TSHAPE_ALLOWED_TARGETS"] = _as_text(tshape.get("allowed_targets"), "planner,dev")

    admin_autonomy = (
        features.get("admin_autonomy", {})
        if isinstance(features.get("admin_autonomy"), dict)
        else {}
    )
    out["FC_ADMIN_AUTONOMY_ENABLED"] = str(_as_int01(admin_autonomy.get("enabled", 1), 1))
    out["FC_ADMIN_STALL_TICKS_THRESHOLD"] = str(
        _as_int(admin_autonomy.get("stall_ticks_threshold", 2), 2)
    )
    out["FC_ADMIN_AUTONOMY_SCOPE"] = _as_text(
        admin_autonomy.get("scope"), "full_with_proofs"
    )
    out["FC_ADMIN_AUTONOMY_MAX_ACTIONS"] = str(
        _as_int(admin_autonomy.get("max_actions", 2), 2)
    )
    out["FC_ADMIN_AUTONOMY_ROLE_COOLDOWN_S"] = str(
        _as_int(admin_autonomy.get("role_cooldown_s", 300), 300)
    )
    out["FC_ADMIN_AUTONOMY_RETRY_BACKOFF_S"] = str(
        _as_int(admin_autonomy.get("retry_backoff_s", 120), 120)
    )
    out["FC_ADMIN_AUTONOMY_FAILSAFE_MAX_RETRIES"] = str(
        _as_int(admin_autonomy.get("failsafe_max_retries", 3), 3)
    )
    out["FC_ADMIN_PROOF_GATE_STRICT"] = str(
        _as_int01(admin_autonomy.get("proof_gate_strict", 1), 1)
    )
    out["FC_ADMIN_AUTONOMY_SECURITY_WINDOW_MIN"] = str(
        _as_int(admin_autonomy.get("security_window_min", 10), 10)
    )

    for must_key in ("prompt_timeout_seconds", "retry_timeout_seconds", "tick_timeout_seconds"):
        if must_key not in role_cfg and must_key not in defaults:
            missing.append(f"{role}.{must_key}")
    return out, missing


def _config_hash(cfg: dict[str, Any]) -> str:
    payload = json.dumps(cfg, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def cmd_validate(args: argparse.Namespace) -> int:
    cfg = _read_config(Path(args.config))
    result = _validate(cfg)
    payload = {
        "ok": result.ok,
        "errors": result.errors,
        "warnings": result.warnings,
        "version": cfg.get("version"),
        "config": str(Path(args.config).resolve()),
    }
    print(json.dumps(payload, ensure_ascii=True))
    return 0 if result.ok else 2


def cmd_emit_env(args: argparse.Namespace) -> int:
    cfg = _read_config(Path(args.config))
    result = _validate(cfg)
    if not result.ok:
        print(json.dumps({"ok": False, "errors": result.errors}, ensure_ascii=True), file=sys.stderr)
        return 2
    role = _canonical_role(str(args.role).strip())
    if role not in REQUIRED_ROLES:
        print(f"invalid role: {role}", file=sys.stderr)
        return 2
    env_map, missing = _flatten(cfg, role)
    env_map["RUNNER_CONFIG_SOURCE"] = str(Path(args.config).expanduser().resolve())
    env_map["RUNNER_CONFIG_HASH"] = _config_hash(cfg)
    fallback_env = int(str(args.fallback_env).strip() or "1")
    strict = fallback_env == 0
    if strict and missing:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "missing_config_keys",
                    "missing": missing,
                    "role": role,
                },
                ensure_ascii=True,
            ),
            file=sys.stderr,
        )
        return 2
    if missing and fallback_env == 1:
        msg = ",".join(missing)
        print(f"# warning config_fallback_env_used role={role} missing={msg}", file=sys.stderr)
    for key in sorted(env_map.keys()):
        print(f"{key}={_shell_quote(str(env_map[key]))}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Runner config loader/validator (v1).")
    parser.add_argument(
        "--config",
        default=os.environ.get(
            "RUNNER_CONFIG_FILE",
            str(DEFAULT_CONFIG_FILE),
        ),
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
