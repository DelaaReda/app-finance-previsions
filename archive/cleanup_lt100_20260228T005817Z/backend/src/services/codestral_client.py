import os
import json
import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


def call_codestral(
    messages: List[Dict[str, Any]],
    model: str = "codestral-2508",
    temperature: float = 0.0,
    max_tokens: int = 800,
) -> Dict[str, Any]:
    """
    Minimal client pour Codestral (API Mistral).
    Requiert CODESTRAL_API_KEY dans l'environnement.
    """
    api_key = os.environ.get("CODESTRAL_API_KEY")
    if not api_key:
        return {"ok": False, "error": "codestral_key_missing", "answer": ""}

    url = "https://codestral.mistral.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
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
            "provider": "Codestral",
            "usage": data.get("usage"),
            "raw": data,
        }
    except requests.HTTPError as e:
        return {"ok": False, "error": f"codestral_http_error: {e}", "answer": ""}
    except Exception as e:
        return {"ok": False, "error": f"codestral_error: {e}", "answer": ""}

