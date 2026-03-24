#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import time
import json
import argparse
import subprocess
import shlex
import hashlib
import shutil
import tempfile
import inspect
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import List, Dict, Any, Optional, Tuple

try:
    import sentry_sdk
except Exception:  # pragma: no cover
    sentry_sdk = None


# ==============================================================================
# CONFIG (overridable via env)
# ==============================================================================

def resolve_default_project_dir() -> Path:
    """Resolve project root across macOS host and Linux VM setups."""
    env_project = os.environ.get("FC_PROJECT_DIR")
    if env_project:
        return Path(env_project).expanduser().resolve()

    script_root = Path(__file__).resolve().parent.parent
    if (script_root / ".git").exists() or (script_root / "copilot-app").exists():
        return script_root

    cwd = Path.cwd().resolve()
    if (cwd / ".git").exists() or (cwd / "copilot-app").exists():
        return cwd

    return script_root


DEFAULT_PROJECT_DIR = resolve_default_project_dir()
PROJECT_DIR = DEFAULT_PROJECT_DIR

BACKEND_DIR = Path(os.environ.get("FC_BACKEND_DIR", str(PROJECT_DIR / "apps" / "api" / "src"))).expanduser().resolve()
BACKEND_SRC = BACKEND_DIR / "src"
VENV_BIN = BACKEND_DIR / ".venv" / "bin"
VENV_PY = VENV_BIN / "python3"

AUTO_CONFIRM = True

APP_LOG_DIR_DEFAULT = Path(
    os.environ.get("FC_APP_LOG_DIR", str(PROJECT_DIR / "finance-app"))
).expanduser().resolve()
RUNS_SUBDIR_NAME = os.environ.get("FC_RUNS_SUBDIR", "orchestrator-runs")
RUNS_DIR_DEFAULT = Path(
    os.environ.get("FC_RUNS_DIR", str(APP_LOG_DIR_DEFAULT / RUNS_SUBDIR_NAME))
).expanduser().resolve()
AGENT_BUS_MAX_CONTENT_CHARS = int(os.environ.get("FC_AGENT_BUS_MAX_CONTENT_CHARS", "2200"))
AGENT_EVENTS_MAX_COMMANDS = int(os.environ.get("FC_AGENT_EVENTS_MAX_COMMANDS", "25"))
AGENT_EVENTS_FILE_LIMIT = int(os.environ.get("FC_AGENT_EVENTS_FILE_LIMIT", "120"))
AGENT_RESPONSE_SOFT_LIMIT = int(os.environ.get("FC_AGENT_RESPONSE_SOFT_LIMIT", "2600"))
CORE_STATUS_ROLES_LEGACY_DEFAULT: Tuple[str, ...] = ("planner", "dev", "tester", "qa")


def _bool_token(value: Any, default: bool = False) -> bool:
    token = str(value or "").strip()
    if not token:
        return default
    return token not in {"0", "false", "False"}


def _read_json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return None


def _runtime_state_file() -> Path:
    token = str(os.environ.get("FC_ORCHESTRATOR_STATE_DIR", "")).strip()
    if token:
        state_root = Path(token).expanduser()
        if not state_root.is_absolute():
            state_root = PROJECT_DIR / state_root
    else:
        state_root = PROJECT_DIR / "logs-codex-runs" / "orchestrator-state"
    return state_root / "runtime-state.json"


def default_status_core_roles() -> Tuple[str, ...]:
    planner_enabled = _bool_token(os.environ.get("FC_PLANNER_ORCHESTRATOR_ENABLED"), False)
    planner_cron_only = _bool_token(os.environ.get("FC_PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY"), False)
    experimental = str(os.environ.get("FC_EXPERIMENTAL_PLANNER_ONLY", "")).strip()
    if experimental:
        planner_enabled = _bool_token(experimental, planner_enabled)
        planner_cron_only = _bool_token(experimental, planner_cron_only)

    execution_mode = str(os.environ.get("FC_EXECUTION_MODE", "")).strip()
    if not execution_mode:
        runtime_state = _read_json_file(_runtime_state_file())
        if isinstance(runtime_state, dict):
            execution_mode = str(runtime_state.get("execution_mode", "") or "").strip()

    if execution_mode == "planner_experimental" or (planner_enabled and planner_cron_only):
        return ("planner",)
    return CORE_STATUS_ROLES_LEGACY_DEFAULT


CORE_STATUS_ROLES_DEFAULT: Tuple[str, ...] = default_status_core_roles()
SPECIALIST_ROLE_SPECS: Dict[str, Dict[str, str]] = {
    "analyst": {
        "env_var": "FC_SESS_ANALYST",
        "default_session": "qwen_analyst",
        "agent_name": "Analyst",
        "system_prompt": (
            "Tu es ANALYST. Tu transformes la demande en objectif clair, "
            "critères d'acceptation testables, hypothèses et priorités."
        ),
    },
    "architect": {
        "env_var": "FC_SESS_ARCHITECT",
        "default_session": "qwen_architect",
        "agent_name": "Architect",
        "system_prompt": (
            "Tu es ARCHITECT. Tu challenge le design, les risques, la scalabilité, "
            "la maintenabilité et la cohérence avec les contraintes."
        ),
    },
    "backend_engineer": {
        "env_var": "FC_SESS_BACKEND_ENGINEER",
        "default_session": "qwen_backend_engineer",
        "agent_name": "BackendEngineer",
        "system_prompt": (
            "Tu es BACKEND_ENGINEER. Tu proposes des changements backend minimaux, "
            "testables, avec commandes d'exécution précises."
        ),
    },
    "frontend_engineer": {
        "env_var": "FC_SESS_FRONTEND_ENGINEER",
        "default_session": "qwen_frontend_engineer",
        "agent_name": "FrontendEngineer",
        "system_prompt": (
            "Tu es FRONTEND_ENGINEER. Tu conçois une UI claire, responsive, "
            "avec validations manuelles et automatisées explicites."
        ),
    },
    "data_engineer": {
        "env_var": "FC_SESS_DATA_ENGINEER",
        "default_session": "qwen_data_engineer",
        "agent_name": "DataEngineer",
        "system_prompt": (
            "Tu es DATA_ENGINEER. Tu sécurises le contrat de données, "
            "pipeline/cache/fallback et qualité des sorties."
        ),
    },
    "security_engineer": {
        "env_var": "FC_SESS_SECURITY_ENGINEER",
        "default_session": "qwen_security_engineer",
        "agent_name": "SecurityEngineer",
        "system_prompt": (
            "Tu es SECURITY_ENGINEER. Tu analyses menaces, surfaces d'attaque, "
            "secrets, permissions et mitigations concrètes."
        ),
    },
    "devops_engineer": {
        "env_var": "FC_SESS_DEVOPS_ENGINEER",
        "default_session": "qwen_devops_engineer",
        "agent_name": "DevOpsEngineer",
        "system_prompt": (
            "Tu es DEVOPS_ENGINEER. Tu optimises CI/CD, observabilité, "
            "rollback, SLO et robustesse opérationnelle."
        ),
    },
}
SPECIALIST_TEAM_PROFILES: Dict[str, Tuple[str, ...]] = {
    "core": tuple(),
    "architecture": ("analyst", "architect"),
    "engineering": (
        "analyst",
        "architect",
        "backend_engineer",
        "frontend_engineer",
        "data_engineer",
        "security_engineer",
        "devops_engineer",
    ),
    "full": (
        "analyst",
        "architect",
        "backend_engineer",
        "frontend_engineer",
        "data_engineer",
        "security_engineer",
        "devops_engineer",
    ),
}
SPECIALIST_ROLE_ALIASES: Dict[str, str] = {
    "analysts": "analyst",
    "analysis": "analyst",
    "architects": "architect",
    "backend": "backend_engineer",
    "backend_dev": "backend_engineer",
    "backend_developer": "backend_engineer",
    "frontend": "frontend_engineer",
    "frontend_dev": "frontend_engineer",
    "frontend_developer": "frontend_engineer",
    "data": "data_engineer",
    "security": "security_engineer",
    "sec": "security_engineer",
    "devops": "devops_engineer",
    "sre": "devops_engineer",
}

# capture tuning
CAPTURE_LAST_LINES = int(os.environ.get("FC_CAPTURE_LAST_LINES", "4000"))
TMUX_HISTORY_LIMIT = int(os.environ.get("FC_TMUX_HISTORY_LIMIT", "200000"))


def now_id() -> str:
    # millisecond precision to avoid run_id collisions on fast repeated launches
    return datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]


def normalize_role_token(raw: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "_", (raw or "").strip().lower()).strip("_")
    return token


def canonical_specialist_role(raw: str) -> str:
    token = normalize_role_token(raw)
    if not token:
        return ""
    token = SPECIALIST_ROLE_ALIASES.get(token, token)
    if token in SPECIALIST_ROLE_SPECS:
        return token
    return ""


def parse_specialist_roles(raw: str) -> List[str]:
    txt = (raw or "").strip()
    if not txt:
        return []
    parts = [p.strip() for p in re.split(r"[;,]", txt) if p.strip()]
    out: List[str] = []
    for part in parts:
        role = canonical_specialist_role(part)
        if role and role not in out:
            out.append(role)
    return out


def specialist_roles_for_profile(profile_name: str) -> List[str]:
    key = normalize_role_token(profile_name) or "core"
    if key not in SPECIALIST_TEAM_PROFILES:
        key = "core"
    return list(SPECIALIST_TEAM_PROFILES.get(key, tuple()))


def resolve_specialist_roles(
    *,
    team_profile: str,
    specialists_raw: str,
    explicit_roles: Optional[List[str]] = None,
    with_architect: bool = False,
) -> List[str]:
    out: List[str] = []

    def add(role_name: str) -> None:
        if role_name and role_name not in out:
            out.append(role_name)

    for role_name in specialist_roles_for_profile(team_profile):
        add(role_name)
    for role_name in parse_specialist_roles(specialists_raw):
        add(role_name)
    for role_name in explicit_roles or []:
        add(canonical_specialist_role(role_name))
    if with_architect:
        add("architect")
    return out


def parse_role_session_pairs(raw: str) -> Dict[str, str]:
    """
    Parse "role=session" pairs separated by comma or semicolon.
    Example: "planner=qwen_planner;dev=qwen_dev,security=qwen_security"
    """
    out: Dict[str, str] = {}
    txt = (raw or "").strip()
    if not txt:
        return out
    parts = [p.strip() for p in re.split(r"[;,]", txt) if p.strip()]
    for part in parts:
        if "=" not in part:
            continue
        role, sess = part.split("=", 1)
        role = role.strip().lower()
        sess = sess.strip()
        specialist_role = canonical_specialist_role(role)
        if specialist_role:
            role = specialist_role
        if not role or not sess:
            continue
        if not re.fullmatch(r"[a-z0-9_.-]+", role):
            continue
        if not re.fullmatch(r"[a-zA-Z0-9_.:-]+", sess):
            continue
        out[role] = sess
    return out


def parse_role_list(raw: str, default: Tuple[str, ...] = CORE_STATUS_ROLES_DEFAULT) -> List[str]:
    """
    Parse a role list from comma/semicolon separated text.
    Example: "planner,dev;tester,qa"
    """
    txt = (raw or "").strip()
    if not txt:
        return list(default)
    parts = [p.strip().lower() for p in re.split(r"[;,]", txt) if p.strip()]
    out: List[str] = []
    for role in parts:
        specialist_role = canonical_specialist_role(role)
        if specialist_role:
            role = specialist_role
        if re.fullmatch(r"[a-z0-9_.-]+", role) and role not in out:
            out.append(role)
    return out or list(default)


def build_sessions() -> Dict[str, str]:
    base = {
        "planner": os.environ.get("FC_SESS_PLANNER", "qwen_planner"),
        "dev": os.environ.get("FC_SESS_DEV", "qwen_dev"),
        "tester": os.environ.get("FC_SESS_TESTER", "qwen_tester"),
        "qa": os.environ.get("FC_SESS_QA", "qwen_qa"),
    }
    extra = parse_role_session_pairs(os.environ.get("FC_EXTRA_SESSIONS", ""))
    base.update(extra)
    return base


SESSIONS: Dict[str, str] = build_sessions()


def build_default_path_override() -> str:
    parts: List[str] = []
    if VENV_BIN.exists():
        parts.append(str(VENV_BIN))
    parts.extend([
        "/opt/homebrew/bin",
        "/usr/local/bin",
        os.environ.get("PATH", ""),
    ])
    return ":".join([p for p in parts if p])


DEFAULT_PATH_OVERRIDE = build_default_path_override()
NODE_BIN_DEFAULT = os.environ.get("FC_NODE_BIN", shutil.which("node") or "node")
SDK_BRIDGE_DEFAULT = Path(
    os.environ.get("FC_QWEN_SDK_BRIDGE", str(PROJECT_DIR / "scripts" / "qwen_sdk_prompt.mjs"))
).expanduser().resolve()
SDK_PERMISSION_MODES = {"default", "plan", "auto-edit", "yolo"}
SDK_SESSION_STATE_FILE = Path(
    os.environ.get("FC_QWEN_SDK_SESSION_STATE_FILE", str(APP_LOG_DIR_DEFAULT / "sdk_sessions.json"))
).expanduser().resolve()
AGENT_MEMORY_DIR = Path(
    os.environ.get("FC_AGENT_MEMORY_DIR", str(APP_LOG_DIR_DEFAULT / "agent-memory"))
).expanduser().resolve()
AGENT_MEMORY_MAX_ENTRIES = int(os.environ.get("FC_AGENT_MEMORY_MAX_ENTRIES", "200"))
AGENT_MEMORY_PROMPT_ENTRIES = int(os.environ.get("FC_AGENT_MEMORY_PROMPT_ENTRIES", "8"))
AGENT_MEMORY_PROMPT_CHARS = int(os.environ.get("FC_AGENT_MEMORY_PROMPT_CHARS", "2200"))

ACTIVE_AGENT_BIN = os.environ.get("FC_AGENT_BIN", "qwen").strip() or "qwen"
ACTIVE_AGENT_CLI_NAME = Path(ACTIVE_AGENT_BIN).name.lower()


def _cli_name_from_bin(agent_bin: str) -> str:
    name = Path((agent_bin or "").strip() or "qwen").name.lower()
    return name or "qwen"


def set_active_agent_cli(agent_bin: str) -> None:
    global ACTIVE_AGENT_BIN, ACTIVE_AGENT_CLI_NAME
    ACTIVE_AGENT_BIN = (agent_bin or "").strip() or "qwen"
    ACTIVE_AGENT_CLI_NAME = _cli_name_from_bin(ACTIVE_AGENT_BIN)


def active_agent_cli_name() -> str:
    return ACTIVE_AGENT_CLI_NAME or "qwen"


def is_active_qwen_cli() -> bool:
    return active_agent_cli_name() == "qwen"


def _relpath_or_abs(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_DIR))
    except Exception:
        return str(path.resolve())


API_ENDPOINT_BEST_PRACTICES_DOC = Path(
    os.environ.get(
        "FC_API_ENDPOINT_BEST_PRACTICES_DOC",
        str(PROJECT_DIR / "docs" / "ops" / "API_ENDPOINT_BEST_PRACTICES.md"),
    )
).expanduser().resolve()


def api_best_practices_doc_reference() -> str:
    return _relpath_or_abs(API_ENDPOINT_BEST_PRACTICES_DOC)


def ensure_api_best_practices_doc(required: bool = True) -> Path:
    doc = API_ENDPOINT_BEST_PRACTICES_DOC
    if required and not doc.exists():
        _die(
            "Référence API obligatoire introuvable: "
            f"{doc}\nCrée/restaure docs/ops/API_ENDPOINT_BEST_PRACTICES.md avant exécution."
        )
    return doc


def api_best_practices_guidance_block() -> str:
    doc_ref = api_best_practices_doc_reference()
    return dedent(f"""
    Doc de référence: `{doc_ref}`
    Checklist obligatoire si endpoint/API modifié:
    - Contrat stable: `ok/data` + `generated_at/source/filters_applied/stats/warnings`
    - Cache: clé déterministe, TTL, eviction, `cache.hit/age_seconds/ttl_seconds`
    - Fallback: never-empty, `error/message/source` explicite (`*_fallback`)
    - Validation: test contrat + test cache-hit au 2e appel + gate backend PASS
    """).strip()


AGENT_ACTIVITY_IGNORE_PATHS = {
    _relpath_or_abs(SDK_SESSION_STATE_FILE),
}
AGENT_ACTIVITY_IGNORE_PREFIXES = {
    _relpath_or_abs(RUNS_DIR_DEFAULT),
    _relpath_or_abs(AGENT_MEMORY_DIR),
}


# ==============================================================================
# Optional Sentry (orchestrator telemetry)
# ==============================================================================

_SENTRY_INITIALIZED = False
_SENTRY_ENABLED = False


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _clamp_rate(value: str, default: float) -> float:
    try:
        parsed = float(value)
    except Exception:
        return default
    return max(0.0, min(1.0, parsed))


def init_orchestrator_sentry() -> bool:
    """
    Initialize Sentry only when a DSN is configured.
    Priority:
    - ORCH_SENTRY_DSN
    - SENTRY_DSN
    """
    global _SENTRY_INITIALIZED, _SENTRY_ENABLED

    if _SENTRY_INITIALIZED:
        return _SENTRY_ENABLED

    dsn = (os.environ.get("ORCH_SENTRY_DSN") or os.environ.get("SENTRY_DSN") or "").strip()
    if not dsn:
        _SENTRY_INITIALIZED = True
        _SENTRY_ENABLED = False
        return False

    if sentry_sdk is None:
        print("⚠️  Sentry DSN configuré mais sentry-sdk est absent. `pip install sentry-sdk`", file=sys.stderr)
        _SENTRY_INITIALIZED = True
        _SENTRY_ENABLED = False
        return False

    traces_rate = _clamp_rate(os.environ.get("ORCH_SENTRY_TRACES_SAMPLE_RATE", "0.1"), 0.1)
    profile_session_rate = _clamp_rate(
        os.environ.get("ORCH_SENTRY_PROFILE_SESSION_SAMPLE_RATE", os.environ.get("ORCH_SENTRY_PROFILES_SAMPLE_RATE", "0.0")),
        0.0,
    )
    profiles_rate = _clamp_rate(
        os.environ.get("ORCH_SENTRY_PROFILES_SAMPLE_RATE", str(profile_session_rate)),
        profile_session_rate,
    )
    environment = (
        os.environ.get("ORCH_SENTRY_ENVIRONMENT")
        or os.environ.get("SENTRY_ENVIRONMENT")
        or os.environ.get("APP_ENV")
        or os.environ.get("ENVIRONMENT")
        or "development"
    )
    release = os.environ.get("ORCH_SENTRY_RELEASE") or os.environ.get("SENTRY_RELEASE")
    enable_logs = _env_bool("ORCH_SENTRY_ENABLE_LOGS", default=True)
    send_default_pii = _env_bool("ORCH_SENTRY_SEND_DEFAULT_PII", default=False)

    try:
        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=traces_rate,
            profile_session_sample_rate=profile_session_rate,
            profiles_sample_rate=profiles_rate,
            profile_lifecycle="trace",
            enable_logs=enable_logs,
            send_default_pii=send_default_pii,
            environment=environment,
            release=release,
        )
    except Exception as e:
        print(f"⚠️  Impossible d'initialiser Sentry: {e}", file=sys.stderr)
        _SENTRY_INITIALIZED = True
        _SENTRY_ENABLED = False
        return False

    _SENTRY_INITIALIZED = True
    _SENTRY_ENABLED = True
    sentry_sdk.set_tag("component", "qwen_orchestrator")
    sentry_sdk.set_tag("orchestrator.script", "scripts/qwen_orchestrator.py")
    sentry_sdk.set_tag("orchestrator.project_dir", str(PROJECT_DIR))
    return True


def sentry_set_context(*, run_id: Optional[str] = None, mode: Optional[str] = None, tmux_cmd: Optional[str] = None) -> None:
    if not _SENTRY_ENABLED or sentry_sdk is None:
        return
    if run_id:
        sentry_sdk.set_tag("orchestrator.run_id", run_id)
    if mode:
        sentry_sdk.set_tag("orchestrator.mode", mode)
    if tmux_cmd:
        sentry_sdk.set_tag("orchestrator.tmux_cmd", tmux_cmd)


def capture_orchestrator_exception(exc: BaseException, *, context: Optional[Dict[str, Any]] = None, flush: bool = True) -> None:
    if not _SENTRY_ENABLED or sentry_sdk is None:
        return
    with sentry_sdk.new_scope() as scope:
        for key, value in (context or {}).items():
            scope.set_extra(str(key), value)
        sentry_sdk.capture_exception(exc)
    if flush:
        sentry_sdk.flush(timeout=2.0)


def sentry_add_breadcrumb(
    message: str,
    *,
    category: str = "orchestrator",
    level: str = "info",
    data: Optional[Dict[str, Any]] = None,
) -> None:
    if not _SENTRY_ENABLED or sentry_sdk is None:
        return
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data or {},
    )


# ==============================================================================
# Strict requirements (NO fallback)
# ==============================================================================

def _die(msg: str) -> None:
    raise RuntimeError(msg)


def _argv_flag_value(argv: List[str], flag: str) -> str:
    for i, token in enumerate(argv):
        if token == flag and i + 1 < len(argv):
            return str(argv[i + 1] or "")
        if token.startswith(flag + "="):
            return token.split("=", 1)[1]
    return ""


def _tmux_cmd_from_argv(argv: List[str]) -> str:
    return (_argv_flag_value(argv, "--tmux-cmd") or "").strip().lower()


def should_skip_venv_reexec(argv: List[str]) -> bool:
    """
    For lightweight tmux management commands used by cron, avoid unnecessary
    venv re-exec to reduce failure surface and startup latency.
    """
    if not _env_bool("FC_SKIP_VENV_FOR_TMUX_CMDS", default=True):
        return False
    if "--print-usage" in argv:
        return True
    cmd = _tmux_cmd_from_argv(argv)
    return cmd in {
        "status",
        "health",
        "start",
        "stop",
        "restart",
        "attach",
        "doctor",
        "cleanup",
        "clear",
        "ping",
        "prompt",
    }


def ensure_venv_or_reexec() -> None:
    """
    Si la venv backend existe mais que l'environnement courant n'est pas la venv,
    on relance le script via VENV_PY.
    """
    if not VENV_PY.exists():
        return

    venv_root = VENV_BIN.parent.resolve()
    in_venv = (Path(sys.prefix).resolve() == venv_root) and (getattr(sys, "base_prefix", sys.prefix) != sys.prefix)
    if in_venv:
        return

    os.execv(str(VENV_PY), [str(VENV_PY), *sys.argv])


def require_module(name: str) -> Any:
    try:
        return __import__(name)
    except Exception as e:
        _die(f"Module requis introuvable: '{name}'. Installe-le puis relance.\nDétail: {e}")


def run(
    cmd: List[str],
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    check: bool = False,
    capture: bool = True,
    timeout: Optional[int] = None,
) -> subprocess.CompletedProcess:
    if capture:
        stdout = subprocess.PIPE
        stderr = subprocess.STDOUT
    else:
        stdout = subprocess.DEVNULL
        stderr = subprocess.DEVNULL

    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        stdout=stdout,
        stderr=stderr,
        check=check,
        timeout=timeout,
    )


def which(bin_name: str) -> Optional[str]:
    try:
        cp = run(["which", bin_name], capture=True)
        out = (cp.stdout or "").strip()
        return out or None
    except Exception:
        return None


def require_bin(bin_name: str) -> str:
    p = which(bin_name)
    if not p:
        _die(f"Binaire requis introuvable: '{bin_name}'. Installe-le (ex: brew install {bin_name}).")
    return p


def require_executable(path_or_name: str) -> str:
    # path explicite
    if os.path.sep in path_or_name or path_or_name.startswith("."):
        p = Path(path_or_name).expanduser().resolve()
        if not p.exists():
            _die(f"Exécutable requis introuvable: {p}")
        if not os.access(str(p), os.X_OK):
            _die(f"Exécutable requis non-exécutable: {p}")
        return str(p)

    # sinon via PATH
    return require_bin(path_or_name)


def ensure_project_root_exists() -> None:
    if not PROJECT_DIR.exists():
        _die(f"PROJECT_DIR introuvable: {PROJECT_DIR}")


def ensure_project_exists() -> None:
    ensure_project_root_exists()
    if not BACKEND_DIR.exists():
        _die(f"BACKEND_DIR introuvable: {BACKEND_DIR}")


# ==============================================================================
# tmux helpers
# ==============================================================================

def ensure_tmux_exists() -> None:
    require_bin("tmux")


def tmux_start_server() -> None:
    run(["tmux", "start-server"], capture=False)


def tmux_target(session: str) -> str:
    return f"{session}.0"


def tmux_has_session(name: str) -> bool:
    tmux_start_server()
    cp = run(["tmux", "has-session", "-t", name], capture=False)
    return cp.returncode == 0


def tmux_kill_session(name: str) -> None:
    tmux_start_server()
    if tmux_has_session(name):
        run(["tmux", "kill-session", "-t", name], capture=False)


def tmux_new_session(name: str, bash_cmd: str) -> None:
    tmux_start_server()
    run(
        ["tmux", "new-session", "-d", "-s", name, "bash", "-lc", bash_cmd],
        capture=False,
        check=True,
    )


def tmux_set_option(session: str, option: str, value: str) -> None:
    tmux_start_server()
    run(["tmux", "set-option", "-t", session, option, value], capture=False)


def tmux_list_sessions() -> List[str]:
    tmux_start_server()
    cp = run(["tmux", "list-sessions", "-F", "#{session_name}"], capture=True)
    if cp.returncode != 0:
        return []
    return [ln.strip() for ln in (cp.stdout or "").splitlines() if ln.strip()]


def tmux_attach(session: str) -> int:
    tmux_start_server()
    if os.environ.get("TMUX"):
        # Already inside tmux: switch client instead of nested attach.
        cp = subprocess.run(["tmux", "switch-client", "-t", session], check=False)
        return cp.returncode
    cp = subprocess.run(["tmux", "attach", "-t", session], check=False)
    return cp.returncode


def tmux_pipe_pane(session: str, log_file: Path, force_repipe: bool = False) -> None:
    tmux_start_server()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    target = tmux_target(session)

    if force_repipe:
        tmux_unpipe_pane(session)

    cleaner = PROJECT_DIR / "scripts" / "tmux_log_clean_stream.py"
    if cleaner.exists():
        cmd = (
            f"python3 -u {shlex.quote(str(cleaner))} >> {shlex.quote(str(log_file))}"
        )
    else:
        cmd = f"cat >> {shlex.quote(str(log_file))}"
    run(["tmux", "pipe-pane", "-o", "-t", target, cmd], capture=False)


def tmux_unpipe_pane(session: str) -> None:
    tmux_start_server()
    target = tmux_target(session)
    run(["tmux", "pipe-pane", "-t", target], capture=False)


def tmux_capture(session: str, last_lines: int = CAPTURE_LAST_LINES) -> str:
    """
    Capture plus robuste:
    - -J : join wrapped lines
    - -S -N : start from last N lines of history
    - -E -1 : end at last line
    """
    tmux_start_server()
    target = tmux_target(session)
    n = max(200, int(last_lines))
    cp = run(["tmux", "capture-pane", "-p", "-J", "-S", f"-{n}", "-E", "-1", "-t", target], capture=True)
    return cp.stdout or ""


def tmux_send_keys(session: str, text: str) -> None:
    tmux_start_server()
    target = tmux_target(session)
    payload = text or ""
    # Avoid "Argument list too long" when prompt/context gets large.
    if len(payload) <= 1200 and "\n" not in payload:
        run(["tmux", "send-keys", "-t", target, payload, "C-m"], capture=False)
        return

    buffer_name = f"orchestrator_{int(time.time() * 1000)}"
    tmp_path: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as tmp:
            tmp.write(payload)
            tmp_path = tmp.name
        run(["tmux", "load-buffer", "-b", buffer_name, tmp_path], capture=False)
        run(["tmux", "paste-buffer", "-d", "-b", buffer_name, "-t", target], capture=False)
        run(["tmux", "send-keys", "-t", target, "C-m"], capture=False)
    finally:
        try:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass


def tmux_clear_screen(session: str) -> None:
    tmux_start_server()
    target = tmux_target(session)
    run(["tmux", "send-keys", "-t", target, "C-l"], capture=False)


def tmux_clear_history(session: str) -> None:
    tmux_start_server()
    target = tmux_target(session)
    run(["tmux", "clear-history", "-t", target], capture=False)


def tmux_current_command(session: str) -> str:
    tmux_start_server()
    target = tmux_target(session)
    cp = run(["tmux", "display-message", "-p", "-t", target, "#{pane_current_command}"], capture=True)
    return (cp.stdout or "").strip().lower()


def tmux_pane_pid(session: str) -> Optional[int]:
    tmux_start_server()
    target = tmux_target(session)
    cp = run(["tmux", "display-message", "-p", "-t", target, "#{pane_pid}"], capture=True)
    raw = (cp.stdout or "").strip()
    try:
        pid = int(raw)
    except Exception:
        return None
    return pid if pid > 0 else None


# ==============================================================================
# Run dirs / transcripts / manifest / snapshots
# ==============================================================================

@dataclass
class RunCtx:
    run_id: str
    run_dir: Path
    tmux_dir: Path
    snapshots_dir: Path
    transcript_path: Path
    manifest_path: Path
    agent_bus_path: Path
    agent_board_path: Path
    events_path: Path
    activity_summary_path: Path


def update_latest_run_pointer(runs_dir: Path, run_dir: Path) -> None:
    """
    Expose un pointeur stable vers la dernière exécution:
    - symlink: <runs_dir>/latest
    - fallback fichier texte: <runs_dir>/latest_run.txt
    """
    latest_link = runs_dir / "latest"
    latest_txt = runs_dir / "latest_run.txt"

    try:
        if latest_link.exists() or latest_link.is_symlink():
            latest_link.unlink()
        latest_link.symlink_to(run_dir.name)
    except Exception:
        # En fallback (FS qui bloque les symlinks), on garde un pointeur texte.
        latest_txt.write_text(str(run_dir) + "\n", encoding="utf-8")


def create_run_ctx(runs_dir: Path) -> RunCtx:
    run_id = now_id()
    run_dir = runs_dir / run_id
    tmux_dir = run_dir / "tmux"
    snapshots_dir = run_dir / "snapshots"
    run_dir.mkdir(parents=True, exist_ok=True)
    tmux_dir.mkdir(parents=True, exist_ok=True)
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    update_latest_run_pointer(runs_dir, run_dir)

    return RunCtx(
        run_id=run_id,
        run_dir=run_dir,
        tmux_dir=tmux_dir,
        snapshots_dir=snapshots_dir,
        transcript_path=run_dir / "transcript.md",
        manifest_path=run_dir / "run.json",
        agent_bus_path=run_dir / "agent_bus.jsonl",
        agent_board_path=run_dir / "agent_board.md",
        events_path=run_dir / "events.jsonl",
        activity_summary_path=run_dir / "agent_activity.json",
    )


def write_manifest(ctx: RunCtx, feature: str, qwen_bin: str, extra: Optional[Dict[str, Any]] = None) -> None:
    data: Dict[str, Any] = {
        "run_id": ctx.run_id,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "feature": feature,
        "project_dir": str(PROJECT_DIR),
        "runs_dir": str(ctx.run_dir.parent),
        "backend_dir": str(BACKEND_DIR),
        "qwen_bin": qwen_bin,
        "sessions": {k: v for k, v in SESSIONS.items()},
        "capture_last_lines": CAPTURE_LAST_LINES,
        "tmux_history_limit": TMUX_HISTORY_LIMIT,
        "references": {
            "api_endpoint_best_practices_doc": api_best_practices_doc_reference(),
            "api_endpoint_best_practices_exists": API_ENDPOINT_BEST_PRACTICES_DOC.exists(),
        },
        "artifacts": {
            "transcript": str(ctx.transcript_path),
            "agent_bus": str(ctx.agent_bus_path),
            "agent_board": str(ctx.agent_board_path),
            "events": str(ctx.events_path),
            "agent_activity": str(ctx.activity_summary_path),
            "snapshots_dir": str(ctx.snapshots_dir),
            "tmux_dir": str(ctx.tmux_dir),
        },
    }
    if extra:
        data.update(extra)
    ctx.manifest_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def transcript_append(ctx: RunCtx, role: str, kind: str, content: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    block = f"\n## [{ts}] {role} — {kind}\n\n```\n{(content or '').rstrip()}\n```\n"
    with ctx.transcript_path.open("a", encoding="utf-8") as f:
        f.write(block)


def event_append(ctx: RunCtx, event: Dict[str, Any]) -> None:
    row: Dict[str, Any] = {"ts": datetime.now().isoformat(timespec="milliseconds")}
    row.update(event)
    with ctx.events_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _git_lines(args: List[str]) -> List[str]:
    cp = run(["git", *args], cwd=PROJECT_DIR, capture=True)
    if cp.returncode != 0:
        return []
    return [ln.strip() for ln in (cp.stdout or "").splitlines() if ln.strip()]


def _sha1_file(path: Path) -> str:
    if not path.exists():
        return "<missing>"
    if not path.is_file():
        return "<not-file>"
    max_bytes = 2_000_000
    size = path.stat().st_size
    if size > max_bytes:
        st = path.stat()
        return f"<large:{size}:{int(st.st_mtime)}>"
    h = hashlib.sha1()
    with path.open("rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def git_dirty_file_signatures(limit: int = AGENT_EVENTS_FILE_LIMIT) -> Dict[str, str]:
    files: List[str] = []
    files.extend(_git_lines(["diff", "--name-only"]))
    files.extend(_git_lines(["diff", "--name-only", "--cached"]))
    files.extend(_git_lines(["ls-files", "--others", "--exclude-standard"]))
    uniq = sorted(set(files))
    if limit > 0:
        uniq = uniq[: int(limit)]

    out: Dict[str, str] = {}
    for rel in uniq:
        full = PROJECT_DIR / rel
        out[rel] = _sha1_file(full)
    return out


def _changed_files_between(pre: Dict[str, str], post: Dict[str, str]) -> Dict[str, List[str]]:
    touched: List[str] = []
    created: List[str] = []
    deleted: List[str] = []
    for path in sorted(set(pre.keys()) | set(post.keys())):
        if path in AGENT_ACTIVITY_IGNORE_PATHS:
            continue
        if any(path == pref or path.startswith(pref + "/") for pref in AGENT_ACTIVITY_IGNORE_PREFIXES):
            continue
        a = pre.get(path)
        b = post.get(path)
        if a == b:
            continue
        touched.append(path)
        if path not in pre and path in post:
            created.append(path)
        if path in pre and post.get(path) == "<missing>":
            deleted.append(path)
    return {"touched": touched, "created": created, "deleted": deleted}


def _delta_text(previous: str, current: str) -> str:
    old = previous or ""
    new = current or ""
    if new.startswith(old):
        return new[len(old):]
    tail = old[-2000:]
    if tail:
        idx = new.find(tail)
        if idx != -1:
            return new[idx + len(tail):]
    return new


def extract_shell_commands(text: str, max_cmds: int = AGENT_EVENTS_MAX_COMMANDS) -> List[str]:
    lines = [(ln or "").strip() for ln in (text or "").splitlines()]
    cmds: List[str] = []
    in_code = False
    code_lang = ""
    for ln in lines:
        if not ln:
            continue
        if ln.startswith("```"):
            fence = ln.strip("`").strip().lower()
            if in_code:
                in_code = False
                code_lang = ""
            else:
                in_code = True
                code_lang = fence
            continue

        if in_code and code_lang in {"", "bash", "sh", "shell", "zsh"}:
            if ln.startswith("#"):
                continue
            if ln.lower().startswith(("output:", "result:", "expected:")):
                continue
            cmds.append(ln)
            continue

        m = re.match(r"^\$\s+(.+)$", ln)
        if m:
            cmds.append(m.group(1).strip())
            continue
        m = re.match(r"^(?:run|cmd|command)\s*:\s*(.+)$", ln, flags=re.IGNORECASE)
        if m:
            cmds.append(m.group(1).strip())
            continue
    if not cmds:
        return []
    out: List[str] = []
    for c in cmds:
        if c not in out:
            out.append(c)
        if len(out) >= max_cmds:
            break
    return out


def _required_sections_for_agent(agent_name: str, execution_profile: str) -> Tuple[str, ...]:
    if execution_profile != "exemplary":
        return tuple()
    name = (agent_name or "").strip().lower()
    mapping: Dict[str, Tuple[str, ...]] = {
        "planner": ("PLAN", "COMMANDS", "RISKS", "NEXT_ACTION_UNIQUE", "VERDICT", "BLOCKER_ID"),
        "architect": ("ARCH_CHECK", "RISKS", "DECISION", "NEXT_ACTION_UNIQUE", "VERDICT", "BLOCKER_ID"),
        "analyst": ("ANALYSIS", "ACCEPTANCE", "RISKS", "NEXT_ACTION_UNIQUE", "VERDICT", "BLOCKER_ID"),
        "dev": ("DELTA", "COMMANDS", "TESTS", "RISKS", "NEXT_ACTION_UNIQUE", "VERDICT", "BLOCKER_ID"),
        "backendengineer": ("DELTA", "COMMANDS", "TESTS", "RISKS", "NEXT_ACTION_UNIQUE", "VERDICT", "BLOCKER_ID"),
        "frontendengineer": ("DELTA", "COMMANDS", "TESTS", "RISKS", "NEXT_ACTION_UNIQUE", "VERDICT", "BLOCKER_ID"),
        "dataengineer": ("DELTA", "COMMANDS", "TESTS", "RISKS", "NEXT_ACTION_UNIQUE", "VERDICT", "BLOCKER_ID"),
        "securityengineer": ("DELTA", "COMMANDS", "TESTS", "RISKS", "NEXT_ACTION_UNIQUE", "VERDICT", "BLOCKER_ID"),
        "devopsengineer": ("DELTA", "COMMANDS", "TESTS", "RISKS", "NEXT_ACTION_UNIQUE", "VERDICT", "BLOCKER_ID"),
        "tester": ("TEST_PLAN", "COMMANDS", "EXPECTED", "RISKS", "NEXT_ACTION_UNIQUE", "VERDICT", "BLOCKER_ID"),
        "qualityobserver": ("STATE", "EVIDENCE", "RISKS", "PRIORITIES", "VERDICT", "BLOCKER_ID"),
        "deliverymanager": ("DECISION", "RISKS", "ACTIONS", "VERDICT", "BLOCKER_ID", "NEXT_ACTION_UNIQUE"),
        "codexreviewer": ("DECISION", "FINDINGS", "RISKS", "VERDICT", "BLOCKER_ID", "NEXT_ACTION_UNIQUE"),
    }
    return mapping.get(name, ("SUMMARY", "COMMANDS", "RISKS", "NEXT_ACTION_UNIQUE", "VERDICT", "BLOCKER_ID"))


def _missing_required_sections(text: str, required_sections: Tuple[str, ...]) -> List[str]:
    payload = (text or "").strip()
    if not payload or not required_sections:
        return []
    missing: List[str] = []
    for section in required_sections:
        pattern = rf"(?im)^\s*{re.escape(section)}\s*[:\-]"
        if not re.search(pattern, payload):
            missing.append(section)
    return missing


def classify_agent_response(text: str, required_sections: Optional[Tuple[str, ...]] = None) -> Dict[str, Any]:
    payload = (text or "").strip()
    low = payload.lower()
    asks_question = "?" in payload
    likely_meta = _looks_like_internal_reasoning(payload)
    has_code_block = "```" in payload
    too_long = len(payload) > AGENT_RESPONSE_SOFT_LIMIT
    missing_sections = _missing_required_sections(payload, required_sections or tuple())
    warnings: List[str] = []
    if likely_meta:
        warnings.append("meta_reasoning")
    if asks_question:
        warnings.append("asks_question")
    if too_long:
        warnings.append("too_long")
    if missing_sections:
        warnings.append("missing_sections")
    return {
        "asks_question": asks_question,
        "likely_meta": likely_meta,
        "has_code_block": has_code_block,
        "too_long": too_long,
        "missing_sections": missing_sections,
        "warnings": warnings,
    }


def _agent_memory_file(agent_name: str) -> Path:
    raw = str(agent_name or "agent").strip().lower()
    safe = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("_") or "agent"
    return AGENT_MEMORY_DIR / f"{safe}.jsonl"


def append_agent_memory(
    agent_name: str,
    *,
    run_id: str,
    feature: str,
    reply: str,
    commands: List[str],
    files_touched: List[str],
    warnings: List[str],
) -> None:
    AGENT_MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    mem_file = _agent_memory_file(agent_name)
    rows: List[Dict[str, Any]] = []
    if mem_file.exists():
        for ln in mem_file.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            try:
                row = json.loads(ln)
            except Exception:
                continue
            if isinstance(row, dict):
                rows.append(row)

    summary = _compact_bus_content(reply, max_chars=900)
    row = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "run_id": run_id,
        "feature": _compact_bus_content(feature, max_chars=280),
        "summary": summary,
        "commands": commands[: AGENT_EVENTS_MAX_COMMANDS],
        "files_touched": files_touched[: AGENT_EVENTS_FILE_LIMIT],
        "warnings": warnings[:20],
    }
    rows.append(row)
    if len(rows) > AGENT_MEMORY_MAX_ENTRIES:
        rows = rows[-AGENT_MEMORY_MAX_ENTRIES:]

    with mem_file.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def load_agent_memory_context(
    agent_name: str,
    *,
    max_entries: int = AGENT_MEMORY_PROMPT_ENTRIES,
    max_chars: int = AGENT_MEMORY_PROMPT_CHARS,
) -> str:
    mem_file = _agent_memory_file(agent_name)
    if not mem_file.exists():
        return ""
    rows: List[Dict[str, Any]] = []
    for ln in mem_file.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        try:
            row = json.loads(ln)
        except Exception:
            continue
        if isinstance(row, dict):
            rows.append(row)
    if not rows:
        return ""
    tail = rows[-max(1, int(max_entries)):]
    out: List[str] = []
    budget = max(300, int(max_chars))
    for r in tail:
        ts = str(r.get("ts") or "").strip()
        summary = str(r.get("summary") or "").strip()
        commands = r.get("commands") or []
        files = r.get("files_touched") or []
        line = f"- [{ts}] {summary}"
        if commands:
            line += f" | cmd: {commands[0]}"
        if files:
            line += f" | files: {', '.join(files[:2])}"
        if len(line) > 550:
            line = line[:550].rstrip() + " ..."
        if len(line) > budget:
            break
        out.append(line)
        budget -= len(line)
        if budget <= 0:
            break
    return "\n".join(out).strip()


def _compact_bus_content(text: str, *, max_chars: int) -> str:
    content = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not content:
        return ""
    content = re.sub(r"\n{3,}", "\n\n", content)
    limit = max(200, int(max_chars))
    if len(content) > limit:
        content = content[:limit].rstrip() + "\n...[tronqué]..."
    return content


def agent_bus_append(ctx: RunCtx, *, sender: str, recipient: str, kind: str, content: str) -> None:
    kind_norm = (kind or "note").strip().lower() or "note"
    cap = 420 if kind_norm in {"prompt", "dispatch"} else AGENT_BUS_MAX_CONTENT_CHARS
    row = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "sender": sender,
        "recipient": recipient,
        "kind": kind_norm,
        "content": _compact_bus_content(content, max_chars=cap),
    }
    with ctx.agent_bus_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def agent_bus_recent_text(
    ctx: RunCtx,
    *,
    limit: int = 8,
    exclude_sender: Optional[str] = None,
    include_kinds: Optional[Tuple[str, ...]] = None,
) -> str:
    if not ctx.agent_bus_path.exists():
        return ""
    include = {k.strip().lower() for k in (include_kinds or ()) if (k or "").strip()}
    rows: List[Dict[str, Any]] = []
    try:
        for line in ctx.agent_bus_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if not isinstance(row, dict):
                continue
            sender = str(row.get("sender") or "")
            if exclude_sender and sender == exclude_sender:
                continue
            kind = str(row.get("kind") or "").strip().lower()
            if include and kind not in include:
                continue
            rows.append(row)
    except Exception:
        return ""

    if not rows:
        return ""
    tail = rows[-max(1, int(limit)):]
    parts: List[str] = []
    for r in tail:
        content = (r.get("content") or "").strip()
        if len(content) > 900:
            content = content[:900].rstrip() + "\n...[tronqué]..."
        parts.append(
            f"[{r.get('sender','?')} -> {r.get('recipient','team')} | {r.get('kind','note')}]\n"
            f"{content}"
        )
    return "\n\n".join(parts).strip()


def agent_bus_write_board(ctx: RunCtx, *, max_rows: int = 80) -> None:
    if not ctx.agent_bus_path.exists():
        return
    lines: List[str] = []
    for ln in ctx.agent_bus_path.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            lines.append(ln.strip())
    if not lines:
        return
    if len(lines) > max_rows:
        lines = lines[-max_rows:]

    out: List[str] = ["# Agent Board", ""]
    for ln in lines:
        try:
            row = json.loads(ln)
        except Exception:
            continue
        ts = row.get("ts", "")
        sender = row.get("sender", "?")
        recipient = row.get("recipient", "team")
        kind = row.get("kind", "note")
        content = (row.get("content") or "").strip()
        if not content:
            continue
        out.append(f"## {ts} — {sender} -> {recipient} ({kind})")
        out.append("")
        out.append(content)
        out.append("")

    ctx.agent_board_path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")


def write_agent_activity_summary(ctx: RunCtx, summary: Dict[str, Any]) -> None:
    ctx.activity_summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def snapshot_all(ctx: RunCtx) -> None:
    for sess in sorted(set(SESSIONS.values())):
        snap = tmux_capture(sess, last_lines=CAPTURE_LAST_LINES)
        (ctx.snapshots_dir / f"{sess}.txt").write_text(snap, encoding="utf-8")


# ==============================================================================
# Logging (tmux raw) + rotation
# ==============================================================================

def rotate_if_too_big(session: str, log_file: Path, max_bytes: int) -> Path:
    if log_file.exists() and log_file.stat().st_size > max_bytes:
        ts = datetime.now().strftime("%H%M%S")
        new_file = log_file.parent / f"{session}_{ts}.log"
        tmux_pipe_pane(session, new_file, force_repipe=True)
        return new_file
    return log_file


# ==============================================================================
# Qwen session management
# ==============================================================================

def session_names() -> List[str]:
    return sorted(set(SESSIONS.values()))


def resolve_session(role_or_session: str) -> str:
    return SESSIONS.get(role_or_session, role_or_session)


def ensure_role_session(role: str, env_name: str, default_session: str) -> str:
    if role not in SESSIONS or not str(SESSIONS.get(role) or "").strip():
        SESSIONS[role] = os.environ.get(env_name, default_session)
    return SESSIONS[role]


def ensure_specialist_session(role: str) -> Optional[str]:
    canonical = canonical_specialist_role(role)
    if not canonical:
        return None
    spec = SPECIALIST_ROLE_SPECS.get(canonical) or {}
    env_name = str(spec.get("env_var") or "").strip()
    default_session = str(spec.get("default_session") or "").strip()
    if not env_name or not default_session:
        return None
    return ensure_role_session(canonical, env_name, default_session)


def ensure_specialist_sessions(roles: List[str]) -> List[str]:
    ensured: List[str] = []
    for role in roles:
        canonical = canonical_specialist_role(role)
        if not canonical or canonical in ensured:
            continue
        if ensure_specialist_session(canonical):
            ensured.append(canonical)
    return ensured


def apply_session_overrides(raw: str) -> None:
    overrides = parse_role_session_pairs(raw)
    if not overrides:
        return
    SESSIONS.update(overrides)


def _parse_env_exports(raw: str) -> List[str]:
    txt = (raw or "").strip()
    if not txt:
        return []
    parts = [p.strip() for p in re.split(r"[;,]", txt) if p.strip()]
    exports: List[str] = []
    for p in parts:
        if "=" not in p:
            continue
        k, v = p.split("=", 1)
        k = k.strip()
        v = v.strip()
        if k and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k):
            exports.append(f"export {k}={shlex.quote(v)}")
    return exports


def _parse_agent_exports(agent_cli_name: str) -> List[str]:
    exports: List[str] = []
    exports.extend(_parse_env_exports(os.environ.get("FC_AGENT_EXPORTS", "")))
    if agent_cli_name == "qwen":
        exports.extend(_parse_env_exports(os.environ.get("FC_QWEN_EXPORTS", "")))
    if agent_cli_name == "codex":
        exports.extend(_parse_env_exports(os.environ.get("FC_CODEX_EXPORTS", "")))
    return exports


def build_qwen_bash_cmd(qwen_bin: str, path_override: str, auto_confirm: bool) -> str:
    agent_cli_name = _cli_name_from_bin(qwen_bin)
    setup_cmds = [f"cd {shlex.quote(str(PROJECT_DIR))}"]

    venv_activate = VENV_BIN / "activate"
    if venv_activate.exists():
        setup_cmds.append(f"source {shlex.quote(str(venv_activate))}")

    setup_cmds.append(f"export PATH={shlex.quote(path_override)}")

    # qwen-code 0.4.0 can crash in TUI with "Invalid number of stops (< 2)"
    # when NO_COLOR=1 or TERM=dumb leads to no-color gradient config.
    if agent_cli_name == "qwen" and _env_bool("FC_QWEN_SANITIZE_COLOR_ENV", default=True):
        setup_cmds.append("unset NO_COLOR")
        setup_cmds.append('if [ "${TERM:-dumb}" = "dumb" ]; then export TERM=xterm-256color; fi')
        setup_cmds.append('export COLORTERM="${COLORTERM:-truecolor}"')
        setup_cmds.append('export FORCE_COLOR="${FORCE_COLOR:-1}"')

    if agent_cli_name == "qwen" and auto_confirm:
        setup_cmds.append("export QWEN_CODE_AUTO_CONFIRM=1")

    setup_cmds.extend(_parse_agent_exports(agent_cli_name))

    setup_cmds.append(f"{shlex.quote(qwen_bin)} || exec bash")
    return " && ".join(setup_cmds)


def qwen_start(
    qwen_bin: str,
    path_override: str,
    auto_confirm: bool,
    restart: bool,
    ctx: Optional[RunCtx],
    enable_tmux_logs: bool,
    clean_startup: bool,
) -> None:
    ensure_tmux_exists()
    ensure_project_exists()
    tmux_start_server()

    qwen_bin = require_executable(qwen_bin)
    set_active_agent_cli(qwen_bin)

    if restart:
        qwen_stop(all_sessions=True)

    bash_cmd = build_qwen_bash_cmd(qwen_bin=qwen_bin, path_override=path_override, auto_confirm=auto_confirm)

    for sess in session_names():
        if not tmux_has_session(sess):
            tmux_new_session(sess, bash_cmd)

        tmux_set_option(sess, "history-limit", str(TMUX_HISTORY_LIMIT))

        if clean_startup:
            time.sleep(0.15)
            tmux_send_keys(sess, "clear")
            tmux_clear_history(sess)

    if ctx and enable_tmux_logs:
        for sess in session_names():
            tmux_pipe_pane(sess, ctx.tmux_dir / f"{sess}.log", force_repipe=True)


def qwen_stop(all_sessions: bool = True, session: Optional[str] = None) -> None:
    ensure_tmux_exists()
    tmux_start_server()

    if all_sessions:
        for sess in session_names():
            tmux_kill_session(sess)
        return

    if not session:
        _die("qwen_stop: session manquante quand all_sessions=False")
    tmux_kill_session(session)


def qwen_restart(qwen_bin: str, path_override: str, auto_confirm: bool, ctx: Optional[RunCtx], enable_tmux_logs: bool, clean_startup: bool) -> None:
    qwen_start(
        qwen_bin=qwen_bin,
        path_override=path_override,
        auto_confirm=auto_confirm,
        restart=True,
        ctx=ctx,
        enable_tmux_logs=enable_tmux_logs,
        clean_startup=clean_startup,
    )


def _expected_agent_processes() -> set[str]:
    cli = active_agent_cli_name()
    # Status/health must tolerate mixed runtimes (legacy qwen sessions + codex tmux cron sessions).
    names = {cli, "qwen", "qwen-code", "codex", "openai-codex"}
    return {n.strip().lower() for n in names if n.strip()}


def _is_agent_process_ready(pane_cmd: str) -> bool:
    cmd = (pane_cmd or "").strip().lower()
    return cmd in _expected_agent_processes()


def _agent_cmdline_tokens() -> set[str]:
    tokens = {active_agent_cli_name(), "qwen", "codex", "openai-codex"}
    try:
        active_path = Path(ACTIVE_AGENT_BIN)
        tokens.add(active_path.name.lower())
        resolved = active_path.expanduser().resolve()
        tokens.add(resolved.name.lower())
        tokens.add(str(resolved).lower())
    except Exception:
        pass
    tokens.update({"qwen-code/cli.js", "@qwen-code/qwen-code/cli.js"})
    return {t for t in tokens if t}


def _read_proc_comm(pid: int) -> str:
    try:
        return Path(f"/proc/{int(pid)}/comm").read_text(encoding="utf-8").strip().lower()
    except Exception:
        return ""


def _read_proc_cmdline(pid: int) -> str:
    try:
        raw = Path(f"/proc/{int(pid)}/cmdline").read_bytes()
    except Exception:
        return ""
    if not raw:
        return ""
    try:
        return raw.replace(b"\x00", b" ").decode("utf-8", errors="ignore").strip().lower()
    except Exception:
        return ""


def _children_map() -> Dict[int, List[int]]:
    cp = run(["ps", "-eo", "pid=,ppid="], capture=True)
    mapping: Dict[int, List[int]] = {}
    for ln in (cp.stdout or "").splitlines():
        txt = ln.strip()
        if not txt:
            continue
        parts = txt.split()
        if len(parts) != 2:
            continue
        try:
            pid = int(parts[0])
            ppid = int(parts[1])
        except Exception:
            continue
        mapping.setdefault(ppid, []).append(pid)
    return mapping


def _descendant_pids(root_pid: int, limit: int = 200) -> List[int]:
    cmap = _children_map()
    out: List[int] = []
    queue: List[int] = [int(root_pid)]
    seen: set[int] = set()
    while queue and len(out) < max(10, int(limit)):
        parent = queue.pop(0)
        if parent in seen:
            continue
        seen.add(parent)
        children = cmap.get(parent, [])
        for child in children:
            if child in seen:
                continue
            out.append(child)
            queue.append(child)
            if len(out) >= limit:
                break
    return out


def _session_has_agent_child_process(session: str) -> bool:
    pane_pid = tmux_pane_pid(session)
    if not pane_pid:
        return False
    shell_names = {"bash", "sh", "zsh", "fish"}
    tokens = _agent_cmdline_tokens()
    for pid in _descendant_pids(pane_pid):
        comm = _read_proc_comm(pid)
        if not comm or comm in shell_names:
            continue
        if comm in _expected_agent_processes():
            return True
        cmdline = _read_proc_cmdline(pid)
        if any(tok in cmdline for tok in tokens):
            return True
    return False


def _session_agent_readiness(session: str, pane_cmd: str) -> Tuple[bool, str]:
    if _is_agent_process_ready(pane_cmd):
        return True, "pane_current_command"
    if _session_has_agent_child_process(session):
        return True, "child_process"
    return False, "no_agent_process"


def _session_alias_candidates(configured_session: str) -> List[str]:
    """
    Build deterministic alias candidates for one configured session name.
    Supports both legacy names (qwen_planner), cron names (qwen_planner_cron),
    and codex-era naming (codex_planner / codex_planner_cron).
    """
    sess = (configured_session or "").strip()
    if not sess:
        return []
    out: List[str] = [sess]
    if sess.endswith("_cron"):
        base = sess[: -len("_cron")]
        if base and base not in out:
            out.append(base)
    else:
        cron_name = f"{sess}_cron"
        if cron_name not in out:
            out.append(cron_name)

    # Cross-family aliases: qwen_* <-> codex_*.
    swap: str = ""
    if sess.startswith("qwen_"):
        swap = "codex_" + sess[len("qwen_") :]
    elif sess.startswith("codex_"):
        swap = "qwen_" + sess[len("codex_") :]
    if swap:
        if swap not in out:
            out.append(swap)
        if swap.endswith("_cron"):
            swap_base = swap[: -len("_cron")]
            if swap_base and swap_base not in out:
                out.append(swap_base)
        else:
            swap_cron = f"{swap}_cron"
            if swap_cron not in out:
                out.append(swap_cron)
    return out


def _resolve_existing_session_name(configured_session: str, existing: set[str]) -> Tuple[str, bool, str]:
    """
    Resolve to an existing tmux session by trying configured name first, then aliases.
    Returns (resolved_name, is_present, source) where source is configured|alias|missing.
    """
    candidates = _session_alias_candidates(configured_session)
    for idx, candidate in enumerate(candidates):
        if candidate in existing:
            return candidate, True, ("configured" if idx == 0 else "alias")
    return configured_session, False, "missing"


def qwen_status_payload(core_roles: Optional[List[str]] = None) -> Dict[str, Any]:
    ensure_tmux_exists()
    tmux_start_server()
    existing = set(tmux_list_sessions())
    mapped_sessions = set(SESSIONS.values())

    role_map: Dict[str, Dict[str, Any]] = {}
    session_up_count = 0
    session_down_count = 0
    ready_up_count = 0
    ready_down_count = 0
    for role in sorted(SESSIONS.keys()):
        configured_sess = SESSIONS[role]
        sess, is_present, session_source = _resolve_existing_session_name(configured_sess, existing)
        mapped_sessions.add(sess)
        pane_cmd = tmux_current_command(sess) if is_present else ""
        ready_source = "session_missing"
        is_ready = False
        if is_present:
            is_ready, ready_source = _session_agent_readiness(sess, pane_cmd)
            if session_source == "alias":
                ready_source = f"{ready_source}+alias_session"
        role_map[role] = {
            "session": sess,
            "configured_session": configured_sess,
            "session_source": session_source,
            "up": is_present,
            "ready": is_ready,
            "pane_command": pane_cmd,
            "ready_source": ready_source,
        }
        if is_present:
            session_up_count += 1
        else:
            session_down_count += 1
        if is_ready:
            ready_up_count += 1
        else:
            ready_down_count += 1

    extra_prefix = f"{active_agent_cli_name()}_"
    extra_sessions = sorted(s for s in existing if s.startswith(extra_prefix) and s not in mapped_sessions)

    required_roles = core_roles or list(CORE_STATUS_ROLES_DEFAULT)
    required_missing = [r for r in required_roles if (r not in role_map) or (not bool(role_map[r].get("ready")))]
    verdict = "PASS" if not required_missing else "BLOCKED"
    blocker_id = "NONE" if verdict == "PASS" else "TMUX_REQUIRED_ROLES_NOT_READY"

    return {
        "project_dir": str(PROJECT_DIR),
        "runs_dir": str(RUNS_DIR_DEFAULT),
        "latest_run_pointer": str(RUNS_DIR_DEFAULT / "latest"),
        "agent_cli": {
            "name": active_agent_cli_name(),
            "bin": ACTIVE_AGENT_BIN,
        },
        "roles": role_map,
        "extra_sessions": extra_sessions,
        "counts": {
            "up": ready_up_count,
            "down": ready_down_count,
            "total": ready_up_count + ready_down_count,
            "sessions_up": session_up_count,
            "sessions_down": session_down_count,
        },
        "required_roles": required_roles,
        "required_missing": required_missing,
        "verdict": verdict,
        "blocker_id": blocker_id,
    }


def format_qwen_status_text(payload: Dict[str, Any]) -> str:
    roles = payload.get("roles") or {}
    lines: List[str] = []
    lines.append(f"Runs dir: {payload.get('runs_dir')}")
    lines.append(f"Latest run pointer: {payload.get('latest_run_pointer')}")
    agent_cli = payload.get("agent_cli") or {}
    lines.append(f"Agent CLI actif: {agent_cli.get('name')} ({agent_cli.get('bin')})")
    lines.append("Sessions tmux (role -> session):")
    for role in sorted(roles.keys()):
        item = roles.get(role) or {}
        state = "UP" if bool(item.get("ready")) else "DOWN"
        present = "UP" if bool(item.get("up")) else "DOWN"
        pane_cmd = str(item.get("pane_command") or "-")
        ready_source = str(item.get("ready_source") or "-")
        lines.append(
            f"  - {role} -> {item.get('session', '?')}: "
            f"{state} (session={present}, pane={pane_cmd}, via={ready_source})"
        )

    extra_sessions = payload.get("extra_sessions") or []
    if extra_sessions:
        lines.append(f"Autres sessions {agent_cli.get('name', 'agent')} (non mappées):")
        for sess in extra_sessions:
            lines.append(f"  - {sess}: UP")

    required_roles = payload.get("required_roles") or []
    required_missing = payload.get("required_missing") or []
    lines.append(
        f"Required roles: {', '.join(required_roles) if required_roles else '(none)'}"
    )
    lines.append(
        f"Missing required: {', '.join(required_missing) if required_missing else 'none'}"
    )
    lines.append(f"VERDICT: {payload.get('verdict', 'BLOCKED')}")
    lines.append(f"BLOCKER_ID: {payload.get('blocker_id', 'UNKNOWN')}")
    return "\n".join(lines)


def format_qwen_status_compact(payload: Dict[str, Any]) -> str:
    required_missing = payload.get("required_missing") or []
    counts = payload.get("counts") or {}
    return (
        f"VERDICT: {payload.get('verdict', 'BLOCKED')} | "
        f"BLOCKER_ID: {payload.get('blocker_id', 'UNKNOWN')} | "
        f"ready={counts.get('up', 0)}/{counts.get('total', 0)} | "
        f"sessions={counts.get('sessions_up', 0)}/{counts.get('total', 0)} | "
        f"required_missing={','.join(required_missing) if required_missing else 'none'}"
    )


def qwen_status(core_roles: Optional[List[str]] = None, fmt: str = "text") -> str:
    payload = qwen_status_payload(core_roles=core_roles)
    fmt_norm = (fmt or "text").strip().lower()
    if fmt_norm == "json":
        return json.dumps(payload, ensure_ascii=False, indent=2)
    if fmt_norm == "compact":
        return format_qwen_status_compact(payload)
    return format_qwen_status_text(payload)


def qwen_attach(role_or_session: str) -> int:
    ensure_tmux_exists()
    tmux_start_server()
    sess = resolve_session(role_or_session)
    return tmux_attach(sess)


def _looks_like_qwen_banner(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    low = t.lower()
    if "tips for getting started" in low:
        return True
    if "██" in t and len([ln for ln in t.splitlines() if ln.strip()]) <= 12:
        return True
    return False


def _looks_like_internal_reasoning(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    low = t.lower()
    if not t.lstrip().startswith("✦"):
        return False
    markers = (
        "the user wants me to",
        "i need to",
        "i should",
        "i will",
        "i'll",
        "let me ",
        "je vais",
        "je dois",
        "j'ai besoin",
        "il faut",
        "je commence",
    )
    return any(m in low for m in markers)


def _launch_qwen_in_session(session: str) -> None:
    agent_cmd = shlex.quote(ACTIVE_AGENT_BIN)
    cmd = (
        "unset NO_COLOR; "
        'if [ "${TERM:-dumb}" = "dumb" ]; then export TERM=xterm-256color; fi; '
        'export COLORTERM="${COLORTERM:-truecolor}"; '
        'export FORCE_COLOR="${FORCE_COLOR:-1}"; '
        f"{agent_cmd}"
    )
    tmux_send_keys(session, cmd)


def qwen_prompt(role_or_session: str, prompt: str, system_prompt: str = "", max_wait: float = 60.0) -> str:
    ensure_tmux_exists()
    tmux_start_server()
    sess = resolve_session(role_or_session)
    if not tmux_has_session(sess):
        _die(f"Session tmux absente: {sess}. Lance d'abord --tmux-cmd start.")

    fallback_sdk = is_active_qwen_cli() and _env_bool("FC_QWEN_TMUX_FALLBACK_SDK", default=True)
    cmd = tmux_current_command(sess)
    ready, _ready_source = _session_agent_readiness(sess, cmd)
    if not ready:
        _launch_qwen_in_session(sess)
        time.sleep(1.6)
        cmd = tmux_current_command(sess)
        ready, _ready_source = _session_agent_readiness(sess, cmd)
        if not ready:
            if fallback_sdk:
                return qwen_prompt_sdk(
                    prompt,
                    system_prompt=system_prompt,
                    max_wait=max_wait,
                    permission_mode=os.environ.get("FC_QWEN_SDK_PERMISSION_MODE", "default"),
                    model=os.environ.get("FC_QWEN_SDK_MODEL", ""),
                    debug=_env_bool("FC_QWEN_SDK_DEBUG", default=False),
                    path_to_qwen_executable=os.environ.get("FC_QWEN_SDK_CLI_PATH", ""),
                    session_key=f"tmux:{sess}",
                    max_session_turns=int(os.environ.get("FC_QWEN_SDK_MAX_SESSION_TURNS", "-1")),
                )
            _die(
                f"Agent TUI non prêt dans la session {sess} "
                f"(pane_current_command={cmd or 'unknown'})."
            )

    llm = QwenTmuxLLM(session_name=sess, system_prompt=system_prompt, max_wait=max(15.0, float(max_wait)))
    reply = llm.chat(prompt)
    if (not reply.strip() or _looks_like_qwen_banner(reply)) and fallback_sdk:
        return qwen_prompt_sdk(
            prompt,
            system_prompt=system_prompt,
            max_wait=max_wait,
            permission_mode=os.environ.get("FC_QWEN_SDK_PERMISSION_MODE", "default"),
            model=os.environ.get("FC_QWEN_SDK_MODEL", ""),
            debug=_env_bool("FC_QWEN_SDK_DEBUG", default=False),
            path_to_qwen_executable=os.environ.get("FC_QWEN_SDK_CLI_PATH", ""),
            session_key=f"tmux:{sess}",
            max_session_turns=int(os.environ.get("FC_QWEN_SDK_MAX_SESSION_TURNS", "-1")),
        )
    return reply


def qwen_ping(target: str = "", max_wait: float = 25.0) -> Dict[str, str]:
    ping_prompt = (
        "PING ORCHESTRATOR: réponds uniquement avec une ligne courte au format "
        "'PONG <session_or_role> <timestamp>'."
    )
    results: Dict[str, str] = {}

    pairs: List[Tuple[str, str]] = []
    if target:
        sess = resolve_session(target)
        pairs.append((target, sess))
    else:
        for role in sorted(SESSIONS.keys()):
            pairs.append((role, SESSIONS[role]))

    for label, sess in pairs:
        if not tmux_has_session(sess):
            results[label] = f"DOWN ({sess})"
            continue
        try:
            reply = qwen_prompt(sess, ping_prompt, system_prompt="", max_wait=max_wait)
            text = (reply or "").strip()
            if not text:
                results[label] = "EMPTY_REPLY"
            elif re.match(r"(?i)^pong\b", text):
                results[label] = text
            else:
                compact = text.replace("\n", " ").strip()
                if len(compact) > 180:
                    compact = compact[:180].rstrip() + "..."
                results[label] = f"INVALID_REPLY: {compact}"
        except Exception as e:
            results[label] = f"ERROR: {e}"
    return results


def _parse_json_object_from_output(text: str) -> Dict[str, Any]:
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    for line in reversed(lines):
        try:
            parsed = json.loads(line)
        except Exception:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("Aucun JSON valide trouvé dans la sortie du bridge SDK.")


def _load_sdk_session_state() -> Dict[str, str]:
    p = SDK_SESSION_STATE_FILE
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    out: Dict[str, str] = {}
    for k, v in data.items():
        ks = str(k or "").strip()
        vs = str(v or "").strip()
        if ks and vs:
            out[ks] = vs
    return out


def _save_sdk_session_state(data: Dict[str, str]) -> None:
    p = SDK_SESSION_STATE_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _get_sdk_session_id(session_key: str) -> str:
    key = (session_key or "").strip()
    if not key:
        return ""
    state = _load_sdk_session_state()
    return str(state.get(key, "")).strip()


def _set_sdk_session_id(session_key: str, session_id: str) -> None:
    key = (session_key or "").strip()
    sid = (session_id or "").strip()
    if not key or not sid:
        return
    state = _load_sdk_session_state()
    if state.get(key) == sid:
        return
    state[key] = sid
    _save_sdk_session_state(state)


def qwen_prompt_sdk(
    prompt: str,
    *,
    system_prompt: str = "",
    max_wait: float = 60.0,
    permission_mode: str = "default",
    model: str = "",
    debug: bool = False,
    path_to_qwen_executable: str = "",
    session_key: str = "",
    max_session_turns: int = -1,
) -> str:
    permission_mode = (permission_mode or "default").strip().lower()
    if permission_mode not in SDK_PERMISSION_MODES:
        _die(
            f"permission_mode SDK invalide: {permission_mode}. "
            f"Valeurs: {', '.join(sorted(SDK_PERMISSION_MODES))}"
        )

    node_bin = require_executable(NODE_BIN_DEFAULT)
    bridge = SDK_BRIDGE_DEFAULT
    if not bridge.exists():
        _die(
            f"Bridge SDK introuvable: {bridge}\n"
            "Crée ce fichier (scripts/qwen_sdk_prompt.mjs) et installe @qwen-code/sdk."
        )

    sdk_prompt = prompt.strip()
    if system_prompt.strip():
        sdk_prompt = (
            "[SYSTEM]\n"
            f"{system_prompt.strip()}\n\n"
            "[USER]\n"
            f"{prompt.strip()}"
        )

    resume_session = _get_sdk_session_id(session_key)

    cmd: List[str] = [
        node_bin,
        str(bridge),
        "--prompt",
        sdk_prompt,
        "--cwd",
        str(PROJECT_DIR),
        "--permission-mode",
        permission_mode,
        "--timeout-sec",
        str(max(10.0, float(max_wait))),
    ]
    if resume_session:
        cmd.extend(["--resume", resume_session])
    if int(max_session_turns) > 0:
        cmd.extend(["--max-session-turns", str(int(max_session_turns))])
    if model.strip():
        cmd.extend(["--model", model.strip()])
    if debug:
        cmd.append("--debug")
    if path_to_qwen_executable.strip():
        cmd.extend(["--path-to-qwen-executable", require_executable(path_to_qwen_executable.strip())])

    cp = run(
        cmd,
        cwd=PROJECT_DIR,
        capture=True,
        timeout=int(max(20.0, float(max_wait) + 45.0)),
    )
    out = (cp.stdout or "").strip()

    if cp.returncode != 0:
        tail = "\n".join((out.splitlines() or [""])[-20:]).strip()
        _die(f"Bridge SDK en échec (rc={cp.returncode}).\n{tail}")

    try:
        payload = _parse_json_object_from_output(out)
    except Exception as e:
        _die(f"Sortie SDK illisible: {e}\nSortie brute:\n{out[-2000:]}")

    if not payload.get("ok", False):
        err = str(payload.get("error") or "Erreur inconnue SDK")
        detail = str(payload.get("detail") or "")
        msg = f"SDK error: {err}"
        if detail:
            msg += f"\n{detail}"
        _die(msg)

    payload_session_id = str(payload.get("sessionId") or "").strip()
    if payload_session_id and session_key.strip():
        _set_sdk_session_id(session_key, payload_session_id)

    assistant = str(payload.get("assistant") or "").strip()
    if assistant:
        return assistant

    result = payload.get("result")
    if result is not None:
        try:
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception:
            return str(result)

    return "(réponse vide)"


def qwen_ping_sdk(
    max_wait: float = 25.0,
    model: str = "",
    debug: bool = False,
    qwen_bin: str = "",
    session_key: str = "sdk:ping",
) -> str:
    ping_prompt = (
        "PING ORCHESTRATOR: réponds uniquement avec une ligne courte au format "
        "'PONG sdk <timestamp>'."
    )
    return qwen_prompt_sdk(
        ping_prompt,
        max_wait=max_wait,
        permission_mode="default",
        model=model,
        debug=debug,
        path_to_qwen_executable=qwen_bin,
        session_key=session_key,
    )


# ==============================================================================
# Qwen tmux backend (chat)
# ==============================================================================

class QwenTmuxSession:
    """
    Stratégie robuste: attendre que la "sortie nettoyée" soit STABLE pendant settle_seconds.
    Ça marche même si la TUI anime des spinners (qu'on supprime au nettoyage).
    """

    CONFIRM_RULES: List[Tuple[re.Pattern, str]] = [
        (re.compile(r"apply\s+patch\?.*(\[\s*y\s*/\s*n\s*\]|\[y/N\]|\(y/n\))", re.IGNORECASE), "y"),
        (re.compile(r"proceed\?.*(\[\s*y\s*/\s*n\s*\]|\[y/N\]|\(y/n\))", re.IGNORECASE), "y"),
        (re.compile(r"allow execution of:", re.IGNORECASE), "1"),
        (re.compile(r"waiting for user confirmation", re.IGNORECASE), "1"),
    ]

    def __init__(self, session_name: str, capture_lines: int = CAPTURE_LAST_LINES):
        self.session = session_name
        self.capture_lines = capture_lines
        self.last_snapshot = tmux_capture(self.session, last_lines=self.capture_lines)

    def _get_new_output(self) -> str:
        cur = tmux_capture(self.session, last_lines=self.capture_lines)

        if cur.startswith(self.last_snapshot):
            new = cur[len(self.last_snapshot):]
            self.last_snapshot = cur
            return (new or "").strip()

        tail = (self.last_snapshot or "")[-2000:]
        if tail:
            idx = cur.find(tail)
            if idx != -1:
                new = cur[idx + len(tail):]
                self.last_snapshot = cur
                return (new or "").strip()

        self.last_snapshot = cur
        return (cur or "").strip()

    def _send(self, text: str) -> None:
        tmux_send_keys(self.session, text)

    def _auto_confirm(self, buffer: str, max_confirms: int, confirms_done: int) -> int:
        if confirms_done >= max_confirms:
            return confirms_done
        for pat, answer in self.CONFIRM_RULES:
            if pat.search(buffer):
                self._send(answer)
                return confirms_done + 1
        return confirms_done

    @staticmethod
    def _strip_terminal_noise(s: str) -> str:
        if not s:
            return ""
        s = re.sub(r"\x1b\][^\x07]*\x07", "", s)        # OSC ... BEL
        s = re.sub(r"\x1b\][^\\x1b]*\x1b\\", "", s)     # OSC ... ST (rare)
        s = re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]", "", s)   # CSI
        s = re.sub(r"\x1B[@-Z\\-_]", "", s)             # other ESC
        return s

    def _clean_output(self, raw: str) -> str:
        """Nettoie la sortie brute de Qwen pour ne garder que la réponse utile."""
        if not raw:
            return ""

        text = self._strip_terminal_noise(raw)
        lines = [line.rstrip() for line in text.splitlines()]

        noise_substrings = [
            "ask questions, edit files, or run commands.",
            "be specific for the best results.",
            "/help for more information.",
            "installed via homebrew. please update with",
            "qwen code update available!",
            "type your message",
            "auto-accept edits",
            "using: 1 qwen.md file",
            "using:",
            "no sandbox",
            "coder-model",
            "sandbox (",
            "(esc to cancel",
            "mining for more",
            "caching the essentials",
            "initializing...",
            "waiting for user confirmation",
            "allow execution of:",
            "yes, allow once",
            "yes, allow always",
            "no, suggest changes",
        ]

        cleaned: List[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            lower = stripped.lower()
            is_error_line = any(
                marker in lower
                for marker in ("error", "exception", "traceback", "failed", "invalid", "not found", "denied")
            )

            # Spinners / loading
            if stripped.startswith(("⠋", "⠙", "⠹", "⠸", "⠼", "⠧", "⠏", "⠴", "⠦")):
                continue

            # TUI frames / borders
            if re.match(r"^[\s┌┐└┘├┤─│╭╮╰╯…·]+$", stripped):
                continue

            # Status bar / path noise
            if "...//analyse-financiere" in stripped:
                continue
            if "coder-model" in lower and "sandbox" in lower:
                continue

            # Generic UI noise
            if (not is_error_line) and any(ns in lower for ns in noise_substrings):
                continue

            cleaned.append(stripped)

        if not cleaned:
            return ""

        # Keep only the last useful block (often starts with "✦")
        last_star_idx = None
        for i, line in enumerate(cleaned):
            if line.lstrip().startswith("✦"):
                last_star_idx = i
        if last_star_idx is not None and not _looks_like_internal_reasoning(cleaned[last_star_idx]):
            cleaned = cleaned[last_star_idx:]

        # Safety: cap output size
        if len(cleaned) > 40:
            cleaned = cleaned[-40:]

        return "\n".join(cleaned).strip()

    def _fallback_from_pane(self) -> str:
        """
        Fallback quand aucun texte utile n'a pu être extrait.
        On renvoie au minimum les lignes d'erreur visibles dans le pane.
        """
        raw = tmux_capture(self.session, last_lines=max(self.capture_lines, 1200))
        text = self._strip_terminal_noise(raw or "")
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            return ""

        err_lines = [
            ln for ln in lines
            if any(m in ln.lower() for m in ("error", "exception", "traceback", "failed", "invalid", "not found", "denied"))
        ]
        if err_lines:
            return "\n".join(err_lines[-12:])[:1500].strip()

        return "\n".join(lines[-8:])[:1500].strip()

    @staticmethod
    def _fingerprint(s: str) -> str:
        return hashlib.sha1((s or "").encode("utf-8", errors="ignore")).hexdigest()

    def ask(
        self,
        text: str,
        *,
        max_wait: float = 90.0,
        settle_seconds: float = 1.8,
        poll_interval: float = 0.55,
        min_wait: float = 1.2,
    ) -> str:
        self._send(text)

        start = time.time()
        deadline = start + max_wait

        buf = ""
        confirms = 0

        last_clean = ""
        last_fp = ""
        last_change = time.time()

        while time.time() < deadline:
            time.sleep(poll_interval)

            new = self._get_new_output()
            if new:
                buf += "\n" + new
                confirms = self._auto_confirm(buf, max_confirms=8, confirms_done=confirms)

            clean = self._clean_output(buf)
            fp = self._fingerprint(clean)

            if fp != last_fp:
                last_fp = fp
                last_clean = clean
                last_change = time.time()

            stable_for = time.time() - last_change
            elapsed = time.time() - start

            if elapsed >= min_wait and stable_for >= settle_seconds and last_clean.strip():
                break

        if not last_clean.strip():
            self._send("Ne recopie pas le prompt. Donne uniquement une réponse structurée et actionnable.")
            time.sleep(0.6)
            extra_buf = ""
            last_fp = ""
            last_change = time.time()
            start2 = time.time()
            while time.time() - start2 < 12.0:
                time.sleep(0.5)
                new2 = self._get_new_output()
                if new2:
                    extra_buf += "\n" + new2
                clean2 = self._clean_output(extra_buf)
                fp2 = self._fingerprint(clean2)
                if fp2 != last_fp:
                    last_fp = fp2
                    last_clean = clean2
                    last_change = time.time()
                if (time.time() - last_change) >= 1.2 and last_clean.strip():
                    break

        if not last_clean.strip():
            last_clean = self._fallback_from_pane()

        return last_clean.strip()


class QwenTmuxLLM:
    def __init__(self, session_name: str, system_prompt: str = "", max_wait: float = 90.0):
        self.session = QwenTmuxSession(session_name, capture_lines=CAPTURE_LAST_LINES)
        self.system_prompt = (system_prompt or "").strip()
        self.max_wait = max_wait
        self._init_done = False
        self._sdk_fallback = _env_bool("FC_QWEN_TMUX_FALLBACK_SDK", default=True)

    def _sdk_system_prompt(self) -> str:
        rules = (
            "Règles:\n"
            "- Réponds en français.\n"
            "- Ne recopie pas le prompt.\n"
            "- Donne des étapes concrètes.\n"
            "- Si bloqué: dis exactement quoi vérifier.\n"
        )
        if self.system_prompt:
            return f"{self.system_prompt}\n\n{rules}"
        return rules

    def _chat_via_sdk(self, prompt: str) -> str:
        return qwen_prompt_sdk(
            prompt,
            system_prompt=self._sdk_system_prompt(),
            max_wait=self.max_wait,
            permission_mode=os.environ.get("FC_QWEN_SDK_PERMISSION_MODE", "default"),
            model=os.environ.get("FC_QWEN_SDK_MODEL", ""),
            debug=_env_bool("FC_QWEN_SDK_DEBUG", default=False),
            path_to_qwen_executable=os.environ.get("FC_QWEN_SDK_CLI_PATH", ""),
            session_key=f"tmux:{self.session.session}",
            max_session_turns=int(os.environ.get("FC_QWEN_SDK_MAX_SESSION_TURNS", "-1")),
        )

    def _ensure_init(self):
        if self._init_done:
            return
        if self.system_prompt:
            self.session.ask(
                "[SYSTEM]\n"
                f"{self.system_prompt}\n\n"
                "Règles:\n"
                "- Réponds en français.\n"
                "- Ne recopie pas le prompt.\n"
                "- Donne des étapes concrètes.\n"
                "- Si bloqué: dis exactement quoi vérifier.\n",
                max_wait=min(35.0, self.max_wait),
                settle_seconds=1.2,
            )
        self._init_done = True

    def chat(self, prompt: str) -> str:
        sdk_fallback = self._sdk_fallback and is_active_qwen_cli()

        if sdk_fallback:
            cmd = tmux_current_command(self.session.session)
            ready, _ready_source = _session_agent_readiness(self.session.session, cmd)
            if not ready:
                try:
                    return self._chat_via_sdk(prompt)
                except Exception:
                    pass

        self._ensure_init()
        reply = self.session.ask(
            prompt,
            max_wait=self.max_wait,
            settle_seconds=1.8,
            poll_interval=0.55,
            min_wait=1.2,
        )
        if sdk_fallback and (
            not reply.strip()
            or _looks_like_qwen_banner(reply)
            or _looks_like_internal_reasoning(reply)
        ):
            try:
                return self._chat_via_sdk(prompt)
            except Exception:
                return reply
        return reply


# ==============================================================================
# dev_tools (in-file)
# ==============================================================================

def _python_cmd() -> List[str]:
    if VENV_PY.exists():
        return [str(VENV_PY)]
    return ["python3"]


def run_exemplary_preflight(ctx: RunCtx) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def _run_check(name: str, cmd: List[str], *, timeout: int = 180, required: bool = True) -> None:
        try:
            cp = run(cmd, cwd=PROJECT_DIR, capture=True, timeout=timeout)
            returncode = int(cp.returncode)
            output = (cp.stdout or "").strip()
        except Exception as exc:
            returncode = 124
            output = f"Exception while running check: {exc}"
        if len(output) > 4500:
            output = output[:4500] + "\n...[output tronqué]..."
        ok = returncode == 0
        checks.append(
            {
                "name": name,
                "ok": ok,
                "required": required,
                "returncode": returncode,
                "cmd": cmd,
                "output": output,
            }
        )
        transcript_append(
            ctx,
            "Runner",
            "INFO",
            f"EXEMPLARY_PREFLIGHT {name}: {'PASS' if ok else 'BLOCKED'} (rc={returncode})",
        )
        event_append(
            ctx,
            {
                "type": "exemplary_preflight_check",
                "name": name,
                "ok": ok,
                "required": required,
                "returncode": returncode,
                "output": output,
            },
        )

    _run_check(
        "validate_batch_state",
        ["python3", "scripts/validate_batch_state.py", "--file", "docs/orchestrator-ops/priority-queue.json"],
        timeout=90,
        required=True,
    )
    _run_check(
        "preflight_dispatch",
        ["bash", "scripts/preflight_dispatch.sh"],
        timeout=120,
        required=True,
    )

    backend_gate = PROJECT_DIR / "scripts" / "backend_regression_gate.sh"
    if backend_gate.exists():
        _run_check(
            "backend_regression_no_live",
            ["bash", str(backend_gate), "--no-live"],
            timeout=600,
            required=True,
        )
    else:
        checks.append(
            {
                "name": "backend_regression_no_live",
                "ok": False,
                "required": True,
                "returncode": 127,
                "cmd": ["bash", "scripts/backend_regression_gate.sh", "--no-live"],
                "output": "missing script: scripts/backend_regression_gate.sh",
            }
        )

    failures = [c for c in checks if c.get("required") and not c.get("ok")]
    return {
        "ok": len(failures) == 0,
        "checks": checks,
        "failures": failures,
    }


def run_pytest_tool() -> Dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(BACKEND_SRC)
    cmd = _python_cmd() + ["-m", "pytest", "-q"]
    cp = run(cmd, cwd=BACKEND_DIR, env=env, capture=True)
    out = cp.stdout or ""
    if len(out) > 7000:
        out = out[:7000] + "\n...[output tronqué]..."
    return {"ok": "true" if cp.returncode == 0 else "false", "output": out}


def run_specific_tests_tool(pattern: str) -> Dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(BACKEND_SRC)
    cmd = _python_cmd() + ["-m", "pytest", "-q", "-k", pattern]
    cp = run(cmd, cwd=BACKEND_DIR, env=env, capture=True)
    out = cp.stdout or ""
    if len(out) > 7000:
        out = out[:7000] + "\n...[output tronqué]..."
    return {"ok": "true" if cp.returncode == 0 else "false", "output": out}


def git_status_tool() -> str:
    cp = run(["git", "status", "--short"], cwd=PROJECT_DIR, capture=True)
    return (cp.stdout or "").strip()


def git_diff_tool(max_lines: int = 220) -> str:
    cp = run(["git", "diff"], cwd=PROJECT_DIR, capture=True)
    lines = (cp.stdout or "").splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines] + ["...[diff tronqué]..."]
    return "\n".join(lines).strip()


def run_codex_independent_review(feature: str, qa_report: str, timeout_sec: int = 180) -> Dict[str, str]:
    """
    Reviewer indépendant via instance Codex non-interactive.
    Retourne {ok, output}.
    """
    codex_bin = require_bin("codex")
    api_doc_ref = api_best_practices_doc_reference()
    prompt = dedent(f"""
    Independent Review Gate (Codex)

    Feature objective:
    {feature}

    QA report from execution team:
    {qa_report}

    Reference (mandatory for endpoint/API changes):
    - `{api_doc_ref}`
    - Check explicit compliance: contract, cache, fallback, tests.

    Task:
    - Review uncommitted changes as an independent reviewer.
    - Decide GO or BLOCKED.
    - If BLOCKED, list exact blocking issues and minimal fixes.
    - Keep response concise and auditable.
    """).strip()

    cp = run(
        [codex_bin, "review", "--uncommitted", prompt],
        cwd=PROJECT_DIR,
        capture=True,
        timeout=max(60, int(timeout_sec)),
    )
    out = (cp.stdout or "").strip()
    if len(out) > 9000:
        out = out[:9000] + "\n...[output tronqué]..."
    return {"ok": "true" if cp.returncode == 0 else "false", "output": out}


# ==============================================================================
# Prompts
# ==============================================================================

def infer_test_pattern(feature: str, default: str = "health") -> str:
    m = re.search(r"/([a-zA-Z0-9_]+)", feature)
    return m.group(1) if m else default


# ==============================================================================
# Debug/smoke mode helpers (marker)
# ==============================================================================

def debug_marker_paths(run_id: str) -> Dict[str, Path]:
    base = BACKEND_DIR / ".qwen_runs" / run_id
    return {"dir": base, "marker": base / "marker.txt"}


def create_marker(run_id: str) -> Path:
    paths = debug_marker_paths(run_id)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    content = f"run_id={run_id}\ncreated_at={datetime.now().isoformat(timespec='seconds')}\n"
    paths["marker"].write_text(content, encoding="utf-8")
    return paths["marker"]


def build_debug_feature(run_id: str) -> str:
    paths = debug_marker_paths(run_id)
    return dedent(f"""
    MODE DEBUG / SMOKE TEST (run_id={run_id})

    Objectif:
    - Valider rapidement l'orchestrateur + logs/transcript.

    Contrainte:
    - Utiliser cet emplacement exact pour les artefacts:
      - Dossier: {paths['dir']}
      - Marker:  {paths['marker']}

    Tâches attendues:
    - PLANNER: justifie pourquoi cet emplacement est bon (artefacts/outillage), et propose 3 règles (gitignore, sécurité, nettoyage).
    - DEV: crée/valide le fichier marker (si absent), et propose une commande de vérif.
    - TESTER: propose 2 validations:
        1) commande shell (test -f ...)
        2) un test pytest minimal qui échoue si le marker est absent.
    """).strip()


# ==============================================================================
# AutoGen classic -> tmux driver (ONLY solution)
# ==============================================================================

def _format_autogen_context(messages: List[Dict[str, Any]], max_msgs: int = 10, max_chars: int = 5000) -> str:
    tail = messages[-max_msgs:] if len(messages) > max_msgs else messages
    parts: List[str] = []
    budget = max(1000, int(max_chars))
    for m in tail:
        role = (m.get("name") or m.get("role") or "unknown").strip()
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if len(content) > 1200:
            content = content[:1200] + "\n...[tronqué]..."
        block = f"[{role}]\n{content}\n"
        if len(block) > budget:
            block = block[:budget] + "\n...[tronqué]...\n"
        parts.append(block)
        budget -= len(block)
        if budget <= 0:
            break
    return "\n".join(parts).strip()


def run_feature_autogen_tmux(
    ctx: RunCtx,
    feature: str,
    max_rounds: int,
    wait_planner: float,
    wait_dev: float,
    wait_tester: float,
    wait_qa: float,
    specialist_roles: Optional[List[str]] = None,
    with_architect: bool = False,
    with_manager: bool = False,
    with_codex_reviewer: bool = False,
    execution_profile: str = "standard",
) -> str:
    autogen = require_module("autogen")  # strict
    execution_profile = (execution_profile or "standard").strip().lower()
    if execution_profile not in {"standard", "exemplary"}:
        execution_profile = "standard"
    exemplary = execution_profile == "exemplary"
    selected_specialists = ensure_specialist_sessions(
        resolve_specialist_roles(
            team_profile="core",
            specialists_raw="",
            explicit_roles=specialist_roles,
            with_architect=with_architect,
        )
    )
    api_doc_ref = api_best_practices_doc_reference()
    api_guidance = api_best_practices_guidance_block()
    agent_bus_append(ctx, sender="Runner", recipient="team", kind="feature", content=feature)
    event_append(
        ctx,
        {
            "type": "run_start",
            "run_id": ctx.run_id,
            "execution_profile": execution_profile,
            "specialist_roles": selected_specialists,
            "feature": _compact_bus_content(feature, max_chars=1200),
        },
    )

    turn_state = {"index": 0}
    activity_summary: Dict[str, Any] = {
        "run_id": ctx.run_id,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "totals": {
            "turns": 0,
            "duration_ms_total": 0,
            "commands_detected": 0,
            "files_touched_unique": 0,
            "warnings_total": 0,
        },
        "agents": {},
    }
    activity_files: set[str] = set()

    def _update_agent_summary(
        agent_name: str,
        *,
        duration_ms: int,
        commands: List[str],
        files_touched: List[str],
        warnings: List[str],
    ) -> None:
        ag = activity_summary["agents"].setdefault(
            agent_name,
            {
                "turns": 0,
                "duration_ms_total": 0,
                "duration_ms_avg": 0,
                "commands_detected": 0,
                "commands_sample": [],
                "files_touched_unique": [],
                "warnings_total": 0,
                "warnings_by_type": {},
            },
        )
        ag["turns"] += 1
        ag["duration_ms_total"] += int(duration_ms)
        ag["duration_ms_avg"] = int(ag["duration_ms_total"] / max(1, ag["turns"]))
        ag["commands_detected"] += len(commands)
        for cmd in commands:
            if cmd not in ag["commands_sample"] and len(ag["commands_sample"]) < 25:
                ag["commands_sample"].append(cmd)
        for fp in files_touched:
            if fp not in ag["files_touched_unique"] and len(ag["files_touched_unique"]) < 120:
                ag["files_touched_unique"].append(fp)
            activity_files.add(fp)
        ag["warnings_total"] += len(warnings)
        for w in warnings:
            ag["warnings_by_type"][w] = int(ag["warnings_by_type"].get(w, 0)) + 1

        activity_summary["totals"]["turns"] = int(turn_state["index"])
        activity_summary["totals"]["duration_ms_total"] += int(duration_ms)
        activity_summary["totals"]["commands_detected"] += len(commands)
        activity_summary["totals"]["files_touched_unique"] = len(activity_files)
        activity_summary["totals"]["warnings_total"] += len(warnings)
        activity_summary["generated_at"] = datetime.now().isoformat(timespec="seconds")
        write_agent_activity_summary(ctx, activity_summary)

    exemplary_tail = ""
    if exemplary:
        exemplary_tail = (
            " Mode exemplaire: pas de blabla, pas de question finale, "
            "réponse orientée exécution immédiate avec sections explicitement nommées."
        )
    reference_tail = (
        f" Référence obligatoire: `{api_doc_ref}`. "
        "Dès qu'un endpoint/API est touché, applique explicitement cette doc "
        "(contrat/cache/fallback/tests)."
    )

    planner_system_prompt = (
        "Tu es PLANNER, architecte technique. Ultra concret et court."
        + reference_tail
        + exemplary_tail
    )
    dev_system_prompt = (
        "Tu es DEV backend senior. Changements minimaux, testables. Donne des commandes."
        + reference_tail
        + exemplary_tail
    )
    tester_system_prompt = (
        "Tu es TESTER/QA. Propose tests pytest concrets + cas limites. Précis sur imports."
        + reference_tail
        + exemplary_tail
    )
    qa_system_prompt = (
        "Tu es QUALITY_OBSERVER. Rapport: ÉTAT GÉNÉRAL, TESTS, RISQUES, PRIORITÉS."
        + reference_tail
        + exemplary_tail
    )
    manager_system_prompt = (
        "Tu es DELIVERY_MANAGER. Tu vérifies la conformité à la demande, "
        "la clarté du livrable, et tu imposes une décision GO/NO-GO."
        + reference_tail
        + exemplary_tail
    )
    specialist_system_prompts: Dict[str, str] = {}
    for role_name in selected_specialists:
        spec = SPECIALIST_ROLE_SPECS.get(role_name) or {}
        base_prompt = str(spec.get("system_prompt") or "").strip()
        if not base_prompt:
            continue
        specialist_system_prompts[role_name] = base_prompt + reference_tail + exemplary_tail

    planner_llm = QwenTmuxLLM(
        session_name=SESSIONS["planner"],
        system_prompt=planner_system_prompt,
        max_wait=max(60.0, wait_planner),
    )
    specialist_llms: Dict[str, Any] = {}
    for role_name in selected_specialists:
        prompt = specialist_system_prompts.get(role_name)
        session_name = SESSIONS.get(role_name)
        if not prompt or not session_name:
            continue
        role_wait = max(85.0, wait_dev)
        if role_name in {"analyst", "architect"}:
            role_wait = max(75.0, wait_planner)
        specialist_llms[role_name] = QwenTmuxLLM(
            session_name=session_name,
            system_prompt=prompt,
            max_wait=role_wait,
        )
    dev_llm = QwenTmuxLLM(
        session_name=SESSIONS["dev"],
        system_prompt=dev_system_prompt,
        max_wait=max(90.0, wait_dev),
    )
    tester_llm = QwenTmuxLLM(
        session_name=SESSIONS["tester"],
        system_prompt=tester_system_prompt,
        max_wait=max(75.0, wait_tester),
    )
    qa_llm = QwenTmuxLLM(
        session_name=SESSIONS["qa"],
        system_prompt=qa_system_prompt,
        max_wait=max(90.0, wait_qa),
    )
    manager_llm = None
    if with_manager:
        manager_llm = QwenTmuxLLM(
            session_name=SESSIONS["manager"],
            system_prompt=manager_system_prompt,
            max_wait=max(80.0, wait_qa),
        )

    planner = autogen.ConversableAgent(
        name="Planner",
        system_message="PLANNER (AutoGen) — réponds en français.",
        llm_config=False,
        human_input_mode="NEVER",
    )
    specialist_agents: Dict[str, Any] = {}
    for role_name in selected_specialists:
        llm = specialist_llms.get(role_name)
        spec = SPECIALIST_ROLE_SPECS.get(role_name) or {}
        if llm is None:
            continue
        agent_name = str(spec.get("agent_name") or role_name).strip() or role_name
        system_message = f"{agent_name.upper()} (AutoGen) — réponds en français."
        if role_name == "architect":
            system_message += " Challenge les angles morts."
        specialist_agent = autogen.ConversableAgent(
            name=agent_name,
            system_message=system_message,
            llm_config=False,
            human_input_mode="NEVER",
        )
        specialist_agent._tmux_llm = llm  # type: ignore[attr-defined]
        specialist_agents[role_name] = specialist_agent
    dev = autogen.ConversableAgent(
        name="Dev",
        system_message="DEV (AutoGen) — réponds en français.",
        llm_config=False,
        human_input_mode="NEVER",
    )
    tester = autogen.ConversableAgent(
        name="Tester",
        system_message="TESTER (AutoGen) — réponds en français.",
        llm_config=False,
        human_input_mode="NEVER",
    )
    qa = autogen.ConversableAgent(
        name="QualityObserver",
        system_message="QA (AutoGen) — réponds en français.",
        llm_config=False,
        human_input_mode="NEVER",
    )
    manager = None
    if with_manager:
        manager = autogen.ConversableAgent(
            name="DeliveryManager",
            system_message="DELIVERY_MANAGER (AutoGen) — réponds en français, décide GO/NO-GO.",
            llm_config=False,
            human_input_mode="NEVER",
        )

    planner._tmux_llm = planner_llm  # type: ignore[attr-defined]
    dev._tmux_llm = dev_llm          # type: ignore[attr-defined]
    tester._tmux_llm = tester_llm    # type: ignore[attr-defined]
    qa._tmux_llm = qa_llm            # type: ignore[attr-defined]
    if manager and manager_llm:
        manager._tmux_llm = manager_llm  # type: ignore[attr-defined]
    round_divisor_state = {"value": 3}

    def tmux_reply(recipient, messages, sender, config):
        turn_state["index"] += 1
        turn_index = int(turn_state["index"])
        round_divisor = max(1, int(round_divisor_state["value"]))
        round_index = max(1, int((turn_index - 1) / round_divisor) + 1)
        started_at = time.time()

        ctx_text = _format_autogen_context(messages or [], max_msgs=10)
        if not ctx_text:
            ctx_text = feature.strip()
        sender_name = getattr(sender, "name", None) or "Runner"
        recipient_name = getattr(recipient, "name", None) or "Agent"
        required_sections = _required_sections_for_agent(recipient_name, execution_profile)
        team_board = agent_bus_recent_text(
            ctx,
            limit=8,
            exclude_sender=recipient_name,
            include_kinds=("feature", "phase", "response", "note", "decision", "qa"),
        )
        agent_memory = load_agent_memory_context(recipient_name)
        section_contract = ""
        if required_sections:
            section_lines = "\n".join(f"- {sec}: ..." for sec in required_sections)
            section_contract = dedent(
                f"""
                CONTRAT SECTIONS OBLIGATOIRES
                -----------------------------
                {section_lines}
                - VERDICT doit être PASS ou BLOCKED.
                - BLOCKER_ID doit être NONE si PASS, sinon identifiant explicite.
                - NEXT_ACTION_UNIQUE doit contenir UNE action exécutable immédiatement.
                """
            ).strip()

        prompt = dedent(f"""
        CONTEXTE (dernier échanges)
        --------------------------
        {ctx_text}

        CANAL ÉQUIPE (messages récents)
        --------------------------------
        {team_board or "(vide)"}

        MÉMOIRE AGENT (persistante inter-runs)
        --------------------------------------
        {agent_memory or "(vide)"}

        RÉFÉRENCE TECHNIQUE OBLIGATOIRE (API)
        -------------------------------------
        {api_guidance}

        RÈGLES
        ------
        - Ne recopie pas le prompt.
        - Réponds en français.
        - Réponse courte, structurée, actionnable.
        {section_contract}

        TA RÉPONSE
        ----------
        """).strip()
        if len(prompt) > 12000:
            prompt = prompt[:12000] + "\n...[prompt tronqué]..."

        transcript_append(ctx, recipient.name, "PROMPT", prompt)
        agent_bus_append(
            ctx,
            sender=sender_name,
            recipient=recipient_name,
            kind="prompt",
            content=f"Prompt envoyé à {recipient_name} ({len(prompt)} chars).",
        )
        event_append(
            ctx,
            {
                "type": "turn_prompt",
                "turn": turn_index,
                "round": round_index,
                "from": sender_name,
                "to": recipient_name,
                "prompt_chars": len(prompt),
            },
        )

        llm = getattr(recipient, "_tmux_llm", None)
        if llm is None:
            _die(f"Agent '{recipient.name}' n'a pas de _tmux_llm attaché.")
        pre_sig = git_dirty_file_signatures()
        sess_name = str(getattr(getattr(llm, "session", None), "session", "") or "")
        pane_before = tmux_capture(sess_name, last_lines=CAPTURE_LAST_LINES) if sess_name else ""
        reply = llm.chat(prompt)
        pane_after = tmux_capture(sess_name, last_lines=CAPTURE_LAST_LINES) if sess_name else ""
        post_sig = git_dirty_file_signatures()
        file_delta = _changed_files_between(pre_sig, post_sig)
        delta_text = _delta_text(pane_before, pane_after)
        commands = extract_shell_commands(delta_text, max_cmds=AGENT_EVENTS_MAX_COMMANDS)
        if not commands:
            commands = extract_shell_commands(reply, max_cmds=AGENT_EVENTS_MAX_COMMANDS)
        duration_ms = int((time.time() - started_at) * 1000)
        quality = classify_agent_response(reply, required_sections=required_sections)
        rewrite_happened = False
        rewrite_details: Dict[str, Any] = {}
        if _env_bool("FC_AGENT_AUTO_REWRITE", default=True):
            triggers_raw = os.environ.get(
                "FC_AGENT_AUTO_REWRITE_WARNINGS",
                "asks_question,too_long,meta_reasoning",
            )
            triggers = {x.strip().lower() for x in triggers_raw.split(",") if x.strip()}
            if required_sections:
                triggers.add("missing_sections")
            rewrite_passes = max(
                1,
                int(os.environ.get("FC_AGENT_AUTO_REWRITE_MAX_PASSES", "1") or "1"),
            )
            if required_sections:
                rewrite_passes = max(rewrite_passes, 2)
            initial_reply = reply
            initial_quality = dict(quality)
            rewrites_applied = 0
            for _ in range(rewrite_passes):
                if not any(w in triggers for w in quality["warnings"]):
                    break
                previous_reply = reply
                previous_quality = dict(quality)
                missing_sections = quality.get("missing_sections") or []
                missing_hint = ", ".join(missing_sections) if missing_sections else "none"
                rewrite_prompt = dedent(f"""
                Reformule ta DERNIÈRE réponse immédiatement.
                Contraintes strictes:
                - Réponds en français.
                - Max 5 puces courtes.
                - Aucune question.
                - Aucun méta-commentaire.
                - Si une commande est nécessaire, mets-la dans un bloc bash.
                - Sections manquantes actuelles: {missing_hint}.
                - Si un contrat de sections est attendu, respecte-le strictement.

                Réponse à reformuler:
                { _compact_bus_content(previous_reply, max_chars=1800) }

                Donne uniquement la version finale.
                """).strip()
                rewritten = llm.chat(rewrite_prompt)
                rewritten_quality = classify_agent_response(rewritten, required_sections=required_sections)

                def _score(q: Dict[str, Any], txt: str) -> int:
                    missing_penalty = int(len(q.get("missing_sections") or [])) * 40
                    return int(len(q.get("warnings") or [])) * 100 + missing_penalty + int(len((txt or "").strip()))

                if _score(rewritten_quality, rewritten) <= _score(previous_quality, previous_reply):
                    reply = rewritten
                    quality = rewritten_quality
                    rewrite_happened = True
                    rewrites_applied += 1
                    rewritten_commands = extract_shell_commands(reply, max_cmds=AGENT_EVENTS_MAX_COMMANDS)
                    if rewritten_commands:
                        commands = rewritten_commands
                else:
                    break
            if rewrite_happened:
                rewrite_details = {
                    "before_warnings": initial_quality.get("warnings") or [],
                    "after_warnings": quality.get("warnings") or [],
                    "before_chars": len((initial_reply or "").strip()),
                    "after_chars": len((reply or "").strip()),
                    "rewrite_passes_applied": rewrites_applied,
                    "missing_sections_after": quality.get("missing_sections") or [],
                }

        transcript_append(ctx, recipient.name, "RESPONSE", reply)
        agent_bus_append(
            ctx,
            sender=recipient_name,
            recipient="team",
            kind="response",
            content=reply,
        )
        event_append(
            ctx,
            {
                "type": "turn_response",
                "turn": turn_index,
                "round": round_index,
                "agent": recipient_name,
                "duration_ms": duration_ms,
                "response_chars": len((reply or "").strip()),
                "commands": commands,
                "files_touched": file_delta["touched"],
                "files_created": file_delta["created"],
                "files_deleted": file_delta["deleted"],
                "quality": quality,
                "rewritten": rewrite_happened,
            },
        )
        if rewrite_happened:
            event_append(
                ctx,
                {
                    "type": "turn_rewrite",
                    "turn": turn_index,
                    "round": round_index,
                    "agent": recipient_name,
                    **rewrite_details,
                },
            )
        _update_agent_summary(
            recipient_name,
            duration_ms=duration_ms,
            commands=commands,
            files_touched=file_delta["touched"],
            warnings=quality["warnings"],
        )
        append_agent_memory(
            recipient_name,
            run_id=ctx.run_id,
            feature=feature,
            reply=reply,
            commands=commands,
            files_touched=file_delta["touched"],
            warnings=quality["warnings"],
        )
        event_append(
            ctx,
            {
                "type": "memory_update",
                "agent": recipient_name,
                "memory_file": str(_agent_memory_file(recipient_name)),
                "warnings": quality["warnings"],
            },
        )
        agent_bus_write_board(ctx)
        return True, reply

    chat_agents = [planner]
    for role_name in selected_specialists:
        specialist_agent = specialist_agents.get(role_name)
        if specialist_agent is not None:
            chat_agents.append(specialist_agent)
    chat_agents.extend([dev, tester])
    if manager is not None:
        chat_agents.append(manager)
    reply_agents = list(chat_agents) + [qa]
    round_divisor_state["value"] = max(3, len(chat_agents))

    for ag in reply_agents:
        ag.register_reply(
            trigger=[autogen.Agent, None],
            reply_func=tmux_reply,
            position=0,
        )

    # --------- FIX: calcul "tours" réellement exécutés ----------
    # On veut au minimum Planner->Dev->Tester (3 tours) par round,
    # et un peu de marge.
    participants_count = max(2, len(chat_agents))
    max_turns = max(6, int(max_rounds) * participants_count)

    # Certaines versions utilisent max_round (et l'interprètent bizarrement).
    # On le met large pour ne pas couper prématurément.
    groupchat = autogen.GroupChat(
        agents=chat_agents,
        messages=[],
        max_round=max_turns,
        speaker_selection_method="round_robin",
        allow_repeat_speaker=False,
    )
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=False)

    transcript_append(ctx, "Runner", "INFO", f"AutoGen-tmux kickoff. max_rounds={max_rounds} max_turns={max_turns}")
    event_append(
        ctx,
        {
            "type": "chat_start",
            "max_rounds": int(max_rounds),
            "max_turns": int(max_turns),
            "specialist_roles": selected_specialists,
            "participants": [getattr(a, "name", "?") for a in chat_agents],
        },
    )

    # Compat autogen: certaines versions utilisent max_turns, d'autres max_round.
    init_sig = inspect.signature(planner.initiate_chat)
    if "max_turns" in init_sig.parameters:
        planner.initiate_chat(manager, message=feature, max_turns=max_turns)
    else:
        planner.initiate_chat(manager, message=feature, max_round=max_turns)

    transcript_append(ctx, "Runner", "INFO", "PHASE QA (autogen-tmux): pytest + git")
    agent_bus_append(ctx, sender="Runner", recipient="QualityObserver", kind="phase", content="PHASE QA")
    event_append(ctx, {"type": "qa_phase_start"})

    pg = run_pytest_tool()
    pattern = infer_test_pattern(feature, default="health")
    pt = run_specific_tests_tool(pattern)
    status = git_status_tool()
    diff = git_diff_tool(max_lines=220)

    qa_contract = ""
    if exemplary:
        qa_contract = dedent(
            """
            Contrat de sortie obligatoire (mode exemplaire):
            STATE:
            EVIDENCE:
            RISKS:
            PRIORITIES:
            VERDICT: PASS|BLOCKED
            BLOCKER_ID: NONE|<ID>
            NEXT_ACTION_UNIQUE:
            """
        ).strip()

    qa_prompt = dedent(f"""
    Contexte: Finance Copilot (FastAPI/Python).

    FEATURE
    -------
    {feature}

    RÉFÉRENCE API (OBLIGATOIRE SI ENDPOINT TOUCHÉ)
    ----------------------------------------------
    {api_guidance}

    PYTEST GLOBAL
    ------------
    {pg["output"]}

    PYTEST CIBLÉ (-k {pattern})
    --------------------------
    {pt["output"]}

    GIT STATUS
    ----------
    {status or "(aucun changement)"}

    GIT DIFF (tronqué)
    ------------------
    {diff or "(diff vide)"}

    Fais ton rapport QA + dis si prêt pour merge (avec revue humaine).
    Inclure explicitement un verdict de conformité à la référence API ci-dessus.
    {qa_contract}
    """).strip()

    transcript_append(ctx, "QualityObserver", "PROMPT", qa_prompt)
    agent_bus_append(
        ctx,
        sender="Runner",
        recipient="QualityObserver",
        kind="prompt",
        content=qa_prompt,
    )
    report = qa_llm.chat(qa_prompt)
    qa_required_sections = _required_sections_for_agent("qualityobserver", execution_profile)
    qa_quality = classify_agent_response(report, required_sections=qa_required_sections)
    transcript_append(ctx, "QualityObserver", "RESPONSE", report)
    agent_bus_append(
        ctx,
        sender="QualityObserver",
        recipient="team",
        kind="response",
        content=report,
    )
    append_agent_memory(
        "QualityObserver",
        run_id=ctx.run_id,
        feature=feature,
        reply=report,
        commands=[],
        files_touched=[],
        warnings=qa_quality["warnings"],
    )
    _update_agent_summary(
        "QualityObserver",
        duration_ms=0,
        commands=[],
        files_touched=[],
        warnings=qa_quality["warnings"],
    )
    agent_bus_write_board(ctx)
    event_append(
        ctx,
        {
            "type": "qa_phase_done",
            "report_chars": len((report or "").strip()),
            "pytest_global_ok": pg.get("ok"),
            "pytest_target_ok": pt.get("ok"),
            "quality": qa_quality,
        },
    )
    if manager_llm is not None:
        manager_contract = ""
        if exemplary:
            manager_contract = dedent(
                """
                Contrat de sortie obligatoire (mode exemplaire):
                DECISION:
                RISKS:
                ACTIONS:
                VERDICT: PASS|BLOCKED
                BLOCKER_ID: NONE|<ID>
                NEXT_ACTION_UNIQUE:
                """
            ).strip()
        delivery_prompt = dedent(f"""
        Tu es DELIVERY_MANAGER.
        Objectif initial:
        {feature}

        Référence API obligatoire si endpoints touchés:
        {api_guidance}

        Rapport QA:
        {report}

        Donne:
        1) Décision: GO ou NO-GO
        2) Top 3 risques bloquants (ou "aucun")
        3) Actions immédiates (max 5)
        Réponse concise et finale.
        {manager_contract}
        """).strip()
        transcript_append(ctx, "DeliveryManager", "PROMPT", delivery_prompt)
        agent_bus_append(
            ctx,
            sender="Runner",
            recipient="DeliveryManager",
            kind="prompt",
            content=f"Prompt DeliveryManager ({len(delivery_prompt)} chars).",
        )
        manager_report = manager_llm.chat(delivery_prompt)
        transcript_append(ctx, "DeliveryManager", "RESPONSE", manager_report)
        agent_bus_append(
            ctx,
            sender="DeliveryManager",
            recipient="team",
            kind="decision",
            content=manager_report,
        )
        manager_required_sections = _required_sections_for_agent("deliverymanager", execution_profile)
        quality_manager = classify_agent_response(manager_report, required_sections=manager_required_sections)
        append_agent_memory(
            "DeliveryManager",
            run_id=ctx.run_id,
            feature=feature,
            reply=manager_report,
            commands=[],
            files_touched=[],
            warnings=quality_manager["warnings"],
        )
        event_append(
            ctx,
            {
                "type": "delivery_gate",
                "response_chars": len((manager_report or "").strip()),
                "quality": quality_manager,
            },
        )
        _update_agent_summary(
            "DeliveryManager",
            duration_ms=0,
            commands=[],
            files_touched=[],
            warnings=quality_manager["warnings"],
        )
        agent_bus_write_board(ctx)

    if with_codex_reviewer:
        transcript_append(ctx, "CodexReviewer", "INFO", "Independent review gate started (codex review --uncommitted).")
        agent_bus_append(
            ctx,
            sender="Runner",
            recipient="CodexReviewer",
            kind="phase",
            content="Independent reviewer phase via Codex instance.",
        )
        started = time.time()
        try:
            codex_result = run_codex_independent_review(feature=feature, qa_report=report, timeout_sec=int(max(wait_qa, 120)))
            codex_reply = codex_result.get("output", "").strip()
            codex_ok = codex_result.get("ok", "false") == "true"
        except Exception as e:
            codex_reply = f"BLOCKED\nIndependent Codex reviewer failed: {e}"
            codex_ok = False

        duration_ms = int((time.time() - started) * 1000)
        transcript_append(ctx, "CodexReviewer", "RESPONSE", codex_reply)
        agent_bus_append(
            ctx,
            sender="CodexReviewer",
            recipient="team",
            kind="decision",
            content=codex_reply,
        )
        codex_required_sections = _required_sections_for_agent("codexreviewer", execution_profile)
        codex_quality = classify_agent_response(codex_reply, required_sections=codex_required_sections)
        append_agent_memory(
            "CodexReviewer",
            run_id=ctx.run_id,
            feature=feature,
            reply=codex_reply,
            commands=["codex review --uncommitted"],
            files_touched=[],
            warnings=codex_quality["warnings"],
        )
        event_append(
            ctx,
            {
                "type": "independent_review_gate",
                "reviewer": "codex",
                "ok": codex_ok,
                "duration_ms": duration_ms,
                "response_chars": len((codex_reply or "").strip()),
                "quality": codex_quality,
            },
        )
        _update_agent_summary(
            "CodexReviewer",
            duration_ms=duration_ms,
            commands=["codex review --uncommitted"],
            files_touched=[],
            warnings=codex_quality["warnings"],
        )
        agent_bus_write_board(ctx)

    write_agent_activity_summary(ctx, activity_summary)
    event_append(
        ctx,
        {
            "type": "run_end",
            "turns": int(turn_state["index"]),
            "agents_count": len(activity_summary.get("agents") or {}),
        },
    )

    print("\n================= RAPPORT QA FINAL (AutoGen-TMUX) =================\n")
    print(report)

    return "AutoGen-tmux terminé. Voir transcript.md + snapshots."


# ==============================================================================
# Doctor / cleanup
# ==============================================================================

def doctor(ctx: RunCtx, qwen_bin: str) -> None:
    autogen_ok = True
    autogen_detail = "OK"
    try:
        require_module("autogen")
    except Exception as e:
        autogen_ok = False
        autogen_detail = str(e)

    require_bin("tmux")
    require_executable(qwen_bin)
    agent_name = _cli_name_from_bin(qwen_bin)

    lines: List[str] = []
    lines.append(f"# Doctor report ({datetime.now().isoformat(timespec='seconds')})")
    lines.append("")
    lines.append(f"- PROJECT_DIR: {PROJECT_DIR} ({'OK' if PROJECT_DIR.exists() else 'MISSING'})")
    lines.append(f"- BACKEND_DIR: {BACKEND_DIR} ({'OK' if BACKEND_DIR.exists() else 'MISSING'})")
    lines.append(f"- autogen: {'OK' if autogen_ok else 'MISSING'}")
    if not autogen_ok:
        lines.append(f"  - detail: {autogen_detail}")
    lines.append(f"- tmux: {which('tmux')}")
    lines.append(f"- agent_cli ({agent_name}): {qwen_bin}")
    lines.append(f"- python venv: {VENV_PY} ({'OK' if VENV_PY.exists() else 'MISSING'})")
    lines.append("")
    lines.append("## Sessions")
    lines.append("```")
    lines.append(qwen_status())
    lines.append("```")

    (ctx.run_dir / "doctor_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    snapshot_all(ctx)


def cleanup_runs(runs_dir: Path, keep_last: int = 10) -> int:
    if not runs_dir.exists():
        return 0
    run_dirs = sorted([p for p in runs_dir.iterdir() if p.is_dir()], key=lambda p: p.name)
    to_delete = run_dirs[:-keep_last] if keep_last >= 0 else run_dirs
    n = 0
    for d in to_delete:
        try:
            shutil.rmtree(d, ignore_errors=False)
            n += 1
        except Exception:
            pass
    return n


# ==============================================================================
# Main feature runner
# ==============================================================================

def run_feature(
    feature: str,
    max_rounds: int,
    restart_tmux: bool,
    runs_dir: Path,
    qwen_bin: str,
    enable_tmux_logs: bool,
    max_log_mb: int,
    mode: str,
    clean_startup: bool,
    wait_planner: float,
    wait_dev: float,
    wait_tester: float,
    wait_qa: float,
    specialist_roles: Optional[List[str]] = None,
    with_architect: bool = False,
    with_manager: bool = False,
    with_codex_reviewer: bool = False,
    execution_profile: str = "standard",
):
    execution_profile = (execution_profile or "standard").strip().lower()
    if execution_profile not in {"standard", "exemplary"}:
        execution_profile = "standard"
    exemplary = execution_profile == "exemplary"

    ensure_project_exists()
    ensure_tmux_exists()
    require_module("autogen")
    ensure_api_best_practices_doc(required=True)
    api_doc_ref = api_best_practices_doc_reference()
    if with_codex_reviewer:
        require_bin("codex")
    qwen_bin = require_executable(qwen_bin)
    set_active_agent_cli(qwen_bin)
    selected_specialists = ensure_specialist_sessions(
        resolve_specialist_roles(
            team_profile="core",
            specialists_raw="",
            explicit_roles=specialist_roles,
            with_architect=with_architect,
        )
    )

    if with_manager:
        ensure_role_session("manager", "FC_SESS_MANAGER", "qwen_manager")

    ctx = create_run_ctx(runs_dir)
    sentry_set_context(run_id=ctx.run_id, mode=mode, tmux_cmd="")
    sentry_add_breadcrumb(
        "feature_run_started",
        data={
            "run_id": ctx.run_id,
            "mode": mode,
            "rounds": max_rounds,
            "runs_dir": str(runs_dir),
            "execution_profile": execution_profile,
            "specialist_roles": selected_specialists,
            "api_best_practices_doc": api_doc_ref,
        },
    )

    if mode == "debug":
        marker = create_marker(ctx.run_id)
        transcript_append(ctx, "Runner", "INFO", f"Marker pre-created: {marker}")
        feature = build_debug_feature(ctx.run_id)
        transcript_append(ctx, "Runner", "INFO", "Feature replaced by DEBUG feature.")

    write_manifest(
        ctx,
        feature=feature,
        qwen_bin=qwen_bin,
        extra={
            "mode": mode,
            "engine": "autogen_tmux",
            "execution_profile": execution_profile,
            "agent_cli": active_agent_cli_name(),
            "with_architect": bool(with_architect),
            "specialist_roles": selected_specialists,
            "with_manager": bool(with_manager),
            "with_codex_reviewer": bool(with_codex_reviewer),
            "agent_memory_dir": str(AGENT_MEMORY_DIR),
            "api_best_practices_doc": api_doc_ref,
        },
    )

    if exemplary:
        transcript_append(ctx, "Runner", "INFO", "EXEMPLARY profile enabled: running mandatory preflight gates.")
        preflight = run_exemplary_preflight(ctx)
        event_append(
            ctx,
            {
                "type": "exemplary_preflight_summary",
                "ok": bool(preflight.get("ok")),
                "failures": preflight.get("failures") or [],
            },
        )
        if not preflight.get("ok"):
            failures = preflight.get("failures") or []
            failure_names = [str(f.get("name") or "unknown") for f in failures]
            transcript_append(
                ctx,
                "Runner",
                "INFO",
                f"BLOCKED: exemplary preflight failed ({', '.join(failure_names)}).",
            )
            print("❌ EXEMPLARY PREFLIGHT BLOCKED")
            for f in failures:
                print(f"- {f.get('name')}: rc={f.get('returncode')}")
            return ctx

    qwen_start(
        qwen_bin=qwen_bin,
        path_override=DEFAULT_PATH_OVERRIDE,
        auto_confirm=AUTO_CONFIRM,
        restart=restart_tmux,
        ctx=ctx,
        enable_tmux_logs=enable_tmux_logs,
        clean_startup=clean_startup,
    )

    snapshot_all(ctx)

    print(f"🧾 Run dir → {ctx.run_dir}")
    print(f"   transcript: {ctx.transcript_path}")
    if enable_tmux_logs:
        print(f"   tmux logs:  {ctx.tmux_dir}")

    _ = run_feature_autogen_tmux(
        ctx=ctx,
        feature=feature,
        max_rounds=max_rounds,
        wait_planner=wait_planner,
        wait_dev=wait_dev,
        wait_tester=wait_tester,
        wait_qa=wait_qa,
        specialist_roles=selected_specialists,
        with_architect=with_architect,
        with_manager=with_manager,
        with_codex_reviewer=with_codex_reviewer,
        execution_profile=execution_profile,
    )

    if enable_tmux_logs:
        max_bytes = max_log_mb * 1024 * 1024
        for sess in session_names():
            lf = ctx.tmux_dir / f"{sess}.log"
            rotate_if_too_big(sess, lf, max_bytes)

    snapshot_all(ctx)
    return ctx


# ==============================================================================
# CLI docs (help text)
# ==============================================================================

def usage_text() -> str:
    return dedent(f"""
    Utilisation rapide
    ==================

    1) AutoGen -> TMUX (solution unique)
       python3 scripts/qwen_orchestrator.py --rounds 2 --feature "Implémente GET /health"
       python3 scripts/qwen_orchestrator.py --rounds 3 --with-architect --with-manager --with-codex-reviewer --feature "..."
       python3 scripts/qwen_orchestrator.py --team-profile engineering --specialists analyst,architect,backend-engineer,security-engineer --rounds 2 --feature "..."
       python3 scripts/qwen_orchestrator.py --execution-profile exemplary --rounds 2 --feature "..."
       python3 scripts/qwen_orchestrator.py --agent-bin codex --rounds 2 --feature "Implémente GET /health"

    2) Mode debug
       python3 scripts/qwen_orchestrator.py --mode debug --rounds 1 --restart

    3) Management tmux
       python3 scripts/qwen_orchestrator.py --tmux-cmd status
       python3 scripts/qwen_orchestrator.py --tmux-cmd status --status-format json
       python3 scripts/qwen_orchestrator.py --tmux-cmd health
       python3 scripts/qwen_orchestrator.py --tmux-cmd start
       python3 scripts/qwen_orchestrator.py --tmux-cmd restart
       python3 scripts/qwen_orchestrator.py --tmux-cmd stop --tmux-all
       python3 scripts/qwen_orchestrator.py --tmux-cmd attach --tmux-target dev
       python3 scripts/qwen_orchestrator.py --tmux-cmd ping
       python3 scripts/qwen_orchestrator.py --tmux-cmd prompt --tmux-target dev --prompt "Donne 3 TODO backend"
       python3 scripts/qwen_orchestrator.py --tmux-cmd prompt --prompt-engine sdk --prompt "Donne 3 TODO backend"

    Notes
    -----
    - Par défaut, les runs sont stockés dans:
      {RUNS_DIR_DEFAULT}
      avec un pointeur "latest" vers la dernière exécution.
    - Référence endpoint/API injectée automatiquement dans les prompts:
      {api_best_practices_doc_reference()}
    - Sentry orchestrator (optionnel):
      - ORCH_SENTRY_DSN (ou SENTRY_DSN)
      - ORCH_SENTRY_TRACES_SAMPLE_RATE (défaut: 0.1)
      - ORCH_SENTRY_PROFILE_SESSION_SAMPLE_RATE / ORCH_SENTRY_PROFILES_SAMPLE_RATE (défaut: 0.0)
      - ORCH_SENTRY_ENABLE_LOGS=true|false
    - Mode prompt SDK (sans nettoyage TUI tmux):
      - Bridge: {SDK_BRIDGE_DEFAULT}
      - npm install @qwen-code/sdk (Node >= 20)
      - CLI: utiliser le bundle SDK par défaut (évite les bugs TUI du binaire local)
      - Optionnel: --sdk-path-to-qwen-executable /path/to/qwen
      - utilise --prompt-engine sdk sur tmux-cmd=prompt|ping
    - Workaround TUI qwen 0.4.0:
      - le launcher nettoie NO_COLOR/TERM par défaut pour éviter
        "Invalid number of stops (< 2)"
      - désactiver ce comportement via FC_QWEN_SANITIZE_COLOR_ENV=0
      - si la TUI quitte quand même en tmux detached, prompt bascule vers SDK
        (désactiver via FC_QWEN_TMUX_FALLBACK_SDK=0)
    - Pour run de feature: autogen/tmux + CLI agent (qwen/codex) doivent être présents sinon erreur.
    - Pour management tmux (status/start/stop/attach/ping/prompt): autogen n'est pas requis.
    - status/health supporte:
      --status-format text|compact|json
      --status-core-roles planner,dev,tester,qa
      --status-strict (exit non-zero si rôles requis DOWN)
    - SDK memory: getSessionId est persisté dans {SDK_SESSION_STATE_FILE}
      (clé par agent/session), puis réutilisé via --resume pour garder le contexte.
    - Mémoire agent persistante (inter-runs) dans:
      {AGENT_MEMORY_DIR}
      injectée dans les prompts sous "MÉMOIRE AGENT".
    - Team multi-agents (architects/analysts/engineers):
      --team-profile core|architecture|engineering|full
      --specialists analyst,architect,backend-engineer,frontend-engineer,data-engineer,security-engineer,devops-engineer
      --with-architect reste compatible (legacy).
      Sessions par défaut:
      analyst={SESSIONS.get('analyst','qwen_analyst')}
      architect={SESSIONS.get('architect','qwen_architect')}
      backend_engineer={SESSIONS.get('backend_engineer','qwen_backend_engineer')}
      frontend_engineer={SESSIONS.get('frontend_engineer','qwen_frontend_engineer')}
      data_engineer={SESSIONS.get('data_engineer','qwen_data_engineer')}
      security_engineer={SESSIONS.get('security_engineer','qwen_security_engineer')}
      devops_engineer={SESSIONS.get('devops_engineer','qwen_devops_engineer')}
    - Rôles avancés optionnels:
      --with-manager --with-codex-reviewer
      (session manager={SESSIONS.get('manager','qwen_manager')})
      --with-codex-reviewer lance une revue indépendante via `codex review --uncommitted`
    - Tu peux ajouter des rôles custom via FC_EXTRA_SESSIONS ou --sessions:
      ex: security=qwen_security,docs=qwen_docs
    - tmux capture utilise history + join wrap (-J), et history-limit est augmenté.
    - Chaque exécution crée un run_dir:
        {RUNS_DIR_DEFAULT}/YYYYMMDD-HHMMSS-mmm/
          - run.json
          - transcript.md
          - agent_bus.jsonl
          - agent_board.md
          - events.jsonl (tours, durées, commandes détectées, fichiers touchés)
          - agent_activity.json (résumé par agent)
          - tmux/*.log (si activé)
          - snapshots/*.txt
          - doctor_report.md (si doctor)
    - Analyse des runs:
      python3 scripts/analyze_orchestrator_runs.py --limit 10
    """).strip()


# ==============================================================================
# Main
# ==============================================================================

def main():
    argv = sys.argv[1:]
    if not should_skip_venv_reexec(argv):
        ensure_venv_or_reexec()

    ap = argparse.ArgumentParser(description="Finance Copilot orchestrator (AutoGen + tmux CLI agents).", add_help=True)

    ap.add_argument("--feature", type=str, default=os.environ.get("FC_FEATURE", "").strip(),
                    help="Texte de la feature (sinon FC_FEATURE)")
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--restart", action="store_true", help="Kill+restart sessions tmux avant de run")

    ap.add_argument("--mode", type=str, default="normal", choices=["normal", "debug"],
                    help="normal: feature ; debug: smoke test marker + prompts déterministes")
    ap.add_argument(
        "--execution-profile",
        type=str,
        default=os.environ.get("FC_EXECUTION_PROFILE", "standard"),
        choices=["standard", "exemplary"],
        help="standard: comportement actuel ; exemplary: preflight obligatoire + contrat de réponse strict.",
    )

    ap.add_argument("--runs-dir", type=str, default=str(RUNS_DIR_DEFAULT))
    ap.add_argument("--no-tmux-logs", action="store_true", help="Désactive pipe-pane tmux raw logs")
    ap.add_argument("--max-log-mb", type=int, default=25, help="Rotation pipe-pane si log > N MB")

    ap.add_argument("--no-clean-startup", action="store_true", help="Ne pas clear-history au démarrage des sessions tmux")

    ap.add_argument(
        "--agent-bin",
        type=str,
        default=os.environ.get("FC_AGENT_BIN", "").strip(),
        help="CLI agent à lancer dans tmux (ex: qwen, codex, /path/to/bin).",
    )
    ap.add_argument(
        "--qwen-bin",
        type=str,
        default=(which("qwen") or "qwen"),
        help="Compat legacy (équivalent à --agent-bin quand --agent-bin est absent).",
    )

    ap.add_argument("--wait-planner", type=float, default=60.0)
    ap.add_argument("--wait-dev", type=float, default=90.0)
    ap.add_argument("--wait-tester", type=float, default=75.0)
    ap.add_argument("--wait-qa", type=float, default=90.0)
    ap.add_argument("--with-architect", action="store_true", help="Ajoute l'agent Architect au groupchat")
    ap.add_argument("--with-manager", action="store_true", help="Ajoute DeliveryManager (groupchat + gate final)")
    ap.add_argument("--with-codex-reviewer", action="store_true", help="Ajoute un reviewer indépendant via `codex review --uncommitted`")
    ap.add_argument(
        "--team-profile",
        type=str,
        default="core",
        choices=sorted(SPECIALIST_TEAM_PROFILES.keys()),
        help="Profil d'équipe spécialistes: core|architecture|engineering|full",
    )
    ap.add_argument(
        "--specialists",
        type=str,
        default="",
        help=(
            "Spécialistes supplémentaires (csv): "
            "analyst,architect,backend-engineer,frontend-engineer,data-engineer,security-engineer,devops-engineer"
        ),
    )

    ap.add_argument("--sessions", type=str, default="",
                    help="Overrides sessions role=session (comma/semicolon separated). Ex: dev=qwen_dev2,security=qwen_sec")
    ap.add_argument("--prompt", type=str, default="", help="Prompt texte pour tmux-cmd=prompt")
    ap.add_argument("--system-prompt", type=str, default="", help="System prompt optionnel pour tmux-cmd=prompt")
    ap.add_argument(
        "--prompt-engine",
        type=str,
        default=os.environ.get("FC_PROMPT_ENGINE", "tmux"),
        choices=["tmux", "sdk"],
        help="Moteur pour tmux-cmd=prompt|ping: tmux (par défaut) ou sdk",
    )
    ap.add_argument(
        "--sdk-permission-mode",
        type=str,
        default=os.environ.get("FC_QWEN_SDK_PERMISSION_MODE", "default"),
        help="Mode permissions SDK: default|plan|auto-edit|yolo",
    )
    ap.add_argument("--sdk-model", type=str, default=os.environ.get("FC_QWEN_SDK_MODEL", "").strip())
    ap.add_argument("--sdk-debug", action="store_true", help="Active debug du bridge SDK")
    ap.add_argument(
        "--sdk-path-to-qwen-executable",
        type=str,
        default=os.environ.get("FC_QWEN_SDK_CLI_PATH", "").strip(),
        help="Optionnel: chemin qwen CLI pour le SDK (sinon CLI bundle SDK)",
    )

    # management commands
    ap.add_argument("--tmux-cmd", type=str, default="",
                    help="Commande: status|health|start|stop|restart|attach|doctor|cleanup|clear|ping|prompt")
    ap.add_argument("--tmux-target", type=str, default="",
                    help="Pour stop/attach/clear/ping/prompt: role (planner/dev/tester/qa/...) ou nom de session")
    ap.add_argument("--tmux-all", action="store_true", help="Pour stop: stop toutes les sessions")
    ap.add_argument("--keep-last", type=int, default=10, help="Pour cleanup: garder N derniers runs")
    ap.add_argument(
        "--status-format",
        type=str,
        default=os.environ.get("FC_STATUS_FORMAT", "text"),
        choices=["text", "compact", "json"],
        help="Format pour tmux-cmd=status|health",
    )
    ap.add_argument(
        "--status-core-roles",
        type=str,
        default=os.environ.get("FC_STATUS_CORE_ROLES", ",".join(CORE_STATUS_ROLES_DEFAULT)),
        help="Rôles requis pour verdict status/health (csv). Ex: planner,dev,tester,qa",
    )
    ap.add_argument(
        "--status-strict",
        action="store_true",
        help="Avec tmux-cmd=status|health: exit non-zero si rôles requis DOWN.",
    )

    ap.add_argument("--print-usage", action="store_true", help="Affiche une doc d'utilisation + exit")

    args = ap.parse_args()
    apply_session_overrides(args.sessions)
    selected_specialists = ensure_specialist_sessions(
        resolve_specialist_roles(
            team_profile=args.team_profile,
            specialists_raw=args.specialists,
            with_architect=bool(args.with_architect),
        )
    )
    if args.with_manager:
        ensure_role_session("manager", "FC_SESS_MANAGER", "qwen_manager")
    tmux_cmd = (args.tmux_cmd or "").strip().lower()
    prompt_engine = (args.prompt_engine or "tmux").strip().lower()
    selected_agent_bin = (args.agent_bin or "").strip() or args.qwen_bin
    set_active_agent_cli(selected_agent_bin)

    init_orchestrator_sentry()
    sentry_set_context(mode=args.mode, tmux_cmd=tmux_cmd or None)
    sentry_add_breadcrumb(
        "main_args_parsed",
        data={
            "mode": args.mode,
            "execution_profile": args.execution_profile,
            "tmux_cmd": tmux_cmd or "(none)",
            "prompt_engine": prompt_engine,
            "runs_dir": args.runs_dir,
            "restart": bool(args.restart),
            "team_profile": args.team_profile,
            "specialist_roles": selected_specialists,
        },
    )

    if args.print_usage:
        print(usage_text())
        return

    ensure_project_root_exists()
    ensure_tmux_exists()

    runs_dir = Path(args.runs_dir).expanduser().resolve()

    if tmux_cmd:
        if tmux_cmd in {"status", "health"}:
            core_roles = parse_role_list(args.status_core_roles)
            payload = qwen_status_payload(core_roles=core_roles)
            status_format = (args.status_format or "text").strip().lower()
            if tmux_cmd == "health" and status_format == "text":
                status_format = "compact"
            sentry_add_breadcrumb("tmux_status")
            print(qwen_status(core_roles=core_roles, fmt=status_format))
            strict = bool(args.status_strict or tmux_cmd == "health")
            if strict and payload.get("verdict") != "PASS":
                sys.exit(22)
            return

        if tmux_cmd == "start":
            ctx = create_run_ctx(runs_dir)
            sentry_set_context(run_id=ctx.run_id, mode="start", tmux_cmd="start")
            sentry_add_breadcrumb("tmux_start", data={"run_id": ctx.run_id})
            write_manifest(ctx, feature="(start only)", qwen_bin=selected_agent_bin, extra={"mode": "start", "agent_cli": active_agent_cli_name()})
            qwen_start(
                selected_agent_bin, DEFAULT_PATH_OVERRIDE, AUTO_CONFIRM,
                restart=False, ctx=ctx,
                enable_tmux_logs=not args.no_tmux_logs,
                clean_startup=not args.no_clean_startup,
            )
            print(f"✅ {active_agent_cli_name()} sessions started.")
            print(f"🧾 Run dir → {ctx.run_dir}")
            return

        if tmux_cmd == "restart":
            ctx = create_run_ctx(runs_dir)
            sentry_set_context(run_id=ctx.run_id, mode="restart", tmux_cmd="restart")
            sentry_add_breadcrumb("tmux_restart", data={"run_id": ctx.run_id})
            write_manifest(ctx, feature="(restart only)", qwen_bin=selected_agent_bin, extra={"mode": "restart", "agent_cli": active_agent_cli_name()})
            qwen_restart(
                selected_agent_bin, DEFAULT_PATH_OVERRIDE, AUTO_CONFIRM,
                ctx=ctx,
                enable_tmux_logs=not args.no_tmux_logs,
                clean_startup=not args.no_clean_startup,
            )
            print(f"✅ {active_agent_cli_name()} sessions restarted.")
            print(f"🧾 Run dir → {ctx.run_dir}")
            return

        if tmux_cmd == "stop":
            if args.tmux_all or not args.tmux_target:
                sentry_add_breadcrumb("tmux_stop_all")
                qwen_stop(all_sessions=True)
                print(f"🛑 {active_agent_cli_name()} sessions stopped (all).")
                return
            sess = resolve_session(args.tmux_target)
            sentry_add_breadcrumb("tmux_stop_one", data={"session": sess})
            qwen_stop(all_sessions=False, session=sess)
            print(f"🛑 {active_agent_cli_name()} session stopped: {sess}")
            return

        if tmux_cmd == "attach":
            target = args.tmux_target or "dev"
            sentry_add_breadcrumb("tmux_attach", data={"target": target})
            sys.exit(qwen_attach(target))

        if tmux_cmd == "doctor":
            ctx = create_run_ctx(runs_dir)
            sentry_set_context(run_id=ctx.run_id, mode="doctor", tmux_cmd="doctor")
            sentry_add_breadcrumb("tmux_doctor", data={"run_id": ctx.run_id})
            write_manifest(ctx, feature="(doctor)", qwen_bin=selected_agent_bin, extra={"mode": "doctor", "agent_cli": active_agent_cli_name()})
            doctor(ctx, qwen_bin=selected_agent_bin)
            print(f"✅ Doctor report écrit: {ctx.run_dir / 'doctor_report.md'}")
            print(f"🧾 Snapshots: {ctx.snapshots_dir}")
            return

        if tmux_cmd == "cleanup":
            sentry_add_breadcrumb("tmux_cleanup", data={"keep_last": args.keep_last})
            n = cleanup_runs(runs_dir, keep_last=args.keep_last)
            print(f"✅ Cleanup terminé. Runs supprimés: {n}. (gardés: {args.keep_last})")
            return

        if tmux_cmd == "clear":
            target = args.tmux_target or "dev"
            sess = resolve_session(target)
            sentry_add_breadcrumb("tmux_clear", data={"session": sess})
            tmux_clear_screen(sess)
            tmux_clear_history(sess)
            print(f"✅ Clear screen + history envoyé à: {sess}")
            return

        if tmux_cmd == "ping":
            target = args.tmux_target.strip()
            sentry_add_breadcrumb("tmux_ping", data={"target": target or "(all)", "engine": prompt_engine})
            if prompt_engine == "sdk":
                if not is_active_qwen_cli():
                    _die("prompt-engine=sdk est disponible uniquement avec --agent-bin qwen.")
                label = target or "sdk"
                results = {
                    label: qwen_ping_sdk(
                        max_wait=25.0,
                        model=args.sdk_model,
                        debug=bool(args.sdk_debug),
                        qwen_bin=args.sdk_path_to_qwen_executable,
                        session_key=f"sdk:{label}",
                    )
                }
            else:
                results = qwen_ping(target=target, max_wait=25.0)
            print("🏓 Ping results:")
            for label, value in results.items():
                print(f"- {label}: {value}")
            return

        if tmux_cmd == "prompt":
            target = (args.tmux_target or "dev").strip()
            if not args.prompt.strip():
                _die("tmux-cmd=prompt nécessite --prompt \"...\"")
            sentry_add_breadcrumb("tmux_prompt", data={"target": target, "engine": prompt_engine})
            if prompt_engine == "sdk":
                if not is_active_qwen_cli():
                    _die("prompt-engine=sdk est disponible uniquement avec --agent-bin qwen.")
                reply = qwen_prompt_sdk(
                    args.prompt.strip(),
                    system_prompt=(args.system_prompt or "").strip(),
                    max_wait=max(args.wait_dev, 20.0),
                    permission_mode=args.sdk_permission_mode,
                    model=args.sdk_model,
                    debug=bool(args.sdk_debug),
                    path_to_qwen_executable=args.sdk_path_to_qwen_executable,
                    session_key=f"sdk:{target}",
                    max_session_turns=int(os.environ.get("FC_QWEN_SDK_MAX_SESSION_TURNS", "-1")),
                )
            else:
                reply = qwen_prompt(
                    target,
                    args.prompt.strip(),
                    system_prompt=(args.system_prompt or "").strip(),
                    max_wait=max(args.wait_dev, 20.0),
                )
            print(reply if (reply or "").strip() else "(réponse vide)")
            return

        _die(
            f"tmux-cmd inconnu: {tmux_cmd} "
            f"(attendu: status|health|start|stop|restart|attach|doctor|cleanup|clear|ping|prompt)"
        )

    feature = args.feature or "Implémente un endpoint GET /health avec test pytest"
    sentry_add_breadcrumb(
        "feature_entrypoint",
        data={
            "feature_preview": feature[:200],
            "rounds": args.rounds,
            "mode": args.mode,
            "team_profile": args.team_profile,
            "specialist_roles": selected_specialists,
        },
    )

    ctx = run_feature(
        feature=feature,
        max_rounds=args.rounds,
        restart_tmux=args.restart,
        runs_dir=runs_dir,
        qwen_bin=selected_agent_bin,
        enable_tmux_logs=not args.no_tmux_logs,
        max_log_mb=args.max_log_mb,
        mode=args.mode,
        clean_startup=not args.no_clean_startup,
        wait_planner=args.wait_planner,
        wait_dev=args.wait_dev,
        wait_tester=args.wait_tester,
        wait_qa=args.wait_qa,
        specialist_roles=selected_specialists,
        with_architect=bool(args.with_architect),
        with_manager=bool(args.with_manager),
        with_codex_reviewer=bool(args.with_codex_reviewer),
        execution_profile=args.execution_profile,
    )

    print(f"\n✅ Terminé. Run dir: {ctx.run_dir}")
    print(f"   transcript: {ctx.transcript_path}")
    print(f"   manifest:   {ctx.manifest_path}")
    print(f"   snapshots:  {ctx.snapshots_dir}")
    if not args.no_tmux_logs:
        print(f"   tmux logs:  {ctx.tmux_dir}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        init_orchestrator_sentry()
        capture_orchestrator_exception(
            exc,
            context={
                "argv": sys.argv,
                "cwd": os.getcwd(),
                "project_dir": str(PROJECT_DIR),
            },
            flush=True,
        )
        raise
