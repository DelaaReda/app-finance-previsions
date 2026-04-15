"""Typed public contracts for Personal Finance copilot payloads.

These contracts are shared between API services (including judge-style facades)
and frontend consumers. They intentionally remain minimal and stable:
- never-empty start payloads
- ask/open action lists
- portfolio context + ranked action
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

try:
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover - defensive fallback for lightweight test/runtime imports
    class BaseModel:  # type: ignore
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        def dict(self, *args, **kwargs):
            return self.__dict__.copy()

        def model_dump(self, *args, **kwargs):  # pragma: no cover
            return self.__dict__.copy()

    def Field(default=None, **_kwargs):  # type: ignore
        return default

CopilotActionKind = Literal["ask", "open"]


class CopilotActionDto(BaseModel):
    id: str = ""
    kind: CopilotActionKind = "open"
    label: str = ""
    target: str = ""
    prefill: Dict[str, Any] = Field(default_factory=dict)


class CopilotRankedActionDto(BaseModel):
    id: str = ""
    kind: CopilotActionKind = "ask"
    label: str = ""
    target: str = ""
    prefill: Dict[str, Any] = Field(default_factory=dict)


class CopilotBriefDto(BaseModel):
    summary: str = ""
    market_sentiment: str = "UNKNOWN"
    top_signals: List[Any] = Field(default_factory=list)
    top_risks: List[Any] = Field(default_factory=list)
    macro_signals: List[Any] = Field(default_factory=list)
    sector_rotation: Dict[str, List[Any]] = Field(default_factory=lambda: {"top": [], "bottom": []})
    source: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    generated_at: str = ""
    freshness: str = ""
    title: Optional[str] = None
    headline: Optional[str] = None
    market_regime: Optional[Dict[str, Any]] = None
    event_timing: Dict[str, Any] = Field(default_factory=dict)
    note: Optional[str] = None


class CopilotStartPayload(BaseModel):
    brief_of_day: CopilotBriefDto = Field(default_factory=CopilotBriefDto)
    ranked_action: Optional[CopilotRankedActionDto] = None
    ask: List[CopilotActionDto] = Field(default_factory=list)
    open: List[CopilotActionDto] = Field(default_factory=list)
    portfolio_context: Optional[Dict[str, Any]] = None
    generated_at: str = ""
    freshness: str = ""
    source: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    filters_applied: Dict[str, Any] = Field(default_factory=dict)
    stats: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    fallback_used: Optional[str] = None
    context_influence: Optional[Dict[str, Any]] = None
    regime_detection: Optional[Dict[str, Any]] = None
    allocation_drift_alerts: Optional[Dict[str, Any]] = None
    scope_tickers: Optional[List[str]] = None
    note: Optional[str] = None
    status: Optional[str] = "ok"
    error: Optional[Any] = None
    message: Optional[str] = None
    cache: Optional[Dict[str, Any]] = None


class CopilotStartResponse(BaseModel):
    ok: bool = True
    data: CopilotStartPayload = Field(default_factory=CopilotStartPayload)


__all__ = [
    "CopilotActionKind",
    "CopilotActionDto",
    "CopilotBriefDto",
    "CopilotRankedActionDto",
    "CopilotStartPayload",
    "CopilotStartResponse",
]
