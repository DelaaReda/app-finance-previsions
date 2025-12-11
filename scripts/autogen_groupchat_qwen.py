#!/usr/bin/env python
import os
from dataclasses import dataclass, field
from textwrap import dedent
from typing import List, Dict, Any, Callable, Optional

from scripts.qwen_tmux_backend import QwenTmuxLLM
from scripts.dev_tools import (
    run_pytest_tool,
    run_specific_tests_tool,
    git_status_tool,
    git_diff_tool,
)

PROJECT_DIR = "/Users/venom/Documents/analyse-financiere"


# ------------------------------------------------------------------------------
# 1. Modèle de message & agent
# ------------------------------------------------------------------------------

@dataclass
class ConversationMessage:
    round_index: int
    sender: str          # "Planner", "Dev", "Tester", "QA"
    role_type: str       # "planner" | "dev" | "tester" | "qa"
    content: str
    meta: Dict[str, Any] = field(default_factory=dict)


class RoleAgent:
    """
    Agent relié à une session tmux Qwen Code.
    Qwen garde le contexte dans la session, nous on gère juste l'orchestration.
    """

    def __init__(
        self,
        name: str,
        role_type: str,
        session_name: str,
        system_prompt: str,
        wait_seconds: int = 15,
    ):
        self.name = name
        self.role_type = role_type
        self.session_name = session_name
        self.llm = QwenTmuxLLM(
            session_name=session_name,
            system_prompt=system_prompt,
            wait_seconds=wait_seconds,
        )

    def send(self, prompt: str) -> str:
        print(f"\n================= {self.name.upper()} – PROMPT =================\n")
        print(prompt)
        print("\n============================================================\n")

        reply = self.llm.chat(
            [
                {
                    "role": "user",
                    "content": prompt,
                }
            ]
        )

        print(f"\n================= {self.name.upper()} – RÉPONSE =================\n")
        print(reply)
        print("\n============================================================\n")

        return reply


# ------------------------------------------------------------------------------
# 2. Moteur de GroupChat générique
# ------------------------------------------------------------------------------

class GroupChatEngine:
    """
    Petit moteur de group chat maison :
    - connaît les rôles,
    - stocke l'historique,
    - gère les rondes,
    - applique une fonction de stop.
    """

    def __init__(
        self,
        agents: Dict[str, RoleAgent],      # { "planner": RoleAgent, ... }
        max_rounds: int = 3,
        stop_condition: Optional[Callable[[List[ConversationMessage]], bool]] = None,
    ):
        self.agents = agents
        self.max_rounds = max_rounds
        self.stop_condition = stop_condition
        self.history: List[ConversationMessage] = []

    def add_message(
        self,
        round_index: int,
        sender: RoleAgent,
        content: str,
        meta: Dict[str, Any] | None = None,
    ):
        self.history.append(
            ConversationMessage(
                round_index=round_index,
                sender=sender.name,
                role_type=sender.role_type,
                content=content,
                meta=meta or {},
            )
        )

    def get_history_text(self) -> str:
        """
        Résumé textuel simple de l'historique.
        Utile si tu veux fournir du contexte à un agent.
        """
        lines = []
        for msg in self.history:
            lines.append(f"[round {msg.round_index}][{msg.sender}]")
            lines.append(msg.content)
            lines.append("")  # ligne vide
        return "\n".join(lines).strip()

    def run_rounds(
        self,
        feature_text: str,
        round_callback: Optional[Callable[["GroupChatEngine", int], None]] = None,
    ):
        """
        Boucle principale : exécute jusqu'à max_rounds, ou jusqu'à ce que stop_condition soit vraie.

        round_callback(self, round_index) te permet d'injecter de la logique custom par round
        (ex: lancer pytest après chaque Dev, etc.).
        """
        for r in range(1, self.max_rounds + 1):
            print(f"\n==================== ROUND {r} ====================\n")

            # 1. Planner
            planner = self.agents.get("planner")
            if planner:
                planner_prompt = self._build_planner_prompt(feature_text, round_index=r)
                planner_reply = planner.send(planner_prompt)
                self.add_message(r, planner, planner_reply)

            # 2. Dev
            dev = self.agents.get("dev")
            if dev:
                dev_prompt = self._build_dev_prompt(feature_text, round_index=r)
                dev_reply = dev.send(dev_prompt)
                self.add_message(r, dev, dev_reply)

            # 3. Tester
            tester = self.agents.get("tester")
            if tester:
                tester_prompt = self._build_tester_prompt(feature_text, round_index=r)
                tester_reply = tester.send(tester_prompt)
                self.add_message(r, tester, tester_reply)

            # callback custom par round (ex: mini-QA intermédiaire)
            if round_callback:
                round_callback(self, r)

            # stop condition globale
            if self.stop_condition and self.stop_condition(self.history):
                print("\n>>> Stop condition atteinte, arrêt des rounds.\n")
                break

    # --------- Prompts standards (tu peux les override dans un subclass) ---------

    def _build_planner_prompt(self, feature_text: str, round_index: int) -> str:
        history_summary = self.get_history_text() if round_index > 1 else ""
        base = dedent(f"""
            Tu es PLANNER (round {round_index}) dans une équipe d'agents qui travaillent
            sur le projet Finance Copilot (backend FastAPI, jobs, services, RAG, etc.).

            Feature à implémenter / améliorer :

            {feature_text}
        """).strip()

        if history_summary:
            base += dedent(f"""

                CONTEXTE DES ROUNDS PRÉCÉDENTS
                --------------------------------
                {history_summary}

                Ta mission :
                - Mettre à jour le plan en fonction de ce qui a déjà été fait / discuté,
                - Proposer des tâches réalistes pour ce round uniquement,
                - Ne pas réécrire tout à zéro, mais affiner.
            """).strip()
        else:
            base += dedent("""

                Ta mission :
                - Proposer un plan de tâches numéroté,
                - Indiquer les fichiers principaux impactés,
                - Mentionner 1–3 risques techniques.

                Forme attendue :

                PLAN
                1. ...
                2. ...

                FICHIERS
                - ...

                RISQUES
                - ...
            """).strip()

        return base

    def _build_dev_prompt(self, feature_text: str, round_index: int) -> str:
        history_summary = self.get_history_text()
        return dedent(f"""
            Tu es DEV (round {round_index}), développeur backend senior dans le projet Finance Copilot.

            FEATURE
            -------
            {feature_text}

            HISTORIQUE
            ----------
            {history_summary}

            Ta mission pour ce round :
            - Implémenter des changements concrets, ciblés, cohérents avec le plan du PLANNER,
            - Indiquer les fichiers précis à modifier (chemins),
            - Fournir des extraits de code précis,
            - Proposer des commandes à exécuter (pytest -k ..., etc.),
            - Rester raisonnable : amélioration incrémentale, pas de refactor massif.

            Réponds avec :

            RÉSUMÉ
            - ...

            MODIFS PROPOSÉES
            - fichier: ...
              ```python
              ...
              ```

            COMMANDES SUGGÉRÉES
            - pytest ...
            - ...
        """).strip()

    def _build_tester_prompt(self, feature_text: str, round_index: int) -> str:
        history_summary = self.get_history_text()
        return dedent(f"""
            Tu es TESTER / QA (round {round_index}).

            FEATURE
            -------
            {feature_text}

            HISTORIQUE
            ----------
            {history_summary}

            Ta mission :
            - Proposer des tests pytest concrets (fichiers + fonctions de test),
            - Couvrir les cas principaux + 2–3 cas limites,
            - Signaler les risques et dettes de tests.

            Forme attendue :

            TESTS PYTEST
            - tests/....py
              - test_xxx: ...

            CAS LIMITES
            - ...

            RISQUES
            - ...
        """).strip()


# ------------------------------------------------------------------------------
# 3. Implémentation spécifique Finance Copilot : QA finale + stop condition
# ------------------------------------------------------------------------------

def stop_condition_basic(history: List[ConversationMessage]) -> bool:
    """
    Exemple simple : on regarde si QA a déjà conclu "prêt pour merge" dans un message.
    (Tu pourras raffiner ça plus tard.)
    """
    for msg in history:
        if msg.role_type == "qa" and "prêt pour un merge" in msg.content.lower():
            return True
    return False


def run_finance_copilot_groupchat(feature_text: str, max_rounds: int = 2):
    # --- Définition des rôles (prompts systèmes) ---

    planner_sys = dedent("""
        Tu es PLANNER, architecte technique pour Finance Copilot.
        Tu penses en termes de petits incréments et tu aides Dev à ne pas partir dans tous les sens.
        Tu réponds toujours en français, de façon structurée.
    """).strip()

    dev_sys = dedent("""
        Tu es DEV, développeur backend Finance Copilot.
        Tu écris du code FastAPI / Python / pytest, en modifiant seulement ce qui est nécessaire.
        Tu évites de casser la structure existante. Tu réponds en français, avec du code précis.
    """).strip()

    tester_sys = dedent("""
        Tu es TESTER / QA technique.
        Tu proposes des tests pytest concrets et signales les trous de couverture.
        Tu réponds en français, sous forme de checklist + explications.
    """).strip()

    qa_sys = dedent("""
        Tu es QUALITY_OBSERVER.
        Tu reçois les résultats pytest, git status et git diff.
        Tu rédiges un rapport QA structuré (ÉTAT GÉNÉRAL, TESTS, RISQUES, PRIORITÉS).
        Tu réponds en français.
    """).strip()

    planner = RoleAgent(
        name="Planner",
        role_type="planner",
        session_name="qwen_planner",
        system_prompt=planner_sys,
        wait_seconds=15,
    )

    dev = RoleAgent(
        name="Dev",
        role_type="dev",
        session_name="qwen_dev",
        system_prompt=dev_sys,
        wait_seconds=25,
    )

    tester = RoleAgent(
        name="Tester",
        role_type="tester",
        session_name="qwen_tester",
        system_prompt=tester_sys,
        wait_seconds=20,
    )

    qa = RoleAgent(
        name="QualityObserver",
        role_type="qa",
        session_name="qwen_tester",  # tu peux créer une session "qwen_qa" si tu veux
        system_prompt=qa_sys,
        wait_seconds=20,
    )

    engine = GroupChatEngine(
        agents={
            "planner": planner,
            "dev": dev,
            "tester": tester,
        },
        max_rounds=max_rounds,
        stop_condition=None,  # on pourrait brancher stop_condition_basic plus tard
    )

    # --- Rounds Planner/Dev/Tester ---

    def round_callback(engine: GroupChatEngine, round_index: int):
        # Ici tu pourrais déjà lancer un mini-pytest à chaque round si tu veux.
        print(f"\n>>> Fin du round {round_index} (callback custom possible ici)\n")

    engine.run_rounds(feature_text=feature_text, round_callback=round_callback)

    # --- Phase QA finale : pytest + git + rapport QA ---

    print("\n================= PHASE QA AUTOMATISÉE =================\n")

    print(">> Lancement pytest global...")
    pytest_global = run_pytest_tool()

    print("\n>> Lancement pytest ciblé (pattern 'health')...")
    pytest_health = run_specific_tests_tool("health")

    print("\n>> Récupération git status / diff...")
    status = git_status_tool()
    diff = git_diff_tool(max_lines=220)

    history_text = engine.get_history_text()

    qa_prompt = dedent(f"""
        Contexte : projet Finance Copilot (FastAPI, Python, pytest).

        FEATURE
        -------
        {feature_text}

        HISTORIQUE DISCUSSION (Planner / Dev / Tester)
        ----------------------------------------------
        {history_text}

        === PYTEST GLOBAL ===
        {pytest_global['output']}

        === PYTEST CIBLÉ (pattern 'health') ===
        {pytest_health['output']}

        === GIT STATUS ===
        {status or '(aucun changement détecté)'}

        === GIT DIFF (tronqué) ===
        {diff or '(diff vide)'}

        Ta mission :
        - Faire un rapport QA structuré (ÉTAT GÉNÉRAL, TESTS, RISQUES, PRIORITÉS),
        - Dire si la feature semble raisonnablement prête pour un merge (en supposant revue humaine),
        - Proposer les 3 prochaines priorités techniques.
    """).strip()

    qa_report = qa.send(qa_prompt)

    print("\n================= RAPPORT FINAL QUALITY_OBSERVER =================\n")
    print(qa_report)
    print("\n============================================================\n")


# ------------------------------------------------------------------------------
# 4. Entrée principale
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    default_feature = (
        "Ajouter un endpoint GET /health sur l'API FastAPI principale "
        "qui retourne un JSON {\"status\": \"ok\", \"version\": \"1.0.0\"}, "
        "documenté dans la doc OpenAPI, avec au moins un test pytest."
    )

    feature = os.environ.get("FC_FEATURE", default_feature)

    os.chdir(PROJECT_DIR)
    run_finance_copilot_groupchat(feature_text=feature, max_rounds=2)