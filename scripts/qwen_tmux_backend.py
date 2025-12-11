import subprocess
import time
import re
from typing import List, Dict, Optional, Any


class QwenTmuxSession:
    """
    Représente une session tmux qui tourne déjà avec `qwen`.
    On envoie du texte avec `tmux send-keys` et on lit la sortie avec `capture-pane`.
    """

    PROMPT_PATTERNS = [
        re.compile(r"Apply patch\?.*\[y/N\]", re.IGNORECASE),
        re.compile(r"Proceed\?.*\[y/N\]", re.IGNORECASE),
        re.compile(r"Allow.*command\?.*\[y/N\]", re.IGNORECASE),
    ]

    NOISE_PATTERNS = [
        "Qwen Code update available",
        "You are running Qwen Code in your home directory",
        "Type your message or @path/to/file",
        "no sandbox",
        "Ask questions, edit files, or run commands.",
        "Be specific for the best results.",
        "/help for more information.",
        "Installed via Homebrew. Please update with",
        "...~//analyse-financiere",
        "coder-model",
        "sandbox (",
    ]

    def __init__(self, session_name: str, wait_seconds: float = 12.0):
        self.session = session_name
        self.wait_seconds = wait_seconds
        self.last_snapshot = self._capture_full()

    def _capture_full(self) -> str:
        return subprocess.check_output(
            ["tmux", "capture-pane", "-pt", self.session],
            text=True,
        )

    def _get_new_output(self) -> str:
        current = self._capture_full()
        if current.startswith(self.last_snapshot):
            new = current[len(self.last_snapshot):]
        else:
            new = current  # désync, on renvoie tout
        self.last_snapshot = current
        return new.strip()

    def _send_raw(self, text: str) -> None:
        subprocess.check_call(["tmux", "send-keys", "-t", self.session, text, "C-m"])

    def _auto_confirm_if_needed(self, buffer: str, max_auto_confirms: int, confirms_done: int) -> int:
        """Détecte les prompts de confirmation et envoie 'y' si besoin."""
        if confirms_done >= max_auto_confirms:
            return confirms_done
        for pat in self.PROMPT_PATTERNS:
            if pat.search(buffer):
                self._send_raw("y")
                return confirms_done + 1
        return confirms_done

    def _clean_output(self, raw: str) -> str:
        """Nettoie la sortie brute de Qwen Code pour ne garder que la réponse utile."""
        if not raw:
            return ""

        # 1) Enlever toutes les séquences ANSI
        ansi_re = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
        text = ansi_re.sub("", raw)

        # 2) Normaliser les lignes
        lines = [line.rstrip() for line in text.splitlines()]
        cleaned: List[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            lower = stripped.lower()

            # UI générique Qwen / helper
            if "ask questions, edit files, or run commands." in stripped:
                continue
            if "be specific for the best results." in stripped:
                continue
            if "/help for more information." in stripped:
                continue
            if "installed via homebrew. please update with" in lower:
                continue
            if "using: 1 qwen.md file" in lower:
                continue
            if "auto-accept edits" in lower:
                continue
            if "waiting for user confirmation" in lower:
                continue
            if "allow execution of:" in lower:
                continue
            if "yes, allow once" in lower or "yes, allow always" in lower:
                continue
            if "no, suggest changes" in lower:
                continue

            # Spinners / “loading” jokes
            if stripped.startswith(("⠋", "⠙", "⠹", "⠸", "⠼", "⠧")):
                continue
            if "(esc to cancel" in lower:
                continue

            # Ligne d’état de la barre en bas (chemin, sandbox, coder-model, etc.)
            if "...//analyse-financiere" in stripped:
                continue
            if "coder-model" in lower and "sandbox" in lower:
                continue

            # Lignes de cadres / bordures (tmux / TUI)
            if re.match(r"^[\s┌┐└┘├┤─│╭╮╰╯…·]+$", stripped):
                continue

            # Autres bruits connus
            if any(pat.lower() in lower for pat in self.NOISE_PATTERNS):
                continue

            cleaned.append(stripped)

        if not cleaned:
            return ""

        # 3) Heuristique : garder le bloc après la dernière ligne qui commence par '✦'
        last_star_idx = None
        for i, line in enumerate(cleaned):
            if line.lstrip().startswith("✦"):
                last_star_idx = i

        if last_star_idx is not None:
            cleaned = cleaned[last_star_idx:]

        # 4) Sécurité : ne conserver que les 40 dernières lignes max
        if len(cleaned) > 40:
            cleaned = cleaned[-40:]

        return "\n".join(cleaned).strip()

    def ask(self, text: str, wait_seconds: Optional[float] = None) -> str:
        """Envoie un message, auto-confirme les prompts et retourne la sortie nettoyée."""
        if wait_seconds is None:
            wait_seconds = self.wait_seconds

        self._send_raw(text)

        deadline = time.time() + wait_seconds
        accumulated = ""
        auto_confirms = 0
        max_auto_confirms = 5

        while time.time() < deadline:
            time.sleep(0.8)
            new = self._get_new_output()
            if not new:
                continue
            accumulated += ("\n" + new)
            auto_confirms = self._auto_confirm_if_needed(
                accumulated,
                max_auto_confirms=max_auto_confirms,
                confirms_done=auto_confirms,
            )

        return self._clean_output(accumulated)


class QwenTmuxLLM:
    """
    Petit wrapper "LLM-like" au-dessus d'une session tmux Qwen.
    messages = [{"role": "system"|"user"|"assistant", "content": "..."}]
    """

    def __init__(
        self,
        session_name: str,
        system_prompt: str = "",
        wait_seconds: float = 12.0,
    ):
        self.session = QwenTmuxSession(session_name, wait_seconds=wait_seconds)
        self.system_prompt = system_prompt
        self._initialized = False

    def _ensure_initialized(self):
        if self._initialized:
            return
        if self.system_prompt:
            self.session.ask(
                f"[SYSTEM ROLE] {self.system_prompt}\n"
                f"Réponds toujours de façon claire. Ne répète pas ce message."
            )
        self._initialized = True

    def chat(self, messages: List[Dict[str, str]]) -> str:
        self._ensure_initialized()
        user_messages = [m for m in messages if m.get("role") == "user"]
        if not user_messages:
            raise ValueError("Pas de message user dans messages.")
        prompt = user_messages[-1]["content"]
        return self.session.ask(prompt)


def quick_test():
    llm = QwenTmuxLLM(
        "qwen_planner",
        system_prompt="Tu es un assistant technique qui répond en français.",
    )
    resp = llm.chat(
        [{"role": "user", "content": "Donne 3 idées de tests unitaires pour une fonction moyenne(x)."}]
    )
    print(resp)


if __name__ == "__main__":
    quick_test()
