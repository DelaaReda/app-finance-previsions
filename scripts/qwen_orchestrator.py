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
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import List, Dict, Any, Callable, Optional, Tuple

# ==============================================================================
# CONFIG
# ==============================================================================

PROJECT_DIR = Path("/Users/venom/Documents/analyse-financiere").resolve()
BACKEND_DIR = PROJECT_DIR / "copilot-app" / "backend"
BACKEND_SRC = BACKEND_DIR / "src"
VENV_BIN = BACKEND_DIR / ".venv" / "bin"
VENV_PY = VENV_BIN / "python3"

# Auto-confirm: toujours actif
AUTO_CONFIRM = True

SESSIONS = {
    "planner": "qwen_planner",
    "dev": "qwen_dev",
    "tester": "qwen_tester",
    # si tu veux une session dédiée: "qa": "qwen_qa"
    "qa": "qwen_tester",
}

RUNS_DIR_DEFAULT = PROJECT_DIR / "logs-qwen-runs"


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
# subprocess / tmux helpers
# ==============================================================================


def run(
    cmd: List[str],
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    check: bool = False,
    capture: bool = True,
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
        raise RuntimeError(f"PROJECT_DIR introuvable: {PROJECT_DIR}")


def ensure_tmux_exists() -> None:
    if which("tmux") is None:
        raise RuntimeError("tmux introuvable. Installe tmux (brew install tmux).")


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
    # CTRL+L
    tmux_start_server()
    target = tmux_target(session)
    run(["tmux", "send-keys", "-t", target, "C-l"], capture=False)

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
    block = f"\n## [{ts}] {role} — {kind}\n\n```\n{content.rstrip()}\n```\n"
    with ctx.transcript_path.open("a", encoding="utf-8") as f:
        f.write(block)


def snapshot_all(ctx: RunCtx) -> None:
    for sess in sorted(set(SESSIONS.values())):
        try:
            snap = tmux_capture(sess)
            (ctx.snapshots_dir / f"{sess}.txt").write_text(snap, encoding="utf-8")
        except Exception:
            pass

# ==============================================================================
# Logging (tmux raw) + rotation
# ==============================================================================


def rotate_if_too_big(session: str, log_file: Path, max_bytes: int) -> Path:
    try:
        if log_file.exists() and log_file.stat().st_size > max_bytes:
            ts = datetime.now().strftime("%H%M%S")
            new_file = log_file.parent / f"{session}_{ts}.log"
            tmux_pipe_pane(session, new_file, force_repipe=True)
            return new_file
    except Exception:
        pass
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

    # raw logs tmux -> ctx/tmux/<sess>.log
    if ctx and enable_tmux_logs:
        for sess in session_names():
            try:
                tmux_pipe_pane(sess, ctx.tmux_dir / f"{sess}.log", force_repipe=True)
            except Exception:
                pass


def qwen_stop(all_sessions: bool = True, session: Optional[str] = None) -> None:
    ensure_tmux_exists()
    tmux_start_server()

    if all_sessions:
        for sess in session_names():
            tmux_kill_session(sess)
        return

    if not session:
        raise ValueError("qwen_stop: session manquante quand all_sessions=False")
    tmux_kill_session(session)


def qwen_restart(qwen_bin: str, path_override: str, auto_confirm: bool, ctx: Optional[RunCtx], enable_tmux_logs: bool) -> None:
    qwen_start(qwen_bin=qwen_bin, path_override=path_override, auto_confirm=auto_confirm, restart=True, ctx=ctx, enable_tmux_logs=enable_tmux_logs)


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
    def _strip_ansi(s: str) -> str:
        ansi = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
        return ansi.sub("", s)

    def _clean_output(self, raw: str) -> str:
        if not raw:
            return ""
        text = self._strip_ansi(raw)

        noise_substrings = [
            "Ask questions, edit files, or run commands.",
            "Be specific for the best results.",
            "/help for more information.",
            "Installed via Homebrew. Please update with",
            "auto-accept edits",
            "Using: 1 QWEN.md file",
            "no sandbox",
            "coder-model",
            "...~//analyse-financiere",
            "(esc to cancel",
            "Mining for more",
            "Caching the essentials",
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
# GroupChat engine
# ==============================================================================


@dataclass
class ConversationMessage:
    round_index: int
    sender: str
    role_type: str
    content: str
    meta: Dict[str, Any] = field(default_factory=dict)


class RoleAgent:
    def __init__(
        self,
        name: str,
        role_type: str,
        session_name: str,
        system_prompt: str,
        wait_seconds: int,
        ctx: Optional[RunCtx] = None,
    ):
        self.name = name
        self.role_type = role_type
        self.session_name = session_name
        self.llm = QwenTmuxLLM(session_name=session_name, system_prompt=system_prompt, wait_seconds=wait_seconds)
        self.ctx = ctx

    def send(self, prompt: str) -> str:
        print(f"\n================= {self.name.upper()} – PROMPT =================\n{prompt}\n")
        if self.ctx:
            transcript_append(self.ctx, self.name, "PROMPT", prompt)

        reply = self.llm.chat(prompt)

        print(f"\n================= {self.name.upper()} – RÉPONSE =================\n{reply}\n")
        if self.ctx:
            transcript_append(self.ctx, self.name, "RESPONSE", reply)

        return reply


class GroupChatEngine:
    def __init__(self, agents: Dict[str, RoleAgent], max_rounds: int, history_chars: int = 6000):
        self.agents = agents
        self.max_rounds = max_rounds
        self.history_chars = history_chars
        self.history: List[ConversationMessage] = []

    def add(self, r: int, agent: RoleAgent, content: str):
        self.history.append(ConversationMessage(r, agent.name, agent.role_type, content or ""))

    def history_text(self) -> str:
        parts: List[str] = []
        for m in self.history:
            parts.append(f"[round {m.round_index}][{m.sender}]")
            parts.append(m.content)
            parts.append("")
        full = "\n".join(parts).strip()
        if len(full) <= self.history_chars:
            return full
        return "(Historique tronqué)\n...\n" + full[-self.history_chars:]

    def run(self, feature: str, round_callback: Optional[Callable[[int], None]] = None):
        for r in range(1, self.max_rounds + 1):
            print(f"\n==================== ROUND {r} ====================\n")

            planner = self.agents["planner"]
            dev = self.agents["dev"]
            tester = self.agents["tester"]

            planner_prompt = build_planner_prompt(feature, r, self.history_text())
            planner_reply = planner.send(planner_prompt)
            self.add(r, planner, planner_reply)

            dev_prompt = build_dev_prompt(feature, r, self.history_text())
            dev_reply = dev.send(dev_prompt)
            self.add(r, dev, dev_reply)

            tester_prompt = build_tester_prompt(feature, r, self.history_text())
            tester_reply = tester.send(tester_prompt)
            self.add(r, tester, tester_reply)

            if round_callback:
                round_callback(r)

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
# Debug/smoke mode: marker file
# ==============================================================================


def debug_marker_paths(run_id: str) -> Dict[str, Path]:
    """
    Choix d'un emplacement stable, pas dans src/:
    - backend/.qwen_runs/<run_id>/marker.txt
    """
    base = BACKEND_DIR / ".qwen_runs" / run_id
    return {
        "dir": base,
        "marker": base / "marker.txt",
    }


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
    - Valider rapidement l'orchestrateur Qwen(tmux) + logs/transcript.
    - On veut une action simple, traçable, qui ne dépend pas du backend.

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
# Doctor / cleanup
# ==============================================================================


def doctor(ctx: RunCtx, qwen_bin: str) -> None:
    lines: List[str] = []
    lines.append(f"# Doctor report ({datetime.now().isoformat(timespec='seconds')})")
    lines.append("")
    lines.append(f"- PROJECT_DIR: {PROJECT_DIR} ({'OK' if PROJECT_DIR.exists() else 'MISSING'})")
    lines.append(f"- BACKEND_DIR: {BACKEND_DIR} ({'OK' if BACKEND_DIR.exists() else 'MISSING'})")
    lines.append(f"- tmux: {which('tmux') or 'MISSING'}")
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
    """
    Supprime les anciens runs, garde les N derniers.
    """
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
    history_chars: int,
    mode: str,
):
    # run context
    ctx = create_run_ctx(runs_dir)
    write_manifest(ctx, feature=feature, qwen_bin=qwen_bin, extra={"mode": mode})

    # start sessions + raw logs
    qwen_start(
        qwen_bin=qwen_bin,
        path_override=DEFAULT_PATH_OVERRIDE,
        auto_confirm=AUTO_CONFIRM,
        restart=restart_tmux,
        ctx=ctx,
        enable_tmux_logs=enable_tmux_logs,
    )

    # always snapshot at start (baseline)
    snapshot_all(ctx)

    # if debug mode -> create marker first (optional but useful)
    if mode == "debug":
        marker = create_marker(ctx.run_id)
        transcript_append(ctx, "Runner", "INFO", f"Marker pre-created: {marker}")

        # replace the feature with a deterministic debug feature
        feature = build_debug_feature(ctx.run_id)
        transcript_append(ctx, "Runner", "INFO", "Feature replaced by DEBUG feature.")

    print(f"🧾 Run dir → {ctx.run_dir}")
    print(f"   transcript: {ctx.transcript_path}")
    if enable_tmux_logs:
        print(f"   tmux logs:  {ctx.tmux_dir}")

    planner_sys = dedent("""
    Tu es PLANNER, architecte technique.
    Tu dois être ultra concret et court.
    """).strip()

    dev_sys = dedent("""
    Tu es DEV backend senior.
    Si tu ne sais pas où modifier, commence par explorer le repo (rg/ls/cat).
    Donne toujours au moins 1 action concrète.
    """).strip()

    tester_sys = dedent("""
    Tu es TESTER/QA.
    Tu dois être précis sur les chemins et les imports pytest.
    """).strip()

    qa_sys = dedent("""
    Tu es QUALITY_OBSERVER.
    Tu produis un rapport QA structuré: ÉTAT GÉNÉRAL, TESTS, RISQUES, PRIORITÉS.
    """).strip()

    agents = {
        "planner": RoleAgent("Planner", "planner", SESSIONS["planner"], planner_sys, wait_seconds=12, ctx=ctx),
        "dev": RoleAgent("Dev", "dev", SESSIONS["dev"], dev_sys, wait_seconds=22, ctx=ctx),
        "tester": RoleAgent("Tester", "tester", SESSIONS["tester"], tester_sys, wait_seconds=16, ctx=ctx),
    }
    qa_agent = RoleAgent("QualityObserver", "qa", SESSIONS["qa"], qa_sys, wait_seconds=14, ctx=ctx)

    engine = GroupChatEngine(agents=agents, max_rounds=max_rounds, history_chars=history_chars)

    def after_round(r: int):
        # rotate tmux logs
        if enable_tmux_logs:
            max_bytes = max_log_mb * 1024 * 1024
            for sess in session_names():
                lf = ctx.tmux_dir / f"{sess}.log"
                rotate_if_too_big(sess, lf, max_bytes)

        snapshot_all(ctx)
        transcript_append(ctx, "Runner", "INFO", f"Fin du round {r}")

    engine.run(feature=feature, round_callback=after_round)

    # QA phase: optional in debug mode (tu peux quand même la garder)
    transcript_append(ctx, "Runner", "INFO", "PHASE QA automatisée: pytest + git")

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

    HISTORIQUE
    ---------
    {engine.history_text()}

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

    report = qa_agent.send(qa_prompt)
    print("\n================= RAPPORT QA FINAL =================\n")
    print(report)

    snapshot_all(ctx)
    return ctx

# ==============================================================================
# CLI docs (help text)
# ==============================================================================


def usage_text() -> str:
    return dedent(f"""
    Utilisation rapide
    ==================

    1) Lancer une feature (mode normal)
       python3 scripts/qwen_orchestrator.py --feature "Implémente GET /health" --rounds 2

    2) Mode debug (smoke test ultra simple + marker)
       python3 scripts/qwen_orchestrator.py --mode debug --rounds 1

    3) Management tmux/qwen
       python3 scripts/qwen_orchestrator.py --tmux-cmd status
       python3 scripts/qwen_orchestrator.py --tmux-cmd start
       python3 scripts/qwen_orchestrator.py --tmux-cmd restart
       python3 scripts/qwen_orchestrator.py --tmux-cmd stop --tmux-all
       python3 scripts/qwen_orchestrator.py --tmux-cmd attach --tmux-target dev

    4) Doctor (diagnostic + snapshots)
       python3 scripts/qwen_orchestrator.py --tmux-cmd doctor

    5) Nettoyer les anciens runs (garde les 10 derniers)
       python3 scripts/qwen_orchestrator.py --tmux-cmd cleanup --keep-last 10

    Notes
    -----
    - auto-confirm est TOUJOURS actif (QWEN_CODE_AUTO_CONFIRM=1 + règles confirm).
    - Les logs tmux (pipe-pane) sont "raw" (bruyants). Le fichier transcript.md est "clean".
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
    ap = argparse.ArgumentParser(description="Finance Copilot Qwen(tmux) orchestrator + management.", add_help=True)
    ap.add_argument("--feature", type=str, default=os.environ.get("FC_FEATURE", "").strip(),
                    help="Texte de la feature (sinon FC_FEATURE)")
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--restart", action="store_true", help="Kill+restart sessions tmux avant de run")

    # run behavior
    ap.add_argument("--mode", type=str, default="normal", choices=["normal", "debug"],
                    help="normal: feature; debug: smoke test marker + prompts déterministes")

    # run dirs / logs
    ap.add_argument("--runs-dir", type=str, default=str(RUNS_DIR_DEFAULT))
    ap.add_argument("--no-tmux-logs", action="store_true", help="Désactive pipe-pane tmux raw logs")
    ap.add_argument("--max-log-mb", type=int, default=25, help="Rotation pipe-pane si log > N MB")
    ap.add_argument("--history-chars", type=int, default=6000, help="Contexte max envoyé aux agents")

    # qwen/tmux
    ap.add_argument("--qwen-bin", type=str, default=(which("qwen") or "qwen"))

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
    runs_dir = Path(args.runs_dir).resolve()

    # ---- management mode
    if tmux_cmd:
        try:
            if tmux_cmd == "status":
                print(qwen_status())
                return

            if tmux_cmd == "start":
                ctx = create_run_ctx(runs_dir)
                write_manifest(ctx, feature="(start only)", qwen_bin=args.qwen_bin, extra={"mode": "start"})
                qwen_start(args.qwen_bin, DEFAULT_PATH_OVERRIDE, AUTO_CONFIRM, restart=False,
                           ctx=ctx, enable_tmux_logs=not args.no_tmux_logs)
                print("✅ Qwen sessions started.")
                print(f"🧾 Run dir → {ctx.run_dir}")
                return

            if tmux_cmd == "restart":
                ctx = create_run_ctx(runs_dir)
                write_manifest(ctx, feature="(restart only)", qwen_bin=args.qwen_bin, extra={"mode": "restart"})
                qwen_restart(args.qwen_bin, DEFAULT_PATH_OVERRIDE, AUTO_CONFIRM, ctx=ctx,
                             enable_tmux_logs=not args.no_tmux_logs)
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
                print(f"✅ Clear screen envoyé à: {sess}")
                return

            print(f"❌ tmux-cmd inconnu: {tmux_cmd}")
            print("   Attendu: status|start|stop|restart|attach|doctor|cleanup|clear")
            sys.exit(2)

        except Exception as e:
            print(f"❌ Erreur management tmux: {e}")
            sys.exit(1)

    # ---- default: run feature
    feature = args.feature or "Implémente un endpoint GET /health avec test pytest"

    ctx = run_feature(
        feature=feature,
        max_rounds=args.rounds,
        restart_tmux=args.restart,
        runs_dir=runs_dir,
        qwen_bin=args.qwen_bin,
        enable_tmux_logs=not args.no_tmux_logs,
        max_log_mb=args.max_log_mb,
        history_chars=args.history_chars,
        mode=args.mode,
    )

    print(f"\n✅ Terminé. Run dir: {ctx.run_dir}")
    print(f"   transcript: {ctx.transcript_path}")
    print(f"   manifest:   {ctx.manifest_path}")
    print(f"   snapshots:  {ctx.snapshots_dir}")
    if not args.no_tmux_logs:
        print(f"   tmux logs:  {ctx.tmux_dir}")


if __name__ == "__main__":
    main()