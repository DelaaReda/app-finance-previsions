"""Typed schemas for Forecasts API (Judge-parity contract)."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

try:
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover
    class BaseModel:  # type: ignore
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    def Field(default=None, **_kwargs):  # type: ignore
        return default


ForecastSortBy = Literal["score", "confidence", "expected_return", "timestamp", "risk_level"]
ForecastSortOrder = Literal["asc", "desc"]


class ForecastCacheMeta(BaseModel):
    hit: bool = False
    age_seconds: Optional[float] = None
    ttl_seconds: Optional[int] = None


class ForecastFiltersApplied(BaseModel):
    asset_type: str
    horizon: str
    search: Optional[str] = None
    sort_by: ForecastSortBy = "score"
    sort_order: ForecastSortOrder = "desc"
    tickers: List[str] = Field(default_factory=list)
    limit: int = 50
    offset: int = 0


class ForecastStats(BaseModel):
    total_loaded: int = 0
    filtered_count: int = 0
    returned_count: int = 0
    high_confidence_count: int = 0
    high_confidence_percentage: float = 0.0
    avg_confidence: float = 0.0


class ForecastsData(BaseModel):
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    count: int = 0
    total: int = 0
    offset: int = 0
    limit: int = 50
    generated_at: str
    freshness: str
    last_update: str
    source: List[str] = Field(default_factory=list)
    filters_applied: ForecastFiltersApplied
    stats: ForecastStats = Field(default_factory=ForecastStats)
    warnings: List[str] = Field(default_factory=list)
    cache: Optional[ForecastCacheMeta] = None
    debug_pipeline: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    message: Optional[str] = None


class ForecastsResponse(BaseModel):
    ok: bool = True
    data: ForecastsData


class ForecastDetailData(BaseModel):
    forecast: Dict[str, Any] = Field(default_factory=dict)
    found: bool = False
    generated_at: str
    freshness: str
    last_update: str
    source: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    message: Optional[str] = None


class ForecastDetailResponse(BaseModel):
    ok: bool = True
    data: ForecastDetailData

