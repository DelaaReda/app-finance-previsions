"""
News features endpoints required by the frontend.
 - GET /api/news/features/daily?ticker=...&start=YYYY-MM-DD&end=YYYY-MM-DD&limit=365

For now, returns empty rows if gold features are not materialized.
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from typing import Any, Dict, List, Optional
from datetime import datetime

router = APIRouter(tags=["news"])


@router.get("/news/features/daily")
async def news_features_daily(
    ticker: Optional[str] = Query(None),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    limit: int = Query(365, ge=1, le=1095),
):
    # Placeholder: gold features parquet not wired here; return never-empty structure
    rows: List[Dict[str, Any]] = []
    return {"ok": True, "data": rows}

