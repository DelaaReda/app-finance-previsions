# News Data Infrastructure

## Overview

The current news pipeline delivers an end-to-end Bronze → Silver → Gold lakehouse
flow implemented in real code under `src/ingestion/`.  It ingests curated
finance RSS feeds, normalises raw articles, enriches them with lightweight NLP
signals, and produces ticker-level daily aggregates ready for analytics or API
consumption.  The orchestration and smoke-validation scripts live under
`scripts/` and can be executed locally with the project virtual environment.

### Core Capabilities (October 2025)
- **Bronze ingestion**: fetches RSS/Atom feeds, canonicalises URLs, stores raw
  metadata and optional HTML snapshots as Parquet partitions by date.
- **Silver enrichment**: extracts readable text, deduplicates by content hash,
  applies language detection, heuristic ticker extraction, sector/event tagging
  via `taxonomy.news_taxonomy`, and sentiment scoring through
  `vaderSentiment` (with keyword fallback).
- **Gold aggregation**: groups Silver articles by ticker/date to compute daily
  counts and sentiment/quality aggregates for dashboards and modelling.
- **Idempotent orchestration**: the CLI orchestrator can re-run any date window
  safely, regenerating partitions without manual cleanup.
- **Validation tooling**: a dedicated script asserts schema presence for each
  layer and optionally triggers a full ingest before running checks.

> **Note**
> Earlier prototype files live under `src/data/bronze_pipeline.py`,
> `src/data/silver_pipeline.py`, and `src/data/gold_features_pipeline.py`.
> They were documentation stubs and are not used by the active pipeline.
  All new development should target `src/ingestion/`.

## Data Layers & Schemas

All schema definitions originate from `src/ingestion/news_schemas.py` where they
are expressed as dataclasses and (optionally) PyArrow schemas.

### Bronze (raw ingestion)
**Location:** `data/news/bronze/dt=YYYY-MM-DD/news_bronze_*.parquet`

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | SHA256 of canonical URL, title and published timestamp |
| `url` | string | Original entry link |
| `canonical_url` | string | Tracking-free lowercased URL |
| `source_domain` | string | Domain component of canonical URL |
| `source_name` | string? | Feed-supplied source name if present |
| `region` | string? | Region bucket (US, CA, FR, DE, INTL, GEO...) |
| `lang_detected` | string? | ISO 639-1 language hint |
| `published_at` | timestamp (UTC) | Article publish time |
| `crawled_at` | timestamp (UTC) | Ingestion timestamp |
| `title` | string? | Feed title |
| `summary` | string? | Feed summary/description |
| `raw_html` | string? | Optional HTML snapshot (if `fetch_html` enabled) |
| `license_hint` | string? | Currently fixed to `rss` |
| `paywall` | bool? | Reserved slot (currently `None`) |
| `status_code` | int? | Reserved slot for crawl status |

### Silver (clean + enriched)
**Location:** `data/news/silver/dt=YYYY-MM-DD/news_silver_*.parquet`

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Carries Bronze identifier |
| `canonical_url` | string | Canonical URL |
| `source_domain` | string | Domain |
| `source_name` | string? | Source label |
| `region` | string? | Region bucket |
| `lang` | string? | Language detected from text |
| `published_at` | timestamp (UTC) | Publish time |
| `crawled_at` | timestamp (UTC) | Crawl time |
| `title` | string? | Article title |
| `summary` | string? | Feed summary |
| `text` | string? | Cleaned body text (BeautifulSoup extraction) |
| `hash_text` | string? | SHA256 hash of cleaned text for dedup |
| `tickers` | list[str] | Uppercase ticker candidates |
| `sectors` | list[str] | Sector tags (taxonomy-based) |
| `events` | list[str] | Event tags (earnings, mna, etc.) |
| `geopolitics` | list[str] | Geopolitical keyword hits |
| `sentiment` | float? | VADER compound score (−1→1) |
| `quality` | float? | Simple length-based heuristic (0→1) |

### Gold (daily aggregations)
**Location:** `data/news/gold/features_daily/dt=YYYY-MM-DD/features.parquet`

| Field | Type | Description |
|-------|------|-------------|
| `date` | date | Trading day |
| `ticker` | string | Ticker symbol |
| `article_count` | int | Count of Silver articles |
| `positive_count` | int | Sentiment ≥ +0.15 |
| `negative_count` | int | Sentiment ≤ −0.15 |
| `neutral_count` | int | Sentiment between thresholds |
| `avg_sentiment` | float? | Mean sentiment |
| `quality_avg` | float? | Mean quality score |
| `sectors` | list[str] | Aggregated sector tags |
| `events` | list[str] | Aggregated event tags |
| `geopolitics` | list[str] | Aggregated geopolitics tags |

## Pipeline Workflow

```
RSS/Atom Feeds (SOURCES in ingestion.finnews)
        ↓
[BRONZE] ingest_bronze_for_date()
    • fetch + canonicalise + store raw metadata/HTML
        ↓
[SILVER] transform_to_silver()
    • clean text, dedupe by hash, tag tickers/sectors/events, score sentiment
        ↓
[GOLD] build_daily_features()
    • aggregate by (date, ticker) and compute sentiment counts
```

Each stage writes Parquet partitions that downstream services (FastAPI, DuckDB,
Dash apps) can consume directly.  Rerunning a date will append new files under
the same partition folder; consumers should `read_parquet()` with globbing.

## Running the Pipeline

All commands below assume the local virtual environment located at `.venv`.

```bash
# Install dependencies once
.venv/bin/python -m pip install pandas feedparser requests langdetect \
    beautifulsoup4 vaderSentiment duckdb

# Run Bronze → Silver → Gold for a single date
.venv/bin/python scripts/news_orchestrator.py --date 2025-10-30 --regions US

# Useful flags
#   --no-html        skip HTML fetch (faster)
#   --backfill 7d    run the past 7 days
#   --skip-gold      stop after Silver if you only need articles
```

The orchestrator prints the target files after each stage.  All stages are safe
to re-run.

## Validation

```bash
# Validate an existing partition
.venv/bin/python scripts/validate_news_infrastructure.py --date 2025-10-30

# Trigger ingestion + validation in a single command
.venv/bin/python scripts/validate_news_infrastructure.py --date 2025-10-30 --ingest --regions US
```

Validation asserts that required Parquet files exist and that mandatory columns
(`id`, `canonical_url`, etc.) are present.  It fails fast when schemas drift or
when deduplication accidentally drops required fields.

## Data Layout Reference

```
data/news/
  bronze/
    dt=2025-10-30/
      news_bronze_025447.parquet
  silver/
    dt=2025-10-30/
      news_silver_025447.parquet
  gold/
    features_daily/
      dt=2025-10-30/
        features.parquet
```

Each rerun will create new timestamped files (keeping historical snapshots).
Clean-up scripts or compaction jobs can be added later if needed.

## Next Steps

1. **API wiring**: extend `src/api/services/news_service.py` to read the new
   Parquet outputs (Silver + Gold) instead of the previous JSONL placeholders.
2. **Enhanced deduplication**: add near-duplicate detection (e.g., SimHash) to
   reduce repeated wire stories.
3. **Embeddings layer**: persist vector representations under
   `data/news/gold/embeddings/` for RAG workloads.
4. **Quality signals**: upgrade the current length-based quality heuristic with
   more robust scoring or model-assisted evaluation.
5. **Archival / compaction**: optionally merge per-run Parquet files into daily
   consolidated outputs once the pipeline stabilises.

This document will continue to evolve as new capabilities land.  When adding a
feature, update the corresponding schema in `news_schemas.py` and mirror the
change here so downstream consumers have a single source of truth.
