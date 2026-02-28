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

try:
    from services.g4f_client import call_llm, get_ranked_tested_models
except Exception:  # pragma: no cover
    call_llm = None  # type: ignore
    get_ranked_tested_models = None  # type: ignore


def _get_tested_g4f_model() -> tuple[None | str, None | str]:
    if get_ranked_tested_models is not None:
        try:
            ranked = get_ranked_tested_models(category_preference="forecast", limit=1)
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
    model: str = None,
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
    tested_provider, tested_model = _get_tested_g4f_model()
    if not model:
        model = (
            (llm_settings.llm_model if llm_settings is not None else None)
            or tested_model
            or os.getenv("LLM_MODEL")
            or os.getenv("G4F_MODEL")
            or "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
        )
    
    # Construct context
    context_text = "\n\n".join([
        f"[{i+1}] {chunk['text']}\nSource: {chunk['meta'].get('url', 'N/A')} | Date: {chunk['meta'].get('date', 'N/A')}"
        for i, chunk in enumerate(context_chunks[:10])  # Limit to 10 chunks
    ])
    
    # System prompt
    system_prompt = """Tu es un analyste financier expert. 
    
Réponds aux questions en te basant UNIQUEMENT sur le contexte fourni.
- Cite TOUJOURS tes sources avec [numéro]
- Si l'information n'est pas dans le contexte, dis "Je n'ai pas cette information"
- Sois concis et précis
- Utilise des chiffres quand disponibles"""
    
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

    if call_llm is not None:
        llm_res = call_llm(
            messages=messages,
            mode=os.getenv("LLM_RAG_MODE") or os.getenv("LLM_MODEL_MODE"),
            model=model,
            timeout=max(20, int(os.getenv("G4F_TIMEOUT_SECONDS", "60") or "60")),
            category_preference="forecast",
        )
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
