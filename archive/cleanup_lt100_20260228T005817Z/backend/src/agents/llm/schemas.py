from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class Contributor(BaseModel):
    source: Literal["equity", "commodity", "macro", "news", "risk"]
    model: str
    horizon: Optional[str] = None
    symbol: Optional[str] = None
    score: Optional[float] = None
    prediction: Optional[str] = None
    rationale: Optional[str] = None


class LLMEnsembleSummary(BaseModel):
    asof: str
    regime: Optional[str] = None
    risk_level: Optional[Literal["low", "medium", "high"]] = None
    outlook_days_7: Optional[str] = None
    outlook_days_30: Optional[str] = None
    key_drivers: List[str] = Field(default_factory=list)
    contributors: List[Contributor] = Field(default_factory=list)

