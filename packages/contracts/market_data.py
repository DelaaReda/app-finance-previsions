"""Shared market-data response contracts.

This module is intentionally non-versioned. It is the single public contract
home for the API wave endpoints under the market-data domain.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover
    class BaseModel:  # type: ignore
        def __init__(self, **kwargs: Any) -> None:
            for key, value in kwargs.items():
                setattr(self, key, value)

    def Field(default: Any = None, **_: Any) -> Any:  # type: ignore
        return default


class MarketDataStats(BaseModel):
    count: int = Field(default=0)
    total: Optional[int] = Field(default=None)


class MarketDataResponseMetadata(BaseModel):
    generated_at: str = Field(default="")
    freshness: Optional[str] = Field(default=None)
    last_update: Optional[str] = Field(default=None)
    source: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    filters_applied: Dict[str, Any] = Field(default_factory=dict)
    stats: MarketDataStats = Field(default_factory=MarketDataStats)
    fallback_used: bool = Field(default=False)


class MarketDataEnvelope(BaseModel):
    ok: bool = Field(default=True)
    data: Dict[str, Any] = Field(default_factory=dict)
    generated_at: Optional[str] = Field(default=None)
    freshness: Optional[str] = Field(default=None)
    last_update: Optional[str] = Field(default=None)
    source: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    filters_applied: Dict[str, Any] = Field(default_factory=dict)
    stats: Dict[str, Any] = Field(default_factory=dict)
    fallback_used: bool = Field(default=False)
