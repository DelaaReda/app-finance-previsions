from __future__ import annotations

import json
import logging
import os
import time
from typing import Dict, List

try:
    from g4f.client import Client as G4FClient
except Exception:
    G4FClient = None  # type: ignore


class LLMClient:
    """Thin wrapper around g4f (default). Can be swapped without changing callers.

    - generate(messages, json_mode=True) returns raw text (ideally JSON when json_mode=True)
    - retries and simple backoff included; logs basic timing.
    """

    def __init__(self, provider: str = "g4f", model: str = None):
        self.provider = provider
        self.model = model or os.getenv("LLM_DEFAULT_MODEL", "deepseek-ai/DeepSeek-R1-0528")

    def _call_g4f(self, messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> str:
        if G4FClient is None:
            raise RuntimeError("g4f is not installed. pip install -U g4f")
        client = G4FClient()
        res = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        try:
            return (res.choices[0].message.content or "").strip()
        except Exception:
            return str(res)

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
                out = self._call_g4f(msgs, temperature=temperature, max_tokens=max_tokens)
                dt = int((time.time() - t0) * 1000)
                logging.getLogger(__name__).info("llm_generate provider=%s model=%s ms=%d", self.provider, self.model, dt)
                return out
            except Exception as e:
                last_err = e
                time.sleep(backoff_sec * (i + 1))
        raise RuntimeError(f"LLM call failed after retries: {last_err}")

