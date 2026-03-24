from __future__ import annotations

from abc import ABC, abstractmethod
import os
from pathlib import Path
import subprocess
from typing import Any, Callable, Mapping

from runtime.core.compat import BaseModel, ConfigDict


RATE_LIMIT_MARKERS = (
    "you've hit your usage limit for gpt-5.3-codex-spark",
    "api-rate-limit-reached",
    "api rate limit reached",
    "insufficient_quota",
    "usage limit",
    "quota exceeded",
    "quota exhausted",
    "quota reached",
    "rate limit exceeded",
    "rate limit exhausted",
    "rate limit reached",
    "too many requests",
    "status 429",
    "http 429",
    " 429",
)

QWEN_AUTH_MARKERS = (
    "qwen oauth authentication",
    "please visit this url to authorize",
    "waiting for authorization",
    "authorize?user_code=",
    "scan the qr code below",
    "no auth type is selected",
    "please configure an auth type",
)


def openclaw_cli_model(model: str) -> str:
    token = str(model or "").strip()
    if not token:
        return "codex-cli/gpt-5.3-codex-spark"
    if "/" in token:
        return token
    return f"codex-cli/{token}"


def openclaw_runtime_model(model: str, sandbox: str) -> str:
    token = str(model or "").strip() or "gpt-5.3-codex-spark"
    if "/" in token:
        return token
    sandbox_token = str(sandbox or "").strip().lower()
    if sandbox_token in {"off", "danger-full-access"}:
        return f"codex-full/{token}"
    if sandbox_token == "workspace-write":
        return f"codex-cli-write/{token}"
    return f"codex-cli/{token}"


class StartInvocationRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    invocation_id: str = ""
    cycle_id: str = ""
    batch_id: str = ""
    task_id: str = ""
    owner_role: str = "planner"
    target_role: str = ""
    backend: str = ""
    backend_requested: str = ""
    backend_used: str = ""
    fallback_reason: str = "none"
    provider_plane: str = "agent"
    policy_plane: str = "model_plane"
    model: str = ""
    thinking: str = ""
    sandbox: str = ""
    timeout_seconds: int = 0
    session_id: str = ""
    idempotency_key: str = ""
    prompt_digest: str = ""
    prompt_preview: str = ""
    heartbeat_ts: str = ""
    metadata: dict[str, Any] = {}


class ResumeInvocationRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    invocation_id: str = ""
    cycle_id: str = ""
    batch_id: str = ""
    task_id: str = ""
    owner_role: str = "planner"
    target_role: str = ""
    backend: str = ""
    backend_requested: str = ""
    backend_used: str = ""
    fallback_reason: str = "none"
    provider_plane: str = "agent"
    policy_plane: str = "model_plane"
    session_id: str = ""
    idempotency_key: str = ""
    heartbeat_ts: str = ""
    metadata: dict[str, Any] = {}


class CollectInvocationRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    invocation_id: str = ""
    cycle_id: str = ""
    batch_id: str = ""
    task_id: str = ""
    owner_role: str = "planner"
    target_role: str = ""
    backend: str = ""
    backend_requested: str = ""
    backend_used: str = ""
    fallback_reason: str = "none"
    provider_plane: str = "agent"
    policy_plane: str = "model_plane"
    session_id: str = ""
    result_status: str = ""
    rc: int = 0
    result_ref: str = ""
    idempotency_key: str = ""
    heartbeat_ts: str = ""
    metadata: dict[str, Any] = {}


class StatusInvocationRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    invocation_id: str = ""
    cycle_id: str = ""
    batch_id: str = ""
    task_id: str = ""
    owner_role: str = "planner"
    target_role: str = ""
    backend: str = ""
    backend_requested: str = ""
    backend_used: str = ""
    fallback_reason: str = "none"
    provider_plane: str = "agent"
    policy_plane: str = "model_plane"
    session_id: str = ""
    idempotency_key: str = ""
    heartbeat_ts: str = ""
    invocation_status: str = ""
    metadata: dict[str, Any] = {}


class ModelInvocationPort(ABC):
    @abstractmethod
    def start(
        self,
        request: StartInvocationRequest,
        invoke: Callable[[], tuple[int, str, str, str]] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def resume(
        self,
        request: ResumeInvocationRequest,
        invoke: Callable[[], tuple[int, str, str, str]] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def collect(self, request: CollectInvocationRequest, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def status(
        self,
        request: StatusInvocationRequest,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError


def looks_like_rate_limited(text: str, markers: tuple[str, ...] = RATE_LIMIT_MARKERS) -> bool:
    lowered = str(text or "").lower()
    return any(marker in lowered for marker in markers)


def planner_qwen_fallback_enabled(env: Mapping[str, str] | None = None) -> bool:
    source = env or os.environ
    token = str(source.get("FC_PLANNER_QWEN_FALLBACK", "1") or "1").strip().lower()
    return token not in {"0", "false", "no", "off"}


def resolve_secondary_codex_fallback(
    target_role: str,
    current_model: Any,
    current_thinking: Any,
    *,
    env: Mapping[str, str] | None = None,
    default_model: str = "gpt-5.3-codex-spark",
    default_thinking: str = "high",
) -> tuple[str, str]:
    source = env or os.environ
    role = str(target_role or "").strip().lower()
    if role == "planner":
        return "", ""
    enabled = str(
        source.get("FC_PLANNER_SECONDARY_CODEX_FALLBACK")
        or source.get("TMUX_ROLE_SECONDARY_CODEX_FALLBACK")
        or "1"
    ).strip().lower()
    if enabled in {"0", "false", "no", "off", ""}:
        return "", ""
    role_token = role.upper().replace("-", "_")
    replacement_model = str(
        source.get(f"LM_ROLE_{role_token}_FALLBACK_MODEL")
        or source.get("LM_USED_SECONDARY_FALLBACK_MODEL")
        or source.get("LM_FALLBACK_SECONDARY_MODEL")
        or source.get("LM_TIER_BUILD_SECONDARY_MODEL")
        or default_model
    ).strip()
    current_model_token = str(current_model or "").strip()
    if "/" in current_model_token and "/" not in replacement_model:
        prefix = current_model_token.split("/", 1)[0].strip()
        if prefix:
            replacement_model = f"{prefix}/{replacement_model}"
    if not replacement_model or replacement_model == current_model_token:
        return "", ""
    thinking = str(
        source.get(f"LM_ROLE_{role_token}_FALLBACK_THINKING")
        or source.get("LM_USED_SECONDARY_FALLBACK_THINKING")
        or source.get("LM_FALLBACK_SECONDARY_THINKING")
        or source.get("LM_TIER_BUILD_SECONDARY_THINKING")
        or default_thinking
    ).strip()
    return replacement_model, thinking or default_thinking


def rate_limit_state_dir(env: Mapping[str, str] | None = None) -> Path:
    source = env or os.environ
    raw = (
        source.get("FC_ROLE_STATE_DIR")
        or source.get("TMUX_ROLE_STATE_DIR")
        or str(Path.home() / ".openclaw" / "cron" / "role-state")
    )
    return Path(str(raw).strip() or str(Path.home() / ".openclaw" / "cron" / "role-state")).expanduser()


def active_rate_limit_reason(prefixes: tuple[str, ...], env: Mapping[str, str] | None = None, now_epoch: int | None = None) -> str:
    state_dir = rate_limit_state_dir(env)
    if not state_dir.exists():
        return ""
    current_epoch = int(now_epoch if now_epoch is not None else __import__("time").time())
    reasons: list[str] = []
    seen: set[Path] = set()
    for prefix in prefixes:
        token = str(prefix or "").strip()
        if not token:
            continue
        patterns = [f"{token}.rate_limit_gate_cache", f"{token}*.rate_limit_gate_cache"]
        for pattern in patterns:
            for path in sorted(state_dir.glob(pattern)):
                if path in seen or not path.is_file():
                    continue
                seen.add(path)
                try:
                    payload = path.read_text(encoding="utf-8", errors="ignore").strip()
                except Exception:
                    continue
                until_raw, _, reason_raw = payload.partition("|")
                try:
                    until_ts = int(str(until_raw or "").strip())
                except Exception:
                    continue
                if until_ts <= current_epoch:
                    continue
                reason = str(reason_raw or path.name).strip()
                if reason and reason not in reasons:
                    reasons.append(reason[:220])
    return " | ".join(reasons[:3])


def resolve_qwen_bin(
    env: Mapping[str, str] | None = None,
    *,
    which: Callable[[str], str] | None = None,
) -> str:
    source = env or os.environ
    candidate = str(
        source.get("FC_PLANNER_QWEN_BIN")
        or source.get("TMUX_ROLE_QWEN_BIN")
        or source.get("LM_USED_QWEN_BIN")
        or "/home/venom/.npm-global/bin/qwen"
    ).strip()
    if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
        return candidate
    if which is not None and candidate:
        located = which(candidate)
        if located:
            return located
    if which is not None:
        return which("qwen")
    return ""


def looks_like_auth_prompt(text: str, markers: tuple[str, ...] | None = None) -> bool:
    lowered = str(text or "").lower()
    active_markers = markers if markers is not None else QWEN_AUTH_MARKERS
    return any(marker in lowered for marker in active_markers)


def run_qwen_cli(
    prompt: str,
    timeout_seconds: int,
    subagent_id: str,
    *,
    env: Mapping[str, str] | None = None,
    which: Callable[[str], str] | None = None,
    cwd: str | Path | None = None,
    auth_markers: tuple[str, ...] | None = None,
) -> tuple[int, str, str, str]:
    source = env or os.environ
    qwen_bin = resolve_qwen_bin(source, which=which)
    if not qwen_bin:
        return 5, "", "qwen_missing", f"qwen:{subagent_id}"
    try:
        timeout_value = int(timeout_seconds)
    except Exception:
        timeout_value = 0
    effective_timeout = max(30, timeout_value) if timeout_value > 0 else None
    model = str(source.get("FC_PLANNER_QWEN_MODEL", "qwen")).strip() or "qwen"
    cmd = [
        qwen_bin,
        "--output-format",
        "text",
        "--approval-mode",
        "yolo",
        "--sandbox",
        "false",
        "-m",
        model,
        "-p",
        prompt,
    ]
    if cwd:
        cmd[0:0] = []
    try:
        proc = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            check=False,
            cwd=str(cwd) if cwd else None,
            timeout=effective_timeout,
        )
        stdout_text = proc.stdout or ""
        stderr_text = proc.stderr or ""
        combined = "\n".join(part for part in (stdout_text, stderr_text) if str(part or "").strip())
        if looks_like_auth_prompt(combined, auth_markers):
            return 5, "", combined[:220] or "qwen_auth_required", f"qwen:{subagent_id}"
        return proc.returncode, stdout_text, stderr_text, f"qwen:{subagent_id}"
    except subprocess.TimeoutExpired as exc:
        timeout_label = effective_timeout if isinstance(effective_timeout, int) else "unbounded"
        return 124, str(exc.stdout or ""), str(exc.stderr or "") or f"qwen_timeout_after_{timeout_label}s", f"qwen:{subagent_id}"


def run_qwen_cli_fallback(
    prompt: str,
    timeout_seconds: int,
    subagent_id: str,
    *,
    reason: str,
    source: str,
    env: Mapping[str, str] | None = None,
    which: Callable[[str], str] | None = None,
    cwd: str | Path | None = None,
    auth_markers: tuple[str, ...] | None = None,
) -> tuple[int, str, str, str] | None:
    if not planner_qwen_fallback_enabled(env):
        return None
    if active_rate_limit_reason(("qwen",), env):
        return None
    rc, stdout, stderr, ref = run_qwen_cli(
        prompt,
        timeout_seconds,
        subagent_id,
        env=env,
        which=which,
        cwd=cwd,
        auth_markers=auth_markers,
    )
    combined = "\n".join(part for part in (stdout, stderr) if str(part or "").strip())
    if looks_like_auth_prompt(combined, auth_markers):
        return None
    if rc == 0 or str(stdout or "").strip():
        note = f"qwen_fallback_from={source}; reason={reason}"[:220]
        stderr_combined = "\n".join(part for part in (stderr, note) if str(part or "").strip())
        return rc, stdout, stderr_combined, ref
    return None


def run_secondary_codex_fallback(
    target_role: str,
    current_model: Any,
    current_thinking: Any,
    prompt: str,
    timeout_seconds: int,
    subagent_id: str,
    *,
    reason: str,
    source: str,
    invoke_codex_exec: Callable[[int, str, str], tuple[int, str, str]],
    env: Mapping[str, str] | None = None,
    default_model: str = "gpt-5.3-codex-spark",
    default_thinking: str = "low",
) -> tuple[int, str, str, str] | None:
    model, thinking = resolve_secondary_codex_fallback(
        target_role,
        current_model,
        current_thinking,
        env=env,
        default_model=default_model,
        default_thinking=default_thinking,
    )
    if not model:
        return None
    rc, stdout, stderr = invoke_codex_exec(timeout_seconds, model, thinking)
    note = f"secondary_codex_fallback_from={source}; reason={reason}; model={model}"[:220]
    stderr_combined = "\n".join(part for part in (stderr, note) if str(part or "").strip())
    return rc, stdout, stderr_combined, f"codex_exec:{subagent_id}:{model}"


def run_secondary_then_qwen_fallback(
    target_role: str,
    current_model: Any,
    current_thinking: Any,
    prompt: str,
    timeout_seconds: int,
    subagent_id: str,
    *,
    reason: str,
    source: str,
    invoke_codex_exec: Callable[[int, str, str], tuple[int, str, str]],
    env: Mapping[str, str] | None = None,
    which: Callable[[str], str] | None = None,
    cwd: str | Path | None = None,
    auth_markers: tuple[str, ...] | None = None,
    default_model: str = "gpt-5.3-codex-spark",
    default_thinking: str = "low",
    invalid_result_prefix: str = "invalid_subagent_result:",
    rate_limit_markers: tuple[str, ...] | None = None,
) -> tuple[int, str, str, str] | None:
    fallback_reason = str(reason or "").strip() or source
    secondary_fallback = run_secondary_codex_fallback(
        target_role,
        current_model,
        current_thinking,
        prompt,
        timeout_seconds,
        subagent_id,
        reason=fallback_reason,
        source=source,
        invoke_codex_exec=invoke_codex_exec,
        env=env,
        default_model=default_model,
        default_thinking=default_thinking,
    )
    if secondary_fallback is not None:
        secondary_combined = "\n".join(part for part in secondary_fallback[1:3] if str(part or "").strip())
        lowered_secondary = secondary_combined.lower()
        active_rate_limit_markers = rate_limit_markers if rate_limit_markers is not None else RATE_LIMIT_MARKERS
        is_rate_limited = any(marker in lowered_secondary for marker in active_rate_limit_markers)
        if not is_rate_limited and invalid_result_prefix not in secondary_combined:
            return secondary_fallback
        fallback_reason = secondary_combined or fallback_reason
    return run_qwen_cli_fallback(
        prompt,
        timeout_seconds,
        subagent_id,
        reason=fallback_reason,
        source=source,
        env=env,
        which=which,
        cwd=cwd,
        auth_markers=auth_markers,
    )


def resolve_effective_backend_details(
    plan: Mapping[str, Any],
    effective_backend: str,
    backend_ref: str,
    backend_route_reason: str,
    *,
    env: Mapping[str, str] | None = None,
    default_qwen_model: str = "qwen",
    default_secondary_model: str = "gpt-5.3-codex-spark",
    default_secondary_thinking: str = "low",
    openclaw_cli_model: Callable[[str], str] | None = None,
) -> tuple[str, str, str]:
    source = env or os.environ
    route_reason = str(backend_route_reason or "none").strip() or "none"
    model = str(plan.get("model", "") or "").strip()
    thinking = str(plan.get("thinking", "") or "").strip()
    backend_ref_token = str(backend_ref or "").strip()
    lowered_ref = backend_ref_token.lower()
    lowered_backend = str(effective_backend or "").strip().lower()

    if route_reason in {"", "none"} and lowered_ref.startswith("codex_exec:") and backend_ref_token.count(":") >= 2:
        route_reason = "secondary_codex_fallback"
    elif route_reason in {"", "none"} and (lowered_ref.startswith("qwen:") or lowered_backend == "qwen"):
        route_reason = "qwen_fallback"

    if lowered_ref.startswith("qwen:") or lowered_backend == "qwen":
        model = str(source.get("FC_PLANNER_QWEN_MODEL", default_qwen_model) or default_qwen_model).strip() or default_qwen_model
        thinking = "fallback"
    elif lowered_ref.startswith("codex_exec:"):
        parts = backend_ref_token.split(":", 2)
        if len(parts) == 3 and str(parts[2] or "").strip():
            model = str(parts[2]).strip()
        if route_reason == "secondary_codex_fallback":
            _, secondary_thinking = resolve_secondary_codex_fallback(
                str(plan.get("target_role", "")),
                plan.get("model", ""),
                plan.get("thinking", ""),
                env=source,
                default_model=default_secondary_model,
                default_thinking=default_secondary_thinking,
            )
            if secondary_thinking:
                thinking = secondary_thinking
    return route_reason, model, thinking


def _planner_backend_token(value: Any) -> str:
    return str(value or "").strip().lower()


def resolve_planner_backend_choice(
    target_role: Any,
    task_kind: Any,
    *,
    backend_override: Any = "",
    config_backend: Any = "",
    backend_by_role: Mapping[str, Any] | None = None,
) -> str:
    def _normalize_configured_backend(token: str) -> str:
        if token == "openclaw":
            return "codex_exec"
        return token

    token = _planner_backend_token(backend_override)
    if token and token != "auto":
        return _normalize_configured_backend(token)
    mapping = backend_by_role or {}
    task_kind_token = _planner_backend_token(task_kind)
    mapped_task_backend = _planner_backend_token(mapping.get(task_kind_token, "")) if task_kind_token else ""
    if mapped_task_backend:
        return _normalize_configured_backend(mapped_task_backend)
    target_token = _planner_backend_token(target_role).replace("-", "_")
    mapped_role_backend = _planner_backend_token(mapping.get(target_token, "")) if target_token else ""
    if mapped_role_backend:
        return _normalize_configured_backend(mapped_role_backend)
    configured = _normalize_configured_backend(_planner_backend_token(config_backend or "codex_exec"))
    if configured == "auto":
        return "codex_exec"
    return configured or "codex_exec"


def validate_planner_dispatch_backend(
    backend: Any,
    *,
    which: Callable[[str], str] | None = None,
) -> str:
    token = _planner_backend_token(backend) or "codex_exec"
    if token not in {"codex_exec", "mock"}:
        if token == "openclaw":
            return "openclaw_provider_deprecated"
        return f"unsupported_backend:{token}"
    if which is None:
        from shutil import which as shutil_which

        which_fn = shutil_which
    else:
        which_fn = which
    if token == "codex_exec" and not str(which_fn("codex") or "").strip():
        return "codex_missing"
    return ""
