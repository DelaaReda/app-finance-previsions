from __future__ import annotations

from typing import Optional

from langchain.chat_models.base import BaseChatModel
from langchain_community.chat_models import ChatOllama
from langchain_openai import ChatOpenAI

from ..config import AgentConfig
from .g4f_chat import G4FChat
from .types import ChatMessage


def get_llm(task: str, cfg: Optional[AgentConfig] = None) -> BaseChatModel:
    cfg = cfg or AgentConfig()
    if cfg.provider == "openai":
        return ChatOpenAI(
            model=cfg.model,
            api_key=cfg.openai_api_key,
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
        return G4FChat(model=cfg.model, temperature=0.1)
    # fallback to OpenAI-compatible endpoint
    return ChatOpenAI(
        model=cfg.model,
        api_key=cfg.openai_api_key,
        base_url=cfg.openai_base_url or None,
        temperature=0.1,
    )


def as_messages(prompt: str) -> list[ChatMessage]:
    return [{"role": "system", "content": "Tu es un staff engineer méticuleux et fiable."},
            {"role": "user", "content": prompt}]
