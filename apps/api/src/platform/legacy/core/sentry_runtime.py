"""
Shared Sentry runtime helpers for API jobs and background scripts.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, Optional

try:
    import sentry_sdk
except Exception:  # pragma: no cover
    sentry_sdk = None


logger = logging.getLogger(__name__)
_SENTRY_READY = False
_SENTRY_ENABLED = False


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _clamp_rate(value: str, default: float) -> float:
    try:
        parsed = float(value)
    except Exception:
        return default
    return max(0.0, min(1.0, parsed))


def _debug_mode() -> bool:
    return str(os.getenv("FINANCE_COPILOT_DEBUG", os.getenv("COPILOT_DEBUG", "0"))).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
        "debug",
    }


def init_sentry(component: str) -> bool:
    """
    Initialize Sentry once per process.
    """
    global _SENTRY_READY, _SENTRY_ENABLED

    if _SENTRY_READY:
        return _SENTRY_ENABLED

    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn or sentry_sdk is None:
        _SENTRY_READY = True
        _SENTRY_ENABLED = False
        return False

    debug_mode = _debug_mode()
    default_traces_rate = 1.0 if debug_mode else 0.2
    default_profile_rate = 0.2 if debug_mode else 0.0

    traces_rate = _clamp_rate(os.getenv("SENTRY_TRACES_SAMPLE_RATE", str(default_traces_rate)), default_traces_rate)
    profile_session_rate = _clamp_rate(
        os.getenv("SENTRY_PROFILE_SESSION_SAMPLE_RATE", os.getenv("SENTRY_PROFILES_SAMPLE_RATE", str(default_profile_rate))),
        default_profile_rate,
    )
    profiles_rate = _clamp_rate(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", str(profile_session_rate)), profile_session_rate)
    profile_lifecycle = os.getenv("SENTRY_PROFILE_LIFECYCLE", "trace")
    enable_logs = _env_bool("SENTRY_ENABLE_LOGS", default=True)
    send_default_pii = _env_bool("SENTRY_SEND_DEFAULT_PII", default=True)
    environment = (
        os.getenv("SENTRY_ENVIRONMENT")
        or os.getenv("APP_ENV")
        or os.getenv("ENVIRONMENT")
        or "development"
    )
    release = os.getenv("SENTRY_RELEASE")

    sentry_sdk.init(
        dsn=dsn,
        send_default_pii=send_default_pii,
        enable_logs=enable_logs,
        traces_sample_rate=traces_rate,
        profile_session_sample_rate=profile_session_rate,
        profile_lifecycle=profile_lifecycle,
        profiles_sample_rate=profiles_rate,
        environment=environment,
        release=release,
    )
    _SENTRY_READY = True
    _SENTRY_ENABLED = True
    logger.info("Sentry initialized for %s (env=%s)", component, environment)
    return True


def set_job_context(job_name: str, **context: Any) -> None:
    """
    Add stable tags/context so job events are easy to filter in Sentry.
    """
    if not _SENTRY_ENABLED or sentry_sdk is None:
        return
    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("component", "job")
        scope.set_tag("job.name", job_name)
        for key, value in context.items():
            scope.set_tag(f"job.{key}", str(value))


def capture_exception(
    exc: BaseException,
    *,
    job_name: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    flush: bool = False,
) -> None:
    """
    Capture handled exceptions explicitly.
    """
    if not _SENTRY_ENABLED or sentry_sdk is None:
        return
    with sentry_sdk.push_scope() as scope:
        if job_name:
            scope.set_tag("component", "job")
            scope.set_tag("job.name", job_name)
        for key, value in (context or {}).items():
            scope.set_extra(key, value)
        sentry_sdk.capture_exception(exc)
    if flush:
        sentry_sdk.flush(timeout=2.0)


def install_global_excepthook(job_name: str) -> bool:
    """
    Capture uncaught exceptions in script entrypoints.
    """
    if not init_sentry(component=f"job:{job_name}"):
        return False
    set_job_context(job_name)

    previous_hook = sys.excepthook

    def _hook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            return previous_hook(exc_type, exc_value, exc_traceback)
        capture_exception(
            exc_value,
            job_name=job_name,
            context={"unhandled": True, "exception_type": getattr(exc_type, "__name__", str(exc_type))},
            flush=True,
        )
        return previous_hook(exc_type, exc_value, exc_traceback)

    sys.excepthook = _hook
    return True
