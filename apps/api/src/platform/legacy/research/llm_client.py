from __future__ import annotations

"""
Client LLM générique avec priorités:
- OpenAI si OPENAI_API_KEY configurée
- Sinon G4F (no‑auth) avec retry et modèles fallback
- Sinon fallback textuel déterministe
"""
import os
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path
import re
import logging
logger = logging.getLogger(__name__)

# Add src to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure .env is loaded before accessing environment variables
try:
    from core.env_loader import ensure_env_loaded, get_env
    ensure_env_loaded()
except ImportError:
    # Fallback if env_loader not available
    def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
        return os.getenv(name, default)

try:
    from core.llm_settings import get_llm_settings
except Exception:  # pragma: no cover
    get_llm_settings = None  # type: ignore

# g4f_client résolu lazily à chaque appel (évite sys.modules stale au startup)
call_llm = None
get_ranked_tested_models = None

def _resolve_g4f():
    """Retourne (call_llm, get_ranked_tested_models) frais à chaque appel."""
    import sys as _sys
    from pathlib import Path as _Path
    _legacy = _Path(__file__).resolve().parent.parent        # platform/legacy
    _src    = _legacy.parent.parent                          # apps/api/src
    for _p in [str(_legacy), str(_src), str(_src/"domains"), str(_src/"services")]:
        if _p not in _sys.path:
            _sys.path.insert(0, _p)
    for _mod, _names in [
        ("services.g4f_client", ("call_llm", "get_ranked_tested_models")),
        ("domains.judge.application.g4f_client", ("call_llm", "get_ranked_tested_models")),
    ]:
        try:
            import importlib as _il
            m = _il.import_module(_mod)
            cl = getattr(m, "call_llm", None)
            gr = getattr(m, "get_ranked_tested_models", None)
            if cl is not None:
                return cl, gr
        except Exception:
            pass
    return None, None


def _get_tested_g4f_model() -> tuple[Optional[str], Optional[str]]:
    _, ranked_fn = _resolve_g4f()
    if ranked_fn is not None:
        try:
            ranked = ranked_fn(category_preference="forecast", limit=1)
            if ranked:
                return ranked[0][0], ranked[0][1]
        except Exception:
            pass
    return None, None


def get_llm_client():
    """Retourne client OpenAI configuré ou None (fallback seulement)."""
    try:
        import openai  # type: ignore
        api_key = get_env("OPENAI_API_KEY")
        base_url = get_env("OPENAI_BASE_URL", "https://api.openai.com/v1")
        if api_key:
            return ("openai", openai.OpenAI(api_key=api_key, base_url=base_url))
    except Exception:
        pass
    return None


def ask_llm(
    question: str,
    context_chunks: List[Dict[str, Any]],
    model: Optional[str] = None,
    max_tokens: int = 1000
) -> Dict[str, Any]:
    """
    Interroge LLM avec contexte RAG.
    
    Args:
        question: Question utilisateur
        context_chunks: Chunks RAG (via rag_store.search())
        model: Modèle (défaut: env LLM_MODEL ou modèle g4f par défaut)
        max_tokens: Limite réponse
    
    Returns:
        {
            "answer": str,
            "citations": List[Dict],
            "model": str,
            "tokens": int
        }
    """
    llm_settings = get_llm_settings() if get_llm_settings is not None else None
    # command-a25 = only reliably working free model (tested 2026-03-03)
    # Ignore ranked_models: DeepInfra/llama always times out
    if not model:
        model = (
            os.getenv("LLM_MODEL")
            or os.getenv("G4F_MODEL")
            or "command-a25"
        )
    
    # Construct context
    context_text = "\n\n".join([
        f"[{i+1}] {chunk['text']}\nSource: {chunk['meta'].get('url', 'N/A')} | Date: {chunk['meta'].get('date', 'N/A')}"
        for i, chunk in enumerate(context_chunks[:10])  # Limit to 10 chunks
    ])
    
    # System prompt
    system_prompt = """Tu es un copilot financier personnel. Ton role: aider l'utilisateur a prendre des decisions d'investissement rapides et claires.

Regles:
- Reponds en 3-5 phrases maximum, orientees action
- Commence toujours par: HOLD / BUY / SELL / REDUIRE / AUGMENTER selon le contexte
- Cite tes sources avec [numero] quand pertinent
- Si les donnees manquent, dis-le en 1 phrase et donne quand meme une direction probable
- Pas de disclaimers juridiques, l'utilisateur sait que c'est une aide et non un conseil officiel
- Utilise les chiffres disponibles (%, prix, tendances)"""
    
    # User prompt
    user_prompt = f"""Contexte (sources de données):
{context_text}

Question: {question}

Réponse (avec citations [1], [2], etc.):"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    last_err = None

    _call_llm, _ = _resolve_g4f()
    if _call_llm is not None:
        logger.warning("[ask_llm] calling with model=%s", model)
        llm_res = _call_llm(
            messages=messages,
            mode=os.getenv("LLM_RAG_MODE") or os.getenv("LLM_MODEL_MODE"),
            model=model,
            timeout=max(20, int(os.getenv("G4F_TIMEOUT_SECONDS", "60") or "60")),
            category_preference="forecast",
        )
        logger.warning("[ask_llm] result: ok=%s model=%s err=%s", llm_res.get('ok'), llm_res.get('model'), str(llm_res.get('error',''))[:100])
        if llm_res.get("ok"):
            answer = str(llm_res.get("answer") or "").strip()
            cited_indices = set(int(g.group(1)) - 1 for g in re.finditer(r"\[(\d+)\]", answer or ""))
            citations = [
                {
                    "index": i + 1,
                    "type": context_chunks[i]["meta"].get("type", "context"),
                    "url": context_chunks[i]["meta"].get("url", ""),
                    "date": context_chunks[i]["meta"].get("date", ""),
                    "excerpt": (context_chunks[i]["text"] or "")[:200] + "...",
                }
                for i in cited_indices
                if 0 <= i < len(context_chunks)
            ]
            return {
                "answer": answer,
                "citations": citations,
                "model": llm_res.get("model") or model,
                "tokens": 0,
            }
        last_err = llm_res.get("error") or "llm_call_failed"

    client_info = get_llm_client()
    if client_info is not None:
        _, client = client_info
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.3,
            )
            answer = getattr(response.choices[0].message, "content", "")
            if not (answer or "").strip():
                raise RuntimeError("empty_response_content")
            tokens = getattr(getattr(response, "usage", None), "total_tokens", 0) or 0
            cited_indices = set(int(g.group(1)) - 1 for g in re.finditer(r"\[(\d+)\]", answer or ""))
            citations = [
                {
                    "index": i + 1,
                    "type": context_chunks[i]["meta"].get("type", "context"),
                    "url": context_chunks[i]["meta"].get("url", ""),
                    "date": context_chunks[i]["meta"].get("date", ""),
                    "excerpt": (context_chunks[i]["text"] or "")[:200] + "...",
                }
                for i in cited_indices
                if 0 <= i < len(context_chunks)
            ]
            return {
                "answer": (answer or "").strip(),
                "citations": citations,
                "model": model,
                "tokens": tokens,
            }
        except Exception as e:
            last_err = e

    fb = "⚠️ LLM indisponible. Résumé des sources:\n\n"
    for i, chunk in enumerate(context_chunks[:5]):
        fb += f"[{i+1}] {chunk.get('text','')[:150]}...\n"
    return {"answer": fb, "citations": [], "model": "fallback", "tokens": 0, "error": str(last_err or "llm_failed")}
