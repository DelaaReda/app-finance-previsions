#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
News Data Schemas (Bronze/Silver/Gold/Embeddings)
PyArrow schemas for 5+ year lakehouse-style storage with DuckDB.

Author: AI Assistant
Created: 2025-10-30
"""

import pyarrow as pa
from typing import Dict

# =======================
# Bronze Schema (Raw/Immutable)
# =======================

BRONZE_SCHEMA = pa.schema([
    # Primary key
    pa.field("id", pa.string(), nullable=False),  # hash(canonical_url|published_at|title_norm)
    
    # Source metadata
    pa.field("url", pa.string(), nullable=False),
    pa.field("canonical_url", pa.string(), nullable=False),
    pa.field("source_domain", pa.string(), nullable=False),  # e.g., wsj.com
    pa.field("source_name", pa.string(), nullable=True),  # e.g., The Wall Street Journal
    
    # Content
    pa.field("lang_detected", pa.string(), nullable=True),  # ISO 639-1 code
    pa.field("published_at", pa.timestamp("us", tz="UTC"), nullable=False),
    pa.field("crawled_at", pa.timestamp("us", tz="UTC"), nullable=False),
    pa.field("region", pa.string(), nullable=True),  # US/CA/EU/INTL
    pa.field("paywall", pa.bool_(), nullable=True),
    pa.field("status_code", pa.int32(), nullable=True),
    
    # Raw HTML (compressed in Parquet with Zstd)
    pa.field("raw_html", pa.string(), nullable=True),
    
    # Licensing
    pa.field("license_hint", pa.string(), nullable=True),  # rss/publisher_terms/unknown
    
    # Versioning
    pa.field("schema_version", pa.int32(), nullable=False),  # v1
])

# =======================
# Silver Schema (Clean & Enriched)
# =======================

# Struct types for complex fields
SENTIMENT_STRUCT = pa.struct([
    pa.field("polarity", pa.float32()),  # -1.0 to 1.0
    pa.field("subjectivity", pa.float32()),  # 0.0 to 1.0
])

QUALITY_STRUCT = pa.struct([
    pa.field("credibility", pa.float32()),  # 0.0 to 1.0
    pa.field("completeness", pa.float32()),  # 0.0 to 1.0
    pa.field("noise", pa.float32()),  # 0.0 to 1.0 (lower is better)
])

ENTITY_STRUCT = pa.struct([
    pa.field("type", pa.string()),  # PERSON/ORG/LOCATION/TICKER/etc
    pa.field("value", pa.string()),
    pa.field("score", pa.float32()),  # confidence
])

SILVER_SCHEMA = pa.schema([
    # Inherited from Bronze
    pa.field("id", pa.string(), nullable=False),
    pa.field("url", pa.string(), nullable=False),
    pa.field("source_domain", pa.string(), nullable=False),
    pa.field("source_tier", pa.string(), nullable=True),  # Tier1/Tier2
    
    # Normalized content
    pa.field("lang", pa.string(), nullable=False),  # normalized ISO code
    pa.field("published_at", pa.timestamp("us", tz="UTC"), nullable=False),
    pa.field("text", pa.string(), nullable=False),  # cleaned article text
    pa.field("title", pa.string(), nullable=False),
    pa.field("summary", pa.string(), nullable=True),  # LLM/extractive
    pa.field("authors", pa.list_(pa.string()), nullable=True),
    
    # Enrichments
    pa.field("tickers", pa.list_(pa.string()), nullable=True),  # ["AAPL", "MSFT"]
    pa.field("entities", pa.list_(ENTITY_STRUCT), nullable=True),
    pa.field("topics", pa.list_(pa.string()), nullable=True),  # ["earnings", "M&A", "AI"]
    
    # Scores
    pa.field("sentiment", SENTIMENT_STRUCT, nullable=True),
    pa.field("quality", QUALITY_STRUCT, nullable=True),
    pa.field("relevance", pa.float32(), nullable=True),  # for ticker/query matching
    
    # Deduplication
    pa.field("dedup_key", pa.string(), nullable=False),  # hash(title_norm|published_date|source)
    pa.field("simhash", pa.string(), nullable=True),  # fingerprint for near-dup
    pa.field("parent_id", pa.string(), nullable=True),  # id of dominant article in cluster
    
    # Versioning
    pa.field("schema_version", pa.int32(), nullable=False),  # v2
])

# =======================
# Gold - Features Daily (Aggregated by ticker & date)
# =======================

FEATURES_DAILY_SCHEMA = pa.schema([
    # Dimensions
    pa.field("date", pa.date32(), nullable=False),
    pa.field("ticker", pa.string(), nullable=False),
    
    # Volume metrics
    pa.field("news_count", pa.int32(), nullable=False),
    pa.field("news_novelty", pa.float32(), nullable=True),  # fraction of non-duplicates
    
    # Sentiment aggregates
    pa.field("sent_mean", pa.float32(), nullable=True),
    pa.field("sent_pos_share", pa.float32(), nullable=True),
    pa.field("sent_neg_share", pa.float32(), nullable=True),
    
    # Topics
    pa.field("top_topics", pa.list_(pa.string()), nullable=True),
    
    # Source quality
    pa.field("source_tier1_share", pa.float32(), nullable=True),
    
    # Intensity (if intraday available)
    pa.field("intraday_intensity", pa.float32(), nullable=True),
    
    # Versioning
    pa.field("features_version", pa.int32(), nullable=False),  # v1
])

# =======================
# Gold - Events (Structured events extracted from news)
# =======================

EVENTS_SCHEMA = pa.schema([
    # Primary key
    pa.field("event_id", pa.string(), nullable=False),  # hash(type|ticker|date|source)
    
    # Event type
    pa.field("event_type", pa.string(), nullable=False),  # earnings/guidance/M&A/regulatory/product
    
    # Associated entities
    pa.field("tickers", pa.list_(pa.string()), nullable=False),
    pa.field("company_name", pa.string(), nullable=True),
    pa.field("event_date", pa.date32(), nullable=False),
    
    # Values (flexible map for numeric data)
    pa.field("values", pa.map_(pa.string(), pa.float64()), nullable=True),  # {"eps": 2.11, "rev": 134.8e9}
    pa.field("qualifiers", pa.list_(pa.string()), nullable=True),  # ["beat", "miss", "investigation"]
    
    # Provenance
    pa.field("source_id", pa.string(), nullable=False),  # link to news.id
    pa.field("confidence", pa.float32(), nullable=True),
    pa.field("extracted_at", pa.timestamp("us", tz="UTC"), nullable=False),
    
    # Versioning
    pa.field("schema_version", pa.int32(), nullable=False),
])

# =======================
# Embeddings (for RAG/ML)
# =======================

EMBEDDINGS_SCHEMA = pa.schema([
    # Primary key (composite)
    pa.field("id", pa.string(), nullable=False),  # news_id + chunk_idx
    pa.field("news_id", pa.string(), nullable=False),
    pa.field("chunk_idx", pa.int32(), nullable=False),
    
    # Content
    pa.field("text_chunk", pa.string(), nullable=False),
    pa.field("embedding", pa.list_(pa.float32()), nullable=False),  # dim=768/1024
    
    # Metadata for filtering
    pa.field("lang", pa.string(), nullable=False),
    pa.field("tickers", pa.list_(pa.string()), nullable=True),
    pa.field("published_at", pa.timestamp("us", tz="UTC"), nullable=False),
    
    # Versioning
    pa.field("embedding_version", pa.int32(), nullable=False),  # v1, v2, ...
])

# =======================
# Helper: Source Tier Mapping
# =======================

SOURCE_TIERS: Dict[str, str] = {
    # Tier1: High-credibility financial sources
    "wsj.com": "Tier1",
    "ft.com": "Tier1",
    "reuters.com": "Tier1",
    "bloomberg.com": "Tier1",
    "economist.com": "Tier1",
    "cnbc.com": "Tier1",
    "marketwatch.com": "Tier1",
    "investing.com": "Tier1",
    "lesechos.fr": "Tier1",
    "handelsblatt.com": "Tier1",
    "globeandmail.com": "Tier1",
    "bnnbloomberg.ca": "Tier1",
    
    # Tier2: Reputable but lower priority
    "seekingalpha.com": "Tier2",
    "fool.com": "Tier2",
    "benzinga.com": "Tier2",
    "business-standard.com": "Tier2",
}

def get_source_tier(domain: str) -> str:
    """Get source tier from domain, default to Tier2."""
    return SOURCE_TIERS.get(domain.lower(), "Tier2")


# =======================
# Helper: Schema Version Constants
# =======================

SCHEMA_VERSIONS = {
    "bronze": 1,
    "silver": 2,
    "features_daily": 1,
    "events": 1,
    "embeddings": 1,
}


if __name__ == "__main__":
    # Print schemas for verification
    print("=== BRONZE SCHEMA ===")
    print(BRONZE_SCHEMA)
    print("\n=== SILVER SCHEMA ===")
    print(SILVER_SCHEMA)
    print("\n=== FEATURES_DAILY SCHEMA ===")
    print(FEATURES_DAILY_SCHEMA)
    print("\n=== EVENTS SCHEMA ===")
    print(EVENTS_SCHEMA)
    print("\n=== EMBEDDINGS SCHEMA ===")
    print(EMBEDDINGS_SCHEMA)
