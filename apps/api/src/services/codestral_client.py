"""Compatibility Codestral client.

Implementation is intentionally lightweight and aligned with other compatibility clients:
try the real HTTP endpoint only if CODESTRAL_API_KEY is present, otherwise return
an explicit failure payload.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)


def call_codestral(
    messages: List[Dict[str, Any]],
    model: str = "codestral-2508",
    temperature: float = 0.0,
    max_tokens: int = 800,
) -> Dict[str, Any]:
    api_key = os.environ.get("CODESTRAL_API_KEY")
    if not api_key:
        return {"ok": False, "error": "codestral_key_missing", "answer": ""}

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    try:
        response = requests.post(
            "https://codestral.mistral.ai/v1/chat/completions",
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
            "provider": "Codestral",
            "usage": data.get("usage"),
            "raw": data,
        }
    except requests.RequestException as exc:
        logger.warning("Codestral HTTP failure: %s", exc)
        return {"ok": False, "error": f"codestral_http_error: {exc}", "answer": ""}
    except Exception as exc:
        logger.exception("Codestral error")
        return {"ok": False, "error": f"codestral_error: {exc}", "answer": ""}

