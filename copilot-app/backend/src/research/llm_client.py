"""
Client LLM générique (OpenAI-compatible).
Supporte OpenAI, Anthropic, local (Ollama), etc.
"""
import os
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

# Add src to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

def get_llm_client():
    """Retourne client configuré selon env."""
    # Check if openai is available
    try:
        import openai
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        
        if api_key:
            return openai.OpenAI(api_key=api_key, base_url=base_url)
        else:
            # Return None if no API key is set
            return None
    except ImportError:
        # Return None if openai is not available
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
    client = get_llm_client()
    
    if client is not None:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.3
            )
            
            answer = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0
            
            # Extract citations (numbers between [])
            import re
            cited_indices = set(int(m.group(1)) - 1 for m in re.finditer(r'\[(\d+)\]', answer))
            
            citations = [
                {
                    "index": i + 1,
                    "type": context_chunks[i]["meta"]["type"],
                    "url": context_chunks[i]["meta"].get("url", ""),
                    "date": context_chunks[i]["meta"].get("date", ""),
                    "excerpt": context_chunks[i]["text"][:200] + "..."
                }
                for i in cited_indices
                if i < len(context_chunks)
            ]
            
            return {
                "answer": answer,
                "citations": citations,
                "model": model,
                "tokens": tokens
            }
        
        except Exception as e:
            # Fallback: heuristic summary
            fallback_answer = f"⚠️ LLM indisponible. Voici un résumé des sources:\n\n"
            for i, chunk in enumerate(context_chunks[:5]):
                fallback_answer += f"[{i+1}] {chunk['text'][:150]}...\n"
            
            return {
                "answer": fallback_answer,
                "citations": [],
                "model": "fallback",
                "tokens": 0,
                "error": str(e)
            }
    else:
        # Fallback response when no LLM client is available
        fallback_answer = f"ℹ️ LLM non configuré (pas de clé API). Voici les sources trouvées:\n\n"
        for i, chunk in enumerate(context_chunks[:10]):
            source_info = chunk['meta'].get('url', 'N/A')
            date_info = chunk['meta'].get('date', 'N/A')
            fallback_answer += f"[{i+1}] {chunk['text'][:150]}... (Source: {source_info}, Date: {date_info})\n"
        
        return {
            "answer": fallback_answer,
            "citations": [],
            "model": "unconfigured",
            "tokens": 0,
            "warning": "LLM non configuré - utilisez OPENAI_API_KEY"
        }