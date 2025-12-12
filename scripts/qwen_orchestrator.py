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
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import List, Dict, Any, Optional, Tuple


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

SESSIONS: Dict[str, str] = {
    "planner": os.environ.get("FC_SESS_PLANNER", "qwen_planner"),
    "dev": os.environ.get("FC_SESS_DEV", "qwen_dev"),
    "tester": os.environ.get("FC_SESS_TESTER", "qwen_tester"),
    "qa": os.environ.get("FC_SESS_QA", "qwen_qa"),
}

RUNS_DIR_DEFAULT = Path(os.environ.get("FC_RUNS_DIR", str(PROJECT_DIR / "logs-qwen-runs"))).expanduser().resolve()


def now_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


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


# ==============================================================================
# Strict requirements (NO fallback)
# ==============================================================================

def _die(msg: str, code: int = 1) -> None:
    raise RuntimeError(msg)


def ensure_venv_or_reexec() -> None:
    """
    Si la venv backend existe mais que l'environnement courant n'est pas la venv,
    on relance le script via VENV_PY. On ne se contente pas de comparer sys.executable
    (souvent un symlink vers l'interpréteur système) : on vérifie sys.prefix/base_prefix.
    """
    if not VENV_PY.exists():
        return

    venv_root = VENV_BIN.parent.resolve()
    in_venv = Path(sys.prefix).resolve() == venv_root and getattr(sys, "base_prefix", None) != sys.prefix
    if in_venv:
        return

    # Re-exec dans la venv pour garantir les deps (autogen, etc.)
    os.execv(str(VENV_PY), [str(VENV_PY), *sys.argv])


def require_module(name: str) -> Any:
    try:
        return __import__(name)
    except Exception as e:
        _die(f"Module requis introuvable: '{name}'. Installe-le puis relance. Détail: {e}")


def require_bin(bin_name: str) -> str:
    p = which(bin_name)
    if not p:
        _die(f"Binaire requis introuvable: '{bin_name}'. Installe-le (ex: brew install {bin_name}).")
    return p


# ==============================================================================
# subprocess / tmux helpers
# ==============================================================================

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


def ensure_project_exists() -> None:
    if not PROJECT_DIR.exists():
        _die(f"PROJECT_DIR introuvable: {PROJECT_DIR}")
    if not BACKEND_DIR.exists():
        _die(f"BACKEND_DIR introuvable: {BACKEND_DIR}")


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


def tmux_list_sessions() -> List[str]:
    tmux_start_server()
    cp = run(["tmux", "list-sessions", "-F", "#{session_name}"], capture=True)
    if cp.returncode != 0:
        return []
    return [ln.strip() for ln in (cp.stdout or "").splitlines() if ln.strip()]


def tmux_attach(session: str) -> int:
    tmux_start_server()
    cp = run(["tmux", "attach", "-t", session], capture=False, check=False)
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


def tmux_capture(session: str) -> str:
    tmux_start_server()
    target = tmux_target(session)
    cp = run(["tmux", "capture-pane", "-p", "-t", target], capture=True)
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


def create_run_ctx(runs_dir: Path) -> RunCtx:
    run_id = now_id()
    run_dir = runs_dir / run_id
    tmux_dir = run_dir / "tmux"
    snapshots_dir = run_dir / "snapshots"
    run_dir.mkdir(parents=True, exist_ok=True)
    tmux_dir.mkdir(parents=True, exist_ok=True)
    snapshots_dir.mkdir(parents=True, exist_ok=True)

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
        "backend_dir": str(BACKEND_DIR),
        "qwen_bin": qwen_bin,
        "sessions": {k: v for k, v in SESSIONS.items()},
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
        snap = tmux_capture(sess)
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


def build_qwen_bash_cmd(qwen_bin: str, path_override: str, auto_confirm: bool) -> str:
    setup_cmds = [f'cd "{str(PROJECT_DIR)}"']

    venv_activate = VENV_BIN / "activate"
    if venv_activate.exists():
        setup_cmds.append(f'source "{str(venv_activate)}"')

    setup_cmds.append(f'export PATH="{path_override}"')

    if auto_confirm:
        setup_cmds.append('export QWEN_CODE_AUTO_CONFIRM=1')

    setup_cmds.append(f'{qwen_bin} || exec bash')
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

    if restart:
        qwen_stop(all_sessions=True)

    bash_cmd = build_qwen_bash_cmd(qwen_bin=qwen_bin, path_override=path_override, auto_confirm=auto_confirm)

    for sess in session_names():
        if tmux_has_session(sess):
            continue
        tmux_new_session(sess, bash_cmd)

        if clean_startup:
            time.sleep(0.2)
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
    lines.append("Qwen tmux sessions:")
    for sess in session_names():
        lines.append(f"  - {sess}: {'UP' if sess in existing else 'DOWN'}")
    return "\n".join(lines)


def qwen_attach(role_or_session: str) -> int:
    ensure_tmux_exists()
    tmux_start_server()
    sess = SESSIONS.get(role_or_session, role_or_session)
    return tmux_attach(sess)


# ==============================================================================
# Qwen tmux backend (chat)
# ==============================================================================

class QwenTmuxSession:
    CONFIRM_RULES: List[Tuple[re.Pattern, str]] = [
        (re.compile(r"apply\s+patch\?.*(\[\s*y\s*/\s*n\s*\]|\[y/N\]|\(y/n\))", re.IGNORECASE), "y"),
        (re.compile(r"proceed\?.*(\[\s*y\s*/\s*n\s*\]|\[y/N\]|\(y/n\))", re.IGNORECASE), "y"),
        (re.compile(r"allow execution of:", re.IGNORECASE), "1"),
        (re.compile(r"waiting for user confirmation", re.IGNORECASE), "1"),
    ]

    def __init__(self, session_name: str, wait_seconds: float = 12.0):
        self.session = session_name
        self.wait_seconds = wait_seconds
        self.last_snapshot = tmux_capture(self.session)

    def _get_new_output(self) -> str:
        cur = tmux_capture(self.session)
        if cur.startswith(self.last_snapshot):
            new = cur[len(self.last_snapshot):]
        else:
            new = cur
        self.last_snapshot = cur
        return (new or "").strip()

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
        s = re.sub(r"\x1b\][^\x1b]*\x1b\\", "", s)      # OSC ... ST
        s = re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]", "", s)   # CSI
        s = re.sub(r"\x1B[@-Z\\-_]", "", s)             # other ESC
        s = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", s)  # C0 except \n \t
        return s

    def _clean_output(self, raw: str) -> str:
        if not raw:
            return ""
        text = self._strip_terminal_noise(raw)

        noise_substrings = [
            "Ask questions, edit files, or run commands.",
            "Be specific for the best results.",
            "/help for more information.",
            "Installed via Homebrew. Please update with",
            "auto-accept edits",
            "Using: 1 QWEN.md file",
            "Using:",
            "no sandbox",
            "coder-model",
            "(esc to cancel",
            "Mining for more",
            "Caching the essentials",
            "Initializing...",
        ]

        cleaned: List[str] = []
        for line in text.splitlines():
            s = line.rstrip()
            if not s.strip():
                continue
            low = s.strip().lower()

            if s.strip().startswith(("⠋", "⠙", "⠹", "⠸", "⠼", "⠧", "⠏", "⠴", "⠦")):
                continue
            if re.match(r"^[\s┌┐└┘├┤─│╭╮╰╯…·]+$", s.strip()):
                continue
            if any(ns.lower() in low for ns in noise_substrings):
                continue

            cleaned.append(s.strip())

        last_star = None
        for i, ln in enumerate(cleaned):
            if ln.lstrip().startswith("✦"):
                last_star = i
        if last_star is not None:
            cleaned = cleaned[last_star:]

        if len(cleaned) > 80:
            cleaned = cleaned[-80:]

        out = "\n".join(cleaned).strip()
        if not out:
            fallback = [ln.strip() for ln in text.splitlines() if ln.strip()]
            return "\n".join(fallback[-80:]).strip()
        return out

    def ask(self, text: str, wait_seconds: Optional[float] = None) -> str:
        if wait_seconds is None:
            wait_seconds = self.wait_seconds

        self._send(text)

        deadline = time.time() + wait_seconds
        buf = ""
        confirms = 0

        while time.time() < deadline:
            time.sleep(0.8)
            new = self._get_new_output()
            if not new:
                continue
            buf += "\n" + new
            confirms = self._auto_confirm(buf, max_confirms=6, confirms_done=confirms)

        return self._clean_output(buf)


class QwenTmuxLLM:
    def __init__(self, session_name: str, system_prompt: str = "", wait_seconds: float = 12.0):
        self.session = QwenTmuxSession(session_name, wait_seconds=wait_seconds)
        self.system_prompt = system_prompt.strip()
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
                "- Donne des étapes concrètes.\n"
                "- Si tu es bloqué, dis exactement quoi vérifier.\n"
            )
        self._init_done = True

    def chat(self, prompt: str) -> str:
        self._ensure_init()
        return self.session.ask(prompt)


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

def build_planner_prompt(feature: str, r: int, history: str) -> str:
    base = dedent(f"""
    Tu es PLANNER (round {r}) sur le backend Finance Copilot (FastAPI).

    FEATURE:
    {feature}
    """).strip()

    if r == 1:
        base += "\n\n" + dedent("""
        Ta mission:
        - Proposer un plan en 5–10 étapes max, concret.
        - Indiquer les fichiers probables.
        - Mentionner 1–3 risques.

        Format:

        PLAN
        1) ...
        ...

        FICHIERS
        - ...

        RISQUES
        - ...
        """).strip()
    else:
        base += "\n\n" + dedent(f"""
        CONTEXTE (résumé historique):
        {history}

        Ta mission:
        - Ajuster le plan pour CE round seulement.
        - Corriger les dérives si Dev/Test n’avancent pas.
        """).strip()

    return base


def build_dev_prompt(feature: str, r: int, history: str) -> str:
    return dedent(f"""
    Tu es DEV (round {r}) dans Finance Copilot (FastAPI/Python).

    FEATURE:
    {feature}

    HISTORIQUE:
    {history}

    Contraintes:
    - Fais des changements minimaux, orientés "feature + test".
    - Indique les chemins de fichiers à modifier.
    - Donne des commandes à exécuter.
    - Si tu dois explorer le repo: propose 2–4 commandes max (rg/ls/cat).

    Format:

    RÉSUMÉ
    - ...

    MODIFS
    - fichier: ...
      ```python
      ...
      ```

    COMMANDES
    - ...
    """).strip()


def build_tester_prompt(feature: str, r: int, history: str) -> str:
    return dedent(f"""
    Tu es TESTER/QA (round {r}).

    FEATURE:
    {feature}

    HISTORIQUE:
    {history}

    Ta mission:
    - Proposer des tests pytest concrets (nom de fichier + fonctions).
    - Inclure 2–3 cas limites.
    - Dire exactement quoi faire si les imports cassent (PYTHONPATH, conftest, etc.).

    Format:

    TESTS
    - tests/xxx.py:
      - test_...

    CAS LIMITES
    - ...

    RISQUES
    - ...
    """).strip()


def infer_test_pattern(feature: str, default: str = "health") -> str:
    m = re.search(r"/([a-zA-Z0-9_]+)", feature)
    return m.group(1) if m else default


# ==============================================================================
# AutoGen classic -> tmux driver (ONLY solution)
# ==============================================================================

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
        wait_seconds=wait_planner,
    )
    dev_llm = QwenTmuxLLM(
        session_name=SESSIONS["dev"],
        system_prompt="Tu es DEV backend senior. Changements minimaux, testables. Donne des commandes.",
        wait_seconds=wait_dev,
    )
    tester_llm = QwenTmuxLLM(
        session_name=SESSIONS["tester"],
        system_prompt="Tu es TESTER/QA. Propose tests pytest concrets + cas limites. Précis sur imports.",
        wait_seconds=wait_tester,
    )
    qa_llm = QwenTmuxLLM(
        session_name=SESSIONS["qa"],
        system_prompt="Tu es QUALITY_OBSERVER. Rapport: ÉTAT GÉNÉRAL, TESTS, RISQUES, PRIORITÉS.",
        wait_seconds=wait_qa,
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

    # Bind tmux LLM
    planner._tmux_llm = planner_llm  # type: ignore[attr-defined]
    dev._tmux_llm = dev_llm          # type: ignore[attr-defined]
    tester._tmux_llm = tester_llm    # type: ignore[attr-defined]
    qa._tmux_llm = qa_llm            # type: ignore[attr-defined]

    def tmux_reply(recipient, messages, sender, config):
        last = ""
        if messages:
            last = (messages[-1].get("content") or "").strip()
        if not last:
            last = "(message vide) — répond quand même avec un next step concret."

        transcript_append(ctx, recipient.name, "PROMPT", last)

        llm = getattr(recipient, "_tmux_llm", None)
        if llm is None:
            _die(f"Agent '{recipient.name}' n'a pas de _tmux_llm attaché.")
        reply = llm.chat(last)

        transcript_append(ctx, recipient.name, "RESPONSE", reply)
        return True, reply

    for ag in (planner, dev, tester, qa):
        ag.register_reply(
            trigger=[autogen.Agent, None],
            reply_func=tmux_reply,
            position=0,
        )

    max_turns = max(3, max_rounds * 3)
    groupchat = autogen.GroupChat(
        agents=[planner, dev, tester],
        messages=[],
        max_round=max_turns,
        speaker_selection_method="round_robin",
        allow_repeat_speaker=False,
    )
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=False)

    transcript_append(ctx, "Runner", "INFO", f"AutoGen-tmux kickoff. max_turns={max_turns}")
    planner.initiate_chat(manager, message=feature)

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
    require_module("autogen")  # strict
    require_bin("tmux")
    require_bin(qwen_bin if os.path.sep in qwen_bin else "qwen")

    lines: List[str] = []
    lines.append(f"# Doctor report ({datetime.now().isoformat(timespec='seconds')})")
    lines.append("")
    lines.append(f"- PROJECT_DIR: {PROJECT_DIR} ({'OK' if PROJECT_DIR.exists() else 'MISSING'})")
    lines.append(f"- BACKEND_DIR: {BACKEND_DIR} ({'OK' if BACKEND_DIR.exists() else 'MISSING'})")
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
            for sub in d.rglob("*"):
                if sub.is_file():
                    sub.unlink()
            for sub in sorted([p for p in d.rglob("*") if p.is_dir()], reverse=True):
                try:
                    sub.rmdir()
                except Exception:
                    pass
            d.rmdir()
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
    # strict requirements: crash early
    ensure_project_exists()
    ensure_tmux_exists()
    require_module("autogen")
    require_bin("qwen") if (qwen_bin == "qwen") else None

    ctx = create_run_ctx(runs_dir)

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
# CLI docs (help text)
# ==============================================================================

def usage_text() -> str:
    return dedent(f"""
    Utilisation rapide
    ==================

    1) AutoGen -> TMUX (solution unique)
       python3 scripts/qwen_orchestrator.py --rounds 2 --feature "Implémente GET /health"

    2) Mode debug
       python3 scripts/qwen_orchestrator.py --mode debug --rounds 1

    3) Management tmux
       python3 scripts/qwen_orchestrator.py --tmux-cmd status
       python3 scripts/qwen_orchestrator.py --tmux-cmd start
       python3 scripts/qwen_orchestrator.py --tmux-cmd restart
       python3 scripts/qwen_orchestrator.py --tmux-cmd stop --tmux-all
       python3 scripts/qwen_orchestrator.py --tmux-cmd attach --tmux-target dev

    Notes
    -----
    - Aucun fallback: autogen/tmux/qwen doivent être présents sinon erreur.
    - Chaque exécution crée un run_dir:
        {RUNS_DIR_DEFAULT}/YYYYMMDD-HHMMSS/
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
    # Strict import at startup (so missing module fails early even before parsing)
    require_module("autogen")

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

    ap.add_argument("--wait-planner", type=float, default=12.0)
    ap.add_argument("--wait-dev", type=float, default=22.0)
    ap.add_argument("--wait-tester", type=float, default=16.0)
    ap.add_argument("--wait-qa", type=float, default=18.0)

    # management commands
    ap.add_argument("--tmux-cmd", type=str, default="",
                    help="Commande: status|start|stop|restart|attach|doctor|cleanup|clear")
    ap.add_argument("--tmux-target", type=str, default="",
                    help="Pour stop/attach/clear: role planner|dev|tester|qa ou nom de session")
    ap.add_argument("--tmux-all", action="store_true", help="Pour stop: stop toutes les sessions")
    ap.add_argument("--keep-last", type=int, default=10, help="Pour cleanup: garder N derniers runs")

    ap.add_argument("--print-usage", action="store_true", help="Affiche une doc d'utilisation + exit")

    args = ap.parse_args()

    if args.print_usage:
        print(usage_text())
        return

    ensure_project_exists()
    ensure_tmux_exists()

    tmux_cmd = (args.tmux_cmd or "").strip().lower()
    runs_dir = Path(args.runs_dir).expanduser().resolve()

    if tmux_cmd:
        if tmux_cmd == "status":
            print(qwen_status())
            return

        if tmux_cmd == "start":
            ctx = create_run_ctx(runs_dir)
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
                qwen_stop(all_sessions=True)
                print("🛑 Qwen sessions stopped (all).")
                return
            sess = SESSIONS.get(args.tmux_target, args.tmux_target)
            qwen_stop(all_sessions=False, session=sess)
            print(f"🛑 Qwen session stopped: {sess}")
            return

        if tmux_cmd == "attach":
            target = args.tmux_target or "dev"
            sys.exit(qwen_attach(target))

        if tmux_cmd == "doctor":
            ctx = create_run_ctx(runs_dir)
            write_manifest(ctx, feature="(doctor)", qwen_bin=args.qwen_bin, extra={"mode": "doctor"})
            doctor(ctx, qwen_bin=args.qwen_bin)
            print(f"✅ Doctor report écrit: {ctx.run_dir / 'doctor_report.md'}")
            print(f"🧾 Snapshots: {ctx.snapshots_dir}")
            return

        if tmux_cmd == "cleanup":
            n = cleanup_runs(runs_dir, keep_last=args.keep_last)
            print(f"✅ Cleanup terminé. Runs supprimés: {n}. (gardés: {args.keep_last})")
            return

        if tmux_cmd == "clear":
            target = args.tmux_target or "dev"
            sess = SESSIONS.get(target, target)
            tmux_clear_screen(sess)
            tmux_clear_history(sess)
            print(f"✅ Clear screen + history envoyé à: {sess}")
            return

        _die(f"tmux-cmd inconnu: {tmux_cmd} (attendu: status|start|stop|restart|attach|doctor|cleanup|clear)")

    feature = args.feature or "Implémente un endpoint GET /health avec test pytest"

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
    main()
