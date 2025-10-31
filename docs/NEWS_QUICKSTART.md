# News Infrastructure - Quick Start Guide

## 🎯 What You Just Got

A complete **lakehouse data infrastructure** for financial news with:

- ✅ **3-layer architecture** (Bronze/Silver/Gold)
- ✅ **Idempotent pipelines** (safe to re-run)
- ✅ **Deduplication** (exact + near-dup)
- ✅ **Rich enrichments** (NER, sentiment, topics, quality)
- ✅ **ML-ready features** (daily ticker-level aggregates)
- ✅ **Fast API** (DuckDB + Parquet for sub-second queries)

## 📁 What Was Created

```
src/ingestion/
├── news_schemas.py           ← PyArrow schemas for all layers
├── bronze_pipeline.py         ← Raw RSS ingestion
├── silver_pipeline.py         ← Clean + enrich
└── gold_features_pipeline.py  ← Daily ticker features

src/api/services/
└── news_service.py           ← FastAPI service (feed, features, stats)

scripts/
└── news_orchestrator.py      ← Run full pipeline end-to-end

docs/
└── NEWS_INFRASTRUCTURE.md    ← Complete documentation
```

## ⚡ 5-Minute Test Drive

### 1. Run Pipeline for Today

```bash
cd /Users/venom/Documents/analyse-financiere

# Full pipeline (Bronze → Silver → Gold)
python scripts/news_orchestrator.py --today
```

**What happens:**
1. Fetches RSS feeds from 10+ sources (CNBC, Reuters, WSJ, etc.)
2. Stores raw HTML in `data/news/bronze/`
3. Extracts clean text, entities, sentiment
4. Computes daily features per ticker
5. Writes to `data/news/silver/` and `data/news/gold/`

**Expected output:**
```
BRONZE INGESTION - 2025-10-30
--- US (4 feeds) ---
  ✓ https://www.cnbc.com/...rss.html: 25 articles
  ✓ https://www.marketwatch.com/rss/topstories: 30 articles
...
BRONZE TOTAL: 120 articles

SILVER PROCESSING - 2025-10-30
Found 3 near-duplicates
✓ Wrote 117 records to data/news/silver/dt=2025-10-30/articles_123456.parquet

GOLD FEATURES - 2025-10-30
Found 45 unique tickers
✓ Computed features for 45 tickers
```

### 2. Query the Data

```python
import duckdb

conn = duckdb.connect(":memory:")

# Get AAPL news from today
df = conn.execute("""
SELECT title, published_at, sentiment, topics
FROM read_parquet('data/news/silver/dt=2025-10-30/*.parquet')
WHERE list_contains(tickers, 'AAPL')
LIMIT 5
""").df()

print(df)
```

### 3. Use the Service

```python
from src.api.services.news_service import get_news_service

service = get_news_service()

# Get news feed
articles = service.get_feed(
    tickers=["AAPL", "MSFT"],
    start_date="2025-10-30",
    limit=10
)

for article in articles:
    print(f"{article.title} - {article.source_domain}")

# Get daily features
features = service.get_daily_features(
    ticker="AAPL",
    start_date="2025-10-30"
)

for feat in features:
    print(f"{feat.date}: {feat.news_count} articles, sentiment={feat.sent_mean:.2f}")
```

## 🔄 Common Workflows

### Daily Pipeline (Production)

```bash
# Add to cron for daily runs (e.g., 8 AM every day)
0 8 * * * cd /path/to/project && python scripts/news_orchestrator.py --today
```

### Backfill Historical Data

```bash
# Last week
python scripts/news_orchestrator.py --backfill 7d

# Last month
python scripts/news_orchestrator.py --backfill 1m

# Last year
python scripts/news_orchestrator.py --backfill 1y

# Full 5 years (takes ~2-4 hours depending on feeds)
python scripts/news_orchestrator.py --backfill 5y
```

### Reprocess Existing Data

```bash
# Silver pipeline only (if Bronze already exists)
python scripts/news_orchestrator.py --date 2025-10-30 --skip-bronze

# Gold pipeline only (if Silver exists)
python scripts/news_orchestrator.py --date 2025-10-30 --skip-bronze --skip-silver
```

### Batch Processing

```bash
# Process October 2025
python scripts/news_orchestrator.py --start-date 2025-10-01 --end-date 2025-10-31
```

## 🎨 Customize for Your Needs

### Add More RSS Feeds

Edit `scripts/news_orchestrator.py`:

```python
FEED_SOURCES = {
    "US": [
        ("https://www.cnbc.com/id/10001147/device/rss/rss.html", "US"),
        # Add your feeds here
        ("https://seekingalpha.com/feed.xml", "US"),
    ],
}
```

### Add Ticker Mappings

Edit `src/ingestion/silver_pipeline.py`:

```python
company_ticker_map = {
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    # Add your mappings
    "Your Company": "TICK",
}
```

### Add Topics

Edit `src/ingestion/silver_pipeline.py`:

```python
TOPIC_KEYWORDS = {
    "earnings": ["earnings", "EPS", "guidance"],
    "AI": ["AI", "artificial intelligence", "ChatGPT"],
    # Add your topics
    "crypto": ["bitcoin", "ethereum", "crypto"],
}
```

### Change Source Tiers

Edit `src/ingestion/news_schemas.py`:

```python
SOURCE_TIERS = {
    "wsj.com": "Tier1",
    "reuters.com": "Tier1",
    # Add your sources
    "yourtrustedsource.com": "Tier1",
}
```

## 🔌 Integrate with FastAPI

Add these endpoints to `src/api/main.py`:

```python
from src.api.services.news_service import get_news_service

@app.get("/api/news/feed")
async def get_news_feed(
    tickers: Optional[str] = None,
    topics: Optional[str] = None,
    start_date: Optional[str] = None,
    limit: int = 100
):
    service = get_news_service()
    
    ticker_list = tickers.split(",") if tickers else None
    topic_list = topics.split(",") if topics else None
    
    articles = service.get_feed(
        tickers=ticker_list,
        topics=topic_list,
        start_date=start_date,
        limit=limit
    )
    
    return {"articles": [vars(a) for a in articles]}


@app.get("/api/news/features/daily")
async def get_daily_features(
    ticker: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    service = get_news_service()
    
    features = service.get_daily_features(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date
    )
    
    return {"features": [vars(f) for f in features]}


@app.get("/api/news/stats")
async def get_news_stats():
    service = get_news_service()
    stats = service.get_stats()
    return vars(stats)
```

## 📊 Example Queries

### Top Tickers by Article Volume

```python
import duckdb

conn = duckdb.connect(":memory:")

df = conn.execute("""
SELECT 
    ticker,
    SUM(news_count) as total_articles,
    AVG(sent_mean) as avg_sentiment
FROM read_parquet('data/news/gold/features_daily/dt=2025-10-*/final.parquet')
GROUP BY ticker
ORDER BY total_articles DESC
LIMIT 10
""").df()

print(df)
```

### Sentiment Over Time for AAPL

```python
df = conn.execute("""
SELECT 
    date,
    news_count,
    sent_mean,
    sent_pos_share,
    sent_neg_share
FROM read_parquet('data/news/gold/features_daily/dt=*/final.parquet')
WHERE ticker = 'AAPL'
ORDER BY date DESC
LIMIT 30
""").df()

# Plot with matplotlib/seaborn
import matplotlib.pyplot as plt
plt.plot(df['date'], df['sent_mean'])
plt.title('AAPL News Sentiment Over Time')
plt.show()
```

### News Novelty (Unique Content Ratio)

```python
df = conn.execute("""
SELECT 
    date,
    ticker,
    news_count,
    news_novelty,
    news_count * news_novelty as unique_articles
FROM read_parquet('data/news/gold/features_daily/dt=2025-10-*/final.parquet')
WHERE ticker IN ('AAPL', 'MSFT', 'GOOGL')
ORDER BY date DESC, ticker
""").df()
```

## 🎯 Next Steps

1. **Run your first pipeline** with `--today`
2. **Backfill 1 month** to get meaningful data
3. **Integrate with your FastAPI** endpoints
4. **Connect to frontend** (React/webapp)
5. **Add to ML pipeline** for alpha signals

## 🆘 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| `No Bronze records` | Run Bronze ingestion first (`--today` without skip flags) |
| `DuckDB locked` | Close all connections, delete `.duckdb` lock files |
| `Feed timeout` | Some feeds are slow, increase timeout in `bronze_pipeline.py` |
| `Missing tickers` | Extend ticker mapping in `silver_pipeline.py` |
| `Low quality scores` | Check source_tier mappings in `news_schemas.py` |

## 📚 Full Documentation

For complete documentation, see: `docs/NEWS_INFRASTRUCTURE.md`

---

**🚀 You're all set! Run your first pipeline now:**

```bash
python scripts/news_orchestrator.py --today
```
