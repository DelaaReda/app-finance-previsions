"""Reusable business logic for Copilot endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from services.service_standard import utc_now_iso
except Exception:  # pragma: no cover
    from src.services.service_standard import utc_now_iso  # type: ignore


def _normalize_tickers(tickers: Optional[List[str]]) -> List[str]:
    return sorted(
        {
            str(item).strip().upper()
            for item in (tickers or [])
            if str(item).strip()
        }
    )


def _build_sources_from_chunks(context_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sources: List[Dict[str, Any]] = []
    for chunk in context_chunks:
        meta = chunk.get("meta") if isinstance(chunk.get("meta"), dict) else {}
        text = str(chunk.get("text") or "")
        sources.append(
            {
                "type": meta.get("type", "context"),
                "url": meta.get("url", ""),
                "date": meta.get("date", ""),
                "ticker": meta.get("ticker", ""),
                "excerpt": text[:200] + "..." if len(text) > 200 else text,
                "id": chunk.get("id", ""),
            }
        )
    return sources


async def build_ask_payload(
    *,
    question: str,
    scope: Optional[Dict[str, Any]] = None,
    tickers: Optional[List[str]] = None,
    max_sources: Optional[int] = 5,
    context_years: Optional[int] = None,
) -> Dict[str, Any]:
    """Build copilot answer payload from RAG + LLM.

    Returns a never-empty payload.
    """
    try:
        from research.rag_store import RAGStore
        from research.llm_client import ask_llm
    except Exception as import_exc:
        return {
            "answer": f"Copilot unavailable: {import_exc}",
            "sources": [],
            "citations": [],
            "model": "unconfigured",
            "confidence": 0.0,
            "generated_at": utc_now_iso(),
            "sources_count": 0,
            "quality_status": "error",
            "requirements_met": {"min_sources_2": False, "quality_threshold": False},
            "error": str(import_exc),
        }

    try:
        rag_store = RAGStore()
        resolved_scope = dict(scope or {})
        normalized_tickers = _normalize_tickers(tickers)
        if normalized_tickers:
            resolved_scope["tickers"] = normalized_tickers
        if context_years is not None:
            resolved_scope.setdefault("context_years", int(context_years))

        top_k = max(1, min(int(max_sources or 5), 20))
        context_chunks = rag_store.search(resolved_scope, top_k=top_k)

        if not context_chunks:
            return {
                "answer": (
                    "Je n'ai pas trouvé d'informations pertinentes pour répondre à votre "
                    f"question: '{question}'."
                ),
                "sources": [],
                "citations": [],
                "model": "rag_empty",
                "confidence": 0.3,
                "generated_at": utc_now_iso(),
                "warning": "Aucune source trouvée dans la mémoire",
                "sources_count": 0,
                "quality_status": "insufficient_sources",
                "requirements_met": {
                    "min_sources_2": False,
                    "quality_threshold": False,
                },
            }

        llm_response = ask_llm(
            question=question,
            context_chunks=context_chunks,
            max_tokens=1000,
        )
        sources = _build_sources_from_chunks(context_chunks)
        model_name = str(llm_response.get("model") or "unknown")
        has_min_sources = len(sources) >= 2
        has_quality_model = model_name not in {"unconfigured", "fallback", "rag_empty"}
        quality_status = (
            "sufficient_sources" if (has_min_sources and has_quality_model) else "insufficient_sources"
        )
        confidence = 0.8 if quality_status == "sufficient_sources" else 0.4

        return {
            "answer": str(llm_response.get("answer") or "").strip(),
            "sources": sources,
            "citations": llm_response.get("citations", []),
            "model": model_name,
            "confidence": confidence,
            "generated_at": utc_now_iso(),
            "sources_count": len(sources),
            "quality_status": quality_status,
            "requirements_met": {
                "min_sources_2": has_min_sources,
                "quality_threshold": has_quality_model,
            },
        }
    except Exception as exc:
        return {
            "answer": f"Désolé, une erreur s'est produite lors du traitement: {exc}",
            "sources": [],
            "citations": [],
            "model": "error",
            "confidence": 0.0,
            "generated_at": utc_now_iso(),
            "sources_count": 0,
            "quality_status": "error",
            "requirements_met": {"min_sources_2": False, "quality_threshold": False},
            "error": str(exc),
        }


def build_history_payload(*, limit: int) -> Dict[str, Any]:
    """Never-empty history payload (no mock data)."""
    return {
        "conversations": [],
        "count": 0,
        "limit": int(limit),
        "source": ["copilot_service", "history_not_persisted"],
    }


async def build_context_payload(context_service_cls: Optional[Any] = None) -> Any:
    """Returns current context when available, or a never-empty fallback."""
    try:
        cls = context_service_cls
        if cls is None:
            try:
                from services.context_service import ContextService as _ContextService
                cls = _ContextService
            except Exception:
                cls = None
        if cls is not None:
            return await cls().get_current_market_context()
    except Exception:
        pass
    return []


def build_report_payload(*, prompt: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a report request payload."""
    return {
        "id": f"rpt_{int(datetime.utcnow().timestamp())}",
        "prompt": prompt,
        "filters": filters or {},
        "created_at": utc_now_iso(),
        "status": "queued",
    }
