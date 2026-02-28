"""Compatibility Groq client."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)


def call_groq(
    messages: List[Dict[str, Any]],
    model: str = "mixtral-8x7b-instruct",
    temperature: float = 0.0,
    max_tokens: int = 800,
) -> Dict[str, Any]:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return {"ok": False, "error": "groq_key_missing", "answer": ""}

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            or ""
        )
        return {
            "ok": True,
            "answer": content,
            "model": data.get("model"),
            "provider": "Groq",
            "usage": data.get("usage"),
            "raw": data,
        }
    except requests.RequestException as exc:
        logger.warning("Groq HTTP failure: %s", exc)
        return {"ok": False, "error": f"groq_http_error: {exc}", "answer": ""}
    except Exception as exc:
        logger.exception("Groq error")
        return {"ok": False, "error": f"groq_error: {exc}", "answer": ""}

