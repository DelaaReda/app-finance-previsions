# src/api/schemas.py
from __future__ import annotations
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class TimePoint(BaseModel):
    t: str
    v: float


class PricePoint(BaseModel):
    t: str
    o: float
    h: float
    l: float
    c: float
    v: float


class MacroSeries(BaseModel):
    id: str
    points: List[TimePoint]
    source: str = "FRED"
    ts: Optional[str] = None
    url: Optional[str] = None


class Indicators(BaseModel):
    rsi: Optional[float] = None
    sma20: Optional[float] = None
    macd: Optional[float] = None


class StockItem(BaseModel):
    ticker: str
    prices: List[PricePoint]
    indicators: Indicators


class NewsItem(BaseModel):
    id: str
    title: str
    url: str
    source: str
    published: str
    score: float = 0.0
    tickers: Optional[List[str]] = None
    lang: Optional[str] = None


class BriefSignal(BaseModel):
    label: str
    value: float
    reason: str


class BriefPick(BaseModel):
    ticker: str
    score: float
    rationale: str


class Brief(BaseModel):
    topSignals: List[BriefSignal]
    topRisks: List[BriefSignal]
    picks: List[BriefPick]


class BriefResponse(BaseModel):
    brief: Brief
    generatedAt: str
    sources: Dict[str, Any] = Field(default_factory=dict)


class CopilotCitation(BaseModel):
    type: Literal["news", "series", "price"]
    ref: str
    url: Optional[str] = None
    t: Optional[str] = None


class CopilotAskRequest(BaseModel):
    question: str
    scope: Optional[Dict[str, Any]] = None


class CopilotAnswer(BaseModel):
    answer: str
    citations: List[CopilotCitation]