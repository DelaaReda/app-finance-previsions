from __future__ import annotations

from typing import Optional

from langchain.chat_models.base import BaseChatModel
from langchain_community.chat_models import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from pydantic import SecretStr

from ..config import AgentConfig
from .g4f_chat import G4FChat


def get_llm(task: str, cfg: Optional[AgentConfig] = None) -> BaseChatModel:
    cfg = cfg or AgentConfig()
    if cfg.provider == "openai":
        return ChatOpenAI(
            model=cfg.model,
            api_key=SecretStr(cfg.openai_api_key) if cfg.openai_api_key else None,
            base_url=cfg.openai_base_url or None,
            temperature=0.1,
        )
    if cfg.provider == "ollama":
        return ChatOllama(
            model=cfg.ollama_model,
            base_url=cfg.ollama_base_url,
            temperature=0.0,
        )
    if cfg.provider == "g4f":
        return G4FChat(
            model=cfg.model,
            models=cfg.g4f_models or None,
            temperature=cfg.g4f_temperature,
            max_tokens=cfg.g4f_max_tokens,
            timeout=cfg.g4f_timeout,
            retries=cfg.g4f_retries,
        )
    # fallback to OpenAI-compatible endpoint
    return ChatOpenAI(
        model=cfg.model,
        api_key=SecretStr(cfg.openai_api_key) if cfg.openai_api_key else None,
        base_url=cfg.openai_base_url or None,
        temperature=0.1,
    )


def as_messages(prompt: str) -> list[BaseMessage]:
    system = SystemMessage(content=(
        "Tu es un architecte logiciel senior (staff).\n"
        "Objectif: définir d'abord les features, interfaces et processus d'intégration entre modules.\n"
        "Règles:\n- commence par un plan d'architecture (composants, APIs, contrats, dataflow, risques)\n"
        "- propose un ADR et un plan d'intégration incrémentale\n- respecte les contraintes QA (ruff, mypy, pytest) et les garde-fous git."
    ))
    user = HumanMessage(content=prompt)
    return [system, user]
