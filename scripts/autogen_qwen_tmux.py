"""
Mini orchestrateur AutoGen-like basé sur Qwen dans tmux.
Requiert:
- tmux avec sessions qwen_planner, qwen_dev, qwen_tester (lancer via scripts/start_qwen_tmux.sh)
- pyautogen installé (optionnel, ce script marche en mode "manuel" sans GroupChat)
"""
from typing import Any, Dict, List

try:
    from autogen import ConversableAgent
except Exception:  # pragma: no cover
    ConversableAgent = None

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT))

from qwen_tmux_backend import QwenTmuxLLM  # noqa: E402


class QwenTmuxAgent(ConversableAgent):
    """ConversableAgent qui parle à une session tmux Qwen."""

    def __init__(
        self,
        name: str,
        session_name: str,
        system_message: str,
        wait_seconds: float = 3.0,
        **kwargs: Any,
    ):
        if ConversableAgent is None:
            raise RuntimeError("pyautogen n'est pas installé. pip install pyautogen")
        super().__init__(
            name=name,
            system_message=system_message,
            llm_config=False,  # on bypass l'OpenAI client; on utilise QwenTmuxLLM
            **kwargs,
        )
        self.qwen_llm = QwenTmuxLLM(
            session_name=session_name,
            system_prompt=system_message,
            wait_seconds=wait_seconds,
        )

    def generate_reply(
        self,
        messages: List[Dict[str, Any]],
        sender: "ConversableAgent",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        text = self.qwen_llm.chat(messages)
        return {
            "role": "assistant",
            "content": text,
        }


def build_agents():
    planner = QwenTmuxAgent(
        name="planner",
        session_name="qwen_planner",
        system_message=(
            "Tu es PLANNER. Tu découpes les demandes de features en tâches techniques claires, "
            "numérotées, détaillées. Réponds en français."
        ),
        wait_seconds=12.0,
    )
    dev = QwenTmuxAgent(
        name="dev",
        session_name="qwen_dev",
        system_message=(
            "Tu es DEV. Tu écris du code et expliques les changements fichier par fichier. "
            "Réponds en français avec des extraits précis."
        ),
        wait_seconds=12.0,
    )
    tester = QwenTmuxAgent(
        name="tester",
        session_name="qwen_tester",
        system_message=(
            "Tu es TESTER. Tu raisonnes comme un QA, tu proposes des tests (unitaires/intégration) "
            "et signales les risques. Réponds en français."
        ),
        wait_seconds=12.0,
    )
    return planner, dev, tester


def simple_workflow():
    feature = (
        "Ajouter un endpoint /health sur une API FastAPI qui retourne un JSON "
        "status='ok' et version='1.0.0'."
    )
    print("=== Feature demandée ===")
    print(feature)
    print()

    planner, dev, tester = build_agents()

    planner_msg = planner.generate_reply(
        messages=[{"role": "user", "content": f"Feature : {feature}\nPlan détaillé demandé."}],
        sender=planner,
    )
    print("=== Planner ===")
    print(planner_msg["content"])
    print()

    dev_msg = dev.generate_reply(
        messages=[
            {
                "role": "user",
                "content": (
                    "Plan fourni :\n"
                    f"{planner_msg['content']}\n\n"
                    "Commence à implémenter la première étape et explique les fichiers impactés."
                ),
            }
        ],
        sender=dev,
    )
    print("=== Dev ===")
    print(dev_msg["content"])
    print()

    tester_msg = tester.generate_reply(
        messages=[
            {
                "role": "user",
                "content": (
                    "Voici le travail du dev :\n"
                    f"{dev_msg['content']}\n\n"
                    "Propose des tests concrets (pytest) et les risques éventuels."
                ),
            }
        ],
        sender=tester,
    )
    print("=== Tester ===")
    print(tester_msg["content"])
    print()
    print("=== Fin du workflow simple ===")


if __name__ == "__main__":
    if ConversableAgent is None:
        print("pyautogen non installé. Installe: pip install pyautogen")
        sys.exit(1)
    simple_workflow()
