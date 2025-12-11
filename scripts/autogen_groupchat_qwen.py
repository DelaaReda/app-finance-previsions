#!/usr/bin/env python
import os
from types import SimpleNamespace

from autogen import ConversableAgent, GroupChat, GroupChatManager, UserProxyAgent

# Import backend Qwen -> tmux (tu l'as déjà dans ton repo)
from scripts.qwen_tmux_backend import QwenTmuxLLM

# Import des outils read-only (déjà présents)
from scripts.dev_tools import (
    run_pytest_tool,
    run_specific_tests_tool,
    git_status_tool,
    git_diff_tool,
)


PROJECT_DIR = "/Users/venom/Documents/analyse-financiere"


# ------------------------------------------------------------------------------
# 1. Bridge AutoGen -> Qwen Code en tmux
# ------------------------------------------------------------------------------

class QwenTmuxModelClient:
    """
    Client minimal pour AutoGen qui envoie les messages au QwenTmuxLLM
    (donc à Qwen Code qui tourne dans tmux).
    """

    def __init__(self, config, **kwargs):
        if isinstance(config, dict) and "config_list" in config:
            cfg = config["config_list"][0]
        else:
            cfg = config or {}

        self.session_name = cfg.get("session_name", "qwen_dev")
        self.wait_seconds = cfg.get("wait_seconds", 10)
        self.system_prompt = cfg.get("system_prompt", "")

        self.qwen = QwenTmuxLLM(
            session_name=self.session_name,
            system_prompt=self.system_prompt,
            wait_seconds=self.wait_seconds,
        )

    def create(self, params):
        """
        AutoGen appelle create(...) avec une liste de messages au format OpenAI.
        On compacte tout dans un prompt texte qu'on envoie à Qwen Code.
        """
        messages = params.get("messages", [])

        prompt_lines = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            prompt_lines.append(f"{role.upper()}:\n{content}\n")

        prompt = "\n".join(prompt_lines).strip()

        reply_text = self.qwen.chat(
            [
                {
                    "role": "user",
                    "content": prompt,
                }
            ]
        )

        msg = SimpleNamespace()
        msg.content = reply_text
        msg.function_call = None

        choice = SimpleNamespace()
        choice.message = msg

        resp = SimpleNamespace()
        resp.choices = [choice]
        resp.model = "qwen-tmux"

        return resp

    def message_retrieval(self, response):
        return [c.message.content for c in response.choices]

    def cost(self, response) -> float:
        return 0.0

    @staticmethod
    def get_usage(response):
        return {}


def make_llm_config(session_name: str, system_prompt: str, wait_seconds: int = 10):
    """
    Configuration LLM pour AutoGen, qui utilise notre QwenTmuxModelClient
    plutôt qu'un modèle OpenAI classique.
    """
    return {
        "config_list": [
            {
                "model": "qwen-tmux",
                "model_client_cls": "QwenTmuxModelClient",
                "session_name": session_name,
                "system_prompt": system_prompt,
                "wait_seconds": wait_seconds,
            }
        ],
        "cache_seed": None,
    }


# ------------------------------------------------------------------------------
# 2. Agents : Planner / Dev / Tester / QualityObserver + UserProxy
# ------------------------------------------------------------------------------

def build_agents(feature_text: str):
    planner_sys = (
        "Tu es PLANNER, architecte technique senior.\n"
        "Tu transformes une feature en plan de tâches clair, numéroté, réaliste, "
        "adapté au projet Finance Copilot (FastAPI backend, jobs, services, RAG, etc.).\n"
        "Toujours en français, structuré. À la fin, adresse un message explicite au Dev."
    )

    dev_sys = (
        "Tu es DEV, développeur backend senior qui travaille DANS le repo Finance Copilot.\n"
        "- Tu peux exécuter des commandes shell via Qwen Code.\n"
        "- Tu fais des changements ciblés, étape par étape.\n"
        "- Tu expliques brièvement ce que tu fais, mais tu privilégies le code.\n"
        "- Tu n'exécutes pas de commandes destructrices (rm -rf, drop DB, etc.).\n"
        "Réponds en français."
    )

    tester_sys = (
        "Tu es TESTER / QA.\n"
        "- Tu ne modifies pas directement le code.\n"
        "- Tu proposes des tests pytest, des cas limites, et critiques le travail de DEV.\n"
        "- Tu peux demander explicitement à DEV d'exécuter des commandes (pytest, etc.).\n"
        "Réponds en français et termine par une recommandation claire."
    )

    quality_sys = (
        "Tu es QUALITY_OBSERVER.\n"
        "On te fournit :\n"
        "- les résultats de pytest (global et ciblé),\n"
        "- le git status,\n"
        "- un diff tronqué.\n\n"
        "Ton rôle :\n"
        "- Résumer l'état de santé de la feature implémentée (succès / échecs tests),\n"
        "- Signaler les risques majeurs (tests manquants, warnings, code fragile),\n"
        "- Proposer des priorités pour le prochain cycle de travail.\n\n"
        "Tu ne donnes pas de patchs détaillés, tu restes au niveau QA/risques.\n"
        "Réponds en français, sous forme de rapport structuré."
    )

    planner_llm = make_llm_config(
        session_name="qwen_planner",
        system_prompt=planner_sys,
        wait_seconds=12,
    )
    dev_llm = make_llm_config(
        session_name="qwen_dev",
        system_prompt=dev_sys,
        wait_seconds=20,
    )
    tester_llm = make_llm_config(
        session_name="qwen_tester",
        system_prompt=tester_sys,
        wait_seconds=15,
    )
    quality_llm = make_llm_config(
        session_name="qwen_tester",  # on peut réutiliser la session tester pour QA
        system_prompt=quality_sys,
        wait_seconds=12,
    )

    planner = ConversableAgent(
        name="Planner",
        system_message=planner_sys,
        llm_config=planner_llm,
        human_input_mode="NEVER",
    )

    dev = ConversableAgent(
        name="Dev",
        system_message=dev_sys,
        llm_config=dev_llm,
        human_input_mode="NEVER",
    )

    tester = ConversableAgent(
        name="Tester",
        system_message=tester_sys,
        llm_config=tester_llm,
        human_input_mode="NEVER",
    )

    quality_observer = ConversableAgent(
        name="QualityObserver",
        system_message=quality_sys,
        llm_config=quality_llm,
        human_input_mode="NEVER",
    )

    user_proxy = UserProxyAgent(
        name="Reda",
        human_input_mode="NEVER",
        code_execution_config=False,
    )

    planner.description = "Découpe les features en plan technique détaillé."
    dev.description = "Implémente les changements dans le code du backend."
    tester.description = "Propose/critique les tests et la qualité."
    quality_observer.description = "Analyse pytest/git diff/status et produit un rapport QA."

    # 🔗 Activer le client custom QwenTmuxModelClient sur chaque agent
    for agent in (planner, dev, tester, quality_observer):
        agent.register_model_client(model_client_cls=QwenTmuxModelClient)

    return user_proxy, planner, dev, tester, quality_observer


# ------------------------------------------------------------------------------
# 3. GroupChat principal + phase QA automatique
# ------------------------------------------------------------------------------

def run_groupchat_for_feature(feature_text: str, max_rounds: int = 10):
    user_proxy, planner, dev, tester, quality_observer = build_agents(feature_text)

    groupchat = GroupChat(
        agents=[planner, dev, tester],
        messages=[],
        max_round=max_rounds,
        send_introductions=True,
    )

    chat_manager = GroupChatManager(
        groupchat=groupchat,
        llm_config=None,
    )

    result = user_proxy.initiate_chat(
        chat_manager,
        message=(
            "Feature à implémenter dans le backend Finance Copilot :\n"
            f"{feature_text}\n\n"
            "Planner : commence par proposer un plan structuré.\n"
            "Dev : implémente progressivement, en petites étapes.\n"
            "Tester : critique et renforce la qualité.\n"
            "Arrêtez quand vous estimez que la feature est globalement en place."
        ),
        summary_method="reflection_with_llm",
    )

    print("\n================= RÉSUMÉ FINAL (GroupChat Autogen) =================\n")
    try:
        print(result.summary)
    except Exception:
        print("(Pas de résumé disponible, mais le chat a bien tourné.)")

    # ---------- Phase QA automatique ----------
    print("\n================= PHASE QA AUTOMATISÉE =================\n")

    print(">> Lancement pytest global...")
    pytest_global = run_pytest_tool()

    print(">> Lancement pytest ciblé (pattern 'health')...")
    pytest_health = run_specific_tests_tool("health")

    print(">> Récupération git status / diff...")
    status = git_status_tool()
    diff = git_diff_tool(max_lines=220)

    qa_message = (
        "Voici les éléments de QA collectés automatiquement après le travail de l'équipe :\n\n"
        "=== PYTEST GLOBAL ===\n"
        f"{pytest_global['output']}\n\n"
        "=== PYTEST CIBLÉ (pattern 'health') ===\n"
        f"{pytest_health['output']}\n\n"
        "=== GIT STATUS ===\n"
        f"{status or '(aucun changement détecté)'}\n\n"
        "=== GIT DIFF (tronqué) ===\n"
        f"{diff or '(diff vide)'}\n\n"
        "Produis un rapport QA structuré, en te basant uniquement sur ces informations."
    )

    qa_result = quality_observer.initiate_chat(
        user_proxy,
        message=qa_message,
    )

    print("\n================= RAPPORT QUALITY_OBSERVER =================\n")
    try:
        last_msg = qa_result.chat_history[-1]["content"]
        print(last_msg)
    except Exception:
        print("(Impossible de récupérer le message QA, mais la conversation a eu lieu.)")


if __name__ == "__main__":
    default_feature = (
        "Ajouter un endpoint GET /health sur l'API FastAPI principale "
        "qui retourne un JSON {\"status\": \"ok\", \"version\": \"1.0.0\"}, "
        "documenté dans la doc OpenAPI, avec au moins un test pytest."
    )

    feature = os.environ.get("FC_FEATURE", default_feature)
    os.chdir(PROJECT_DIR)
    run_groupchat_for_feature(feature_text=feature, max_rounds=8)
