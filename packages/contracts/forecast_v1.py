"""Forecast DTO schemas (versioned API contract).

This module defines the canonical forecast response contract shared by:
- backend route (`api/routes/forecasts.py`)
- service payload (`services/forecasts_service.py`)
- frontend consumers (DTO-driven rendering only)
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

try:
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover - defensive fallback
    class BaseModel:  # type: ignore
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    def Field(default=None, **_kwargs):  # type: ignore
        return default


ForecastSortBy = Literal[
    "score",
    "confidence",
    "expected_return",
    "timestamp",
    "risk_level",
]
ForecastSortOrder = Literal["asc", "desc"]


class ForecastContractDto(BaseModel):
    forecast_id: str
    ticker: str
    asset_type: str = Field(default="all")
    horizon: str = Field(default="all")

    # Decision contract (must exist end-to-end)
    action: str = Field(default="hold")
    direction: str = Field(default="flat")
    confidence: float = Field(default=0.0)
    why: str = Field(default="")
    risk_flag: bool = Field(default=False)
    generated_at: str = Field(default="")
    updated_at: str = Field(default="")
    freshness_status: Literal["fresh", "stale", "unknown"] = Field(default="unknown")

    # Additional forecasting fields used by UI/ranking.
    expected_return: float = Field(default=0.0)
    score: float = Field(default=0.0)
    risk_level: Literal["low", "medium", "high", "critical"] = Field(default="medium")
    timestamp: str = Field(default="")
    name: Optional[str] = None
    sector: Optional[str] = None
    model: Optional[str] = None

    # Observability contract (forecast-oriented).
    provider_chain: List[str] = Field(default_factory=list)
    fallback_used: bool = Field(default=False)
    latency_ms: float = Field(default=0.0)
    freshness_age: float = Field(default=-1.0)
    provenance: Dict[str, Any] = Field(default_factory=dict)


class ForecastsDataDto(BaseModel):
    rows: List[ForecastContractDto] = Field(default_factory=list)
    count: int = Field(default=0)
    total: int = Field(default=0)
    offset: int = Field(default=0)
    limit: int = Field(default=50)
    generated_at: str = Field(default="")
    freshness: str = Field(default="")
    freshness_status: Literal["fresh", "stale", "unknown"] = Field(default="unknown")
    freshness_age: float = Field(default=-1.0)
    last_update: str = Field(default="")
    updated_at: str = Field(default="")
    source: List[str] = Field(default_factory=list)
    filters_applied: Dict[str, Any] = Field(default_factory=dict)
    stats: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    cache: Dict[str, Any] = Field(default_factory=dict)
    provider_chain: List[str] = Field(default_factory=list)
    fallback_used: bool = Field(default=False)
    latency_ms: float = Field(default=0.0)
    observability: Dict[str, Any] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    debug_pipeline: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None
    error: Optional[str] = None


class ForecastsResponse(BaseModel):
    ok: bool = True
    data: ForecastsDataDto = Field(default_factory=ForecastsDataDto)


class ForecastDetailDataDto(BaseModel):
    forecast: Dict[str, Any] = Field(default_factory=dict)
    found: bool = False
    generated_at: str = Field(default="")
    freshness: str = Field(default="")
    last_update: str = Field(default="")
    source: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    message: Optional[str] = None
    error: Optional[str] = None


class ForecastDetailResponse(BaseModel):
    ok: bool = True
    data: ForecastDetailDataDto = Field(default_factory=ForecastDetailDataDto)


class WalkForwardScoreboardRowDto(BaseModel):
    metric_key: str
    label: str
    scope: str = Field(default="overall")
    value: float = Field(default=0.0)
    target: Optional[float] = None
    comparator: Literal["gte", "lte", "info"] = Field(default="info")
    status: Literal["pass", "fail", "unknown"] = Field(default="unknown")
    sample_size: int = Field(default=0)


class WalkForwardScoreboardDataDto(BaseModel):
    rows: List[WalkForwardScoreboardRowDto] = Field(default_factory=list)
    count: int = Field(default=0)
    generated_at: str = Field(default="")
    freshness: str = Field(default="")
    last_update: str = Field(default="")
    updated_at: str = Field(default="")
    freshness_status: Literal["fresh", "stale", "unknown"] = Field(default="unknown")
    freshness_age: float = Field(default=-1.0)
    source: List[str] = Field(default_factory=list)
    filters_applied: Dict[str, Any] = Field(default_factory=dict)
    stats: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    cache: Dict[str, Any] = Field(default_factory=dict)
    threshold_summary: Dict[str, Any] = Field(default_factory=dict)
    summary: Dict[str, Any] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    debug_pipeline: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None
    error: Optional[str] = None


class WalkForwardScoreboardResponse(BaseModel):
    ok: bool = True
    data: WalkForwardScoreboardDataDto = Field(default_factory=WalkForwardScoreboardDataDto)
