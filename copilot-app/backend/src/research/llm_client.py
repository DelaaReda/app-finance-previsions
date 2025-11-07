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

# Add src to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

def get_llm_client():
    """Retourne client LLM configuré ou None (OpenAI ou G4F)."""
    # 1) OpenAI
    try:
        import openai  # type: ignore
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        if api_key:
            return ("openai", openai.OpenAI(api_key=api_key, base_url=base_url))
    except Exception:
        pass
    # 2) G4F (no‑auth)
    try:
        from g4f.client import Client as G4FClient  # type: ignore
        return ("g4f", G4FClient())
    except Exception:
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
        model: Modèle (défaut: env LLM_MODEL ou gpt-4o-mini)
        max_tokens: Limite réponse
    
    Returns:
        {
            "answer": str,
            "citations": List[Dict],
            "model": str,
            "tokens": int
        }
    """
    if not model:
        model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    
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
    
    # Try to use LLM if available
    client_info = get_llm_client()
    if client_info is not None:
        kind, client = client_info
        # Prepare messages once
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        # Prefer provided model; define sensible fallbacks for g4f
        fallbacks = [
            model,
            "gpt-4o-mini",
            os.getenv("G4F_DEFAULT_MODEL", "deepseek-ai/DeepSeek-R1-0528"),
        ]
        last_err = None
        for m in [m for m in fallbacks if m]:
            try:
                response = client.chat.completions.create(
                    model=m,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.3,
                )
                answer = getattr(response.choices[0].message, "content", "")
                tokens = getattr(getattr(response, "usage", None), "total_tokens", 0) or 0
                # Treat empty/near-empty answers as failure and try next model
                if not (answer or "").strip():
                    raise RuntimeError(f"empty response content for model {m}")
                # Extract citations (numbers between [])
                import re
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
                    "model": m,
                    "tokens": tokens,
                }
            except Exception as e:  # try next model
                last_err = e
                continue
        # All providers/models failed → fallback summary
        fb = "⚠️ LLM indisponible. Résumé des sources:\n\n"
        for i, chunk in enumerate(context_chunks[:5]):
            fb += f"[{i+1}] {chunk.get('text','')[:150]}...\n"
        return {"answer": fb, "citations": [], "model": "fallback", "tokens": 0, "error": str(last_err or "llm_failed")}

    # No client available → unconfigured fallback
    fallback_answer = "ℹ️ LLM non configuré (OpenAI/G4F indisponibles).\n\n"
    for i, chunk in enumerate(context_chunks[:8]):
        source_info = chunk['meta'].get('url', 'N/A')
        date_info = chunk['meta'].get('date', 'N/A')
        fallback_answer += f"[{i+1}] {chunk.get('text','')[:150]}... (Source: {source_info}, Date: {date_info})\n"
    return {
        "answer": fallback_answer,
        "citations": [],
        "model": "unconfigured",
        "tokens": 0,
        "warning": "LLM non configuré (ni OpenAI ni G4F)",
    }
