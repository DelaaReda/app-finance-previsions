# src/api/schemas.py
"""
Pydantic schemas for FastAPI with full traceability.
All responses include: created_at, source, asof_date, hash
"""
from __future__ import annotations

from datetime import datetime, date
from typing import Optional, List, Dict, Any, Literal
from enum import Enum

from pydantic import BaseModel, Field, field_validator


# ======================== TRACEABILITY ========================

class TraceMetadata(BaseModel):
    """Mandatory traceability metadata for all responses."""
    created_at: datetime = Field(..., description="Timestamp de création ISO8601")
    source: str = Field(..., description="Source des données (FRED, yfinance, RSS, etc.)")
    asof_date: date = Field(..., description="Date de validité des données")
    hash: str = Field(..., description="Hash SHA256 des données pour versionning")

    class Config:
        json_schema_extra = {
            "example": {
                "created_at": "2025-10-30T14:30:00Z",
                "source": "FRED",
                "asof_date": "2025-10-30",
                "hash": "a3f5d8c9e2b1f4a6d8c9e2b1f4a6d8c9"
            }
        }


# ======================== COMMON ========================

class ApiResponse(BaseModel):
    """Base API response wrapper."""
    ok: bool = Field(..., description="Success status")
    data: Optional[Any] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message if ok=False")
    trace: Optional[TraceMetadata] = Field(None, description="Traceability metadata")


class HealthStatus(str, Enum):
    UP = "up"
    DEGRADED = "degraded"
    DOWN = "down"


class FreshnessStatus(str, Enum):
    FRESH = "fresh"
    STALE = "stale"
    MISSING = "missing"


# ======================== HEALTH ========================

class HealthData(BaseModel):
    status: HealthStatus
    timestamp: datetime
    version: str


class HealthResponse(BaseModel):
    ok: bool = True
    data: HealthData


class DataSourceFreshness(BaseModel):
    last_update: Optional[datetime]
    age_hours: Optional[float]
    status: FreshnessStatus


class FreshnessData(BaseModel):
    macro: DataSourceFreshness
    stocks: DataSourceFreshness
    news: DataSourceFreshness


class FreshnessResponse(BaseModel):
    ok: bool = True
    data: FreshnessData


# ======================== MACRO (PILIER 1) ========================

class DataPoint(BaseModel):
    """Single time series point."""
    timestamp: datetime
    value: float


class MacroSeries(BaseModel):
    """FRED time series with metadata."""
    series_id: str = Field(..., description="FRED series ID")
    name: str = Field(..., description="Human-readable name")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    values: List[DataPoint] = Field(..., description="Time series data points")
    latest: Optional[Dict[str, Any]] = Field(None, description="Latest value")
    trace: TraceMetadata


class MacroOverviewData(BaseModel):
    """Macro overview response data."""
    series: List[MacroSeries]
    range: str
    trace: TraceMetadata


class MacroOverviewResponse(BaseModel):
    ok: bool = True
    data: MacroOverviewData


class MacroSnapshotData(BaseModel):
    """Current macro snapshot (latest values)."""
    snapshot: Dict[str, float]
    trace: TraceMetadata


class MacroSnapshotResponse(BaseModel):
    ok: bool = True
    data: MacroSnapshotData


class MacroIndicatorsData(BaseModel):
    """Derived macro indicators."""
    cpi_yoy: Optional[float]
    yield_curve_10y_2y: Optional[float]
    recession_probability: Optional[float]
    vix: Optional[float]
    trace: TraceMetadata


class MacroIndicatorsResponse(BaseModel):
    ok: bool = True
    data: MacroIndicatorsData


# ======================== STOCKS (PILIER 2) ========================

class PricePoint(BaseModel):
    """Price history point (downsampled)."""
    timestamp: int = Field(..., description="Unix timestamp")
    value: float


class TechnicalIndicators(BaseModel):
    """Technical indicators for a stock."""
    rsi: Optional[float] = Field(None, description="RSI (14 periods)")
    sma20: Optional[float] = Field(None, description="20-day SMA")
    sma50: Optional[float] = Field(None, description="50-day SMA")
    sma200: Optional[float] = Field(None, description="200-day SMA")
    macd: Optional[Dict[str, float]] = Field(None, description="MACD components")
    bollinger: Optional[Dict[str, float]] = Field(None, description="Bollinger Bands")


class SignalType(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class StockSignal(BaseModel):
    """Trading signal."""
    type: SignalType
    strength: float = Field(..., ge=0.0, le=1.0, description="Signal strength 0-1")
    message: str = Field(..., description="Signal description")
    source: str = Field(..., description="Indicator source (RSI, MACD, etc.)")


class CompositeScore(BaseModel):
    """Composite score (40% macro + 40% tech + 20% news)."""
    total: float = Field(..., ge=0.0, le=1.0)
    macro: float = Field(..., ge=0.0, le=1.0)
    technical: float = Field(..., ge=0.0, le=1.0)
    news: float = Field(..., ge=0.0, le=1.0)


class PriceData(BaseModel):
    """Current price info."""
    current: float
    change: Optional[float] = None
    change_percent: Optional[float] = None
    currency: str = "USD"
    date: date


class StockOverviewData(BaseModel):
    """Complete stock overview."""
    ticker: str
    price: PriceData
    price_history: List[PricePoint] = Field(..., description="Downsampled LTTB")
    technicals: Optional[TechnicalIndicators] = None
    signals: List[StockSignal] = Field(default_factory=list)
    composite_score: Optional[CompositeScore] = None
    trace: TraceMetadata


class StockOverviewResponse(BaseModel):
    ok: bool = True
    data: StockOverviewData


class StockUniverseData(BaseModel):
    """List of tracked tickers."""
    tickers: List[str]
    count: int


class StockUniverseResponse(BaseModel):
    ok: bool = True
    data: StockUniverseData


# ======================== NEWS (PILIER 3) ========================

class NewsScore(BaseModel):
    """News article scoring."""
    total: float = Field(..., ge=0.0, le=1.0, description="Total score")
    freshness: float = Field(..., ge=0.0, le=1.0, description="Freshness score")
    source_quality: float = Field(..., ge=0.0, le=1.0, description="Source quality score")
    relevance: float = Field(..., ge=0.0, le=1.0, description="Relevance score")


class NewsArticle(BaseModel):
    """Single news article with scoring."""
    id: str
    title: str
    summary: Optional[str] = None
    url: str
    source: str
    published_at: datetime
    tickers: List[str] = Field(default_factory=list)
    score: NewsScore
    trace: TraceMetadata


class NewsFeedFilters(BaseModel):
    """Applied filters for news feed."""
    tickers: Optional[List[str]] = None
    since: str
    score_min: float
    region: str


class NewsFeedData(BaseModel):
    """News feed response data."""
    articles: List[NewsArticle]
    count: int = Field(..., description="Number of articles returned")
    total: Optional[int] = Field(None, description="Total before limit")
    filters: NewsFeedFilters
    trace: TraceMetadata


class NewsFeedResponse(BaseModel):
    ok: bool = True
    data: NewsFeedData


class SentimentData(BaseModel):
    """Aggregated sentiment by ticker."""
    sentiment: Dict[str, float]
    count: int
    trace: TraceMetadata


class SentimentResponse(BaseModel):
    ok: bool = True
    data: SentimentData


# ======================== COPILOT (PILIER 4) ========================

class CopilotAskRequest(BaseModel):
    """Request for LLM copilot."""
    question: str = Field(..., min_length=1, description="Question for the LLM")
    context_years: int = Field(5, ge=1, le=10, description="Years of context (RAG)")
    max_sources: int = Field(10, ge=1, le=20, description="Max sources to cite")
    tickers: Optional[List[str]] = Field(None, description="Specific tickers for context")


class SourceType(str, Enum):
    MACRO = "macro"
    NEWS = "news"
    PRICE = "price"
    FUNDAMENTAL = "fundamental"


class CopilotSource(BaseModel):
    """Source citation."""
    type: SourceType
    content: str = Field(..., description="Relevant excerpt")
    date: date
    url: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)


class CopilotAskData(BaseModel):
    """LLM response with sources."""
    answer: str
    sources: List[CopilotSource]
    confidence: float = Field(..., ge=0.0, le=1.0)
    warnings: Optional[List[str]] = Field(None, description="Limitations or caveats")
    trace: TraceMetadata


class CopilotAskResponse(BaseModel):
    ok: bool = True
    data: CopilotAskData


# ======================== BRIEF (PILIER 5) ========================

class BriefSection(BaseModel):
    """Section of market brief."""
    title: str
    content: str
    signals: Optional[List[str]] = None
    risks: Optional[List[str]] = None


class BriefData(BaseModel):
    """Market brief response."""
    title: str
    date: date
    period: Literal["daily", "weekly"]
    sections: List[BriefSection]
    composite_scores: Optional[Dict[str, CompositeScore]] = None
    trace: TraceMetadata


class BriefResponse(BaseModel):
    ok: bool = True
    data: BriefData


# ======================== SIGNALS ========================

class TopSignal(BaseModel):
    """Top signal or risk."""
    ticker: Optional[str] = None
    type: Literal["signal", "risk"]
    category: Literal["macro", "technical", "news"]
    strength: float = Field(..., ge=0.0, le=1.0)
    message: str
    details: Optional[str] = None


class SignalsData(BaseModel):
    """Top 3 signals and top 3 risks."""
    signals: List[TopSignal] = Field(..., max_length=3)
    risks: List[TopSignal] = Field(..., max_length=3)
    scoring_weights: Dict[str, float] = Field(
        default={"macro": 0.4, "technical": 0.4, "news": 0.2}
    )
    trace: TraceMetadata


class SignalsResponse(BaseModel):
    ok: bool = True
    data: SignalsData


# ======================== ERROR ========================

class ErrorResponse(BaseModel):
    """Error response."""
    ok: bool = False
    error: str
    trace: Optional[TraceMetadata] = None
