# News Data Infrastructure (5+ Years)

## 🎯 Overview

A complete **lakehouse-style data pipeline** for financial news that supports:
- ✅ **5+ years historical data** with idempotent ingestion
- ✅ **Bronze/Silver/Gold architecture** for clean data lineage
- ✅ **Deduplication** (exact + near-dup with SimHash)
- ✅ **NER, sentiment, quality scoring** for every article
- ✅ **Daily ticker-level features** for ML/analytics
- ✅ **Fast queries** with DuckDB + Parquet (Zstd compression)
- ✅ **RAG-ready** embeddings layer (coming soon)

## 📊 Data Layers

### Bronze (Raw/Immutable)
**Location:** `data/news/bronze/source=<domain>/dt=YYYY-MM-DD/*.parquet`

Raw article HTML + metadata from RSS/Atom feeds. Append-only, never modified.

**Schema:**
```
id                 STRING (hash of canonical_url|date|title)
url                STRING
canonical_url      STRING (normalized, no tracking params)
source_domain      STRING (e.g., wsj.com)
lang_detected      STRING (ISO 639-1)
published_at       TIMESTAMP (UTC)
crawled_at         TIMESTAMP (UTC)
region             STRING (US/CA/EU/INTL)
paywall            BOOLEAN
raw_html           STRING (Zstd compressed)
schema_version     INT (v1)
```

### Silver (Clean & Enriched)
**Location:** `data/news/silver/dt=YYYY-MM-DD/*.parquet`

Cleaned text + NER + sentiment + topics + deduplication.

**Schema:**
```
id                 STRING
title              STRING
text               STRING (cleaned, readability-extracted)
url                STRING
source_domain      STRING
source_tier        STRING (Tier1/Tier2 based on credibility)
lang               STRING
published_at       TIMESTAMP (UTC)
tickers            ARRAY<STRING> (e.g., ["AAPL", "MSFT"])
entities           ARRAY<STRUCT<type, value, score>>
topics             ARRAY<STRING> (e.g., ["earnings", "M&A"])
sentiment          STRUCT<polarity FLOAT, subjectivity FLOAT>
quality            STRUCT<credibility, completeness, noise>
relevance          FLOAT
dedup_key          STRING (hash for exact duplicate detection)
simhash            STRING (fingerprint for near-dup)
parent_id          STRING (ID of original if duplicate)
schema_version     INT (v2)
```

### Gold - Features Daily
**Location:** `data/news/gold/features_daily/dt=YYYY-MM-DD/final.parquet`

Aggregated daily features per ticker for ML models.

**Schema:**
```
date                   DATE
ticker                 STRING
news_count             INT
news_novelty           FLOAT (fraction non-duplicates)
sent_mean              FLOAT (avg sentiment)
sent_pos_share         FLOAT
sent_neg_share         FLOAT
top_topics             ARRAY<STRING>
source_tier1_share     FLOAT
features_version       INT (v1)
```

### Gold - Events (Coming Soon)
**Location:** `data/news/gold/events/dt=YYYY-MM-DD/final.parquet`

Structured events extracted from news (earnings, M&A, regulatory).

### Embeddings (Coming Soon)
**Location:** `data/news/gold/embeddings/version=vN/dt=YYYY-MM-DD/*.parquet`

Vector embeddings for RAG/semantic search.

## 🔄 Pipeline Workflow

```
RSS/Atom Feeds
     ↓
[BRONZE] Raw Ingestion
  • Fetch feeds
  • Canonicalize URLs
  • Detect language/paywall
  • Store raw HTML
     ↓
[SILVER] Clean & Enrich
  • Extract clean text (readability)
  • Deduplicate (exact + SimHash)
  • NER & ticker mapping
  • Topic classification
  • Sentiment analysis
  • Quality scoring
     ↓
[GOLD] Aggregate Features
  • Group by (date, ticker)
  • Compute daily features
  • Store for ML/analytics
     ↓
[API] FastAPI Service
  • Query feed (/news/feed)
  • Get features (/news/features/daily)
  • RAG search (coming)
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install pyarrow pandas duckdb feedparser requests beautifulsoup4 langdetect vaderSentiment
```

### 2. Run Pipeline for Today

```bash
# Full pipeline (Bronze -> Silver -> Gold)
python scripts/news_orchestrator.py --today

# Specific regions only
python scripts/news_orchestrator.py --today --regions US,CA

# Skip Bronze (if already ingested)
python scripts/news_orchestrator.py --today --skip-bronze
```

### 3. Backfill Historical Data

```bash
# Last 7 days
python scripts/news_orchestrator.py --backfill 7d

# Last 3 months
python scripts/news_orchestrator.py --backfill 3m

# Last 5 years
python scripts/news_orchestrator.py --backfill 5y
```

### 4. Run Specific Date

```bash
python scripts/news_orchestrator.py --date 2025-10-30
```

### 5. Run Date Range

```bash
python scripts/news_orchestrator.py --start-date 2025-10-01 --end-date 2025-10-30
```

## 📡 API Usage

### Start API Server

```bash
# (Assuming FastAPI is already integrated in main.py)
cd /Users/venom/Documents/analyse-financiere
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8050 --reload
```

### Query News Feed

```bash
# Get recent news for AAPL
curl "http://localhost:8050/api/news/feed?tickers=AAPL&limit=10"

# Filter by date range
curl "http://localhost:8050/api/news/feed?start_date=2025-10-25&end_date=2025-10-30"

# Filter by topics
curl "http://localhost:8050/api/news/feed?topics=earnings,M&A"

# Filter by source tier (Tier1 only)
curl "http://localhost:8050/api/news/feed?source_tier=Tier1"
```

### Query Daily Features

```bash
# Get features for AAPL
curl "http://localhost:8050/api/news/features/daily?ticker=AAPL&start_date=2025-10-01"

# Get all tickers with min 5 news articles
curl "http://localhost:8050/api/news/features/daily?min_news_count=5"
```

### Get Statistics

```bash
curl "http://localhost:8050/api/news/stats"
```

## 🔧 Configuration

### RSS Feed Sources

Edit `scripts/news_orchestrator.py` to add/remove feeds:

```python
FEED_SOURCES = {
    "US": [
        ("https://www.cnbc.com/id/10001147/device/rss/rss.html", "US"),
        ("https://www.marketwatch.com/rss/topstories", "US"),
        # Add more...
    ],
    "CA": [...],
    "FR": [...],
}
```

### Source Tier Mapping

Edit `src/ingestion/news_schemas.py`:

```python
SOURCE_TIERS = {
    "wsj.com": "Tier1",
    "ft.com": "Tier1",
    "reuters.com": "Tier1",
    # Add more...
}
```

### Topic Keywords

Edit `src/ingestion/silver_pipeline.py`:

```python
TOPIC_KEYWORDS = {
    "earnings": ["earnings", "EPS", "guidance", "revenue"],
    "M&A": ["merger", "acquisition", "takeover"],
    # Add more...
}
```

## 🧪 Testing

### Test Bronze Ingestion

```bash
python -c "
from src.ingestion.bronze_pipeline import ingest_to_bronze
count = ingest_to_bronze(
    feed_url='https://www.cnbc.com/id/10001147/device/rss/rss.html',
    region='US',
    max_items=10,
    dry_run=True
)
print(f'Would ingest {count} articles')
"
```

### Test Silver Processing

```bash
python -c "
from src.ingestion.silver_pipeline import process_bronze_to_silver
count = process_bronze_to_silver('2025-10-30', dry_run=True)
print(f'Would process {count} articles')
"
```

### Test Gold Features

```bash
python -c "
from src.ingestion.gold_features_pipeline import compute_daily_features
count = compute_daily_features('2025-10-30', dry_run=True)
print(f'Would compute {count} ticker-features')
"
```

### Test API Service

```bash
python src/api/services/news_service.py
```

## 📊 DuckDB Queries

### Query Silver Directly

```python
import duckdb

conn = duckdb.connect(":memory:")

# Get recent news for AAPL
df = conn.execute("""
SELECT title, published_at, sentiment, topics
FROM read_parquet('data/news/silver/dt=*/articles_*.parquet')
WHERE list_contains(tickers, 'AAPL')
  AND published_at >= '2025-10-01'
ORDER BY published_at DESC
LIMIT 10
""").df()

print(df)
```

### Query Gold Features

```python
import duckdb

conn = duckdb.connect(":memory:")

# Get features for AAPL over time
df = conn.execute("""
SELECT date, news_count, sent_mean, top_topics
FROM read_parquet('data/news/gold/features_daily/dt=*/final.parquet')
WHERE ticker = 'AAPL'
ORDER BY date DESC
""").df()

print(df)
```

### Aggregate Statistics

```python
# News volume by source tier
df = conn.execute("""
SELECT source_tier, COUNT(*) as article_count
FROM read_parquet('data/news/silver/dt=2025-10-30/*.parquet')
GROUP BY source_tier
ORDER BY article_count DESC
""").df()

# Top tickers by article count
df = conn.execute("""
SELECT unnest(tickers) as ticker, COUNT(*) as article_count
FROM read_parquet('data/news/silver/dt=2025-10-*/articles_*.parquet')
GROUP BY ticker
ORDER BY article_count DESC
LIMIT 10
""").df()
```

## 🎯 Performance

### Storage Efficiency
- **Compression:** Zstd level 6-9 (50-70% reduction)
- **Dictionary encoding:** Enabled for repeated strings
- **Partitioning:** By date for fast range queries

### Query Speed
- **DuckDB:** Parallelized Parquet scanning
- **Typical queries:** <1s for single day, <5s for 30 days
- **Full table scan (5 years):** ~30-60s depending on size

### Deduplication
- **Exact duplicates:** O(n) with hash-based detection
- **Near-duplicates:** O(n²) with SimHash (threshold=3 bits)
- **Typical near-dup rate:** 10-20% depending on sources

## 🔮 Roadmap

### Phase 1: Core Infrastructure ✅
- [x] Bronze/Silver/Gold pipelines
- [x] Deduplication (exact + near-dup)
- [x] NER & ticker mapping
- [x] Sentiment & quality scoring
- [x] Daily features aggregation
- [x] FastAPI service
- [x] Orchestrator script

### Phase 2: Enrichment (Next)
- [ ] Embeddings pipeline (OpenAI/Cohere)
- [ ] Hybrid search (BM25 + vector)
- [ ] Event extraction (earnings, M&A, regulatory)
- [ ] Summarization (LLM-based)
- [ ] Enhanced NER (spaCy/Flair)

### Phase 3: Advanced Features
- [ ] Real-time ingestion (WebSocket/streaming)
- [ ] Alerting system (ticker mentions, sentiment spikes)
- [ ] Topic modeling (LDA/BERTopic)
- [ ] Entity resolution (company aliases)
- [ ] Cross-lingual search

### Phase 4: ML Integration
- [ ] Feature engineering for alpha models
- [ ] Backtest framework (news → returns)
- [ ] Nowcasting models (GDP, earnings)
- [ ] Regime detection (news-driven)

## 📚 References

### Schemas
- `src/ingestion/news_schemas.py` - PyArrow schemas for all layers

### Pipelines
- `src/ingestion/bronze_pipeline.py` - Raw ingestion
- `src/ingestion/silver_pipeline.py` - Clean & enrich
- `src/ingestion/gold_features_pipeline.py` - Daily features

### Services
- `src/api/services/news_service.py` - FastAPI service

### Scripts
- `scripts/news_orchestrator.py` - Pipeline orchestrator

## 🆘 Troubleshooting

### Issue: "No Bronze records found"
**Solution:** Check that Bronze ingestion completed successfully. Run with `--today` first.

### Issue: "DuckDB permission denied"
**Solution:** Close any open DuckDB connections. Delete `.duckdb` lock files if present.

### Issue: "Feed parsing failed"
**Solution:** Check internet connectivity. Some feeds may be rate-limited or temporarily down.

### Issue: "Duplicate articles"
**Solution:** Deduplication runs in Silver pipeline. Check `parent_id` field to see which articles are marked as duplicates.

### Issue: "Missing tickers"
**Solution:** Ticker mapping is heuristic-based. Extend the company→ticker map in `silver_pipeline.py`.

## 📝 License

Internal use only. See main project LICENSE.

---

**Questions?** Check the main project documentation or contact the team.
