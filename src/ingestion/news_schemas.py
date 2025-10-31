"""Structured schema definitions for the news lakehouse pipeline.

The schemas are expressed as dataclass containers so the pipeline can use them
without depending on heavy tooling.  When :mod:`pyarrow` is available we also
expose helpers to obtain Arrow schemas that mirror the Python definitions.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

try:  # Optional dependency when writing Parquet with Arrow
    import pyarrow as pa
except Exception:  # pragma: no cover - pyarrow is optional at runtime
    pa = None  # type: ignore


# ---------------------------------------------------------------------------
# Bronze (raw ingestion)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class BronzeRecord:
    """Minimal immutable snapshot of a raw RSS article."""

    id: str
    url: str
    canonical_url: str
    source_domain: str
    source_name: Optional[str]
    region: Optional[str]
    lang_detected: Optional[str]
    published_at: datetime
    crawled_at: datetime
    title: Optional[str]
    summary: Optional[str]
    raw_html: Optional[str] = None
    license_hint: Optional[str] = None
    paywall: Optional[bool] = None
    status_code: Optional[int] = None


BRONZE_FIELDS: List[tuple[str, str]] = [
    ("id", "string"),
    ("url", "string"),
    ("canonical_url", "string"),
    ("source_domain", "string"),
    ("source_name", "string"),
    ("region", "string"),
    ("lang_detected", "string"),
    ("published_at", "timestamp[us, tz=UTC]"),
    ("crawled_at", "timestamp[us, tz=UTC]"),
    ("title", "string"),
    ("summary", "string"),
    ("raw_html", "string"),
    ("license_hint", "string"),
    ("paywall", "bool"),
    ("status_code", "int32"),
]


# ---------------------------------------------------------------------------
# Silver (clean text + enrichment)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SilverRecord:
    """Cleaned and enriched representation of an article."""

    id: str
    canonical_url: str
    source_domain: str
    source_name: Optional[str]
    region: Optional[str]
    lang: Optional[str]
    published_at: datetime
    crawled_at: datetime
    title: Optional[str]
    summary: Optional[str]
    text: Optional[str]
    hash_text: Optional[str]
    tickers: List[str] = field(default_factory=list)
    sectors: List[str] = field(default_factory=list)
    events: List[str] = field(default_factory=list)
    geopolitics: List[str] = field(default_factory=list)
    sentiment: Optional[float] = None
    quality: Optional[float] = None


SILVER_FIELDS: List[tuple[str, str]] = [
    ("id", "string"),
    ("canonical_url", "string"),
    ("source_domain", "string"),
    ("source_name", "string"),
    ("region", "string"),
    ("lang", "string"),
    ("published_at", "timestamp[us, tz=UTC]"),
    ("crawled_at", "timestamp[us, tz=UTC]"),
    ("title", "string"),
    ("summary", "string"),
    ("text", "string"),
    ("hash_text", "string"),
    ("tickers", "list[string]"),
    ("sectors", "list[string]"),
    ("events", "list[string]"),
    ("geopolitics", "list[string]"),
    ("sentiment", "float64"),
    ("quality", "float64"),
]


# ---------------------------------------------------------------------------
# Gold (daily ticker features)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class GoldDailyFeatures:
    """Aggregated features per ticker and date."""

    date: datetime
    ticker: str
    article_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    avg_sentiment: Optional[float]
    quality_avg: Optional[float]
    sectors: List[str] = field(default_factory=list)
    events: List[str] = field(default_factory=list)
    geopolitics: List[str] = field(default_factory=list)


GOLD_FIELDS: List[tuple[str, str]] = [
    ("date", "date32"),
    ("ticker", "string"),
    ("article_count", "int32"),
    ("positive_count", "int32"),
    ("negative_count", "int32"),
    ("neutral_count", "int32"),
    ("avg_sentiment", "float64"),
    ("quality_avg", "float64"),
    ("sectors", "list[string]"),
    ("events", "list[string]"),
    ("geopolitics", "list[string]"),
]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def asdict_recursive(record: Any) -> Dict[str, Any]:
    """Convert dataclasses (possibly containing lists) to plain dicts."""

    if hasattr(record, "__dataclass_fields__"):
        result = {}
        for key, value in asdict(record).items():
            result[key] = asdict_recursive(value)
        return result
    if isinstance(record, list):
        return [asdict_recursive(v) for v in record]
    return record


def _to_arrow_type(decl: str) -> "pa.DataType":  # pragma: no cover - trivial
    if pa is None:
        raise RuntimeError("pyarrow is not available")
    if decl.startswith("list[") and decl.endswith("]"):
        inner = decl[5:-1]
        return pa.list_(_to_arrow_type(inner))
    if decl.startswith("timestamp"):
        tz = "UTC" if "tz=UTC" in decl else None
        return pa.timestamp("us", tz=tz)
    if decl == "date32":
        return pa.date32()
    return getattr(pa, decl)()


def bronze_arrow_schema() -> "pa.Schema":
    if pa is None:
        raise RuntimeError("pyarrow is required for Arrow schemas")
    return pa.schema([pa.field(name, _to_arrow_type(dtype)) for name, dtype in BRONZE_FIELDS])


def silver_arrow_schema() -> "pa.Schema":
    if pa is None:
        raise RuntimeError("pyarrow is required for Arrow schemas")
    return pa.schema([pa.field(name, _to_arrow_type(dtype)) for name, dtype in SILVER_FIELDS])


def gold_arrow_schema() -> "pa.Schema":
    if pa is None:
        raise RuntimeError("pyarrow is required for Arrow schemas")
    return pa.schema([pa.field(name, _to_arrow_type(dtype)) for name, dtype in GOLD_FIELDS])


__all__ = [
    "BronzeRecord",
    "SilverRecord",
    "GoldDailyFeatures",
    "BRONZE_FIELDS",
    "SILVER_FIELDS",
    "GOLD_FIELDS",
    "asdict_recursive",
    "bronze_arrow_schema",
    "silver_arrow_schema",
    "gold_arrow_schema",
]
