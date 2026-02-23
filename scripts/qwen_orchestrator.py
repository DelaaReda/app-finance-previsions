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

DEFAULT_PROJECT_DIR = Path("/Users/venom/Documents/analyse-financiere").resolve()
PROJECT_DIR = Path(os.environ.get("FC_PROJECT_DIR", str(DEFAULT_PROJECT_DIR))).expanduser().resolve()

BACKEND_DIR = Path(os.environ.get("FC_BACKEND_DIR", str(PROJECT_DIR / "copilot-app" / "backend"))).expanduser().resolve()
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

# capture tuning
CAPTURE_LAST_LINES = int(os.environ.get("FC_CAPTURE_LAST_LINES", "4000"))
TMUX_HISTORY_LIMIT = int(os.environ.get("FC_TMUX_HISTORY_LIMIT", "200000"))


def now_id() -> str:
    # millisecond precision to avoid run_id collisions on fast repeated launches
    return datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]


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
        if not role or not sess:
            continue
        if not re.fullmatch(r"[a-z0-9_.-]+", role):
            continue
        if not re.fullmatch(r"[a-zA-Z0-9_.:-]+", sess):
            continue
        out[role] = sess
    return out


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


def ensure_project_exists() -> None:
    if not PROJECT_DIR.exists():
        _die(f"PROJECT_DIR introuvable: {PROJECT_DIR}")
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
    run(["tmux", "send-keys", "-t", target, text, "C-m"], capture=False)


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
    }
    if extra:
        data.update(extra)
    ctx.manifest_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def transcript_append(ctx: RunCtx, role: str, kind: str, content: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    block = f"\n## [{ts}] {role} — {kind}\n\n```\n{(content or '').rstrip()}\n```\n"
    with ctx.transcript_path.open("a", encoding="utf-8") as f:
        f.write(block)


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


def apply_session_overrides(raw: str) -> None:
    overrides = parse_role_session_pairs(raw)
    if not overrides:
        return
    SESSIONS.update(overrides)


def _parse_fc_qwen_exports() -> List[str]:
    raw = (os.environ.get("FC_QWEN_EXPORTS") or "").strip()
    if not raw:
        return []
    parts = [p.strip() for p in re.split(r"[;,]", raw) if p.strip()]
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


def build_qwen_bash_cmd(qwen_bin: str, path_override: str, auto_confirm: bool) -> str:
    setup_cmds = [f"cd {shlex.quote(str(PROJECT_DIR))}"]

    venv_activate = VENV_BIN / "activate"
    if venv_activate.exists():
        setup_cmds.append(f"source {shlex.quote(str(venv_activate))}")

    setup_cmds.append(f"export PATH={shlex.quote(path_override)}")

    # qwen-code 0.4.0 can crash in TUI with "Invalid number of stops (< 2)"
    # when NO_COLOR=1 or TERM=dumb leads to no-color gradient config.
    if _env_bool("FC_QWEN_SANITIZE_COLOR_ENV", default=True):
        setup_cmds.append("unset NO_COLOR")
        setup_cmds.append('if [ "${TERM:-dumb}" = "dumb" ]; then export TERM=xterm-256color; fi')
        setup_cmds.append('export COLORTERM="${COLORTERM:-truecolor}"')
        setup_cmds.append('export FORCE_COLOR="${FORCE_COLOR:-1}"')

    if auto_confirm:
        setup_cmds.append("export QWEN_CODE_AUTO_CONFIRM=1")

    setup_cmds.extend(_parse_fc_qwen_exports())

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


def qwen_status() -> str:
    ensure_tmux_exists()
    tmux_start_server()
    existing = set(tmux_list_sessions())
    lines: List[str] = []
    lines.append(f"Runs dir: {RUNS_DIR_DEFAULT}")
    lines.append(f"Latest run pointer: {RUNS_DIR_DEFAULT / 'latest'}")
    lines.append("Qwen tmux sessions (role -> session):")
    for role in sorted(SESSIONS.keys()):
        sess = SESSIONS[role]
        lines.append(f"  - {role} -> {sess}: {'UP' if sess in existing else 'DOWN'}")
    return "\n".join(lines)


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


def _launch_qwen_in_session(session: str) -> None:
    cmd = (
        "unset NO_COLOR; "
        'if [ "${TERM:-dumb}" = "dumb" ]; then export TERM=xterm-256color; fi; '
        'export COLORTERM="${COLORTERM:-truecolor}"; '
        'export FORCE_COLOR="${FORCE_COLOR:-1}"; '
        "qwen"
    )
    tmux_send_keys(session, cmd)


def qwen_prompt(role_or_session: str, prompt: str, system_prompt: str = "", max_wait: float = 60.0) -> str:
    ensure_tmux_exists()
    tmux_start_server()
    sess = resolve_session(role_or_session)
    if not tmux_has_session(sess):
        _die(f"Session tmux absente: {sess}. Lance d'abord --tmux-cmd start.")

    fallback_sdk = _env_bool("FC_QWEN_TMUX_FALLBACK_SDK", default=True)
    cmd = tmux_current_command(sess)
    if cmd != "qwen":
        _launch_qwen_in_session(sess)
        time.sleep(1.6)
        cmd = tmux_current_command(sess)
        if cmd != "qwen":
            if fallback_sdk:
                return qwen_prompt_sdk(
                    prompt,
                    system_prompt=system_prompt,
                    max_wait=max_wait,
                    permission_mode=os.environ.get("FC_QWEN_SDK_PERMISSION_MODE", "default"),
                    model=os.environ.get("FC_QWEN_SDK_MODEL", ""),
                    debug=_env_bool("FC_QWEN_SDK_DEBUG", default=False),
                    path_to_qwen_executable=os.environ.get("FC_QWEN_SDK_CLI_PATH", ""),
                )
            _die(f"Qwen TUI n'est pas actif dans la session {sess} (pane_current_command={cmd or 'unknown'}).")

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
            results[label] = (reply or "").strip() or "(réponse vide)"
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


def qwen_prompt_sdk(
    prompt: str,
    *,
    system_prompt: str = "",
    max_wait: float = 60.0,
    permission_mode: str = "default",
    model: str = "",
    debug: bool = False,
    path_to_qwen_executable: str = "",
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


def qwen_ping_sdk(max_wait: float = 25.0, model: str = "", debug: bool = False, qwen_bin: str = "") -> str:
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
        if last_star_idx is not None:
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
        self._ensure_init()
        return self.session.ask(
            prompt,
            max_wait=self.max_wait,
            settle_seconds=1.8,
            poll_interval=0.55,
            min_wait=1.2,
        )


# ==============================================================================
# dev_tools (in-file)
# ==============================================================================

def _python_cmd() -> List[str]:
    if VENV_PY.exists():
        return [str(VENV_PY)]
    return ["python3"]


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

def _format_autogen_context(messages: List[Dict[str, Any]], max_msgs: int = 10) -> str:
    tail = messages[-max_msgs:] if len(messages) > max_msgs else messages
    parts: List[str] = []
    for m in tail:
        role = (m.get("name") or m.get("role") or "unknown").strip()
        content = (m.get("content") or "").strip()
        if not content:
            continue
        parts.append(f"[{role}]\n{content}\n")
    return "\n".join(parts).strip()


def run_feature_autogen_tmux(
    ctx: RunCtx,
    feature: str,
    max_rounds: int,
    wait_planner: float,
    wait_dev: float,
    wait_tester: float,
    wait_qa: float,
) -> str:
    autogen = require_module("autogen")  # strict

    planner_llm = QwenTmuxLLM(
        session_name=SESSIONS["planner"],
        system_prompt="Tu es PLANNER, architecte technique. Ultra concret et court.",
        max_wait=max(60.0, wait_planner),
    )
    dev_llm = QwenTmuxLLM(
        session_name=SESSIONS["dev"],
        system_prompt="Tu es DEV backend senior. Changements minimaux, testables. Donne des commandes.",
        max_wait=max(90.0, wait_dev),
    )
    tester_llm = QwenTmuxLLM(
        session_name=SESSIONS["tester"],
        system_prompt="Tu es TESTER/QA. Propose tests pytest concrets + cas limites. Précis sur imports.",
        max_wait=max(75.0, wait_tester),
    )
    qa_llm = QwenTmuxLLM(
        session_name=SESSIONS["qa"],
        system_prompt="Tu es QUALITY_OBSERVER. Rapport: ÉTAT GÉNÉRAL, TESTS, RISQUES, PRIORITÉS.",
        max_wait=max(90.0, wait_qa),
    )

    planner = autogen.ConversableAgent(
        name="Planner",
        system_message="PLANNER (AutoGen) — réponds en français.",
        llm_config=False,
        human_input_mode="NEVER",
    )
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

    planner._tmux_llm = planner_llm  # type: ignore[attr-defined]
    dev._tmux_llm = dev_llm          # type: ignore[attr-defined]
    tester._tmux_llm = tester_llm    # type: ignore[attr-defined]
    qa._tmux_llm = qa_llm            # type: ignore[attr-defined]

    def tmux_reply(recipient, messages, sender, config):
        ctx_text = _format_autogen_context(messages or [], max_msgs=10)
        if not ctx_text:
            ctx_text = feature.strip()

        prompt = dedent(f"""
        CONTEXTE (dernier échanges)
        --------------------------
        {ctx_text}

        RÈGLES
        ------
        - Ne recopie pas le prompt.
        - Réponds en français.
        - Réponse courte, structurée, actionnable.

        TA RÉPONSE
        ----------
        """).strip()

        transcript_append(ctx, recipient.name, "PROMPT", prompt)

        llm = getattr(recipient, "_tmux_llm", None)
        if llm is None:
            _die(f"Agent '{recipient.name}' n'a pas de _tmux_llm attaché.")
        reply = llm.chat(prompt)

        transcript_append(ctx, recipient.name, "RESPONSE", reply)
        return True, reply

    for ag in (planner, dev, tester, qa):
        ag.register_reply(
            trigger=[autogen.Agent, None],
            reply_func=tmux_reply,
            position=0,
        )

    # --------- FIX: calcul "tours" réellement exécutés ----------
    # On veut au minimum Planner->Dev->Tester (3 tours) par round,
    # et un peu de marge.
    max_turns = max(6, int(max_rounds) * 3)

    # Certaines versions utilisent max_round (et l'interprètent bizarrement).
    # On le met large pour ne pas couper prématurément.
    groupchat = autogen.GroupChat(
        agents=[planner, dev, tester],
        messages=[],
        max_round=max_turns,
        speaker_selection_method="round_robin",
        allow_repeat_speaker=False,
    )
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=False)

    transcript_append(ctx, "Runner", "INFO", f"AutoGen-tmux kickoff. max_rounds={max_rounds} max_turns={max_turns}")

    # --------- FIX: forcer le nombre de tours côté initiate_chat ----------
    try:
        planner.initiate_chat(manager, message=feature, max_turns=max_turns)
    except TypeError:
        # compat versions autogen: max_round au lieu de max_turns
        planner.initiate_chat(manager, message=feature, max_round=max_turns)

    transcript_append(ctx, "Runner", "INFO", "PHASE QA (autogen-tmux): pytest + git")

    pg = run_pytest_tool()
    pattern = infer_test_pattern(feature, default="health")
    pt = run_specific_tests_tool(pattern)
    status = git_status_tool()
    diff = git_diff_tool(max_lines=220)

    qa_prompt = dedent(f"""
    Contexte: Finance Copilot (FastAPI/Python).

    FEATURE
    -------
    {feature}

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
    """).strip()

    transcript_append(ctx, "QualityObserver", "PROMPT", qa_prompt)
    report = qa_llm.chat(qa_prompt)
    transcript_append(ctx, "QualityObserver", "RESPONSE", report)

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

    lines: List[str] = []
    lines.append(f"# Doctor report ({datetime.now().isoformat(timespec='seconds')})")
    lines.append("")
    lines.append(f"- PROJECT_DIR: {PROJECT_DIR} ({'OK' if PROJECT_DIR.exists() else 'MISSING'})")
    lines.append(f"- BACKEND_DIR: {BACKEND_DIR} ({'OK' if BACKEND_DIR.exists() else 'MISSING'})")
    lines.append(f"- autogen: {'OK' if autogen_ok else 'MISSING'}")
    if not autogen_ok:
        lines.append(f"  - detail: {autogen_detail}")
    lines.append(f"- tmux: {which('tmux')}")
    lines.append(f"- qwen: {qwen_bin}")
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
):
    ensure_project_exists()
    ensure_tmux_exists()
    require_module("autogen")
    qwen_bin = require_executable(qwen_bin)

    ctx = create_run_ctx(runs_dir)
    sentry_set_context(run_id=ctx.run_id, mode=mode, tmux_cmd="")
    sentry_add_breadcrumb(
        "feature_run_started",
        data={
            "run_id": ctx.run_id,
            "mode": mode,
            "rounds": max_rounds,
            "runs_dir": str(runs_dir),
        },
    )

    if mode == "debug":
        marker = create_marker(ctx.run_id)
        transcript_append(ctx, "Runner", "INFO", f"Marker pre-created: {marker}")
        feature = build_debug_feature(ctx.run_id)
        transcript_append(ctx, "Runner", "INFO", "Feature replaced by DEBUG feature.")

    write_manifest(ctx, feature=feature, qwen_bin=qwen_bin, extra={"mode": mode, "engine": "autogen_tmux"})

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

    2) Mode debug
       python3 scripts/qwen_orchestrator.py --mode debug --rounds 1 --restart

    3) Management tmux
       python3 scripts/qwen_orchestrator.py --tmux-cmd status
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
    - Pour run de feature: autogen/tmux/qwen doivent être présents sinon erreur.
    - Pour management tmux (status/start/stop/attach/ping/prompt): autogen n'est pas requis.
    - Tu peux ajouter des rôles custom via FC_EXTRA_SESSIONS ou --sessions:
      ex: security=qwen_security,docs=qwen_docs
    - tmux capture utilise history + join wrap (-J), et history-limit est augmenté.
    - Chaque exécution crée un run_dir:
        {RUNS_DIR_DEFAULT}/YYYYMMDD-HHMMSS-mmm/
          - run.json
          - transcript.md
          - tmux/*.log (si activé)
          - snapshots/*.txt
          - doctor_report.md (si doctor)
    """).strip()


# ==============================================================================
# Main
# ==============================================================================

def main():
    ensure_venv_or_reexec()

    ap = argparse.ArgumentParser(description="Finance Copilot orchestrator (AutoGen + tmux Qwen Code).", add_help=True)

    ap.add_argument("--feature", type=str, default=os.environ.get("FC_FEATURE", "").strip(),
                    help="Texte de la feature (sinon FC_FEATURE)")
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--restart", action="store_true", help="Kill+restart sessions tmux avant de run")

    ap.add_argument("--mode", type=str, default="normal", choices=["normal", "debug"],
                    help="normal: feature ; debug: smoke test marker + prompts déterministes")

    ap.add_argument("--runs-dir", type=str, default=str(RUNS_DIR_DEFAULT))
    ap.add_argument("--no-tmux-logs", action="store_true", help="Désactive pipe-pane tmux raw logs")
    ap.add_argument("--max-log-mb", type=int, default=25, help="Rotation pipe-pane si log > N MB")

    ap.add_argument("--no-clean-startup", action="store_true", help="Ne pas clear-history au démarrage des sessions tmux")

    ap.add_argument("--qwen-bin", type=str, default=(which("qwen") or "qwen"))

    ap.add_argument("--wait-planner", type=float, default=60.0)
    ap.add_argument("--wait-dev", type=float, default=90.0)
    ap.add_argument("--wait-tester", type=float, default=75.0)
    ap.add_argument("--wait-qa", type=float, default=90.0)

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
                    help="Commande: status|start|stop|restart|attach|doctor|cleanup|clear|ping|prompt")
    ap.add_argument("--tmux-target", type=str, default="",
                    help="Pour stop/attach/clear/ping/prompt: role (planner/dev/tester/qa/...) ou nom de session")
    ap.add_argument("--tmux-all", action="store_true", help="Pour stop: stop toutes les sessions")
    ap.add_argument("--keep-last", type=int, default=10, help="Pour cleanup: garder N derniers runs")

    ap.add_argument("--print-usage", action="store_true", help="Affiche une doc d'utilisation + exit")

    args = ap.parse_args()
    apply_session_overrides(args.sessions)
    tmux_cmd = (args.tmux_cmd or "").strip().lower()
    prompt_engine = (args.prompt_engine or "tmux").strip().lower()

    init_orchestrator_sentry()
    sentry_set_context(mode=args.mode, tmux_cmd=tmux_cmd or None)
    sentry_add_breadcrumb(
        "main_args_parsed",
        data={
            "mode": args.mode,
            "tmux_cmd": tmux_cmd or "(none)",
            "prompt_engine": prompt_engine,
            "runs_dir": args.runs_dir,
            "restart": bool(args.restart),
        },
    )

    if args.print_usage:
        print(usage_text())
        return

    ensure_project_exists()
    ensure_tmux_exists()

    runs_dir = Path(args.runs_dir).expanduser().resolve()

    if tmux_cmd:
        if tmux_cmd == "status":
            sentry_add_breadcrumb("tmux_status")
            print(qwen_status())
            return

        if tmux_cmd == "start":
            ctx = create_run_ctx(runs_dir)
            sentry_set_context(run_id=ctx.run_id, mode="start", tmux_cmd="start")
            sentry_add_breadcrumb("tmux_start", data={"run_id": ctx.run_id})
            write_manifest(ctx, feature="(start only)", qwen_bin=args.qwen_bin, extra={"mode": "start"})
            qwen_start(
                args.qwen_bin, DEFAULT_PATH_OVERRIDE, AUTO_CONFIRM,
                restart=False, ctx=ctx,
                enable_tmux_logs=not args.no_tmux_logs,
                clean_startup=not args.no_clean_startup,
            )
            print("✅ Qwen sessions started.")
            print(f"🧾 Run dir → {ctx.run_dir}")
            return

        if tmux_cmd == "restart":
            ctx = create_run_ctx(runs_dir)
            sentry_set_context(run_id=ctx.run_id, mode="restart", tmux_cmd="restart")
            sentry_add_breadcrumb("tmux_restart", data={"run_id": ctx.run_id})
            write_manifest(ctx, feature="(restart only)", qwen_bin=args.qwen_bin, extra={"mode": "restart"})
            qwen_restart(
                args.qwen_bin, DEFAULT_PATH_OVERRIDE, AUTO_CONFIRM,
                ctx=ctx,
                enable_tmux_logs=not args.no_tmux_logs,
                clean_startup=not args.no_clean_startup,
            )
            print("✅ Qwen sessions restarted.")
            print(f"🧾 Run dir → {ctx.run_dir}")
            return

        if tmux_cmd == "stop":
            if args.tmux_all or not args.tmux_target:
                sentry_add_breadcrumb("tmux_stop_all")
                qwen_stop(all_sessions=True)
                print("🛑 Qwen sessions stopped (all).")
                return
            sess = resolve_session(args.tmux_target)
            sentry_add_breadcrumb("tmux_stop_one", data={"session": sess})
            qwen_stop(all_sessions=False, session=sess)
            print(f"🛑 Qwen session stopped: {sess}")
            return

        if tmux_cmd == "attach":
            target = args.tmux_target or "dev"
            sentry_add_breadcrumb("tmux_attach", data={"target": target})
            sys.exit(qwen_attach(target))

        if tmux_cmd == "doctor":
            ctx = create_run_ctx(runs_dir)
            sentry_set_context(run_id=ctx.run_id, mode="doctor", tmux_cmd="doctor")
            sentry_add_breadcrumb("tmux_doctor", data={"run_id": ctx.run_id})
            write_manifest(ctx, feature="(doctor)", qwen_bin=args.qwen_bin, extra={"mode": "doctor"})
            doctor(ctx, qwen_bin=args.qwen_bin)
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
                label = target or "sdk"
                results = {
                    label: qwen_ping_sdk(
                        max_wait=25.0,
                        model=args.sdk_model,
                        debug=bool(args.sdk_debug),
                        qwen_bin=args.sdk_path_to_qwen_executable,
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
                reply = qwen_prompt_sdk(
                    args.prompt.strip(),
                    system_prompt=(args.system_prompt or "").strip(),
                    max_wait=max(args.wait_dev, 20.0),
                    permission_mode=args.sdk_permission_mode,
                    model=args.sdk_model,
                    debug=bool(args.sdk_debug),
                    path_to_qwen_executable=args.sdk_path_to_qwen_executable,
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

        _die(f"tmux-cmd inconnu: {tmux_cmd} (attendu: status|start|stop|restart|attach|doctor|cleanup|clear|ping|prompt)")

    feature = args.feature or "Implémente un endpoint GET /health avec test pytest"
    sentry_add_breadcrumb(
        "feature_entrypoint",
        data={"feature_preview": feature[:200], "rounds": args.rounds, "mode": args.mode},
    )

    ctx = run_feature(
        feature=feature,
        max_rounds=args.rounds,
        restart_tmux=args.restart,
        runs_dir=runs_dir,
        qwen_bin=args.qwen_bin,
        enable_tmux_logs=not args.no_tmux_logs,
        max_log_mb=args.max_log_mb,
        mode=args.mode,
        clean_startup=not args.no_clean_startup,
        wait_planner=args.wait_planner,
        wait_dev=args.wait_dev,
        wait_tester=args.wait_tester,
        wait_qa=args.wait_qa,
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
