from __future__ import annotations

import json
import logging
import os
import time
from typing import Dict, List

try:
    from services.g4f_client import call_llm, get_ranked_tested_models
except Exception:  # pragma: no cover
    call_llm = None  # type: ignore
    get_ranked_tested_models = None  # type: ignore

try:
    from core.llm_settings import get_llm_settings
except Exception:  # pragma: no cover
    get_llm_settings = None  # type: ignore


class LLMClient:
    """Thin wrapper around g4f (default). Can be swapped without changing callers.

    - generate(messages, json_mode=True) returns raw text (ideally JSON when json_mode=True)
    - retries and simple backoff included; logs basic timing.
    """

    def __init__(self, provider: str = "g4f", model: str = None):
        self.provider = provider
        llm_settings = get_llm_settings() if get_llm_settings is not None else None
        tested_models: List[str] = []
        if get_ranked_tested_models is not None:
            try:
                tested_models = [m for _, m in get_ranked_tested_models(category_preference="forecast", limit=6)]
            except Exception:
                tested_models = []
        tested_model = tested_models[0] if tested_models else None

        fallback_model = (
            tested_model
            or (llm_settings.llm_model if llm_settings is not None else None)
            or os.getenv("G4F_MODEL")
            or os.getenv("LLM_MODEL")
            or os.getenv("LLM_DEFAULT_MODEL")
            or os.getenv("G4F_DEFAULT_MODEL")
            or "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
        )
        self.model = model or os.getenv("LLM_DEFAULT_MODEL", fallback_model)

    def _call_llm(self, messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> str:
        if call_llm is None:
            raise RuntimeError("services.g4f_client.call_llm unavailable")
        res = call_llm(
            messages=messages,
            mode=os.getenv("LLM_AGENT_MODE") or os.getenv("LLM_MODEL_MODE"),
            category_preference="forecast",
            timeout=max(20, int(os.getenv("G4F_TIMEOUT_SECONDS", "60") or "60")),
            model=self.model,
        )
        if not res.get("ok"):
            raise RuntimeError(str(res.get("error") or "g4f_call_failed"))
        answer = str(res.get("answer") or "").strip()
        if not answer:
            raise RuntimeError("g4f_empty_response")
        self.model = str(res.get("model") or self.model)
        return answer

    def generate(
        self,
        messages: List[Dict[str, str]],
        *,
        json_mode: bool = True,
        temperature: float = 0.2,
        max_tokens: int = 1200,
        retries: int = 2,
        backoff_sec: float = 1.5,
    ) -> str:
        sys_json_rule = {
            "role": "system",
            "content": "Réponds STRICTEMENT en JSON valide, sans markdown, sans texte hors JSON.",
        } if json_mode else None
        msgs = ([sys_json_rule] if sys_json_rule else []) + messages
        t0 = time.time()
        last_err = None
        for i in range(max(1, retries) + 1):
            try:
                out = self._call_llm(msgs, temperature=temperature, max_tokens=max_tokens)
                dt = int((time.time() - t0) * 1000)
                logging.getLogger(__name__).info("llm_generate provider=%s model=%s ms=%d", self.provider, self.model, dt)
                return out
            except Exception as e:
                last_err = e
                time.sleep(backoff_sec * (i + 1))
        raise RuntimeError(f"LLM call failed after retries: {last_err}")
