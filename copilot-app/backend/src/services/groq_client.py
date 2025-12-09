import os
import json
import logging
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)


def call_groq(
    messages: List[Dict[str, Any]],
    model: str = "mixtral-8x7b-instruct",
    temperature: float = 0.0,
    max_tokens: int = 800,
) -> Dict[str, Any]:
    """
    Minimal Groq client (OpenAI-compatible endpoint).
    Requiert GROQ_API_KEY dans l'environnement.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return {"ok": False, "error": "groq_key_missing", "answer": ""}

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        return {
            "ok": True,
            "answer": content,
            "model": data.get("model"),
            "provider": "Groq",
            "usage": data.get("usage"),
            "raw": data,
        }
    except requests.HTTPError as e:
        return {"ok": False, "error": f"groq_http_error: {e}", "answer": ""}
    except Exception as e:
        return {"ok": False, "error": f"groq_error: {e}", "answer": ""}

