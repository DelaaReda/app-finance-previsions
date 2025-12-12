#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import time
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

SESSIONS = {
    "planner": "qwen_planner",
    "dev": "qwen_dev",
    "tester": "qwen_tester",
    "qa": "qwen_tester",  # tu peux créer qwen_qa si tu veux
}

def build_default_path_override() -> str:
    parts = []
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
# Helpers: subprocess / tmux (robuste + silencieux)
# ==============================================================================

def run(
    cmd: List[str],
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    check: bool = False,
    capture: bool = True,
) -> subprocess.CompletedProcess:
    """
    capture=True  -> stdout+stderr capturés dans stdout
    capture=False -> stdout+stderr envoyés à DEVNULL (silencieux)
    """
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

def tmux_start_server() -> None:
    # Important: évite "no server running on ..."
    run(["tmux", "start-server"], capture=False)

def tmux_target(session: str) -> str:
    # On utilise toujours la première fenêtre/pane
    return f"{session}.0"

def tmux_has_session(name: str) -> bool:
    try:
        tmux_start_server()
        cp = run(["tmux", "has-session", "-t", name], capture=False)
        return cp.returncode == 0
    except FileNotFoundError:
        raise RuntimeError("tmux introuvable. Installe tmux (brew install tmux).")

def tmux_kill_session(name: str) -> None:
    tmux_start_server()
    if tmux_has_session(name):
        run(["tmux", "kill-session", "-t", name], capture=False)

def tmux_new_session(name: str, bash_cmd: str) -> None:
    """
    Crée une session tmux détachée et lance:
      bash -lc "<bash_cmd>"
    Sans quotes imbriquées foireuses.
    """
    tmux_start_server()
    run(
        ["tmux", "new-session", "-d", "-s", name, "bash", "-lc", bash_cmd],
        capture=False,
        check=True,
    )

def tmux_pipe_pane(session: str, log_file: Path, force_repipe: bool = False) -> None:
    """
    Active le logging live de la pane session.0 vers log_file.
    -o : only if not already piped
    Si force_repipe=True -> on coupe et on rebranche vers le nouveau fichier.
    """
    tmux_start_server()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    target = tmux_target(session)

    if force_repipe:
        tmux_unpipe_pane(session)

    # cat >> "file"
    cmd = f"cat >> {shlex.quote(str(log_file))}"
    run(["tmux", "pipe-pane", "-o", "-t", target, cmd], capture=False)

def tmux_unpipe_pane(session: str) -> None:
    tmux_start_server()
    target = tmux_target(session)
    # Toggle off si un pipe existe (best effort, silencieux)
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

# ==============================================================================
# Logging + rotation
# ==============================================================================

@dataclass
class RunLogs:
    run_dir: Path
    files: Dict[str, Path]  # session_name -> file

def create_run_logs(base_dir: Path) -> RunLogs:
    run_dir = base_dir / datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    files: Dict[str, Path] = {}
    for sess in set(SESSIONS.values()):
        files[sess] = run_dir / f"{sess}.log"
    return RunLogs(run_dir=run_dir, files=files)

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
# Ensure sessions (100% Python)
# ==============================================================================

def ensure_qwen_sessions(
    restart: bool,
    logs: Optional[RunLogs],
    qwen_bin: str,
    path_override: str,
    auto_confirm: bool,
) -> None:
    """
    Démarre qwen dans les sessions tmux.
    Si logs != None : pipe-pane vers des fichiers (et re-pipe à chaque run pour viser le bon dossier).
    """
    tmux_start_server()

    if restart:
        for sess in set(SESSIONS.values()):
            tmux_kill_session(sess)

    # Crée/assure sessions
    for sess in set(SESSIONS.values()):
        if tmux_has_session(sess):
            continue

        setup_cmds = [f'cd "{str(PROJECT_DIR)}"']

        venv_activate = VENV_BIN / "activate"
        if venv_activate.exists():
            setup_cmds.append(f'source "{str(venv_activate)}"')

        setup_cmds.append(f'export PATH="{path_override}"')
        if auto_confirm:
            setup_cmds.append('export QWEN_CODE_AUTO_CONFIRM=1')

        setup_cmds.append(f'{qwen_bin} || exec bash')

        bash_cmd = " && ".join(setup_cmds)
        tmux_new_session(sess, bash_cmd)

    # Logging live via pipe-pane (toujours viser le run_dir courant)
    if logs:
        for sess, f in logs.files.items():
            try:
                tmux_pipe_pane(sess, f, force_repipe=True)
            except Exception:
                pass

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

        if len(cleaned) > 60:
            cleaned = cleaned[-60:]

        out = "\n".join(cleaned).strip()
        if not out:
            fallback = [ln.strip() for ln in text.splitlines() if ln.strip()]
            return "\n".join(fallback[-60:]).strip()
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
    def __init__(self, name: str, role_type: str, session_name: str, system_prompt: str, wait_seconds: int):
        self.name = name
        self.role_type = role_type
        self.session_name = session_name
        self.llm = QwenTmuxLLM(session_name=session_name, system_prompt=system_prompt, wait_seconds=wait_seconds)

    def send(self, prompt: str) -> str:
        print(f"\n================= {self.name.upper()} – PROMPT =================\n{prompt}\n")
        reply = self.llm.chat(prompt)
        print(f"\n================= {self.name.upper()} – RÉPONSE =================\n{reply}\n")
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
# Main runner
# ==============================================================================

def run_feature(
    feature: str,
    max_rounds: int,
    restart_tmux: bool,
    enable_logs: bool,
    logs_dir: Path,
    qwen_bin: str,
    max_log_mb: int,
    history_chars: int,
    auto_confirm: bool,
):
    logs = create_run_logs(logs_dir) if enable_logs else None

    ensure_qwen_sessions(
        restart=restart_tmux,
        logs=logs,
        qwen_bin=qwen_bin,
        path_override=DEFAULT_PATH_OVERRIDE,
        auto_confirm=auto_confirm,
    )

    if logs:
        print(f"🧾 Logs live → {logs.run_dir}")
        print(f"   Ex: tail -f {logs.run_dir}/{SESSIONS['dev']}.log")

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
        "planner": RoleAgent("Planner", "planner", SESSIONS["planner"], planner_sys, wait_seconds=12),
        "dev": RoleAgent("Dev", "dev", SESSIONS["dev"], dev_sys, wait_seconds=22),
        "tester": RoleAgent("Tester", "tester", SESSIONS["tester"], tester_sys, wait_seconds=16),
    }
    qa_agent = RoleAgent("QualityObserver", "qa", SESSIONS["qa"], qa_sys, wait_seconds=14)

    engine = GroupChatEngine(agents=agents, max_rounds=max_rounds, history_chars=history_chars)

    def after_round(r: int):
        if logs:
            max_bytes = max_log_mb * 1024 * 1024
            for sess, lf in list(logs.files.items()):
                logs.files[sess] = rotate_if_too_big(sess, lf, max_bytes)
        print(f"\n>>> Fin du round {r}\n")

    engine.run(feature=feature, round_callback=after_round)

    print("\n================= PHASE QA AUTOMATISÉE =================\n")
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

    if logs:
        print(f"\n🧾 Logs run: {logs.run_dir}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feature", type=str, default=os.environ.get("FC_FEATURE", "").strip(),
                    help="Texte de la feature (sinon FC_FEATURE)")
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--restart", action="store_true", help="Kill+restart sessions tmux avant de run")
    ap.add_argument("--no-logs", action="store_true")
    ap.add_argument("--logs-dir", type=str, default=str(PROJECT_DIR / "logs"))
    ap.add_argument("--qwen-bin", type=str, default=(which("qwen") or "qwen"))
    ap.add_argument("--max-log-mb", type=int, default=25, help="Rotation pipe-pane si log > N MB")
    ap.add_argument("--history-chars", type=int, default=6000, help="Contexte max envoyé aux agents")
    ap.add_argument("--auto-confirm", action="store_true",
                    help="Tente d'auto-répondre aux prompts (y/1) quand Qwen attend une confirmation")

    args = ap.parse_args()

    feature = args.feature or 'Implémente un endpoint GET /health avec test pytest'

    if not PROJECT_DIR.exists():
        print(f"❌ PROJECT_DIR introuvable: {PROJECT_DIR}")
        sys.exit(1)

    if which("tmux") is None:
        print("❌ tmux introuvable. Installe tmux (brew install tmux).")
        sys.exit(1)

    enable_logs = not args.no_logs
    run_feature(
        feature=feature,
        max_rounds=args.rounds,
        restart_tmux=args.restart,
        enable_logs=enable_logs,
        logs_dir=Path(args.logs_dir).resolve(),
        qwen_bin=args.qwen_bin,
        max_log_mb=args.max_log_mb,
        history_chars=args.history_chars,
        auto_confirm=args.auto_confirm,
    )

if __name__ == "__main__":
    main()