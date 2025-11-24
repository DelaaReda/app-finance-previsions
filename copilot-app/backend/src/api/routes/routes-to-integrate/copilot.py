"""
Copilot endpoints expected by the frontend.
Implements minimal, never-empty endpoints backed by existing services when possible.
 - POST /api/copilot/ask
 - GET  /api/copilot/history
 - GET  /api/copilot/context
 - POST /api/copilot/reports
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    from services.context_service import ContextService
except Exception:  # pragma: no cover
    ContextService = None  # type: ignore


router = APIRouter(tags=["copilot"])


class CopilotAskRequest(BaseModel):
    question: str
    scope: Optional[Dict[str, Any]] = None
    tickers: Optional[List[str]] = None
    max_sources: Optional[int] = 5


@router.post("/copilot/ask")
async def copilot_ask(req: CopilotAskRequest):
    # Best effort: provide an answer using context hints if available
    try:
        context_summary = ""
        if ContextService is not None:
            ctx = await ContextService().get_current_market_context()
            regime = (ctx or {}).get("regime") or "NORMAL"
            context_summary = f"Current market regime: {regime}."
        answer = (f"Analysis queued. {context_summary} Question: {req.question}").strip()
        return {
            "ok": True,
            "data": {
                "answer": answer,
                "sources": [],
                "citations": [],
                "confidence": 0.4,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "sources_count": 0,
                "quality_status": "insufficient_sources",
            },
        }
    except Exception as e:
        return {
            "ok": True,
            "data": {
                "answer": f"Temporary issue: {e}. Please retry.",
                "sources": [],
                "citations": [],
                "confidence": 0.0,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "sources_count": 0,
                "quality_status": "error",
            },
        }


@router.get("/copilot/history")
async def copilot_history(limit: int = 20):
    return {
        "ok": True,
        "data": {
            "conversations": [],
            "count": 0,
            "limit": limit,
        },
    }


@router.get("/copilot/context")
async def copilot_context():
    try:
        if ContextService is not None:
            ctx = await ContextService().get_current_market_context()
            return {"ok": True, "data": ctx}
    except Exception:
        pass
    return {"ok": True, "data": []}


class CopilotReportRequest(BaseModel):
    prompt: str
    filters: Optional[Dict[str, Any]] = None


@router.post("/copilot/reports")
async def copilot_reports(req: CopilotReportRequest):
    # Minimal acceptance to unblock UI
    return {
        "ok": True,
        "data": {
            "id": f"rpt_{int(datetime.utcnow().timestamp())}",
            "prompt": req.prompt,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "status": "queued",
        },
    }

